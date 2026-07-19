"use client";

import type { SummaryRow } from "@/lib/types";
import {
  formatCurrency,
  formatCurrencyCompact,
  formatMultiplier,
} from "@/lib/format";

interface MetricCardsProps {
  rows: SummaryRow[];
  selectedScenario: string;
  onSelectScenario: (name: string) => void;
}

export function MetricCards({
  rows,
  selectedScenario,
  onSelectScenario,
}: MetricCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((row) => {
        const active = row.scenario === selectedScenario;
        return (
          <button
            key={row.scenario}
            type="button"
            onClick={() => onSelectScenario(row.scenario)}
            className={`card p-5 text-left transition-all ${
              active
                ? "ring-2 ring-accent-500/70"
                : "hover:border-white/15 hover:bg-white/[0.02]"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink-100">
                {row.scenario}
              </h3>
              {active ? (
                <span className="shrink-0 rounded-full bg-accent-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-accent-400">
                  Selected
                </span>
              ) : null}
            </div>

            <div className="mt-4">
              <span className="field-label">Target quote</span>
              <div
                className="tnum mt-1 text-4xl font-semibold text-ink-50"
                title={formatCurrency(row.suggested_target_quote)}
              >
                {formatCurrencyCompact(row.suggested_target_quote)}
              </div>
            </div>

            <div className="mt-4 border-t border-white/[0.06] pt-4">
              <span className="field-label">Expedited quote</span>
              <div
                className="tnum mt-1 text-2xl font-semibold text-accent-400"
                title={formatCurrency(row.suggested_expedited_quote)}
              >
                {formatCurrencyCompact(row.suggested_expedited_quote)}
              </div>
            </div>

            <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-4 text-center">
              <div>
                <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">
                  Scarcity
                </dt>
                <dd className="tnum mt-0.5 text-sm font-semibold text-ink-100">
                  {formatMultiplier(row.scarcity_multiplier)}
                </dd>
              </div>
              <div>
                <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">
                  Parallel
                </dt>
                <dd className="tnum mt-0.5 text-sm font-semibold text-ink-100">
                  {formatMultiplier(row.parallelism_multiplier)}
                </dd>
              </div>
              <div>
                <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">
                  Retool
                </dt>
                <dd className="tnum mt-0.5 text-sm font-semibold text-ink-100">
                  {formatMultiplier(row.retooling_multiplier)}
                </dd>
              </div>
            </dl>
          </button>
        );
      })}
    </div>
  );
}
