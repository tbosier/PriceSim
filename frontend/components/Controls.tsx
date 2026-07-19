"use client";

import type { JobScenario } from "@/lib/types";

export interface ControlValues {
  nSims: number;
  randomSeed: number;
  nLines: number;
  utilization: number; // percent, 0 to 100
  targetMargin: number; // percent, 0 to 95
}

interface ControlsProps {
  values: ControlValues;
  onChange: (patch: Partial<ControlValues>) => void;
  scenarios: JobScenario[];
  selected: string[];
  onToggleScenario: (name: string) => void;
  onRun: () => void;
  running: boolean;
  errorDetail: string | null;
}

function NumberField({
  label,
  hint,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  hint?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="field-label">{label}</span>
      <input
        className="input mt-1.5 tnum"
        type="number"
        value={Number.isNaN(value) ? "" : value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(e.target.valueAsNumber)}
      />
      {hint ? <span className="mt-1 block text-xs text-ink-500">{hint}</span> : null}
    </label>
  );
}

export function Controls({
  values,
  onChange,
  scenarios,
  selected,
  onToggleScenario,
  onRun,
  running,
  errorDetail,
}: ControlsProps) {
  const nothingSelected = selected.length === 0;

  return (
    <div className="card p-5 lg:sticky lg:top-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-ink-50">Controls</h2>
        <span className="text-xs text-ink-500">Prefilled from the API</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <NumberField
          label="Simulations"
          value={values.nSims}
          min={1}
          step={1000}
          onChange={(v) => onChange({ nSims: v })}
        />
        <NumberField
          label="Random seed"
          value={values.randomSeed}
          min={0}
          step={1}
          onChange={(v) => onChange({ randomSeed: v })}
        />
        <NumberField
          label="Lines"
          hint="Factory capacity"
          value={values.nLines}
          min={1}
          step={1}
          onChange={(v) => onChange({ nLines: v })}
        />
        <NumberField
          label="Utilization"
          hint="Percent, 0 to 100"
          value={values.utilization}
          min={0}
          max={100}
          step={1}
          onChange={(v) => onChange({ utilization: v })}
        />
        <NumberField
          label="Target margin"
          hint="Percent, 0 to 95"
          value={values.targetMargin}
          min={0}
          max={95}
          step={1}
          onChange={(v) => onChange({ targetMargin: v })}
        />
      </div>

      <div className="mt-5">
        <span className="field-label">Scenarios</span>
        <div className="mt-2 space-y-2">
          {scenarios.length === 0 ? (
            <p className="text-sm text-ink-500">Loading sample scenarios...</p>
          ) : (
            scenarios.map((s) => {
              const on = selected.includes(s.name);
              return (
                <button
                  key={s.name}
                  type="button"
                  onClick={() => onToggleScenario(s.name)}
                  className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                    on
                      ? "border-accent-500/60 bg-accent-500/10"
                      : "border-white/10 hover:border-white/20"
                  }`}
                >
                  <span
                    className={`grid h-4 w-4 shrink-0 place-items-center rounded border ${
                      on
                        ? "border-accent-500 bg-accent-500"
                        : "border-ink-400 bg-transparent"
                    }`}
                    aria-hidden
                  >
                    {on ? (
                      <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                        <path
                          d="M2.5 6.5l2.5 2.5 4.5-5"
                          stroke="#08111f"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : null}
                  </span>
                  <span className="text-sm text-ink-100">{s.name}</span>
                </button>
              );
            })
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onRun}
        disabled={running || nothingSelected}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-accent-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-500 disabled:cursor-not-allowed disabled:bg-ink-700 disabled:text-ink-400"
      >
        {running ? "Running simulation..." : "Run simulation"}
      </button>

      {nothingSelected ? (
        <p className="mt-2 text-xs text-ink-500">
          Select at least one scenario to run.
        </p>
      ) : null}

      {errorDetail ? (
        <div
          role="alert"
          className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2.5 text-sm text-red-200"
        >
          <span className="font-semibold text-red-100">Could not run. </span>
          {errorDetail}
        </div>
      ) : null}
    </div>
  );
}
