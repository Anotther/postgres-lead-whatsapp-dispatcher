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

        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

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
                    response = client.post(url, headers=headers, json=payload)

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
