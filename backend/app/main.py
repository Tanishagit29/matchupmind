import os
from typing import Optional

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import common
from .briefing import briefing
from .predict import predict

app = FastAPI(title="MatchupMind AI")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
                   allow_methods=["*"], allow_headers=["*"])
_cache = {}


def art():
    path = common.MODEL_PATH
    if _cache.get("path") != str(path):
        if not path.exists():
            raise HTTPException(503, "Model not trained yet. Run data_prep then train (see README).")
        _cache.update(path=str(path), a=joblib.load(path))
    return _cache["a"]


class Scenario(BaseModel):
    batter: str
    bowler: str
    over: int = Field(ge=0, le=19, description="0-indexed T20 over")
    wickets: int = Field(0, ge=0, le=9)
    innings: int = Field(1, ge=1, le=2)


class WhatIf(BaseModel):
    baseline: Scenario
    changes: dict


def _check(a, s: Scenario):
    for role, name, pool in (("batter", s.batter, a["batters"]), ("bowler", s.bowler, a["bowlers"])):
        if name not in pool:
            raise HTTPException(404, f"No historical records for {role} '{name}'.")


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": common.MODEL_PATH.exists()}


@app.get("/players")
def players(q: Optional[str] = None, limit: int = 20):
    a = art()
    names = [p for p in a["players"] if not q or q.lower() in p.lower()]
    return {"players": names[:limit], "data_source": a["data_source"]}


@app.get("/players/{name}/stats")
def player_stats(name: str, role: str = "batter"):
    a = art()
    st = a["stats"].get(role, {}).get(name)
    if role not in ("batter", "bowler") or not st:
        raise HTTPException(404, f"No historical {role} records for '{name}'.")
    b = st["balls"]
    out = {"name": name, "role": role, "data_source": a["data_source"], **st,
           "strike_rate" if role == "batter" else "economy": round(100 * st["runs"] / b, 1) if role == "batter" else round(6 * st["runs"] / b, 2),
           "warnings": [f"Small sample: only {b} balls on record."] if b < 100 else []}
    return out


@app.post("/predict")
def do_predict(s: Scenario):
    a = art(); _check(a, s)
    return predict(a, s.batter, s.bowler, s.over, s.wickets, s.innings)


@app.post("/whatif")
def whatif(w: WhatIf):
    a = art()
    bad = set(w.changes) - {"batter", "bowler", "over", "wickets", "innings"}
    if bad:
        raise HTTPException(422, f"Unsupported changes: {sorted(bad)}")
    alt = Scenario(**{**w.baseline.model_dump(), **w.changes})
    _check(a, w.baseline); _check(a, alt)
    b = predict(a, **w.baseline.model_dump())
    c = predict(a, **alt.model_dump())
    delta = {k: c["probabilities"][k] - b["probabilities"][k] for k in b["probabilities"]}
    text, src = briefing(b, c, w.baseline.model_dump(), alt.model_dump())
    return {"baseline": b, "alternative": c, "probability_delta": delta, "briefing": text, "briefing_source": src}


@app.get("/model/metrics")
def metrics():
    a = art()
    return {"metrics": a["metrics"], "data_source": a["data_source"]}
