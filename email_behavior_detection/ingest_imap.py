import imaplib
import email
from email import policy
from email.utils import parseaddr, getaddresses, parsedate_to_datetime
from html import unescape
import re
from typing import List, Optional

from .models import Thread, Message


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or " ").strip()


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return _clean_text(unescape(text))


def _extract_body(msg: email.message.EmailMessage) -> str:
    if msg.is_multipart():
        # Prefer first text/plain part
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    return part.get_content().strip()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
        # Fallback to first text/html
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/html" and "attachment" not in disp:
                try:
                    return _html_to_text(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    return _html_to_text(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        ctype = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True) or b""
            content = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/html":
            return _html_to_text(content)
        return content.strip()


def fetch_thread_by_subject(
    host: str,
    port: int,
    username: str,
    password: str,
    subject: str,
    mailbox: str = "INBOX",
    limit: Optional[int] = None,
) -> Thread:
    imap = imaplib.IMAP4_SSL(host, port)
    try:
        # Support XOAUTH2 if password starts with 'oauth2:' (then it's an access token)
        if password.startswith("oauth2:"):
            access_token = password.split(":", 1)[1]
            auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
            imap.authenticate("XOAUTH2", lambda x: auth_string)
        else:
            imap.login(username, password)
        imap.select(mailbox)

        # Try subject search (quoted)
        typ, data = imap.search(None, 'SUBJECT', f'"{subject}"')
        ids = []
        if typ == 'OK' and data and len(data) > 0:
            ids = data[0].split()
        if not ids:
            # Fallback to ALL and filter client-side
            typ, data = imap.search(None, 'ALL')
            if typ == 'OK' and data:
                ids = data[0].split()

        # Limit and sort (ascending by date if possible)
        msgs = []
        for msg_id in ids[-(limit or len(ids)):] if ids else []:
            ftyp, fdata = imap.fetch(msg_id, '(RFC822)')
            if ftyp != 'OK' or not fdata or not isinstance(fdata[0], tuple):
                continue
            raw = fdata[0][1]
            em = email.message_from_bytes(raw, policy=policy.default)
            sub = em.get('Subject', '') or ''
            if subject and subject.lower() not in (sub or '').lower():
                # client-side filter when using ALL
                continue
            # Addresses
            from_name, from_email = parseaddr(em.get('From', '') or '')
            to_list = [addr for _, addr in getaddresses(em.get_all('To', []) or []) if addr]
            cc_list = [addr for _, addr in getaddresses(em.get_all('Cc', []) or []) if addr]
            date_hdr = em.get('Date', '') or ''
            try:
                dt = parsedate_to_datetime(date_hdr)
                ts = dt.isoformat()
            except Exception:
                ts = date_hdr
            body = _extract_body(em)
            msgs.append((dt if 'dt' in locals() else None, Message(
                timestamp=ts,
                from_name=from_name or from_email,
                from_email=from_email or '',
                to=to_list,
                cc=cc_list,
                body=body,
                meta={}
            )))

        # Sort by datetime if available
        msgs.sort(key=lambda x: (x[0] or '' ,))
        thread_msgs = [m for _, m in msgs]

        thread_subject = subject or (thread_msgs[0].meta.get('subject') if thread_msgs else '')
        if not thread_subject and msgs:
            # fallback to first message subject
            thread_subject = email.message_from_bytes(
                imap.fetch(ids[0], '(RFC822)')[1][0][1], policy=policy.default
            ).get('Subject', '')

        return Thread(subject=thread_subject, messages=thread_msgs)
    finally:
        try:
            imap.logout()
        except Exception:
            pass
