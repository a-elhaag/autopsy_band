"""Tests for the Band transport stage graph — the per-agent step logic that
each Band agent runs. Model calls are stubbed; no Band connectivity needed.
"""
from app.agents import stages
from app.band import stage_graph

INPUT = "PROMPT: build everything in one prompt.\nOUTPUT: done."
QUOTE = "build everything in one prompt"


def _router(monkeypatch, by_role):
    def fake(system, user, model):
        for marker, value in by_role.items():
            if marker in system:
                return value
        raise AssertionError(system[:30])

    monkeypatch.setattr(stages, "complete_json", fake)


def test_chain_walks_all_six():
    seen = []
    s = stage_graph.CHAIN[0]
    while s is not None:
        seen.append(s)
        s = stage_graph.next_agent(s)
    assert seen == stage_graph.CHAIN
    assert len(seen) == 6


def test_full_chain_via_run_stage(monkeypatch):
    _router(
        monkeypatch,
        {
            "ANNOTATOR": [{"failure_mode_id": "FM-02", "quote": QUOTE}],
            "VERIFIER": [{"failure_mode_id": "FM-02", "quote": QUOTE, "validated": True}],
            "CONFIDENCE SCORER": [{"failure_mode_id": "FM-02", "severity": "Critical", "confidence": 88}],
            "RECONSTRUCTOR": {"reconstructed_spec": "Scope it down."},
            "APEX SYNTHESIZER": {"primary_failure_mode": "FM-02", "verdict": "Critical", "causal_chain": []},
            "HUMAN-ESCALATION": {"escalation": True, "ticket": {"summary": "x", "reviewer_role": "y"}},
        },
    )
    payload = {"correlation_id": "c1", "original_input": INPUT}
    terminal = False
    for stage in stage_graph.CHAIN:
        payload, terminal = stage_graph.run_stage(stage, payload)
    assert terminal is True
    report = stage_graph.final_report(payload)
    assert report["verdict"]["verdict"] == "Critical"
    assert report["escalation"]["escalation"] is True


def test_verifier_short_circuits_to_fm00(monkeypatch):
    _router(
        monkeypatch,
        {
            "ANNOTATOR": [{"failure_mode_id": "FM-12", "quote": "not in the input at all"}],
            "VERIFIER": [{"failure_mode_id": "FM-12", "quote": "not in the input at all", "validated": True}],
        },
    )
    payload = {"correlation_id": "c2", "original_input": INPUT}
    payload, _ = stage_graph.run_stage("Annotator", payload)
    payload, terminal = stage_graph.run_stage("Verifier", payload)
    assert terminal is True  # gate dropped fabricated quote -> terminal FM-00
    report = stage_graph.final_report(payload)
    assert report["verdict"]["primary_failure_mode"] == "FM-00"
