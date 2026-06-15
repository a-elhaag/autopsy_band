"""Cross-process result store for completed diagnoses.

Band agents run as a separate long-lived process from the web app. When the
final agent (HumanEscalation) finishes, it writes the report here keyed by
correlation_id; the web app polls for it. Backed by a JSON file under the system
temp dir — simple, dependency-free, fine for a single-host demo. Swap for Redis
if you need multi-host.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

_DIR = Path(tempfile.gettempdir()) / "autopsy_band_results"


def _path(correlation_id: str) -> Path:
    return _DIR / f"{correlation_id}.json"


def put(correlation_id: str, report: dict) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    _path(correlation_id).write_text(json.dumps(report))


def get(correlation_id: str) -> dict | None:
    p = _path(correlation_id)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def wait(correlation_id: str, timeout: float = 120.0, poll: float = 0.5) -> dict | None:
    """Block until the report appears or timeout elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        report = get(correlation_id)
        if report is not None:
            return report
        time.sleep(poll)
    return None
