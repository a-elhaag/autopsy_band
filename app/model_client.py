"""Provider-agnostic chat wrapper.

Default backend is OpenRouter via the OpenAI-compatible SDK. The public surface
is a single `complete()` call so a Foundry/Azure backend can slot in later
behind the same signature without touching agent code.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from openai import OpenAI

from .config import settings


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


def complete(system: str, user: str, model: str, *, temperature: float = 0.0) -> str:
    """Run one chat round trip and return the assistant text."""
    resp = _client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        extra_headers={
            "HTTP-Referer": settings.app_url,
            "X-OpenRouter-Title": settings.app_name,
        },
    )
    return resp.choices[0].message.content or ""


def complete_json(system: str, user: str, model: str) -> Any:
    """Run a completion and parse the response as JSON.

    Tolerates models that wrap JSON in prose or ```json fences. Raises
    ValueError if no JSON object/array can be recovered.
    """
    raw = complete(system, user, model)
    return _extract_json(raw)


def _extract_json(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fence
        text = text.split("```", 2)
        text = text[1] if len(text) > 1 else raw
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # last resort: grab the outermost {...} or [...]
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in model output: {raw[:200]!r}")
