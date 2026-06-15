"""Taxonomy loading.

Per agent.md: agents receive only `{id, name, definition}` per failure mode.
Remediation text is stored separately and appended by FM-ID *after*
classification, keeping diagnosis separate from prescription.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads((_DIR / "taxonomy.json").read_text())


@lru_cache(maxsize=1)
def _remediation() -> dict[str, str]:
    return json.loads((_DIR / "remediation.json").read_text())


@lru_cache(maxsize=1)
def modes() -> list[dict]:
    """All modes as {id, name, definition} — the only view agents get."""
    return _raw()["modes"]


@lru_cache(maxsize=1)
def categories() -> dict[str, str]:
    return _raw()["categories"]


def category_of(fm_id: str) -> str:
    return categories().get(fm_id, "Unknown")


def remediation_for(fm_id: str) -> str:
    """Appended only after classification."""
    return _remediation().get(fm_id, "")


def definitions_block() -> str:
    """Render the taxonomy as a compact text block for agent system prompts."""
    lines = []
    for m in modes():
        lines.append(f"{m['id']} — {m['name']}: {m['definition']}")
    return "\n".join(lines)


def name_of(fm_id: str) -> str:
    for m in modes():
        if m["id"] == fm_id:
            return m["name"]
    return fm_id
