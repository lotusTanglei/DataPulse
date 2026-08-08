import httpx
import pytest

from datapulse.contracts.dataset import RestQuery
from datapulse.datasource.connector import ConnectorSecret, QueryPolicy
from datapulse.datasource.http_api import HttpApiConnector, HttpApiQueryError
from datapulse.datasource.models import ConnectorType, HttpApiConfig


def test_http_api_config_defaults_and_secret_is_not_in_config() -> None:
    config = HttpApiConfig(base_url="https://api.example.com/v1")

    assert config.type is ConnectorType.HTTP_API
    assert config.auth_type == "none"
    assert config.api_key_header == "X-API-Key"
    assert "password" not in config.model_dump(mode="json")


@pytest.mark.anyio
async def test_http_api_query_normalizes_nested_rows_and_bearer_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["authorization"] == "Bearer token-1"
        assert request.url.params["region"] == "north"
        return httpx.Response(
            200,
            json={"data": [{"name": "north", "total": 12}, {"name": "south", "total": 8}]},
        )

    connector = HttpApiConnector(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    result = await connector.execute_rest(
        HttpApiConfig(base_url="https://api.example.com", auth_type="bearer"),
        ConnectorSecret(password="token-1"),
        RestQuery(
            method="GET",
            url="https://api.example.com/report",
            query={"region": "north"},
            response_path="data",
        ),
        parameters={},
        policy=QueryPolicy(max_rows=100),
        request_id="http-1",
    )

    assert len(requests) == 1
    assert result.columns[0].name == "name"
    assert result.rows == (("north", 12), ("south", 8))
    assert result.row_count == 2


@pytest.mark.anyio
async def test_http_api_query_supports_post_json_and_max_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.read() == b'{"limit":2}'
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}, {"id": 3}])

    connector = HttpApiConnector(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    result = await connector.execute_rest(
        HttpApiConfig(base_url="https://api.example.com"),
        None,
        RestQuery(
            method="POST",
            url="https://api.example.com/items",
            body={"limit": 2},
        ),
        parameters={},
        policy=QueryPolicy(max_rows=2),
        request_id="http-2",
    )

    assert result.rows == ((1,), (2,))
    assert result.truncated is True


@pytest.mark.anyio
async def test_http_api_rejects_private_literal_hosts_and_cross_origin_urls() -> None:
    connector = HttpApiConnector()
    with pytest.raises(HttpApiQueryError, match="safe"):
        await connector.execute_rest(
            HttpApiConfig(base_url="https://127.0.0.1"),
            None,
            RestQuery(url="https://127.0.0.1/items"),
            parameters={},
            policy=QueryPolicy(),
            request_id="http-3",
        )

    with pytest.raises(HttpApiQueryError, match="same host"):
        await connector.execute_rest(
            HttpApiConfig(base_url="https://api.example.com"),
            None,
            RestQuery(url="https://other.example.com/items"),
            parameters={},
            policy=QueryPolicy(),
            request_id="http-4",
        )
