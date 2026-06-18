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
import json
import time
from collections.abc import AsyncIterator

from ..agents import stages
from ..config import settings


class InputTooLargeError(ValueError):
    pass


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def stream(original_input: str) -> AsyncIterator[str]:
    """Yield SSE data lines as each stage starts/completes."""
    original_input = original_input.strip()
    if len(original_input) > settings.max_input_chars:
        yield _sse({"type": "error", "message": f"input exceeds {settings.max_input_chars} chars"})
        return

    try:
        # 1. Annotator
        candidates = []
        async for item in _timed_stage("annotator", "Classifying failure candidates", settings.model_annotator, stages.annotate, original_input):
            if isinstance(item, str):
                yield item
            else:
                candidates = item

        # 2. Verifier
        validated = []
        async for item in _timed_stage("verifier", "Grounding claims with quotes", settings.model_verifier, stages.verify_and_gate, original_input, candidates):
            if isinstance(item, str):
                yield item
            else:
                validated = item

        if not validated:
            from ..report import renderer as _renderer
            yield _sse({"type": "report", "html": _renderer.to_html(_fm00_report())})
            return

        # 3 + 4. Scorer and Reconstructor in parallel
        yield _sse({"type": "stage_start", "stage": "scorer", "label": "Scoring confidence", "model": settings.model_scorer.split("/")[-1]})
        yield _sse({"type": "stage_start", "stage": "reconstructor", "label": "Rebuilding spec", "model": settings.model_reconstructor.split("/")[-1]})
        t0 = time.monotonic()
        scored, reconstructed_spec = await asyncio.gather(
            asyncio.to_thread(stages.score, original_input, validated),
            asyncio.to_thread(stages.reconstruct, original_input, validated),
        )
        ms = int((time.monotonic() - t0) * 1000)
        yield _sse({"type": "stage_done", "stage": "scorer", "ms": ms})
        yield _sse({"type": "stage_done", "stage": "reconstructor", "ms": ms})

        # 5. Apex
        verdict = {}
        async for item in _timed_stage("apex", "Synthesizing verdict", settings.model_apex, stages.synthesize, original_input, scored, reconstructed_spec):
            if isinstance(item, str):
                yield item
            else:
                verdict = item

        # 6. Escalation
        escalation = {}
        async for item in _timed_stage("escalation", "Checking escalation severity", settings.model_escalation, stages.escalate, verdict):
            if isinstance(item, str):
                yield item
            else:
                escalation = item

        from ..report import renderer as _renderer
        result = {
            "validated_claims": validated,
            "scored_claims": scored,
            "verdict": verdict,
            "escalation": escalation,
        }
        yield _sse({"type": "report", "html": _renderer.to_html(result)})

    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


async def _timed_stage(name: str, label: str, model: str, fn, *args) -> AsyncIterator:
    from ..model_client import get_last_thinking, set_token_callback
    loop = asyncio.get_event_loop()
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()

    def on_token(tok: str) -> None:
        loop.call_soon_threadsafe(token_queue.put_nowait, tok)

    yield _sse({"type": "stage_start", "stage": name, "label": label, "model": model.split("/")[-1]})
    t0 = time.monotonic()

    def _fn_in_thread(*a):
        set_token_callback(on_token)
        try:
            return fn(*a)
        finally:
            set_token_callback(None)
            loop.call_soon_threadsafe(token_queue.put_nowait, None)  # sentinel

    task = asyncio.create_task(asyncio.to_thread(_fn_in_thread, *args))

    while True:
        tok = await token_queue.get()
        if tok is None:
            break
        yield _sse({"type": "token", "stage": name, "text": tok})

    result = await task
    ms = int((time.monotonic() - t0) * 1000)
    thinking = get_last_thinking()
    yield _sse({"type": "stage_done", "stage": name, "ms": ms, "thinking": thinking})
    yield result


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
