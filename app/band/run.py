"""Boot the 6-agent council as Band agents.

Run as a long-lived process alongside the web app:

    uv run python -m app.band.run

Requires:
  - THENVOI_REST_URL / THENVOI_WS_URL in the environment
  - agent_config.yaml with the 6 agent entries (see agent_config.example.yaml)
  - the 6 agents registered on app.band.ai, all participants in one chat room
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from thenvoi import Agent
from thenvoi.config import load_agent_config

from .adapter import CouncilAdapter
from .stage_graph import CHAIN, CONFIG_KEYS

# Band routes on the registered agent name; we register them as the CHAIN names.
AGENT_NAMES = {stage: stage for stage in CHAIN}


async def _start_one(stage: str) -> Agent:
    agent_id, api_key = load_agent_config(CONFIG_KEYS[stage])
    adapter = CouncilAdapter(stage, api_key, agent_names=AGENT_NAMES)
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )
    await agent.start()
    print(f"[band] {stage} connected ({agent.agent_name})")
    return agent


async def main() -> None:
    load_dotenv()
    agents = [await _start_one(stage) for stage in CHAIN]
    print("[band] council online — waiting for handoffs")
    try:
        await asyncio.Event().wait()  # run until cancelled
    finally:
        for a in agents:
            await a.stop()


if __name__ == "__main__":
    asyncio.run(main())
