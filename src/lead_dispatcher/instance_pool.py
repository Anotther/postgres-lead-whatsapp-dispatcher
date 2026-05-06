from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from .settings import settings


def _optional_int(value) -> int | None:
    if value is None:
        return None

    return int(value)


@dataclass
class Instance:
    name: str
    min_delay: int
    max_delay: int
    enabled: bool = True
    run_limit: int | None = None
    daily_limit: int | None = None
    report_enabled: bool = False
    next_available_at: float = 0
    sent_count: int = 0
    daily_sent_count: int = 0


class InstancePool:
    def __init__(self, instances: list[Instance]):
        self.instances = instances

    def get_available_instance(self, *, ignore_limits: bool = False) -> Instance | None:
        now = time.time()

        available = [
            i for i in self.instances
            if i.enabled
            and i.next_available_at <= now
            and (
                ignore_limits
                or (
                    (i.run_limit is None or i.sent_count < i.run_limit)
                    and (i.daily_limit is None or i.daily_sent_count < i.daily_limit)
                )
            )
        ]

        if not available:
            return None

        # escolhe a que enviou menos (balanceamento)
        return sorted(available, key=lambda x: x.sent_count)[0]

    def mark_sent(self, instance: Instance):
        delay = random.randint(instance.min_delay, instance.max_delay)

        instance.next_available_at = time.time() + delay
        instance.sent_count += 1
        instance.daily_sent_count += 1

    def has_enabled_instances(self) -> bool:
        return any(instance.enabled for instance in self.instances)

    def next_available_instance(self, *, ignore_limits: bool = False) -> Instance | None:
        limited_instances = [
            instance for instance in self.instances
            if instance.enabled
            and (
                ignore_limits
                or (
                    (instance.run_limit is None or instance.sent_count < instance.run_limit)
                    and (
                        instance.daily_limit is None
                        or instance.daily_sent_count < instance.daily_limit
                    )
                )
            )
        ]

        if not limited_instances:
            return None

        return sorted(limited_instances, key=lambda instance: instance.next_available_at)[0]

    def all_enabled_instances_at_limit(self) -> bool:
        enabled_instances = [instance for instance in self.instances if instance.enabled]

        if not enabled_instances:
            return False

        return all(
            (
                instance.run_limit is not None
                and instance.sent_count >= instance.run_limit
            )
            or (
                instance.daily_limit is not None
                and instance.daily_sent_count >= instance.daily_limit
            )
            for instance in enabled_instances
        )


def load_instances_config() -> list[Instance]:
    path = Path(settings.instances_config_path)

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    instances = []
    for item in config.get("instances", []):
        instances.append(
            Instance(
                name=item["name"],
                enabled=bool(item.get("enabled", True)),
                min_delay=int(item.get("min_delay_seconds", 45)),
                max_delay=int(item.get("max_delay_seconds", 120)),
                run_limit=_optional_int(item.get("run_limit")),
                daily_limit=_optional_int(item.get("daily_limit")),
                report_enabled=bool(item.get("report_enabled", False)),
            )
        )

    return instances


def apply_daily_counts(instances: list[Instance], daily_counts: dict[str, int]) -> None:
    for instance in instances:
        instance.daily_sent_count = int(daily_counts.get(instance.name, 0))
