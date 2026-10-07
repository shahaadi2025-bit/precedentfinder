"""Stage 1 pipeline: EDGAR -> isolate deal text -> regex extract -> deals / unparsed tables.
Reuses cached filing text in data/texts so re-runs after regex fixes are fast.
Usage: python -m app.ingest --start 2022-01-01 --end 2025-12-31 --forms DEFM14A --max 50 [--sectors Technology] [--no-reuse]"""
import argparse, json, re
from . import edgar
from .config import TEXTS
from .db import conn, jdump
from .extractor import extract

def is_spac(name, full):
    """Banks also mention 'trust account' (fiduciary business), so require SPAC-specific language too."""
    if len(re.findall(r"trust account", full, re.I)) < 5: return False
    return len(re.findall(r"initial business combination", full, re.I)) >= 3 or \
        bool(re.search(r"acquisition (?:corp|co\b)|\bcapital (?:two|ii|iii)\b|\bSPAC\b", name, re.I))

def date_flags(ann, filed):
    """Plausibility of the extracted agreement date relative to the proxy's filing date."""
    from datetime import date
    try: f = date.fromisoformat(filed)
    except (TypeError, ValueError): return []
    if ann > f: return ["date_after_filing"]
    gap = (f - ann).days
    return ["date_within_14d_of_filing"] if gap < 14 else (["date_over_13mo_before_filing"] if gap > 400 else [])

def known_sector(c, adsh):
    r = c.execute("SELECT sector, sic FROM deals WHERE adsh=? UNION SELECT sector, '' FROM unparsed WHERE adsh=?", (adsh, adsh)).fetchone()
    return (r[0], r[1]) if r else None

def process(hit, sector_filter=None, reuse=True):
    c = conn(); adsh = hit["adsh"]; cache = TEXTS / f"{adsh}.txt"
    ks = known_sector(c, adsh) if reuse else None
    if ks: sector, sic = ks
    else:
        sic, _ = edgar.sic_for(hit["cik"]); sector = edgar.sector_from_sic(sic)
    if sector_filter and sector not in sector_filter: return "skipped_sector"
    if reuse and cache.exists():
        full = cache.read_text(encoding="utf-8"); focus = edgar.focus_from_text(full)
    else:
        focus, full = edgar.isolate_deal_text(edgar.fetch_html(hit["url"])); cache.write_text(full, encoding="utf-8")
    if is_spac(hit["name"], full):
        c.execute("DELETE FROM deals WHERE adsh=?", (adsh,)); c.execute("DELETE FROM unparsed WHERE adsh=?", (adsh,)); c.commit(); c.close()
        return "skipped_spac"
    r = extract(focus, hit["name"])
    if r["date"]:
        extra = date_flags(r["date"], hit.get("file_date"))
        r["flags"] += extra
        if "date_after_filing" in extra: r["confidence"] = "unparsed"; r["reasons"].append("date_after_filing")
        elif extra and r["confidence"] == "high": r["confidence"] = "medium"
    if r["confidence"] == "unparsed":
        c.execute("DELETE FROM deals WHERE adsh=?", (adsh,))
        c.execute("INSERT OR REPLACE INTO unparsed VALUES(?,?,?,?,?,?,?,?)", (adsh, hit["form"], hit["name"], sector, hit["url"],
            jdump(r["reasons"] + r["flags"]), jdump({k: r[k] for k in ("acquirer", "date", "premium", "premium_ref", "deal_value_musd", "all_premiums", "premium_ctx")}),
            jdump([focus[:400]])))
        out = "unparsed"
    else:
        c.execute("DELETE FROM unparsed WHERE adsh=?", (adsh,))
        flags = r["flags"] + ([f"value_ctx: {r['deal_value_ctx']}"] if r["deal_value_ctx"] else [])
        c.execute("INSERT OR REPLACE INTO deals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (adsh, hit["form"], hit["name"],
            r["acquirer"], str(r["date"]), r["deal_value_musd"], r["price"], r["premium"], r["premium_ref"], r["multiple"],
            r["multiple_type"], sector, sic, r["confidence"], jdump(flags), hit["url"]))
        out = "parsed"
    c.commit(); c.close(); return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-01-01"); ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--forms", nargs="+", default=["DEFM14A"]); ap.add_argument("--max", type=int, default=100)
    ap.add_argument("--sectors", nargs="*", default=None); ap.add_argument("--no-reuse", action="store_true")
    a = ap.parse_args(); stats = {}
    for form in a.forms:
        for hit in edgar.search(form, a.start, a.end, max_hits=a.max):
            try: s = process(hit, a.sectors, reuse=not a.no_reuse)
            except Exception as e: s = "error"; print("ERR", hit["name"], e)
            stats[s] = stats.get(s, 0) + 1; print(f"{s:14} {hit['form']:7} {hit['name']}")
    print(json.dumps(stats))
if __name__ == "__main__": main()
