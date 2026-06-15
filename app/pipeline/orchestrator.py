"""The council pipeline (in-process path).

Drives the six stages in order, faithful to agent.md:

  Annotator -> Verifier -> (ConfidenceScorer || Reconstructor) -> Apex -> Escalation

Each agent gets only the original input + the prior agent's structured output —
never raw chat history. The pipeline is stateless: the input is not persisted.

This in-process path is the synchronous one used by the web UI / demo. The Band
transport (`app/band/`) runs the identical stage functions (`agents/stages.py`)
as distributed Band agents when BAND is enabled.
"""
from __future__ import annotations

import asyncio

from ..agents import stages
from ..config import settings


class InputTooLargeError(ValueError):
    pass


async def run(original_input: str) -> dict:
    """Run the full council and return the final report payload."""
    original_input = original_input.strip()
    if len(original_input) > settings.max_input_chars:
        raise InputTooLargeError(f"input exceeds {settings.max_input_chars} chars")

    # 1. Annotator
    candidates = await asyncio.to_thread(stages.annotate, original_input)

    # 2. Verifier (model pass + code-enforced proof gate)
    validated = await asyncio.to_thread(stages.verify_and_gate, original_input, candidates)

    # FM-00 short circuit: no validated claims is a high-accuracy result.
    if not validated:
        return _fm00_report()

    # 3 + 4. Scorer and Reconstructor fan out in parallel off validated_claims.
    scored, reconstructed_spec = await asyncio.gather(
        asyncio.to_thread(stages.score, original_input, validated),
        asyncio.to_thread(stages.reconstruct, original_input, validated),
    )

    # 5. Apex
    verdict = await asyncio.to_thread(
        stages.synthesize, original_input, scored, reconstructed_spec
    )

    # 6. Escalation
    escalation = await asyncio.to_thread(stages.escalate, verdict)

    return {
        "validated_claims": validated,
        "scored_claims": scored,
        "verdict": verdict,
        "escalation": escalation,
    }


def _fm00_report() -> dict:
    return {
        "validated_claims": [],
        "scored_claims": [],
        "verdict": stages.fm00_verdict(),
        "escalation": {"escalation": False},
    }
