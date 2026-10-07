"""Per-field precision/recall vs. a hand-labeled CSV.
labels.csv columns: adsh,acquirer,ann_date,premium,deal_value_musd,multiple  (leave blank where the filing states nothing)
Usage: python scripts/eval_accuracy.py labels.csv"""
import sys, csv, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.db import rows
FIELDS = {"acquirer": "acquirer", "ann_date": "ann_date", "premium": "premium", "deal_value_musd": "deal_value_musd", "multiple": "multiple"}
def eq(a, b):
    try: return abs(float(a) - float(b)) < 0.06
    except (TypeError, ValueError): return str(a).strip().lower() == str(b).strip().lower()
pred = {r["adsh"]: r for r in rows("SELECT * FROM deals")}
lab = [l for l in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if (l.get("labeled") or "y").strip().lower() == "y"]   # only rows you marked labeled=Y
print(f"{'field':18}{'precision':>10}{'recall':>8}   (tp/pred, tp/labeled)")
for f in FIELDS:
    tp = npred = nlab = 0
    for l in lab:
        p = pred.get(l["adsh"], {}); pv, lv = p.get(f), (l.get(f) or "").strip()
        if pv not in (None, ""): npred += 1
        if lv: nlab += 1
        if pv not in (None, "") and lv and eq(pv, lv): tp += 1
    print(f"{f:18}{(tp/npred if npred else 0):>10.2f}{(tp/nlab if nlab else 0):>8.2f}   ({tp}/{npred}, {tp}/{nlab})")
print(f"filings labeled: {len(lab)}; extracted as deals: {sum(1 for l in lab if l['adsh'] in pred)}; unparsed: {len(rows('SELECT adsh FROM unparsed'))}")
