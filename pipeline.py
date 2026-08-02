"""
HAI Milestone 1: Bias & Fairness Analysis on Adult Census Income Dataset
Author: Om Anil

Pipeline:
1. Load + clean data
2. Pre-mitigation bias audit
3. Train baseline model, evaluate overall + subgroup performance
4. Fairness metrics (statistical parity, equal opportunity, disparate impact)
5. Apply mitigation strategies (feature elimination, reweighting, threshold optimization)
6. Re-evaluate and compare before/after
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from fairlearn.metrics import (
    MetricFrame, demographic_parity_difference, demographic_parity_ratio,
    equalized_odds_difference, selection_rate, true_positive_rate, false_positive_rate
)
from fairlearn.reductions import ExponentiatedGradient, DemographicParity
from fairlearn.postprocessing import ThresholdOptimizer

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education-num",
    "marital-status", "occupation", "relationship", "race", "sex",
    "capital-gain", "capital-loss", "hours-per-week", "native-country", "income"
]

# ---------------------------------------------------------------------------
# 1. LOAD + CLEAN
# ---------------------------------------------------------------------------
def load_data():
    data_path = "data/raw"
    train = pd.read_csv(f"{data_path}/adult.data", header=None, names=COLUMNS, na_values=" ?", skipinitialspace=True)
    test = pd.read_csv(f"{data_path}/adult.test", header=None, names=COLUMNS, na_values=" ?", skipinitialspace=True, skiprows=1)
    test["income"] = test["income"].str.replace(".", "", regex=False)
    df = pd.concat([train, test], ignore_index=True)
    df = df.dropna().reset_index(drop=True)
    df["income_binary"] = (df["income"].str.strip() == ">50K").astype(int)
    return df

def preprocess(df, drop_proxies=False):
    """Encode categoricals. drop_proxies removes sex/relationship/marital-status
    (feature elimination mitigation)."""
    data = df.copy()
    sex_col = data["sex"].copy()
    race_col = data["race"].copy()

    cat_cols = ["workclass", "education", "marital-status", "occupation",
                "relationship", "race", "sex", "native-country"]

    drop_cols = ["income", "income_binary", "fnlwgt"]
    if drop_proxies:
        drop_cols += ["sex", "relationship", "marital-status"]
        cat_cols = [c for c in cat_cols if c not in ["sex", "relationship", "marital-status"]]

    X = data.drop(columns=drop_cols)
    for c in cat_cols:
        le = LabelEncoder()
        X[c] = le.fit_transform(X[c])

    y = data["income_binary"]
    return X, y, sex_col, race_col

# ---------------------------------------------------------------------------
# 2. PRE-MITIGATION BIAS AUDIT
# ---------------------------------------------------------------------------
def bias_audit(df):
    print("=" * 70)
    print("PRE-TRAINING BIAS AUDIT")
    print("=" * 70)

    print("\n--- Representation by sex ---")
    print(df["sex"].value_counts(normalize=True))

    print("\n--- Representation by race ---")
    print(df["race"].value_counts(normalize=True))

    print("\n--- Base income>50K rate by sex ---")
    print(df.groupby("sex")["income_binary"].mean())

    print("\n--- Base income>50K rate by race ---")
    print(df.groupby("race")["income_binary"].mean())

    print("\n--- Proxy check: relationship status vs sex ---")
    print(pd.crosstab(df["sex"], df["relationship"], normalize="index"))

    print("""
Sources of potential bias identified:
1. Sampling bias: dataset is 1994 US Census extract — heavily male (~2:1),
   heavily White (~85%), not representative of current population.
2. Historical/label bias: income itself reflects historical wage gaps by
   sex and race baked into the labels, not just feature-driven differences.
3. Measurement bias: 'hours-per-week' and 'occupation' interact with
   'sex' due to historical occupational segregation.
4. Proxy bias: 'relationship' (e.g., Wife/Husband) and 'marital-status'
   strongly correlate with 'sex' and can act as proxies for it even if
   'sex' itself is removed.
""")

# ---------------------------------------------------------------------------
# 3 & 4. TRAIN + EVALUATE (overall + subgroup + fairness)
# ---------------------------------------------------------------------------
def train_and_evaluate(X, y, sensitive_series, label="baseline", model_type="logreg"):
    X_train, X_test, y_train, y_test, s_train, s_test = train_test_split(
        X, y, sensitive_series, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    if model_type == "logreg":
        model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    else:
        model = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, max_depth=10)

    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)

    results = evaluate_predictions(y_test, y_pred, s_test, label)
    return model, scaler, X_test, X_test_s, y_test, y_pred, s_test, results

def evaluate_predictions(y_test, y_pred, s_test, label):
    print("\n" + "=" * 70)
    print(f"EVALUATION: {label}")
    print("=" * 70)

    overall = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
    }
    print("\nOverall metrics:", {k: round(v, 4) for k, v in overall.items()})

    mf = MetricFrame(
        metrics={
            "accuracy": accuracy_score, "precision": precision_score,
            "recall": recall_score, "f1": f1_score, "selection_rate": selection_rate,
        },
        y_true=y_test, y_pred=y_pred, sensitive_features=s_test,
    )
    print("\nSubgroup metrics:\n", mf.by_group.round(4))

    dp_diff = demographic_parity_difference(y_test, y_pred, sensitive_features=s_test)
    dp_ratio = demographic_parity_ratio(y_test, y_pred, sensitive_features=s_test)
    eo_diff = equalized_odds_difference(y_test, y_pred, sensitive_features=s_test)

    print(f"\nStatistical parity difference: {dp_diff:.4f}")
    print(f"Disparate impact ratio (demographic parity ratio): {dp_ratio:.4f}  (1.0 = fair, <0.8 = concerning by 80% rule)")
    print(f"Equalized odds difference (proxy for equal opportunity gap): {eo_diff:.4f}")

    return {
        "label": label, "overall": overall, "by_group": mf.by_group,
        "dp_diff": dp_diff, "dp_ratio": dp_ratio, "eo_diff": eo_diff,
    }

# ---------------------------------------------------------------------------
# 5. MITIGATION STRATEGIES
# ---------------------------------------------------------------------------
def mitigate_reweighting(X, y, s):
    """Reweighting: upweight underrepresented (group, label) combos so the
    model sees an effectively balanced joint distribution."""
    df = pd.DataFrame({"s": s.values, "y": y.values})
    group_counts = df.groupby(["s", "y"]).size()
    total = len(df)
    n_groups = df["s"].nunique()
    n_labels = df["y"].nunique()
    expected = total / (n_groups * n_labels)
    weights = df.apply(lambda r: expected / group_counts[(r["s"], r["y"])], axis=1)
    return weights.values

def mitigate_threshold_optimizer(model, scaler, X_train, y_train, s_train, X_test_s, s_test):
    """Post-hoc: ThresholdOptimizer picks group-specific decision thresholds
    to equalize odds."""
    to = ThresholdOptimizer(
        estimator=model, constraints="equalized_odds",
        predict_method="predict_proba", prefit=True,
    )
    X_train_s = scaler.transform(X_train)
    to.fit(X_train_s, y_train, sensitive_features=s_train)
    y_pred_mitigated = to.predict(X_test_s, sensitive_features=s_test)
    return y_pred_mitigated

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = load_data()
    print(f"Total rows after cleaning: {len(df)}")
    bias_audit(df)

    # ---- BASELINE (all features, no mitigation) ----
    X, y, sex, race = preprocess(df, drop_proxies=False)
    model, scaler, X_test, X_test_s, y_test, y_pred, s_test, baseline_results = \
        train_and_evaluate(X, y, sex, label="Baseline (Logistic Regression, no mitigation)", model_type="logreg")

    # ---- MITIGATION 1: Feature elimination ----
    X_fe, y_fe, sex_fe, race_fe = preprocess(df, drop_proxies=True)
    model_fe, scaler_fe, X_test_fe, X_test_fe_s, y_test_fe, y_pred_fe, s_test_fe, fe_results = \
        train_and_evaluate(X_fe, y_fe, sex_fe, label="Mitigation A: Feature Elimination (drop sex/relationship/marital-status)", model_type="logreg")

    # ---- MITIGATION 2: Reweighting ----
    X_train, X_test2, y_train, y_test2, s_train, s_test2 = train_test_split(
        X, y, sex, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    weights = mitigate_reweighting(X_train, y_train, s_train)
    scaler2 = StandardScaler()
    X_train_s2 = scaler2.fit_transform(X_train)
    X_test_s2 = scaler2.transform(X_test2)
    model_rw = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    model_rw.fit(X_train_s2, y_train, sample_weight=weights)
    y_pred_rw = model_rw.predict(X_test_s2)
    rw_results = evaluate_predictions(y_test2, y_pred_rw, s_test2, "Mitigation B: Reweighting")

    # ---- MITIGATION 3: Threshold Optimization (post-hoc, on baseline model) ----
    X_train3, X_test3, y_train3, y_test3, s_train3, s_test3 = train_test_split(
        X, y, sex, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    scaler3 = StandardScaler()
    X_train3_s = scaler3.fit_transform(X_train3)
    X_test3_s = scaler3.transform(X_test3)
    base_model3 = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    base_model3.fit(X_train3_s, y_train3)
    y_pred_to = mitigate_threshold_optimizer(base_model3, scaler3, X_train3, y_train3, s_train3, X_test3_s, s_test3)
    to_results = evaluate_predictions(y_test3, y_pred_to, s_test3, "Mitigation C: Threshold Optimization (equalized odds)")

    # ---- SUMMARY TABLE ----
    print("\n" + "=" * 70)
    print("SUMMARY: BEFORE vs AFTER MITIGATION")
    print("=" * 70)
    summary = pd.DataFrame([
        {"Model": r["label"], "Accuracy": r["overall"]["accuracy"], "F1": r["overall"]["f1"],
         "DP Diff": r["dp_diff"], "DP Ratio": r["dp_ratio"], "EO Diff": r["eo_diff"]}
        for r in [baseline_results, fe_results, rw_results, to_results]
    ])
    print(summary.round(4).to_string(index=False))
    os.makedirs("output", exist_ok=True)
    summary.to_csv("output/summary_results.csv", index=False)

    # ---- PLOT ----
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    labels_short = ["Baseline", "Feature\nElimination", "Reweighting", "Threshold\nOpt."]

    axes[0].bar(labels_short, summary["Accuracy"], color="#4C72B0", label="Accuracy")
    axes[0].bar(labels_short, summary["F1"], color="#DD8452", alpha=0.6, label="F1", width=0.5)
    axes[0].set_title("Overall Performance")
    axes[0].set_ylim(0, 1)
    axes[0].legend()

    axes[1].bar(labels_short, summary["DP Diff"].abs(), color="#55A868", label="|Statistical Parity Diff|")
    axes[1].bar(labels_short, summary["EO Diff"].abs(), color="#C44E52", alpha=0.6, label="|Equalized Odds Diff|", width=0.5)
    axes[1].set_title("Fairness Gaps (lower = fairer)")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig("output/fairness_comparison.png", dpi=150)
    print("\nSaved: output/summary_results.csv, output/fairness_comparison.png")
