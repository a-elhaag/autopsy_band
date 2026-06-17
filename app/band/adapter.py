"""CouncilAdapter — one Band agent's behaviour on the bus.

Each of the 6 council agents runs a CouncilAdapter bound to its stage. On every
@mention it: pulls the running payload from the incoming message's metadata,
executes its stage (`stage_graph.run_stage`), then either forwards the updated
payload to the next agent by @mention, or — if terminal — writes the final
report to the result store for the web app to collect.

NOTE: the exact attribute names on the inbound `msg` object depend on the
installed thenvoi version. Extraction is centralised in `_payload_from_msg` /
`_chat_id_from` so it can be aligned to the live SDK schema in one place.
"""
from __future__ import annotations

import json
from typing import Any

from thenvoi.core.simple_adapter import SimpleAdapter

from . import client, result_store
from .stage_graph import final_report, next_agent, run_stage
from .agent_config import AGENT_CONFIG

class CouncilAdapter(SimpleAdapter[list]):
    def __init__(self, stage: str, api_key: str, *, agent_names: dict[str, str]):
        super().__init__()
        self.stage = stage
        self.api_key = api_key
        # display stage name -> the @mention handle Band routes on
        self.agent_names = agent_names

    async def on_message(
        self,
        msg,
        tools,
        history,
        participants_msg,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        if is_session_bootstrap:
            return

        payload = self._payload_from_msg(msg)
        if payload is None or "original_input" not in payload:
            return  # not a council handoff we recognise

        updated, terminal = run_stage(self.stage, payload)
        chat_id = self._chat_id_from(msg, room_id)

        if terminal:
            report = final_report(updated)
            result_store.put(updated["correlation_id"], report)
            return

        nxt = next_agent(self.stage)
        if nxt is None:
            result_store.put(updated["correlation_id"], final_report(updated))
            return

        mention = self.agent_names.get(nxt, nxt)
        client.send_message(
            chat_id=chat_id,
            api_key=self.api_key,
            content=f"@{mention} council handoff from {self.stage}",
            mentions=[{"id": AGENT_CONFIG[f"{mention}".lower()]["agent_id"], "type": "agent"}],
            metadata={"council_payload": updated},
        )

    # --- SDK-schema-coupled extraction (align to live thenvoi if needed) ---

    @staticmethod
    def _payload_from_msg(msg: Any) -> dict | None:
        meta = _get(msg, "metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        payload = meta.get("council_payload") if isinstance(meta, dict) else None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _chat_id_from(msg: Any, room_id: str) -> str:
        return _get(msg, "chat_id") or _get(msg, "room_id") or room_id


def _get(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
