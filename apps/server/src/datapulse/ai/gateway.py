from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from datapulse.ai.models import AiGatewayError, AiHealth

T = TypeVar("T", bound=BaseModel)


class AiGateway:
    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str | None,
        api_key: str | None,
        model: str | None,
        timeout_seconds: int,
        client: httpx.AsyncClient | Any | None = None,
    ) -> None:
        self._enabled = enabled
        self._base_url = base_url.rstrip("/") if isinstance(base_url, str) else None
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._owns_client = client is None and self._is_configured()
        self._client = client
        if self._client is None and self._owns_client:
            self._client = httpx.AsyncClient(base_url=self._base_url)

    def _is_configured(self) -> bool:
        return self._enabled and all(
            isinstance(value, str) and value.strip() != ""
            for value in (self._base_url, self._api_key, self._model)
        )

    def health(self) -> AiHealth:
        if not self._is_configured():
            return AiHealth(status="unconfigured", model=None)
        return AiHealth(status="configured", model=self._model)

    def ensure_configured(self) -> None:
        if not self._is_configured() or self._client is None:
            raise AiGatewayError("AI_NOT_CONFIGURED", "AI is not configured.")

    async def aclose(self) -> None:
        if self._client is not None and hasattr(self._client, "aclose"):
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, *, system: str, user: str) -> dict[str, object]:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }

    def _extract_content(self, payload: object) -> str:
        if not isinstance(payload, dict):
            raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")
        first = choices[0]
        if not isinstance(first, dict):
            raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")
        message = first.get("message")
        if not isinstance(message, dict):
            raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")
        refusal = message.get("refusal")
        if isinstance(refusal, str) and refusal.strip() != "":
            raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")
        content = message.get("content")
        if isinstance(content, str) and content.strip() != "":
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            joined = "".join(parts).strip()
            if joined != "":
                return joined
        raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.")

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        self.ensure_configured()
        assert self._client is not None

        last_timeout: httpx.TimeoutException | None = None
        last_http_error: httpx.HTTPError | None = None
        for attempt in range(2):
            try:
                response = await self._client.post(
                    "chat/completions",
                    headers=self._headers(),
                    json=self._payload(system=system, user=user),
                    timeout=self._timeout_seconds,
                )
            except httpx.TimeoutException as error:
                last_timeout = error
                if attempt == 0:
                    continue
                raise AiGatewayError("AI_TIMEOUT", "AI request timed out.") from error
            except httpx.HTTPError as error:
                last_http_error = error
                if attempt == 0:
                    continue
                raise AiGatewayError("AI_UNAVAILABLE", "AI service is unavailable.") from error

            if response.status_code >= 500 and attempt == 0:
                continue
            if response.status_code >= 400:
                raise AiGatewayError("AI_UNAVAILABLE", "AI service is unavailable.")

            try:
                payload = response.json()
            except ValueError as error:
                raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.") from error
            content = self._extract_content(payload)
            try:
                return response_model.model_validate_json(content)
            except (ValidationError, ValueError) as error:
                raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.") from error

        if last_timeout is not None:
            raise AiGatewayError("AI_TIMEOUT", "AI request timed out.") from last_timeout
        if last_http_error is not None:
            raise AiGatewayError(
                "AI_UNAVAILABLE", "AI service is unavailable."
            ) from last_http_error
        raise AiGatewayError("AI_UNAVAILABLE", "AI service is unavailable.")


__all__ = ["AiGateway"]
