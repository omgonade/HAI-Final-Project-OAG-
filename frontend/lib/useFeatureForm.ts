"use client";

import { useState } from "react";
import type { FeatureSchema, PredictionInput } from "@/lib/api";

// Input-handling logic for the census feature form, factored out so the
// Milestone 3 page can reuse it. The original PredictForm deliberately keeps
// its own copy: the Milestone 2 interface is a submitted artefact and should not
// change behaviour because a later page needed a refactor.

export const MONEY_COLUMNS = new Set(["capital-gain", "capital-loss"]);
export const USD_TO_INR = 96;
export type Currency = "USD" | "INR";

export function usdToDisplay(usd: number, currency: Currency): number {
  return currency === "USD" ? usd : Math.round(usd * USD_TO_INR);
}

export function displayToUsd(display: number, currency: Currency): number {
  return currency === "USD" ? display : Math.round(display / USD_TO_INR);
}

export function currencySymbol(currency: Currency): string {
  return currency === "USD" ? "$" : "₹";
}

function buildDefaults(schema: FeatureSchema): PredictionInput {
  const defaults: Record<string, string | number> = {};
  for (const col of schema.baseline.columns) {
    const numeric = schema.baseline.numeric[col];
    if (numeric) {
      defaults[col] = numeric.median;
    } else {
      // Prefer the most common value where the schema supplies one; the first
      // option alphabetically is an arbitrary and often absurd starting point.
      defaults[col] =
        schema.baseline.defaults?.[col] ?? schema.baseline.categorical[col][0];
    }
  }
  return defaults as unknown as PredictionInput;
}

/** Validates typed text as a whole number in [min, max]. Null means valid. */
function validateInteger(text: string, min: number, max: number): string | null {
  const trimmed = text.trim();
  if (trimmed === "") return "Required.";
  if (!/^\d+$/.test(trimmed))
    return `Enter a whole number, digits only (e.g. ${min.toLocaleString()}).`;
  const n = Number(trimmed);
  if (n < min || n > max)
    return `Must be between ${min.toLocaleString()} and ${max.toLocaleString()}.`;
  return null;
}

export type FeatureForm = ReturnType<typeof useFeatureForm>;

export function useFeatureForm(schema: FeatureSchema) {
  const [values, setValues] = useState<PredictionInput>(() => buildDefaults(schema));
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

  function updateField(col: string, value: string | number) {
    setValues((prev) => ({ ...prev, [col]: value }));
  }

  function handleNumericChange(col: string, rawText: string, min: number, max: number) {
    setNumericText((prev) => ({ ...prev, [col]: rawText }));
    const err = validateInteger(rawText, min, max);
    setNumericErrors((prev) => ({ ...prev, [col]: err }));
    if (!err) {
      const displayValue = Number(rawText.trim());
      const usdValue = MONEY_COLUMNS.has(col)
        ? displayToUsd(displayValue, currency)
        : displayValue;
      updateField(col, usdValue);
    }
  }

  function switchCurrency(next: Currency) {
    if (next === currency) return;
    setCurrency(next);
    // Re-render the money fields in the new currency from the last valid USD value.
    setNumericText((prev) => {
      const updated = { ...prev };
      for (const col of MONEY_COLUMNS) {
        updated[col] = String(usdToDisplay(values[col as keyof PredictionInput] as number, next));
      }
      return updated;
    });
    setNumericErrors((prev) => {
      const updated = { ...prev };
      for (const col of MONEY_COLUMNS) updated[col] = null;
      return updated;
    });
  }

  /** Load a complete person at once (the example buttons). */
  function applyPreset(preset: PredictionInput) {
    setValues(preset);
    setNumericText(() => {
      const text: Record<string, string> = {};
      for (const col of schema.baseline.columns) {
        if (!schema.baseline.numeric[col]) continue;
        const usdValue = preset[col as keyof PredictionInput] as number;
        text[col] = String(
          MONEY_COLUMNS.has(col) ? usdToDisplay(usdValue, currency) : usdValue
        );
      }
      return text;
    });
    setNumericErrors({});
  }

  const hasErrors = Object.values(numericErrors).some((e) => e);

  return {
    schema,
    values,
    currency,
    numericText,
    numericErrors,
    hasErrors,
    updateField,
    handleNumericChange,
    switchCurrency,
    applyPreset,
  };
}
