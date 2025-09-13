import json
import streamlit as st

from email_behavior_detection.models import Thread, Message
from email_behavior_detection.config import load_config
from email_behavior_detection.intents import IntentDetector
from email_behavior_detection.policy import choose_next_action
from email_behavior_detection.templating import load_templates, render_template
from email_behavior_detection.ingest_imap import fetch_thread_by_subject
from email_behavior_detection.gmail_oauth import get_access_token


st.set_page_config(page_title="Email Behavior Detection", layout="wide")
st.title("Email Behavior Detection")
st.caption("Detect intents from threads and propose next steps + draft a reply.")


with st.sidebar:
    st.header("Inputs")
    mode = st.radio("Source", ["Upload/Paste JSON", "IMAP"], index=0)
    if mode == "Upload/Paste JSON":
        thread_file = st.file_uploader("Upload thread JSON", type=["json"], accept_multiple_files=False)
        thread_text = st.text_area("Or paste thread JSON", height=160)
    else:
        st.subheader("IMAP")
        imap_host = st.text_input("IMAP host", placeholder="imap.gmail.com")
        imap_port = st.number_input("IMAP port", value=993, step=1)
        imap_username = st.text_input("Username (email)")
        auth_mode = st.radio("Auth", ["Password/App Password", "Gmail OAuth2"], index=0)
        imap_password = ""
        gmail_client_secret = None
        gmail_token_file = None
        if auth_mode == "Password/App Password":
            imap_password = st.text_input("Password / App Password", type="password")
        else:
            st.caption("Provide Google OAuth client secrets. First run will ask for consent and store a token.")
            client_file = st.file_uploader("client_secret.json", type=["json"], accept_multiple_files=False, key="client_secret")
            token_filename = st.text_input("Token filename (persisted)", value=".gmail_token.json")
            if client_file is not None:
                gmail_client_secret = client_file.read().decode("utf-8")
                gmail_token_file = token_filename
        imap_mailbox = st.text_input("Mailbox", value="INBOX")
        imap_subject = st.text_input("Subject contains", placeholder="Exact or partial subject")
        imap_limit = st.number_input("Limit messages (optional)", min_value=0, value=0, step=1)

    st.divider()
    config_file = st.file_uploader("Config (YAML)", type=["yaml", "yml"], accept_multiple_files=False)
    templates_file = st.file_uploader("Templates (YAML)", type=["yaml", "yml"], accept_multiple_files=False)

    ctx_text = st.text_area("Extra context (JSON)", value="{}", height=100)
    run_btn = st.button("Run detection")


def _load_json_bytes(b: bytes):
    return json.loads(b.decode("utf-8"))


def _load_yaml_bytes(b: bytes):
    import yaml
    return yaml.safe_load(b.decode("utf-8"))


col1, col2 = st.columns([1, 1])

if run_btn:
    try:
        # Thread source
        if mode == "Upload/Paste JSON":
            if 'thread_file' in locals() and thread_file is not None:
                thread_data = _load_json_bytes(thread_file.read())
            elif 'thread_text' in locals() and thread_text.strip():
                thread_data = json.loads(thread_text)
            else:
                st.error("Please upload or paste a thread JSON.")
                st.stop()
        else:
            # IMAP path
            if not (imap_host and imap_username and imap_subject):
                st.error("IMAP: host, username, and subject are required.")
                st.stop()
            # Determine auth
            pwd = imap_password
            if auth_mode == "Gmail OAuth2":
                if not gmail_client_secret:
                    st.error("Upload client_secret.json for Gmail OAuth2.")
                    st.stop()
                # Persist client_secret.json and token file on disk for the helper
                import os, json as _json
                cs_path = ".gmail_client_secret.json"
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(gmail_client_secret)
                token_path = gmail_token_file or ".gmail_token.json"
                token, _ = get_access_token(cs_path, token_path, use_console=True)
                pwd = f"oauth2:{token}"
            thread = fetch_thread_by_subject(
                host=imap_host,
                port=int(imap_port or 993),
                username=imap_username,
                password=pwd,
                subject=imap_subject,
                mailbox=imap_mailbox or "INBOX",
                limit=int(imap_limit or 0) or None,
            )
            thread_data = {
                "subject": thread.subject,
                "messages": [
                    {
                        "timestamp": m.timestamp,
                        "from_name": m.from_name,
                        "from_email": m.from_email,
                        "to": m.to,
                        "cc": m.cc,
                        "body": m.body,
                        "meta": m.meta,
                    }
                    for m in thread.messages
                ],
            }

        # Config
        if config_file is not None:
            cfg = _load_yaml_bytes(config_file.read()) or {}
        else:
            # Fallback to default config in repo
            cfg = load_config("configs/default_config.yaml")

        # Templates
        if templates_file is not None:
            templates = _load_yaml_bytes(templates_file.read()) or {}
        else:
            templates = load_templates("templates/default_templates.yaml")

        # Context
        extra_ctx = json.loads(ctx_text or "{}")

    # Build objects
        messages = [
            {
                "timestamp": m.get("timestamp", ""),
                "from_name": m.get("from_name", ""),
                "from_email": m.get("from_email", ""),
                "to": m.get("to", []),
                "cc": m.get("cc", []),
                "body": m.get("body", ""),
                "meta": m.get("meta", {}),
            }
            for m in thread_data.get("messages", [])
        ]

        # Build Thread object directly
        thread = Thread(
            subject=thread_data.get("subject", ""),
            messages=[
                Message(
                    timestamp=m["timestamp"],
                    from_name=m["from_name"],
                    from_email=m["from_email"],
                    to=m.get("to", []),
                    cc=m.get("cc", []),
                    body=m.get("body", ""),
                    meta=m.get("meta", {}),
                )
                for m in messages
            ],
        )

    except Exception as e:
        st.exception(e)
        st.stop()

    # Detect
    detector = IntentDetector(
        rules=cfg.get("rules", {}),
        team_domains=cfg.get("team", {}).get("domains", []),
        team_addresses=cfg.get("team", {}).get("addresses", []),
    )

    detections = []
    for msg in thread.messages:
        intents = detector.detect(msg)
        detections.append({"from": msg.from_email, "intents": [i.__dict__ for i in intents]})

    latest_intents = detector.detect(thread.messages[-1]) if thread.messages else []
    decision = choose_next_action(latest_intents)
    ctx = {
        "subject": thread.subject,
        "latest_from": thread.messages[-1].from_name if thread.messages else "",
        "latest_email": thread.messages[-1].from_email if thread.messages else "",
        **extra_ctx,
    }
    draft = render_template(templates, decision.get("template", "ack_general"), ctx)

    with col1:
        st.subheader("Detections")
        st.json(detections)
        st.subheader("Decision")
        st.json(decision)

    with col2:
        st.subheader("Draft reply")
        st.code(draft, language="markdown")

else:
    with col1:
        st.info("Upload or paste a thread JSON, optionally provide config/templates, then click Run detection.")
    with col2:
        st.code("""{
  "subject": "...",
  "messages": [
    {"timestamp": "...", "from_name": "...", "from_email": "...", "to": ["..."], "cc": ["..."], "body": "..."}
  ]
}
""", language="json")
