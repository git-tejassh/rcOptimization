// Shapes of web/public/data/*.json (written by `rcopt export`, see src/rcopt/report/export_json.py).

export interface Meta {
  project: string;
  generated: string;
  config_hash: string;
  provisional: boolean;
  provisional_items: string[];
  gravity_only_caveat: string;
  honest_novelty: string;
  deviations: { id: string; brief: string; spec: string; reason: string }[];
  frame: {
    bays_x_m: number[];
    bays_z_m: number[];
    storey_heights_m: number[];
    stub_height_m: number;
    beam_groups: number[][];
    column_groups: number[][];
    column_D_axis: string;
  };
  headline: Record<string, number | string | null>;
  findings: { level: "info" | "warn" | "bad"; text: string }[];
}

export interface Gene {
  name: string;
  options: (number | string)[];
}
export interface DesignSpaceData {
  genes: Gene[];
  n_genes: number;
  total_combinations: number;
  beam_groups: number[][];
  column_groups: number[][];
  cover_mm: { exposure: string; beam: number; column: number };
  detailing: Record<string, number | boolean>;
  sampling: Record<string, unknown>;
  constraints: { name: string; description: string; clause: string }[];
}

export interface BeamDesc {
  group: number;
  b_mm: number;
  D_mm: number;
  bottom: string;
  top: string;
  stirrups: string;
}
export interface ColDesc {
  group: number;
  b_mm: number;
  D_mm: number;
  bars: string;
  pt_percent: number;
}
export interface Verification {
  verified: boolean;
  passed?: boolean;
  boundary_pick?: boolean;
  reasons?: string[];
}
export interface ParetoDesign {
  id: number;
  genome: number[];
  concrete: string;
  steel: string;
  cement: string;
  beams: BeamDesc[];
  columns: ColDesc[];
  pred_cost: number;
  pred_carbon: number;
  true_cost: number | null;
  true_carbon: number | null;
  feasible_true: boolean;
  status: string;
  quantities?: Record<string, number>;
  cost_inr?: Record<string, number>;
  carbon_kgco2e?: Record<string, number>;
  utilisation?: {
    flexure_by_beam_group: number[];
    shear_by_beam_group: number[];
    column_by_group: number[];
    U_flex_max: number;
    U_shear_max: number;
    U_col_max: number;
    deflection_ratio: number;
    deflection_mm: number;
  };
  stirrup_spacing_mm?: number[];
  pred_util?: Record<string, number>;
  verification: Verification;
}
export interface ParetoData {
  variants: Record<string, ParetoDesign[]>;
  cloud: { cost: number; carbon: number; feasible: boolean; stratum: string }[];
  labels: Record<string, string>;
}

export interface MetricBlock {
  n: number;
  R2: number;
  MAE: number;
  RMSE: number;
  max_abs_err: number;
  p95_abs_err: number;
}
export interface ModelEval {
  overall: Record<string, MetricBlock>;
  boundary: Record<string, MetricBlock>;
  n_boundary: number;
  feasibility_overall: Record<string, number>;
  feasibility_boundary: Record<string, number>;
  gmax_boundary_abs_err_q95: number;
  cost_mape?: number;
  demands?: Record<string, MetricBlock & { mean_abs_value: number }>;
}
export interface SurrogateData {
  n_train: number;
  n_test: number;
  n_test_boundary: number;
  chosen_params: Record<string, number>;
  tuning: { params: Record<string, number>; cv_mean_log_mae: number; cv_std: number }[];
  before_AL: { A: ModelEval; B: ModelEval };
  after_AL: { A: ModelEval; B: ModelEval };
  baseline_random_forest_A_before_AL: ModelEval;
  active_learning: Record<string, unknown>;
  margin_q95: { A: number; B: number };
  feature_importance_top: Record<string, Record<string, number>>;
  parity_points_before: Record<string, Record<string, unknown>>;
  parity_points_after: Record<string, Record<string, unknown>>;
}

export interface VerificationRow {
  index: number;
  pred_cost: number;
  true_cost?: number;
  boundary_pick: boolean;
  status: string;
  feasible_true?: boolean;
  passed: boolean;
  reasons: string[];
  [k: string]: unknown;
}
export interface VerificationVariant {
  variant: string;
  front_size: number;
  n_verified: number;
  n_pass: number;
  pass_rate: number;
  pass_target: number;
  target_met: boolean;
  n_truly_feasible: number;
  n_within_tolerance: number;
  boundary_picks: { n: number; n_pass: number };
  failures: { index: number; boundary_pick: boolean; reasons: string[] }[];
  error_stats: Record<string, { mean_abs_err: number; max_abs_err: number }>;
  cost_rel_err_mean: number | null;
  carbon_rel_err_mean: number | null;
  designs: VerificationRow[];
}
export interface VerificationData {
  tolerance: { util_abs: number; defl_rel: number };
  selection: Record<string, number>;
  variants: Record<string, VerificationVariant>;
  full_front: Record<string, Record<string, number>>;
}

export interface ComputeData {
  compute: {
    mean_fe_solve_time_s_single_process: number;
    data_generation: Record<string, number>;
    surrogate_training_s: number;
    configs: Record<string, Record<string, number>>;
  };
  optimization: Record<
    string,
    {
      hv_final_mean: number;
      hv_final_std: number;
      hv_pooled_front_true: number;
      pooled_front_size: number;
      true_front_size: number;
      cost_carbon_correlation_pooled: number;
      convergence: { n_eval: number[]; hv_mean: number[]; hv_std: number[] };
    }
  >;
  verdict: string;
}

export interface SensitivityData {
  scenarios: {
    name: string;
    label: string;
    front_size: number;
    hv: number;
    cost_range: number[];
    carbon_range: number[];
    baseline_survival_fraction: number;
    cost_rank_spearman: number;
    carbon_rank_spearman: number;
    knee: { cost: number; carbon: number; concrete: string; steel: string; same_knee_as_baseline: boolean };
    front: { cost: number; carbon: number }[];
  }[];
  verdict: string;
}

export interface CementData {
  n_structural_designs: number;
  note: string;
  scenarios: {
    psc_premium_inr_per_kg: number | null;
    psc_price_inr_per_kg: number;
    front_size: number;
    cost_span_pct: number;
    carbon_span_pct: number;
    cement_types_on_front: Record<string, number>;
    front: { cost: number; carbon: number; cement: string }[];
  }[];
}

export interface ProvenanceData {
  cost_rates: { item: string; value: number; unit: string; source: string; status: string }[];
  carbon_factors: { item: string; value: number | string; unit: string; source: string; confidence?: string; india_specific?: boolean; status: string }[];
  is456_tables_status: string;
  assumptions_markdown: string;
  decisions_markdown: string;
  benchmark_markdown: string;
  carbon_audit_markdown: string;
}

export interface SampleData {
  name: string;
  text: string;
}
