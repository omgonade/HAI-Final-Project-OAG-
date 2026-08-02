# Project Structure

## Files

```
Final Project/
├── pipeline.py              # Main script — everything runs from here
├── download_data.py         # Downloads adult.data/adult.test/adult.names into data/raw/
├── requirements.txt         # pandas, numpy, scikit-learn, fairlearn, matplotlib
├── Dockerfile
├── data/raw/                # adult.data, adult.test, adult.names (downloaded, not committed)
└── output/                  # Generated: summary_results.csv, fairness_comparison.png
```

There is no `src/` package. `pipeline.py` is intentionally a single, self-contained
script — every function it needs is defined in that file, so there's nothing to wire
up or keep in sync across modules.

---

## `pipeline.py` walkthrough

Run top to bottom, the script does:

**1. Load + clean (`load_data`)**
Reads `data/raw/adult.data` and `data/raw/adult.test`, concatenates them, drops rows
with missing values (`?` entries), and adds a binary `income_binary` column
(1 = >50K, 0 = ≤50K).

**2. Preprocess (`preprocess`)**
Label-encodes the categorical columns (workclass, education, marital-status,
occupation, relationship, race, sex, native-country). Drops `income`, `income_binary`,
and `fnlwgt` (a census sampling weight, not a predictive feature) from the feature
matrix. When called with `drop_proxies=True`, also drops `sex`, `relationship`, and
`marital-status` — this is the Feature Elimination mitigation.

**3. Bias audit (`bias_audit`)**
Prints, before any model is trained:
- Representation by sex and race (`value_counts(normalize=True)`)
- Base income>50K rate by sex and by race
- A crosstab of relationship status vs. sex, to show how strongly `relationship`
  proxies for `sex`
- A short written summary of the four bias categories this evidence supports
  (sampling, historical/label, measurement, proxy)

**4. Train + evaluate (`train_and_evaluate`, `evaluate_predictions`)**
`train_and_evaluate` does a stratified 75/25 train-test split, standardizes features,
fits a Logistic Regression (or Random Forest, via `model_type="rf"`), and hands off to
`evaluate_predictions`, which computes:
- Overall accuracy / precision / recall / F1
- Subgroup metrics via `fairlearn.metrics.MetricFrame`
- Three fairness metrics: `demographic_parity_difference`,
  `demographic_parity_ratio`, `equalized_odds_difference`

**5. Mitigation strategies**
- `mitigate_reweighting(X, y, s)` — computes a per-sample weight so that each
  (sex, income) combination contributes equally to the training loss, then the main
  block trains a fresh Logistic Regression with `sample_weight=weights`.
- `mitigate_threshold_optimizer(model, scaler, ...)` — wraps
  `fairlearn.postprocessing.ThresholdOptimizer` around an already-trained model,
  choosing a separate decision threshold per sex group to satisfy the
  `equalized_odds` constraint.
- Feature Elimination isn't a separate function — it's just `preprocess(df,
  drop_proxies=True)` followed by the normal `train_and_evaluate` call.

**6. Summary + plot**
Builds a comparison table (`summary_results.csv`) across all four models
(baseline + 3 mitigations) and a two-panel bar chart (`fairness_comparison.png`):
left panel is Accuracy/F1, right panel is the two fairness gaps.

---

## `download_data.py`

Standalone script. Downloads the three UCI Adult dataset files into `data/raw/`,
skipping any that already exist, then verifies file sizes. Run once before
`pipeline.py`.

---

## Reproducibility

`RANDOM_STATE = 42` is set once near the top of `pipeline.py` and used for every
`train_test_split` and every model's `random_state`. Re-running the pipeline against
the same `data/raw/` files will reproduce the same numbers.

---

**Last Updated**: August 2, 2026
