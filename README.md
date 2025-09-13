# Email Behavior Detection

A small, configurable framework to detect intents from email threads and propose the next step (plus a draft reply) for an email reply team. Built for many paths, not just one example.

## What it does
- Parses a thread (JSON) of emails.
- Detects intents using simple, configurable keyword/regex rules.
- Applies a lightweight policy engine to propose the next action.
- Drafts a reply using templates with placeholders.

## Quick start

- Requirements: Python 3.9+
- Install deps:

```
pip install -r requirements.txt
```

- Run on the example thread:

```
python -m email_behavior_detection.cli \
  --thread examples/thread_example.json \
  --config configs/default_config.yaml \
  --templates templates/default_templates.yaml
```

You’ll see:
- Intents detected per message
- Proposed next step
- A draft reply with placeholders filled

## Streamlit app

- Launch locally:

```
streamlit run streamlit_app.py
```

Then open http://localhost:8501. Upload or paste a thread JSON, optionally provide config/templates, and click "Run detection".

### URLs
- Local development: http://localhost:8501
- Streamlit Cloud (after deploy): https://email-behavior-detection.streamlit.app
  - Replace with your actual app URL shown after deployment.

IMAP in the Streamlit UI:
- Switch Source to "IMAP" in the sidebar.
- Enter host, username, password (App Password), mailbox (INBOX), and a subject.
- Click Run detection. The app will fetch messages by subject and analyze.

Gmail OAuth in Streamlit:
- Switch Auth to "Gmail OAuth2" under IMAP.
- Upload your Google `client_secret.json` (Desktop client).
- First run: follow console instructions to paste the code; a token file is saved for reuse.

### Deploy to Streamlit Community Cloud
1. Push this repo to GitHub (branch: main).
2. Go to https://streamlit.io/cloud and create a new app from your repo.
3. Set main file path to `streamlit_app.py` and deploy. Streamlit will install from `requirements.txt`.

### Deploy to Render (optional)
1. Push to GitHub.
2. In Render, create a new Web Service from repo; it will detect `render.yaml`.
3. Deploy; Render will run `streamlit run streamlit_app.py` on the assigned port.

## Data format (input thread JSON)
Minimal structure used by the example:

```
{
  "subject": "Corporate stay plan (Oct–Dec) — quick check",
  "messages": [
    {
      "timestamp": "Day 0, 09:10",
      "from_name": "Email Reply Team",
      "from_email": "reply-team@yourcompany.com",
      "to": ["sales@sunrisehotel.com"],
      "cc": [],
      "body": "Hi Team, ..."
    }
    // more messages
  ]
}
```

Fields used by detectors: `from_name`, `from_email`, `body`, plus lightweight checks for who sent the email (your team vs external). Extend as needed.

## Connect to your email (IMAP)

The CLI can fetch a thread by subject directly from your inbox via IMAP.

Example:

```
python -m email_behavior_detection.cli \
  --imap \
  --imap-host imap.gmail.com \
  --imap-port 993 \
  --imap-username your.name@gmail.com \
  --imap-password 'APP_PASSWORD' \
  --imap-subject 'Corporate stay plan (Oct–Dec) — quick check' \
  --config configs/default_config.yaml \
  --templates templates/default_templates.yaml
```

Notes:
- Gmail: enable 2FA and use an App Password; regular account passwords won’t work.
- Outlook/Office 365: create an app password or use an IMAP-enabled app-specific credential.
- Security: prefer passing credentials via environment variables and a wrapper script, not the shell history. Consider using a secrets manager for production.
- The IMAP fetcher searches by subject; you can adjust `--imap-limit` and mailbox with `--imap-mailbox`.

### Gmail OAuth2 (no app password)
You can use OAuth2 for Gmail IMAP via XOAUTH2:

```
python -m email_behavior_detection.cli \
  --imap \
  --imap-host imap.gmail.com \
  --imap-port 993 \
  --imap-username your.name@gmail.com \
  --gmail-oauth \
  --gmail-client-secrets path/to/client_secret.json \
  --gmail-token .gmail_token.json \
  --imap-subject 'Corporate stay plan (Oct–Dec) — quick check' \
  --config configs/default_config.yaml \
  --templates templates/default_templates.yaml
```

The first run opens a browser for consent and writes the token file. Subsequent runs reuse and refresh the token automatically.

## Extending
- Add/modify intents or rules in `configs/default_config.yaml`.
- Add/modify templates in `templates/default_templates.yaml`.
- Add new detectors in `email_behavior_detection/intents.py`.
- Update policy/next steps in `email_behavior_detection/policy.py`.

## Notes
- This is intentionally simple and deterministic. For production, consider ML/NLP models, richer state, trust boundaries, audit logs, and human-in-the-loop.