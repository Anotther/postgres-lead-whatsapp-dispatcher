from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
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

        except Exception as exc:
            return SendMessageResult(
                success=False,
                instance=instance,
                number=number,
                error=str(exc),
            )