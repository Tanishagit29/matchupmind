"""Chronological match-based split -> baselines -> model -> metrics -> model.joblib"""
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from . import model as M
from .common import BALLS_CSV, CLASSES, MODEL_PATH, phase_of


def train(csv=None, out=None):
    csv, out = csv or BALLS_CSV, out or MODEL_PATH
    df = pd.read_csv(csv, parse_dates=["date"])
    order = df.groupby("match_id")["date"].min().sort_values(kind="stable").index.tolist()
    n = len(order)
    tr_ids, va_ids, te_ids = set(order[:int(.7 * n)]), set(order[int(.7 * n):int(.85 * n)]), set(order[int(.85 * n):])
    tr, te = df[df.match_id.isin(tr_ids)], df[df.match_id.isin(te_ids)]
    assert tr.date.max() <= te.date.min(), "leakage: train must precede test"

    art = M.build_artifacts(tr)
    Xtr, ytr, _ = M.matrix(art, tr)
    Xte, yte, dte = M.matrix(art, te)
    mdl = M.fit(Xtr, ytr)
    p_model = M.predict_proba(mdl, Xte)

    prior = art["prior"]
    p_global = np.tile(prior, (len(yte), 1))
    ph_tab = pd.crosstab(tr.over.map(phase_of), tr.outcome, normalize="index").reindex(columns=CLASSES, fill_value=0).clip(lower=1e-4)
    p_phase = np.vstack([ph_tab.loc[phase_of(o)].values for o in dte.over])
    labels = list(range(len(CLASSES)))
    ll = lambda p: float(log_loss(yte, p / p.sum(axis=1, keepdims=True), labels=labels))
    wk = CLASSES.index("W")
    metrics = {
        "log_loss": {"global_frequency_baseline": ll(p_global), "phase_frequency_baseline": ll(p_phase), "model": ll(p_model)},
        "wicket_brier": {"global_frequency_baseline": float(np.mean(((yte == wk) - p_global[:, wk]) ** 2)),
                         "model": float(np.mean(((yte == wk) - p_model[:, wk]) ** 2))},
        "split": {"train_matches": len(tr_ids), "val_matches": len(va_ids), "test_matches": len(te_ids),
                  "test_from": str(te.date.min().date()), "test_balls": int(len(te))},
        "calibration_note": "Multinomial logistic regression; reliability curves not yet implemented.",
    }
    df["runs"] = df.outcome.map({"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "6": 6, "W": 0})

    def pstats(col):
        out = {}
        for name, g in df.groupby(col):
            m = g.groupby("match_id").agg(date=("date", "max"), runs=("runs", "sum"), balls=("runs", "size"),
                                          wk=("outcome", lambda s: int((s == "W").sum()))).sort_values("date").tail(10)
            out[name] = {"balls": int(len(g)), "runs": int(g.runs.sum()), "dismissals": int((g.outcome == "W").sum()),
                         "boundary_pct": float(g.outcome.isin(["4", "6"]).mean() * 100),
                         "recent_form": [{"runs": int(r.runs), "balls": int(r.balls), "wickets": r.wk} for r in m.itertuples()]}
        return out

    h2h = tr.groupby(["batter", "bowler"])["outcome"].value_counts().unstack(fill_value=0).reindex(columns=CLASSES, fill_value=0)
    art.update(stats={"batter": pstats("batter"), "bowler": pstats("bowler")}, model=mdl, metrics=metrics, data_source=str(df["source"].iloc[0]),
               h2h={k: v.to_dict() for k, v in h2h.iterrows()},
               players=sorted(set(df.batter) | set(df.bowler)), batters=sorted(set(df.batter)), bowlers=sorted(set(df.bowler)))
    out = __import__("pathlib").Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(art, out)
    return metrics


if __name__ == "__main__":
    import json
    print(json.dumps(train(), indent=2))
