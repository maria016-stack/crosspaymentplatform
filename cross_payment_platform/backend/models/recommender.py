"""
Recommendation engine used by the API. Loads the trained Random Forest
(success prediction) + Gradient Boosting (risk-flag) model bundle and
combines it with the PRI (Payment Reliability Index) formula to rank
platforms for a given transaction request.
"""
import os
import sys
import pandas as pd
import joblib
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from platforms import PLATFORMS, SMART_ROUTING_THRESHOLD, TRANSACTION_TYPE_CATEGORIES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_PATH = os.path.join(HERE, "model_bundle.pkl")

_bundle = None


def _ensure_trained():
    global _bundle
    if _bundle is not None:
        return _bundle
    if not os.path.exists(BUNDLE_PATH):
        from . import train_model as tm  # local import to avoid circular cost at import time
        df = tm.generate_dataset()
        tm.train_models(df)
    _bundle = joblib.load(BUNDLE_PATH)
    return _bundle


def _safe_encode(le, value):
    """Encode a value, falling back to the first known class if unseen."""
    try:
        return le.transform([value])[0]
    except ValueError:
        return le.transform([le.classes_[0]])[0]


def _speed_score(seconds: float) -> float:
    # 0-100, faster = higher. 10s -> ~100, 60s -> ~0
    return max(0.0, min(100.0, 100 - (seconds - 10) * 1.8))


def _cost_score(fee: float, amount: float) -> float:
    ratio = fee / max(amount, 1)
    # lower fee ratio -> higher score
    return max(0.0, min(100.0, 100 - ratio * 4000))


def recommend(amount: float, transaction_type: str, location: str, hour: int = None):
    bundle = _ensure_trained()
    rf = bundle["rf_model"]
    le_platform = bundle["le_platform"]
    le_type = bundle["le_type"]
    le_location = bundle["le_location"]
    le_category = bundle["le_category"]
    feature_columns = bundle["feature_columns"]

    if hour is None:
        hour = datetime.now().hour
    is_peak = 1 if hour in (7, 8, 12, 13, 17, 18, 19, 20) else 0
    is_urban = 1 if location in ("Dar es Salaam", "Arusha", "Mwanza") else 0

    candidates = list(PLATFORMS.items())

    # Restrict candidates to platforms that actually serve the selected
    # transaction type (e.g. "Bank Transfer" -> bank platforms only). This is
    # what stops mobile-money platforms like M-PESA from being recommended
    # when the user explicitly asked for a bank transfer.
    allowed_categories = TRANSACTION_TYPE_CATEGORIES.get(transaction_type)
    if allowed_categories:
        type_filtered = [(n, c) for n, c in candidates if c["category"] in allowed_categories]
        if type_filtered:  # keep the filter only if it doesn't wipe out every option
            candidates = type_filtered

    # Smart routing: large transactions auto-route to bank/aggregator platforms
    if amount > SMART_ROUTING_THRESHOLD:
        size_filtered = [(n, c) for n, c in candidates if c["category"] in ("bank", "aggregator")]
        if size_filtered:
            candidates = size_filtered

    rows = []
    for name, cfg in candidates:
        fee = round(min(max(amount * cfg["fee_percent"], cfg["min_fee"]), cfg["max_fee"]))
        speed = cfg["base_speed_seconds"] + (4 if is_peak else 0)

        feat = pd.DataFrame([{
            "platform_enc": _safe_encode(le_platform, name),
            "category_enc": _safe_encode(le_category, cfg["category"]),
            "amount": amount,
            "type_enc": _safe_encode(le_type, transaction_type),
            "location_enc": _safe_encode(le_location, location),
            "hour": hour,
            "is_peak": is_peak,
            "is_urban": is_urban,
        }])[feature_columns]

        success_prob = float(rf.predict_proba(feat)[0][1]) * 100
        efficiency = _cost_score(fee, amount) * 0.5 + success_prob * 0.5
        speed_sc = _speed_score(speed)
        cost_sc = _cost_score(fee, amount)

        pri = 0.40 * success_prob + 0.30 * efficiency + 0.20 * speed_sc + 0.10 * cost_sc
        pri = round(min(pri, 99.9), 1)

        rows.append({
            "platform": name,
            "network": cfg["network"],
            "category": cfg["category"],
            "pri_score": pri,
            "success_rate": round(success_prob, 1),
            "fee": int(fee),
            "speed_seconds": int(speed),
            "efficiency": round(efficiency, 1),
        })

    rows.sort(key=lambda r: r["pri_score"], reverse=True)
    best = rows[0]
    # naive "savings" estimate vs. the average fee of the other candidates
    avg_other_fee = sum(r["fee"] for r in rows[1:]) / max(len(rows) - 1, 1) if len(rows) > 1 else best["fee"]
    savings = max(0, round(avg_other_fee - best["fee"]))

    return {
        "recommended": best,
        "all_ranked": rows,
        "savings": savings,
        "is_peak": bool(is_peak),
        "smart_routed": amount > SMART_ROUTING_THRESHOLD,
    }
