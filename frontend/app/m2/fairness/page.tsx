import { getMetrics, type ModelResult } from "@/lib/api";

const MODEL_ORDER: { key: keyof Awaited<ReturnType<typeof getMetrics>>; short: string }[] = [
  { key: "baseline", short: "Baseline" },
  { key: "feature_elimination", short: "Feature Elimination" },
  { key: "reweighting", short: "Reweighting" },
  { key: "threshold_optimization", short: "Threshold Optimization" },
];

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function dpRatioColor(ratio: number) {
  if (ratio >= 0.8) return "text-green-700 dark:text-green-400";
  if (ratio >= 0.6) return "text-amber-700 dark:text-amber-400";
  return "text-red-700 dark:text-red-400";
}

export default async function FairnessPage() {
  const metrics = await getMetrics();

  return (
    <div className="flex flex-col gap-10 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Fairness &amp; Performance Dashboard</h1>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1">
          Measured on a held-out test split by sex. &ldquo;Before&rdquo; is the
          unmitigated baseline; the served model is Feature Elimination.
        </p>
      </div>

      <section className="overflow-x-auto">
        <h2 className="text-lg font-medium mb-3">Overall performance vs. fairness</h2>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left border-b border-black/15 dark:border-white/20">
              <th className="py-2 pr-4">Model</th>
              <th className="py-2 pr-4">Accuracy</th>
              <th className="py-2 pr-4">F1</th>
              <th className="py-2 pr-4" title="Gap in selection rate between sex groups (0 = fair)">
                DP Diff
              </th>
              <th className="py-2 pr-4" title="Selection-rate ratio (1.0 = fair, <0.8 fails the 80% rule)">
                DP Ratio
              </th>
              <th className="py-2 pr-4" title="Gap in true-positive rate between sex groups (0 = fair)">
                EO Diff
              </th>
            </tr>
          </thead>
          <tbody>
            {MODEL_ORDER.map(({ key, short }) => {
              const r: ModelResult = metrics[key];
              return (
                <tr key={key} className="border-b border-black/5 dark:border-white/10">
                  <td className="py-2 pr-4 font-medium">{short}</td>
                  <td className="py-2 pr-4">{pct(r.overall.accuracy)}</td>
                  <td className="py-2 pr-4">{pct(r.overall.f1)}</td>
                  <td className="py-2 pr-4">{r.dp_diff.toFixed(3)}</td>
                  <td className={`py-2 pr-4 font-medium ${dpRatioColor(r.dp_ratio)}`}>
                    {r.dp_ratio.toFixed(3)}
                  </td>
                  <td className="py-2 pr-4">{r.eo_diff.toFixed(3)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="text-xs text-black/50 dark:text-white/50 mt-2">
          DP Ratio below 0.8 fails the legal &ldquo;80% rule&rdquo; for disparate
          impact — shown in red. 0.8 and above is shown in green.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-medium mb-3">
          Selection rate by sex — before vs. after mitigation
        </h2>
        <div className="flex flex-col gap-6">
          <GroupBars title="Baseline (before)" result={metrics.baseline} />
          <GroupBars title="Feature Elimination (after — served model)" result={metrics.feature_elimination} />
        </div>
        <p className="text-xs text-black/50 dark:text-white/50 mt-3">
          Selection rate = share of that group predicted &gt;$50K. A large gap between
          Female and Male bars is what Statistical Parity Difference measures.
        </p>
      </section>
    </div>
  );
}

function GroupBars({ title, result }: { title: string; result: ModelResult }) {
  const groups = Object.entries(result.by_group);
  const max = Math.max(...groups.map(([, g]) => g.selection_rate), 0.01);

  return (
    <div>
      <p className="text-sm font-medium mb-2">{title}</p>
      <div className="flex flex-col gap-2">
        {groups.map(([name, g]) => (
          <div key={name} className="flex items-center gap-3 text-sm">
            <span className="w-16 shrink-0">{name}</span>
            <div className="flex-1 bg-black/5 dark:bg-white/10 rounded h-4 overflow-hidden">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-full rounded"
                style={{ width: `${(g.selection_rate / max) * 100}%` }}
              />
            </div>
            <span className="w-14 shrink-0 text-right tabular-nums">
              {pct(g.selection_rate)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
