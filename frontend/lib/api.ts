const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type NumericRange = { min: number; max: number; median: number };

export type FeatureSchema = {
  baseline: {
    columns: string[];
    categorical: Record<string, string[]>;
    numeric: Record<string, NumericRange>;
    /** Most common value per categorical field. Only the Milestone 3 schema
     *  supplies this; Milestone 2's falls back to the first option. */
    defaults?: Record<string, string>;
  };
  feature_elimination: {
    columns: string[];
    categorical: Record<string, string[]>;
  };
};

export type ModelCard = {
  task: string;
  served_model: string;
  training_data: string;
  scope: string[];
  known_bias_sources: string[];
};

export type ModelResult = {
  label: string;
  overall: { accuracy: number; precision: number; recall: number; f1: number };
  by_group: Record<
    string,
    { accuracy: number; precision: number; recall: number; f1: number; selection_rate: number }
  >;
  dp_diff: number;
  dp_ratio: number;
  eo_diff: number;
};

export type Metrics = {
  baseline: ModelResult;
  feature_elimination: ModelResult;
  reweighting: ModelResult;
  threshold_optimization: ModelResult;
};

export type PredictionInput = {
  age: number;
  workclass: string;
  education: string;
  "education-num": number;
  "marital-status": string;
  occupation: string;
  relationship: string;
  race: string;
  sex: string;
  "capital-gain": number;
  "capital-loss": number;
  "hours-per-week": number;
  "native-country": string;
};

export type PredictionOutcome = { prediction: ">50K" | "<=50K"; probability_above_50k: number };

export type PredictionResponse = {
  feature_elimination: PredictionOutcome;
  baseline: PredictionOutcome;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const getFeatureSchema = () => getJson<FeatureSchema>("/feature-schema");
export const getModelCard = () => getJson<ModelCard>("/metadata");
export const getMetrics = () => getJson<Metrics>("/metrics");

export async function postPredict(input: PredictionInput): Promise<PredictionResponse> {
  const res = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Prediction failed: ${res.status}`);
  }
  return res.json();
}
