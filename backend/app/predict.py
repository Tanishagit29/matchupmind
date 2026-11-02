import numpy as np

from . import model as M
from .common import CLASSES, RUNS_PER_CLASS


def _evidence(art, batter, bowler):
    row = art["h2h"].get((batter, bowler))
    if not row:
        return {"balls": 0, "runs": 0, "dismissals": 0, "strike_rate": None, "boundary_pct": None}
    balls = sum(row.values())
    runs = sum(int(k) * v for k, v in row.items() if k != "W")
    return {"balls": int(balls), "runs": int(runs), "dismissals": int(row["W"]),
            "strike_rate": round(100 * runs / balls, 1), "boundary_pct": round(100 * (row["4"] + row["6"]) / balls, 1)}


def predict(art, batter, bowler, over, wickets, innings=1):
    x = M.features(art, batter, bowler, over, wickets, innings)[None, :]
    p = M.predict_proba(art["model"], x)[0]
    rb = float(np.dot(p, RUNS_PER_CLASS))
    nb, nw = art["bat"].get(batter, (None, 0))[1], art["bowl"].get(bowler, (None, 0))[1]
    ev = _evidence(art, batter, bowler)
    warnings = []
    if nb < 100: warnings.append(f"Small sample: only {nb} historical balls for {batter}.")
    if nw < 100: warnings.append(f"Small sample: only {nw} historical balls for {bowler}.")
    if ev["balls"] < 12: warnings.append(f"Head-to-head sample is only {ev['balls']} balls (shown as evidence; the model does not use it directly).")
    return {
        "source": "trained_model", "data_source": art["data_source"],
        "probabilities": dict(zip(CLASSES, map(float, p))),
        "boundary_probability": float(p[CLASSES.index("4")] + p[CLASSES.index("6")]),
        "wicket_probability": float(p[CLASSES.index("W")]),
        "expected_runs_next_ball": rb,
        "expected_runs_next_over": rb * 6,  # approximation: 6 independent balls, extras ignored
        "evidence": {"historical_head_to_head": ev, "batter_balls": nb, "bowler_balls": nw},
        "warnings": warnings,
    }


def explain(base, alt):
    """Template fallback briefing (no LLM key needed). Describes model output only."""
    d = alt["wicket_probability"] - base["wicket_probability"]
    r = alt["expected_runs_next_over"] - base["expected_runs_next_over"]
    side = "favours the bowler" if d > 0 and r < 0 else "favours the batter" if d < 0 and r > 0 else "has a mixed effect"
    return (f"In the model's estimate, the changed scenario {side}: expected next-over runs move by {r:+.2f} and wicket "
            f"probability per ball by {100*d:+.1f} percentage points. This is a statistical estimate, not proof of what would have happened.")
