import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from app.extractor import extract
from tests.sample_texts import S

EXPECT = {  # hand-labeled from the filing text
 "Nevro": ("Globus Medical Inc.", "2025-02-06", 13.8, "high"), "ProAssurance": ("The Doctors Company", "2025-03-19", 58.8, "high"),
 "ODP": ("ACR Ocean Resources LLC", "2025-09-22", 34.5, "high"), "Enzo": ("Bethpage Parent Inc.", "2025-06-23", 32.0, "high"),
 "Altus": (None, "2025-02-05", 66.0, "unparsed"), "Monogram": (None, None, 23.0, "unparsed"), "FARO": (None, None, 40.0, "unparsed"),
 "SpringWorks": (None, "2025-04-27", 26.0, "unparsed"), "AvidXchange": (None, None, 45.0, "unparsed")}

def test_extractor_samples():
    for k, (txt, name) in S.items():
        r = extract(txt, name); acq, d, p, c = EXPECT[k]
        assert r["acquirer"] == acq, k
        assert (str(r["date"]) if r["date"] else None) == d, k
        assert r["premium"] == p, k
        assert r["confidence"] == c, k

def test_never_guesses_value_or_multiple():
    r = extract(S["Nevro"][0], "Nevro Corp"); assert r["deal_value_musd"] is None and r["multiple"] is None

def test_value_and_multiple_patterns():
    t = "The aggregate consideration is approximately $1.2 billion. The merger implies 11.5x LTM EBITDA. enterprise value of approximately $950 million."
    r = extract(t, "X"); assert r["deal_value_musd"] == 1200.0 and r["multiple"] == 11.5

def test_crosscheck():
    from app.rag import crosscheck
    deals = [{"premium": 34.5, "multiple": None, "deal_value_musd": 1200.0, "price_per_share": 28.0}]
    out = crosscheck("ODP paid $28.00 per share, a 34.5% premium, worth $1.2 billion; also a 99% premium and $5 million.", "src 34.5%", deals)
    st = {c["value"]: c["status"] for c in out}
    assert st["34.5%"] == "table_match" and st["$28.00"] == "table_match" and st["$1.2 billion"] == "table_match"
    assert st["99%"] == "unverified"

def test_sector_map():
    from app.edgar import sector_from_sic
    assert sector_from_sic("7372") == "Technology" and sector_from_sic("2834") == "Healthcare" and sector_from_sic("6022") == "Financials"

def test_ml_smoke_on_synthetic(tmp_path, monkeypatch):
    from app import ml
    rng = np.random.default_rng(0); n = 80
    df = pd.DataFrame({"sector": rng.choice(["Technology", "Healthcare", "Financials"], n), "deal_value_musd": rng.uniform(50, 8000, n),
                       "year": rng.integers(2021, 2026, n), "premium": rng.uniform(10, 60, n)})
    df["value_bucket"] = df["deal_value_musd"].map(ml.bucket)
    monkeypatch.setattr(ml, "frame", lambda: df); monkeypatch.setattr(ml, "MODEL_PATH", tmp_path / "m.joblib"); monkeypatch.setattr(ml, "METRICS_PATH", tmp_path / "m.json")
    m = ml.train(); assert m["trained"] and "test_mae" in m and "feature_importance" in m
    p = ml.predict("Technology", 500.0, 2025); assert p["low_p10"] <= p["point"] <= p["high_p90"]

def test_ml_refuses_tiny_sample(monkeypatch):
    from app import ml
    monkeypatch.setattr(ml, "frame", lambda: pd.DataFrame({"premium": [1, 2]}))
    assert ml.train()["trained"] is False

# ---- regression cases from the first live EDGAR run ----
def _acq(txt, target="Target Corp"):
    from app.extractor import extract_acquirer
    return extract_acquirer(" ".join(txt.split()), target)[0]

def test_acquirer_party_list_with_defined_terms():
    t = ("pursuant to the Agreement and Plan of Merger, dated as of December 14, 2023 (the \u201cMerger Agreement\u201d), by and among "
         "Battalion Oil Corporation, a Delaware corporation (the \u201cCompany\u201d), Fury Resources, Inc., a Delaware corporation (\u201cParent\u201d), "
         "and Fury Merger Sub, Inc., a Delaware corporation and wholly owned subsidiary of Parent, pursuant to which")
    assert _acq(t, "BATTALION OIL CORP") == "Fury Resources Inc."

def test_acquirer_bank_by_and_between():
    t = "the Agreement and Plan of Merger, dated as of February 22, 2023, by and between Partners Bancorp and Chesapeake Financial Shares, Inc., pursuant to which"
    assert _acq(t, "PARTNERS BANCORP") == "Chesapeake Financial Shares Inc."

def test_acquirer_rejects_junk():
    junk = ("form of Voting Agreement and Bank Merger Agreement attached and Amendment to the Agreement and Plan of Merger, dated as of March 21, 2023, "
            "with as borrower, a Delaware corporation")
    assert _acq(junk, "MALVERN BANCORP") is None

def test_acquirer_defined_term_after_among():
    t = ("dated as of September 22, 2025 (the \u201cmerger agreement\u201d), among ODP, ACR Ocean Resources LLC (\u201cParent\u201d), and Vail Holdings 1, Inc., "
         "a wholly owned subsidiary of Parent")
    assert _acq(t, "ODP Corp") == "ACR Ocean Resources LLC"

def test_premium_window_does_not_bleed_into_next_sentence():
    t = ("dated as of July 14, 2025 with Zimmer Biomet Holdings, Inc., a Delaware corporation (\u201cZimmer\u201d). Agreement and Plan of Merger "
         "represents a premium of approximately 23% over the closing price on July 11, 2025. On August 27, 2025, the latest practicable trading day, the price was $5.63.")
    r = extract(t, "Monogram Technologies Inc.")
    assert "premium_ref_date_after_agreement" not in r["flags"]

def test_unknown_reference_premium_not_trusted():
    r = extract("dated as of May 1, 2023 with Acme Holdings, Inc., a Delaware corporation. a premium of approximately 51.4% in connection with the offer.", "USA Truck Inc")
    assert r["premium"] is None

def test_deal_value_skips_financing_context():
    t = "Parent obtained a commitment for a senior credit facility of $1 billion. The aggregate consideration was approximately $6.2 billion."
    from app.extractor import extract_deal_value
    assert extract_deal_value(t)[0] == 6200.0
    assert extract_deal_value("a credit facility; aggregate consideration payable under the facility of $1 billion")[0] is None

# ---- second live run ----
def test_date_reorganization_and_plain_dated():
    from app.extractor import extract_date
    assert str(extract_date("the Agreement and Plan of Merger and Reorganization, dated as of June 5, 2023, by and between")[0]) == "2023-06-05"
    assert str(extract_date("the Agreement and Plan of Reorganization dated September 28, 2023 by and between")[0]) == "2023-09-28"
    assert str(extract_date("Company entered into an Agreement and Plan of Merger on March 3, 2022 with")[0]) == "2022-03-03"

def test_acquirer_rejects_bare_suffix_and_jurisdiction():
    assert _acq("by and among Target Corp, INC, and Canada, pursuant to") is None

def test_value_ignores_loi_range_and_screening():
    from app.extractor import extract_deal_value
    assert extract_deal_value("the offer was for aggregate consideration of between $1.0 billion and $1.2 billion.")[0] is None
    assert extract_deal_value("a letter of intent contemplating aggregate transaction value of approximately $147.2 million.")[0] is None
    assert extract_deal_value("targets with an equity value of $400 million or more")[0] is None
    assert extract_deal_value("The aggregate merger consideration is approximately $220.5 million (or $31.45 per share).")[0] == 220.5
    assert extract_deal_value("x" * 41000 + " aggregate consideration of approximately $5 billion")[0] is None

def test_premium_loose_wording_and_new_refs():
    from app.extractor import extract_premiums
    c = extract_premiums("a premium of approximately $2.10 per share, or 28.5%, to the closing sale price on May 3, 2023.")
    assert c and c[0]["pct"] == 28.5 and c[0]["ref"] == "spot_close"
    c = extract_premiums("represents a 41% premium to the average closing price over the prior 20 trading days.")
    assert c[0]["ref"] == "vwap"

def test_spac_filter_spares_banks():
    from app.ingest import is_spac
    bank = "trust account " * 8 + "The bank's fiduciary business holds assets in a trust account."
    assert not is_spac("CapStar Financial Holdings, Inc.", bank)
    assert is_spac("Blue World Acquisition Corp", "trust account " * 6)
    assert is_spac("Skillsoft Corp.", "trust account " * 6 + "initial business combination " * 4)

# ---- Deal Analyzer ----
ACQ = {"price": 50.0, "shares_m": 100.0, "net_income_m": 500.0, "cash_m": 100.0, "debt_m": 0.0, "ebitda_m": 900.0}
TGT = {"price": 20.0, "shares_m": 50.0, "net_income_m": 40.0, "revenue_m": 400.0, "ebitda_m": 80.0, "cash_m": 20.0, "debt_m": 60.0}

def test_dealmath_hand_calculated():
    from app import dealmath
    s = dealmath.scenario(ACQ, TGT, 30, 0.0)        # all stock
    assert abs(s["offer_price"] - 26.0) < 1e-9 and abs(s["equity_value_m"] - 1300.0) < 1e-9 and abs(s["ev_m"] - 1340.0) < 1e-9
    assert abs(s["ev_revenue"] - 3.35) < 1e-9 and abs(s["ev_ebitda"] - 16.75) < 1e-9
    assert abs(s["new_shares_m"] - 26.0) < 1e-9 and abs(s["eps_pro_forma"] - 540 / 126) < 1e-9
    assert abs(s["eps_accretion_pct"] - (540 / 126 / 5 - 1) * 100) < 1e-9          # -14.29%
    c = dealmath.scenario(ACQ, TGT, 30, 1.0)        # all cash, new debt at 6% pre-tax, 25% tax
    assert abs(c["eps_pro_forma"] - 4.815) < 1e-9 and abs(c["eps_accretion_pct"] - (-3.7)) < 1e-9
    assert abs(c["breakeven_synergies_m"] - 18.5 / 0.75) < 1e-9
    assert c["cash_needs_new_debt_m"] == 1200.0
    z = dealmath.scenario(ACQ, TGT, 30, 1.0, synergies_musd=c["breakeven_synergies_m"])
    assert abs(z["eps_accretion_pct"]) < 1e-9                                         # synergies exactly at break-even

def test_dealmath_handles_losses():
    from app import dealmath
    t = dict(TGT, net_income_m=-10.0, ebitda_m=-5.0)
    s = dealmath.scenario(ACQ, t, 25, 0.5)
    assert s["offer_pe"] is None and s["ev_ebitda"] is None
    assert dealmath.scenario(dict(ACQ, net_income_m=-1.0), TGT, 25, 0.5)["eps_accretion_pct"] is None

def _cf(tag, val, end="2023-12-31", start="2023-01-01", unit="USD", form="10-K", ns="us-gaap", fp="FY"):
    e = {"end": end, "val": val, "form": form, "fp": fp, "filed": "2024-02-20"}
    if start: e["start"] = start
    return ns, tag, {unit: [e]}

def test_sec_facts_parse():
    from app import sec_facts
    facts = {"entityName": "Acme Inc", "facts": {"us-gaap": {}, "dei": {}}}
    for ns, tag, units in [_cf("Revenues", 400e6), _cf("NetIncomeLoss", 40e6), _cf("OperatingIncomeLoss", 60e6), _cf("DepreciationDepletionAndAmortization", 20e6),
                           _cf("CashAndCashEquivalentsAtCarryingValue", 20e6, start=None), _cf("LongTermDebt", 60e6, start=None),
                           _cf("Revenues", 999e6, start="2023-10-01"),                                    # quarterly entry must be ignored
                           _cf("EntityCommonStockSharesOutstanding", 50e6, unit="shares", ns="dei", start=None, form="10-K")]:
        node = facts["facts"][ns].setdefault(tag, {"units": {}}); 
        for u, ent in units.items(): node["units"].setdefault(u, []).extend(ent)
    f = sec_facts.parse_financials(facts)
    assert f["revenue_m"] == 400.0 and f["net_income_m"] == 40.0 and f["ebitda_m"] == 80.0 and f["debt_m"] == 60.0 and f["shares_m"] == 50.0 and f["cash_m"] == 20.0

def test_check_numbers_for_narrative():
    from app.rag import check_numbers
    known = {"pct": [-14.3, 30.0], "multiple": [3.35], "usd_m": [1300.0], "usd": [26.0]}
    out = check_numbers("Offer $26.00, equity value $1.3 billion, 30% premium, 3.35x revenue, -14.3% dilution, and a surprise 77% figure.", "", known)
    st = {c["value"]: c["status"] for c in out}
    assert st["$26.00"] == "table_match" and st["$1.3 billion"] == "table_match" and st["30%"] == "table_match" and st["3.35x"] == "table_match"
    assert st["77%"] == "unverified"

def test_analyze_end_to_end_with_fakes(monkeypatch):
    from app import analyze, sec_facts, edgar, ml
    fin_a = {"entity": "Acq", "shares_m": 100.0, "net_income_m": 500.0, "revenue_m": 5000.0, "ebitda_m": 900.0, "cash_m": 100.0, "debt_m": 0.0, "sources": {"x": 1}}
    fin_t = {"entity": "Tgt", "shares_m": 50.0, "net_income_m": 40.0, "revenue_m": 400.0, "ebitda_m": 80.0, "cash_m": 20.0, "debt_m": 60.0, "sources": {"x": 1}}
    rs = {"acq": {"cik_str": 1, "ticker": "ACQ", "title": "Acq Corp"}, "tgt": {"cik_str": 2, "ticker": "TGT", "title": "Tgt Inc"}}
    monkeypatch.setattr(sec_facts, "resolve", lambda q: (rs[q], [rs[q]]))
    monkeypatch.setattr(sec_facts, "financials", lambda cik: fin_a if cik == 1 else fin_t)
    monkeypatch.setattr(edgar, "sic_for", lambda cik: ("7372", "Services-Prepackaged Software"))
    def no_model(*a, **k): raise RuntimeError("Model not trained")
    monkeypatch.setattr(ml, "predict", no_model)
    monkeypatch.setattr(analyze, "comps", lambda s: {"n": 8, "scope": "same sector", "p25": 22.0, "median": 31.0, "p75": 42.0, "min": 10.0, "max": 77.0, "recent": []})
    r = analyze.run({"acquirer": "acq", "target": "tgt", "acquirer_price": 50.0, "target_price": 20.0, "premium_pct": 30.0, "pct_cash": 50.0}, with_narrative=False)
    assert r["premium_view"]["points"] == [22.0, 30.0, 31.0, 42.0] or r["premium_view"]["points"] == [22.0, 30.0, 31.0, 42.0]
    assert r["premium_view"]["source"].startswith("precedent quartiles")
    assert abs(r["base"]["equity_value_m"] - 1300.0) < 1e-6 and r["sector"] == "Technology" and len(r["grid"]) == 3 * len(r["premium_view"]["points"])
    k = analyze._known(r); assert 1300.0 in [round(x, 1) for x in k["usd_m"]]
    try: analyze.run({"acquirer": "acq", "target": "tgt", "acquirer_price": 0, "target_price": 20.0}, with_narrative=False); assert False
    except ValueError: pass


# ---- guards added after verifying the second live run ----
def test_date_skips_proxy_statement_and_amendment_dates():
    from app.extractor import extract_date
    t = "The Merger Agreement is described in this proxy statement, which is dated August 27, 2025. Later: the Agreement and Plan of Merger, dated as of July 14, 2025, among"
    assert str(extract_date(t)[0]) == "2025-07-14"
    t2 = "Amendment to the Agreement and Plan of Merger, dated as of March 21, 2023. The Agreement and Plan of Merger, dated as of December 13, 2022, by and between"
    assert str(extract_date(t2)[0]) == "2022-12-13"

def test_premium_range_is_not_used():
    from app.extractor import extract_premiums, pick_premium
    c = extract_premiums("to be paid in cash (representing a 26.6% - 29.0% premium to the $8.06 price per share of the Company common stock as of the close of trading on October 4, 2023).")
    assert c and all(x["ref"] == "range" for x in c) and pick_premium(c) == (None, "range")
    c2 = extract_premiums("representing a premium of 26.6% to 29.0% over the closing price on October 4, 2023.")
    assert pick_premium(c2)[0] is None

def test_price_per_share_close_of_trading_is_spot():
    from app.extractor import extract_premiums
    c = extract_premiums("representing a 47.8% premium to the $9.64 price per share of the Company common stock as of the close of trading on May 17, 2023")
    assert c[0]["ref"] == "spot_close"

def test_premium_outlier_flagged_and_not_high():
    r = extract("the Agreement and Plan of Merger, dated as of May 1, 2023, with Acme Holdings, Inc., a Delaware corporation. a premium of approximately 139% over the closing price on April 3, 2023.", "Penns Woods Bancorp")
    assert "premium_outlier_gt100" in r["flags"] and r["confidence"] == "medium"

def test_date_plausibility_flags():
    from datetime import date
    from app.ingest import date_flags
    assert date_flags(date(2025, 8, 27), "2025-08-20") == ["date_after_filing"]
    assert date_flags(date(2025, 8, 20), "2025-08-27") == ["date_within_14d_of_filing"]
    assert date_flags(date(2022, 1, 1), "2023-06-01") == ["date_over_13mo_before_filing"]
    assert date_flags(date(2025, 5, 1), "2025-08-27") == []

# ---- feature pack ----
def test_breakeven_premium_is_consistent():
    from app import features, dealmath
    p = features.breakeven_premium(ACQ, TGT, 1.0, 30.0)
    assert p is not None and abs(dealmath.scenario(ACQ, TGT, p, 1.0, 30.0)["eps_accretion_pct"]) < 0.05
    assert features.breakeven_premium(ACQ, TGT, 1.0, 0.0) is None or dealmath.scenario(ACQ, TGT, 0, 1.0, 0.0)["eps_accretion_pct"] >= 0

def test_sensitivity_and_percentile_and_football():
    from app import features
    s = features.sensitivity(ACQ, TGT, 30, 1.0, [0.0, 24.667])
    assert s[0]["eps_accretion_pct"] < 0 and abs(s[1]["eps_accretion_pct"]) < 0.01
    assert features.percentile_rank(30, [10, 20, 30, 40]) == 75.0 and features.percentile_rank(5, []) is None
    pv = {"comps": {"n": 5, "min": 5, "max": 60, "p25": 20, "p75": 40}, "ml": {"low_p10": 15, "high_p90": 45}}
    assert [x["label"] for x in features.football(pv, 33)] == ["Precedent min-max", "Precedent IQR", "ML P10-P90", "Your premium"]

def test_risk_flags_trigger():
    from app import features, dealmath
    big = dealmath.scenario(ACQ, dict(TGT, price=200.0), 40, 1.0)      # huge deal relative to acquirer
    f = features.risk_flags(big, 40.0, {"comps": {"n": 3, "p75": 35}})
    txt = " ".join(x["text"] for x in f)
    assert "market cap" in txt and "dilution" in txt and "Only 3 precedent" in txt and "above the precedent 75th" in txt

def test_quality_stats_and_csv(monkeypatch):
    from app import features
    import json
    deals = [{"confidence": "high", "premium": 30.0, "acquirer": "A", "ann_date": "2023-01-01", "deal_value_musd": None, "flags": json.dumps(["premium_not_spot", "value_ctx: x"])},
             {"confidence": "medium", "premium": None, "acquirer": "B", "ann_date": "2023-02-01", "deal_value_musd": 5.0, "flags": "[]"}]
    unp = [{"reasons": json.dumps(["date", "no_premium_or_value"])}]
    monkeypatch.setattr(features, "rows", lambda sql, a=(): deals if "FROM deals" in sql else unp)
    q = features.quality()
    assert q["parse_rate_pct"] == 66.7 and q["coverage_pct"]["premium"] == 50.0 and q["coverage_pct"]["deal_value"] == 50.0 and ("premium_not_spot", 1) in q["top_flags"]
    monkeypatch.setattr(features, "rows", lambda sql, a=(): [{"target": "T", "premium": 5}])
    assert features.export_csv().splitlines()[0] == "target,premium"

def test_report_markdown_has_sections():
    from app import features, dealmath
    b = dealmath.scenario(ACQ, TGT, 30, 0.5)
    r = {"acquirer": {"name": "Acq"}, "target": {"name": "Tgt"}, "sector": "Tech", "disclaimer": "d", "base": b, "grid": [b], "warnings": ["w"], "risk_flags": [{"level": "info", "text": "x"}], "narrative": None}
    md = features.report_md(r)
    assert "# Deal analysis: Acq + Tgt" in md and "## Risk flags" in md and "| Premium |" in md

def test_saved_analyses_roundtrip(tmp_path, monkeypatch):
    from app import features, db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    i = features.save_analysis("t1", {"a": 1}); assert features.get_analysis(i) == {"a": 1} and features.list_analyses()[0]["title"] == "t1"
    features.delete_analysis(i); assert features.get_analysis(i) is None

# ---- pack 2 ----
def _fake_rows(monkeypatch, mapping):
    from app import features
    monkeypatch.setattr(features, "rows", lambda sql, a=(): next((v for k, v in mapping.items() if k in sql), []))

def test_acquirers_grouping(monkeypatch):
    _fake_rows(monkeypatch, {"FROM deals WHERE acquirer": [{"acquirer": "X", "target": "A", "premium": 20.0}, {"acquirer": "X", "target": "B", "premium": 40.0}, {"acquirer": "Y", "target": "C", "premium": None}]})
    from app import features
    r = features.acquirers(); assert r[0]["acquirer"] == "X" and r[0]["deals"] == 2 and r[0]["median_premium"] == 30.0 and r[1]["median_premium"] is None

def test_histogram_and_forecast(monkeypatch):
    from app import features
    _fake_rows(monkeypatch, {"SELECT premium FROM deals": [{"premium": v} for v in (5, 15, 25, 25, 45, 80)]})
    h = features.histogram(); assert sum(x["n"] for x in h) == 6 and h[2]["n"] == 2 and h[0]["bin"] == "0-10%"
    _fake_rows(monkeypatch, {"substr(ann_date": [{"y": "2021", "premium": p} for p in (20, 22)] + [{"y": "2022", "premium": p} for p in (30, 32)] + [{"y": "2023", "premium": p} for p in (40, 42)]})
    f = features.forecast(); assert f["available"] and f["next_year"] == 2024 and abs(f["projected_median"] - 51.0) < 0.6 and f["slope_pts_per_year"] > 9
    _fake_rows(monkeypatch, {"substr(ann_date": [{"y": "2021", "premium": 20}]})
    assert features.forecast()["available"] is False

def test_compare_and_price_parse_and_refresh_window():
    from app import features, dealmath
    from datetime import date
    mk = lambda p: {"base": dealmath.scenario(ACQ, TGT, p, 0.5), "breakeven_premium": 12.0}
    rows_ = features.compare(mk(20), mk(30)); d = {x["metric"]: x for x in rows_}
    assert d["Premium %"]["diff"] == 10.0 and d["Break-even premium %"]["diff"] == 0.0 and d["Equity value $M"]["diff"] > 0
    assert features.parse_stooq("Symbol,Date,Time,Open,High,Low,Close,Volume\nAAPL.US,2026-10-06,22:00:09,1,2,0.5,189.25,100\n") == {"ticker": "AAPL", "close": 189.25, "date": "2026-10-06"}
    try: features.parse_stooq("Symbol,Date,Time,Open,High,Low,Close,Volume\nZZZZ.US,N/D,N/D,N/D,N/D,N/D,N/D,N/D\n"); assert False
    except ValueError: pass
    assert features.refresh_window("2025-06-01", date(2025, 10, 6)) == ("2025-01-02", "2025-10-06")
    assert features.refresh_window(None, date(2025, 10, 6))[0] == "2024-10-06"

def test_watchlist_roundtrip(tmp_path, monkeypatch):
    from app import features, db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "w.db")
    features.watch_add("msft", "target?"); features.watch_add("MSFT", "updated")
    w = features.watch_list(); assert len(w) == 1 and w[0]["ticker"] == "MSFT" and w[0]["note"] == "updated"
    features.watch_del(w[0]["id"]); assert features.watch_list() == []

# ---- pack 3: valuation / mlplus / ops / ragplus ----
def test_valuation_hand_calculated():
    from app import valuation as v
    assert abs(v.premium_paid_m(TGT, 30) - 300.0) < 1e-9
    assert abs(v.synergy_value_m(100, 0.25) - 75 / 0.07) < 1e-9 and v.synergy_value_m(100, 0.25, 0.02, 0.02) is None
    vc = v.value_creation(ACQ, TGT, 30, 100, 0.25)
    assert abs(vc["net_value_created_m"] - (75 / 0.07 - 300 - 1300 * 0.015)) < 1e-9 and abs(vc["payback_years"] - 4.0) < 1e-9
    assert abs(v.exchange_ratio(26.0, 50.0, 0.0) - 0.52) < 1e-9 and abs(v.exchange_ratio(26.0, 50.0, 0.5) - 0.26) < 1e-9
    assert v.breakeven_acquirer_price(ACQ, TGT, 30, 0.0, 0.0, 0.25, 0.06) is not None
    assert abs(v.breakeven_acquirer_price(ACQ, TGT, 30, 0.0, 0.0, 0.25, 0.06) - 162.5) < 0.05
    assert v.breakeven_acquirer_price(ACQ, TGT, 30, 1.0, 0.0, 0.25, 0.06) is None

def test_valuation_collar_leverage_mc_tornado():
    from app import valuation as v
    c = v.collar_table(ACQ, TGT, 30, 0.5); mid = next(x for x in c if x["acq_price_move_pct"] == 0)
    assert abs(mid["value_per_target_share"] - 26.0) < 1e-9 and abs(mid["effective_premium_pct"] - 30.0) < 0.05 and c[0]["value_per_target_share"] < 26.0
    lc = v.max_cash_at_leverage(ACQ, TGT, 30, 0.0, cap=3.5)
    assert abs(lc["capacity_m"] - (3.5 * 980 - (60 - 120))) < 1e-9 and lc["max_pct_cash"] == 1.0
    om = v.optimal_mix(ACQ, TGT, 30, 100.0, 0.25, 0.06, cap=3.5); assert om and 0 <= om["pct_cash"] <= 1 and om["pf_net_debt_ebitda"] <= 3.5
    mc = v.monte_carlo(ACQ, TGT, 30, 50.0, 0.5, 0.25, 0.06, n=300, seed=1)
    assert mc["p5"] <= mc["p50"] <= mc["p95"] and 0 <= mc["prob_accretive_pct"] <= 100 and sum(h["n"] for h in mc["hist"]) == mc["n"]
    assert v.monte_carlo(ACQ, TGT, 30, 50.0, 0.5, 0.25, 0.06, n=300, seed=1) == mc          # reproducible
    tn = v.tornado(ACQ, TGT, 30, 0.5, 50.0, 0.25, 0.06); assert [r["swing"] for r in tn] == sorted([r["swing"] for r in tn], reverse=True) and len(tn) == 5
    adv = v.advanced(ACQ, TGT, 30, 0.5, 20.0, 0.25, 0.06)
    assert {"value_creation", "contribution", "monte_carlo", "tornado", "collar", "credit", "leverage_cap"} <= set(adv)
    assert adv["contribution"]["rows"][2]["target_pct"] == round(40 / 540 * 100, 1)

def test_mlplus_on_synthetic(monkeypatch):
    import numpy as np, pandas as pd
    from app import ml, mlplus
    rng = np.random.default_rng(0); n = 80
    df = pd.DataFrame({"target": [f"T{i}" for i in range(n)], "sector": rng.choice(["Technology", "Healthcare", "Financials"], n), "year": rng.integers(2021, 2026, n), "deal_value_musd": rng.uniform(50, 8000, n)})
    df["premium"] = 20 + 10 * (df["sector"] == "Technology") + rng.normal(0, 3, n); df["value_bucket"] = df["deal_value_musd"].map(ml.bucket)
    cmp_ = mlplus.model_compare(df); assert {r["model"] for r in cmp_} == {"mean baseline", "ridge", "random forest", "gradient boosting"} and any(r["beats_baseline"] for r in cmp_)
    assert list(mlplus.permutation_report(df))[0] == "sector"                 # sector is the real signal in this synthetic set
    assert 0 <= mlplus.interval_coverage(df)["coverage_pct"] <= 100 and len(mlplus.learning_curve(df)) == 4 and len(mlplus.worst_misses(df)) == 5
    assert mlplus.diagnostics(df.head(5))["available"] is False
    rows_ = [{"sector": "A", "ann_date": "2021-01-01", "premium": 10.0}, {"sector": "B", "ann_date": "2025-01-01", "premium": 20.0}, {"sector": "B", "ann_date": "2022-01-01", "premium": 30.0}]
    assert mlplus.similar_deals(rows_, "B", 2025, 2)[0]["premium"] == 20.0

def test_ops_ratelimit_cache_validate_normalize(tmp_path):
    from app import ops
    rl = ops.RateLimiter(capacity=2, per_sec=1.0)
    assert rl.allow("a", 0.0) and rl.allow("a", 0.0) and not rl.allow("a", 0.0) and rl.allow("a", 1.1) and rl.allow("b", 0.0)
    calls = []; fetch = lambda: calls.append(1) or {"x": 1}
    assert ops.cached_json("k", 100, fetch, base=tmp_path, now=1000.0) == {"x": 1}
    import os; f = next(tmp_path.iterdir()); os.utime(f, (1000.0, 1000.0))
    ops.cached_json("k", 100, fetch, base=tmp_path, now=1050.0); assert len(calls) == 1
    ops.cached_json("k", 100, fetch, base=tmp_path, now=1200.0); assert len(calls) == 2
    assert ops.validate_analyze({"acquirer": "A", "target": "B", "acquirer_price": 10, "target_price": 5, "pct_cash": 50}) == []
    errs = ops.validate_analyze({"acquirer": "A", "target": "a", "acquirer_price": 0, "target_price": 5, "pct_cash": 150, "tax_rate": 90})
    assert len(errs) == 4
    assert ops.normalize_company("Microsoft Corporation") == "microsoft" and ops.normalize_company("The Doctors Company, Inc.") == "doctors"

def test_ragplus_routing_rerank_cache():
    from app import ragplus
    deals = [{"target": "ODP Corp", "premium": 34.5, "premium_ref": "spot_close", "acquirer": "ACR Ocean Resources LLC", "ann_date": "2025-09-22", "confidence": "high"}]
    r = ragplus.route_question("What premium did ODP stockholders get and who is the acquirer?", deals)
    assert r and "34.5%" in r["answer"] and "ACR Ocean Resources LLC" in r["answer"] and "not generated by the LLM" in r["answer"]
    assert ragplus.route_question("How do mergers work in general?", deals) is None and ragplus.route_question("Tell me about ODP's board", deals) is None
    docs = ["unrelated boilerplate about voting procedures", "the merger premium was 34.5 percent over closing price", "premium premium premium"]
    out, _ = ragplus.keyword_rerank("merger premium closing price", docs, [{}, {}, {}], alpha=0.9); assert out[0] == docs[1]
    ragplus.cache_put("What is X?", {"a": 1}, now=100.0); assert ragplus.cache_get("what is x", ttl=60, now=130.0) == {"a": 1} and ragplus.cache_get("what is x", ttl=60, now=200.0) is None
