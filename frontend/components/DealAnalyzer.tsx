"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API, api } from "../lib";

const n = (v: any, d = 1) => (v === null || v === undefined ? "—" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d }));
const tone = (v: number | null) => (v === null ? "" : v >= 0 ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800");

export default function DealAnalyzer() {
  const [f, setF] = useState({ acquirer: "", target: "", acquirer_price: "", target_price: "", premium_pct: "", pct_cash: "50", synergies_musd: "0", tax_rate: "25", cost_of_debt: "6" });
  const [res, setRes] = useState<any>(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [wantNarr, setWantNarr] = useState(true);
  const [saved, setSaved] = useState<any[]>([]);
  const loadSaved = () => api("/analyses").then(setSaved).catch(() => {});
  useEffect(() => { loadSaved(); const id = new URLSearchParams(window.location.search).get("analysis"); if (id) api(`/analyses/${id}`).then(setRes).catch(() => {}); }, []);
  const [shared, setShared] = useState(""); const save = async () => { const out = await api("/analyses", { method: "POST", body: JSON.stringify({ title: `${res.acquirer.ticker} + ${res.target.ticker} @ ${res.base.premium_pct.toFixed(1)}%`, payload: res }) }); const link = `${window.location.origin}/dashboard?analysis=${out.id}`; setShared(link); navigator.clipboard?.writeText(link); loadSaved(); };
  const download = async () => { const r = await fetch(`${API}/report`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(res) }); const b = await r.blob(); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = `deal-${res.acquirer.ticker}-${res.target.ticker}.md`; a.click(); };
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  const go = async () => {
    setBusy(true); setErr(""); setRes(null);
    try {
      setRes(await api("/analyze", { method: "POST", body: JSON.stringify({
        acquirer: f.acquirer, target: f.target, acquirer_price: +f.acquirer_price, target_price: +f.target_price,
        premium_pct: f.premium_pct === "" ? null : +f.premium_pct, pct_cash: +f.pct_cash, synergies_musd: +f.synergies_musd,
        tax_rate: +f.tax_rate, cost_of_debt: +f.cost_of_debt, narrative: wantNarr }) }));
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };
  const ok = f.acquirer && f.target && +f.acquirer_price > 0 && +f.target_price > 0;
  const prem = res ? [...new Set<number>(res.grid.map((g: any) => g.premium_pct))] : [];
  const mixes = res ? [...new Set<number>(res.grid.map((g: any) => g.pct_cash))] : [];
  const chart = res ? prem.map(p => Object.fromEntries([["premium", `${p}%`], ...mixes.map(m => [`${Math.round(m * 100)}% cash`, res.grid.find((g: any) => g.premium_pct === p && g.pct_cash === m)?.eps_accretion_pct ?? null])])) : [];
  const Fin = ({ c, title }: any) => (<div className="text-sm"><p className="font-medium">{title}: {c.name} <span className="text-slate-500">({c.ticker})</span></p>
    <p className="text-slate-600">Revenue ${n(c.fin.revenue_m, 0)}M · Net income ${n(c.fin.net_income_m, 0)}M · EBITDA ${n(c.fin.ebitda_m, 0)}M · Cash ${n(c.fin.cash_m, 0)}M · Debt ${n(c.fin.debt_m, 0)}M · Shares {n(c.fin.shares_m, 1)}M</p>
    {c.other_matches?.length > 0 && <p className="text-xs text-slate-500">Other matches: {c.other_matches.join("; ")} — use the ticker if this isn't the right company.</p>}</div>);
  return (<section className="card space-y-3"><h2 className="font-medium">Deal analyzer</h2>
    <p className="text-sm text-slate-600">Enter two US-listed companies and today's share prices. Financials come from their latest SEC 10-K; premium ranges come from the model and precedent data; the EPS math is plain arithmetic you can check.</p>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
      <input className="inp" placeholder="Acquirer (name or ticker)" value={f.acquirer} onChange={set("acquirer")} />
      <input className="inp" placeholder="Acquirer share price $" value={f.acquirer_price} onChange={set("acquirer_price")} />
      <input className="inp" placeholder="Target (name or ticker)" value={f.target} onChange={set("target")} />
      <input className="inp" placeholder="Target share price $" value={f.target_price} onChange={set("target_price")} />
      <input className="inp" placeholder="Your premium % (optional)" value={f.premium_pct} onChange={set("premium_pct")} />
      <input className="inp" placeholder="% cash (0-100)" value={f.pct_cash} onChange={set("pct_cash")} />
      <input className="inp" placeholder="Pre-tax synergies $M/yr" value={f.synergies_musd} onChange={set("synergies_musd")} />
      <input className="inp" placeholder="Cost of new debt %" value={f.cost_of_debt} onChange={set("cost_of_debt")} /></div>
    <div className="flex items-center gap-3 text-sm"><button className="btn" disabled={busy || !ok} onClick={go}>{busy ? "Analyzing… (the AI step can take a minute)" : "Analyze deal"}</button>
      <label className="flex gap-1"><input type="checkbox" checked={wantNarr} onChange={e => setWantNarr(e.target.checked)} />Include AI analysis (needs local Ollama)</label></div>
    {err && <p className="text-red-600 text-sm">{err}</p>}
    {saved.length > 0 && <details className="text-sm"><summary className="cursor-pointer">Saved analyses ({saved.length})</summary><ul className="mt-1 space-y-1">{saved.map(x => <li key={x.id} className="flex gap-2">
      <button className="underline" onClick={async () => setRes(await api(`/analyses/${x.id}`))}>{x.title}</button><span className="text-slate-500">{x.ts}</span>
      <button onClick={async () => { await api(`/analyses/${x.id}`, { method: "DELETE" }); loadSaved(); }}>✕</button></li>)}</ul></details>}
    {res && <div className="space-y-4">
      <Fin c={res.acquirer} title="Acquirer" /><Fin c={res.target} title="Target" />
      {res.warnings.map((w: string, i: number) => <p key={i} className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-1.5">⚠ {w}</p>)}
      <div className="grid md:grid-cols-3 gap-3 text-sm">
        <div className="border rounded p-2"><p className="font-medium">Base case</p><p>Premium {n(res.base.premium_pct)}% → offer ${n(res.base.offer_price, 2)}/share</p>
          <p>Equity value ${n(res.base.equity_value_m, 0)}M · EV ${n(res.base.ev_m, 0)}M</p><p>EV/Revenue {n(res.base.ev_revenue, 2)}x · EV/EBITDA {n(res.base.ev_ebitda, 2)}x · P/E {n(res.base.offer_pe, 1)}x</p>
          <p>Deal = {n(res.base.size_vs_acq_mcap_pct)}% of acquirer market cap</p></div>
        <div className="border rounded p-2"><p className="font-medium">EPS impact (base)</p><p>Standalone ${n(res.base.eps_standalone, 2)} → pro forma ${n(res.base.eps_pro_forma, 2)}</p>
          <p className={`inline-block px-1 rounded ${tone(res.base.eps_accretion_pct)}`}>{res.base.eps_accretion_pct === null ? "n/a" : `${n(res.base.eps_accretion_pct)}% ${res.base.eps_accretion_pct >= 0 ? "accretive" : "dilutive"}`}</p>
          <p>Target holders own {n(res.base.target_holders_pct)}% of combined</p><p>Break-even pre-tax synergies ${n(res.base.breakeven_synergies_m, 0)}M/yr</p></div>
        <div className="border rounded p-2"><p className="font-medium">Premium view ({res.premium_view.source})</p><p>Scenarios: {res.premium_view.points.map((p: number) => `${p}%`).join(", ")}</p>
          {res.premium_view.comps.n > 0 ? <p>Precedents ({res.premium_view.comps.scope}, n={res.premium_view.comps.n}): median {res.premium_view.comps.median}%, IQR {res.premium_view.comps.p25}–{res.premium_view.comps.p75}%</p> : <p>No precedent data yet — ingest filings first.</p>}
          {res.premium_view.ml ? <p className="text-xs text-slate-500">ML test MAE {res.premium_view.ml.test_mae} pts on n={res.premium_view.ml.n_train} deals — treat as rough.</p> : <p className="text-xs text-slate-500">ML model not trained; using precedent quartiles.</p>}</div></div>
      <div><p className="text-sm font-medium">EPS accretion / dilution by premium and cash mix (%)</p>
        <div className="h-64"><ResponsiveContainer><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="premium" /><YAxis unit="%" width={55} /><Tooltip /><Legend />
          {mixes.map((m, i) => <Bar key={m} dataKey={`${Math.round(m * 100)}% cash`} fill={["#0f172a", "#64748b", "#cbd5e1", "#94a3b8"][i % 4]} />)}</BarChart></ResponsiveContainer></div></div>
      <div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="text-left border-b">{["Premium", "% cash", "Offer $", "Equity $M", "EV/EBITDA", "New debt $M", "Target owns", "EPS accretion", "Break-even syn. $M"].map(h => <th key={h} className="py-1 pr-2">{h}</th>)}</tr></thead>
        <tbody>{res.grid.map((g: any, i: number) => <tr key={i} className="border-b"><td className="py-1 pr-2">{n(g.premium_pct)}%</td><td>{Math.round(g.pct_cash * 100)}%</td><td>{n(g.offer_price, 2)}</td><td>{n(g.equity_value_m, 0)}</td><td>{n(g.ev_ebitda, 1)}x</td>
          <td>{n(g.cash_needs_new_debt_m, 0)}</td><td>{n(g.target_holders_pct)}%</td><td className={tone(g.eps_accretion_pct)}>{g.eps_accretion_pct === null ? "n/a" : `${n(g.eps_accretion_pct)}%`}</td><td>{n(g.breakeven_synergies_m, 0)}</td></tr>)}</tbody></table></div>
      <div className="grid md:grid-cols-3 gap-3 text-sm">
        <div className="border rounded p-2"><p className="font-medium">Break-even & context</p><p>Max EPS-neutral premium at this mix/synergies: <b>{res.breakeven_premium === null ? "none (dilutive even at 0%)" : `${n(res.breakeven_premium)}%`}</b></p>
          <p>Your base premium sits at the <b>{res.premium_percentile ?? "—"}th</b> percentile of precedents</p>
          <p>Cash-on-hand case ({Math.round(res.cash_on_hand_case.pct_cash * 100)}% cash): EPS {res.cash_on_hand_case.eps_accretion_pct === null ? "n/a" : `${n(res.cash_on_hand_case.eps_accretion_pct)}%`}</p></div>
        <div className="border rounded p-2"><p className="font-medium">Synergy sensitivity (EPS %)</p>{res.sensitivity.map((x: any, i: number) => <p key={i}>${n(x.synergies_m, 0)}M → <span className={`px-1 rounded ${tone(x.eps_accretion_pct)}`}>{x.eps_accretion_pct === null ? "n/a" : `${n(x.eps_accretion_pct)}%`}</span></p>)}</div>
        <div className="border rounded p-2"><p className="font-medium">Premium football field</p>{res.football.map((x: any, i: number) => <div key={i} className="mb-1"><div className="flex justify-between text-xs"><span>{x.label}</span><span>{x.low === x.high ? `${x.low}%` : `${x.low}–${x.high}%`}</span></div>
          <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded relative"><div className="absolute h-2 bg-indigo-500 rounded" style={{ left: `${Math.min(x.low, 100)}%`, width: `${Math.max(1.5, Math.min(x.high, 100) - Math.min(x.low, 100))}%` }} /></div></div>)}</div></div>
      <div className="space-y-1">{res.risk_flags.map((r: any, i: number) => <p key={i} className={`text-xs rounded p-1.5 border ${r.level === "high" ? "bg-red-50 border-red-300 text-red-800" : r.level === "medium" ? "bg-amber-50 border-amber-300 text-amber-800" : "bg-slate-50 border-slate-200 text-slate-700"}`}><b>{r.level.toUpperCase()}</b> · {r.text}</p>)}</div>
      <div className="flex gap-2"><button className="btn" onClick={save}>💾 Save analysis</button><button className="btn" onClick={download}>⬇ Download report (.md)</button><button className="btn" onClick={() => window.print()}>🖨 Print / PDF</button></div>
      {shared && <p className="text-xs">Share link copied: <code>{shared}</code> (works for anyone using your running backend)</p>}
      {res.narrative && (res.narrative.available ? <div className="space-y-2 text-sm border rounded p-3"><p className="font-medium">AI analysis (local model + precedent filings)</p>
        <p className="whitespace-pre-wrap">{res.narrative.text}</p>
        <div className="flex flex-wrap gap-2">{res.narrative.number_checks.map((c: any, i: number) => <span key={i} className={`px-2 py-0.5 rounded border text-xs ${c.flag ? "bg-amber-50 border-amber-300 text-amber-800" : "bg-green-50 border-green-300 text-green-800"}`}>{c.value}: {c.status === "table_match" ? "matches computed" : c.status === "in_source_text_only" ? "from excerpts only" : "UNVERIFIED"}</span>)}</div>
        {res.narrative.any_flagged && <p className="text-amber-700 text-xs">⚠ Some figures in the AI text don't match the computed numbers. Trust the tables above.</p>}
        <details><summary className="cursor-pointer text-xs">Precedent excerpts used</summary>{res.narrative.sources.map((s: any, i: number) => <p key={i} className="text-xs text-slate-600 mt-1"><b>{s.target}</b>: {s.excerpt}…</p>)}</details></div>
        : <p className="text-xs text-slate-600">AI analysis unavailable: {res.narrative.reason}</p>)}
      <p className="text-xs text-slate-500">{res.disclaimer}</p></div>}
  </section>);
}
