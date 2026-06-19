import os

def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val

AGENT_CONFIG = {
    "annotator": {
        "agent_id": _require("ANNOTATOR_AGENT_ID"),
        "api_key": _require("ANNOTATOR_API_KEY"),
    },
    "verifier": {
        "agent_id": _require("VERIFIER_AGENT_ID"),
        "api_key": _require("VERIFIER_API_KEY"),
    },
    "scorer": {
        "agent_id": _require("SCORER_AGENT_ID"),
        "api_key": _require("SCORER_API_KEY"),
    },
    "reconstructor": {
        "agent_id": _require("RECONSTRUCTOR_AGENT_ID"),
        "api_key": _require("RECONSTRUCTOR_API_KEY"),
    },
    "apex": {
        "agent_id": _require("APEX_AGENT_ID"),
        "api_key": _require("APEX_API_KEY"),
    },
    "escalation": {
        "agent_id": _require("ESCALATION_AGENT_ID"),
        "api_key": _require("ESCALATION_API_KEY"),
    },
}
