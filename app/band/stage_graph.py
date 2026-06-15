"""The council stage graph for Band transport.

agent.md fans Scorer and Reconstructor in parallel off the Verifier. Over a
message bus that parallel join requires an aggregator; for the Band transport we
linearize into a single chain — Scorer and Reconstructor both depend only on
`validated_claims` + the original input, so chaining them is data-equivalent and
avoids a fan-in barrier. The verdict is identical to the in-process path.

Each stage carries a `payload` dict accumulating:
  correlation_id, original_input, candidates, validated, scored,
  reconstructed_spec, verdict, escalation
"""
from __future__ import annotations

from ..agents import stages

# Order of agents on the bus. Names must match the registered Band agent names
# used in @mentions (see agent_config.example.yaml).
CHAIN = [
    "Annotator",
    "Verifier",
    "ConfidenceScorer",
    "Reconstructor",
    "ApexSynthesizer",
    "HumanEscalation",
]

# Display name -> agent_config.yaml key
CONFIG_KEYS = {
    "Annotator": "annotator",
    "Verifier": "verifier",
    "ConfidenceScorer": "scorer",
    "Reconstructor": "reconstructor",
    "ApexSynthesizer": "apex",
    "HumanEscalation": "escalation",
}


def next_agent(stage: str) -> str | None:
    i = CHAIN.index(stage)
    return CHAIN[i + 1] if i + 1 < len(CHAIN) else None


def run_stage(stage: str, payload: dict) -> tuple[dict, bool]:
    """Execute one agent's work against the payload.

    Returns (updated_payload, is_terminal). is_terminal is True when the
    diagnosis is complete (final agent, or an early FM-00 short circuit).
    """
    original = payload["original_input"]

    if stage == "Annotator":
        payload["candidates"] = stages.annotate(original)
        return payload, False

    if stage == "Verifier":
        payload["validated"] = stages.verify_and_gate(
            original, payload.get("candidates", [])
        )
        # FM-00 short circuit: no validated claims -> terminal, skip the rest.
        if not payload["validated"]:
            payload["verdict"] = stages.fm00_verdict()
            payload["escalation"] = {"escalation": False}
            payload["scored"] = []
            return payload, True
        return payload, False

    if stage == "ConfidenceScorer":
        payload["scored"] = stages.score(original, payload["validated"])
        return payload, False

    if stage == "Reconstructor":
        payload["reconstructed_spec"] = stages.reconstruct(original, payload["validated"])
        return payload, False

    if stage == "ApexSynthesizer":
        payload["verdict"] = stages.synthesize(
            original, payload.get("scored", []), payload.get("reconstructed_spec", "")
        )
        return payload, False

    if stage == "HumanEscalation":
        payload["escalation"] = stages.escalate(payload["verdict"])
        return payload, True

    raise ValueError(f"unknown stage: {stage}")


def final_report(payload: dict) -> dict:
    return {
        "validated_claims": payload.get("validated", []),
        "scored_claims": payload.get("scored", []),
        "verdict": payload.get("verdict", stages.fm00_verdict()),
        "escalation": payload.get("escalation", {"escalation": False}),
    }
