"""Code-enforced proof gate.

The anti-hallucination invariant from agent.md: no claim survives without a
quote that is verbatim-present in the original input. This is enforced in code,
independent of the Verifier model, so a model that rubber-stamps claims cannot
get a fabricated quote past the gate.
"""
from __future__ import annotations

import re


def _normalize(text: str) -> str:
    """Collapse whitespace so trivial reflow differences don't fail a real quote."""
    return re.sub(r"\s+", " ", text).strip()


def quote_present(quote: str, original: str) -> bool:
    if not quote:
        return False
    return _normalize(quote.lower()) in _normalize(original.lower())


def gate(claims: list[dict], original: str) -> list[dict]:
    """Return only claims whose quote is verbatim-present in the original input.

    Each surviving claim is stamped validated=True. Claims missing a quote or
    failing the substring check are dropped.
    """
    survived: list[dict] = []
    for claim in claims:
        quote = claim.get("quote", "")
        if quote_present(quote, original):
            kept = dict(claim)
            kept["validated"] = True
            survived.append(kept)
    return survived
