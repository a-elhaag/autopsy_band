"""Per-agent stage functions, shared by the in-process orchestrator and the
Band council transport.

Each function takes the running payload and returns its structured output.
Keeping these pure (no transport, no asyncio) lets both execution paths reuse
the identical diagnostic logic.
"""
from __future__ import annotations

import json
from typing import Any

from ..config import settings
from ..model_client import complete_json
from ..pipeline import verifier_gate
from . import prompts


def _to_text(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def annotate(original_input: str) -> list[dict]:
    out = complete_json(prompts.annotator(), original_input, settings.model_annotator)
    return out if isinstance(out, list) else []


def verify_and_gate(original_input: str, candidates: list[dict]) -> list[dict]:
    """Model verify pass, then the code-enforced proof gate (the real gate)."""
    user = f"ORIGINAL INPUT:\n{original_input}\n\nCANDIDATE CLAIMS:\n{_to_text(candidates)}"
    try:
        verified = complete_json(prompts.verifier(), user, settings.model_verifier)
    except ValueError:
        verified = candidates
    if not isinstance(verified, list):
        verified = candidates
    return verifier_gate.gate(verified, original_input)


def score(original_input: str, validated: list[dict]) -> list[dict]:
    user = f"ORIGINAL INPUT:\n{original_input}\n\nVALIDATED CLAIMS:\n{_to_text(validated)}"
    out = complete_json(prompts.scorer(), user, settings.model_scorer)
    return out if isinstance(out, list) else []


def reconstruct(original_input: str, validated: list[dict]) -> str:
    user = f"ORIGINAL INPUT:\n{original_input}\n\nVALIDATED CLAIMS:\n{_to_text(validated)}"
    out = complete_json(prompts.reconstructor(), user, settings.model_reconstructor)
    return out.get("reconstructed_spec", "") if isinstance(out, dict) else ""


def synthesize(
    original_input: str, scored: list[dict], reconstructed_spec: str
) -> dict:
    user = (
        f"ORIGINAL INPUT:\n{original_input}\n\n"
        f"SCORED CLAIMS:\n{_to_text(scored)}\n\n"
        f"RECONSTRUCTED SPEC:\n{reconstructed_spec}"
    )
    out = complete_json(prompts.apex(), user, settings.model_apex)
    if not isinstance(out, dict):
        out = {}
    out.setdefault("reconstructed_spec", reconstructed_spec)
    return out


def escalate(verdict: dict) -> dict:
    out = complete_json(prompts.escalation(), _to_text(verdict), settings.model_escalation)
    return out if isinstance(out, dict) else {"escalation": False}


def fm00_verdict() -> dict:
    return {
        "primary_failure_mode": "FM-00",
        "causal_chain": [],
        "verdict": "Inconclusive",
        "reconstructed_spec": "",
    }
