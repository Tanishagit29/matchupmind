import json
import os

import httpx

from .predict import explain


def briefing(base, alt, s_base, s_alt):
    """LLM briefing if ANTHROPIC_API_KEY is set; otherwise (or on any failure) the template fallback."""
    key = os.getenv("ANTHROPIC_API_KEY")
    fallback = explain(base, alt)
    if not key:
        return fallback, "template_fallback"
    facts = {"baseline_scenario": s_base, "alternative_scenario": s_alt,
             "baseline": {k: base[k] for k in ("probabilities", "wicket_probability", "boundary_probability", "expected_runs_next_over")},
             "alternative": {k: alt[k] for k in ("probabilities", "wicket_probability", "boundary_probability", "expected_runs_next_over")},
             "baseline_evidence": base["evidence"], "alternative_evidence": alt["evidence"],
             "warnings": base["warnings"] + alt["warnings"], "data_source": base["data_source"]}
    prompt = ("Write a 3-4 sentence plain-language cricket matchup briefing comparing the two scenarios. Use ONLY the numbers "
              "in this JSON; do not invent statistics. Mention small samples if warnings exist, note that this is a model "
              "estimate and not proof of what would have happened.\n" + json.dumps(facts))
    try:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=20,
                       headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                       json={"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 400,
                             "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"], "llm"
    except Exception:
        return fallback, "template_fallback"
