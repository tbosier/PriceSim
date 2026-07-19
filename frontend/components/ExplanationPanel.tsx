"use client";

import type { SummaryRow } from "@/lib/types";
import { formatMultiplier } from "@/lib/format";

interface ExplanationPanelProps {
  scenario: string;
  explanation: string;
  summary: SummaryRow;
}

export function ExplanationPanel({
  scenario,
  explanation,
  summary,
}: ExplanationPanelProps) {
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-ink-50">
          Why this quote, for {scenario}
        </h3>
        <div className="flex gap-2">
          <Pill label="Scarcity" value={formatMultiplier(summary.scarcity_multiplier)} />
          <Pill
            label="Parallelism"
            value={formatMultiplier(summary.parallelism_multiplier)}
          />
          <Pill
            label="Retooling"
            value={formatMultiplier(summary.retooling_multiplier)}
          />
        </div>
      </div>
      <p className="mt-3 text-[0.95rem] leading-relaxed text-ink-200">
        {explanation}
      </p>
    </div>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs">
      <span className="text-ink-500">{label}</span>
      <span className="tnum font-semibold text-ink-100">{value}</span>
    </span>
  );
}
