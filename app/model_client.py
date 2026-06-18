"""Provider-agnostic chat wrapper.

Default backend is OpenRouter via the OpenAI-compatible SDK. The public surface
is a single `complete()` call so a Foundry/Azure backend can slot in later
behind the same signature without touching agent code.
"""
from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from typing import Any, Callable

from openai import OpenAI

from .config import settings

_thinking = threading.local()
_token_cb: threading.local = threading.local()


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


def get_last_thinking() -> str:
    return getattr(_thinking, "last", "")


def set_token_callback(cb: Callable[[str], None] | None) -> None:
    _token_cb.fn = cb


def complete(system: str, user: str, model: str, *, temperature: float = 0.0) -> str:
    """Run one chat round trip and return the assistant text.

    If a token callback is registered on this thread via set_token_callback(),
    uses streaming mode and forwards each token to the callback.
    """
    cb = getattr(_token_cb, "fn", None)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    headers = {
        "HTTP-Referer": settings.app_url,
        "X-OpenRouter-Title": settings.app_name,
    }

    if cb:
        stream = _client().chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
            extra_headers=headers,
            stream=True,
        )
        chunks: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                chunks.append(delta)
                cb(delta)
        return "".join(chunks)

    resp = _client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
        extra_headers=headers,
    )
    return resp.choices[0].message.content or ""


def complete_json(system: str, user: str, model: str) -> Any:
    """Run a completion and parse the response as JSON."""
    raw = complete(system, user, model)
    return _extract_json(raw)


def _extract_json(raw: str) -> Any:
    text = raw.strip()

    # capture <think> block before stripping (reasoning models)
    think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    _thinking.last = think_match.group(1).strip() if think_match else ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if text.startswith("```"):
        parts = text.split("```", 2)
        text = parts[1] if len(parts) > 1 else raw
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in model output: {raw[:200]!r}")
