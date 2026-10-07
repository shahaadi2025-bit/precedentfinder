"""Extra analytics: dataset stats, data quality, exports, saved analyses, and deal-analysis helpers (break-even premium, sensitivity, risk flags, football field, report)."""
import csv, io, json, collections
import numpy as np
from . import dealmath
from .db import conn, rows

OK = "premium_ref='spot_close' AND premium BETWEEN 0 AND 100 AND flags NOT LIKE '%premium_outlier%'"
def _q(v): return {"n": len(v), "median": round(float(np.median(v)), 1), "p25": round(float(np.percentile(v, 25)), 1), "p75": round(float(np.percentile(v, 75)), 1)}

def sector_stats():
    by = collections.defaultdict(list)
    for r in rows(f"SELECT sector, premium FROM deals WHERE {OK}"): by[r["sector"]].append(r["premium"])
    return sorted(({"sector": s, **_q(v)} for s, v in by.items()), key=lambda d: -d["n"])

def trend():
    by = collections.defaultdict(list)
    for r in rows(f"SELECT substr(ann_date,1,4) y, premium FROM deals WHERE {OK}"): by[r["y"]].append(r["premium"])
    return [{"year": y, **_q(v)} for y, v in sorted(by.items())]

def quality():
    d, u = rows("SELECT confidence, premium, acquirer, ann_date, deal_value_musd, flags FROM deals"), rows("SELECT reasons FROM unparsed")
    n = len(d) or 1; flags, why = collections.Counter(), collections.Counter()
    for r in d: flags.update(f.split(":")[0] for f in json.loads(r["flags"] or "[]"))
    for r in u: why.update(set(json.loads(r["reasons"] or "[]")))
    cov = lambda k: round(100 * sum(1 for r in d if r[k] not in (None, "", "None")) / n, 1)
    return {"total_filings": len(d) + len(u), "parsed": len(d), "unparsed": len(u), "parse_rate_pct": round(100 * len(d) / max(1, len(d) + len(u)), 1),
            "confidence": dict(collections.Counter(r["confidence"] for r in d)),
            "coverage_pct": {"premium": cov("premium"), "acquirer": cov("acquirer"), "date": cov("ann_date"), "deal_value": cov("deal_value_musd")},
            "top_flags": flags.most_common(6), "top_reject_reasons": why.most_common(6),
            "note": "Coverage is how often a field was extracted, NOT how often it is correct. Measure correctness with scripts/review.py + eval_accuracy.py."}

def export_csv():
    r = rows("SELECT target, acquirer, ann_date, deal_value_musd, price_per_share, premium, premium_ref, multiple, multiple_type, sector, confidence, flags, url FROM deals ORDER BY ann_date DESC")
    out = io.StringIO()
    if r: w = csv.DictWriter(out, fieldnames=list(r[0].keys())); w.writeheader(); w.writerows(r)
    return out.getvalue()

def save_analysis(title, payload):
    with conn() as c: cur = c.execute("INSERT INTO saved_analyses(title,payload) VALUES(?,?)", (title, json.dumps(payload, default=str))); return cur.lastrowid
def list_analyses(): return rows("SELECT id, ts, title FROM saved_analyses ORDER BY id DESC LIMIT 50")
def get_analysis(i):
    r = rows("SELECT payload FROM saved_analyses WHERE id=?", (i,)); return json.loads(r[0]["payload"]) if r else None
def delete_analysis(i):
    with conn() as c: c.execute("DELETE FROM saved_analyses WHERE id=?", (i,))

# ---- deal-analysis helpers (pure) ----
def breakeven_premium(acq, tgt, pct_cash, syn, **kw):
    """Highest premium (0-300%) at which EPS is still >= standalone. None if dilutive even at 0% or EPS undefined."""
    f = lambda p: dealmath.scenario(acq, tgt, p, pct_cash, syn, **kw)["eps_accretion_pct"]
    if f(0) is None or f(0) < 0: return None
    if f(300) >= 0: return 300.0
    lo, hi = 0.0, 300.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) >= 0: lo = mid
        else: hi = mid
    return round(lo, 1)

def sensitivity(acq, tgt, premium, pct_cash, synergies, **kw):
    return [{"synergies_m": s, "eps_accretion_pct": dealmath.scenario(acq, tgt, premium, pct_cash, s, **kw)["eps_accretion_pct"]} for s in synergies]

def percentile_rank(value, vals):
    return None if not vals else round(100 * sum(1 for v in vals if v <= value) / len(vals), 0)

def risk_flags(base, tgt_ni, pv):
    out, add = [], lambda lvl, t: out.append({"level": lvl, "text": t})
    if base["size_vs_acq_mcap_pct"] > 50: add("high", f"Deal equity value is {base['size_vs_acq_mcap_pct']:.0f}% of the acquirer's market cap (transformational, hard to integrate).")
    elif base["size_vs_acq_mcap_pct"] > 25: add("medium", f"Deal is {base['size_vs_acq_mcap_pct']:.0f}% of acquirer market cap.")
    if base["pf_net_debt_ebitda"] is not None and base["pf_net_debt_ebitda"] > 4: add("high", f"Pro forma net debt/EBITDA of {base['pf_net_debt_ebitda']:.1f}x is high.")
    elif base["pf_net_debt_ebitda"] is not None and base["pf_net_debt_ebitda"] > 3: add("medium", f"Pro forma net debt/EBITDA of {base['pf_net_debt_ebitda']:.1f}x.")
    a = base["eps_accretion_pct"]
    if a is not None and a < -10: add("high", f"EPS dilution of {abs(a):.1f}% before further synergies.")
    elif a is not None and a < 0: add("medium", f"EPS dilution of {abs(a):.1f}%.")
    if base["target_holders_pct"] > 35: add("medium", f"Target holders would own {base['target_holders_pct']:.0f}% of the combined company (governance/control implications).")
    if tgt_ni <= 0: add("medium", "Target is loss-making; value depends on synergies or turnaround.")
    c = pv["comps"]
    if c.get("n") and base["premium_pct"] > c["p75"]: add("medium", f"Premium {base['premium_pct']:.0f}% is above the precedent 75th percentile ({c['p75']}%).")
    if c.get("n", 0) < 8: add("info", f"Only {c.get('n', 0)} precedent premiums behind the premium view; treat as indicative.")
    if base["cash_needs_new_debt_m"] > 0: add("info", f"Cash portion needs ${base['cash_needs_new_debt_m']:,.0f}M of new financing.")
    return out or [{"level": "info", "text": "No rule-based red flags triggered."}]

def football(pv, user_prem):
    f, c = [], pv["comps"]
    if c.get("n"): f += [{"label": "Precedent min-max", "low": c["min"], "high": c["max"]}, {"label": "Precedent IQR", "low": c["p25"], "high": c["p75"]}]
    if pv["ml"]: f.append({"label": "ML P10-P90", "low": pv["ml"]["low_p10"], "high": pv["ml"]["high_p90"]})
    if user_prem is not None: f.append({"label": "Your premium", "low": user_prem, "high": user_prem})
    return f

def report_md(r):
    b, a, t = r["base"], r["acquirer"], r["target"]; g = lambda x, d=1: "n/a" if x is None else f"{x:,.{d}f}"
    L = [f"# Deal analysis: {a['name']} + {t['name']}", "", f"*Sector: {r['sector']}. {r['disclaimer']}*", "", "## Base case",
         f"- Premium {g(b['premium_pct'])}% -> offer ${g(b['offer_price'], 2)}/share; equity value ${g(b['equity_value_m'], 0)}M; EV ${g(b['ev_m'], 0)}M",
         f"- EV/Revenue {g(b['ev_revenue'], 2)}x; EV/EBITDA {g(b['ev_ebitda'], 2)}x; offer P/E {g(b['offer_pe'])}x",
         f"- EPS ${g(b['eps_standalone'], 2)} -> ${g(b['eps_pro_forma'], 2)} ({g(b['eps_accretion_pct'])}%); break-even synergies ${g(b['breakeven_synergies_m'], 0)}M",
         f"- Break-even premium at this mix/synergies: {g(r.get('breakeven_premium'))}%", "", "## Risk flags"] + [f"- [{x['level']}] {x['text']}" for x in r.get("risk_flags", [])]
    L += ["", "## Scenarios", "| Premium | % cash | Equity $M | EPS accretion % |", "|---|---|---|---|"]
    L += [f"| {g(x['premium_pct'])}% | {x['pct_cash']*100:.0f}% | {g(x['equity_value_m'], 0)} | {g(x['eps_accretion_pct'])} |" for x in r["grid"]]
    n = r.get("narrative")
    if n and n.get("available"): L += ["", "## AI analysis (draft, verify numbers)", n["text"]]
    L += ["", "## Warnings"] + [f"- {w}" for w in r["warnings"]]
    return "\n".join(L)

# ---------------- pack 2 ----------------
def acquirers():
    by = collections.defaultdict(list)
    for r in rows("SELECT acquirer, target, premium FROM deals WHERE acquirer IS NOT NULL"): by[r["acquirer"]].append(r)
    out = []
    for a, v in by.items():
        p = [x["premium"] for x in v if x["premium"] is not None and 0 <= x["premium"] <= 100]
        out.append({"acquirer": a, "deals": len(v), "targets": [x["target"] for x in v][:5], "median_premium": round(float(np.median(p)), 1) if p else None})
    return sorted(out, key=lambda d: (-d["deals"], d["acquirer"]))

def histogram(edges=(0, 10, 20, 30, 40, 50, 75, 100)):
    vals = [r["premium"] for r in rows(f"SELECT premium FROM deals WHERE {OK}")]
    counts, _ = np.histogram(vals, bins=list(edges)) if vals else (np.zeros(len(edges) - 1, int), None)
    return [{"bin": f"{edges[i]}-{edges[i+1]}%", "n": int(c)} for i, c in enumerate(counts)]

def forecast():
    t = [x for x in trend() if x["n"] >= 2 and x["year"].isdigit()]
    if len(t) < 3: return {"available": False, "reason": "Need at least 3 years with 2+ premiums each."}
    yrs, med, w = np.array([int(x["year"]) for x in t], float), np.array([x["median"] for x in t]), np.array([x["n"] for x in t], float)
    slope, icpt = np.polyfit(yrs, med, 1, w=np.sqrt(w)); nxt = int(yrs.max()) + 1
    resid = float(np.std(med - (slope * yrs + icpt)))
    return {"available": True, "next_year": nxt, "projected_median": round(float(slope * nxt + icpt), 1), "slope_pts_per_year": round(float(slope), 2), "resid_std": round(resid, 1),
            "note": f"Straight-line fit on {len(t)} yearly medians. With so few points this is a rough trend, not a forecast you should rely on."}

COMPARE_METRICS = [("Premium %", lambda r: r["base"]["premium_pct"]), ("Offer price $", lambda r: r["base"]["offer_price"]), ("Equity value $M", lambda r: r["base"]["equity_value_m"]),
    ("EV $M", lambda r: r["base"]["ev_m"]), ("EV/EBITDA x", lambda r: r["base"]["ev_ebitda"]), ("EPS accretion %", lambda r: r["base"]["eps_accretion_pct"]),
    ("Target owns %", lambda r: r["base"]["target_holders_pct"]), ("Break-even synergies $M", lambda r: r["base"]["breakeven_synergies_m"]), ("Break-even premium %", lambda r: r.get("breakeven_premium"))]
def compare(a, b):
    out = []
    for name, f in COMPARE_METRICS:
        x, y = f(a), f(b); out.append({"metric": name, "a": x, "b": y, "diff": None if x is None or y is None else round(y - x, 2)})
    return out

def parse_stooq(text):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2: raise ValueError("empty price response")
    h, v = lines[0].lower().split(","), lines[1].split(","); row = dict(zip(h, v))
    try: return {"ticker": row["symbol"].split(".")[0].upper(), "close": float(row["close"]), "date": row.get("date")}
    except (KeyError, ValueError): raise ValueError("no price available for that ticker (stooq returned N/D)")
def price(ticker):
    import requests
    r = requests.get(f"https://stooq.com/q/l/?s={ticker.lower()}.us&f=sd2t2ohlcv&h&e=csv", timeout=20); r.raise_for_status()
    return parse_stooq(r.text)

def watch_add(ticker, note=""):
    with conn() as c: c.execute("INSERT OR REPLACE INTO watchlist(ticker,note) VALUES(?,?)", (ticker.upper().strip(), note))
def watch_list(): return rows("SELECT id, ticker, note FROM watchlist ORDER BY ticker")
def watch_del(i):
    with conn() as c: c.execute("DELETE FROM watchlist WHERE id=?", (i,))

def refresh_window(latest_ann_date, today, overlap_days=150):
    """Proxies are filed months after signing, so re-scan from latest agreement date minus an overlap."""
    import datetime as dt
    start = dt.date.fromisoformat(latest_ann_date) - dt.timedelta(days=overlap_days) if latest_ann_date else today - dt.timedelta(days=365)
    return start.isoformat(), today.isoformat()
