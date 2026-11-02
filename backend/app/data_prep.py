"""Convert Cricsheet CSV2 ball-by-ball files into one balls.csv.

Usage:  python -m app.data_prep cricsheet --src <folder of Cricsheet csv files>
        python -m app.data_prep demo      (SYNTHETIC data, for pipeline testing only)
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import BALLS_CSV


def _outcome(row):
    wt = row["wicket_type"]
    if isinstance(wt, str) and wt not in ("retired hurt", "retired out", "run out"):
        return "W"  # run outs are not credited to the bowler
    r = int(row["runs_off_bat"])
    return str(r) if r in (0, 1, 2, 3, 4, 6) else ("1" if r == 5 else "0")


def from_cricsheet(src: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(Path(src).glob("*.csv")):
        if f.name.endswith("_info.csv"):
            continue
        df = pd.read_csv(f, low_memory=False)
        if "striker" not in df.columns:
            continue
        frames.append(df)
    if not frames:
        raise SystemExit(f"No Cricsheet ball-by-ball CSV files found in {src}")
    d = pd.concat(frames, ignore_index=True)
    for c in ("wides", "noballs", "wicket_type"):
        if c not in d.columns:
            d[c] = np.nan
    d = d[d["wides"].isna() & d["innings"].isin([1, 2])]
    out = pd.DataFrame({
        "match_id": d["match_id"], "date": pd.to_datetime(d["start_date"]),
        "innings": d["innings"], "over": d["ball"].astype(float).astype(int),
        "batter": d["striker"], "bowler": d["bowler"],
        "outcome": d.apply(_outcome, axis=1),
    })
    out["source"] = "cricsheet"
    return out


def make_demo(n_matches=400, seed=7) -> pd.DataFrame:
    """SYNTHETIC data with invented players. Not real cricket statistics."""
    rng = np.random.default_rng(seed)
    bats = [f"Demo Batter {i}" for i in range(1, 25)]
    bowls = [f"Demo Bowler {i}" for i in range(1, 17)]
    skill = {b: rng.normal(0, .4) for b in bats}
    econ = {b: rng.normal(0, .4) for b in bowls}
    cls = ["0", "1", "2", "3", "4", "6", "W"]
    rows = []
    for m in range(n_matches):
        date = pd.Timestamp("2018-01-01") + pd.Timedelta(days=int(m * 4))
        for inn in (1, 2):
            for over in range(20):
                bowler = bowls[rng.integers(len(bowls))]
                boost = .1 if over < 6 else -.1 if over < 15 else .4
                for _ in range(6):
                    b = bats[rng.integers(12)]
                    s = skill[b] - econ[bowler] + boost
                    p = np.array([.38, .30, .07, .01, .10 + .03 * s, .04 + .03 * s, .04 - .01 * s])
                    p = np.clip(p, .005, None); p /= p.sum()
                    rows.append((m, date, inn, over, b, bowler, str(rng.choice(cls, p=p))))
    df = pd.DataFrame(rows, columns=["match_id", "date", "innings", "over", "batter", "bowler", "outcome"])
    df["source"] = "DEMO_SYNTHETIC"
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("cricsheet"); c.add_argument("--src", required=True)
    sp.add_parser("demo")
    a = ap.parse_args()
    df = from_cricsheet(Path(a.src)) if a.cmd == "cricsheet" else make_demo()
    BALLS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(BALLS_CSV, index=False)
    print(f"Wrote {len(df):,} balls from {df.match_id.nunique():,} matches to {BALLS_CSV} (source={df.source.iloc[0]})")
