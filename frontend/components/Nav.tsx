import Link from "next/link";

export default function Nav() {
  return (
    <header className="border-b border-black/10 dark:border-white/15">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <span className="font-semibold text-sm">Adult Census Income Predictor</span>
        <nav className="flex gap-4 text-sm">
          <Link href="/" className="hover:underline">
            Predict
          </Link>
          <Link href="/about" className="hover:underline">
            Model Card
          </Link>
          <Link href="/fairness" className="hover:underline">
            Fairness Dashboard
          </Link>
        </nav>
      </div>
      <div className="bg-amber-50 dark:bg-amber-950/40 border-t border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-200 text-xs px-4 py-2 text-center">
        Trained on 1994 US Census data for a coursework fairness study — not a
        real income-prediction tool.{" "}
        <Link href="/about" className="underline">
          Read the Model Card
        </Link>
        .
      </div>
    </header>
  );
}
