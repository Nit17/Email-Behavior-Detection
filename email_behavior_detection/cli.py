import argparse
import json
from typing import Dict, Any

from .config import load_config
from .models import Thread, Message
from .intents import IntentDetector
from .policy import choose_next_action
from .templating import load_templates, render_template


def _load_thread(path: str) -> Thread:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    messages = [
        Message(
            timestamp=m.get("timestamp", ""),
            from_name=m.get("from_name", ""),
            from_email=m.get("from_email", ""),
            to=m.get("to", []),
            cc=m.get("cc", []),
            body=m.get("body", ""),
            meta=m.get("meta", {}),
        )
        for m in data.get("messages", [])
    ]
    return Thread(subject=data.get("subject", ""), messages=messages)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Email Behavior Detection")
    parser.add_argument("--thread", required=True, help="Path to thread JSON")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--templates", required=True, help="Path to templates YAML")
    parser.add_argument("--context", default="{}", help="Extra JSON context for templates")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    templates = load_templates(args.templates)
    thread = _load_thread(args.thread)
    extra_ctx: Dict[str, Any] = json.loads(args.context)

    detector = IntentDetector(
        rules=cfg.get("rules", {}),
        team_domains=cfg.get("team", {}).get("domains", []),
        team_addresses=cfg.get("team", {}).get("addresses", []),
    )

    all_detections = []
    for msg in thread.messages:
        intents = detector.detect(msg)
        all_detections.append({
            "from": msg.from_email,
            "intents": [i.__dict__ for i in intents],
        })

    latest_intents = []
    if thread.messages:
        latest_intents = detector.detect(thread.messages[-1])

    decision = choose_next_action(latest_intents)

    ctx = {
        "subject": thread.subject,
        "latest_from": thread.messages[-1].from_name if thread.messages else "",
        "latest_email": thread.messages[-1].from_email if thread.messages else "",
        **extra_ctx,
    }
    draft = render_template(templates, decision.get("template", "ack_general"), ctx)

    output = {
        "detections": all_detections,
        "decision": decision,
        "draft": draft,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
