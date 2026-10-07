"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib";
export default function Predictor() {
  const [sectors, setSectors] = useState<string[]>([]); const [sector, setSector] = useState(""); const [value, setValue] = useState(""); const [year, setYear] = useState(new Date().getFullYear());
  const [res, setRes] = useState<any>(null); const [m, setM] = useState<any>(null); const [err, setErr] = useState("");
  const load = () => api("/ml/metrics").then(setM).catch(() => {});
  useEffect(() => { api("/sectors").then(s => { setSectors(s); setSector(s[0] || ""); }).catch(() => {}); load(); }, []);
  const train = async () => { setErr(""); try { setM(await api("/ml/train", { method: "POST" })); } catch (e: any) { setErr(e.message); } };
  const go = async () => { setErr(""); try { setRes(await api("/ml/predict", { method: "POST", body: JSON.stringify({ sector, deal_value_musd: value ? +value : null, year }) })); } catch (e: any) { setErr(e.message); } };
  const imp = (res?.feature_importance || m?.feature_importance) ? Object.entries(res?.feature_importance || m.feature_importance).map(([k, v]) => ({ k, v })) : [];
  return (<section className="card space-y-3"><h2 className="font-medium">Premium estimator</h2>
    <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">Data-driven estimate from a limited historical sample — not a guaranteed outcome. Real premiums depend on deal-specific factors this model does not see.</p>
    <div className="flex flex-wrap gap-2 text-sm items-center">
      <select className="inp" value={sector} onChange={e => setSector(e.target.value)}>{sectors.map(s => <option key={s}>{s}</option>)}</select>
      <input className="inp w-36" placeholder="Deal value ($M)" value={value} onChange={e => setValue(e.target.value)} />
      <input className="inp w-24" type="number" value={year} onChange={e => setYear(+e.target.value)} />
      <button className="btn" onClick={go}>Estimate</button><button className="btn bg-slate-600" onClick={train}>(Re)train model</button></div>
    {err && <p className="text-red-600 text-sm">{err}</p>}
    {res && <p className="text-lg">Estimated premium: <b>{res.point}%</b> <span className="text-sm text-slate-600">(10th–90th pct across trees: {res.low_p10}%–{res.high_p90}%; trained on {res.n_train} deals; test MAE {res.test_mae} pts)</span></p>}
    {m?.trained && <div className="text-sm text-slate-700 space-y-1"><p>Held-out test: MAE <b>{m.test_mae}</b> pts, R² <b>{m.test_r2}</b> (n={m.n_test}); mean-only baseline MAE {m.baseline_mean_mae}; 5-fold CV MAE {m.cv_mae_mean} ± {m.cv_mae_std}.
      {m.beats_baseline ? "" : " ⚠ The model does NOT beat a predict-the-average baseline."}</p>
      <details><summary className="cursor-pointer">Where it performs poorly (per-sector test MAE)</summary>{Object.entries(m.per_sector_test_mae).map(([k, v]: any) => <p key={k}>{k}: {v.mae} pts (n={v.n})</p>)}</details></div>}
    {m && !m.trained && <p className="text-sm text-slate-600">{m.reason || "Model not trained yet."}</p>}
    {imp.length > 0 && <div><p className="text-sm font-medium">What's driving the prediction (feature importance)</p>
      <div className="h-40"><ResponsiveContainer><BarChart data={imp} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="k" width={90} /><Tooltip /><Bar dataKey="v" fill="#0f172a" /></BarChart></ResponsiveContainer></div></div>}
  </section>);
}
