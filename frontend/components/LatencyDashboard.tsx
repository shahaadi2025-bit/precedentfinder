"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib";
const NAMES: Record<string, string> = { embed_ms: "Query embedding", retrieve_ms: "Vector retrieval", llm_ms: "LLM generation", crosscheck_ms: "Cross-check", total_ms: "Total" };
export default function LatencyDashboard() {
  const [d, setD] = useState<any>(null);
  const load = () => api("/latency").then(setD).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, []);
  const data = d ? Object.entries(d.stages).map(([k, v]: any) => ({ stage: NAMES[k], p50: v.p50, p95: v.p95, p99: v.p99 })) : [];
  return (<section className="card space-y-3"><h2 className="font-medium">RAG latency (p50 / p95 / p99, last {d?.n ?? 0} queries)</h2>
    {d?.n ? <><div className="h-64"><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="stage" /><YAxis unit=" ms" width={70} /><Tooltip /><Legend />
      <Bar dataKey="p50" fill="#0f172a" /><Bar dataKey="p95" fill="#64748b" /><Bar dataKey="p99" fill="#cbd5e1" /></BarChart></ResponsiveContainer></div>
      {d.n < 20 && <p className="text-xs text-slate-500">Only {d.n} queries logged — p95/p99 are not meaningful below ~20–100 samples.</p>}</> : <p className="text-sm text-slate-600">No queries logged yet. Ask a question above.</p>}
  </section>);
}
