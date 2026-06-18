"""Submit a diagnosis to the Band council and await the result.

The web app calls `submit_and_wait()` when BAND is enabled: it posts the input
into the council chat room addressed to @Annotator, then blocks on the result
store until HumanEscalation writes the final report.
"""
from __future__ import annotations

import asyncio
import uuid

from app.band.agent_config import AGENT_CONFIG
from ..config import settings
from . import client, result_store
from .stage_graph import CHAIN

_FIRST = CHAIN[0]  # "Annotator"


def _submit(original_input: str) -> str:
    correlation_id = uuid.uuid4().hex
    client.send_message(
        chat_id=settings.band_chat_id,
        api_key=settings.band_initiator_api_key,
        content="new autopsy request",
        mentions=[{"id": AGENT_CONFIG[_FIRST.lower()]["agent_id"], "type": "agent"}],
    )
    return correlation_id


async def submit_and_wait(original_input: str, timeout: float = 120.0) -> dict | None:
    correlation_id = await asyncio.to_thread(_submit, original_input)
    return await asyncio.to_thread(result_store.wait, correlation_id, timeout)
