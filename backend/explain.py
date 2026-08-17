"""Explanation engine for the /explain interface (Milestone 3).

Serves the one-hot models written by ../train_explainable.py. Because those are
logistic regressions, a prediction decomposes exactly:

    logit(p) = intercept + sum_j (coef_j * scaled_x_j)

so each feature's contribution is a real number in log-odds, not an estimate.
Contributions from the one-hot columns of the same original feature are summed
back together, so the user reads one line per question they answered
("Marital status: Married-civ-spouse  +0.62") instead of one line per column.

Four things are exposed:
  local_explanation  - why this answer, for this person
  recourse           - the smallest realistic change that flips the answer
  fairness_probe     - the same person with sex flipped, through both models
  GLOBAL             - how the model behaves overall (precomputed at train time)
"""

import json
import math
import os

import joblib
import numpy as np
import pandas as pd

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

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

# Roughly "how hard is this to actually do", used only to rank the recourse
# suggestions so the easiest one is offered first. Deliberately hand-set rather
# than learned: this encodes a human judgement about effort, not a fact about
# the data.
EFFORT_PER_UNIT = {
    "hours-per-week": 0.10,   # per extra hour per week
    "education": 1.50,        # per extra year of schooling
    "occupation": 4.00,       # flat: changing career
    "workclass": 3.00,        # flat: changing employment type
}


def _load(prefix):
    return joblib.load(os.path.join(ARTIFACTS_DIR, f"{prefix}.joblib"))


_BASELINE = _load("x_baseline")
_FE = _load("x_fe")

with open(os.path.join(ARTIFACTS_DIR, "x_global.json")) as f:
    GLOBAL = json.load(f)

with open(os.path.join(ARTIFACTS_DIR, "x_metrics.json")) as f:
    X_METRICS = json.load(f)

with open(os.path.join(ARTIFACTS_DIR, "x_recourse.json")) as f:
    _RECOURSE_CONFIG = json.load(f)

# Milestone 3 serves its own form schema rather than reusing Milestone 2's,
# which still offers "?" as a category these models were never trained on.
with open(os.path.join(ARTIFACTS_DIR, "x_schema.json")) as f:
    SCHEMA = json.load(f)

# feature -> global rank, so a personal factor can carry its global context
# inline ("the model's #1 factor overall") instead of sending the user off to
# read a separate chart.
_GLOBAL_RANK = {
    entry["feature"]: entry["rank"] for entry in GLOBAL["feature_elimination"]["features"]
}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _scale_rows(variant, raws: list) -> np.ndarray:
    """Encode a batch of raw input dicts into the variant's scaled matrix."""
    frame = pd.DataFrame(raws)
    numeric = frame[variant["numeric"]].astype(float).reset_index(drop=True)
    onehot = variant["encoder"].transform(frame[variant["categorical"]])
    onehot_names = [
        f"{feature}={category}"
        for feature, categories in zip(variant["categorical"], variant["encoder"].categories_)
        for category in categories
    ]
    combined = pd.concat([numeric, pd.DataFrame(onehot, columns=onehot_names)], axis=1)
    return variant["scaler"].transform(combined[variant["columns"]])


def _probabilities(variant, raws: list) -> np.ndarray:
    return variant["model"].predict_proba(_scale_rows(variant, raws))[:, 1]


# Recourse must not suggest things no person would do. The dataset's
# hours-per-week runs up to 99, but offering "work 99 hours a week" as advice is
# worse than offering nothing, so the search is capped at a punishing-but-real
# upper bound.
MAX_SUGGESTED_HOURS = 70

# Noun phrases so the one-line summary reads as English rather than as a form
# dump ("no capital gains", not "capital gain ($0)").
def _summary_phrase(raw: dict, feature: str) -> str:
    value = raw[feature]
    if feature == "age":
        return f"an age of {int(value)}"
    if feature == "hours-per-week":
        return f"{int(value)} hours a week"
    if feature == "education-num":
        return f"{int(value)} years of schooling"
    if feature == "education":
        return f"{value}-level education"
    if feature == "occupation":
        return f"{value} work"
    if feature == "capital-gain":
        return "no capital gains" if int(value) == 0 else f"${int(value):,} in capital gains"
    if feature == "capital-loss":
        return "no capital losses" if int(value) == 0 else f"${int(value):,} in capital losses"
    if feature == "native-country":
        return f"{value} as native country"
    return f"{HUMAN_LABELS.get(feature, feature).lower()} of {value}"


def _value_label(raw: dict, feature: str) -> str:
    value = raw[feature]
    if feature in ("capital-gain", "capital-loss"):
        return f"${int(value):,}"
    if feature == "hours-per-week":
        return f"{int(value)} hours/week"
    if feature == "education-num":
        return f"{int(value)} years"
    if feature == "age":
        return f"{int(value)} years old"
    return str(value)


def local_explanation(variant, raw: dict) -> dict:
    """Exact per-feature contribution breakdown for one person."""
    scaled = _scale_rows(variant, [raw])[0]
    coef = variant["model"].coef_[0]
    intercept = float(variant["model"].intercept_[0])
    per_column = scaled * coef

    grouped = {}
    for idx, column in enumerate(variant["columns"]):
        owner = variant["owners"][column]
        grouped[owner] = grouped.get(owner, 0.0) + float(per_column[idx])

    logit = intercept + float(per_column.sum())
    probability = _sigmoid(logit)

    factors = [
        {
            "feature": feature,
            "label": HUMAN_LABELS.get(feature, feature),
            "value": _value_label(raw, feature),
            "contribution": round(contribution, 6),
            "direction": "up" if contribution >= 0 else "down",
            "global_rank": _GLOBAL_RANK.get(feature),
        }
        for feature, contribution in grouped.items()
    ]
    factors.sort(key=lambda f: abs(f["contribution"]), reverse=True)

    return {
        "prediction": ">50K" if probability >= 0.5 else "<=50K",
        "probability_above_50k": round(probability, 4),
        # Probability for a statistically average person: every scaled input at
        # its training mean of zero, so only the intercept remains. This is the
        # starting point the factors below move away from.
        "base_probability": round(_sigmoid(intercept), 4),
        "factors": factors,
        "helped": [f for f in factors if f["contribution"] > 0],
        "hurt": [f for f in factors if f["contribution"] < 0],
    }


def plain_summary(explanation: dict, raw: dict) -> str:
    """The one sentence most users will read instead of the whole breakdown."""
    predicted_high = explanation["prediction"] == ">50K"
    drivers = explanation["helped"] if predicted_high else explanation["hurt"]
    if not drivers:
        return "No single answer stood out as the reason for this result."

    pieces = [_summary_phrase(raw, f["feature"]) for f in drivers[:3]]
    if len(pieces) == 1:
        joined = pieces[0]
    elif len(pieces) == 2:
        joined = f"{pieces[0]} and {pieces[1]}"
    else:
        joined = f"{pieces[0]}, {pieces[1]} and {pieces[2]}"

    verdict = "above $50K" if predicted_high else "at or below $50K"
    return f"What mattered most here: {joined} — together these put this person {verdict}."


def _candidate_changes(raw: dict, variant) -> list:
    """Enumerate every single-feature change the recourse search may consider."""
    config = _RECOURSE_CONFIG
    education_to_num = config["education_to_num"]
    low, high = config["hours_range"]
    candidates = []

    for feature in config["actionable"]:
        if feature not in variant["numeric"] and feature not in variant["categorical"]:
            continue

        if feature == "hours-per-week":
            current = int(raw[feature])
            ceiling = min(high, max(MAX_SUGGESTED_HOURS, current))
            for hours in range(low, ceiling + 1):
                if hours == current:
                    continue
                changed = dict(raw)
                changed[feature] = hours
                delta = hours - current
                candidates.append({
                    "raw": changed,
                    "feature": feature,
                    "effort": abs(delta) * EFFORT_PER_UNIT[feature],
                    "text": f"work {hours} hours a week instead of {current}",
                })
            continue

        if feature == "education":
            current = str(raw["education"])
            current_years = int(raw["education-num"])
            for level, years in education_to_num.items():
                if level == current:
                    continue
                changed = dict(raw)
                changed["education"] = level
                # education-num is a strict lookup of education in this dataset;
                # changing one without the other would describe a person who
                # cannot exist.
                changed["education-num"] = years
                candidates.append({
                    "raw": changed,
                    "feature": feature,
                    "effort": abs(years - current_years) * EFFORT_PER_UNIT[feature],
                    "text": f"have {level} instead of {current}",
                })
            continue

        # Remaining actionable features are plain categoricals with a flat cost.
        options = _category_options(variant, feature)
        current = str(raw[feature])
        for option in options:
            if option == current:
                continue
            changed = dict(raw)
            changed[feature] = option
            candidates.append({
                "raw": changed,
                "feature": feature,
                "effort": EFFORT_PER_UNIT[feature],
                "text": f"have {HUMAN_LABELS.get(feature, feature).lower()} "
                        f"'{option}' instead of '{current}'",
            })

    return candidates


def _category_options(variant, feature: str) -> list:
    index = variant["categorical"].index(feature)
    return [str(c) for c in variant["encoder"].categories_[index]]


def recourse(variant, raw: dict, current_probability: float, limit: int = 3) -> dict:
    """Smallest realistic single change that flips the predicted bracket.

    Only features a person can actually act on are searched -- see ACTIONABLE in
    ../train_explainable.py for why age, sex, race, country, marital status and
    capital gains are all excluded.
    """
    candidates = _candidate_changes(raw, variant)
    if not candidates:
        return {"available": False, "options": [], "closest": None}

    probabilities = _probabilities(variant, [c["raw"] for c in candidates])
    currently_high = current_probability >= 0.5

    flips = []
    for candidate, probability in zip(candidates, probabilities):
        candidate["probability"] = round(float(probability), 4)
        candidate["delta"] = round(float(probability) - current_probability, 4)
        if (probability >= 0.5) != currently_high:
            flips.append(candidate)

    flips.sort(key=lambda c: c["effort"])

    # Keep at most one suggestion per feature so the list reads as three
    # different routes rather than three variations of the same one.
    chosen, seen = [], set()
    for candidate in flips:
        if candidate["feature"] in seen:
            continue
        seen.add(candidate["feature"])
        chosen.append(candidate)
        if len(chosen) == limit:
            break

    def present(candidate):
        return {
            "feature": candidate["feature"],
            "label": HUMAN_LABELS.get(candidate["feature"], candidate["feature"]),
            "text": candidate["text"],
            "probability": candidate["probability"],
            "delta": candidate["delta"],
        }

    if chosen:
        return {
            "available": True,
            "direction": "down" if currently_high else "up",
            "options": [present(c) for c in chosen],
            "closest": None,
        }

    # Nothing flipped it. Report the change that moved the needle furthest in
    # the useful direction, so the answer is still informative rather than "no".
    best = max(candidates, key=lambda c: -c["delta"] if currently_high else c["delta"])
    return {
        "available": False,
        "direction": "down" if currently_high else "up",
        "options": [],
        "closest": present(best),
    }


_SEX_FLIP = {"Male": "Female", "Female": "Male"}
# relationship encodes sex directly for married people, which is exactly the
# proxy problem the mitigation exists to address.
_RELATIONSHIP_FLIP = {"Husband": "Wife", "Wife": "Husband"}


def fairness_probe(raw: dict, fe_probability: float, baseline_probability: float) -> dict:
    """The same person with sex flipped, run through both models.

    The mitigated model never sees sex, so its number must not move -- showing
    that zero next to the baseline's movement is the point of the probe.
    """
    original_sex = str(raw["sex"])
    flipped_sex = _SEX_FLIP.get(original_sex)
    if flipped_sex is None:
        return {"available": False}

    flipped = dict(raw)
    flipped["sex"] = flipped_sex

    # Second probe: flip the relationship proxy alongside sex. If this moves the
    # baseline more than the sex flip alone, removing 'sex' by itself would not
    # have been enough -- which is why relationship and marital-status are
    # dropped too.
    flipped_proxy = dict(flipped)
    relationship_flip = _RELATIONSHIP_FLIP.get(str(raw["relationship"]))
    if relationship_flip:
        flipped_proxy["relationship"] = relationship_flip

    baseline_flipped, baseline_proxy = _probabilities(
        _BASELINE, [flipped, flipped_proxy]
    )
    fe_flipped = float(_probabilities(_FE, [flipped])[0])

    return {
        "available": True,
        "original_sex": original_sex,
        "flipped_sex": flipped_sex,
        "relationship_also_flipped": bool(relationship_flip),
        "baseline": {
            "original": round(baseline_probability, 4),
            "flipped": round(float(baseline_flipped), 4),
            "delta": round(float(baseline_flipped) - baseline_probability, 4),
        },
        "baseline_with_proxy": {
            "flipped": round(float(baseline_proxy), 4),
            "delta": round(float(baseline_proxy) - baseline_probability, 4),
        },
        "served": {
            "original": round(fe_probability, 4),
            "flipped": round(fe_flipped, 4),
            "delta": round(fe_flipped - fe_probability, 4),
        },
    }


def explain(raw: dict) -> dict:
    """Everything the /explain page needs, from one round trip."""
    served = local_explanation(_FE, raw)
    baseline = local_explanation(_BASELINE, raw)

    return {
        "served": {
            **served,
            "summary": plain_summary(served, raw),
        },
        "baseline": {
            "prediction": baseline["prediction"],
            "probability_above_50k": baseline["probability_above_50k"],
        },
        "recourse": recourse(_FE, raw, served["probability_above_50k"]),
        "fairness_probe": fairness_probe(
            raw, served["probability_above_50k"], baseline["probability_above_50k"]
        ),
    }
