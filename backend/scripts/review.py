"""Show the source sentences behind every extracted field so you can verify against the filing, and write a labeling template.
Usage: python scripts/review.py [--n 25]    -> prints evidence, writes labels_template.csv
Fill the label columns from the FILING (not from the extracted values), set labeled=Y, then run: python scripts/eval_accuracy.py labels_template.csv"""
import sys, csv, argparse, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.config import TEXTS
from app.db import rows
from app.edgar import focus_from_text
from app.extractor import extract, _clean
ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=25); a = ap.parse_args()
out = []
for d in rows("SELECT * FROM deals ORDER BY confidence DESC, ann_date DESC LIMIT ?", (a.n,)):
    f = TEXTS / f"{d['adsh']}.txt"
    if not f.exists(): continue
    r = extract(focus_from_text(f.read_text(encoding="utf-8")), d["target"]); ev = r["evidence"]
    print("=" * 100); print(f"{d['target']}  [{d['confidence']}]  {d['url']}")
    print(f"  ACQUIRER: {r['acquirer']}  ({r['acq_rule']})\n    ...{(ev['acquirer'] or '')[-230:]}")
    print(f"  DATE: {r['date']}  ({r['date_rule']})\n    ...{(ev['date'] or '')[-230:]}")
    print(f"  PREMIUM: {r['premium']} ({r['premium_ref']}); all={r['all_premiums']}\n    ...{(ev['premium'] or '')[-230:]}")
    out.append({"adsh": d["adsh"], "target": d["target"], "url": d["url"], "acquirer": "", "ann_date": "", "premium": "", "deal_value_musd": "", "multiple": "", "labeled": "",
                "x_acquirer": r["acquirer"], "x_date": r["date"], "x_premium": r["premium"]})
with open("labels_template.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"\nwrote labels_template.csv with {len(out)} rows (label columns blank; x_* columns are what the extractor found)")
