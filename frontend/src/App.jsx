import React, { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, AlertTriangle, BarChart3, GitCompare, Home, Search, Shuffle, Users } from "lucide-react";
import { api } from "./api.js";
import Players from "./Players.jsx";

const CLASSES = ["0", "1", "2", "3", "4", "6", "W"];
const LIME = "#a3e635", GREY = "#64748b";
const pct = (x) => (100 * x).toFixed(1) + "%";
const PAGES = [["home", "Home", Home], ["matchup", "Matchup", Activity], ["whatif", "What-If", Shuffle],
  ["compare", "Compare", GitCompare], ["players", "Players", Users], ["method", "Model", BarChart3]];

const Badge = ({ src }) => src && (
  <span className={"rounded-full px-2 py-0.5 text-xs " + (src === "DEMO_SYNTHETIC" ? "bg-amber-400/20 text-amber-300" : "bg-lime-400/20 text-lime-300")}>
    {src === "DEMO_SYNTHETIC" ? "DEMO · synthetic data" : "Historical data: " + src} · trained-model estimate</span>);
const Err = ({ e }) => e && <div className="card border-red-400/40 text-red-300">{e}</div>;
const Warn = ({ list }) => list?.length > 0 && (
  <div className="card border-amber-400/30 text-sm text-amber-200">{list.map((w) => <p key={w} className="flex gap-2"><AlertTriangle size={16} className="shrink-0" />{w}</p>)}</div>);

function PlayerInput({ label, value, onChange }) {
  const [opts, setOpts] = useState([]);
  useEffect(() => { api.players(value).then((r) => setOpts(r.players)).catch(() => setOpts([])); }, [value]);
  const id = "dl-" + label;
  return (<label className="block text-sm">{label}
    <div className="relative mt-1"><Search size={14} className="absolute left-3 top-3 text-white/40" />
      <input className="inp pl-8" list={id} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Search players…" /></div>
    <datalist id={id}>{opts.map((o) => <option key={o} value={o} />)}</datalist></label>);
}

function ScenarioForm({ s, set }) {
  return (<div className="grid gap-3 sm:grid-cols-2">
    <PlayerInput label="Batter" value={s.batter} onChange={(v) => set({ ...s, batter: v })} />
    <PlayerInput label="Bowler" value={s.bowler} onChange={(v) => set({ ...s, bowler: v })} />
    <label className="text-sm">Over: {s.over + 1} of 20 ({s.over < 6 ? "powerplay" : s.over < 15 ? "middle" : "death"})
      <input type="range" min="0" max="19" value={s.over} onChange={(e) => set({ ...s, over: +e.target.value })} className="w-full accent-lime-400" /></label>
    <label className="text-sm">Wickets lost: {s.wickets}
      <input type="range" min="0" max="9" value={s.wickets} onChange={(e) => set({ ...s, wickets: +e.target.value })} className="w-full accent-lime-400" /></label>
  </div>);
}

const Stat = ({ k, v }) => <div className="card fade"><div className="text-xs text-white/50">{k}</div><div className="text-2xl font-bold text-lime-300">{v}</div></div>;
const dist = (p) => CLASSES.map((c) => ({ outcome: c, p: +(100 * p[c]).toFixed(2) }));

function Matchup({ s, set, base, setBase }) {
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); setErr(""); try { setBase(await api.predict(s)); } catch (e) { setErr(e.message); } setBusy(false); };
  const ev = base?.evidence.historical_head_to_head;
  return (<div className="space-y-4"><div className="card space-y-3"><ScenarioForm s={s} set={set} />
    <button className="btn" onClick={run} disabled={busy || !s.batter || !s.bowler}>{busy ? "Predicting…" : "Generate baseline prediction"}</button></div>
    <Err e={err} />
    {base && (<div className="space-y-4 fade"><Badge src={base.data_source} /><Warn list={base.warnings} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat k="Wicket prob. (next ball)" v={pct(base.wicket_probability)} /><Stat k="Boundary prob." v={pct(base.boundary_probability)} />
        <Stat k="Exp. runs next ball" v={base.expected_runs_next_ball.toFixed(2)} /><Stat k="Exp. runs next over (approx.)" v={base.expected_runs_next_over.toFixed(1)} /></div>
      <div className="card"><h3 className="mb-2 font-semibold">Next-ball outcome distribution (%)</h3>
        <ResponsiveContainer width="100%" height={240}><BarChart data={dist(base.probabilities)}><CartesianGrid stroke="#ffffff15" /><XAxis dataKey="outcome" stroke="#999" /><YAxis stroke="#999" />
          <Tooltip contentStyle={{ background: "#111", border: "1px solid #333" }} /><Bar dataKey="p" fill={LIME} radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
      <div className="card text-sm"><h3 className="mb-2 font-semibold">Historical evidence (training period)</h3>
        {ev.balls ? <p>Head-to-head: {ev.runs} runs off {ev.balls} balls · SR {ev.strike_rate} · {ev.dismissals} dismissals · {ev.boundary_pct}% boundaries.</p> : <p>No head-to-head balls on record.</p>}
        <p className="text-white/60">Career sample: {base.evidence.batter_balls} balls (batter), {base.evidence.bowler_balls} balls (bowler).</p></div></div>)}</div>);
}

function WhatIf({ s, set, setBase, setAlt, alt }) {
  const [c, setC] = useState({ bowler: "", batter: "", over: null, wickets: null }); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const run = async () => {
    const changes = Object.fromEntries(Object.entries(c).filter(([, v]) => v !== "" && v !== null));
    setBusy(true); setErr("");
    try { const r = await api.whatif(s, changes); setBase(r.baseline); setAlt(r); } catch (e) { setErr(e.message); } setBusy(false); };
  return (<div className="space-y-4"><div className="card space-y-3"><h3 className="font-semibold">1 · Baseline</h3><ScenarioForm s={s} set={set} />
    <h3 className="pt-2 font-semibold">2 · What if… (leave blank to keep baseline)</h3>
    <div className="grid gap-3 sm:grid-cols-2"><PlayerInput label="Different bowler" value={c.bowler} onChange={(v) => setC({ ...c, bowler: v })} />
      <PlayerInput label="Different batter" value={c.batter} onChange={(v) => setC({ ...c, batter: v })} />
      <label className="text-sm">Different over: {c.over === null ? "—" : c.over + 1}<input type="range" min="0" max="19" value={c.over ?? s.over} onChange={(e) => setC({ ...c, over: +e.target.value })} className="w-full accent-lime-400" /></label>
      <label className="text-sm">Different wickets: {c.wickets === null ? "—" : c.wickets}<input type="range" min="0" max="9" value={c.wickets ?? s.wickets} onChange={(e) => setC({ ...c, wickets: +e.target.value })} className="w-full accent-lime-400" /></label></div>
    <button className="btn" onClick={run} disabled={busy || !s.batter || !s.bowler}>{busy ? "Comparing…" : "Run what-if"}</button></div>
    <Err e={err} />
    {alt && (<div className="card fade space-y-2"><Badge src={alt.alternative.data_source} /><p>{alt.briefing}</p>
      <p className="text-xs text-white/50">Briefing source: {alt.briefing_source}. See the Compare page for charts.</p><Warn list={alt.alternative.warnings} /></div>)}</div>);
}

function Compare({ alt }) {
  if (!alt) return <div className="card">Run a what-if first (What-If page).</div>;
  const b = alt.baseline, a = alt.alternative;
  const data = CLASSES.map((c) => ({ outcome: c, Baseline: +(100 * b.probabilities[c]).toFixed(2), Alternative: +(100 * a.probabilities[c]).toFixed(2) }));
  const row = (k, x, y, f) => <tr key={k} className="border-t border-white/10"><td className="py-2">{k}</td><td>{f(x)}</td><td>{f(y)}</td><td className="text-lime-300">{f(y - x)}</td></tr>;
  return (<div className="space-y-4 fade"><Badge src={a.data_source} />
    <div className="card"><ResponsiveContainer width="100%" height={280}><BarChart data={data}><CartesianGrid stroke="#ffffff15" /><XAxis dataKey="outcome" stroke="#999" /><YAxis stroke="#999" />
      <Tooltip contentStyle={{ background: "#111", border: "1px solid #333" }} /><Legend /><Bar dataKey="Baseline" fill={GREY} radius={[6, 6, 0, 0]} /><Bar dataKey="Alternative" fill={LIME} radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
    <div className="card overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-white/50"><th>Metric</th><th>Baseline</th><th>Alternative</th><th>Change</th></tr></thead><tbody>
      {row("Wicket prob.", b.wicket_probability, a.wicket_probability, (v) => (100 * v).toFixed(2) + "%")}
      {row("Boundary prob.", b.boundary_probability, a.boundary_probability, (v) => (100 * v).toFixed(2) + "%")}
      {row("Exp. runs / over", b.expected_runs_next_over, a.expected_runs_next_over, (v) => v.toFixed(2))}</tbody></table></div>
    <p className="text-sm text-white/60">{alt.briefing} Turning-point insights (how a specific wicket or boundary shifts match outcome) are not implemented yet; this model predicts the next ball only.</p></div>);
}

function Method() {
  const [m, setM] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { api.metrics().then(setM).catch((e) => setErr(e.message)); }, []);
  if (err) return <Err e={err} />; if (!m) return <p>Loading…</p>;
  const ll = m.metrics.log_loss, sp = m.metrics.split;
  return (<div className="space-y-4 fade"><Badge src={m.data_source} />
    <div className="card text-sm"><h3 className="mb-2 font-semibold">Test log-loss (lower is better)</h3>
      <p>Global frequency baseline: {ll.global_frequency_baseline.toFixed(4)}</p><p>Phase frequency baseline: {ll.phase_frequency_baseline.toFixed(4)}</p>
      <p className="text-lime-300">Model: {ll.model.toFixed(4)}</p>
      <p className="mt-2 text-white/60">Wicket Brier: baseline {m.metrics.wicket_brier.global_frequency_baseline.toFixed(5)} vs model {m.metrics.wicket_brier.model.toFixed(5)}</p></div>
    <div className="card text-sm text-white/70"><h3 className="mb-2 font-semibold text-white">Methodology</h3>
      <p>Chronological split by match: {sp.train_matches} train / {sp.val_matches} validation / {sp.test_matches} test matches (test from {sp.test_from}, {sp.test_balls} balls). Player rates are computed from training matches only and shrunk toward the league average. Multinomial logistic regression; {m.metrics.calibration_note} What-if results are model estimates, not proof of what would have happened.</p></div></div>);
}

export default function App() {
  const [page, setPage] = useState("home");
  const [s, set] = useState({ batter: "", bowler: "", over: 17, wickets: 3, innings: 1 });
  const [base, setBase] = useState(null); const [alt, setAlt] = useState(null); const [h, setH] = useState(null);
  useEffect(() => { api.health().then(setH).catch(() => setH({ ok: false })); }, []);
  return (<div className="mx-auto max-w-5xl p-4 pb-24">
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-extrabold">MatchupMind <span className="text-lime-400">AI</span></h1>
      <nav className="flex flex-wrap gap-1">{PAGES.map(([k, l, I]) => (<button key={k} onClick={() => setPage(k)}
        className={"flex items-center gap-1 rounded-xl px-3 py-1.5 text-sm " + (page === k ? "bg-lime-400 text-black" : "bg-white/5 hover:bg-white/10")}><I size={14} />{l}</button>))}</nav></header>
    <main key={page} className="fade">
      {page === "home" && (<div className="card space-y-3"><h2 className="text-xl font-bold">Cricket “what if?” simulator</h2>
        <p className="text-white/70">Pick a batter and bowler, generate a next-ball prediction, then change the bowler, batter, over or wickets and compare.</p>
        <p className="text-sm">Backend: {h === null ? "checking…" : h.ok && h.model_loaded ? <span className="text-lime-300">connected, model loaded</span> : h.ok ? <span className="text-amber-300">connected, model not trained yet</span> : <span className="text-red-300">not reachable</span>}</p>
        <button className="btn" onClick={() => setPage("matchup")}>Start with a matchup</button></div>)}
      {page === "matchup" && <Matchup s={s} set={set} base={base} setBase={setBase} />}
      {page === "whatif" && <WhatIf s={s} set={set} setBase={setBase} setAlt={setAlt} alt={alt} />}
      {page === "compare" && <Compare alt={alt} />}
      {page === "players" && <Players s={s} set={set} />}
      {page === "method" && <Method />}</main></div>);
}
