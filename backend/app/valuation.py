"""Advanced deal valuation (pure functions, $M). Same simplifications as dealmath, plus optional fees. Illustrative only."""
import numpy as np
from . import dealmath
S = dealmath.scenario
def _acc(a, t, p, c, syn, tax, cod): return S(a, t, p, c, syn, tax, cod)["eps_accretion_pct"]

def premium_paid_m(tgt, premium): return tgt["price"] * premium / 100 * tgt["shares_m"]
def synergy_value_m(syn_pre, tax, discount=0.09, growth=0.02):
    return None if discount <= growth else syn_pre * (1 - tax) / (discount - growth)
def exchange_ratio(offer, acq_price, pct_cash): return offer * (1 - pct_cash) / acq_price

def value_creation(a, t, premium, syn, tax, fees_pct=0.015, discount=0.09, growth=0.02):
    pm = premium_paid_m(t, premium); eq = t["price"] * (1 + premium / 100) * t["shares_m"]; fees = eq * fees_pct; sv = synergy_value_m(syn, tax, discount, growth)
    return {"premium_paid_m": pm, "fees_m": fees, "synergy_value_m": sv, "net_value_created_m": None if sv is None else sv - pm - fees,
            "share_of_synergies_to_target_pct": None if not sv else pm / sv * 100, "payback_years": pm / (syn * (1 - tax)) if syn > 0 else None,
            "assumptions": f"synergies capitalized at {discount*100:.0f}% discount, {growth*100:.0f}% growth; fees {fees_pct*100:.1f}% of equity value"}

def contribution(a, t, holders_pct):
    rows = []
    for name, k in (("Revenue", "revenue_m"), ("EBITDA", "ebitda_m"), ("Net income", "net_income_m")):
        x, y = a.get(k), t.get(k)
        rows.append({"metric": name, "target_pct": None if x is None or y is None or x + y <= 0 or y < 0 else round(y / (x + y) * 100, 1)})
    return {"rows": rows, "target_holders_ownership_pct": round(holders_pct, 1)}

def relative_pe(a, equity_m):
    ape = a["price"] * a["shares_m"] / a["net_income_m"] if a["net_income_m"] > 0 else None
    return {"acquirer_pe": ape, "offer_pe_target": None, "note": "n/a"} if ape is None else {"acquirer_pe": ape, "note": "A stock deal tends to be EPS-accretive when the offer P/E is below the acquirer's P/E."}

def max_cash_at_leverage(a, t, premium, syn, cap=3.5):
    eq = t["price"] * (1 + premium / 100) * t["shares_m"]; pf_e = (a.get("ebitda_m") or 0) + (t.get("ebitda_m") or 0) + syn
    if pf_e <= 0: return {"capacity_m": None, "max_pct_cash": None}
    cap_m = cap * pf_e - ((a.get("debt_m") or 0) + (t.get("debt_m") or 0) - (a.get("cash_m") or 0) - (t.get("cash_m") or 0))
    return {"capacity_m": cap_m, "max_pct_cash": float(min(1.0, max(0.0, cap_m / eq))), "cap_x": cap}

def optimal_mix(a, t, premium, syn, tax, cod, cap=3.5, step=0.05):
    best = None
    for i in range(int(round(1 / step)) + 1):
        c = round(i * step, 4); s = S(a, t, premium, c, syn, tax, cod); lev = s["pf_net_debt_ebitda"]
        if s["eps_accretion_pct"] is None or (lev is not None and lev > cap): continue
        if best is None or s["eps_accretion_pct"] > best["eps_accretion_pct"]: best = {"pct_cash": c, "eps_accretion_pct": s["eps_accretion_pct"], "pf_net_debt_ebitda": lev}
    return best

def monte_carlo(a, t, premium, syn, pct_cash, tax, cod, n=2000, seed=0, prem_sd=8.0):
    rng = np.random.default_rng(seed); out = []
    for p, s in zip(np.clip(rng.normal(premium, prem_sd, n), 0, 150), np.maximum(0, rng.normal(syn, 0.5 * syn, n))):
        v = _acc(a, t, float(p), pct_cash, float(s), tax, cod)
        if v is not None: out.append(v)
    if not out: return None
    q = lambda x: round(float(np.percentile(out, x)), 2); cnt, edges = np.histogram(out, bins=10)
    return {"n": len(out), "p5": q(5), "p25": q(25), "p50": q(50), "p75": q(75), "p95": q(95), "prob_accretive_pct": round(100 * sum(v >= 0 for v in out) / len(out), 1),
            "hist": [{"bin": f"{edges[i]:.1f}", "n": int(c)} for i, c in enumerate(cnt)], "assumption": f"premium ~ N({premium:g}, {prem_sd:g}); synergies ~ N({syn:g}, {0.5*syn:g}), floored at 0"}

def tornado(a, t, premium, pct_cash, syn, tax, cod):
    if _acc(a, t, premium, pct_cash, syn, tax, cod) is None: return []
    cl = lambda x: min(1.0, max(0.0, x)); rows = []
    for name, lo, hi in (("Premium ±10 pts", (premium - 10, pct_cash, syn, tax, cod), (premium + 10, pct_cash, syn, tax, cod)),
                         ("Synergies ±50%", (premium, pct_cash, syn * 0.5, tax, cod), (premium, pct_cash, syn * 1.5, tax, cod)),
                         ("Cash mix ±25 pts", (premium, cl(pct_cash - 0.25), syn, tax, cod), (premium, cl(pct_cash + 0.25), syn, tax, cod)),
                         ("Tax rate ±5 pts", (premium, pct_cash, syn, tax - 0.05, cod), (premium, pct_cash, syn, tax + 0.05, cod)),
                         ("Cost of debt ±2 pts", (premium, pct_cash, syn, tax, cod - 0.02), (premium, pct_cash, syn, tax, cod + 0.02))):
        x, y = _acc(a, t, max(0, lo[0]), *lo[1:]), _acc(a, t, max(0, hi[0]), *hi[1:]); rows.append({"driver": name, "low_case": round(x, 2), "high_case": round(y, 2), "swing": round(abs(y - x), 2)})
    return sorted(rows, key=lambda r: -r["swing"])

def breakeven_acquirer_price(a, t, premium, pct_cash, syn, tax, cod):
    if pct_cash >= 1 or a["net_income_m"] <= 0: return None
    f = lambda p: _acc(dict(a, price=p), t, premium, pct_cash, syn, tax, cod)
    lo, hi = a["price"] * 0.05, a["price"] * 20
    if f(hi) < 0 or f(lo) >= 0: return None if f(hi) < 0 else round(lo, 2)
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) >= 0: hi = mid
        else: lo = mid
    return round(hi, 2)

def collar_table(a, t, premium, pct_cash, moves=(-20, -10, 0, 10, 20)):
    """Fixed exchange ratio: value delivered per target share as the acquirer's price moves after signing."""
    offer = t["price"] * (1 + premium / 100); er = exchange_ratio(offer, a["price"], pct_cash); cash = offer * pct_cash
    return [{"acq_price_move_pct": m, "acq_price": round(a["price"] * (1 + m / 100), 2), "value_per_target_share": round(cash + er * a["price"] * (1 + m / 100), 2),
             "effective_premium_pct": round((cash + er * a["price"] * (1 + m / 100)) / t["price"] * 100 - 100, 1)} for m in moves]

def credit(a, t, cash_part_m, syn, cod):
    pf_debt = (a.get("debt_m") or 0) + (t.get("debt_m") or 0) + cash_part_m; pf_e = (a.get("ebitda_m") or 0) + (t.get("ebitda_m") or 0) + syn
    return {"pf_gross_debt_m": pf_debt, "pf_gross_debt_ebitda": pf_debt / pf_e if pf_e > 0 else None, "approx_interest_cover": pf_e / (pf_debt * cod) if pf_debt > 0 and pf_e > 0 else None}

def advanced(a, t, premium, pct_cash, syn, tax, cod, cap=3.5):
    b = S(a, t, premium, pct_cash, syn, tax, cod); rp = relative_pe(a, b["equity_value_m"]); rp["offer_pe_target"] = b["offer_pe"]
    return {"value_creation": value_creation(a, t, premium, syn, tax), "contribution": contribution(a, t, b["target_holders_pct"]), "relative_pe": rp,
            "leverage_cap": {**max_cash_at_leverage(a, t, premium, syn, cap), "optimal_mix": optimal_mix(a, t, premium, syn, tax, cod, cap)},
            "credit": credit(a, t, b["cash_part_m"], syn, cod), "monte_carlo": monte_carlo(a, t, premium, syn, pct_cash, tax, cod), "tornado": tornado(a, t, premium, pct_cash, syn, tax, cod),
            "breakeven_acquirer_price": breakeven_acquirer_price(a, t, premium, pct_cash, syn, tax, cod), "collar": collar_table(a, t, premium, pct_cash),
            "exchange_ratio": exchange_ratio(t["price"] * (1 + premium / 100), a["price"], pct_cash)}
