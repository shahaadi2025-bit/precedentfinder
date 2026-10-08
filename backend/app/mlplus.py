"""ML diagnostics: honest model comparison, permutation importance, interval coverage, learning curve, worst misses, similar deals."""
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from . import ml

def _pre(): return ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["sector", "value_bucket"])], remainder="passthrough")
def _split(df): return train_test_split(df[ml.FEATS], df["premium"], test_size=0.25, random_state=42)

def model_compare(df):
    X, y = df[ml.FEATS], df["premium"]; cv = KFold(5, shuffle=True, random_state=42); out = []
    for name, m in {"mean baseline": DummyRegressor(), "ridge": Ridge(1.0), "random forest": RandomForestRegressor(200, min_samples_leaf=2, random_state=42), "gradient boosting": GradientBoostingRegressor(random_state=42)}.items():
        s = -cross_val_score(Pipeline([("pre", _pre()), ("m", m)]), X, y, cv=cv, scoring="neg_mean_absolute_error"); out.append({"model": name, "cv_mae": round(float(s.mean()), 2), "cv_std": round(float(s.std()), 2)})
    base = next(r["cv_mae"] for r in out if r["model"] == "mean baseline")
    for r in out: r["beats_baseline"] = r["cv_mae"] < base
    return sorted(out, key=lambda r: r["cv_mae"])

def permutation_report(df):
    Xtr, Xte, ytr, yte = _split(df); p = ml._pipe().fit(Xtr, ytr)
    r = permutation_importance(p, Xte, yte, n_repeats=20, random_state=0, scoring="neg_mean_absolute_error")
    return {c: round(float(v), 3) for c, v in sorted(zip(ml.FEATS, r.importances_mean), key=lambda x: -x[1])}

def _tree_preds(p, X): return np.array([t.predict(p.named_steps["pre"].transform(X)) for t in p.named_steps["rf"].estimators_])
def interval_coverage(df, lo=10, hi=90):
    """Share of held-out premiums inside the tree-spread band. A true 80% interval would cover ~80%; tree spread usually covers far less."""
    Xtr, Xte, ytr, yte = _split(df); p = ml._pipe().fit(Xtr, ytr); tp = _tree_preds(p, Xte)
    l, h = np.percentile(tp, lo, axis=0), np.percentile(tp, hi, axis=0)
    return {"coverage_pct": round(float(100 * np.mean((yte.values >= l) & (yte.values <= h))), 1), "nominal_pct": hi - lo, "n_test": int(len(yte))}

def learning_curve(df, fracs=(0.4, 0.6, 0.8, 1.0)):
    Xtr, Xte, ytr, yte = _split(df); out = []
    for f in fracs:
        k = max(5, int(len(Xtr) * f)); p = ml._pipe().fit(Xtr.iloc[:k], ytr.iloc[:k]); out.append({"n_train": k, "test_mae": round(float(mean_absolute_error(yte, p.predict(Xte))), 2)})
    return out

def worst_misses(df, k=5):
    Xtr, Xte, ytr, yte = _split(df); p = ml._pipe().fit(Xtr, ytr); err = np.abs(p.predict(Xte) - yte.values); idx = np.argsort(-err)[:k]
    return [{"target": df.loc[yte.index[i], "target"] if "target" in df else None, "actual": float(yte.values[i]), "predicted": round(float(p.predict(Xte)[i]), 1), "abs_error": round(float(err[i]), 1)} for i in idx]

def similar_deals(rows_, sector, year, k=5):
    sc = lambda r: (0.0 if r["sector"] == sector else 1.0) + abs(int(str(r["ann_date"])[:4]) - year) / 5
    return sorted([r for r in rows_ if r.get("premium") is not None and str(r.get("ann_date"))[:4].isdigit()], key=sc)[:k]

def diagnostics(df):
    if len(df) < ml.MIN_ROWS: return {"available": False, "reason": f"Only {len(df)} usable rows (need >= {ml.MIN_ROWS})."}
    return {"available": True, "n": len(df), "model_comparison": model_compare(df), "permutation_importance_mae_increase": permutation_report(df), "interval_coverage": interval_coverage(df),
            "learning_curve": learning_curve(df), "worst_misses": worst_misses(df), "reading_guide": "Lower MAE is better. If no model beats the baseline, the features carry little signal at this sample size."}
