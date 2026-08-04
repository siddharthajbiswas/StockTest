/**
 * Browser-side engine service — the in-worker equivalent of
 * `reference/service.py::EngineService`.
 *
 * Same responsibilities: load the data once, cache built markets per
 * (universe, start, end), and turn a request into a response. The differences
 * are environment, not behaviour:
 *
 *   * Data arrives over `fetch` from the Phase 1 bundle instead of from CSVs.
 *     The loader is injected so tests can serve it from disk.
 *   * Loading is LAZY and split. Manual mode pulls a handful of per-ticker
 *     files (~129 kB gzipped each); only picker mode pays for the 13 MB
 *     universe bundle. Python loads everything at startup because it can.
 *   * No locking. A worker is single-threaded, so the mutex around the market
 *     cache has nothing to protect.
 */

import { Backtest } from "./engine.js";
import { Combo, type Rebalance } from "./composite.js";
import { MarketData } from "./market.js";
import { Result } from "./result.js";
import { makeTaxPolicy, type TaxPolicy } from "./tax.js";
import { makePicker, FixedListPicker, type Fundamentals } from "./pickers.js";
import { makeTimer } from "./timers.js";
import { BuyAndHold } from "./strategies.js";
import { TickerIndex, type TickerRecord } from "./search.js";
import {
  clipSeries, dayFromIso, decodeCalendar, decodeTicker, decodeUniverse,
  type TickerSeries,
} from "./data.js";
import { membersByCalendar, type PitMembership } from "./universe.js";
import { alignTotals, metricsDict, roundTrips, totals, tradesList } from "./serialize.js";
import { isoOfDay } from "./result.js";
import { runAllCurves, type ProgressFn } from "./walkforward.js";
import { runValidation, type ValidationResult } from "./validation.js";

const BENCHMARK = "SPY";
const MARKET_CACHE_MAX = 16;

/** Fetches a bundle-relative path. Injected so tests can read from disk. */
export type Loader = (path: string) => Promise<ArrayBuffer>;

export interface BacktestRequest {
  picker_id?: string | null;
  picker_params?: Record<string, number | string | null>;
  tickers?: string[] | null;
  timer_id: string;
  timer_params?: Record<string, number | string>;
  top_n?: number;
  rebalance?: Rebalance;
  universe?: "all" | "sp500-pit";
  start?: string | null;
  end?: string | null;
  cash?: number;
  commission_pct?: number;
  slippage_pct?: number;
  tax?: {
    enabled: boolean; short_term_rate: number;
    long_term_rate: number; long_term_days: number;
  };
}

export class UnknownTickersError extends Error {
  constructor(readonly missing: string[]) {
    super(`Unknown ticker(s): ${missing.join(", ")}`);
    this.name = "UnknownTickersError";
  }
}

export class InvalidStrategyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidStrategyError";
  }
}

const DEFAULT_TAX = {
  enabled: true, short_term_rate: 0.35, long_term_rate: 0.15, long_term_days: 365,
};

export class EngineService {
  private manifest: any = null;
  private calendar: Int32Array = new Int32Array(0);
  private fundamentals: Fundamentals | null = null;
  private pit: PitMembership | null = null;
  private catalog: any = null;
  private index: TickerIndex | null = null;
  private dataStart: string | null = null;
  private dataEnd: string | null = null;
  private fingerprint = "unknown";

  private universeSeries: Map<string, TickerSeries> | null = null;
  private readonly tickerCache = new Map<string, TickerSeries>();
  private readonly marketCache = new Map<string, MarketData>();
  /**
   * In-flight loads, keyed by path. Without this, two concurrent callers both
   * observe an empty cache and each start their own download — which for
   * universe.bin means fetching 13 MB two or three times over. Memoizing the
   * PROMISE (not just the result) collapses them into one request.
   */
  private readonly inflight = new Map<string, Promise<unknown>>();

  /** Run `fn` once per key, sharing the promise with concurrent callers. */
  private once<T>(key: string, fn: () => Promise<T>): Promise<T> {
    const existing = this.inflight.get(key) as Promise<T> | undefined;
    if (existing !== undefined) return existing;
    const p = fn().finally(() => this.inflight.delete(key));
    this.inflight.set(key, p);
    return p;
  }

  constructor(private readonly load: Loader) {}

  // ---- lazy loading ----------------------------------------------------
  private async json<T>(path: string): Promise<T> {
    const buf = await this.load(path);
    return JSON.parse(new TextDecoder().decode(buf)) as T;
  }

  /** Metadata + calendar only — small, and enough for the catalog UI. */
  async init(): Promise<void> {
    if (this.manifest !== null) return;
    const [manifest, calBuf, catalog, tickers] = await Promise.all([
      this.json<any>("manifest.json"),
      this.load("calendar.bin"),
      this.json<any>("catalog.json"),
      this.json<any>("tickers.json"),
    ]);
    this.manifest = manifest;
    this.calendar = decodeCalendar(calBuf);
    this.catalog = catalog;
    this.index = new TickerIndex(tickers.records as TickerRecord[], tickers.has_name_data);
    this.dataStart = tickers.data_start ?? null;
    this.dataEnd = tickers.data_end ?? null;
    // Identifies the exact price bundle, for namespacing the client-side result
    // cache. Served from here because the deployed bundle ships only .gz files —
    // a main-thread fetch of "manifest.json" would 404.
    this.fingerprint = `${manifest.format_version}:${manifest.universe?.sha256 ?? "unknown"}`;
  }

  private async needFundamentals(): Promise<Fundamentals> {
    if (this.fundamentals !== null) return this.fundamentals;
    return this.once("fundamentals.json", async () => {
      this.fundamentals = await this.json<Fundamentals>("fundamentals.json");
      return this.fundamentals;
    });
  }

  private async needPit(): Promise<PitMembership> {
    if (this.pit !== null) return this.pit;
    return this.once("sp500-pit.json", async () => {
      this.pit = await this.json<PitMembership>("sp500-pit.json");
      return this.pit;
    });
  }

  /** The 13 MB Close bundle — only picker mode needs it. */
  private async needUniverse(): Promise<Map<string, TickerSeries>> {
    if (this.universeSeries !== null) return this.universeSeries;
    return this.once("universe.bin", async () => {
      const buf = await this.load("universe.bin");
      this.universeSeries = decodeUniverse(buf, this.manifest.universe.tickers, this.calendar);
      return this.universeSeries;
    });
  }

  private async needTicker(symbol: string): Promise<TickerSeries> {
    const hit = this.tickerCache.get(symbol);
    if (hit !== undefined) return hit;
    return this.once(`tickers/${symbol}.bin`, async () => {
      const buf = await this.load(`tickers/${symbol}.bin`);
      const decoded = decodeTicker(symbol, buf, this.calendar);
      this.tickerCache.set(symbol, decoded);
      return decoded;
    });
  }

  private cachePut(key: string, m: MarketData): void {
    this.marketCache.set(key, m);
    if (this.marketCache.size > MARKET_CACHE_MAX) {
      const oldest = this.marketCache.keys().next().value as string | undefined;
      if (oldest !== undefined) this.marketCache.delete(oldest);
    }
  }

  // ---- catalog / discovery --------------------------------------------
  health() {
    return {
      status: "ok",
      tickers_loaded: this.index?.count() ?? 0,
      data_start: this.dataStart ?? undefined,
      data_end: this.dataEnd ?? undefined,
      data_fingerprint: this.fingerprint,
    };
  }

  pickers() { return this.catalog.pickers; }
  timers() { return this.catalog.timers; }
  universes() { return this.catalog.universes; }

  private universeNote() {
    return {
      count: this.index?.count() ?? 0,
      has_name_data: this.index?.hasNameData ?? false,
    };
  }

  allTickers() {
    return { universe: this.universeNote(), tickers: this.index!.all() };
  }

  searchTickers(q: string, limit = 20) {
    return { universe: this.universeNote(), results: this.index!.search(q, limit) };
  }

  /**
   * One ticker's close-price history, for the stock detail view.
   *
   * Reads the same per-ticker file a manual-mode backtest would, so opening a
   * stock from the trade log costs nothing extra once that ticker is cached.
   * Downsamples to at most `maxPoints` bars: a full history can be 16,000 days,
   * and the chart cannot resolve more than a few hundred. The last bar is always
   * kept so the series ends where the data does rather than at a stride boundary.
   */
  async tickerHistory(
    symbol: string,
    start: string | null = null,
    end: string | null = null,
    maxPoints = 900,
  ): Promise<{
    symbol: string;
    name: string | null;
    dates: string[];
    closes: number[];
    first_date: string | null;
    last_date: string | null;
    n_bars: number;
  }> {
    await this.init();
    const record = this.index!.get(symbol);
    if (record === undefined) throw new UnknownTickersError([symbol]);

    const full = await this.needTicker(symbol);
    const clipped = clipSeries(
      full,
      start === null ? null : dayFromIso(start),
      end === null ? null : dayFromIso(end),
    );
    const close = clipped.fields.Close;
    const n = clipped.days.length;
    if (close === undefined || n === 0) {
      return {
        symbol, name: record.name, dates: [], closes: [],
        first_date: null, last_date: null, n_bars: 0,
      };
    }

    const stride = Math.max(1, Math.ceil(n / maxPoints));
    const dates: string[] = [];
    const closes: number[] = [];
    for (let i = 0; i < n; i += stride) {
      dates.push(isoOfDay(clipped.days[i]));
      closes.push(close[i]);
    }
    if ((n - 1) % stride !== 0) {
      dates.push(isoOfDay(clipped.days[n - 1]));
      closes.push(close[n - 1]);
    }

    return {
      symbol,
      name: record.name,
      dates,
      closes,
      first_date: isoOfDay(clipped.days[0]),
      last_date: isoOfDay(clipped.days[n - 1]),
      n_bars: n,
    };
  }

  // ---- market construction --------------------------------------------
  private async manualMarket(tickers: string[], start: string | null, end: string | null) {
    const wanted = [...new Set(tickers)];
    const missing = wanted.filter((t) => this.index!.get(t) === undefined);
    if (missing.length > 0) throw new UnknownTickersError(missing);

    const withSpy = wanted.includes(BENCHMARK) ? wanted : [...wanted, BENCHMARK];
    const key = `manual|${withSpy.join(",")}|${start}|${end}`;
    const cached = this.marketCache.get(key);
    const startDay = start ? dayFromIso(start) : null;
    const endDay = end ? dayFromIso(end) : null;

    const prices = new Map<string, TickerSeries>();
    for (const t of withSpy) {
      let s: TickerSeries;
      try {
        s = await this.needTicker(t);
      } catch {
        continue; // SPY may legitimately be absent from a trimmed bundle
      }
      const c = clipSeries(s, startDay, endDay);
      if (c.days.length > 0) prices.set(t, c);
    }
    const basket = wanted.filter((t) => prices.has(t));
    if (basket.length === 0) {
      throw new InvalidStrategyError("None of the requested tickers have data in the date range.");
    }
    const market = cached ?? new MarketData(prices, null);
    if (cached === undefined) this.cachePut(key, market);
    return { market, prices, tickersUsed: basket };
  }

  private async universeMarket(
    universe: "all" | "sp500-pit", start: string | null, end: string | null,
  ) {
    const key = `universe|${universe}|${start}|${end}`;
    const startDay = start ? dayFromIso(start) : null;
    const endDay = end ? dayFromIso(end) : null;

    const uni = await this.needUniverse();
    const prices = new Map<string, TickerSeries>();
    for (const t of [...(this.manifest.universe.tickers as string[])].sort()) {
      const s = uni.get(t);
      if (s === undefined) continue;
      const c = clipSeries(s, startDay, endDay);
      if (c.days.length > 0) prices.set(t, c);
    }
    if (prices.size === 0) {
      throw new InvalidStrategyError("No price data in the requested date range.");
    }

    const cached = this.marketCache.get(key);
    if (cached !== undefined) return { market: cached, prices };

    let members: Array<Set<string>> | null = null;
    if (universe === "sp500-pit") {
      const cal = new MarketData(prices, null).calendar;
      members = membersByCalendar(await this.needPit(), cal, new Set(prices.keys()));
    }
    const market = new MarketData(prices, members);
    this.cachePut(key, market);
    return { market, prices };
  }

  // ---- the core run ----------------------------------------------------
  async runBacktest(req: BacktestRequest): Promise<any> {
    await this.init();
    const tax = req.tax ?? DEFAULT_TAX;
    const isManual = req.tickers != null && req.tickers.length > 0;
    if (isManual === (req.picker_id != null)) {
      throw new InvalidStrategyError(
        "Provide exactly one of `picker_id` (AI mode) or a non-empty `tickers` list.",
      );
    }
    const cash = req.cash ?? 100_000.0;
    const commissionPct = req.commission_pct ?? 0.0005;
    const slippagePct = req.slippage_pct ?? 0.0005;
    const rebalance = req.rebalance ?? "M";
    const start = req.start ?? null;
    const end = req.end ?? null;

    let market: MarketData;
    let prices: Map<string, TickerSeries>;
    let tickersUsed: string[] | null = null;
    let topN: number;

    if (isManual) {
      const m = await this.manualMarket(req.tickers!, start, end);
      market = m.market; prices = m.prices; tickersUsed = m.tickersUsed;
      topN = Math.max(1, req.tickers!.length);
    } else {
      const m = await this.universeMarket(req.universe ?? "all", start, end);
      market = m.market; prices = m.prices;
      topN = req.top_n ?? 15;
    }

    const fundamentals = isManual ? null : await this.needFundamentals();
    const policy: TaxPolicy | null = tax.enabled
      ? makeTaxPolicy(tax.short_term_rate, tax.long_term_rate, tax.long_term_days)
      : null;

    const makeStrat = () =>
      new Combo(
        isManual
          ? new FixedListPicker(req.tickers!)
          : makePicker(req.picker_id!, req.picker_params ?? {}, fundamentals),
        makeTimer(req.timer_id, req.timer_params ?? {}),
        topN,
        rebalance,
      );

    const run = (p: TaxPolicy | null): Result =>
      new Backtest(makeStrat(), market, {
        cash, commissionPct, slippagePct, taxPolicy: p,
      }).run();

    const net = run(policy);
    const gross = policy !== null ? run(null) : net;

    let benchmark: any = null;
    const spy = prices.get(BENCHMARK);
    if (spy !== undefined) {
      const spyMarket = new MarketData(new Map([[BENCHMARK, spy]]), null);
      const runSpy = (p: TaxPolicy | null): Result =>
        new Backtest(new BuyAndHold(), spyMarket, {
          cash, commissionPct, slippagePct, taxPolicy: p,
        }).run();
      const spyNet = runSpy(policy);
      const spyGross = policy !== null ? runSpy(null) : spyNet;
      benchmark = {
        benchmark: BENCHMARK,
        metrics: metricsDict(spyNet),
        excess_cagr: net.cagr - spyNet.cagr,
        beats_spy: net.cagr > spyNet.cagr,
        excess_after_tax_cagr: null,
        beats_spy_after_tax: null,
      };
      if (net.taxesPaid !== null && spyNet.taxesPaid !== null) {
        benchmark.excess_after_tax_cagr = net.afterTaxCagr - spyNet.afterTaxCagr;
        benchmark.beats_spy_after_tax = net.afterTaxCagr > spyNet.afterTaxCagr;
      }
      benchmark.curve = {
        pretax: alignTotals(spyGross, market.calendar),
        aftertax: alignTotals(spyNet, market.calendar),
      };
    }

    const { rt, winRate } = roundTrips(net.trades);
    const metrics: Record<string, unknown> = { ...metricsDict(net) };
    metrics.pretax_cagr = gross.cagr;
    metrics.pretax_total_return = gross.totalReturn;
    metrics.final_value_pretax = gross.finalValue;
    metrics.tax_drag_value = gross.finalValue - net.afterTaxFinalValue;
    metrics.tax_drag_cagr = gross.cagr - net.afterTaxCagr;
    metrics.win_rate = winRate;
    metrics.n_round_trips = rt.length;

    const days = market.calendar;
    return {
      mode: isManual ? "manual" : "picker",
      picker_id: isManual ? null : req.picker_id,
      timer_id: req.timer_id,
      universe: isManual ? "all" : (req.universe ?? "all"),
      period: { start: isoOfDay(days[0]), end: isoOfDay(days[days.length - 1]) },
      tickers_used: tickersUsed,
      metrics,
      equity_curve: {
        dates: Array.from(days, isoOfDay),
        pretax: totals(gross),
        aftertax: totals(net),
      },
      benchmark,
      trades: tradesList(net),
      round_trips: rt,
    };
  }

  /** The user's exact combo as a net-of-tax equity curve, for validation. */
  private async targetCurve(req: BacktestRequest, market: MarketData, topN: number) {
    const tax = req.tax ?? DEFAULT_TAX;
    const isManual = req.tickers != null && req.tickers.length > 0;
    const fundamentals = isManual ? null : await this.needFundamentals();
    const policy = tax.enabled
      ? makeTaxPolicy(tax.short_term_rate, tax.long_term_rate, tax.long_term_days)
      : null;
    return new Backtest(
      new Combo(
        isManual
          ? new FixedListPicker(req.tickers!)
          : makePicker(req.picker_id!, req.picker_params ?? {}, fundamentals),
        makeTimer(req.timer_id, req.timer_params ?? {}),
        topN,
        req.rebalance ?? "M",
      ),
      market,
      {
        cash: 100_000.0,
        commissionPct: req.commission_pct ?? 0.0005,
        slippagePct: req.slippage_pct ?? 0.0005,
        taxPolicy: policy,
      },
    ).run();
  }

  async runValidation(
    req: BacktestRequest & { split?: string | null; train_years?: number; step_years?: number; price_only?: boolean },
    onProgress?: ProgressFn,
  ): Promise<ValidationResult> {
    await this.init();
    const tax = req.tax ?? DEFAULT_TAX;
    const isManual = req.tickers != null && req.tickers.length > 0;
    const priceOnly = req.price_only ?? true;

    // Python: the sweep universe is cfg.universe, or sp500-pit for manual mode
    // (a manual basket has no universe of its own to sweep).
    const sweepUniverse = isManual ? "sp500-pit" : (req.universe ?? "all");
    const { market, prices } = await this.universeMarket(
      sweepUniverse as "all" | "sp500-pit", req.start ?? null, req.end ?? null,
    );
    const spy = prices.get(BENCHMARK);
    const spyMarket = spy === undefined ? null : new MarketData(new Map([[BENCHMARK, spy]]), null);

    const sweep = await runAllCurves(
      {
        market, spyMarket,
        cash: 100_000.0,
        commissionPct: req.commission_pct ?? 0.0005,
        slippagePct: req.slippage_pct ?? 0.0005,
        policy: makeTaxPolicy(
          tax.enabled ? tax.short_term_rate : 0.35,
          tax.enabled ? tax.long_term_rate : 0.15,
          365,
        ),
        priceOnly,
        fundamentals: priceOnly ? null : await this.needFundamentals(),
      },
      onProgress,
    );

    // The user's own combo runs on its own market when manual.
    let targetMarket = market;
    let topN = req.top_n ?? 15;
    if (isManual) {
      const m = await this.manualMarket(req.tickers!, req.start ?? null, req.end ?? null);
      targetMarket = m.market;
      topN = Math.max(1, req.tickers!.length);
    }
    const target = await this.targetCurve(req, targetMarket, topN);

    return runValidation({
      sweep,
      targetDays: target.equity.days,
      targetTotals: target.equity.total,
      split: req.split ?? null,
      trainYears: req.train_years ?? 3,
      stepYears: req.step_years ?? 1,
      priceOnly,
    }, onProgress);
  }
}
