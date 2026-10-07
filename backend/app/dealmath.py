"""Deterministic deal math (no ML, no LLM). Units: $ millions, shares in millions, per-share in $.
Simplifications (stated in the UI): cash portion funded by new debt at cost_of_debt; no purchase-accounting amortization,
no fees, no refinancing of target debt, tax rate flat. This is an illustration, not a model of a real transaction."""

def _div(a, b): return None if (b is None or b == 0 or a is None) else a / b

def scenario(acq, tgt, premium_pct, pct_cash, synergies_musd=0.0, tax_rate=0.25, cost_of_debt=0.06):
    offer = tgt["price"] * (1 + premium_pct / 100)
    equity = offer * tgt["shares_m"]
    ev = equity + (tgt.get("debt_m") or 0) - (tgt.get("cash_m") or 0)
    cash_part = equity * pct_cash; stock_part = equity - cash_part
    new_shares = stock_part / acq["price"]
    interest_at = cash_part * cost_of_debt * (1 - tax_rate)
    syn_at = synergies_musd * (1 - tax_rate)
    pf_ni = acq["net_income_m"] + tgt["net_income_m"] + syn_at - interest_at
    pf_shares = acq["shares_m"] + new_shares
    eps_acq = _div(acq["net_income_m"], acq["shares_m"]); eps_pf = pf_ni / pf_shares
    accretion = None if not eps_acq or eps_acq <= 0 else (eps_pf / eps_acq - 1) * 100
    be_at = (eps_acq * pf_shares - (acq["net_income_m"] + tgt["net_income_m"] - interest_at)) if eps_acq and eps_acq > 0 else None
    be_syn = None if be_at is None else be_at / (1 - tax_rate)      # pre-tax synergies for EPS-neutral; negative => already accretive
    acq_mcap = acq["price"] * acq["shares_m"]
    pf_net_debt = (acq.get("debt_m") or 0) + (tgt.get("debt_m") or 0) + cash_part - (acq.get("cash_m") or 0) - (tgt.get("cash_m") or 0)
    pf_ebitda = (acq.get("ebitda_m") or 0) + (tgt.get("ebitda_m") or 0) + synergies_musd
    return {
        "premium_pct": premium_pct, "pct_cash": pct_cash, "offer_price": offer, "equity_value_m": equity, "ev_m": ev,
        "ev_revenue": _div(ev, tgt.get("revenue_m")), "ev_ebitda": _div(ev, tgt["ebitda_m"]) if (tgt.get("ebitda_m") or 0) > 0 else None,
        "offer_pe": _div(equity, tgt["net_income_m"]) if tgt["net_income_m"] > 0 else None,
        "cash_part_m": cash_part, "stock_part_m": stock_part, "new_shares_m": new_shares,
        "target_holders_pct": new_shares / pf_shares * 100, "size_vs_acq_mcap_pct": equity / acq_mcap * 100,
        "eps_standalone": eps_acq, "eps_pro_forma": eps_pf, "eps_accretion_pct": accretion, "breakeven_synergies_m": be_syn,
        "pf_net_debt_ebitda": _div(pf_net_debt, pf_ebitda) if pf_ebitda > 0 else None,
        "cash_needs_new_debt_m": max(0.0, cash_part - (acq.get("cash_m") or 0)),
    }

def grid(acq, tgt, premiums, cash_mixes, synergies_musd=0.0, **kw):
    return [scenario(acq, tgt, p, c, synergies_musd, **kw) for p in premiums for c in cash_mixes]
