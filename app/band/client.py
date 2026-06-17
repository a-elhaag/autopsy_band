"""Thin Band REST client for posting messages into a chat room.

Wraps `POST /api/v1/agent/chats/{chat_id}/messages`. Every message must carry an
@mention or Band won't route it. Structured handoff data rides in `metadata`.
"""
from __future__ import annotations

import os

import httpx


def _rest_base() -> str:
    return os.getenv("THENVOI_REST_URL", "https://app.band.ai/").rstrip("/")


def send_message(
    *,
    chat_id: str,
    api_key: str,
    content: str,
    mentions: list[dict],
    metadata: dict | None = None,
    timeout: float = 30.0,
) -> None:
    """Post a message addressed to `mentions` into `chat_id`."""
    url = f"{_rest_base()}/api/v1/agent/chats/{chat_id}/messages"
    body = {
        "message": {
            "content": content, "mentions": mentions
        }
    }
    print(f"Posting message to Band: {body}")
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
