"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  getDefaultConfig,
  getSampleScenarios,
  postSimulate,
} from "@/lib/api";
import type {
  FoundryConfig,
  JobScenario,
  SimulateResponse,
} from "@/lib/types";
import { Controls, type ControlValues } from "@/components/Controls";
import { MetricCards } from "@/components/MetricCards";
import { ScenarioTable } from "@/components/ScenarioTable";
import { DistributionsPanel } from "@/components/DistributionsPanel";
import { ExplanationPanel } from "@/components/ExplanationPanel";
import { FormulaDetails, HowToRead } from "@/components/InfoSections";

export default function Page() {
  const [baseFoundry, setBaseFoundry] = useState<FoundryConfig | null>(null);
  const [scenarios, setScenarios] = useState<JobScenario[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [controls, setControls] = useState<ControlValues | null>(null);

  const [initError, setInitError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>("");

  // Load defaults and sample scenarios once, then run automatically so the
  // dashboard shows real numbers on first paint when the backend is up.
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [config, sample] = await Promise.all([
          getDefaultConfig(),
          getSampleScenarios(),
        ]);
        if (cancelled) return;
        setBaseFoundry(config.foundry);
        setScenarios(sample.scenarios);
        setSelected(sample.scenarios.map((s) => s.name));
        setControls({
          nSims: config.simulation.n_sims,
          randomSeed: config.simulation.random_seed,
          nLines: config.foundry.n_lines,
          utilization: Math.round(config.foundry.current_utilization * 100),
          targetMargin: Math.round(config.foundry.target_margin * 100),
        });
      } catch (error) {
        if (cancelled) return;
        setInitError(
          error instanceof ApiError
            ? error.detail
            : "Could not load defaults from the backend.",
        );
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const patchControls = useCallback((patch: Partial<ControlValues>) => {
    setControls((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  const toggleScenario = useCallback((name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  }, []);

  const run = useCallback(async () => {
    if (!baseFoundry || !controls) return;
    const chosen = scenarios.filter((s) => selected.includes(s.name));
    if (chosen.length === 0) return;

    setRunning(true);
    setRunError(null);
    try {
      const response = await postSimulate({
        foundry: {
          ...baseFoundry,
          n_lines: controls.nLines,
          current_utilization: controls.utilization / 100,
          target_margin: controls.targetMargin / 100,
        },
        simulation: {
          n_sims: controls.nSims,
          random_seed: controls.randomSeed,
        },
        scenarios: chosen,
      });
      setResult(response);
      setSelectedScenario((current) => {
        const names = response.summary.map((row) => row.scenario);
        return names.includes(current) ? current : (names[0] ?? "");
      });
    } catch (error) {
      setRunError(
        error instanceof ApiError
          ? error.detail
          : "Something went wrong while running the simulation.",
      );
    } finally {
      setRunning(false);
    }
  }, [baseFoundry, controls, scenarios, selected]);

  // Auto-run once, after defaults arrive.
  const ready = Boolean(baseFoundry && controls && scenarios.length > 0);
  const [autoRan, setAutoRan] = useState(false);
  useEffect(() => {
    if (ready && !autoRan) {
      setAutoRan(true);
      run();
    }
  }, [ready, autoRan, run]);

  const activeRow = useMemo(
    () => result?.summary.find((row) => row.scenario === selectedScenario),
    [result, selectedScenario],
  );
  const activeDistributions = result?.distributions[selectedScenario];
  const activeExplanation = result?.explanations[selectedScenario];

  return (
    <div className="mx-auto max-w-[1400px] px-5 py-10 sm:px-8 lg:py-14">
      <Header />

      {initError ? (
        <div
          role="alert"
          className="mb-8 rounded-xl border border-red-500/40 bg-red-500/10 px-5 py-4 text-sm text-red-200"
        >
          <span className="font-semibold text-red-100">
            Could not reach the backend.{" "}
          </span>
          {initError} Start the API on port 8000 and reload.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div>
          {controls ? (
            <Controls
              values={controls}
              onChange={patchControls}
              scenarios={scenarios}
              selected={selected}
              onToggleScenario={toggleScenario}
              onRun={run}
              running={running}
              errorDetail={runError}
            />
          ) : (
            <div className="card h-64 animate-pulse" />
          )}
        </div>

        <div className="space-y-6">
          {!result ? (
            <EmptyState running={running} hasError={Boolean(initError)} />
          ) : (
            <>
              <MetricCards
                rows={result.summary}
                selectedScenario={selectedScenario}
                onSelectScenario={setSelectedScenario}
              />
              <ScenarioTable
                rows={result.summary}
                selectedScenario={selectedScenario}
                onSelectScenario={setSelectedScenario}
              />
              {activeRow && activeDistributions ? (
                <DistributionsPanel
                  scenario={selectedScenario}
                  distributions={activeDistributions}
                  summary={activeRow}
                />
              ) : null}
              {activeRow && activeExplanation ? (
                <ExplanationPanel
                  scenario={selectedScenario}
                  explanation={activeExplanation}
                  summary={activeRow}
                />
              ) : null}
            </>
          )}

          <div className="grid grid-cols-1 gap-4">
            <FormulaDetails />
            <HowToRead />
          </div>
        </div>
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="mb-10">
      <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-medium text-ink-300">
        <span className="h-1.5 w-1.5 rounded-full bg-accent-500" aria-hidden />
        Monte Carlo pricing
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-ink-50 sm:text-4xl">
        Foundry Pricing Simulator
      </h1>
      <p className="mt-3 max-w-2xl text-[1.02rem] leading-relaxed text-ink-300">
        Quoting a foundry job is not just counting line-hours. A job that grabs
        the whole factory for a week disrupts far more than one that takes a
        single line for a month, even when the line-weeks are identical. This
        tool runs thousands of simulations to price that difference and show you
        the full range of outcomes, not a single guess.
      </p>
    </header>
  );
}

function EmptyState({
  running,
  hasError,
}: {
  running: boolean;
  hasError: boolean;
}) {
  return (
    <div className="card grid h-72 place-items-center px-6 text-center">
      <div>
        <p className="text-base font-medium text-ink-200">
          {running
            ? "Running the simulation..."
            : hasError
              ? "Waiting on the backend."
              : "Run a simulation to see results."}
        </p>
        <p className="mt-1 text-sm text-ink-500">
          {running
            ? "Drawing thousands of cost outcomes per scenario."
            : "Adjust the controls on the left, then press Run simulation."}
        </p>
      </div>
    </div>
  );
}
