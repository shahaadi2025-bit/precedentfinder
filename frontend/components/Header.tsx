"use client";
import { useEffect, useState } from "react";
import { API } from "../lib";
export default function Header() {
  const [dark, setDark] = useState(false);
  useEffect(() => { const d = localStorage.getItem("pf-dark") === "1"; setDark(d); document.documentElement.classList.toggle("dark", d); }, []);
  const toggle = () => { const d = !dark; setDark(d); localStorage.setItem("pf-dark", d ? "1" : "0"); document.documentElement.classList.toggle("dark", d); };
  return (<header className="flex items-center justify-between"><div><a href="/" className="text-2xl font-semibold">PrecedentFinder</a>
    <p className="text-sm text-slate-500">Extracted data can contain errors; verify against the filing.</p></div>
    <div className="flex gap-2 text-sm"><a className="inp" href={`${API}/export/deals.csv`}>⬇ CSV</a><button className="inp" onClick={toggle}>{dark ? "☀ Light" : "🌙 Dark"}</button></div></header>);
}
