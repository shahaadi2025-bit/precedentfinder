"use client";
import { useState } from "react";
import { api } from "../lib";
export default function Diagnostics() {
  const [d, setD] = useState<any>(null); const [err, setErr] = useState("");
  const run = async () => { setErr(""); try { setD(await api("/ml/diagnostics")); } catch (e: any) { setErr(e.message); } };
  return (<section className="card space-y-2 text-sm"><div className="flex items-center gap-3"><h2 className="font-medium">Model diagnostics</h2><button className="btn" onClick={run}>Run (takes ~10s)</button></div>{err && <p className="text-red-600">{err}</p>}
    {d && !d.available && <p className="text-slate-600">{d.reason}</p>}
    {d?.available && <div className="grid md:grid-cols-2 gap-4"><div><p className="font-medium">Model comparison (5-fold CV MAE, lower is better)</p>{d.model_comparison.map((m: any) => <p key={m.model}>{m.model}: {m.cv_mae} ± {m.cv_std} {m.model !== "mean baseline" && (m.beats_baseline ? "✅ beats baseline" : "❌ no better than baseline")}</p>)}
      <p className="font-medium mt-2">Does the "80% band" really cover 80%?</p><p>Held-out coverage: <b>{d.interval_coverage.coverage_pct}%</b> vs nominal {d.interval_coverage.nominal_pct}% (n={d.interval_coverage.n_test})</p></div>
      <div><p className="font-medium">Permutation importance (MAE increase when shuffled)</p>{Object.entries(d.permutation_importance_mae_increase).map(([k, v]: any) => <p key={k}>{k}: {v}</p>)}
        <p className="font-medium mt-2">Learning curve</p>{d.learning_curve.map((l: any) => <p key={l.n_train}>n={l.n_train}: MAE {l.test_mae}</p>)}</div>
      <div className="md:col-span-2"><p className="font-medium">Biggest misses</p>{d.worst_misses.map((w: any, i: number) => <p key={i}>{w.target ?? "deal"}: actual {w.actual}% vs predicted {w.predicted}% (off by {w.abs_error})</p>)}<p className="text-xs text-slate-500 mt-1">{d.reading_guide}</p></div></div>}</section>);
}
