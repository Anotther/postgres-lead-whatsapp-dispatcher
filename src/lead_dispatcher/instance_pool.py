import time
import random
from dataclasses import dataclass


@dataclass
class Instance:
    name: str
    min_delay: int
    max_delay: int
    next_available_at: float = 0
    sent_count: int = 0


class InstancePool:
    def __init__(self, instances: list[Instance]):
        self.instances = instances

    def get_available_instance(self) -> Instance | None:
        now = time.time()

        available = [
            i for i in self.instances
            if i.next_available_at <= now
        ]

        if not available:
            return None

        # escolhe a que enviou menos (balanceamento)
        return sorted(available, key=lambda x: x.sent_count)[0]

    def mark_sent(self, instance: Instance):
        delay = random.randint(instance.min_delay, instance.max_delay)

        instance.next_available_at = time.time() + delay
        instance.sent_count += 1