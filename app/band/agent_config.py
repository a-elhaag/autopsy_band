import yaml

with open("agent_config.yaml", "r") as f:
    AGENT_CONFIG = yaml.safe_load(f)