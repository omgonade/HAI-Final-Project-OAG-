// Milestone 3 endpoints. These talk to the one-hot model variants, which are
// separate from the ones behind /predict — the original page is untouched.
import type { FeatureSchema, PredictionInput } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** One question the user answered, and how much it moved the answer (log-odds). */
export type Factor = {
  feature: string;
  label: string;
  value: string;
  contribution: number;
  direction: "up" | "down";
  /** Where this feature ranks in the model's overall priorities. */
  global_rank: number | null;
};

export type RecourseOption = {
  feature: string;
  label: string;
  text: string;
  probability: number;
  delta: number;
};

export type Recourse = {
  available: boolean;
  direction?: "up" | "down";
  options: RecourseOption[];
  closest: RecourseOption | null;
};

export type FairnessProbe =
  | { available: false }
  | {
      available: true;
      original_sex: string;
      flipped_sex: string;
      relationship_also_flipped: boolean;
      baseline: { original: number; flipped: number; delta: number };
      baseline_with_proxy: { flipped: number; delta: number };
      served: { original: number; flipped: number; delta: number };
    };

export type Explanation = {
  served: {
    prediction: ">50K" | "<=50K";
    probability_above_50k: number;
    base_probability: number;
    summary: string;
    factors: Factor[];
    helped: Factor[];
    hurt: Factor[];
  };
  baseline: { prediction: ">50K" | "<=50K"; probability_above_50k: number };
  recourse: Recourse;
  fairness_probe: FairnessProbe;
};

export type GlobalFeature = {
  feature: string;
  label: string;
  importance: number;
  rank: number;
};

export type CategoryEffect = {
  feature: string;
  label: string;
  value: string;
  effect: number;
};

export type NumericEffect = { feature: string; label: string; effect: number };

export type GlobalModelView = {
  features: GlobalFeature[];
  top_category_effects: CategoryEffect[];
  numeric_effects: NumericEffect[];
  intercept: number;
};

export type GlobalExplanation = {
  feature_elimination: GlobalModelView;
  baseline: GlobalModelView;
  dropped_by_mitigation: string[];
  human_labels: Record<string, string>;
};

export type ExplainMetrics = {
  baseline: ExplainModelMetrics;
  feature_elimination: ExplainModelMetrics;
};

export type ExplainModelMetrics = {
  label: string;
  overall: { accuracy: number; precision: number; recall: number; f1: number };
  by_group: Record<string, { selection_rate: number; accuracy: number }>;
  dp_diff: number;
  dp_ratio: number;
  eo_diff: number;
};

export async function postExplain(input: PredictionInput): Promise<Explanation> {
  const res = await fetch(`${API_URL}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Explanation failed: ${res.status}`);
  }
  return res.json();
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const getExplainSchema = () => getJson<FeatureSchema>("/explain-schema");
export const getGlobalExplanation = () =>
  getJson<GlobalExplanation>("/global-explanation");
export const getExplainMetrics = () => getJson<ExplainMetrics>("/explain-metrics");
