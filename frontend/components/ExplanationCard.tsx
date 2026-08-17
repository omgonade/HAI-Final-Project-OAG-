"use client";

import type { Explanation, Factor, FairnessProbe, Recourse } from "@/lib/explainApi";
import Link from "next/link";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

/** Log-odds are meaningless to a non-technical reader, so each factor also gets
 *  a plain word for its size. The exact number stays visible for graders. */
function strengthWord(magnitude: number, largest: number): string {
  const share = largest === 0 ? 0 : magnitude / largest;
  if (share >= 0.66) return "strong";
  if (share >= 0.3) return "moderate";
  return "slight";
}

export default function ExplanationCard({ explanation }: { explanation: Explanation }) {
  const { served, baseline, recourse, fairness_probe } = explanation;
  const high = served.prediction === ">50K";
  const disagrees = baseline.prediction !== served.prediction;
  const largestContribution = Math.max(
    ...served.factors.map((f) => Math.abs(f.contribution)),
    0.0001
  );

  return (
    <div className="flex flex-col gap-4">
      {/* 1. The answer, in a sentence. Tinted by outcome so the verdict reads
          before any of the words do. */}
      <section
        className={`border rounded-2xl p-6 sm:p-7 ${
          high
            ? "border-emerald-600/30 bg-emerald-50/60 dark:bg-emerald-950/25"
            : "border-black/15 dark:border-white/20 bg-black/[0.02] dark:bg-white/[0.03]"
        }`}
      >
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          The model&rsquo;s answer
        </p>
        <p className="text-2xl sm:text-3xl font-semibold mt-2 leading-snug tracking-tight">
          Likely earns{" "}
          <span className={high ? "text-emerald-700 dark:text-emerald-400" : ""}>
            {high ? "more than $50K" : "$50K or less"}
          </span>
        </p>
        <p className="text-sm text-black/55 dark:text-white/55 mt-1">
          {pct(served.probability_above_50k)} confidence
        </p>

        <ConfidenceBar probability={served.probability_above_50k} />

        {/* 2. The plain-language reason — where most readers stop. */}
        <p className="mt-6 text-[15px] sm:text-base leading-relaxed">
          {served.summary}
        </p>

        <p className="mt-3 text-xs text-black/50 dark:text-white/50">
          Starting point before anything about you was considered:{" "}
          {pct(served.base_probability)}. Your answers moved it to{" "}
          {pct(served.probability_above_50k)}.
        </p>
      </section>

      {/* 3. What helped / what hurt. */}
      <Panel
        step={1}
        title="What moved the answer"
        note="Every answer you gave, sorted by how much it mattered for you specifically."
      >
        <div className="grid gap-6 sm:grid-cols-2 mt-4">
          {/* Both columns share one scale. Normalising each column against its
              own maximum would draw a -0.40 factor the same length as a +0.71
              one, which is exactly the comparison this panel exists to make. */}
          <FactorColumn
            title="Pushed toward >$50K"
            tone="up"
            factors={served.helped}
            scale={largestContribution}
          />
          <FactorColumn
            title="Pushed toward ≤$50K"
            tone="down"
            factors={served.hurt}
            scale={largestContribution}
          />
        </div>
      </Panel>

      {/* 4. The forward-looking part. */}
      <RecourseSection recourse={recourse} high={high} />

      {/* 5. Fairness, collapsed by default. */}
      <ProbeSection probe={fairness_probe} disagrees={disagrees} baseline={baseline} />

      <p className="text-xs text-black/50 dark:text-white/50">
        This is a likelihood estimate from a model trained on 1994 census data, not
        a real assessment of anyone&rsquo;s income or worth.{" "}
        <Link href="/m3/how-it-works" className="underline">
          How this model behaves in general
        </Link>
        .
      </p>
    </div>
  );
}

/** Numbered section shell, so the card reads as an ordered explanation rather
 *  than a stack of unrelated boxes. */
function Panel({
  step,
  title,
  note,
  accent,
  children,
}: {
  step: number;
  title: string;
  note: string;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`border rounded-2xl p-6 sm:p-7 ${
        accent
          ? "border-blue-600/30 bg-blue-50/50 dark:bg-blue-950/20"
          : "border-black/15 dark:border-white/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`shrink-0 mt-0.5 w-6 h-6 rounded-full grid place-items-center text-xs font-semibold ${
            accent
              ? "bg-blue-600 text-white"
              : "bg-black/10 dark:bg-white/15 text-black/70 dark:text-white/70"
          }`}
          aria-hidden
        >
          {step}
        </span>
        <div>
          <h3 className="font-medium">{title}</h3>
          <p className="text-xs text-black/55 dark:text-white/55 mt-1">{note}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function ConfidenceBar({ probability }: { probability: number }) {
  return (
    <div className="mt-4">
      <div className="relative h-3 rounded-full bg-black/10 dark:bg-white/15 overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-blue-600 dark:bg-blue-500"
          style={{ width: `${probability * 100}%` }}
        />
        {/* The 50% decision threshold — being near it is itself information. */}
        <div className="absolute inset-y-0 left-1/2 w-px bg-black/50 dark:bg-white/60" />
      </div>
      <div className="flex justify-between text-[11px] text-black/45 dark:text-white/45 mt-1">
        <span>0%</span>
        <span>50% — the cut-off</span>
        <span>100%</span>
      </div>
    </div>
  );
}

function FactorColumn({
  title,
  tone,
  factors,
  scale,
}: {
  title: string;
  tone: "up" | "down";
  factors: Factor[];
  /** Shared across both columns so bar lengths are comparable. */
  scale: number;
}) {
  const up = tone === "up";
  const largest = scale;
  const shown = factors.slice(0, 5);
  const rest = factors.slice(5);

  return (
    <div>
      <p
        className={`text-sm font-medium ${
          up
            ? "text-emerald-700 dark:text-emerald-400"
            : "text-rose-700 dark:text-rose-400"
        }`}
      >
        {up ? "▲" : "▼"} {title}
      </p>

      {shown.length === 0 ? (
        <p className="text-xs text-black/50 dark:text-white/50 mt-2">
          Nothing pushed this way.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {shown.map((factor) => (
            <li key={factor.feature}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span>
                  <span className="text-black/55 dark:text-white/55">
                    {factor.label}:
                  </span>{" "}
                  <span className="font-medium">{factor.value}</span>
                </span>
                <span className="text-[11px] tabular-nums text-black/40 dark:text-white/40 shrink-0">
                  {factor.contribution > 0 ? "+" : ""}
                  {factor.contribution.toFixed(2)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-black/5 dark:bg-white/10 mt-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    up ? "bg-emerald-600 dark:bg-emerald-500" : "bg-rose-600 dark:bg-rose-500"
                  }`}
                  style={{
                    width: `${(Math.abs(factor.contribution) / largest) * 100}%`,
                  }}
                />
              </div>
              {/* The global view, delivered inline — so the reader gets the
                  context without going off to study a separate chart. */}
              <p className="text-[11px] text-black/45 dark:text-white/45 mt-1">
                A {strengthWord(Math.abs(factor.contribution), largest)} effect for you
                {factor.global_rank
                  ? factor.global_rank === 1
                    ? "; this is the model's single biggest factor overall."
                    : `; it is the model's #${factor.global_rank} factor overall.`
                  : "."}
              </p>
            </li>
          ))}
        </ul>
      )}

      {rest.length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-black/55 dark:text-white/55 cursor-pointer hover:underline">
            {rest.length} smaller factor{rest.length === 1 ? "" : "s"}
          </summary>
          <ul className="mt-2 flex flex-col gap-1 text-xs text-black/60 dark:text-white/60">
            {rest.map((factor) => (
              <li key={factor.feature} className="flex justify-between gap-2">
                <span>
                  {factor.label}: <span className="font-medium">{factor.value}</span>
                </span>
                <span className="tabular-nums text-black/40 dark:text-white/40">
                  {factor.contribution > 0 ? "+" : ""}
                  {factor.contribution.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function RecourseSection({ recourse, high }: { recourse: Recourse; high: boolean }) {
  // Framing depends on which way the flip goes. Telling someone predicted below
  // $50K what would lift them above it is genuinely useful advice. Telling
  // someone already above it to get less education is not advice at all — for
  // them the same computation answers a different question: how safe is this
  // result? Same numbers, honest framing either way.
  const heading = high ? "How solid is this answer?" : "What would change this answer?";
  const note =
    (high
      ? "The smallest single change that would tip this result back below $50K — how close to the edge it sits."
      : "The smallest single change that would lift this result above $50K.") +
    " Only things a person could actually act on are considered — never age, sex, race or country.";

  return (
    <Panel step={2} title={heading} note={note} accent>
      {recourse.available ? (
        <ul className="mt-4 flex flex-col gap-3">
          {recourse.options.map((option) => (
            <li
              key={option.feature}
              className="flex items-baseline justify-between gap-3 text-sm border-l-2 border-blue-500 pl-3"
            >
              <span>
                {high ? "Changing just one thing — " : "If you "}
                <span className="font-medium">{option.text}</span>
                {high ? " — would tip it to ≤$50K." : ", the model would say >$50K."}
              </span>
              <span className="text-xs tabular-nums text-black/50 dark:text-white/50 shrink-0">
                {pct(option.probability)}
              </span>
            </li>
          ))}
        </ul>
      ) : recourse.closest ? (
        <p className="mt-4 text-sm">
          {high
            ? "No single change we allow would tip this below $50K — the result is not balanced on one answer. The largest move available is to "
            : "No single change we allow would lift this above $50K. The biggest move available is to "}
          <span className="font-medium">{recourse.closest.text}</span>, which shifts
          the estimate to {pct(recourse.closest.probability)} — still{" "}
          {high ? "above" : "below"} the cut-off.
        </p>
      ) : (
        <p className="mt-4 text-sm text-black/60 dark:text-white/60">
          No changeable factor was available for this input.
        </p>
      )}
    </Panel>
  );
}

function ProbeSection({
  probe,
  disagrees,
  baseline,
}: {
  probe: FairnessProbe;
  disagrees: boolean;
  baseline: Explanation["baseline"];
}) {
  return (
    <details className="border rounded-2xl border-black/15 dark:border-white/20 group">
      <summary className="p-6 sm:p-7 cursor-pointer list-none flex items-start gap-3">
        <span
          className="shrink-0 mt-0.5 w-6 h-6 rounded-full grid place-items-center text-xs font-semibold bg-black/10 dark:bg-white/15 text-black/70 dark:text-white/70"
          aria-hidden
        >
          3
        </span>
        <span className="flex-1">
          <span className="font-medium block">Was this answer fair to you?</span>
          <span className="text-xs text-black/55 dark:text-white/55 mt-1 block">
            The same person, with only sex changed, run through both models.
          </span>
        </span>
        <span className="text-xs text-black/45 dark:text-white/45 shrink-0 group-open:hidden underline">
          Show
        </span>
      </summary>

      <div className="px-6 sm:px-7 pb-6 sm:pb-7 flex flex-col gap-4 text-sm">
        {probe.available ? (
          <>
            <p className="text-black/70 dark:text-white/70">
              We re-ran the exact same person with only one thing changed — sex{" "}
              {probe.original_sex} → {probe.flipped_sex} — through both models.
            </p>

            <div className="flex flex-col gap-3">
              <ProbeRow
                title="The unmitigated baseline model"
                before={probe.baseline.original}
                after={probe.baseline.flipped}
                delta={probe.baseline.delta}
              />
              <ProbeRow
                title="The model you are using (sex removed)"
                before={probe.served.original}
                after={probe.served.flipped}
                delta={probe.served.delta}
              />
            </div>

            <p className="text-xs text-black/55 dark:text-white/55">
              {Math.abs(probe.baseline.delta) >= 0.01
                ? `Changing nothing but sex moved the baseline model by ${(
                    Math.abs(probe.baseline.delta) * 100
                  ).toFixed(1)} percentage points. The model serving you does not
                    receive sex at all, so its answer cannot move — that is what the
                    0.0 means, and it is the whole reason the mitigation exists.`
                : `The baseline barely moved for this particular person, but it does
                   move for many others — see the group-level gaps on the Fairness
                   Dashboard. The model serving you cannot move at all, because it
                   never receives sex.`}
            </p>
          </>
        ) : (
          <p className="text-black/60 dark:text-white/60">
            The sex-flip test is not available for this input.
          </p>
        )}

        <div className="border-t pt-4 border-black/10 dark:border-white/15">
          <p className="text-xs uppercase tracking-wide text-black/45 dark:text-white/45">
            What the unmitigated model would have said
          </p>
          <p className="mt-1">
            {baseline.prediction}{" "}
            <span className="text-black/55 dark:text-white/55">
              ({pct(baseline.probability_above_50k)} probability)
            </span>
          </p>
          <p className="text-xs mt-2 text-black/55 dark:text-white/55">
            {disagrees
              ? "The two models disagree on this person — a concrete sign of how much sex, relationship and marital status were driving the unmitigated model."
              : "Both models land on the same bracket here, though their confidence differs. Agreeing on one case does not make them equally fair overall."}
          </p>
          <Link href="/m3/fairness" className="text-xs underline mt-2 inline-block">
            See the group-level fairness numbers
          </Link>
        </div>
      </div>
    </details>
  );
}

function ProbeRow({
  title,
  before,
  after,
  delta,
}: {
  title: string;
  before: number;
  after: number;
  delta: number;
}) {
  const moved = Math.abs(delta) >= 0.001;
  return (
    <div className="flex items-center justify-between gap-3 border rounded-lg px-3 py-2 border-black/10 dark:border-white/15">
      <span className="text-sm">{title}</span>
      <span className="text-sm tabular-nums shrink-0">
        {pct(before)} → {pct(after)}{" "}
        <span
          className={
            moved
              ? "text-rose-700 dark:text-rose-400 font-medium"
              : "text-emerald-700 dark:text-emerald-400 font-medium"
          }
        >
          ({delta > 0 ? "+" : ""}
          {(delta * 100).toFixed(1)} pts)
        </span>
      </span>
    </div>
  );
}
