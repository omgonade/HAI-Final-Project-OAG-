"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// The two milestones are separate interfaces, so the navigation is too: while
// you are inside one, you only see that one's pages, plus a single control to
// jump to the other. Mixing all the links together would defeat the point of
// keeping the versions apart.

type Milestone = "m2" | "m3";

const LINKS: Record<Milestone, { href: string; label: string }[]> = {
  m2: [
    { href: "/m2", label: "Predict" },
    { href: "/m2/about", label: "Model Card" },
    { href: "/m2/fairness", label: "Fairness Dashboard" },
  ],
  m3: [
    { href: "/m3", label: "Why this answer" },
    { href: "/m3/how-it-works", label: "How it works" },
    { href: "/m3/fairness", label: "Fairness Dashboard" },
    { href: "/m3/about", label: "Model Card" },
  ],
};

const TITLES: Record<Milestone, string> = {
  m2: "Milestone 2 — Prediction interface",
  m3: "Milestone 3 — Explainable interface",
};

export default function Nav() {
  const pathname = usePathname();
  const milestone: Milestone | null = pathname.startsWith("/m3")
    ? "m3"
    : pathname.startsWith("/m2")
      ? "m2"
      : null;

  return (
    <header className="border-b border-black/10 dark:border-white/15">
      <div className="max-w-4xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="font-semibold text-sm">Adult Census Income Predictor</span>
          {milestone && (
            <span
              className={`text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 ${
                milestone === "m3"
                  ? "bg-blue-600 text-white"
                  : "bg-black/10 dark:bg-white/15 text-black/70 dark:text-white/70"
              }`}
            >
              {milestone === "m3" ? "M3" : "M2"}
            </span>
          )}
        </Link>

        {milestone && (
          <nav className="flex flex-wrap items-center gap-4 text-sm">
            {LINKS[milestone].map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "font-medium underline underline-offset-4"
                      : "hover:underline"
                  }
                >
                  {link.label}
                </Link>
              );
            })}
            <Link
              href={milestone === "m3" ? "/m2" : "/m3"}
              className="rounded-full border border-black/20 dark:border-white/25 px-3 py-1 text-xs hover:border-black/50 dark:hover:border-white/50 transition-colors"
            >
              {milestone === "m3" ? "← View Milestone 2" : "View Milestone 3 →"}
            </Link>
          </nav>
        )}
      </div>

      {milestone && (
        <div className="bg-black/[0.03] dark:bg-white/[0.04] border-t border-black/10 dark:border-white/10 text-[11px] px-4 py-1.5 text-center text-black/55 dark:text-white/55">
          You are viewing <span className="font-medium">{TITLES[milestone]}</span>
        </div>
      )}

      <div className="bg-amber-50 dark:bg-amber-950/40 border-t border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-200 text-xs px-4 py-2 text-center">
        Trained on 1994 US Census data for a coursework fairness study — not a real
        income-prediction tool.{" "}
        <Link href={milestone === "m2" ? "/m2/about" : "/m3/about"} className="underline">
          Read the Model Card
        </Link>
        .
      </div>
    </header>
  );
}
