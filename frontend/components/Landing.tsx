"use client";
import { useEffect, useRef, useState } from "react";

function useReveal() {
  useEffect(() => {
    const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && e.target.classList.add("in")), { threshold: 0.15 });
    document.querySelectorAll(".reveal").forEach(el => io.observe(el)); return () => io.disconnect();
  }, []);
}
function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const [v, setV] = useState(0); const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => { if (!e.isIntersecting) return; io.disconnect(); const t0 = performance.now();
      const tick = (t: number) => { const p = Math.min(1, (t - t0) / 1400); setV(Math.round(to * (1 - Math.pow(1 - p, 3)))); if (p < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
    if (ref.current) io.observe(ref.current); return () => io.disconnect();
  }, [to]);
  return <span ref={ref}>{v}{suffix}</span>;
}

function HeroGraphic() {
  return (<svg viewBox="0 0 560 380" className="w-full max-w-xl" role="img" aria-label="Animated diagram: acquirer and target companies linked by a premium, with EPS impact bars">
    <defs><linearGradient id="g1" x1="0" x2="1"><stop offset="0" stopColor="#6366f1" /><stop offset="1" stopColor="#06b6d4" /></linearGradient>
      <filter id="blur"><feGaussianBlur stdDeviation="18" /></filter></defs>
    <circle cx="120" cy="90" r="70" fill="#6366f1" opacity=".35" filter="url(#blur)" className="float" /><circle cx="450" cy="300" r="80" fill="#06b6d4" opacity=".3" filter="url(#blur)" className="float2" />
    <g className="float"><rect x="30" y="60" width="150" height="86" rx="14" fill="#fff" stroke="#c7d2fe" /><text x="105" y="95" textAnchor="middle" fontSize="13" fill="#64748b">ACQUIRER</text><text x="105" y="122" textAnchor="middle" fontSize="20" fontWeight="700" fill="#0f172a">Acme Corp</text></g>
    <g className="float2"><rect x="380" y="60" width="150" height="86" rx="14" fill="#fff" stroke="#a5f3fc" /><text x="455" y="95" textAnchor="middle" fontSize="13" fill="#64748b">TARGET</text><text x="455" y="122" textAnchor="middle" fontSize="20" fontWeight="700" fill="#0f172a">Nova Inc</text></g>
    <path d="M180 103 C 250 40, 310 40, 380 103" fill="none" stroke="url(#g1)" strokeWidth="3" className="flow" />
    <circle cx="280" cy="58" r="22" fill="#6366f1" className="ring" /><circle cx="280" cy="58" r="22" fill="url(#g1)" /><text x="280" y="63" textAnchor="middle" fontSize="13" fontWeight="700" fill="#fff">+31%</text>
    <text x="280" y="170" textAnchor="middle" fontSize="12" fill="#64748b">premium from precedent filings + ML</text>
    <g transform="translate(70,210)"><text x="0" y="-8" fontSize="12" fill="#64748b">EPS impact by cash mix</text>
      {[["0%", 52, "#ef4444"], ["50%", 34, "#f59e0b"], ["100%", 18, "#22c55e"]].map(([l, h, c], i) => (<g key={i} transform={`translate(${i * 120},0)`}>
        <rect x="0" y={120 - (h as number)} width="60" height={h as number} rx="6" fill={c as string} className="bar" style={{ animationDelay: `${0.4 + i * 0.25}s` }} /><text x="30" y="140" textAnchor="middle" fontSize="12" fill="#475569">{l as string} cash</text></g>))}</g>
  </svg>);
}

function Pipeline() {
  const steps = [["📄", "SEC EDGAR", "DEFM14A / 8-K filings"], ["🔎", "Extract", "regex + confidence"], ["🧠", "Embed", "MiniLM + ChromaDB"], ["📈", "Model", "Random Forest premiums"], ["💬", "Explain", "local LLM + number checks"]];
  return (<div className="relative"><svg className="absolute left-0 right-0 top-10 w-full h-2 hidden md:block" preserveAspectRatio="none" viewBox="0 0 100 2"><line x1="8" x2="92" y1="1" y2="1" stroke="#6366f1" strokeWidth=".4" className="flow" /></svg>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 relative">{steps.map(([i, t, d], k) => (<div key={k} className="reveal text-center" style={{ transitionDelay: `${k * 120}ms` }}>
      <div className="mx-auto w-20 h-20 rounded-2xl bg-white shadow-lg border border-indigo-100 flex items-center justify-center text-3xl float" style={{ animationDelay: `${k * 0.4}s` }}>{i}</div>
      <p className="mt-3 font-semibold text-slate-900">{t}</p><p className="text-sm text-slate-500">{d}</p></div>))}</div></div>);
}

const FEATURES = [
  ["🧾", "Filing extraction", "Target, acquirer, date, premium and reference type pulled from proxies; low-confidence filings stay 'unparsed' with reasons."],
  ["🛡️", "Evidence & guardrails", "Range, outlier, date-plausibility and SPAC checks; a review script shows the sentence behind every field."],
  ["🤖", "Ask the filings", "Local RAG with a small open model; every number in the answer is cross-checked against the extracted table."],
  ["🎯", "Premium estimator", "Random Forest with honest hold-out metrics, baseline comparison and a P10–P90 range."],
  ["⚖️", "Deal analyzer", "Two companies in, scenarios out: offer price, EV multiples, EPS accretion at 0/50/100% cash, break-even synergies."],
  ["🏁", "Football field", "Precedent IQR, ML range and your premium on one scale, plus your percentile versus precedents."],
  ["🚩", "Risk flags", "Rule-based warnings: size vs market cap, leverage, dilution, ownership split, thin comps."],
  ["📊", "Dataset insights", "Premium by sector and year, parse rate, field coverage, top rejection reasons."],
  ["💾", "Save & export", "Saved analyses, Markdown reports, CSV export of the precedent table, dark mode."],
];

export default function Landing() {
  useReveal();
  return (<div className="bg-gradient-to-b from-slate-50 via-white to-indigo-50 text-slate-900 overflow-x-hidden">
    <nav className="max-w-6xl mx-auto flex items-center justify-between p-5"><span className="font-bold text-lg">◆ PrecedentFinder</span>
      <div className="flex gap-5 text-sm items-center"><a href="#features" className="hidden sm:block">Features</a><a href="#how" className="hidden sm:block">How it works</a><a href="/dashboard" className="rounded-full bg-slate-900 text-white px-4 py-1.5">Open dashboard →</a></div></nav>
    <section className="max-w-6xl mx-auto px-5 pt-8 pb-20 grid md:grid-cols-2 gap-10 items-center">
      <div style={{ animation: "fadeUp .9s both" }}><p className="inline-block text-xs font-semibold tracking-wider text-indigo-700 bg-indigo-100 rounded-full px-3 py-1">FREE · LOCAL-FIRST · NO PAID APIs</p>
        <h1 className="mt-4 text-4xl md:text-6xl font-extrabold leading-tight">M&A precedents, <span className="grad-text">premiums</span> and deal math from public filings.</h1>
        <p className="mt-5 text-lg text-slate-600">Extract deal terms from SEC proxies, ask questions in plain English, estimate premiums with an honest model, and test a hypothetical deal between any two US-listed companies.</p>
        <div className="mt-7 flex flex-wrap gap-3"><a href="/dashboard" className="rounded-full bg-indigo-600 text-white px-6 py-3 font-medium shadow-lg shadow-indigo-300/50 hover:-translate-y-0.5 transition">Analyze a deal</a>
          <a href="#how" className="rounded-full border border-slate-300 px-6 py-3 font-medium hover:bg-white transition">See how it works</a></div>
        <p className="mt-4 text-xs text-slate-500">Illustrative analysis, not investment advice. Extracted data can contain errors; verify against the filing.</p></div>
      <div className="flex justify-center"><HeroGraphic /></div></section>
    <section className="bg-slate-900 text-white"><div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 p-10 text-center">
      {[[5, "", "pipeline stages"], [0, "", "paid APIs"], [3, "", "cash mixes per scenario"], [100, "%", "local LLM option"]].map(([v, s, l], i) => (<div key={i} className="reveal"><p className="text-4xl font-extrabold"><Counter to={v as number} suffix={s as string} /></p><p className="text-sm text-slate-300">{l as string}</p></div>))}</div></section>
    <section id="how" className="max-w-6xl mx-auto px-5 py-20"><h2 className="text-3xl font-bold text-center reveal">From filing to insight</h2><p className="text-center text-slate-600 mt-2 mb-12 reveal">Every stage is inspectable: low-confidence results are shown, not hidden.</p><Pipeline /></section>
    <section id="features" className="max-w-6xl mx-auto px-5 pb-20"><h2 className="text-3xl font-bold text-center reveal mb-10">Built for careful analysis</h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{FEATURES.map(([i, t, d], k) => (<div key={k} className="reveal rounded-2xl bg-white border border-slate-200 p-5 shadow-sm hover:shadow-xl hover:-translate-y-1 transition" style={{ transitionDelay: `${(k % 3) * 100}ms` }}>
        <div className="text-3xl">{i}</div><h3 className="mt-2 font-semibold">{t}</h3><p className="text-sm text-slate-600 mt-1">{d}</p></div>))}</div></section>
    <section className="max-w-4xl mx-auto px-5 pb-24 text-center reveal"><div className="rounded-3xl bg-gradient-to-r from-indigo-600 to-cyan-500 text-white p-10 shadow-2xl"><h2 className="text-3xl font-bold">Test your first deal in a minute</h2><p className="mt-2 text-indigo-50">Enter two tickers and today's prices. See scenarios, break-evens and risks.</p>
      <a href="/dashboard" className="inline-block mt-6 rounded-full bg-white text-indigo-700 px-7 py-3 font-semibold hover:scale-105 transition">Open the dashboard</a></div>
      <p className="text-xs text-slate-500 mt-8">Data from SEC EDGAR. Precedent samples are small; the model reports its own error and baseline.</p></section></div>);
}
