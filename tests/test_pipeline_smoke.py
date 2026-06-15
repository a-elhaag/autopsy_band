"""End-to-end pipeline smoke test with the model client stubbed.

The stub routes by agent role (detected in the system prompt) instead of call
order, so the parallel Scorer/Reconstructor branch can't make it flaky.
"""
import pytest

from app.agents import stages
from app.pipeline import orchestrator
from app.report import renderer

INPUT = (
    "PROMPT: build a CRM that does everything for everyone in one prompt.\n"
    "OUTPUT: here is a complete production app with auth, billing and analytics."
)
QUOTE = "build a CRM that does everything for everyone in one prompt"


def _router(monkeypatch, by_role):
    def fake(system, user, model):
        for marker, value in by_role.items():
            if marker in system:
                return value
        raise AssertionError(f"no stub for system: {system[:40]!r}")

    monkeypatch.setattr(stages, "complete_json", fake)


@pytest.mark.asyncio
async def test_full_pipeline_produces_report(monkeypatch):
    _router(
        monkeypatch,
        {
            "ANNOTATOR": [{"failure_mode_id": "FM-02", "quote": QUOTE, "location": "PROMPT"}],
            "VERIFIER": [{"failure_mode_id": "FM-02", "quote": QUOTE, "validated": True}],
            "CONFIDENCE SCORER": [{"failure_mode_id": "FM-02", "severity": "Critical", "confidence": 90}],
            "RECONSTRUCTOR": {"reconstructed_spec": "Decompose into scoped milestones."},
            "APEX SYNTHESIZER": {
                "primary_failure_mode": "FM-02",
                "causal_chain": ["FM-02 -> FM-05"],
                "verdict": "Critical",
                "reconstructed_spec": "Decompose into scoped milestones.",
            },
            "HUMAN-ESCALATION": {
                "escalation": True,
                "ticket": {
                    "summary": "Overloaded single prompt; needs redesign.",
                    "primary_failure_mode": "FM-02",
                    "reviewer_role": "Lead architect",
                },
            },
        },
    )

    result = await orchestrator.run(INPUT)
    assert result["verdict"]["verdict"] == "Critical"
    assert result["verdict"]["primary_failure_mode"] == "FM-02"
    assert result["escalation"]["escalation"] is True
    assert len(result["validated_claims"]) == 1

    html = renderer.to_html(result)
    assert "FM-02" in html
    assert "God-Prompt Overload" in html
    assert "escalation ticket" in html.lower()


@pytest.mark.asyncio
async def test_fabricated_quote_yields_fm00(monkeypatch):
    _router(
        monkeypatch,
        {
            "ANNOTATOR": [{"failure_mode_id": "FM-12", "quote": "invented a payment API"}],
            "VERIFIER": [{"failure_mode_id": "FM-12", "quote": "invented a payment API", "validated": True}],
        },
    )
    result = await orchestrator.run(INPUT)
    # Code gate drops the fabricated quote -> no validated claims -> FM-00
    assert result["verdict"]["primary_failure_mode"] == "FM-00"
    assert result["validated_claims"] == []
    assert "FM-00" in renderer.to_markdown(result)


@pytest.mark.asyncio
async def test_input_too_large():
    from app.config import settings

    big = "x" * (settings.max_input_chars + 1)
    with pytest.raises(orchestrator.InputTooLargeError):
        await orchestrator.run(big)
