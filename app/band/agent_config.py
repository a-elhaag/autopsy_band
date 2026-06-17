from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).with_name("agent_config.yaml")

with CONFIG_PATH.open() as f:
    AGENT_CONFIG = yaml.safe_load(f)
