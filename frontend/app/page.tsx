import { getFeatureSchema } from "@/lib/api";
import PredictForm from "@/components/PredictForm";

export default async function PredictPage() {
  const schema = await getFeatureSchema();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Predict income bracket</h1>
        <p className="text-sm text-black/60 dark:text-white/60 mt-1 max-w-2xl">
          Enter the attributes below to get a prediction from the fairness-mitigated
          model, alongside what the unmitigated baseline model would have said for the
          same input.
        </p>
      </div>
      <PredictForm schema={schema} />
    </div>
  );
}
