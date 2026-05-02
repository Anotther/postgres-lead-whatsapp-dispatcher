from __future__ import annotations

import re
from typing import Any

PHONE_LIKE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default

    text = str(value).strip()
    return text or default


def get_first_name(full_name: str | None) -> str:
    name = safe_str(full_name)
    if not name:
        return ""

    return name.split()[0]


def mask_phone(phone: str | int | None) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))

    if not digits:
        return ""

    if len(digits) <= 4:
        return "*" * len(digits)

    if len(digits) <= 8:
        return f"{digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"

    return f"{digits[:4]}{'*' * (len(digits) - 6)}{digits[-2:]}"


def mask_phone_numbers(text: str) -> str:
    return PHONE_LIKE_PATTERN.sub(lambda match: mask_phone(match.group(0)), text)
