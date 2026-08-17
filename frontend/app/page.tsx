import Link from "next/link";

// Landing page: one decision, nothing else. The milestone number is the thing
// being chosen, so it is the largest element on the card — everything that is
// not needed to make the choice lives on the pages themselves.

const MILESTONES = [
  {
    href: "/m2",
    number: "2",
    title: "Prediction interface",
    line: "Get an income-bracket prediction, with the unmitigated model's answer alongside it.",
    points: ["Prediction with confidence", "Model card", "Fairness dashboard"],
    latest: false,
  },
  {
    href: "/m3",
    number: "3",
    title: "Explainable interface",
    line: "The same prediction, plus the reasoning behind it — for the specific person you describe.",
    points: [
      "Why this result, in plain language",
      "What would change the answer",
      "Fairness test on your own case",
    ],
    latest: true,
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">
          Adult Census Income Predictor
        </h1>
        <p className="text-black/60 dark:text-white/60 mt-2">
          Two versions of the same fairness-aware model. Which one do you want to see?
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {MILESTONES.map((milestone) => (
          <Link
            key={milestone.href}
            href={milestone.href}
            className="group flex flex-col rounded-2xl border-2 border-black/15 dark:border-white/20 p-7 hover:border-blue-600 dark:hover:border-blue-500 hover:shadow-lg transition-all"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-2xl font-bold tracking-tight">
                Milestone {milestone.number}
              </span>
              {milestone.latest && (
                <span className="text-[10px] font-semibold uppercase tracking-wide rounded-full px-2.5 py-1 bg-blue-600 text-white shrink-0">
                  Latest
                </span>
              )}
            </div>

            <p className="text-base font-medium text-black/75 dark:text-white/75 mt-0.5">
              {milestone.title}
            </p>

            <p className="text-sm text-black/60 dark:text-white/60 mt-3 leading-relaxed">
              {milestone.line}
            </p>

            <ul className="mt-4 flex flex-col gap-1.5 text-sm">
              {milestone.points.map((point) => (
                <li key={point} className="flex gap-2">
                  <span className="text-blue-600 dark:text-blue-400 shrink-0">→</span>
                  <span className="text-black/70 dark:text-white/70">{point}</span>
                </li>
              ))}
            </ul>

            <span className="mt-6 text-sm font-semibold inline-flex items-center gap-1.5 text-blue-700 dark:text-blue-400 group-hover:gap-2.5 transition-all">
              Open Milestone {milestone.number}
              <span aria-hidden>→</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
