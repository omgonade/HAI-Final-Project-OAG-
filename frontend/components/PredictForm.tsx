"use client";

import { useEffect, useRef, useState } from "react";
import {
  type FeatureSchema,
  type PredictionInput,
  type PredictionResponse,
  postPredict,
} from "@/lib/api";
import { FIELD_HELP, OPTION_HELP } from "@/lib/fieldHelp";
import OptionSelect from "@/components/OptionSelect";

const LABELS: Record<string, string> = {
  age: "Age",
  workclass: "Work class",
  education: "Education",
  "education-num": "Years of education",
  "marital-status": "Marital status",
  occupation: "Occupation",
  relationship: "Relationship",
  race: "Race",
  sex: "Sex",
  "capital-gain": "Capital gain",
  "capital-loss": "Capital loss",
  "hours-per-week": "Hours per week",
  "native-country": "Native country",
};

function HelpIcon({ text }: { text: string }) {
  return (
    <span
      title={text}
      className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] leading-none border border-black/30 dark:border-white/40 text-black/60 dark:text-white/60 cursor-help select-none"
      aria-label={text}
    >
      ?
    </span>
  );
}

const MONEY_COLUMNS = new Set(["capital-gain", "capital-loss"]);
const USD_TO_INR = 96;
type Currency = "USD" | "INR";

function usdToDisplay(usd: number, currency: Currency): number {
  return currency === "USD" ? usd : Math.round(usd * USD_TO_INR);
}

function displayToUsd(display: number, currency: Currency): number {
  return currency === "USD" ? display : Math.round(display / USD_TO_INR);
}

function currencySymbol(currency: Currency): string {
  return currency === "USD" ? "$" : "₹";
}

function buildDefaults(schema: FeatureSchema): PredictionInput {
  const defaults: Record<string, string | number> = {};
  for (const col of schema.baseline.columns) {
    const numeric = schema.baseline.numeric[col];
    if (numeric) {
      defaults[col] = numeric.median;
    } else {
      defaults[col] = schema.baseline.categorical[col][0];
    }
  }
  return defaults as unknown as PredictionInput;
}

// Validates typed text as a whole number in [min, max]. Returns an error
// message, or null if the text is a valid number in range.
function validateInteger(text: string, min: number, max: number): string | null {
  const trimmed = text.trim();
  if (trimmed === "") return "Required.";
  if (!/^\d+$/.test(trimmed)) return `Enter a whole number, digits only (e.g. ${min.toLocaleString()}).`;
  const n = Number(trimmed);
  if (n < min || n > max) return `Must be between ${min.toLocaleString()} and ${max.toLocaleString()}.`;
  return null;
}

export default function PredictForm({ schema }: { schema: FeatureSchema }) {
  const [values, setValues] = useState<PredictionInput>(() => buildDefaults(schema));
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [currency, setCurrency] = useState<Currency>("USD");

  const [numericText, setNumericText] = useState<Record<string, string>>(() => {
    const text: Record<string, string> = {};
    for (const col of schema.baseline.columns) {
      const numeric = schema.baseline.numeric[col];
      if (numeric) text[col] = String(numeric.median);
    }
    return text;
  });
  const [numericErrors, setNumericErrors] = useState<Record<string, string | null>>({});
  const [justPredicted, setJustPredicted] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!result) return;
    resultRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setJustPredicted(true);
    const timer = setTimeout(() => setJustPredicted(false), 1600);
    return () => clearTimeout(timer);
  }, [result]);

  function updateField(col: string, value: string | number) {
    setValues((prev) => ({ ...prev, [col]: value }));
  }

  function handleNumericChange(col: string, rawText: string, min: number, max: number) {
    setNumericText((prev) => ({ ...prev, [col]: rawText }));
    const err = validateInteger(rawText, min, max);
    setNumericErrors((prev) => ({ ...prev, [col]: err }));
    if (!err) {
      const displayValue = Number(rawText.trim());
      const usdValue = MONEY_COLUMNS.has(col) ? displayToUsd(displayValue, currency) : displayValue;
      updateField(col, usdValue);
    }
  }

  function switchCurrency(next: Currency) {
    if (next === currency) return;
    setCurrency(next);
    // Re-render the money fields' text in the new currency, from the last valid USD value.
    setNumericText((prev) => {
      const updated = { ...prev };
      for (const col of MONEY_COLUMNS) {
        const usdValue = values[col as keyof PredictionInput] as number;
        updated[col] = String(usdToDisplay(usdValue, next));
      }
      return updated;
    });
    setNumericErrors((prev) => {
      const updated = { ...prev };
      for (const col of MONEY_COLUMNS) updated[col] = null;
      return updated;
    });
  }

  const hasErrors = Object.values(numericErrors).some((e) => e);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (hasErrors) {
      setError("Fix the highlighted fields before predicting.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const prediction = await postPredict(values);
      setResult(prediction);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {schema.baseline.columns.map((col) => {
          const numeric = schema.baseline.numeric[col];
          const label = LABELS[col] ?? col;
          const fieldError = numericErrors[col];

          if (numeric && MONEY_COLUMNS.has(col)) {
            const min = usdToDisplay(numeric.min, currency);
            const max = usdToDisplay(numeric.max, currency);
            return (
              <div key={col} className="flex flex-col gap-1 text-sm">
                {col === "capital-gain" && (
                  <div className="flex items-center gap-2 text-xs mb-1 bg-black/5 dark:bg-white/10 rounded px-2 py-1.5 w-fit">
                    <span className="font-medium">Currency:</span>
                    <button
                      type="button"
                      onClick={() => switchCurrency("USD")}
                      className={`px-2 py-0.5 rounded ${currency === "USD" ? "bg-foreground text-background" : ""}`}
                    >
                      $ USD
                    </button>
                    <button
                      type="button"
                      onClick={() => switchCurrency("INR")}
                      className={`px-2 py-0.5 rounded ${currency === "INR" ? "bg-foreground text-background" : ""}`}
                    >
                      ₹ INR
                    </button>
                    <span className="text-black/50 dark:text-white/50">
                      Rate used: $1 = ₹{USD_TO_INR}
                    </span>
                  </div>
                )}
                <label className="flex flex-col gap-1">
                  <span className="font-medium flex items-center gap-1.5">
                    {label} ({currencySymbol(currency)})
                    {FIELD_HELP[col] && <HelpIcon text={FIELD_HELP[col]} />}
                  </span>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={numericText[col] ?? ""}
                    onChange={(e) => handleNumericChange(col, e.target.value, min, max)}
                    className={`border rounded px-2 py-1.5 bg-transparent ${
                      fieldError ? "border-red-500" : "border-black/15 dark:border-white/20"
                    }`}
                  />
                  {fieldError ? (
                    <span className="text-xs text-red-600">{fieldError}</span>
                  ) : (
                    <span className="text-xs text-black/50 dark:text-white/50">
                      Range in training data: {currencySymbol(currency)}
                      {min.toLocaleString()}–{currencySymbol(currency)}
                      {max.toLocaleString()}
                      {currency === "INR" && " (converted from USD, model trained on USD amounts)"}
                    </span>
                  )}
                </label>
              </div>
            );
          }

          if (numeric) {
            return (
              <label key={col} className="flex flex-col gap-1 text-sm">
                <span className="font-medium flex items-center gap-1.5">
                  {label}
                  {FIELD_HELP[col] && <HelpIcon text={FIELD_HELP[col]} />}
                </span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={numericText[col] ?? ""}
                  onChange={(e) => handleNumericChange(col, e.target.value, numeric.min, numeric.max)}
                  className={`border rounded px-2 py-1.5 bg-transparent ${
                    fieldError ? "border-red-500" : "border-black/15 dark:border-white/20"
                  }`}
                />
                {fieldError ? (
                  <span className="text-xs text-red-600">{fieldError}</span>
                ) : (
                  <span className="text-xs text-black/50 dark:text-white/50">
                    Range in training data: {numeric.min}–{numeric.max}
                  </span>
                )}
              </label>
            );
          }
          const options = schema.baseline.categorical[col];
          return (
            <label key={col} className="flex flex-col gap-1 text-sm">
              <span className="font-medium flex items-center gap-1.5">
                {label}
                {FIELD_HELP[col] && <HelpIcon text={FIELD_HELP[col]} />}
              </span>
              <OptionSelect
                value={values[col as keyof PredictionInput] as string}
                options={options}
                optionHelp={OPTION_HELP[col]}
                onChange={(v) => updateField(col, v)}
              />
            </label>
          );
        })}

        <button
          type="submit"
          disabled={loading || hasErrors}
          className="mt-2 rounded-full bg-foreground text-background px-5 py-2.5 font-medium disabled:opacity-50"
        >
          {loading ? "Predicting…" : "Predict income bracket"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      <div
        ref={resultRef}
        className={`rounded-lg transition-shadow duration-700 ${
          justPredicted ? "ring-2 ring-blue-500 ring-offset-2 ring-offset-background" : ""
        }`}
      >
        {result ? (
          <ResultCard result={result} />
        ) : (
          <div className="text-sm text-black/60 dark:text-white/60 border border-dashed rounded-lg p-6 border-black/15 dark:border-white/20">
            Fill in the form and submit to see a prediction. This model estimates a
            likelihood, not a certainty — see the Model Card for what it can and
            cannot tell you.
          </div>
        )}
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: PredictionResponse }) {
  const fe = result.feature_elimination;
  const base = result.baseline;
  const feChanged = fe.prediction !== base.prediction;

  return (
    <div className="border rounded-lg p-6 border-black/15 dark:border-white/20 flex flex-col gap-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          Predicted income bracket (mitigated model)
        </p>
        <p className="text-3xl font-semibold mt-1">{fe.prediction}</p>
        <p className="text-sm mt-1 text-black/60 dark:text-white/60">
          Estimated probability of &gt;$50K:{" "}
          <span className="font-medium">
            {(fe.probability_above_50k * 100).toFixed(1)}%
          </span>
        </p>
      </div>

      <div className="border-t pt-4 border-black/10 dark:border-white/15">
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          What the unmitigated baseline model would have said
        </p>
        <p className="text-lg font-medium mt-1">
          {base.prediction}{" "}
          <span className="text-sm font-normal text-black/60 dark:text-white/60">
            ({(base.probability_above_50k * 100).toFixed(1)}% probability)
          </span>
        </p>
        <p className="text-xs mt-2 text-black/60 dark:text-white/60">
          {feChanged
            ? "The mitigation changed the predicted bracket for this input — a concrete sign of how much sex/relationship/marital-status were driving the unmitigated model's decision."
            : "Both models agree on the bracket for this input, though their confidence may differ. Agreement on one case does not mean the models are equally fair overall — see the Fairness Dashboard."}
        </p>
      </div>

      <p className="text-xs text-black/50 dark:text-white/50">
        This is a likelihood estimate from a model trained on 1994 census data, not a
        real assessment of this person&rsquo;s income or worth.
      </p>
    </div>
  );
}
