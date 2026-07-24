"""
Generates a synthetic Tanzania mobile-money / bank transaction dataset and
trains two models used by the recommendation engine:

  1. RandomForestClassifier  -> predicts probability of transaction SUCCESS
                                 for a given platform + transaction context.
  2. GradientBoostingClassifier -> predicts probability of the transaction
                                 being FLAGGED as suspicious/fraud-risk
                                 (kept low-weight, mirrors the "fraud
                                 detection model" mentioned in the project).

Run this once (or via main.py at startup if models don't exist yet):
    python train_model.py
"""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from platforms import PLATFORMS, TRANSACTION_TYPES, LOCATIONS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
os.makedirs(DATA_DIR, exist_ok=True)

N_ROWS = 20500
RNG = np.random.default_rng(42)


def generate_dataset():
    platform_names = list(PLATFORMS.keys())
    rows = []
    for _ in range(N_ROWS):
        platform = RNG.choice(platform_names)
        cfg = PLATFORMS[platform]
        amount = float(np.round(RNG.lognormal(mean=10.5, sigma=1.2), -2))
        amount = min(max(amount, 500), 15_000_000)
        ttype = RNG.choice(TRANSACTION_TYPES)
        location = RNG.choice(LOCATIONS)
        hour = int(RNG.integers(0, 24))
        is_peak = 1 if hour in (7, 8, 12, 13, 17, 18, 19, 20) else 0
        is_urban = 1 if location in ("Dar es Salaam", "Arusha", "Mwanza") else 0

        # success probability driven by baseline platform reliability,
        # degraded by peak congestion and very large amounts
        base = cfg["base_success_rate"] / 100
        congestion_penalty = 0.05 if is_peak else 0.0
        size_penalty = 0.03 if amount > 5_000_000 else 0.0
        prob_success = np.clip(base - congestion_penalty - size_penalty + RNG.normal(0, 0.02), 0.5, 0.999)
        success = RNG.random() < prob_success

        # fraud-risk signal: rare, correlated with very large + odd-hour transactions
        fraud_risk_prob = 0.01 + (0.05 if amount > 3_000_000 and hour in (0, 1, 2, 3) else 0)
        flagged = RNG.random() < fraud_risk_prob

        fee = round(np.clip(amount * cfg["fee_percent"], cfg["min_fee"], cfg["max_fee"]))
        speed = cfg["base_speed_seconds"] + (RNG.integers(0, 8) if is_peak else RNG.integers(0, 3))

        rows.append({
            "platform": platform,
            "category": cfg["category"],
            "amount": amount,
            "transaction_type": ttype,
            "location": location,
            "hour": hour,
            "is_peak": is_peak,
            "is_urban": is_urban,
            "fee": fee,
            "speed_seconds": speed,
            "success": int(success),
            "flagged": int(flagged),
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "synthetic_transactions.csv"), index=False)
    return df


def train_models(df: pd.DataFrame):
    le_platform = LabelEncoder().fit(df["platform"])
    le_type = LabelEncoder().fit(df["transaction_type"])
    le_location = LabelEncoder().fit(df["location"])
    le_category = LabelEncoder().fit(df["category"])

    features = pd.DataFrame({
        "platform_enc": le_platform.transform(df["platform"]),
        "category_enc": le_category.transform(df["category"]),
        "amount": df["amount"],
        "type_enc": le_type.transform(df["transaction_type"]),
        "location_enc": le_location.transform(df["location"]),
        "hour": df["hour"],
        "is_peak": df["is_peak"],
        "is_urban": df["is_urban"],
    })

    # --- Random Forest: predicts SUCCESS probability ---
    X_train, X_test, y_train, y_test = train_test_split(
        features, df["success"], test_size=0.2, random_state=42, stratify=df["success"]
    )
   rf = RandomForestClassifier(n_estimators=60, max_depth=8, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_pred)
    rf_f1 = f1_score(y_test, rf_pred)
    print(f"[RandomForest - success prediction] accuracy={rf_acc:.3f} f1={rf_f1:.3f}")

    # --- Gradient Boosting: predicts FRAUD/RISK flag ---
    Xf_train, Xf_test, yf_train, yf_test = train_test_split(
        features, df["flagged"], test_size=0.2, random_state=42, stratify=df["flagged"]
    )
   gb = GradientBoostingClassifier(n_estimators=80, max_depth=3, learning_rate=0.1, random_state=42)
    gb.fit(Xf_train, yf_train)
    gb_pred = gb.predict(Xf_test)
    gb_acc = accuracy_score(yf_test, gb_pred)
    gb_f1 = f1_score(yf_test, gb_pred, zero_division=0)
    print(f"[GradientBoosting - fraud-risk flag] accuracy={gb_acc:.3f} f1={gb_f1:.3f}")

    bundle = {
        "rf_model": rf,
        "gb_model": gb,
        "le_platform": le_platform,
        "le_type": le_type,
        "le_location": le_location,
        "le_category": le_category,
        "feature_columns": list(features.columns),
        "metrics": {"rf_accuracy": rf_acc, "rf_f1": rf_f1, "gb_accuracy": gb_acc, "gb_f1": gb_f1},
    }
    joblib.dump(bundle, BUNDLE_PATH, compress=3)
    print("Saved model bundle to model_bundle.pkl")


if __name__ == "__main__":
    print(f"Generating {N_ROWS} synthetic transactions...")
    dataset = generate_dataset()
    print("Training models...")
    train_models(dataset)
    print("Done.")
