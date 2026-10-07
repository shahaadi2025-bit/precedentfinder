"use client";
import { useEffect, useState } from "react";
import { api } from "../lib";
export default function DealsTable() {
  const [rows, setRows] = useState<any[]>([]); const [sectors, setSectors] = useState<string[]>([]);
  const [qs, setQs] = useState(""); const [sector, setSector] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [high, setHigh] = useState(false); const [unp, setUnp] = useState<any[]>([]); const [err, setErr] = useState("");
  useEffect(() => { api("/sectors").then(setSectors).catch(e => setErr(e.message)); api("/unparsed").then(setUnp).catch(() => {}); }, []);
  useEffect(() => {
    const q = new URLSearchParams(); if (qs) q.set("q", qs); if (sector) q.set("sector", sector); if (from) q.set("date_from", from); if (to) q.set("date_to", to); if (high) q.set("min_conf", "high");
    api("/deals?" + q).then(setRows).catch(e => setErr(e.message));
  }, [qs, sector, from, to, high]);
  const f = (v: any, s = "") => (v === null || v === undefined ? "—" : v + s);
  return (<section className="card space-y-3"><h2 className="font-medium">Precedent transactions</h2>
    {err && <p className="text-red-600 text-sm">{err}</p>}
    <div className="flex flex-wrap gap-2 items-center text-sm">
      <input className="inp" placeholder="Search target/acquirer" value={qs} onChange={e => setQs(e.target.value)} /><select className="inp" value={sector} onChange={e => setSector(e.target.value)}><option value="">All sectors</option>{sectors.map(s => <option key={s}>{s}</option>)}</select>
      <input type="date" className="inp" value={from} onChange={e => setFrom(e.target.value)} /><input type="date" className="inp" value={to} onChange={e => setTo(e.target.value)} />
      <label className="flex gap-1"><input type="checkbox" checked={high} onChange={e => setHigh(e.target.checked)} />High confidence only</label>
      <span className="text-slate-500">{rows.length} deals · {unp.length} unparsed filings</span></div>
    <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left border-b">
      {["Target", "Acquirer", "Date", "Value ($M)", "Premium", "Multiple", "Sector", "Conf."].map(h => <th key={h} className="py-1 pr-3">{h}</th>)}</tr></thead>
      <tbody>{rows.map(r => <tr key={r.adsh} className="border-b hover:bg-slate-50">
        <td className="py-1 pr-3"><a className="underline" href={r.url} target="_blank">{r.target}</a></td><td className="pr-3">{f(r.acquirer)}</td><td className="pr-3">{r.ann_date}</td>
        <td className="pr-3">{f(r.deal_value_musd)}</td><td className="pr-3" title={r.premium_ref}>{f(r.premium, "%")}</td>
        <td className="pr-3">{r.multiple ? `${r.multiple}x ${r.multiple_type}` : "—"}</td><td className="pr-3">{r.sector}</td>
        <td><span className={r.confidence === "high" ? "text-green-700" : "text-amber-600"}>{r.confidence}</span></td></tr>)}</tbody></table></div>
    {unp.length > 0 && <details className="text-sm"><summary className="cursor-pointer">Unparsed filings (what the extractor refused to guess)</summary>
      <ul className="mt-2 space-y-1">{unp.map(u => <li key={u.adsh}><a className="underline" href={u.url} target="_blank">{u.target}</a> — {u.reasons}</li>)}</ul></details>}
  </section>);
}
