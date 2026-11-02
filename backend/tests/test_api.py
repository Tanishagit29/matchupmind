import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("mm")
    from app import common, data_prep, train as T, main
    data_prep.make_demo(n_matches=120).to_csv(d / "b.csv", index=False)
    T.train(d / "b.csv", d / "m.joblib")
    common.MODEL_PATH = d / "m.joblib"
    return TestClient(main.app)


def test_metrics_and_labels(client):
    m = client.get("/model/metrics").json()
    assert m["data_source"] == "DEMO_SYNTHETIC"
    assert m["metrics"]["log_loss"]["model"] > 0


def test_predict_sums_to_one(client):
    r = client.post("/predict", json={"batter": "Demo Batter 1", "bowler": "Demo Bowler 1", "over": 18, "wickets": 3}).json()
    assert abs(sum(r["probabilities"].values()) - 1) < 1e-6 and r["source"] == "trained_model"


def test_whatif_and_missing_player(client):
    base = {"batter": "Demo Batter 1", "bowler": "Demo Bowler 1", "over": 18, "wickets": 3}
    r = client.post("/whatif", json={"baseline": base, "changes": {"bowler": "Demo Bowler 2"}})
    assert r.status_code == 200 and "briefing" in r.json()
    assert client.post("/predict", json={**base, "batter": "Nobody"}).status_code == 404


def test_player_stats(client):
    r = client.get("/players/Demo Batter 1/stats?role=batter").json()
    assert r["balls"] > 0 and r["strike_rate"] > 0 and len(r["recent_form"]) <= 10
    assert client.get("/players/Nobody/stats?role=bowler").status_code == 404


def test_briefing_fallback(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    base = {"batter": "Demo Batter 1", "bowler": "Demo Bowler 1", "over": 18, "wickets": 3}
    r = client.post("/whatif", json={"baseline": base, "changes": {"over": 3}}).json()
    assert r["briefing_source"] == "template_fallback"
