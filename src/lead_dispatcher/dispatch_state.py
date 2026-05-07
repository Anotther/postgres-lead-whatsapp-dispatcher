from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .settings import settings


class DispatchState:
    def __init__(
        self,
        path: str | Path | None = None,
        *,
        timezone: str | None = None,
    ) -> None:
        self.path = Path(path or settings.dispatch_state_path)
        self.timezone = timezone or settings.timezone
        self.current_date = self._today()
        self.data = self._load()

    def _today(self) -> str:
        try:
            tzinfo = ZoneInfo(self.timezone)
        except Exception:
            tzinfo = ZoneInfo("UTC")

        return datetime.now(tzinfo).date().isoformat()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"date": self.current_date, "instances": {}}

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            return {"date": self.current_date, "instances": {}}

        if data.get("date") != self.current_date:
            return {"date": self.current_date, "instances": {}}

        instances = data.get("instances")
        if not isinstance(instances, dict):
            instances = {}

        return {"date": self.current_date, "instances": instances}

    def get_daily_count(self, instance_name: str) -> int:
        value = self.data.get("instances", {}).get(instance_name, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def increment_daily_count(self, instance_name: str) -> None:
        instances = self.data.setdefault("instances", {})
        instances[instance_name] = self.get_daily_count(instance_name) + 1
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2, sort_keys=True)
