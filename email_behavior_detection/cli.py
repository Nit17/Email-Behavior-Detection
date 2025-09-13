import argparse
import json
from typing import Dict, Any

from .config import load_config
from .models import Thread, Message
from .intents import IntentDetector
from .policy import choose_next_action
from .templating import load_templates, render_template
from .ingest_imap import fetch_thread_by_subject
from .gmail_oauth import get_access_token


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
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--thread", help="Path to thread JSON")
    src.add_argument("--imap", action="store_true", help="Fetch thread via IMAP by subject")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--templates", required=True, help="Path to templates YAML")
    parser.add_argument("--context", default="{}", help="Extra JSON context for templates")
    # IMAP options
    parser.add_argument("--imap-host", help="IMAP server host")
    parser.add_argument("--imap-port", type=int, default=993, help="IMAP SSL port (default 993)")
    parser.add_argument("--imap-username", help="IMAP username (email address)")
    parser.add_argument("--imap-password", help="IMAP password or app-specific password")
    parser.add_argument("--imap-mailbox", default="INBOX", help="Mailbox (default INBOX)")
    parser.add_argument("--imap-subject", help="Subject to match and fetch thread")
    parser.add_argument("--imap-limit", type=int, help="Limit number of messages considered")
    # Gmail OAuth2
    parser.add_argument("--gmail-oauth", action="store_true", help="Use Gmail OAuth2 (XOAUTH2) for IMAP")
    parser.add_argument("--gmail-client-secrets", help="Path to Google OAuth client_secret.json")
    parser.add_argument("--gmail-token", default=".gmail_token.json", help="Path to store OAuth token JSON")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    templates = load_templates(args.templates)
    if args.imap:
        # Basic validation
        required = [args.imap_host, args.imap_username, args.imap_password, args.imap_subject]
        if not all(required):
            parser.error("--imap requires --imap-host, --imap-username, --imap-password, and --imap-subject")
        # Optionally use Gmail OAuth2 to get an access token and pass as oauth2:token
        imap_password = args.imap_password
        if args.gmail_oauth:
            if not args.gmail_client_secrets:
                parser.error("--gmail-oauth requires --gmail-client-secrets")
            token, _ = get_access_token(args.gmail_client_secrets, args.gmail_token)
            imap_password = f"oauth2:{token}"

        thread = fetch_thread_by_subject(
            host=args.imap_host,
            port=args.imap_port,
            username=args.imap_username,
            password=imap_password,
            subject=args.imap_subject,
            mailbox=args.imap_mailbox,
            limit=args.imap_limit,
        )
    else:
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
