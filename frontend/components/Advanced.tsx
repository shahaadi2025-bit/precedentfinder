"use client";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
const n = (v: any, d = 1) => (v === null || v === undefined ? "—" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d }));
export default function Advanced({ adv }: { adv: any }) {
  const vc = adv.value_creation, mc = adv.monte_carlo, lc = adv.leverage_cap;
  return (<details className="border rounded p-3 text-sm space-y-3"><summary className="cursor-pointer font-medium">Advanced valuation (value creation, risk, leverage, collar)</summary>
    <div className="grid md:grid-cols-3 gap-3 mt-2">
      <div><p className="font-medium">Value-creation test</p><p>Premium paid ${n(vc.premium_paid_m, 0)}M · fees ${n(vc.fees_m, 0)}M</p><p>Capitalized synergies ${n(vc.synergy_value_m, 0)}M</p>
        <p>Net value created: <b className={vc.net_value_created_m >= 0 ? "text-green-700" : "text-red-700"}>${n(vc.net_value_created_m, 0)}M</b></p>
        <p>{vc.share_of_synergies_to_target_pct === null ? "" : `${n(vc.share_of_synergies_to_target_pct, 0)}% of synergy value goes to target holders · `}payback {vc.payback_years === null ? "n/a" : `${n(vc.payback_years)} yrs`}</p><p className="text-xs text-slate-500">{vc.assumptions}</p></div>
      <div><p className="font-medium">Contribution vs ownership</p>{adv.contribution.rows.map((r: any) => <p key={r.metric}>{r.metric}: target contributes {r.target_pct === null ? "n/a" : `${r.target_pct}%`}</p>)}
        <p>Target holders own {adv.contribution.target_holders_ownership_pct}% pro forma</p><p className="text-xs text-slate-500">Acquirer P/E {n(adv.relative_pe.acquirer_pe)}x vs offer P/E {n(adv.relative_pe.offer_pe_target)}x. {adv.relative_pe.note}</p></div>
      <div><p className="font-medium">Leverage & credit</p><p>Debt capacity at {lc.cap_x}x: ${n(lc.capacity_m, 0)}M (max {lc.max_pct_cash === null ? "n/a" : `${n(lc.max_pct_cash * 100, 0)}%`} cash)</p>
        <p>Best EPS mix within cap: {lc.optimal_mix ? `${n(lc.optimal_mix.pct_cash * 100, 0)}% cash → ${n(lc.optimal_mix.eps_accretion_pct)}% EPS` : "none feasible"}</p>
        <p>Pro forma gross debt/EBITDA {n(adv.credit.pf_gross_debt_ebitda, 2)}x · approx. interest cover {n(adv.credit.approx_interest_cover, 1)}x</p>
        <p>Stock exchange ratio {n(adv.exchange_ratio, 3)} acquirer shares per target share · break-even acquirer price {adv.breakeven_acquirer_price === null ? "n/a (cash deal)" : `$${n(adv.breakeven_acquirer_price, 2)}`}</p></div></div>
    {mc && <div><p className="font-medium">Monte Carlo EPS accretion ({mc.n} draws) — {mc.prob_accretive_pct}% chance accretive; P5 {mc.p5}% · median {mc.p50}% · P95 {mc.p95}%</p>
      <div className="h-40"><ResponsiveContainer><BarChart data={mc.hist}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bin" tick={{ fontSize: 10 }} /><YAxis width={30} /><Tooltip /><Bar dataKey="n" fill="#6366f1" /></BarChart></ResponsiveContainer></div><p className="text-xs text-slate-500">{mc.assumption}</p></div>}
    <div className="grid md:grid-cols-2 gap-3"><div><p className="font-medium">What moves EPS most (tornado)</p>{adv.tornado.map((t: any) => <div key={t.driver} className="mb-1"><div className="flex justify-between text-xs"><span>{t.driver}</span><span>{t.low_case}% → {t.high_case}%</span></div>
      <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded"><div className="h-2 bg-amber-500 rounded" style={{ width: `${Math.min(100, t.swing * 4)}%` }} /></div></div>)}</div>
      <div><p className="font-medium">Fixed exchange-ratio collar</p><table className="text-xs w-full"><thead><tr className="text-left border-b"><th>Acq. move</th><th>Value/target share</th><th>Effective premium</th></tr></thead>
        <tbody>{adv.collar.map((c: any) => <tr key={c.acq_price_move_pct} className="border-b"><td>{c.acq_price_move_pct}%</td><td>${n(c.value_per_target_share, 2)}</td><td>{c.effective_premium_pct}%</td></tr>)}</tbody></table></div></div></details>);
}
