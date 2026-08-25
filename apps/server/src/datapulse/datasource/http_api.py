from __future__ import annotations

import ipaddress
import json
from collections.abc import Callable
from time import perf_counter
from urllib.parse import urlsplit

import httpx

from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import RestQuery
from datapulse.datasource.connector import (
    ConnectionTestResult,
    ConnectorSecret,
    NamespaceInfo,
    QueryPolicy,
    RelationInfo,
    RelationSchema,
)
from datapulse.datasource.models import ConnectorType, DatasourceConfig, HttpApiConfig
from datapulse.query.models import QueryColumn, QueryResult, ValidatedQuery


class HttpApiQueryError(ValueError):
    """A safe, user-facing error raised while executing a JSON API query."""


def _is_unsafe_host(host: str | None) -> bool:
    if not host or host.lower() in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # DNS rebinding protection belongs at the deployment egress layer;
        # literal private/link-local addresses are rejected here deterministically.
        return False
    return not address.is_global


def _effective_port(parts: object) -> int:
    scheme = getattr(parts, "scheme", "")
    port = getattr(parts, "port", None)
    return port or (443 if scheme == "https" else 80)


def _data_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "string"
    return "string"


def _rows_from_payload(
    payload: object,
) -> tuple[tuple[QueryColumn, ...], list[tuple[JsonValue, ...]]]:
    if isinstance(payload, list):
        items = payload
    else:
        items = [payload]
    if not items:
        return (), []
    if all(isinstance(item, dict) for item in items):
        names: list[str] = []
        for item in items:
            for name in item:
                if name not in names:
                    names.append(name)
        rows = [tuple(item.get(name) for name in names) for item in items]
        sample = items[0]
        return (
            tuple(QueryColumn(name=name, data_type=_data_type(sample.get(name))) for name in names),
            rows,
        )
    rows = [(item,) for item in items]
    return (QueryColumn(name="value", data_type=_data_type(items[0])),), rows


class HttpApiConnector:
    type = ConnectorType.HTTP_API
    dialect = "http_api"

    def __init__(
        self,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        max_response_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self._client_factory = client_factory or (lambda: httpx.AsyncClient())
        self._max_response_bytes = max_response_bytes

    @staticmethod
    def _config(config: DatasourceConfig) -> HttpApiConfig:
        if not isinstance(config, HttpApiConfig):
            raise HttpApiQueryError("The HTTP API connector requires an HTTP API config.")
        return config

    @staticmethod
    def _auth(
        config: HttpApiConfig,
        secret: ConnectorSecret | None,
    ) -> tuple[dict[str, str], httpx.BasicAuth | None]:
        token = secret.password.get_secret_value() if secret is not None else None
        if config.auth_type == "none":
            return {}, None
        if not token:
            raise HttpApiQueryError("An API credential is required for this datasource.")
        if config.auth_type == "bearer":
            return {"Authorization": f"Bearer {token}"}, None
        if config.auth_type == "api_key":
            return {config.api_key_header: token}, None
        if not config.username:
            raise HttpApiQueryError("A username is required for basic authentication.")
        return {}, httpx.BasicAuth(config.username, token)

    @classmethod
    def _validate_target(cls, config: HttpApiConfig, query: RestQuery) -> str:
        base = urlsplit(str(config.base_url))
        target = urlsplit(str(query.url))
        if _is_unsafe_host(base.hostname) or _is_unsafe_host(target.hostname):
            raise HttpApiQueryError("The HTTP API URL is not a safe public address.")
        if target.scheme != base.scheme or target.hostname != base.hostname:
            raise HttpApiQueryError("The request URL must use the same host as the datasource.")
        if _effective_port(target) != _effective_port(base):
            raise HttpApiQueryError("The request URL must use the same host as the datasource.")
        return str(query.url)

    @staticmethod
    def _response_path(payload: object, path: str | None) -> object:
        if not path:
            return payload
        value = payload
        for part in path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
                continue
            if isinstance(value, list) and part.isdigit() and int(part) < len(value):
                value = value[int(part)]
                continue
            raise HttpApiQueryError("The response_path does not exist in the API response.")
        return value

    async def _request_json(
        self,
        *,
        config: HttpApiConfig,
        secret: ConnectorSecret | None,
        query: RestQuery,
        policy: QueryPolicy,
    ) -> object:
        url = self._validate_target(config, query)
        headers, auth = self._auth(config, secret)
        if query.method == "GET" and query.body is not None:
            raise HttpApiQueryError("GET requests cannot include a JSON body.")
        timeout = httpx.Timeout(policy.timeout_seconds)
        kwargs: dict[str, object] = {
            "params": query.query or None,
            "headers": headers,
            "auth": auth,
            "timeout": timeout,
            "follow_redirects": False,
        }
        if query.method == "POST" and query.body is not None:
            kwargs["json"] = query.body
        try:
            async with self._client_factory() as client:
                async with client.stream(query.method, url, **kwargs) as response:
                    if response.status_code >= 300:
                        raise HttpApiQueryError(
                            f"The HTTP API returned status {response.status_code}."
                        )
                    content_length = response.headers.get("content-length")
                    if (
                        content_length is not None
                        and int(content_length) > self._max_response_bytes
                    ):
                        raise HttpApiQueryError("The HTTP API response is too large.")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self._max_response_bytes:
                            raise HttpApiQueryError("The HTTP API response is too large.")
                        chunks.append(chunk)
        except HttpApiQueryError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            raise HttpApiQueryError("The HTTP API request failed.") from error
        try:
            return json.loads(b"".join(chunks))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise HttpApiQueryError("The HTTP API response is not valid JSON.") from error

    async def execute_rest(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        query: RestQuery,
        *,
        parameters: dict[str, JsonValue],
        policy: QueryPolicy,
        request_id: str,
    ) -> QueryResult:
        started = perf_counter()
        request_query = query.model_copy(update={"query": {**query.query, **parameters}})
        payload = await self._request_json(
            config=self._config(config),
            secret=secret,
            query=request_query,
            policy=policy,
        )
        selected = self._response_path(payload, query.response_path)
        columns, rows = _rows_from_payload(selected)
        truncated = len(rows) > policy.max_rows
        rows = rows[: policy.max_rows]
        return QueryResult(
            request_id=request_id,
            columns=columns,
            rows=tuple(tuple(value for value in row) for row in rows),
            row_count=len(rows),
            truncated=truncated,
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
        )

    async def test_connection(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> ConnectionTestResult:
        started = perf_counter()
        try:
            payload = await self._request_json(
                config=self._config(config),
                secret=secret,
                query=RestQuery(url=self._config(config).base_url),
                policy=QueryPolicy(timeout_seconds=10, max_rows=1),
            )
            del payload
        except HttpApiQueryError:
            return ConnectionTestResult(
                ok=False,
                latency_ms=max(0, round((perf_counter() - started) * 1000)),
                error_code="DATASOURCE_CONNECTION_FAILED",
            )
        return ConnectionTestResult(
            ok=True,
            latency_ms=max(0, round((perf_counter() - started) * 1000)),
        )

    async def list_namespaces(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> tuple[NamespaceInfo, ...]:
        del config, secret
        return ()

    async def list_relations(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
    ) -> tuple[RelationInfo, ...]:
        del config, secret, namespace
        return ()

    async def describe_relation(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
        relation: str,
    ) -> RelationSchema:
        del config, secret, namespace, relation
        raise HttpApiQueryError("HTTP API datasources do not expose database relations.")

    async def stream_query(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        query: ValidatedQuery,
        parameters: dict[str, JsonValue],
        policy: QueryPolicy,
    ) -> object:
        del config, secret, query, parameters, policy
        raise HttpApiQueryError("Use a REST query for HTTP API datasources.")


__all__ = ["HttpApiConnector", "HttpApiQueryError"]
