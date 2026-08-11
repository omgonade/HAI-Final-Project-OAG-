import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from model import FEATURE_SCHEMA, METRICS, PredictionInput, UnknownCategoryError, predict

app = FastAPI(title="Adult Census Income Predictor API")

default_origins = "http://localhost:3000,http://127.0.0.1:3000"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_CARD = {
    "task": "Predicts whether a person's annual income is above or below $50K, "
            "based on the 1994 US Census 'Adult' dataset.",
    "served_model": "Feature Elimination (sex, relationship, and marital-status "
                     "dropped from the inputs) — the best fairness/accuracy tradeoff "
                     "found in training. The unmitigated baseline model's prediction "
                     "is also returned alongside it for comparison.",
    "training_data": "48,842 rows from the 1994 US Census Adult dataset "
                      "(UCI ML Repository), combined train+test split, rows with "
                      "missing values dropped.",
    "scope": [
        "This is a demonstration model for a fairness/bias analysis coursework "
        "project, not a production income-prediction system.",
        "Predictions reflect patterns in 1994 US labor-market data, including "
        "historical wage gaps by sex and race baked into the income labels "
        "themselves — not a current or universal reflection of income potential.",
        "The model predicts an income bracket correlated with the input features; "
        "it makes no causal claim about why a person earns what they earn, and "
        "should never be used to make real decisions about a real person "
        "(hiring, lending, etc).",
    ],
    "known_bias_sources": [
        "Sampling bias: ~2:1 male-to-female, ~85% White in the training data — "
        "not representative of the general population.",
        "Historical/label bias: the income label reflects real 1994 wage gaps by "
        "sex and race, so bias is present in the ground truth itself.",
        "Measurement bias: features like hours-per-week differ systematically by "
        "sex, encoding historical labor patterns.",
        "Proxy bias: relationship status (e.g. Husband/Wife) strongly correlates "
        "with sex, so dropping sex alone does not remove that signal — this is "
        "why relationship and marital-status are also dropped in the served model.",
    ],
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metadata")
def metadata():
    return MODEL_CARD


@app.get("/metrics")
def metrics():
    return METRICS


@app.get("/feature-schema")
def feature_schema():
    return FEATURE_SCHEMA


@app.post("/predict")
def predict_endpoint(input_data: PredictionInput):
    try:
        return predict(input_data)
    except UnknownCategoryError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown value '{e.value}' for '{e.column}'. Allowed: {e.allowed}",
        )
