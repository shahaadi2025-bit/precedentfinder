"use client";
import { useEffect, useState } from "react";
import { api } from "../lib";
const n = (v: any, d = 1) => (v === null || v === undefined ? "—" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }));

export default function Tools() {
  const [saved, setSaved] = useState<any[]>([]); const [pick, setPick] = useState<number[]>([]); const [cmp, setCmp] = useState<any>(null);
  const [wl, setWl] = useState<any[]>([]); const [tk, setTk] = useState(""); const [note, setNote] = useState(""); const [acq, setAcq] = useState<any[]>([]);
  const [px, setPx] = useState<any>(null); const [pt, setPt] = useState(""); const [err, setErr] = useState("");
  const load = () => { api("/analyses").then(setSaved).catch(() => {}); api("/watchlist").then(setWl).catch(() => {}); api("/acquirers").then(setAcq).catch(() => {}); };
  useEffect(load, []);
  const toggle = (id: number) => setPick(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id].slice(-2));
  const compare = async () => { setErr(""); try { setCmp(await api(`/compare?a=${pick[0]}&b=${pick[1]}`)); } catch (e: any) { setErr(e.message); } };
  const price = async () => { setErr(""); setPx(null); try { setPx(await api(`/price?ticker=${encodeURIComponent(pt)}`)); } catch (e: any) { setErr(e.message); } };
  return (<section className="card space-y-4 text-sm"><h2 className="font-medium">Tools</h2>{err && <p className="text-red-600">{err}</p>}
    <div><p className="font-medium">Share price lookup <span className="text-xs text-slate-500">(free Stooq quote; may be delayed — confirm before using)</span></p>
      <div className="flex gap-2 mt-1"><input className="inp" placeholder="Ticker e.g. MSFT" value={pt} onChange={e => setPt(e.target.value)} /><button className="btn" disabled={!pt} onClick={price}>Get price</button>
        {px && <span className="self-center">{px.ticker}: <b>${n(px.close, 2)}</b> <span className="text-slate-500">({px.date})</span></span>}</div></div>
    <div><p className="font-medium">Compare saved analyses</p>
      {saved.length < 2 ? <p className="text-slate-500">Save two analyses in the Deal analyzer to compare them here.</p> : <>
        <div className="flex flex-wrap gap-3">{saved.map(s => <label key={s.id} className="flex gap-1"><input type="checkbox" checked={pick.includes(s.id)} onChange={() => toggle(s.id)} />{s.title}</label>)}</div>
        <button className="btn mt-1" disabled={pick.length !== 2} onClick={compare}>Compare</button></>}
      {cmp && <table className="mt-2 text-xs w-full"><thead><tr className="text-left border-b"><th>Metric</th><th>{cmp.a}</th><th>{cmp.b}</th><th>Δ (B−A)</th></tr></thead>
        <tbody>{cmp.rows.map((r: any) => <tr key={r.metric} className="border-b"><td className="py-1">{r.metric}</td><td>{n(r.a, 2)}</td><td>{n(r.b, 2)}</td><td>{n(r.diff, 2)}</td></tr>)}</tbody></table>}</div>
    <div><p className="font-medium">Watchlist</p>
      <div className="flex gap-2 mt-1"><input className="inp w-28" placeholder="Ticker" value={tk} onChange={e => setTk(e.target.value)} /><input className="inp flex-1" placeholder="Note" value={note} onChange={e => setNote(e.target.value)} />
        <button className="btn" disabled={!tk} onClick={async () => { await api("/watchlist", { method: "POST", body: JSON.stringify({ ticker: tk, note }) }); setTk(""); setNote(""); load(); }}>Add</button></div>
      <ul className="mt-1">{wl.map(w => <li key={w.id} className="flex gap-2"><b>{w.ticker}</b><span className="text-slate-500">{w.note}</span><button onClick={async () => { await api(`/watchlist/${w.id}`, { method: "DELETE" }); load(); }}>✕</button></li>)}</ul></div>
    <div><p className="font-medium">Acquirer history (from extracted deals)</p>
      <table className="text-xs w-full"><thead><tr className="text-left border-b"><th>Acquirer</th><th>Deals</th><th>Median premium</th><th>Targets</th></tr></thead>
        <tbody>{acq.slice(0, 15).map(a => <tr key={a.acquirer} className="border-b"><td className="py-1">{a.acquirer}</td><td>{a.deals}</td><td>{a.median_premium === null ? "—" : `${a.median_premium}%`}</td><td>{a.targets.join(", ")}</td></tr>)}</tbody></table></div>
  </section>);
}
