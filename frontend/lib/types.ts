// Types mirror the Pydantic models and the REST contract in
// tasks/ORCHESTRATION.md exactly. Field names match the backend one to one.

export type RetoolingComplexity = "low" | "medium" | "high" | "extreme";

export interface FoundryConfig {
  n_lines: number;
  hours_per_line_week: number;
  base_line_hour_cost: number;
  base_line_hour_value: number;
  engineering_hour_cost: number;
  current_utilization: number;
  target_margin: number;
  risk_percentile: number;
  downtime_probability: number;
  downtime_hours_mean: number;
  downtime_hours_sd: number;
}

export interface SimulationSettings {
  n_sims: number;
  random_seed: number;
}

export interface JobScenario {
  name: string;
  lines_requested: number;
  production_weeks: number;
  tooling_weeks_mean: number;
  tooling_weeks_sd: number;
  debug_weeks_mean: number;
  debug_weeks_sd: number;
  engineering_hours_mean: number;
  engineering_hours_sd: number;
  tooling_parts_cost_mean: number;
  tooling_parts_cost_sd: number;
  expected_units: number;
  revenue_per_unit: number;
  variable_cost_per_unit: number;
  yield_alpha: number;
  yield_beta: number;
  expedite_willingness_to_pay: number;
  retooling_complexity: RetoolingComplexity;
}

export interface DefaultConfigResponse {
  foundry: FoundryConfig;
  simulation: SimulationSettings;
}

export interface SampleScenariosResponse {
  scenarios: JobScenario[];
}

// One row per scenario. Matches summarize_results output.
export interface SummaryRow {
  scenario: string;
  avg_tooling_weeks: number;
  p80_tooling_weeks: number;
  avg_debug_weeks: number;
  avg_reserved_line_hours: number;
  avg_direct_cost: number;
  avg_opportunity_cost: number;
  p50_economic_floor: number;
  p80_economic_floor: number;
  p90_economic_floor: number;
  suggested_target_quote: number;
  suggested_expedited_quote: number;
  avg_margin_at_target: number;
  p10_margin_at_target: number;
  scarcity_multiplier: number;
  parallelism_multiplier: number;
  retooling_multiplier: number;
}

// Server-computed histogram. n+1 edges, n counts.
export interface Histogram {
  bin_edges: number[];
  counts: number[];
}

export interface ScenarioDistributions {
  economic_floor: Histogram;
  margin_at_target: Histogram;
}

export interface SimulateRequest {
  foundry: FoundryConfig;
  simulation: SimulationSettings;
  scenarios: JobScenario[];
}

export interface SimulateResponse {
  summary: SummaryRow[];
  distributions: Record<string, ScenarioDistributions>;
  explanations: Record<string, string>;
}

// Schedule endpoint. Included for completeness of the wrapper surface.
export interface BacklogJob {
  job_id: string;
  customer: string;
  required_line_weeks: number;
  margin_value: number;
  due_week: number;
  late_penalty_per_week: number;
  priority: number;
}

export interface ScheduleRequest {
  foundry: FoundryConfig;
  backlog: BacklogJob[];
  scenario?: JobScenario;
}

export interface OpportunityCost {
  opportunity_cost_from_schedule: number;
  total_net_value_without: number;
  total_net_value_with: number;
  delayed_jobs: { job_id: string; weeks_delayed: number }[];
}

export interface ScheduleRow {
  job_id: string;
  completion_week: number;
  lateness_weeks: number;
  late_penalty: number;
  net_value: number;
  [column: string]: number | string;
}

export interface ScheduleResponse {
  schedule: ScheduleRow[];
  opportunity_cost: OpportunityCost | null;
}
