"""Deal Analyzer: two companies + assumptions -> scenarios (deterministic math), premium view (ML + precedent comps),
and an optional RAG+LLM narrative whose numbers are cross-checked against the computed facts."""
import datetime as dt
import numpy as np
from . import dealmath, edgar, features, ml, sec_facts, valuation
from .config import ENABLE_RAG
from .db import rows

DISCLAIMER = ("Illustrative analysis from public data and your assumptions. Not investment advice. Simplifications: cash funded by new debt, "
              "no fees, no purchase-accounting adjustments, flat tax rate; premium views come from a small precedent sample.")

def _company(q):
    best, cands = sec_facts.resolve(q)
    fin = sec_facts.financials(best["cik_str"])
    return {"query": q, "name": best["title"], "ticker": best["ticker"], "cik": int(best["cik_str"]), "fin": fin,
            "other_matches": [f"{c['title']} ({c['ticker']})" for c in cands[1:4]]}

def _need(fin, keys, who):
    miss = [k for k in keys if fin.get(k) in (None, 0)]
    if miss: raise ValueError(f"SEC XBRL data for {who} is missing {', '.join(miss)} (common for banks, foreign filers, or unusual tags). Can't run the math without it.")

def comps(sector):
    base = ("SELECT target, acquirer, ann_date, premium, deal_value_musd FROM deals WHERE premium IS NOT NULL AND premium_ref='spot_close' "
            "AND premium BETWEEN 0 AND 100 AND flags NOT LIKE '%premium_outlier%'")
    r = rows(base + " AND sector=?", (sector,)); scope = "same sector"
    if len(r) < 5: r = rows(base); scope = "all sectors (too few in this sector)"
    v = [x["premium"] for x in r]
    if not v: return {"n": 0, "scope": scope}
    p = lambda q: round(float(np.percentile(v, q)), 1)
    return {"n": len(v), "scope": scope, "p25": p(25), "median": p(50), "p75": p(75), "min": min(v), "max": max(v),
            "recent": sorted(r, key=lambda x: x["ann_date"], reverse=True)[:6]}

def premium_view(sector, equity_at_ref, user_premium):
    c = comps(sector); mlp = None
    try: mlp = ml.predict(sector, equity_at_ref, dt.date.today().year)
    except Exception: mlp = None
    if mlp: pts, src = [mlp["low_p10"], mlp["point"], mlp["high_p90"]], "ML (P10 / point / P90)"
    elif c["n"] >= 3: pts, src = [c["p25"], c["median"], c["p75"]], "precedent quartiles"
    else: pts, src = [20.0, 30.0, 40.0], "generic placeholder (no precedent data)"
    if user_premium is not None: pts = pts + [user_premium]
    pts = sorted({round(p, 1) for p in pts})
    return {"ml": mlp, "comps": c, "points": pts, "source": src, "base": user_premium if user_premium is not None else (mlp["point"] if mlp else (c.get("median", 30.0)))}

def _known(result):
    k = {"pct": [], "multiple": [], "usd_m": [], "usd": []}
    def add(sc):
        for key, kind in (("premium_pct", "pct"), ("eps_accretion_pct", "pct"), ("target_holders_pct", "pct"), ("size_vs_acq_mcap_pct", "pct"),
                          ("ev_revenue", "multiple"), ("ev_ebitda", "multiple"), ("offer_pe", "multiple"), ("pf_net_debt_ebitda", "multiple"),
                          ("equity_value_m", "usd_m"), ("ev_m", "usd_m"), ("cash_part_m", "usd_m"), ("stock_part_m", "usd_m"), ("breakeven_synergies_m", "usd_m"),
                          ("cash_needs_new_debt_m", "usd_m"), ("offer_price", "usd"), ("eps_standalone", "usd"), ("eps_pro_forma", "usd")):
            if sc.get(key) is None: continue
            k[kind].append(sc[key])
            if kind == "pct": k[kind].append(abs(sc[key]))      # LLM text may say "dilution of 14.3%" for -14.3
    for sc in [result["base"]] + result["grid"]: add(sc)
    k["pct"] += [result["assumptions"]["pct_cash"] * 100, result["assumptions"]["tax_rate"] * 100, result["assumptions"]["cost_of_debt"] * 100] + result["premium_view"]["points"]
    cm = result["premium_view"]["comps"]; k["pct"] += [cm[x] for x in ("p25", "median", "p75", "min", "max") if x in cm]
    for who in ("acquirer", "target"):
        f = result[who]["fin"]; k["usd_m"] += [f[x] for x in ("revenue_m", "net_income_m", "ebitda_m", "cash_m", "debt_m") if f.get(x) is not None]
    k["usd"] += [result["inputs"]["acquirer_price"], result["inputs"]["target_price"]]
    k["usd_m"].append(result["assumptions"]["synergies_musd"])
    return k

def facts_text(r):
    b, a, t = r["base"], r["acquirer"], r["target"]; f = lambda x, n=1: "n/a" if x is None else f"{x:,.{n}f}"
    L = [f"Acquirer: {a['name']} ({a['ticker']}); price ${f(r['inputs']['acquirer_price'],2)}; net income ${f(a['fin']['net_income_m'])} million; revenue ${f(a['fin']['revenue_m'])} million.",
         f"Target: {t['name']} ({t['ticker']}); sector {r['sector']}; price ${f(r['inputs']['target_price'],2)}; net income ${f(t['fin']['net_income_m'])} million; revenue ${f(t['fin']['revenue_m'])} million; EBITDA ${f(t['fin']['ebitda_m'])} million.",
         f"Base case: {f(b['premium_pct'])}% premium, offer ${f(b['offer_price'],2)} per share, equity value ${f(b['equity_value_m'])} million, enterprise value ${f(b['ev_m'])} million, "
         f"{f(b['pct_cash']*100,0)}% cash, EV/Revenue {f(b['ev_revenue'],2)}x, EV/EBITDA {f(b['ev_ebitda'],2)}x, deal is {f(b['size_vs_acq_mcap_pct'])}% of acquirer market cap.",
         f"EPS effect in base case: standalone ${f(b['eps_standalone'],2)}, pro forma ${f(b['eps_pro_forma'],2)}, accretion {f(b['eps_accretion_pct'])}%, "
         f"target holders own {f(b['target_holders_pct'])}% of combined company; pre-tax synergies to break even ${f(b['breakeven_synergies_m'])} million.",
         f"Premium view ({r['premium_view']['source']}): " + ", ".join(f"{p}%" for p in r["premium_view"]["points"]) + "."]
    c = r["premium_view"]["comps"]
    if c.get("n"): L.append(f"Precedent premiums ({c['scope']}, n={c['n']}): median {c['median']}%, quartiles {c['p25']}% to {c['p75']}%.")
    return "\n".join(L)

def narrative(r):
    if not ENABLE_RAG: return {"available": False, "reason": "RAG/LLM disabled on this host (ENABLE_RAG=false). Run the backend locally with Ollama."}
    try:
        from . import rag
        docs, metas = [], []
        for q in (f"{r['sector']} merger strategic rationale synergies benefits to the acquirer", "premium paid to stockholders and why the board considered it fair"):
            d, m = rag.retrieve_context(q, 3); docs += d; metas += m
        ctx = "\n\n".join(f"[{i+1}] ({m['target']}) {d[:900]}" for i, (d, m) in enumerate(zip(docs, metas)))
        facts = facts_text(r)
        prompt = ("You are an M&A analyst assistant. Write a concise analysis (max 300 words) of the hypothetical deal below using ONLY the FACTS for numbers "
                  "(quote them exactly; never invent figures) and the PRECEDENT EXCERPTS for qualitative context. Sections: 1) Possible strategic benefits (label as hypotheses), "
                  "2) What the valuation and EPS math says, 3) Financing and risks, 4) What to verify next. Do not give investment advice.\n\n"
                  f"FACTS:\n{facts}\n\nPRECEDENT EXCERPTS (from other companies' merger filings):\n{ctx}\n\nANALYSIS:")
        text = rag.generate(prompt)
        checks = rag.check_numbers(text, facts + "\n" + ctx, _known(r))
        return {"available": True, "text": text, "number_checks": checks, "any_flagged": any(c["flag"] for c in checks),
                "sources": [{"target": m["target"], "excerpt": d[:240]} for d, m in zip(docs, metas)], "model_note": "Small local models can be wrong; the badges show which numbers match the computed facts."}
    except Exception as e:
        return {"available": False, "reason": f"Narrative unavailable ({type(e).__name__}: {e}). Is Ollama running and /index done?"}

def run(req, with_narrative=True):
    a, t = _company(req["acquirer"]), _company(req["target"])
    _need(a["fin"], ["shares_m", "net_income_m"], a["name"]); _need(t["fin"], ["shares_m"], t["name"])
    if t["fin"].get("net_income_m") is None: raise ValueError(f"SEC XBRL data for {t['name']} is missing net_income_m.")
    for k in ("acquirer_price", "target_price"):
        if not req.get(k) or req[k] <= 0: raise ValueError(f"{k} must be a positive number (current share price).")
    sic, _ = edgar.sic_for(t["cik"]); sector = edgar.sector_from_sic(sic)
    A = {"price": req["acquirer_price"], "shares_m": a["fin"]["shares_m"], "net_income_m": a["fin"]["net_income_m"], "cash_m": a["fin"].get("cash_m") or 0,
         "debt_m": a["fin"].get("debt_m") or 0, "ebitda_m": a["fin"].get("ebitda_m"), "revenue_m": a["fin"].get("revenue_m")}
    T = {"price": req["target_price"], "shares_m": t["fin"]["shares_m"], "net_income_m": t["fin"]["net_income_m"], "revenue_m": t["fin"].get("revenue_m"),
         "ebitda_m": t["fin"].get("ebitda_m"), "cash_m": t["fin"].get("cash_m") or 0, "debt_m": t["fin"].get("debt_m") or 0}
    warns = []
    if str(sic).startswith("60") or str(sic).startswith("61"): warns.append("Target looks like a bank/lender: EV/EBITDA and debt-based metrics are not meaningful; focus on P/E and premium.")
    if t["fin"].get("ebitda_m") is None: warns.append("No EBITDA available for the target (operating income or D&A tag missing); EV/EBITDA skipped.")
    if t["fin"].get("revenue_m") is None: warns.append("No revenue tag found for the target; EV/Revenue skipped.")
    if A["net_income_m"] <= 0: warns.append("Acquirer net income is not positive, so EPS accretion/dilution is not defined.")
    if T["net_income_m"] <= 0: warns.append("Target net income is not positive; offer P/E is n/a and the target is dilutive to earnings before synergies.")
    for who in (a, t):
        if not who["fin"].get("sources"): warns.append(f"No annual XBRL facts found for {who['name']}.")
    warns.append(f"Financials are the latest annual 10-K figures from SEC XBRL, which may be stale vs. today's prices (shares from the cover page). Verify before relying on them.")
    ref_equity = T["price"] * 1.3 * T["shares_m"]
    pv = premium_view(sector, ref_equity, req.get("premium_pct"))
    asm = {"pct_cash": req.get("pct_cash", 50) / 100, "synergies_musd": req.get("synergies_musd", 0.0),
           "tax_rate": req.get("tax_rate", 25) / 100, "cost_of_debt": req.get("cost_of_debt", 6) / 100}
    kw = {"tax_rate": asm["tax_rate"], "cost_of_debt": asm["cost_of_debt"]}
    mixes = sorted({0.0, 0.5, 1.0, round(asm["pct_cash"], 2)})
    base = dealmath.scenario(A, T, pv["base"], asm["pct_cash"], asm["synergies_musd"], **kw)
    grid = dealmath.grid(A, T, pv["points"], mixes, asm["synergies_musd"], **kw)
    if base["cash_needs_new_debt_m"] > 0: warns.append(f"Base case cash portion exceeds the acquirer's cash by ${base['cash_needs_new_debt_m']:,.0f}M, i.e. needs new borrowing.")
    syn0 = asm["synergies_musd"]; be = base["breakeven_synergies_m"] or 0
    sens = features.sensitivity(A, T, pv["base"], asm["pct_cash"], sorted({0.0, syn0, max(0.0, be) * 0.5, max(0.0, be), max(0.0, be) * 2}), **kw)
    coh = dealmath.scenario(A, T, pv["base"], min(1.0, A["cash_m"] / base["equity_value_m"]) if base["equity_value_m"] else 0.0, syn0, **kw)
    cvals = [x["premium"] for x in rows("SELECT premium FROM deals WHERE premium_ref='spot_close' AND premium BETWEEN 0 AND 100")]
    r = {"acquirer": a, "target": t, "sector": sector, "inputs": {"acquirer_price": req["acquirer_price"], "target_price": req["target_price"], "user_premium": req.get("premium_pct")},
         "assumptions": asm, "premium_view": pv, "base": base, "grid": grid, "warnings": warns, "disclaimer": DISCLAIMER,
         "breakeven_premium": features.breakeven_premium(A, T, asm["pct_cash"], syn0, **kw), "sensitivity": sens, "cash_on_hand_case": coh,
         "premium_percentile": features.percentile_rank(pv["base"], cvals), "risk_flags": features.risk_flags(base, T["net_income_m"], pv),
         "football": features.football(pv, req.get("premium_pct")),
         "advanced": valuation.advanced(A, T, pv["base"], asm["pct_cash"], syn0, asm["tax_rate"], asm["cost_of_debt"])}
    r["narrative"] = narrative(r) if with_narrative else None
    return r
