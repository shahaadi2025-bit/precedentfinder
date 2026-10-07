import sys, sqlite3, json, collections, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect("data/precedent.db"); c.row_factory = sqlite3.Row
sh = lambda x, n=60: (str(x)[:n] + "...") if x and len(str(x)) > n else x
print("=== PARSED DEALS (target | acquirer | date | premium/ref | conf | flags)")
deals = c.execute("select target,acquirer,ann_date,premium,premium_ref,confidence,flags from deals order by confidence, target").fetchall()
for r in deals: print(sh(r["target"], 28), "|", sh(r["acquirer"]), "|", r["ann_date"], "|", r["premium"], r["premium_ref"], "|", r["confidence"], "|", sh(r["flags"], 150))
sp = [r["premium"] for r in deals if r["premium_ref"] == "spot_close" and r["premium"] is not None and r["premium"] <= 100]
if sp: print(f"\nspot-close premiums <=100%: n={len(sp)} median={statistics.median(sp):.1f} min={min(sp)} max={max(sp)}")
print("\n=== REJECTION REASONS (counts)")
cnt = collections.Counter(); rows = c.execute("select target,reasons,partial from unparsed").fetchall()
for r in rows: cnt[tuple(sorted(set(json.loads(r["reasons"]))))] += 1
for k, v in cnt.most_common(): print(v, k)
print("\n=== EACH UNPARSED")
for r in rows:
    p = json.loads(r["partial"]); print(sh(r["target"], 30), "|", sorted(set(json.loads(r["reasons"]))), "| acq:", sh(p.get("acquirer")), "date:", p.get("date"), "prem:", p.get("premium"), p.get("premium_ref"))
    for pc in (p.get("premium_ctx") or []):
        if pc[1] in ("unknown", "vwap", "range"): print("      ctx:", pc[0], pc[1], "::", pc[2].replace("\n", " "))
