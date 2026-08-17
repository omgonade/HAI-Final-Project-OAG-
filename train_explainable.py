"""HAI Milestone 3: trains the *explainable* model variants used by /explain.

Why a second training script instead of editing pipeline.py:

pipeline.py label-encodes categoricals (Occupation -> 0..13, alphabetically).
That is fine for measuring accuracy and fairness, but it makes per-prediction
explanation impossible: there is a single coefficient for "occupation" as if it
were a quantity, so the model cannot say "being an Exec-manager added +0.71".

Here the categoricals are one-hot encoded instead, so every individual category
gets its own coefficient. The model is still logistic regression, which means a
prediction decomposes *exactly* into per-feature contributions:

    logit(p) = intercept + sum_j (coef_j * scaled_x_j)

For a linear model this decomposition is precisely the SHAP value of each
feature, so no approximation or sampling is involved.

Artifacts are written with an `x_` prefix alongside the Milestone 1/2 ones, so the
original interface keeps serving the exact same numbers it always did.
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from fairlearn.metrics import (
    MetricFrame, demographic_parity_difference, demographic_parity_ratio,
    equalized_odds_difference, selection_rate,
)

from pipeline import load_data, RANDOM_STATE

CATEGORICAL = [
    "workclass", "education", "marital-status", "occupation",
    "relationship", "race", "sex", "native-country",
]
NUMERIC = ["age", "education-num", "capital-gain", "capital-loss", "hours-per-week"]

# Features the "what would change this?" search is allowed to modify. Age, race,
# sex and native-country are excluded because they are not things a person can
# act on, and recommending them would be both useless and offensive. Capital
# gain/loss are excluded because having investment income is not a decision one
# simply makes. Marital status and relationship are excluded on the same
# grounds -- "get married" is not legitimate financial advice (and the served
# model does not use them anyway).
ACTIONABLE = ["hours-per-week", "education", "occupation", "workclass"]

DROPPED_BY_MITIGATION = ["sex", "relationship", "marital-status"]

HUMAN_LABELS = {
    "age": "Age",
    "workclass": "Work class",
    "education": "Education",
    "education-num": "Years of education",
    "marital-status": "Marital status",
    "occupation": "Occupation",
    "relationship": "Relationship",
    "race": "Race",
    "sex": "Sex",
    "capital-gain": "Capital gain",
    "capital-loss": "Capital loss",
    "hours-per-week": "Hours per week",
    "native-country": "Native country",
}

ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "backend", "artifacts"
)


class Variant:
    """One trained model plus everything needed to encode a row and explain it."""

    def __init__(self, name, numeric, categorical, encoder, scaler, model, columns, owners):
        self.name = name
        self.numeric = numeric
        self.categorical = categorical
        self.encoder = encoder
        self.scaler = scaler
        self.model = model
        self.columns = columns      # expanded column names, in matrix order
        self.owners = owners        # expanded column -> original feature name


def build_variant(df, name, drop_features):
    """One-hot encode, scale, and fit logistic regression for one feature set."""
    numeric = [c for c in NUMERIC if c not in drop_features]
    categorical = [c for c in CATEGORICAL if c not in drop_features]

    y = df["income_binary"]
    raw = df[numeric + categorical]

    # Every category keeps its own column (no drop="first"): a dropped reference
    # category would silently fold its effect into the intercept and make the
    # per-category explanations harder to read.
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoder.fit(raw[categorical])

    expanded = list(numeric)
    owners = {c: c for c in numeric}
    for feature, categories in zip(categorical, encoder.categories_):
        for category in categories:
            column = f"{feature}={category}"
            expanded.append(column)
            owners[column] = feature

    X = _encode_frame(raw, numeric, categorical, encoder, expanded)

    X_train, X_test, y_train, y_test, s_train, s_test = train_test_split(
        X, y, df["sex"], test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)
    model.fit(X_train_s, y_train)

    variant = Variant(name, numeric, categorical, encoder, scaler, model, expanded, owners)
    metrics = _evaluate(model, X_test_s, y_test, s_test, name)
    return variant, metrics, X_test_s


def _encode_frame(raw, numeric, categorical, encoder, expanded):
    """Numeric columns as-is + one-hot block, returned in `expanded` order."""
    onehot = encoder.transform(raw[categorical])
    onehot_names = [
        f"{feature}={category}"
        for feature, categories in zip(categorical, encoder.categories_)
        for category in categories
    ]
    frame = pd.concat(
        [
            raw[numeric].reset_index(drop=True).astype(float),
            pd.DataFrame(onehot, columns=onehot_names),
        ],
        axis=1,
    )
    return frame[expanded]


def _evaluate(model, X_test_s, y_test, s_test, label):
    y_pred = model.predict(X_test_s)
    mf = MetricFrame(
        metrics={
            "accuracy": accuracy_score, "precision": precision_score,
            "recall": recall_score, "f1": f1_score, "selection_rate": selection_rate,
        },
        y_true=y_test, y_pred=y_pred, sensitive_features=s_test,
    )
    result = {
        "label": label,
        "overall": {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 6),
            "precision": round(float(precision_score(y_test, y_pred)), 6),
            "recall": round(float(recall_score(y_test, y_pred)), 6),
            "f1": round(float(f1_score(y_test, y_pred)), 6),
        },
        "by_group": {
            str(k): {m: round(float(v), 6) for m, v in row.items()}
            for k, row in mf.by_group.iterrows()
        },
        "dp_diff": round(float(demographic_parity_difference(y_test, y_pred, sensitive_features=s_test)), 6),
        "dp_ratio": round(float(demographic_parity_ratio(y_test, y_pred, sensitive_features=s_test)), 6),
        "eo_diff": round(float(equalized_odds_difference(y_test, y_pred, sensitive_features=s_test)), 6),
    }
    print(f"\n--- {label} (one-hot) ---")
    print("overall:", result["overall"])
    print(f"dp_diff={result['dp_diff']}  dp_ratio={result['dp_ratio']}  eo_diff={result['eo_diff']}")
    return result


def global_explanation(variant, X_test_s):
    """Global importance, derived from the same contributions used locally.

    Importance of a feature = the mean absolute contribution it makes to a
    prediction across the held-out test set. Using the local contributions
    themselves (rather than raw coefficient size) means the global page and the
    personal explanation are two views of one quantity, not two different
    stories -- and it accounts for how often each category actually occurs.
    """
    coef = variant.model.coef_[0]
    contributions = X_test_s * coef                     # (n_rows, n_columns)
    mean_abs = np.abs(contributions).mean(axis=0)

    per_feature = {}
    for idx, column in enumerate(variant.columns):
        owner = variant.owners[column]
        per_feature[owner] = per_feature.get(owner, 0.0) + float(mean_abs[idx])

    ranked = sorted(per_feature.items(), key=lambda kv: kv[1], reverse=True)
    features = [
        {
            "feature": feature,
            "label": HUMAN_LABELS.get(feature, feature),
            "importance": round(importance, 6),
            "rank": rank,
        }
        for rank, (feature, importance) in enumerate(ranked, start=1)
    ]

    # Signed per-category effects: the "which specific answers move the needle"
    # view. Reported in log-odds, on the scaled inputs, so magnitudes are
    # comparable across features.
    effects = []
    for idx, column in enumerate(variant.columns):
        owner = variant.owners[column]
        if owner == column:
            continue  # numeric feature, has no single "category" to report
        effects.append({
            "feature": owner,
            "label": HUMAN_LABELS.get(owner, owner),
            "value": column.split("=", 1)[1],
            "effect": round(float(coef[idx]), 6),
        })
    effects.sort(key=lambda e: abs(e["effect"]), reverse=True)

    numeric_effects = [
        {
            "feature": column,
            "label": HUMAN_LABELS.get(column, column),
            "effect": round(float(coef[idx]), 6),
        }
        for idx, column in enumerate(variant.columns)
        if variant.owners[column] == column
    ]
    numeric_effects.sort(key=lambda e: abs(e["effect"]), reverse=True)

    return {
        "features": features,
        "top_category_effects": effects[:25],
        "numeric_effects": numeric_effects,
        "intercept": round(float(variant.model.intercept_[0]), 6),
    }


def education_mapping(df):
    """education -> education-num, so recourse can change both consistently.

    In this dataset the two are a strict lookup of each other; treating them as
    independent would let the search suggest impossible people.
    """
    pairs = df.groupby("education")["education-num"].median().round().astype(int)
    return {str(k): int(v) for k, v in pairs.items()}


# Order the form presents the fields in — the dataset's own column order.
INPUT_ORDER = [
    "age", "workclass", "education", "education-num", "marital-status",
    "occupation", "relationship", "race", "sex", "capital-gain",
    "capital-loss", "hours-per-week", "native-country",
]


def input_schema(df):
    """Form schema for the Milestone 3 page, built from the *cleaned* data.

    Milestone 2's feature_schema.json still lists "?" as a selectable category,
    because pipeline.py never dropped the missing values (see drop_missing).
    Serving that schema here would offer the user a value these models were
    never trained on: OneHotEncoder(handle_unknown="ignore") would silently zero
    the whole feature out and the explanation would quietly be wrong rather than
    erroring. So Milestone 3 serves a schema that matches its own models.

    Shaped like feature_schema.json so the frontend's existing type applies.
    """
    return {
        "baseline": {
            "columns": INPUT_ORDER,
            "categorical": {
                c: sorted(str(v) for v in df[c].unique()) for c in CATEGORICAL
            },
            "numeric": {
                c: {
                    "min": int(df[c].min()),
                    "max": int(df[c].max()),
                    "median": int(df[c].median()),
                }
                for c in NUMERIC
            },
            # Options stay alphabetical so they are easy to scan, but the form
            # opens on the most common value of each. Falling back to the first
            # option alphabetically produces a nonsense starting person
            # (Federal-gov, 10th grade, born in Cambodia) that no one intended.
            "defaults": {c: str(df[c].mode()[0]) for c in CATEGORICAL},
        },
        "feature_elimination": {
            "columns": [c for c in INPUT_ORDER if c not in DROPPED_BY_MITIGATION],
        },
    }


def save(variant, prefix):
    joblib.dump(
        {
            "numeric": variant.numeric,
            "categorical": variant.categorical,
            "encoder": variant.encoder,
            "scaler": variant.scaler,
            "model": variant.model,
            "columns": variant.columns,
            "owners": variant.owners,
        },
        os.path.join(ARTIFACTS_DIR, f"{prefix}.joblib"),
    )


def drop_missing(df):
    """Actually remove the rows with missing values.

    pipeline.load_data() intends to do this via na_values=" ?", but it also
    passes skipinitialspace=True, so the leading space is stripped before the
    na_values comparison and "?" never matches. The result is that no rows are
    dropped and "?" survives as if it were a real category -- which showed up
    here as the recourse search cheerfully suggesting a work class of "?".

    Fixed only for the Milestone 3 models so that pipeline.py, and the Milestone
    1 numbers already reported from it, are left untouched.
    """
    cleaned = df.replace("?", np.nan).dropna().reset_index(drop=True)
    print(f"Dropped {len(df) - len(cleaned)} rows containing missing values")
    return cleaned


if __name__ == "__main__":
    df = drop_missing(load_data())
    print(f"Rows after cleaning: {len(df)}")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    baseline, baseline_metrics, baseline_X = build_variant(df, "baseline", drop_features=[])
    fe, fe_metrics, fe_X = build_variant(
        df, "feature_elimination", drop_features=DROPPED_BY_MITIGATION
    )

    save(baseline, "x_baseline")
    save(fe, "x_fe")

    with open(os.path.join(ARTIFACTS_DIR, "x_metrics.json"), "w") as f:
        json.dump({"baseline": baseline_metrics, "feature_elimination": fe_metrics}, f, indent=2)

    with open(os.path.join(ARTIFACTS_DIR, "x_global.json"), "w") as f:
        json.dump(
            {
                "feature_elimination": global_explanation(fe, fe_X),
                "baseline": global_explanation(baseline, baseline_X),
                "dropped_by_mitigation": DROPPED_BY_MITIGATION,
                "human_labels": HUMAN_LABELS,
            },
            f,
            indent=2,
        )

    with open(os.path.join(ARTIFACTS_DIR, "x_schema.json"), "w") as f:
        json.dump(input_schema(df), f, indent=2)

    with open(os.path.join(ARTIFACTS_DIR, "x_recourse.json"), "w") as f:
        json.dump(
            {
                "actionable": ACTIONABLE,
                "education_to_num": education_mapping(df),
                "hours_range": [
                    int(df["hours-per-week"].min()),
                    int(df["hours-per-week"].max()),
                ],
            },
            f,
            indent=2,
        )

    print(f"\nSaved explainable artifacts (x_*) to {ARTIFACTS_DIR}")
