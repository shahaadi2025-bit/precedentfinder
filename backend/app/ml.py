"""Stage 3: premium regressor with honest evaluation."""
import json, numpy as np, pandas as pd, joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from .config import MODEL_PATH, METRICS_PATH
from .db import rows
MIN_ROWS = 15
BUCKETS = [(0, 250, "<$250M"), (250, 1000, "$250M-1B"), (1000, 5000, "$1-5B"), (5000, 1e12, ">$5B")]
def bucket(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "unknown"
    return next(n for lo, hi, n in BUCKETS if lo <= v < hi)
def frame():
    df = pd.DataFrame(rows("SELECT * FROM deals WHERE premium IS NOT NULL AND premium BETWEEN 0 AND 100 AND premium_ref IN ('spot_close') AND flags NOT LIKE '%premium_outlier%' AND flags NOT LIKE '%date_after_filing%'"))
    if df.empty: return df
    df["year"] = pd.to_datetime(df["ann_date"], errors="coerce").dt.year
    df["value_bucket"] = df["deal_value_musd"].map(bucket)
    return df.dropna(subset=["year"])
FEATS = ["sector", "value_bucket", "year"]
def _pipe():
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["sector", "value_bucket"])], remainder="passthrough")
    return Pipeline([("pre", pre), ("rf", RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42))])
def train():
    df = frame()
    if len(df) < MIN_ROWS: return {"trained": False, "reason": f"Only {len(df)} usable rows (need >= {MIN_ROWS}). Ingest more filings."}
    X, y = df[FEATS], df["premium"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)
    p = _pipe().fit(Xtr, ytr); pred = p.predict(Xte)
    base = np.full(len(yte), ytr.mean())
    cv = -cross_val_score(_pipe(), X, y, cv=KFold(5, shuffle=True, random_state=42), scoring="neg_mean_absolute_error")
    sect = pd.DataFrame({"sector": Xte["sector"].values, "abs_err": np.abs(pred - yte.values)}).groupby("sector")["abs_err"].agg(["mean", "count"])
    metrics = {"trained": True, "n_total": len(df), "n_train": len(ytr), "n_test": len(yte),
        "test_mae": round(mean_absolute_error(yte, pred), 2), "test_r2": round(r2_score(yte, pred), 3),
        "baseline_mean_mae": round(mean_absolute_error(yte, base), 2), "cv_mae_mean": round(cv.mean(), 2), "cv_mae_std": round(cv.std(), 2),
        "beats_baseline": bool(mean_absolute_error(yte, pred) < mean_absolute_error(yte, base)),
        "per_sector_test_mae": {k: {"mae": round(v["mean"], 1), "n": int(v["count"])} for k, v in sect.iterrows()},
        "feature_importance": importances(p),
        "caveat": "Small historical sample; premiums vary widely with deal-specific factors not modeled. Treat as a rough, data-driven estimate."}
    p.fit(X, y); joblib.dump(p, MODEL_PATH); METRICS_PATH.write_text(json.dumps(metrics, indent=2)); return metrics
def importances(p):
    names = p.named_steps["pre"].get_feature_names_out(); imp = p.named_steps["rf"].feature_importances_; agg = {}
    for n, v in zip(names, imp):
        key = n.split("__")[1]; key = "sector" if key.startswith("sector") else "value_bucket" if key.startswith("value_bucket") else key
        agg[key] = agg.get(key, 0) + float(v)
    return {k: round(v, 3) for k, v in sorted(agg.items(), key=lambda kv: -kv[1])}
def metrics(): return json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {"trained": False}
def predict(sector, deal_value_musd, year):
    if not MODEL_PATH.exists(): raise RuntimeError("Model not trained")
    p = joblib.load(MODEL_PATH); x = pd.DataFrame([{"sector": sector, "value_bucket": bucket(deal_value_musd), "year": year}])
    trees = np.array([t.predict(p.named_steps["pre"].transform(x)) for t in p.named_steps["rf"].estimators_]).ravel()
    return {"point": round(float(trees.mean()), 1), "low_p10": round(float(np.percentile(trees, 10)), 1), "high_p90": round(float(np.percentile(trees, 90)), 1),
            "feature_importance": importances(p), "n_train": metrics().get("n_total"), "test_mae": metrics().get("test_mae"),
            "disclaimer": "Data-driven estimate from a limited historical sample, not a guaranteed outcome."}
