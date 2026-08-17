"use client";

import { useEffect, useRef, useState } from "react";
import type { FeatureSchema, PredictionInput } from "@/lib/api";
import { postExplain, type Explanation } from "@/lib/explainApi";
import { useFeatureForm } from "@/lib/useFeatureForm";
import FeatureFields from "@/components/FeatureFields";
import ExplanationCard from "@/components/ExplanationCard";

// Filling in thirteen fields before seeing anything is a poor first impression,
// so the page opens with ready-made people a visitor can explain in one click.
const PRESETS: { name: string; note: string; input: PredictionInput }[] = [
  {
    name: "Mid-career manager",
    note: "Predicted above $50K",
    input: {
      age: 42, workclass: "Private", education: "Bachelors", "education-num": 13,
      "marital-status": "Married-civ-spouse", occupation: "Exec-managerial",
      relationship: "Husband", race: "White", sex: "Male", "capital-gain": 0,
      "capital-loss": 0, "hours-per-week": 50, "native-country": "United-States",
    },
  },
  {
    name: "Part-time clerk",
    note: "Predicted at or below $50K",
    input: {
      age: 27, workclass: "Private", education: "HS-grad", "education-num": 9,
      "marital-status": "Never-married", occupation: "Adm-clerical",
      relationship: "Not-in-family", race: "White", sex: "Female", "capital-gain": 0,
      "capital-loss": 0, "hours-per-week": 30, "native-country": "United-States",
    },
  },
  {
    name: "Where the two models disagree",
    note: "Mitigation changes the answer",
    input: {
      age: 29, workclass: "Private", education: "Bachelors", "education-num": 13,
      "marital-status": "Married-civ-spouse", occupation: "Exec-managerial",
      relationship: "Husband", race: "White", sex: "Male", "capital-gain": 0,
      "capital-loss": 0, "hours-per-week": 45, "native-country": "United-States",
    },
  },
];

export default function ExplainForm({ schema }: { schema: FeatureSchema }) {
  const form = useFeatureForm(schema);
  const [result, setResult] = useState<Explanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [flashKey, setFlashKey] = useState(0);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!result) return;
    const el = resultRef.current;
    if (el) {
      const rect = el.getBoundingClientRect();
      if (rect.top < 0 || rect.top > window.innerHeight * 0.5) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    // Remount the wrapper so the flash animation replays on back-to-back runs.
    setFlashKey((k) => k + 1);
  }, [result]);

  async function submit(input: PredictionInput) {
    setLoading(true);
    setError(null);
    try {
      setResult(await postExplain(input));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.hasErrors) {
      setError("Fix the highlighted fields before continuing.");
      return;
    }
    submit(form.values);
  }

  function handlePreset(input: PredictionInput) {
    form.applyPreset(input);
    submit(input);
  }

  return (
    <div className="flex flex-col gap-8">
      <section>
        <p className="text-sm font-medium">Try an example</p>
        <div className="flex flex-wrap gap-2 mt-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              type="button"
              onClick={() => handlePreset(preset.input)}
              disabled={loading}
              className="text-left border rounded-lg px-3 py-2 border-black/15 dark:border-white/20 hover:border-black/40 dark:hover:border-white/50 transition-colors disabled:opacity-50"
            >
              <span className="block text-sm font-medium">{preset.name}</span>
              <span className="block text-xs text-black/50 dark:text-white/50">
                {preset.note}
              </span>
            </button>
          ))}
        </div>
      </section>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] items-start">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <p className="text-sm font-medium">…or describe someone yourself</p>
          <FeatureFields form={form} />
          <button
            type="submit"
            disabled={loading || form.hasErrors}
            className="mt-2 rounded-full bg-foreground text-background px-5 py-2.5 font-medium disabled:opacity-50"
          >
            {loading ? "Working…" : "Predict and explain"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>

        <div ref={resultRef}>
          {result ? (
            <div key={flashKey} className="result-flash">
              <ExplanationCard explanation={result} />
            </div>
          ) : (
            <div className="text-sm text-black/60 dark:text-white/60 border border-dashed rounded-xl p-8 border-black/15 dark:border-white/20">
              Pick an example above or fill in the form. You&rsquo;ll get the
              prediction, the reasons behind it in plain language, what would have to
              change to flip it, and a test of whether sex affected the answer.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
