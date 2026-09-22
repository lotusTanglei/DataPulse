from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from datapulse.ai.models import AiGatewayError, AiHealth

T = TypeVar("T", bound=BaseModel)


class AiGateway:
    _schema_capability_cache: dict[tuple[str, str], bool] = {}

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

    @classmethod
    def clear_capability_cache(cls) -> None:
        cls._schema_capability_cache.clear()

    def _capability_key(self, model: str | None) -> tuple[str, str]:
        return (self._base_url or "", model or self._model or "")

    def _payload(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        model: str | None = None,
        strict_schema: bool = True,
    ) -> dict[str, object]:
        response_format: dict[str, object]
        if strict_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__.lower(),
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            }
        else:
            response_format = {"type": "json_object"}
        return {
            "model": model or self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": response_format,
        }

    @staticmethod
    def _strict_schema_unsupported(response: httpx.Response) -> bool:
        if response.status_code != 400:
            return False
        try:
            body = response.json()
        except ValueError:
            body = response.text
        text = str(body).lower()
        return "response_format" in text or "json_schema" in text or "structured output" in text

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
        model: str | None = None,
        timeout_seconds: int | float | None = None,
    ) -> T:
        self.ensure_configured()
        assert self._client is not None

        selected_model = model or self._model
        capability_key = self._capability_key(selected_model)
        strict_schema = self._schema_capability_cache.get(capability_key, True)
        retry_count = 0
        while True:
            try:
                response = await self._client.post(
                    "chat/completions",
                    headers=self._headers(),
                    json=self._payload(
                        system=system,
                        user=user,
                        response_model=response_model,
                        model=model,
                        strict_schema=strict_schema,
                    ),
                    timeout=timeout_seconds or self._timeout_seconds,
                )
            except httpx.TimeoutException as error:
                if retry_count == 0:
                    retry_count += 1
                    continue
                raise AiGatewayError("AI_TIMEOUT", "AI request timed out.") from error
            except httpx.HTTPError as error:
                if retry_count == 0:
                    retry_count += 1
                    continue
                raise AiGatewayError("AI_UNAVAILABLE", "AI service is unavailable.") from error

            if strict_schema and self._strict_schema_unsupported(response):
                self._schema_capability_cache[capability_key] = False
                strict_schema = False
                continue
            if response.status_code >= 500 and retry_count == 0:
                retry_count += 1
                continue
            if response.status_code >= 400:
                code = "AI_RATE_LIMITED" if response.status_code == 429 else "AI_PROVIDER_4XX"
                if response.status_code >= 500:
                    code = "AI_UNAVAILABLE"
                raise AiGatewayError(code, "AI provider request failed.")

            if capability_key not in self._schema_capability_cache:
                self._schema_capability_cache[capability_key] = strict_schema

            try:
                payload = response.json()
            except ValueError as error:
                raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.") from error
            content = self._extract_content(payload)
            try:
                return response_model.model_validate_json(content)
            except (ValidationError, ValueError) as error:
                raise AiGatewayError("AI_INVALID_OUTPUT", "AI response is invalid.") from error


__all__ = ["AiGateway"]
