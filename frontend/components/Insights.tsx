"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib";
export default function Insights() {
  const [s, setS] = useState<any[]>([]); const [t, setT] = useState<any[]>([]); const [q, setQ] = useState<any>(null); const [h, setH] = useState<any[]>([]); const [fc, setFc] = useState<any>(null);
  useEffect(() => { api("/stats/sectors").then(setS).catch(() => {}); api("/stats/trend").then(setT).catch(() => {}); api("/quality").then(setQ).catch(() => {}); api("/stats/histogram").then(setH).catch(() => {}); api("/stats/forecast").then(setFc).catch(() => {}); }, []);
  return (<section className="card space-y-4"><h2 className="font-medium">Dataset insights</h2>
    <div className="grid md:grid-cols-2 gap-4">
      <div><p className="text-sm font-medium">Median spot-close premium by sector (n shown on hover)</p><div className="h-56"><ResponsiveContainer><BarChart data={s}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="sector" tick={{ fontSize: 10 }} /><YAxis unit="%" width={45} /><Tooltip /><Bar dataKey="median" fill="#6366f1" /></BarChart></ResponsiveContainer></div></div>
      <div><p className="text-sm font-medium">Median premium by announcement year</p><div className="h-56"><ResponsiveContainer><LineChart data={t}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="year" /><YAxis unit="%" width={45} /><Tooltip /><Line dataKey="median" stroke="#06b6d4" strokeWidth={2} /></LineChart></ResponsiveContainer></div></div></div>
    <div className="grid md:grid-cols-2 gap-4"><div><p className="text-sm font-medium">Distribution of spot-close premiums</p><div className="h-48"><ResponsiveContainer><BarChart data={h}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bin" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} width={30} /><Tooltip /><Bar dataKey="n" fill="#a855f7" /></BarChart></ResponsiveContainer></div></div>
      <div className="text-sm">{fc && (fc.available ? <p>Trend: median premium moves about <b>{fc.slope_pts_per_year} pts/year</b>; straight-line projection for {fc.next_year}: <b>{fc.projected_median}%</b> (±{fc.resid_std} residual). <span className="text-xs text-amber-700">{fc.note}</span></p> : <p className="text-slate-500">{fc.reason}</p>)}</div></div>
    {q && <div className="text-sm space-y-1"><p className="font-medium">Data quality</p>
      <p>{q.parsed} parsed / {q.unparsed} unparsed ({q.parse_rate_pct}% parse rate). Field coverage: premium {q.coverage_pct.premium}% · acquirer {q.coverage_pct.acquirer}% · date {q.coverage_pct.date}% · deal value {q.coverage_pct.deal_value}%.</p>
      <p className="text-xs text-slate-500">Top flags: {q.top_flags.map((f: any) => `${f[0]} (${f[1]})`).join(", ") || "none"} · Top rejection reasons: {q.top_reject_reasons.map((f: any) => `${f[0]} (${f[1]})`).join(", ") || "none"}</p>
      <p className="text-xs text-amber-700">{q.note}</p></div>}
  </section>);
}
