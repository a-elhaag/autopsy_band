from pathlib import Path
import yaml

current = Path(__file__).resolve()

for parent in current.parents:
    candidate = parent / "agent_config.yaml"
    if candidate.exists():
        CONFIG_PATH = candidate
        break
else:
    raise FileNotFoundError("agent_config.yaml not found")

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    AGENT_CONFIG = yaml.safe_load(f)