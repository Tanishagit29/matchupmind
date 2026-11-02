import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .common import CLASSES, PHASES, phase_of

K = 30  # shrinkage strength toward the global rate


def _rates(df, key, prior):
    ct = pd.crosstab(df[key], df["outcome"]).reindex(columns=CLASSES, fill_value=0)
    n = ct.sum(axis=1)
    shr = (ct.values + K * prior) / (n.values[:, None] + K)
    return {k: (shr[i], int(n.iloc[i])) for i, k in enumerate(ct.index)}


def build_artifacts(train: pd.DataFrame):
    """All lookup stats are computed from TRAIN rows only (no leakage)."""
    prior = train["outcome"].value_counts(normalize=True).reindex(CLASSES, fill_value=0).values
    prior = np.clip(prior, 1e-4, None); prior = prior / prior.sum()
    return {"prior": prior, "bat": _rates(train, "batter", prior), "bowl": _rates(train, "bowler", prior)}


def features(art, batter, bowler, over, wickets, innings=1):
    pr = art["prior"]
    br = art["bat"].get(batter, (pr, 0))[0]
    bo = art["bowl"].get(bowler, (pr, 0))[0]
    ph = [1.0 if phase_of(over) == p else 0.0 for p in PHASES]
    return np.concatenate([np.log(br / pr), np.log(bo / pr), ph, [wickets / 10, over / 20, innings - 1]])


def matrix(art, df):
    d = df.sort_values(["match_id", "innings"], kind="stable").copy()
    w = (d["outcome"] == "W").astype(int)
    d["wk"] = (w.groupby([d["match_id"], d["innings"]]).cumsum() - w).clip(upper=9)
    X = np.vstack([features(art, b, w_, o, k, i) for b, w_, o, k, i in zip(d.batter, d.bowler, d.over, d.wk, d.innings)])
    return X, d["outcome"].map({c: i for i, c in enumerate(CLASSES)}).values, d


def fit(X, y):
    return LogisticRegression(max_iter=500, C=1.0).fit(X, y)


def predict_proba(model, X):
    p = np.full((len(X), len(CLASSES)), 1e-6)
    p[:, model.classes_] = model.predict_proba(X)
    return p / p.sum(axis=1, keepdims=True)
