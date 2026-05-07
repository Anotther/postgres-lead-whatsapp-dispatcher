from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PHONE_LIKE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
PHONE_ALLOWED_PATTERN = re.compile(r"^[\d\s()+.-]+$")


@dataclass(frozen=True)
class PhoneNormalizationResult:
    normalized: str | None
    reason: str | None = None


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


def normalize_phone(
    phone: str | int | None,
    *,
    default_country_code: str = "55",
) -> PhoneNormalizationResult:
    text = safe_str(phone)
    country_code = re.sub(r"\D", "", default_country_code)

    if not text:
        return PhoneNormalizationResult(None, "missing_phone")

    if not PHONE_ALLOWED_PATTERN.fullmatch(text):
        return PhoneNormalizationResult(None, "invalid_phone_characters")

    digits = re.sub(r"\D", "", text)

    if not digits:
        return PhoneNormalizationResult(None, "missing_phone")

    if country_code and not digits.startswith(country_code):
        digits = f"{country_code}{digits}"

    if len(digits) < 12 or len(digits) > 13:
        return PhoneNormalizationResult(None, "invalid_phone_length")

    return PhoneNormalizationResult(digits)
