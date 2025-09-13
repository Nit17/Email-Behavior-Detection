import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .models import Message


@dataclass
class DetectedIntent:
    name: str
    confidence: float
    evidence: str


class IntentDetector:
    def __init__(self, rules: Dict[str, Any], team_domains: List[str], team_addresses: List[str]):
        self.rules = rules or {}
        self.team_domains = [d.lower() for d in (team_domains or [])]
        self.team_addresses = [a.lower() for a in (team_addresses or [])]

    def detect(self, msg: Message) -> List[DetectedIntent]:
        text = f"{msg.from_name}\n{msg.body}".lower()
        intents: List[DetectedIntent] = []

        def add(name: str, conf: float, ev: str):
            intents.append(DetectedIntent(name=name, confidence=conf, evidence=ev))

        # OOO / auto-reply
        if re.search(r"out of office|ooo|auto[- ]?reply|vacation responder", text):
            add("auto_reply_ooo", 0.95, "OOO/auto-reply patterns")

        # Redirect (ask to contact another address)
        if re.search(r"write to|contact|reach (out )?to", text) and re.search(r"@", text):
            add("redirect", 0.7, "Mentions contacting another email")

        # Expressed interest
        if re.search(r"interested|sounds good|please proceed|go ahead", text):
            add("interest", 0.7, "Interest keywords")

        # Asking for pricing, inclusions, late checkout
        if re.search(r"price|pricing|rate|cost", text):
            add("ask_pricing", 0.65, "Price keywords")
        if re.search(r"breakfast|wi[- ]?fi|late checkout|late check[- ]?out", text):
            add("ask_inclusions", 0.6, "Inclusion keywords")

        # Add teammate / CC
        if re.search(r"adding|cc'ing|ccing|looping|include|add (.+?) from our team", text):
            add("add_teammate", 0.6, "Add teammate phrasing")

        # Billing info request
        if re.search(r"billing|invoice|bill to|payment details", text) and re.search(r"confirm|provide|name|email", text):
            add("ask_billing_info", 0.75, "Billing info request")

        # Proceed / confirm
        if re.search(r"please proceed|we aim to confirm|confirm by|let's move forward|go ahead", text):
            add("proceed", 0.7, "Proceed phrasing")

        # Pause reminders
        if re.search(r"pause reminders|stop reminders|hold off|we'll reply", text):
            add("pause_reminders", 0.8, "Pause reminders phrasing")

        # Not interested
        if re.search(r"not interested|no thanks|pass for now", text):
            add("not_interested", 0.9, "Not interested phrasing")

        # Fallback: question
        if re.search(r"\?", msg.body):
            add("question", 0.4, "Contains question mark")

        # If message from our own team, add a meta intent
        from_domain = msg.from_email.split("@")[-1].lower() if "@" in msg.from_email else ""
        if msg.from_email.lower() in self.team_addresses or from_domain in self.team_domains:
            add("from_internal_team", 1.0, "Sender is internal")

        return intents
