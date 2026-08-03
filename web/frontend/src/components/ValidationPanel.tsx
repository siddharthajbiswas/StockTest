import type { ValidationResult, VerdictLevel } from "../types";
import { pct, signedPct } from "../format";

// Plain-language framing for each overall outcome. Keyed by the engine's
// verdict.level, which counts how many of the three checks below held.
const HEADLINE: Record<VerdictLevel, string> = {
  held: "This strategy's edge held up out-of-sample",
  mixed: "Mixed evidence — some checks held, others didn't",
  failed: "This strategy's edge did not persist out-of-sample",
};

const SUBTEXT: Record<VerdictLevel, string> = {
  held:
    "On data it was NOT chosen using, this combo still ranked well and kept pace with the market. That's the sign of a real edge rather than a lucky fit.",
  mixed:
    "Some of the out-of-sample checks passed and some didn't. Treat the earlier result as promising but unproven — don't rely on it alone.",
  failed:
    "On data it was NOT chosen using, this combo's advantage disappeared. The earlier result was most likely luck or overfitting — treat it with caution.",
};

const CLS: Record<VerdictLevel, string> = {
  held: "lvl-good",
  mixed: "lvl-moderate",
  failed: "lvl-high",
};

function Check({ pass, title, children }: { pass: boolean; title: string; children: React.ReactNode }) {
  return (
    <li className="oos-item">
      <span className={"oos-badge " + (pass ? "pass" : "fail")}>{pass ? "✓" : "✕"}</span>
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </li>
  );
}

export function ValidationPanel({ data }: { data: ValidationResult }) {
  const { verdict: v, holdout: h, walkforward: w, meta } = data;

  return (
    <div className={"oos-panel " + CLS[v.level]}>
      <div className="oos-head">
        <span className={"oos-chip " + CLS[v.level]}>
          {v.level === "held" ? "Held up" : v.level === "mixed" ? "Mixed" : "Did not hold"}
        </span>
        <div>
          <strong className="oos-headline">{HEADLINE[v.level]}</strong>
          <p className="oos-sub">{SUBTEXT[v.level]}</p>
        </div>
      </div>

      <p className="oos-why">
        <strong>Why this matters:</strong> a strategy that looks good on one stretch of history can
        just be luck — it was picked <em>because</em> it happened to do well there. These checks
        re-score it on data it wasn't chosen using ({meta.span_years} years, split for a{" "}
        {meta.train_years}-year training window), which is a much harder test to pass.
      </p>

      <ul className="oos-list">
        <Check pass={h.rank_held} title="Its ranking held up on unseen data">
          Against {h.n_ranked} baseline combos, yours ranked #{h.your_test_rank} on the later,
          held-out half (it was #{h.your_train_rank} on the earlier half it was picked from).
          {h.spearman != null &&
            ` Overall, combos that ranked well early tended to rank well late (rank correlation ${h.spearman.toFixed(2)}).`}
        </Check>

        <Check pass={h.beats_spy_test} title="It beat the S&P 500 on the held-out half">
          On the unseen half it returned {pct(h.your_test_cagr)}/yr vs the S&P's{" "}
          {pct(h.spy_test_cagr)}/yr ({signedPct((h.your_test_cagr ?? 0) - (h.spy_test_cagr ?? 0))} edge).
        </Check>

        <Check pass={w.your_oos_beats_spy} title="Its walk-forward track record beat the S&P">
          {w.has_windows ? (
            <>
              Retested year-by-year on the out-of-sample span, it returned {pct(w.your_oos_cagr)}/yr
              vs the S&P's {pct(w.spy_oos_cagr)}/yr.
            </>
          ) : (
            <>Not enough post-training history to build walk-forward windows over this period.</>
          )}
        </Check>
      </ul>

      {w.has_windows && w.most_picked.length > 0 && (
        <p className="oos-foot">
          For reference, an “always chase last year's winner” strategy over the same span returned{" "}
          {pct(w.adaptive_oos_cagr)}/yr (S&P {pct(w.spy_oos_cagr)}/yr), most often landing on{" "}
          {w.most_picked
            .slice(0, 2)
            .map((p) => p.combo)
            .join(" and ")}
          .
        </p>
      )}
    </div>
  );
}
