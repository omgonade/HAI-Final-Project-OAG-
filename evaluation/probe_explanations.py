"""Third evidence pass: probes the /explain endpoint directly.

The UI walkthrough raised three questions that need numbers rather than
screenshots:

  1. The result card prints `probability_above_50k` under the word
     "confidence". How badly does that mislabel low-probability cases?
  2. The form collects 13 fields; the served model uses 10. Which inputs are
     silently discarded, and does the response say so anywhere?
  3. Recourse excludes capital-gain as "not actionable", yet it is a top-ranked
     factor. How often is the strongest driver something the recourse panel
     refuses to discuss?

Usage:  venv\\Scripts\\python.exe evaluation\\probe_explanations.py
"""

import json
import os
import urllib.request

API = os.environ.get("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
# See run_inspection.py: generated evidence lives with the report, which is
# gitignored, so that this script stays readable in the repository.
OUTPUT = os.environ.get(
    "EVAL_OUTPUT_DIR",
    os.path.join(HERE, os.pardir, "Reports", "Milestone4_Evaluation"),
)
LOGS = os.path.join(OUTPUT, "logs")
os.makedirs(LOGS, exist_ok=True)


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req))


BASE_PERSON = {
    "age": 42, "workclass": "Private", "education": "Bachelors",
    "education-num": 13, "marital-status": "Married-civ-spouse",
    "occupation": "Exec-managerial", "relationship": "Husband", "race": "White",
    "sex": "Male", "capital-gain": 0, "capital-loss": 0, "hours-per-week": 50,
    "native-country": "United-States",
}

CASES = {
    "preset_mid_career_manager": BASE_PERSON,
    "preset_part_time_clerk": {
        **BASE_PERSON, "age": 27, "education": "HS-grad", "education-num": 9,
        "marital-status": "Never-married", "occupation": "Adm-clerical",
        "relationship": "Not-in-family", "sex": "Female", "hours-per-week": 30,
    },
    "preset_models_disagree": {**BASE_PERSON, "age": 29, "hours-per-week": 45},
    "borderline_just_under": {**BASE_PERSON, "hours-per-week": 45, "age": 30},
    "very_low_probability": {
        **BASE_PERSON, "age": 18, "education": "11th", "education-num": 7,
        "occupation": "Other-service", "hours-per-week": 20, "sex": "Female",
        "marital-status": "Never-married", "relationship": "Own-child",
    },
    "very_high_probability": {
        **BASE_PERSON, "age": 50, "education": "Doctorate", "education-num": 16,
        "capital-gain": 15000, "hours-per-week": 60,
    },
    "capital_gain_dominant": {**BASE_PERSON, "capital-gain": 20000},
}

FORM_FIELDS = list(BASE_PERSON.keys())

out = {"api": API, "cases": {}}

for name, person in CASES.items():
    r = post("/explain", person)
    served = r["served"]
    p = served["probability_above_50k"]
    factors = {f["feature"]: f["contribution"] for f in served["factors"]}
    strongest = max(factors, key=lambda k: abs(factors[k])) if factors else None
    recourse_features = [o["feature"] for o in r["recourse"]["options"]]

    out["cases"][name] = {
        "prediction": served["prediction"],
        "probability_above_50k": p,
        # What the card actually prints under the word "confidence" vs. the
        # model's real confidence in the bracket it just announced.
        "printed_as_confidence": round(p * 100, 1),
        "true_confidence_in_stated_bracket": round(
            (p if served["prediction"] == ">50K" else 1 - p) * 100, 1
        ),
        "confidence_label_error_pts": round(
            abs((p if served["prediction"] == ">50K" else 1 - p) - p) * 100, 1
        ),
        "distance_from_threshold_pts": round(abs(p - 0.5) * 100, 1),
        "n_factors_shown": len(served["factors"]),
        "fields_collected_but_unused": [f for f in FORM_FIELDS if f not in factors],
        "strongest_factor": strongest,
        "strongest_factor_value": round(factors[strongest], 3) if strongest else None,
        "strongest_factor_is_actionable": strongest in
            ["hours-per-week", "education", "education-num", "occupation", "workclass"],
        "recourse_available": r["recourse"]["available"],
        "recourse_features_offered": recourse_features,
        "baseline_prediction": r["baseline"]["prediction"],
        "models_disagree": r["baseline"]["prediction"] != served["prediction"],
        "probe_baseline_delta_pts": round(
            r["fairness_probe"].get("baseline", {}).get("delta", 0) * 100, 2
        ),
        # Computed by the backend, never rendered by any component.
        "probe_baseline_with_proxy_delta_pts": round(
            r["fairness_probe"].get("baseline_with_proxy", {}).get("delta", 0) * 100, 2
        ),
    }

path = os.path.join(LOGS, "explanation_probe.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("case                          pred     printed'confidence'  true conf   error")
print("-" * 78)
for name, c in out["cases"].items():
    print("%-28s %-8s %6.1f%%          %6.1f%%   %5.1f pts"
          % (name, c["prediction"], c["printed_as_confidence"],
             c["true_confidence_in_stated_bracket"], c["confidence_label_error_pts"]))

print()
print("fields collected but never explained:",
      out["cases"]["preset_mid_career_manager"]["fields_collected_but_unused"])
print()
print("case                          strongest factor   actionable?  recourse offers")
print("-" * 78)
for name, c in out["cases"].items():
    print("%-28s %-18s %-12s %s"
          % (name, c["strongest_factor"], c["strongest_factor_is_actionable"],
             c["recourse_features_offered"] or "(none)"))

print()
print("sex-flip vs sex+relationship-flip on the baseline (pts moved):")
for name, c in out["cases"].items():
    print("  %-28s sex only %+6.2f   sex+relationship %+6.2f  <- second never shown in UI"
          % (name, c["probe_baseline_delta_pts"],
             c["probe_baseline_with_proxy_delta_pts"]))

print("\nWrote " + path)
