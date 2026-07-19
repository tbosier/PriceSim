"use client";

import type { ScenarioDistributions, SummaryRow } from "@/lib/types";
import { formatCurrencyCompact, formatPercent } from "@/lib/format";
import { HistogramChart } from "./HistogramChart";

interface DistributionsPanelProps {
  scenario: string;
  distributions: ScenarioDistributions;
  summary: SummaryRow;
}

export function DistributionsPanel({
  scenario,
  distributions,
  summary,
}: DistributionsPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-base font-semibold text-ink-50">
          Economic floor distribution
        </h3>
        <p className="mt-0.5 text-sm text-ink-400">
          The all-in cost to serve this job across {scenario}. The target quote
          sits above this floor.
        </p>
        <div className="mt-4">
          <HistogramChart
            histogram={distributions.economic_floor}
            color="#3b82f6"
            formatX={(v) => formatCurrencyCompact(v)}
            marker={{
              value: summary.suggested_target_quote,
              label: "Target quote",
            }}
          />
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-base font-semibold text-ink-50">
          Margin at target distribution
        </h3>
        <p className="mt-0.5 text-sm text-ink-400">
          Realized margin if you win at the target quote. The dashed line marks
          break-even.
        </p>
        <div className="mt-4">
          <HistogramChart
            histogram={distributions.margin_at_target}
            color="#60a5fa"
            formatX={(v) => formatPercent(v, 0)}
            marker={{ value: 0, label: "Break-even" }}
          />
        </div>
      </div>
    </div>
  );
}
