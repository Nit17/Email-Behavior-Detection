from typing import Dict, Any
import yaml


def load_templates(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Expect a mapping name -> template string
    return data


def render_template(templates: Dict[str, str], name: str, ctx: Dict[str, Any]) -> str:
    tpl = templates.get(name, templates.get("ack_general", ""))
    try:
        return tpl.format(**ctx)
    except Exception:
        # Fallback render without formatting on error
        return tpl
