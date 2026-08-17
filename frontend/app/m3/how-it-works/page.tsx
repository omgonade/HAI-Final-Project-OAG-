import Link from "next/link";
import {
  getExplainMetrics,
  getGlobalExplanation,
  type CategoryEffect,
  type GlobalFeature,
  type GlobalModelView,
  type NumericEffect,
} from "@/lib/explainApi";

export const metadata = {
  title: "How this model works",
};

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default async function HowItWorksPage() {
  const [global, metrics] = await Promise.all([
    getGlobalExplanation(),
    getExplainMetrics(),
  ]);
  const dropped = new Set(global.dropped_by_mitigation);

  return (
    <div className="flex flex-col gap-12 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">How this model works in general</h1>
        <p className="text-sm text-black/60 dark:text-white/60 mt-2">
          This page is the model&rsquo;s overall behaviour, across everyone. If you
          want to know about one specific person instead, that lives on{" "}
          <Link href="/m3" className="underline">
            Why this answer
          </Link>{" "}
          — and the key parts of this page are repeated there, inline, so you never
          have to come here to understand your own result.
        </p>
      </div>

      <section>
        <h2 className="text-lg font-medium">It is a scorecard</h2>
        <div className="text-sm text-black/70 dark:text-white/70 mt-2 flex flex-col gap-3">
          <p>
            The model is a logistic regression. Every answer you give adds or
            subtracts points from a running total, and that total is turned into a
            probability. Nothing else happens — there are no hidden layers or
            interactions.
          </p>
          <p>
            That matters for honesty: because the model is a plain sum, the
            explanations on this site are <strong>exact</strong>, not estimates. Each
            number is literally the amount that answer contributed to the total. (For
            a linear model, this decomposition is the same thing SHAP computes.)
          </p>
          <p>
            The points are measured in <em>log-odds</em>. You do not need the unit —
            only that bigger means more influence, positive pushes toward
            &gt;$50K, and negative pushes toward ≤$50K.
          </p>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-medium">What the model pays attention to</h2>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1">
          Each feature&rsquo;s average influence on a prediction, measured across the
          held-out test set. This is the same quantity shown per-person on the
          explanation page, averaged — so the two views cannot tell different stories.
        </p>

        <div className="grid gap-8 sm:grid-cols-2 mt-5">
          <ImportanceList
            title="The model you are served"
            subtitle="Sex, relationship and marital status removed"
            view={global.feature_elimination}
            dropped={dropped}
          />
          <ImportanceList
            title="The unmitigated baseline"
            subtitle="All features, no mitigation"
            view={global.baseline}
            dropped={dropped}
          />
        </div>

        <p className="text-xs text-black/55 dark:text-white/55 mt-4">
          The three highlighted rows on the right are what mitigation removed. In the
          baseline, marital status and relationship are among the most influential
          features in the whole model — and both correlate strongly with sex, which is
          why removing sex alone would not have been enough.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-medium">Which specific answers move the needle</h2>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1">
          Individual categories in the served model, strongest first. This is only
          possible because the model gives every category its own weight.
        </p>
        <CategoryEffects effects={global.feature_elimination.top_category_effects} />
      </section>

      <section>
        <h2 className="text-lg font-medium">How the numeric answers are used</h2>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1">
          Effect of a one-standard-deviation increase in each numeric input, holding
          everything else fixed.
        </p>
        <NumericEffects effects={global.feature_elimination.numeric_effects} />
      </section>

      <section>
        <h2 className="text-lg font-medium">Accuracy and fairness of these models</h2>
        <div className="overflow-x-auto mt-3">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b border-black/15 dark:border-white/20">
                <th className="py-2 pr-4">Model</th>
                <th className="py-2 pr-4">Accuracy</th>
                <th className="py-2 pr-4">F1</th>
                <th className="py-2 pr-4" title="Selection-rate gap between sex groups (0 = fair)">
                  DP Diff
                </th>
                <th className="py-2 pr-4" title="True-positive-rate gap between sex groups (0 = fair)">
                  EO Diff
                </th>
              </tr>
            </thead>
            <tbody>
              {(["baseline", "feature_elimination"] as const).map((key) => {
                const m = metrics[key];
                return (
                  <tr key={key} className="border-b border-black/5 dark:border-white/10">
                    <td className="py-2 pr-4 font-medium">
                      {key === "baseline" ? "Baseline" : "Feature Elimination (served)"}
                    </td>
                    <td className="py-2 pr-4">{pct(m.overall.accuracy)}</td>
                    <td className="py-2 pr-4">{pct(m.overall.f1)}</td>
                    <td className="py-2 pr-4">{m.dp_diff.toFixed(3)}</td>
                    <td className="py-2 pr-4">{m.eo_diff.toFixed(3)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-black/55 dark:text-white/55 mt-3">
          These numbers differ slightly from the{" "}
          <Link href="/m3/fairness" className="underline">
            Fairness Dashboard
          </Link>
          . That dashboard reports the earlier models, where categories were
          encoded as single numbers. For Milestone 3 the categories were one-hot
          encoded so that each one gets its own weight — without that, no per-answer
          explanation is possible. Retraining shifts the metrics a little; the
          direction of the fairness result is unchanged, and mitigation still narrows
          both gaps.
        </p>
      </section>
    </div>
  );
}

function ImportanceList({
  title,
  subtitle,
  view,
  dropped,
}: {
  title: string;
  subtitle: string;
  view: GlobalModelView;
  dropped: Set<string>;
}) {
  const max = Math.max(...view.features.map((f) => f.importance), 0.0001);

  return (
    <div>
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs text-black/50 dark:text-white/50">{subtitle}</p>
      <ul className="mt-3 flex flex-col gap-2">
        {view.features.map((feature: GlobalFeature) => {
          const isDropped = dropped.has(feature.feature);
          return (
            <li key={feature.feature} className="text-xs">
              <div className="flex justify-between gap-2">
                <span className={isDropped ? "font-medium text-amber-700 dark:text-amber-400" : ""}>
                  {feature.label}
                  {isDropped && " — removed by mitigation"}
                </span>
                <span className="tabular-nums text-black/40 dark:text-white/40 shrink-0">
                  {feature.importance.toFixed(3)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-black/5 dark:bg-white/10 mt-1 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    isDropped
                      ? "bg-amber-500"
                      : "bg-blue-600 dark:bg-blue-500"
                  }`}
                  style={{ width: `${(feature.importance / max) * 100}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function CategoryEffects({ effects }: { effects: CategoryEffect[] }) {
  const max = Math.max(...effects.map((e) => Math.abs(e.effect)), 0.0001);

  return (
    <ul className="mt-4 flex flex-col gap-2">
      {effects.map((effect) => {
        const up = effect.effect >= 0;
        return (
          <li key={`${effect.feature}=${effect.value}`} className="text-sm">
            <div className="flex justify-between gap-3">
              <span>
                <span className="text-black/55 dark:text-white/55">{effect.label}:</span>{" "}
                <span className="font-medium">{effect.value}</span>
              </span>
              <span
                className={`text-xs tabular-nums shrink-0 ${
                  up
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-rose-700 dark:text-rose-400"
                }`}
              >
                {up ? "+" : ""}
                {effect.effect.toFixed(2)}
              </span>
            </div>
            {/* Centre line so direction is visible at a glance, not only by colour. */}
            <div className="relative h-1.5 mt-1 bg-black/5 dark:bg-white/10 rounded-full">
              <div className="absolute inset-y-0 left-1/2 w-px bg-black/25 dark:bg-white/30" />
              <div
                className={`absolute inset-y-0 rounded-full ${
                  up ? "bg-emerald-600 dark:bg-emerald-500" : "bg-rose-600 dark:bg-rose-500"
                }`}
                style={
                  up
                    ? { left: "50%", width: `${(effect.effect / max) * 50}%` }
                    : { right: "50%", width: `${(Math.abs(effect.effect) / max) * 50}%` }
                }
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function NumericEffects({ effects }: { effects: NumericEffect[] }) {
  const max = Math.max(...effects.map((e) => Math.abs(e.effect)), 0.0001);

  return (
    <ul className="mt-4 flex flex-col gap-3">
      {effects.map((effect) => {
        const up = effect.effect >= 0;
        return (
          <li key={effect.feature} className="text-sm">
            <div className="flex justify-between gap-3">
              <span>{effect.label}</span>
              <span
                className={`text-xs tabular-nums ${
                  up
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-rose-700 dark:text-rose-400"
                }`}
              >
                {up ? "+" : ""}
                {effect.effect.toFixed(2)} per standard deviation
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-black/5 dark:bg-white/10 mt-1 overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  up ? "bg-emerald-600 dark:bg-emerald-500" : "bg-rose-600 dark:bg-rose-500"
                }`}
                style={{ width: `${(Math.abs(effect.effect) / max) * 100}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
