"use client";
import { useState } from "react";
import { api } from "../lib";
export default function QueryBox() {
  const [q, setQ] = useState(""); const [res, setRes] = useState<any>(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const ask = async () => { setBusy(true); setErr(""); setRes(null);
    try { setRes(await api("/query", { method: "POST", body: JSON.stringify({ question: q }) })); } catch (e: any) { setErr(e.message); } setBusy(false); };
  return (<section className="card space-y-3"><h2 className="font-medium">Ask the filings</h2>
    <div className="flex gap-2"><input className="inp flex-1" placeholder="e.g. What premium did ODP stockholders receive?" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && q && ask()} />
      <button className="btn" disabled={busy || !q} onClick={ask}>{busy ? "Thinking…" : "Ask"}</button></div>
    {err && <p className="text-red-600 text-sm">{err}</p>}
    {res && <div className="space-y-2 text-sm"><p className="whitespace-pre-wrap">{res.answer}</p>
      {res.number_checks.length > 0 && <div className="flex flex-wrap gap-2">{res.number_checks.map((c: any, i: number) =>
        <span key={i} className={`px-2 py-0.5 rounded border ${c.flag ? "bg-amber-50 border-amber-300 text-amber-800" : "bg-green-50 border-green-300 text-green-800"}`}>
          {c.value}: {c.status === "table_match" ? "matches extracted data" : c.status === "in_source_text_only" ? "in excerpt, not in table" : "UNVERIFIED"}</span>)}</div>}
      {res.any_flagged && <p className="text-amber-700">⚠ Some figures in this answer don't match the extracted table. Verify against the source.</p>}
      <p className="text-slate-500">Timing (ms): {Object.entries(res.timings_ms).map(([k, v]) => `${k.replace("_ms", "")} ${v}`).join(" · ")}</p>
      <details><summary className="cursor-pointer">Sources</summary>{res.sources.map((s: any, i: number) => <p key={i} className="mt-1 text-slate-600"><b>[{i + 1}] {s.target}</b>: {s.excerpt}…</p>)}</details></div>}
  </section>);
}
