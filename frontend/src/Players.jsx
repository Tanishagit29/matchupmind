import React, { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "./api.js";

const Stat = ({ k, v }) => <div className="card"><div className="text-xs text-white/50">{k}</div><div className="text-xl font-bold text-lime-300">{v}</div></div>;

export default function Players({ s, set }) {
  const [q, setQ] = useState(""), [list, setList] = useState([]), [err, setErr] = useState("");
  const [sel, setSel] = useState(null), [role, setRole] = useState("batter"), [st, setSt] = useState(null);
  useEffect(() => { api.players(q).then((r) => { setList(r.players); setErr(""); }).catch((e) => setErr(e.message)); }, [q]);
  useEffect(() => {
    if (!sel) return;
    setSt(null);
    api.stats(sel, role).then((r) => { setSt(r); setErr(""); }).catch((e) => { setSt(null); setErr(e.message); });
  }, [sel, role]);
  const form = st?.recent_form.map((f, i) => ({ match: "M" + (i + 1), value: role === "batter" ? f.runs : f.wickets, runs: f.runs, balls: f.balls }));
  return (
    <div className="grid gap-4 md:grid-cols-[280px_1fr]">
      <div className="card space-y-2">
        <input className="inp" placeholder="Search players…" value={q} onChange={(e) => setQ(e.target.value)} />
        {list.length === 0 && !err && <p className="text-sm text-white/60">No players found.</p>}
        <ul className="max-h-96 overflow-auto">{list.map((p) => (
          <li key={p}><button onClick={() => setSel(p)} className={"w-full rounded-lg px-2 py-1.5 text-left text-sm " + (sel === p ? "bg-lime-400 text-black" : "hover:bg-white/10")}>{p}</button></li>))}</ul>
      </div>
      <div className="space-y-4">
        {err && <div className="card border-red-400/40 text-red-300">{err}</div>}
        {!sel && <div className="card text-white/60">Select a player to see historical statistics.</div>}
        {sel && (
          <div className="space-y-4">
            <div className="card flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-bold">{sel}</h3>
              <div className="flex gap-2 text-sm">
                {["batter", "bowler"].map((r) => <button key={r} onClick={() => setRole(r)} className={"rounded-lg px-3 py-1 " + (role === r ? "bg-lime-400 text-black" : "bg-white/10")}>{r}</button>)}
                <button className="text-lime-300 hover:underline" onClick={() => set({ ...s, [role]: sel })}>use in simulator</button>
              </div>
            </div>
            {st && (<>
              {st.warnings.map((w) => <div key={w} className="card border-amber-400/30 text-sm text-amber-200">{w}</div>)}
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat k="Balls" v={st.balls} /><Stat k="Runs" v={st.runs} />
                <Stat k={role === "batter" ? "Strike rate" : "Economy"} v={st.strike_rate ?? st.economy} />
                <Stat k={role === "batter" ? "Dismissals" : "Wickets"} v={st.dismissals} />
                <Stat k="Boundary %" v={st.boundary_pct.toFixed(1) + "%"} />
              </div>
              <div className="card">
                <h4 className="mb-2 text-sm font-semibold">Recent form: last {form.length} matches ({role === "batter" ? "runs" : "wickets"})</h4>
                <ResponsiveContainer width="100%" height={200}><BarChart data={form}><CartesianGrid stroke="#ffffff15" /><XAxis dataKey="match" stroke="#999" /><YAxis stroke="#999" />
                  <Tooltip contentStyle={{ background: "#111", border: "1px solid #333" }} formatter={(v, n, p) => [v + " (" + p.payload.runs + " runs / " + p.payload.balls + " balls)", ""]} />
                  <Bar dataKey="value" fill="#a3e635" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer>
              </div>
              <p className="text-xs text-white/50">Source: {st.data_source}. Display statistics use all loaded matches; the prediction model uses only its training split.</p>
            </>)}
          </div>)}
      </div>
    </div>
  );
}
