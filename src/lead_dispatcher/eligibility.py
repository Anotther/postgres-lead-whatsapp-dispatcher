from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EligibilityResult:
    is_eligible: bool
    reason: str = "eligible"


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, int):
        return value == 1

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "sim", "s"}

    return bool(value)


def check_lead_eligibility(lead: dict[str, Any]) -> EligibilityResult:
    """Validate if a lead can receive a message.

    This is a defensive layer. The SQL query should already filter invalid
    leads, but this function protects the dispatcher if the query or source
    schema changes.
    """

    phone = str(lead.get("phone") or "").strip()

    if not phone:
        return EligibilityResult(False, "missing_phone")

    if lead.get("sale_started") is not None and is_truthy(lead.get("sale_started")):
        return EligibilityResult(False, "sale_started")

    if lead.get("enrollment_done") is not None and is_truthy(lead.get("enrollment_done")):
        return EligibilityResult(False, "enrollment_done")

    if lead.get("already_sent") is not None and is_truthy(lead.get("already_sent")):
        return EligibilityResult(False, "already_sent")

    if lead.get("opt_in_whatsapp") is not None and not is_truthy(lead.get("opt_in_whatsapp")):
        return EligibilityResult(False, "missing_whatsapp_opt_in")

    return EligibilityResult(True)