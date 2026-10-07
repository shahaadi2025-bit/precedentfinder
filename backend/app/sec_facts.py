"""Company lookup + latest-annual financials from SEC EDGAR XBRL (free). Figures are as-reported; tags vary by filer."""
import json, difflib, re
from datetime import date
from . import edgar
from .config import DATA

TICKERS = DATA / "company_tickers.json"
def _tickers():
    if not TICKERS.exists():
        TICKERS.write_text(json.dumps(edgar._get("https://www.sec.gov/files/company_tickers.json").json()), encoding="utf-8")
    return list(json.loads(TICKERS.read_text(encoding="utf-8")).values())

def _norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
def resolve(query):
    """ticker exact match first, then best fuzzy match on company title. Returns (best, candidates)."""
    q = query.strip(); rows = _tickers()
    for r in rows:
        if r["ticker"].lower() == q.lower(): return r, [r]
    qn = " ".join(_norm(q)); scored = []
    for r in rows:
        tn = " ".join(_norm(r["title"]))
        s = difflib.SequenceMatcher(None, qn, tn).ratio() + (0.25 if qn and tn.startswith(qn) else 0)
        scored.append((s, r))
    scored.sort(key=lambda x: -x[0]); cands = [r for s, r in scored[:5]]
    if not scored or scored[0][0] < 0.5: raise ValueError(f"Couldn't find '{query}' in SEC company list (US-listed filers only). Try the ticker.")
    return cands[0], cands

TAGS = {
 "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet"],
 "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
 "operating_income": ["OperatingIncomeLoss"],
 "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet", "DepreciationNonproduction"],
 "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
 "debt": ["LongTermDebt", "DebtInstrumentCarryingAmount"],
 "debt_nc": ["LongTermDebtNoncurrent"], "debt_c": ["LongTermDebtCurrent", "DebtCurrent"],
 "assets": ["Assets"], "equity": ["StockholdersEquity"],
 "eps_diluted": ["EarningsPerShareDiluted"],
}
FLOW = {"revenue", "net_income", "operating_income", "da", "eps_diluted"}
ANNUAL_FORMS = {"10-K", "10-K/A", "10-KT", "20-F", "40-F"}

def _days(e):
    try:
        a = date.fromisoformat(e["start"]); b = date.fromisoformat(e["end"]); return (b - a).days
    except Exception: return None

def _latest(facts, key, unit_pref=("USD", "USD/shares")):
    best = None
    for tag in TAGS[key]:
        node = facts.get("us-gaap", {}).get(tag)
        if not node: continue
        for unit, entries in node["units"].items():
            if unit not in unit_pref: continue
            for e in entries:
                if e.get("form") not in ANNUAL_FORMS or e.get("fp") != "FY": continue
                if key in FLOW:
                    d = _days(e)
                    if d is None or not 330 <= d <= 400: continue
                cand = (e["end"], e.get("filed", ""), e["val"], tag)
                if best is None or cand[:2] > best[:2]: best = cand
    return best   # (end, filed, value, tag)

def _shares(facts):
    best = None
    for ns, tag in (("dei", "EntityCommonStockSharesOutstanding"), ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding")):
        node = facts.get(ns, {}).get(tag)
        if not node: continue
        for e in node["units"].get("shares", []):
            cand = (e["end"], e.get("filed", ""), e["val"], tag)
            if best is None or cand[:2] > best[:2]: best = cand
        if best: break
    return best

def parse_financials(companyfacts):
    f = companyfacts.get("facts", {}); out = {"entity": companyfacts.get("entityName")}; src = {}
    for k in TAGS:
        r = _latest(f, k)
        if r: out[k] = r[2]; src[k] = f"{r[3]} (FY end {r[0]})"
    sh = _shares(f)
    if sh: out["shares"] = sh[2]; src["shares"] = f"{sh[3]} ({sh[0]})"
    debt = out.get("debt")
    if debt is None and (out.get("debt_nc") is not None or out.get("debt_c") is not None):
        debt = (out.get("debt_nc") or 0) + (out.get("debt_c") or 0); src["debt"] = "LongTermDebtNoncurrent + current portion"
    ebitda = out["operating_income"] + out["da"] if "operating_income" in out and "da" in out else None
    m = lambda v: None if v is None else v / 1e6
    return {"entity": out["entity"], "revenue_m": m(out.get("revenue")), "net_income_m": m(out.get("net_income")),
            "operating_income_m": m(out.get("operating_income")), "ebitda_m": m(ebitda), "cash_m": m(out.get("cash")),
            "debt_m": m(debt), "assets_m": m(out.get("assets")), "equity_m": m(out.get("equity")),
            "eps_diluted": out.get("eps_diluted"), "shares_m": m(out.get("shares")), "sources": src}

def financials(cik):
    cf = edgar._get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json").json()
    return parse_financials(cf)
