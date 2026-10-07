import re
from datetime import datetime

MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
DATE = rf"{MONTH}\s+\d{{1,2}},\s+\d{{4}}"
PCT = r"(\d{1,3}(?:\.\d+)?)\s?%"

def _d(s): return datetime.strptime(re.sub(r"\s+", " ", s), "%B %d, %Y").date()
def _clean(t):
    t = re.sub(r"[\u200b\u00a0]", " ", t); return re.sub(r"\s+", " ", t)

# ---------------- date ----------------
AGR = r"(?:Agreement\s+and\s+Plan\s+of\s+(?:Merger|Reorganization|Share\s+Exchange)(?:\s+and\s+Reorganization)?|Merger\s+Agreement|merger\s+agreement)"
PROXYWORDS = re.compile(r"proxy|prospectus|document|circular|mailed|statement|notice|meeting", re.I)
AMEND = re.compile(r"Amendment\s+(?:No\.?\s*\d+\s+)?to\s+(?:the\s+)?$", re.I)
DATE_RULES = [
    ("dated_as_of", rf"{AGR}[^.]{{0,160}}?dated\s+(?:as\s+of\s+)?({DATE})"),
    ("on_entered_into", rf"On\s+({DATE}),\s+[^.]{{0,80}}?entered\s+into\s+(?:an?|the)\s+{AGR}"),
    ("entered_into_on", rf"entered\s+into\s+(?:an?|the)\s+{AGR}[^.]{{0,100}}?\bon\s+({DATE})"),
]
def extract_date(t):
    """-> (date, rule, evidence). Skips proxy-statement dates and amendment dates."""
    for rule, pat in DATE_RULES:
        for m in re.finditer(pat, t):
            if PROXYWORDS.search(m.group(0)) or AMEND.search(t[max(0, m.start() - 40): m.start()]): continue
            return _d(m.group(1)), rule, t[max(0, m.start() - 60): m.end() + 40]
    return None, None, None

# ---------------- acquirer ----------------
BAD = re.compile(r"agreement|attached|exhibit|annex|borrower|lender|dated|merger sub|merger subsidiary|acquisition sub|"
                 r"section|\bthe company\b|stockholder|shareholder|proxy|bank merger|\bparent\b$|\bsurviving\b|\bmerger\b", re.I)
SUFFIX = r"(?:Inc|LLC|L\.L\.C|Ltd|Corp|L\.P|LP|N\.A|plc|Co)"
DESC = r",?\s+an?\s+(?:[A-Za-z\-]+\s+){0,4}?(?:corporation|company|partnership|association|bank)\b[^,]*"
DEFTERM = re.compile(r"\(\s*(?:the\s+)?[\u201c\u201d\"']?\s*(Parent|Buyer|Purchaser|Acquirer|Acquiror|Holdco)\s*[\u201c\u201d\"']?\s*\)")
JURIS = re.compile(r"^(?:inc|llc|ltd|corp|corporation|limited|company|co|plc|lp|delaware|nevada|canada|ontario|british columbia|cayman islands|bermuda|"
                   r"maryland|new york|texas|florida|ohio|virginia|pennsylvania|united states|u\.s\.|usa|cayman|the)\.?$", re.I)

def _norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
def _is_target(name, target):
    a, b = _norm(name), _norm(target)
    return bool(a and b and a[0] == b[0])
def _valid(n, target):
    n = n.strip(" ,;:-\u201c\u201d\"'")
    if JURIS.match(n): return None
    if not (3 <= len(n) <= 70) or len(n.split()) > 8 or not n[0].isupper(): return None
    if BAD.search(n) or "(" in n or ")" in n or (target and _is_target(n, target)): return None
    return n
def _names(seg):
    seg = re.sub(r"\([^)]*\)", " ", seg)
    seg = re.sub(rf",\s+(?={SUFFIX}\b)", " ", seg)
    seg = re.sub(DESC, "", seg)
    return [p.strip() for p in re.split(r",\s+and\s+|\s*,\s*|\s+and\s+", seg) if p.strip()]

def extract_acquirer(t, target):
    """-> (name, rule, evidence)"""
    for m in DEFTERM.finditer(t):
        w = t[max(0, m.start() - 200): m.start()]
        w = re.sub(rf",\s+(?={SUFFIX}\b)", " ", w)
        w = re.sub(DESC + r"\s*$", "", w)
        piece = re.split(r"\bwith\b|\bamong\b|\bbetween\b|;|,|\band\b", w)[-1]
        n = _valid(piece, target)
        if n: return n, "defined_term", t[max(0, m.start() - 160): m.end()]
    for m in re.finditer(rf"dated\s+as\s+of\s+{DATE},?\s+with\s+([^,(]{{3,70}}?(?:,\s+{SUFFIX}\.?)?),?\s+an?\s+[A-Z]\w+", t):
        n = _valid(re.sub(rf",\s+(?={SUFFIX}\b)", " ", m.group(1)), target)
        if n: return n, "with_clause", m.group(0)[-200:]
    for m in re.finditer(r"(?:by and among|by and between|\bamong|\bbetween)\s+(.{20,420}?)(?:\.\s|,?\s+pursuant|,?\s+Subject|,?\s+under which|,?\s+providing)", t):
        for n in _names(m.group(1)):
            v = _valid(n, target)
            if v: return v, "party_list", m.group(0)[:240]
    return None, None, None

# ---------------- premium ----------------
REF_RULES = [
    ("unaffected_vwap", r"unaffected[^.]{0,40}(?:volume[- ]weighted|VWAP|\d+[- ]day)"),
    ("unaffected", r"unaffected|prior to (?:the )?(?:first )?(?:market )?(?:speculation|media reports|announcement of a formal review)|before media reports"),
    ("vwap", r"volume[- ]weighted|VWAP|\d+[- ]day|average (?:closing|trading)|trailing"),
    ("spot_close", r"closing (?:sale |stock |share |trading )?price|last (?:full |closing )?(?:trading|business) day|market price|(?:stock|share) price|price per share|close of (?:trading|business)|prior to (?:the )?(?:public )?announcement"),
]
SENT_END = re.compile(r"\.\s+(?=(?:On|The|As|In|If|Each|Following|Such|This|At|Upon|For|Our|We)\b)")
RANGE_BEFORE = re.compile(r"\d+(?:\.\d+)?\s?%\s*(?:-|\u2013|\u2014|to|and)\s*$")
RANGE_AFTER = re.compile(r"^\s*(?:-|\u2013|\u2014|to|and)\s*\d+(?:\.\d+)?\s?%")

def extract_premiums(t):
    cands, seen = [], set()
    pat = rf"(?:premium\s+(?:of\s+)?(?:approximately\s+)?{PCT})|(?:{PCT}\s+premium)|(?:premium(?:(?!\.\s)[^%]){{1,70}}?{PCT})"
    for m in re.finditer(pat, t):
        pct = float(m.group(1) or m.group(2) or m.group(3))
        if (m.start() // 40, pct) in seen: continue
        seen.add((m.start() // 40, pct))
        ref = t[m.end(): m.end() + 260]
        cut = SENT_END.search(ref)
        if cut: ref = ref[:cut.start()]
        nxt = re.search(r"premium", ref)
        if nxt: ref = ref[:nxt.start()]
        kind = "unknown"
        if RANGE_BEFORE.search(t[max(0, m.start() - 16): m.start()]) or RANGE_AFTER.search(t[m.end(): m.end() + 16]):
            kind = "range"
        else:
            for k, rx in REF_RULES:
                if re.search(rx, ref, re.I): kind = k; break
            if kind == "unaffected" and re.search(r"closing", ref, re.I) and not re.search(r"media reports|speculation|formal review", ref, re.I):
                kind = "spot_close"
        cands.append({"pct": pct, "ref": kind, "ref_text": ref[:160].strip(), "ctx": t[max(0, m.start() - 60): m.end() + 100]})
    return cands

def pick_premium(cands):
    spot = [c for c in cands if c["ref"] == "spot_close"]
    if len(spot) == 1: return spot[0], "clean"
    if len(spot) > 1: return spot[0], "ambiguous"
    un = [c for c in cands if c["ref"] in ("unaffected", "unaffected_vwap")]
    if un: return un[0], "weak"
    vw = [c for c in cands if c["ref"] == "vwap"]
    if vw: return vw[0], "weak"
    if any(c["ref"] == "range" for c in cands): return None, "range"
    return None, ("unknown_ref" if cands else "none")   # unrecognised reference or range is NOT trusted

def extract_price(t):
    m = re.search(r"\$\s?(\d{1,4}(?:\.\d{1,4})?)\s+(?:per share\s+)?in cash", t)
    return float(m.group(1)) if m else None

# ---------------- deal value ----------------
FIN = re.compile(r"credit|facilit|financing|debt|loan|\bnotes\b|revolv|borrow|commitment|termination fee|break[- ]?up|reverse|fee\b|bridge|guarant", re.I)
NEG = re.compile(r"letter of intent|\bLOI\b|proposal|indicat|non-binding|\bbetween\s+\$|\brange\b|screen|criteria|selected|or more|since 20|Duff|Phelps|"
                 r"valuation|fairness|illustrat|estimated|preliminary|initial offer|prior offer|comparable|precedent", re.I)
VALUE_PATTERNS = [
    r"(?:aggregate|total)\s+(?:merger\s+)?(?:consideration|equity value|purchase price|transaction value)[^$]{0,80}\$\s?(\d[\d,.]*)\s*(million|billion)",
    r"(?:implied\s+)?(?:fully[- ]diluted\s+)?equity value of (?:approximately |roughly )?\$\s?(\d[\d,.]*)\s*(million|billion)",
    r"enterprise value of (?:approximately |roughly )?\$\s?(\d[\d,.]*)\s*(million|billion)",
]
VALUE_WINDOW = 40000
def extract_deal_value(t):
    t = t[:VALUE_WINDOW]
    for pat in VALUE_PATTERNS:
        for m in re.finditer(pat, t, re.I):
            pre = t[max(0, m.start() - 160): m.start()]
            pre = pre[pre.rfind(". ") + 2:] if ". " in pre else pre
            ctx = pre + t[m.start(): m.end() + 120]
            if FIN.search(ctx) or NEG.search(ctx): continue
            try: v = float(m.group(1).replace(",", "").rstrip("."))
            except ValueError: continue
            return v * (1000 if m.group(2).lower() == "billion" else 1), ctx.strip()
    return None, None

def extract_multiple(t):
    m = re.search(r"(?:impl(?:ied|ies)|represents|transaction)[^.]{0,80}?(\d{1,3}(?:\.\d+)?)x\s*(?:LTM |NTM |CY\d+ )?(EBITDA|revenue|sales)", t, re.I)
    return (float(m.group(1)), m.group(2).upper()) if m else (None, None)

def extract(t, target_name, target_short=None):
    t = _clean(t)
    date, dsrc, dctx = extract_date(t)
    acq, asrc, actx = extract_acquirer(t, target_name)
    cands = extract_premiums(t)
    prem, ptier = pick_premium(cands)
    ev, vctx = extract_deal_value(t); mult, mtype = extract_multiple(t)
    flags = []
    ref_dates = [_d(x) for x in re.findall(DATE, " ".join(c["ref_text"] for c in cands))]
    if date and any(r > date for r in ref_dates): flags.append("premium_ref_date_after_agreement")
    if ptier == "ambiguous": flags.append("multiple_spot_premiums")
    if ptier == "weak": flags.append("premium_not_spot")
    if ptier == "unknown_ref": flags.append("premium_unknown_reference")
    if ptier == "range": flags.append("premium_is_range")
    if prem and prem["pct"] > 100: flags.append("premium_outlier_gt100")
    req = {"target": bool(target_name), "acquirer": bool(acq), "date": bool(date)}
    ok = all(req.values()) and (prem is not None or ev is not None)
    conf = "high" if ok and ptier == "clean" and not flags else \
           "medium" if ok and "premium_ref_date_after_agreement" not in flags else "unparsed"
    reasons = [k for k, v in req.items() if not v]
    if prem is None and ev is None: reasons.append("no_premium_or_value")
    if "premium_ref_date_after_agreement" in flags: reasons.append("premium_ref_date_after_agreement")
    return dict(target=target_name, acquirer=acq, acq_rule=asrc, date=date, date_rule=dsrc,
                price=extract_price(t), deal_value_musd=ev, deal_value_ctx=vctx,
                premium=prem["pct"] if prem else None, premium_ref=prem["ref"] if prem else None,
                premium_tier=ptier, all_premiums=[(c["pct"], c["ref"]) for c in cands],
                premium_ctx=[(c["pct"], c["ref"], c["ctx"]) for c in cands[:4]],
                multiple=mult, multiple_type=mtype, confidence=conf, flags=flags, reasons=reasons,
                evidence={"date": dctx, "acquirer": actx, "premium": prem["ctx"] if prem else None, "value": vctx})
