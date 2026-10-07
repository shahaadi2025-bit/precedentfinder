"""EDGAR access: full-text search, filing download, SIC lookup. Polite: <=8 req/s, descriptive UA."""
import re, time, warnings, requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)
from .config import USER_AGENT
_last = [0.0]
def _get(url, **kw):
    wait = 0.125 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    for attempt in range(4):
        r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}, timeout=60, **kw)
        _last[0] = time.time()
        if r.status_code in (429, 503): time.sleep(2 ** attempt); continue
        r.raise_for_status(); return r
    r.raise_for_status()

def search(form, start, end, q='"agreement and plan of merger"', page_size=100, max_hits=500):
    """Yield dicts: adsh, cik, name, file_date, form, url. Uses efts full-text search."""
    got, frm = 0, 0
    while got < max_hits:
        r = _get("https://efts.sec.gov/LATEST/search-index", params={
            "q": q, "forms": form, "dateRange": "custom", "startdt": start, "enddt": end, "from": frm})
        hits = r.json().get("hits", {}).get("hits", [])
        if not hits: return
        for h in hits:
            s = h["_source"]; adsh, fname = h["_id"].split(":", 1)
            cik = str(int(s["ciks"][0]))
            if form == "8-K" and not any(i in ("1.01", "2.01") for i in (s.get("items") or [])): continue
            yield dict(adsh=adsh, cik=cik, name=s["display_names"][0].split("(")[0].strip(), file_date=s["file_date"],
                       form=s["form"], url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{fname}")
            got += 1
            if got >= max_hits: return
        frm += page_size

def sic_for(cik):
    j = _get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json").json()
    return str(j.get("sic") or ""), j.get("sicDescription") or ""

SECTOR_RANGES = [(100, 999, "Agriculture"), (1000, 1499, "Energy & Mining"), (1500, 1799, "Construction"),
  (2000, 2799, "Consumer & Manufacturing"), (2800, 2829, "Chemicals"), (2830, 2836, "Healthcare"),
  (2837, 2899, "Chemicals"), (2900, 2999, "Energy & Mining"), (3000, 3569, "Industrials"), (3570, 3579, "Technology"),
  (3580, 3669, "Industrials"), (3670, 3679, "Technology"), (3680, 3829, "Industrials"), (3830, 3859, "Healthcare"),
  (3860, 3999, "Industrials"), (4000, 4799, "Transportation"), (4800, 4899, "Telecom & Media"),
  (4900, 4999, "Utilities"), (5000, 5199, "Wholesale"), (5200, 5999, "Retail"), (6000, 6499, "Financials"),
  (6500, 6599, "Real Estate"), (6700, 6799, "Financials"), (7370, 7379, "Technology"), (7000, 7369, "Services"),
  (7380, 7999, "Services"), (8000, 8099, "Healthcare"), (8100, 8999, "Services")]
def sector_from_sic(sic):
    try: n = int(sic)
    except (TypeError, ValueError): return "Unknown"
    for lo, hi, name in SECTOR_RANGES:
        if lo <= n <= hi: return name
    return "Other"

def fetch_html(url): return _get(url).text

KEYS = re.compile(r"premium|enterprise value|aggregate (?:consideration|equity value)|EBITDA|per share in cash|Agreement and Plan of Merger", re.I)
def focus_from_text(text, head_chars=60000, window=700):
    """Keep the cover/summary (first ~60k chars) plus windows around deal-terms keywords."""
    spans = [(0, min(head_chars, len(text)))]
    for m in KEYS.finditer(text[head_chars:]):
        a = head_chars + m.start(); spans.append((max(head_chars, a - window), min(len(text), a + window)))
    spans.sort(); merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]: merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else: merged.append((a, b))
    return " ... ".join(text[a:b] for a, b in merged)

def isolate_deal_text(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]): t.decompose()
    text = " ".join(soup.get_text(" ").split())
    return focus_from_text(text), text
