from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .settings import settings


@dataclass(frozen=True)
class SendMessageResult:
    success: bool
    instance: str
    number: str
    status_code: int | None = None
    response: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class InstanceStatusResult:
    success: bool
    instance: str
    connected: bool = False
    state: str | None = None
    status_code: int | None = None
    response: dict[str, Any] | None = None
    error: str | None = None


class EvolutionClient:
    """HTTP client for Evolution API / Evolution Go compatible endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.evolution_base_url).rstrip("/")
        self.api_key = api_key or settings.evolution_api_key
        self.timeout_seconds = timeout_seconds or getattr(settings, "request_timeout_seconds", 30)
        self.max_retries = max(1, int(getattr(settings, "max_retries", 3)))

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _parse_state(self, data: dict[str, Any]) -> str | None:
        for nested_key in ("data", "instance"):
            nested_data = data.get(nested_key)
            if isinstance(nested_data, dict):
                connected_value = nested_data.get("Connected", nested_data.get("connected"))
                logged_in_value = nested_data.get("LoggedIn", nested_data.get("loggedIn"))

                if connected_value is True or logged_in_value is True:
                    return "connected"

                if connected_value is False or logged_in_value is False:
                    return "disconnected"

        connected_value = data.get("Connected", data.get("connected"))
        logged_in_value = data.get("LoggedIn", data.get("loggedIn"))

        if connected_value is True or logged_in_value is True:
            return "connected"

        if connected_value is False or logged_in_value is False:
            return "disconnected"

        candidates = [
            data.get("state"),
            data.get("status"),
            data.get("connectionStatus"),
        ]

        for nested_key in ("data", "instance"):
            instance_data = data.get(nested_key)
            if not isinstance(instance_data, dict):
                continue

            candidates.extend(
                [
                    instance_data.get("state"),
                    instance_data.get("status"),
                    instance_data.get("connectionStatus"),
                ]
            )

        for candidate in candidates:
            if candidate is not None:
                return str(candidate).strip().lower()

        return None

    def _connected_states(self) -> set[str]:
        raw_value = getattr(settings, "evolution_connected_states", "open,connected,online")
        return {
            state.strip().lower()
            for state in raw_value.split(",")
            if state.strip()
        }

    def get_instance_status(self, instance: str) -> InstanceStatusResult:
        endpoint_template = getattr(
            settings,
            "evolution_instance_status_path",
            "/instance/connectionState/{instance}",
        )
        url = f"{self.base_url}{endpoint_template.format(instance=instance)}"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=self._headers())

            try:
                response_body = response.json()
            except ValueError:
                response_body = {"raw": response.text}

            if not isinstance(response_body, dict):
                response_body = {"raw": response_body}

            state = self._parse_state(response_body)
            connected = bool(state and state in self._connected_states())

            return InstanceStatusResult(
                success=200 <= response.status_code < 300 and state is not None,
                instance=instance,
                connected=connected,
                state=state,
                status_code=response.status_code,
                response=response_body,
                error=None if state else "instance_state_not_found",
            )

        except Exception as exc:
            return InstanceStatusResult(
                success=False,
                instance=instance,
                error=str(exc),
            )

    def is_instance_connected(self, instance: str) -> bool:
        return self.get_instance_status(instance).connected

    def send_text(
        self,
        *,
        instance: str,
        number: str,
        text: str,
        delay: int = 0,
        link_preview: bool = False,
    ) -> SendMessageResult:
        endpoint_template = getattr(
            settings,
            "evolution_send_text_path",
            "/message/sendText/{instance}",
        )

        url = f"{self.base_url}{endpoint_template.format(instance=instance)}"

        payload = {
            "number": number,
            "text": text,
            "delay": delay,
            "linkPreview": link_preview,
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=self._headers(), json=payload)

                try:
                    response_body = response.json()
                except ValueError:
                    response_body = {"raw": response.text}

                if 200 <= response.status_code < 300:
                    return SendMessageResult(
                        success=True,
                        instance=instance,
                        number=number,
                        status_code=response.status_code,
                        response=response_body,
                    )

                return SendMessageResult(
                    success=False,
                    instance=instance,
                    number=number,
                    status_code=response.status_code,
                    response=response_body,
                    error=f"evolution_api_error_{response.status_code}",
                )

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = str(exc)
                if attempt == self.max_retries:
                    break

            except Exception as exc:
                return SendMessageResult(
                    success=False,
                    instance=instance,
                    number=number,
                    error=str(exc),
                )

        return SendMessageResult(
            success=False,
            instance=instance,
            number=number,
            error=last_error or "evolution_transport_error",
        )
