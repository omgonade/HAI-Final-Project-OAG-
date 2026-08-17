"use client";

import type { PredictionInput } from "@/lib/api";
import { FIELD_HELP, OPTION_HELP } from "@/lib/fieldHelp";
import OptionSelect from "@/components/OptionSelect";
import {
  MONEY_COLUMNS,
  USD_TO_INR,
  currencySymbol,
  usdToDisplay,
  type FeatureForm,
} from "@/lib/useFeatureForm";

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

export default function FeatureFields({ form }: { form: FeatureForm }) {
  const { schema, values, currency, numericText, numericErrors } = form;

  return (
    <>
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
                    onClick={() => form.switchCurrency("USD")}
                    className={`px-2 py-0.5 rounded ${currency === "USD" ? "bg-foreground text-background" : ""}`}
                  >
                    $ USD
                  </button>
                  <button
                    type="button"
                    onClick={() => form.switchCurrency("INR")}
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
                  onChange={(e) => form.handleNumericChange(col, e.target.value, min, max)}
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
                    {currency === "INR" &&
                      " (converted from USD, model trained on USD amounts)"}
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
                onChange={(e) =>
                  form.handleNumericChange(col, e.target.value, numeric.min, numeric.max)
                }
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

        return (
          <label key={col} className="flex flex-col gap-1 text-sm">
            <span className="font-medium flex items-center gap-1.5">
              {label}
              {FIELD_HELP[col] && <HelpIcon text={FIELD_HELP[col]} />}
            </span>
            <OptionSelect
              value={values[col as keyof PredictionInput] as string}
              options={schema.baseline.categorical[col]}
              optionHelp={OPTION_HELP[col]}
              onChange={(v) => form.updateField(col, v)}
            />
          </label>
        );
      })}
    </>
  );
}
