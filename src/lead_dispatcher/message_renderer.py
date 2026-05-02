from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from .settings import settings
from .utils import get_first_name, safe_str


def load_message_config() -> dict[str, Any]:
    path = Path(settings.messages_config_path)

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_enabled_messages(config: dict[str, Any]) -> list[dict[str, Any]]:
    messages = config.get("messages", [])

    return [
        message
        for message in messages
        if message.get("enabled", True)
    ]


def choose_weighted_message(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not messages:
        raise ValueError("No enabled messages found in messages config.")

    weights = [
        int(message.get("weight", 1))
        for message in messages
    ]

    return random.choices(messages, weights=weights, k=1)[0]


def choose_greeting(config: dict[str, Any]) -> str:
    greetings = config.get("greeting_variations") or ["Olá"]

    return random.choice(greetings)


def render_message(lead: dict[str, Any]) -> tuple[str, str]:
    config = load_message_config()
    messages = get_enabled_messages(config)

    selected_message = choose_weighted_message(messages)
    greeting = choose_greeting(config)

    full_name = safe_str(
        lead.get("full_name")
        or lead.get("name")
    )

    first_name = safe_str(
        lead.get("first_name")
        or get_first_name(full_name)
    )

    course_interest = safe_str(
        lead.get("course_interest"),
        "curso de interesse"
    )

    duration_interest = safe_str(
        lead.get("duration_interest"),
        "duração informada"
    )

    text = selected_message["text"].format(
        greeting=greeting,
        first_name=first_name,
        full_name=full_name,
        course_interest=course_interest,
        duration_interest=duration_interest,
    )

    return selected_message["id"], text