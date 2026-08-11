"""Loads the artifacts written by ../pipeline.py and serves predictions.

Two model variants are loaded:
- "baseline": trained on all features, no fairness mitigation.
- "feature_elimination": trained without sex/relationship/marital-status,
  the mitigation with the best fairness/accuracy tradeoff (see root README).

Every prediction returns both, so callers can show the effect of mitigation
on that specific input.
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

CATEGORICAL_COLUMNS = [
    "workclass", "education", "marital-status", "occupation",
    "relationship", "race", "sex", "native-country",
]
NUMERIC_COLUMNS = ["age", "education-num", "capital-gain", "capital-loss", "hours-per-week"]


class PredictionInput(BaseModel):
    age: int
    workclass: str
    education: str
    education_num: int = Field(alias="education-num")
    marital_status: str = Field(alias="marital-status")
    occupation: str
    relationship: str
    race: str
    sex: str
    capital_gain: int = Field(alias="capital-gain")
    capital_loss: int = Field(alias="capital-loss")
    hours_per_week: int = Field(alias="hours-per-week")
    native_country: str = Field(alias="native-country")

    model_config = {"populate_by_name": True}

    def to_raw_dict(self) -> dict:
        return {
            "age": self.age,
            "workclass": self.workclass,
            "education": self.education,
            "education-num": self.education_num,
            "marital-status": self.marital_status,
            "occupation": self.occupation,
            "relationship": self.relationship,
            "race": self.race,
            "sex": self.sex,
            "capital-gain": self.capital_gain,
            "capital-loss": self.capital_loss,
            "hours-per-week": self.hours_per_week,
            "native-country": self.native_country,
        }


class UnknownCategoryError(ValueError):
    def __init__(self, column: str, value: str, allowed: list):
        self.column = column
        self.value = value
        self.allowed = allowed
        super().__init__(f"Unknown value '{value}' for '{column}'")


class _ModelVariant:
    def __init__(self, name: str, columns: list, model, scaler, encoders: dict):
        self.name = name
        self.columns = columns
        self.model = model
        self.scaler = scaler
        self.encoders = encoders

    def encode(self, raw: dict) -> np.ndarray:
        row = {}
        for col in self.columns:
            value = raw[col]
            if col in self.encoders:
                le = self.encoders[col]
                str_value = str(value)
                if str_value not in le.classes_:
                    raise UnknownCategoryError(col, str_value, list(le.classes_))
                row[col] = le.transform([str_value])[0]
            else:
                row[col] = value
        frame = pd.DataFrame([row], columns=self.columns)
        return self.scaler.transform(frame)

    def predict(self, raw: dict) -> dict:
        X = self.encode(raw)
        proba = self.model.predict_proba(X)[0]
        pred = int(self.model.predict(X)[0])
        return {
            "prediction": ">50K" if pred == 1 else "<=50K",
            "probability_above_50k": round(float(proba[1]), 4),
        }


def _load_variant(name: str, prefix: str, columns: list) -> _ModelVariant:
    model = joblib.load(os.path.join(ARTIFACTS_DIR, f"{prefix}_model.joblib"))
    scaler = joblib.load(os.path.join(ARTIFACTS_DIR, f"{prefix}_scaler.joblib"))
    encoders = joblib.load(os.path.join(ARTIFACTS_DIR, f"{prefix}_encoders.joblib"))
    return _ModelVariant(name, columns, model, scaler, encoders)


with open(os.path.join(ARTIFACTS_DIR, "feature_schema.json")) as f:
    FEATURE_SCHEMA = json.load(f)

with open(os.path.join(ARTIFACTS_DIR, "metrics.json")) as f:
    METRICS = json.load(f)

_baseline = _load_variant("baseline", "baseline", FEATURE_SCHEMA["baseline"]["columns"])
_feature_elimination = _load_variant(
    "feature_elimination", "fe", FEATURE_SCHEMA["feature_elimination"]["columns"]
)


def predict(input_data: PredictionInput) -> dict:
    raw = input_data.to_raw_dict()
    return {
        "feature_elimination": _feature_elimination.predict(raw),
        "baseline": _baseline.predict(raw),
    }
