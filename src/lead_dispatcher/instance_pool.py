from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from .settings import settings


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


class InstancePool:
    def __init__(self, instances: list[Instance]):
        self.instances = instances

    def get_available_instance(self) -> Instance | None:
        now = time.time()

        available = [
            i for i in self.instances
            if i.enabled
            and i.next_available_at <= now
            and (i.run_limit is None or i.sent_count < i.run_limit)
        ]

        if not available:
            return None

        # escolhe a que enviou menos (balanceamento)
        return sorted(available, key=lambda x: x.sent_count)[0]

    def mark_sent(self, instance: Instance):
        delay = random.randint(instance.min_delay, instance.max_delay)

        instance.next_available_at = time.time() + delay
        instance.sent_count += 1


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
                run_limit=item.get("run_limit"),
                daily_limit=item.get("daily_limit"),
                report_enabled=bool(item.get("report_enabled", False)),
            )
        )

    return instances
