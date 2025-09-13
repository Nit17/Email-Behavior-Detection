from typing import List, Dict, Any

from .intents import DetectedIntent


def choose_next_action(intents: List[DetectedIntent]) -> Dict[str, Any]:
    # Priority order for actionable intents
    priority = [
        "pause_reminders",
        "not_interested",
        "proceed",
        "ask_billing_info",
        "add_teammate",
        "ask_pricing",
        "ask_inclusions",
        "redirect",
        "auto_reply_ooo",
        "interest",
    ]

    best = None
    for name in priority:
        for it in intents:
            if it.name == name:
                best = it
                break
        if best:
            break

    if not best:
        return {"action": "acknowledge_and_offer_help", "template": "ack_general"}

    mapping = {
        "pause_reminders": {"action": "pause_reminders", "template": "ack_pause"},
        "not_interested": {"action": "log_and_close", "template": "ack_not_interested"},
        "proceed": {"action": "send_agreement_and_form", "template": "send_agreement"},
        "ask_billing_info": {"action": "provide_billing_details", "template": "provide_billing"},
        "add_teammate": {"action": "welcome_teammate_and_share_docs", "template": "ack_add_teammate"},
        "ask_pricing": {"action": "send_price_list", "template": "send_pricing"},
        "ask_inclusions": {"action": "send_inclusions_info", "template": "send_inclusions"},
        "redirect": {"action": "route_to_address", "template": "ack_redirect"},
        "auto_reply_ooo": {"action": "schedule_followup_after_ooo", "template": "ack_ooo"},
        "interest": {"action": "send_materials_and_questions", "template": "send_materials"},
    }

    return mapping.get(best.name, {"action": "acknowledge_and_offer_help", "template": "ack_general"})
