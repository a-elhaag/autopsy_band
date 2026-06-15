"""Band SDK integration — the real inter-agent transport for the council.

The 6 agents run as distributed Band (thenvoi) agents in one chat room. Each
handoff from agent.md is a Band message carrying the running diagnosis as
structured `metadata`, routed to the next agent by @mention.

The diagnostic logic itself lives in `app/agents/stages.py` and is shared with
the in-process orchestrator, so both paths produce identical results.
"""
