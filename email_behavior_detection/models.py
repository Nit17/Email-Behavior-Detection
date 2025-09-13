from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Message:
    timestamp: str
    from_name: str
    from_email: str
    to: List[str]
    cc: List[str]
    body: str
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class Thread:
    subject: str
    messages: List[Message]

    def latest(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None


def is_from_team(msg: Message, team_domains: List[str], team_addresses: List[str]) -> bool:
    email = msg.from_email.lower().strip()
    domain = email.split("@")[-1] if "@" in email else ""
    return email in {a.lower() for a in team_addresses} or domain in {d.lower() for d in team_domains}
