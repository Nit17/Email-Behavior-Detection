from typing import Any, Dict
import yaml


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # Normalize expected keys
    cfg.setdefault("team", {})
    cfg["team"].setdefault("domains", [])
    cfg["team"].setdefault("addresses", [])
    cfg.setdefault("rules", {})
    cfg.setdefault("settings", {})
    return cfg
