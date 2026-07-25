import { useEffect, useRef, useState } from "react";
import { searchTickers } from "../api";
import type { TickerRecord, UniverseNote } from "../types";

interface Props {
  selected: string[];
  onChange: (tickers: string[]) => void;
  universeNote: UniverseNote | null;
}

export function TickerPicker({ selected, onChange, universeNote }: Props) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<TickerRecord[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounced search-as-you-type against /tickers/search.
  useEffect(() => {
    const term = q.trim();
    if (!term) {
      setResults([]);
      return;
    }
    const h = setTimeout(async () => {
      try {
        const { results } = await searchTickers(term, 12);
        setResults(results);
        setActive(0);
        setOpen(true);
      } catch {
        setResults([]);
      }
    }, 160);
    return () => clearTimeout(h);
  }, [q]);

  // Close the dropdown on outside click.
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const add = (sym: string) => {
    if (!selected.includes(sym)) onChange([...selected, sym]);
    setQ("");
    setResults([]);
    setOpen(false);
  };
  const remove = (sym: string) => onChange(selected.filter((s) => s !== sym));

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      add(results[active].symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div>
      {universeNote && (
        <div className="note-banner">
          <span aria-hidden>ℹ️</span>
          <span>
            You can pick from a fixed set of <strong>{universeNote.count} well-known US
            stocks</strong> we have price history for — not literally any ticker. Search by symbol
            {universeNote.has_company_names ? " or company name" : ""}.
          </span>
        </div>
      )}

      <div className="search-wrap" ref={boxRef}>
        <input
          className="search-input"
          placeholder="Search a ticker, e.g. AAPL, MSFT, JPM…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={onKeyDown}
          aria-label="Search tickers"
        />
        {open && results.length > 0 && (
          <div className="results-list" role="listbox">
            {results.map((r, idx) => {
              const chosen = selected.includes(r.symbol);
              return (
                <div
                  key={r.symbol}
                  className={"result-row" + (idx === active ? " active" : "")}
                  role="option"
                  aria-selected={idx === active}
                  onMouseEnter={() => setActive(idx)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    if (!chosen) add(r.symbol);
                  }}
                >
                  <span className="sym mono">{r.symbol}</span>
                  <span className="nm">{r.name ?? "—"}</span>
                  {chosen ? <span className="added">Added ✓</span> : <span className="added" style={{ color: "var(--muted)" }}>Add +</span>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="chips">
        {selected.length === 0 ? (
          <span className="empty-hint">No stocks selected yet — search and add a few above.</span>
        ) : (
          selected.map((s) => (
            <span key={s} className="chip mono">
              {s}
              <button onClick={() => remove(s)} aria-label={`Remove ${s}`}>
                ×
              </button>
            </span>
          ))
        )}
      </div>
    </div>
  );
}
