import { getExplainSchema } from "@/lib/explainApi";
import ExplainForm from "@/components/ExplainForm";

export const metadata = {
  title: "Why this answer? — Milestone 3",
};

const CAPABILITIES = [
  "Why this result, in plain language",
  "What helped and what hurt, ranked",
  "What would change the answer",
  "Whether sex affected it",
];

export default async function ExplainPage() {
  const schema = await getExplainSchema();

  return (
    <div className="flex flex-col gap-8">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight">Why this answer?</h1>
        <p className="text-black/60 dark:text-white/60 mt-2">
          Pick an example or describe someone, and the model will show its reasoning
          — not just its verdict.
        </p>

        <ul className="flex flex-wrap gap-2 mt-4">
          {CAPABILITIES.map((capability) => (
            <li
              key={capability}
              className="text-xs rounded-full border border-black/15 dark:border-white/20 px-3 py-1 text-black/70 dark:text-white/70"
            >
              {capability}
            </li>
          ))}
        </ul>
      </div>

      <ExplainForm schema={schema} />
    </div>
  );
}
