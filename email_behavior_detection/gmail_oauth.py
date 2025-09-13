from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://mail.google.com/"]


def load_or_create_credentials(
    client_secrets_file: str,
    token_file: str,
    use_console: bool = False,
) -> Credentials:
    token_path = Path(token_file)
    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            if use_console:
                # Prints a URL and asks for code — works on Streamlit Cloud
                creds = flow.run_console()
            else:
                # Local server flow opens a browser for consent — best for local runs
                creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        token_path.write_text(creds.to_json())
    return creds


def get_access_token(
    client_secrets_file: str,
    token_file: str,
    use_console: bool = False,
) -> Tuple[str, Credentials]:
    creds = load_or_create_credentials(client_secrets_file, token_file, use_console=use_console)
    if not creds.valid:
        creds.refresh(Request())
    return creds.token, creds
