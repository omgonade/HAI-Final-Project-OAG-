import { getModelCard } from "@/lib/api";

export default async function AboutPage() {
  const card = await getModelCard();

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Model Card</h1>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1">
          What this model does, and — more importantly — what it does not do.
        </p>
      </div>

      <Section title="Task">
        <p>{card.task}</p>
      </Section>

      <Section title="Which model is being served">
        <p>{card.served_model}</p>
      </Section>

      <Section title="Training data">
        <p>{card.training_data}</p>
      </Section>

      <Section title="Scope and limitations">
        <ul className="list-disc pl-5 flex flex-col gap-2">
          {card.scope.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Section>

      <Section title="Known bias sources">
        <ul className="list-disc pl-5 flex flex-col gap-2">
          {card.known_bias_sources.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Section>

      <div className="border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 rounded-lg p-4 text-sm">
        This model must not be used to make real decisions about real people (e.g.
        hiring, lending, benefits eligibility). It exists to demonstrate bias
        measurement and mitigation for a coursework project.
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-medium">{title}</h2>
      <div className="text-sm text-black/70 dark:text-white/70 leading-relaxed">
        {children}
      </div>
    </section>
  );
}
