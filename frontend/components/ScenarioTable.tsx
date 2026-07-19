"use client";

import type { SummaryRow } from "@/lib/types";
import {
  formatCurrency,
  formatMultiplier,
  formatPercent,
} from "@/lib/format";

interface ScenarioTableProps {
  rows: SummaryRow[];
  selectedScenario: string;
  onSelectScenario: (name: string) => void;
}

type Align = "left" | "right";

interface Column {
  key: string;
  label: string;
  align: Align;
  render: (row: SummaryRow) => string;
}

const COLUMNS: Column[] = [
  {
    key: "scenario",
    label: "Scenario",
    align: "left",
    render: (r) => r.scenario,
  },
  {
    key: "suggested_target_quote",
    label: "Target quote",
    align: "right",
    render: (r) => formatCurrency(r.suggested_target_quote),
  },
  {
    key: "suggested_expedited_quote",
    label: "Expedited quote",
    align: "right",
    render: (r) => formatCurrency(r.suggested_expedited_quote),
  },
  {
    key: "p50_economic_floor",
    label: "Floor p50",
    align: "right",
    render: (r) => formatCurrency(r.p50_economic_floor),
  },
  {
    key: "p80_economic_floor",
    label: "Floor p80",
    align: "right",
    render: (r) => formatCurrency(r.p80_economic_floor),
  },
  {
    key: "p90_economic_floor",
    label: "Floor p90",
    align: "right",
    render: (r) => formatCurrency(r.p90_economic_floor),
  },
  {
    key: "avg_margin_at_target",
    label: "Avg margin",
    align: "right",
    render: (r) => formatPercent(r.avg_margin_at_target),
  },
  {
    key: "p10_margin_at_target",
    label: "Margin p10",
    align: "right",
    render: (r) => formatPercent(r.p10_margin_at_target),
  },
  {
    key: "scarcity_multiplier",
    label: "Scarcity",
    align: "right",
    render: (r) => formatMultiplier(r.scarcity_multiplier),
  },
  {
    key: "parallelism_multiplier",
    label: "Parallelism",
    align: "right",
    render: (r) => formatMultiplier(r.parallelism_multiplier),
  },
  {
    key: "retooling_multiplier",
    label: "Retooling",
    align: "right",
    render: (r) => formatMultiplier(r.retooling_multiplier),
  },
];

export function ScenarioTable({
  rows,
  selectedScenario,
  onSelectScenario,
}: ScenarioTableProps) {
  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4">
        <h2 className="text-lg font-semibold text-ink-50">Scenario comparison</h2>
        <p className="mt-0.5 text-sm text-ink-400">
          Same total line-weeks, priced three ways. Click a row to focus its
          charts and explanation.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] border-collapse text-sm">
          <thead>
            <tr className="border-y border-white/[0.06] bg-white/[0.02]">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-400 ${
                    col.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const active = row.scenario === selectedScenario;
              return (
                <tr
                  key={row.scenario}
                  onClick={() => onSelectScenario(row.scenario)}
                  className={`cursor-pointer border-b border-white/[0.04] transition-colors last:border-b-0 ${
                    active ? "bg-accent-500/[0.08]" : "hover:bg-white/[0.03]"
                  }`}
                >
                  {COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className={`whitespace-nowrap px-4 py-3 ${
                        col.align === "right"
                          ? "tnum text-right text-ink-100"
                          : "font-medium text-ink-50"
                      } ${
                        col.key === "scenario" && active
                          ? "border-l-2 border-accent-500"
                          : ""
                      }`}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
