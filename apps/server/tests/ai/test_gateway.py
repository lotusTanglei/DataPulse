from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx
import pytest

from datapulse.ai.gateway import AiGateway
from datapulse.ai.models import AiGatewayError, AiHealth
from datapulse.contracts.ai import AiAnalysisDraft

pytestmark = pytest.mark.anyio


def ai_response_payload() -> dict[str, object]:
    return {
        "plan": {
            "question": "按月份汇总销售额",
            "dataset_ids": ("sales",),
            "dimensions": ("month",),
            "measures": ({"field": "amount", "aggregation": "sum"},),
            "filters": (),
            "sort": (),
            "recommended_chart": "line",
            "assumptions": (),
            "requires_confirmation": True,
        },
        "narrative": "销售额整体上升。",
        "chart_spec": None,
        "warnings": (),
    }


def openai_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        request=httpx.Request("POST", "https://llm.test/chat/completions"),
        json={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                }
            ],
        },
    )


@dataclass
class FakeAsyncClient:
    responses: Sequence[object] = ()
    calls: list[dict[str, object]] = field(default_factory=list)
    closed: bool = False

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        self.calls.append({"url": url, **kwargs})
        outcome = self.responses[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def aclose(self) -> None:
        self.closed = True


async def test_gateway_posts_openai_compatible_json_request() -> None:
    client = FakeAsyncClient(
        responses=(openai_response(AiAnalysisDraft(**ai_response_payload()).model_dump_json()),),
    )
    gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="super-secret",
        model="gpt-4.1-mini",
        timeout_seconds=12,
        client=client,
    )

    response = await gateway.complete_json(
        system="You are an analyst.",
        user="Question: 按月份汇总销售额",
        response_model=AiAnalysisDraft,
    )

    assert response.narrative == "销售额整体上升。"
    assert len(client.calls) == 1
    assert client.calls[0]["url"] == "chat/completions"
    assert client.calls[0]["headers"] == {
        "Authorization": "Bearer super-secret",
        "Content-Type": "application/json",
    }
    assert client.calls[0]["timeout"] == 12
    assert client.calls[0]["json"] == {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "You are an analyst."},
            {"role": "user", "content": "Question: 按月份汇总销售额"},
        ],
        "response_format": {"type": "json_object"},
    }


async def test_gateway_retries_once_for_transient_http_errors_and_redacts_api_key() -> None:
    api_key = "top-secret-key"
    client = FakeAsyncClient(
        responses=(
            httpx.ConnectError(
                "boom", request=httpx.Request("POST", "https://llm.test/chat/completions")
            ),
            openai_response(AiAnalysisDraft(**ai_response_payload()).model_dump_json()),
        ),
    )
    gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key=api_key,
        model="gpt-4.1-mini",
        timeout_seconds=30,
        client=client,
    )

    response = await gateway.complete_json(
        system="system",
        user="user",
        response_model=AiAnalysisDraft,
    )

    assert response.plan.dataset_ids == ("sales",)
    assert len(client.calls) == 2


async def test_gateway_maps_timeout_after_one_retry() -> None:
    client = FakeAsyncClient(
        responses=(
            httpx.ReadTimeout(
                "slow", request=httpx.Request("POST", "https://llm.test/chat/completions")
            ),
            httpx.ReadTimeout(
                "still slow", request=httpx.Request("POST", "https://llm.test/chat/completions")
            ),
        ),
    )
    gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="secret",
        model="gpt-4.1-mini",
        timeout_seconds=5,
        client=client,
    )

    with pytest.raises(AiGatewayError) as error:
        await gateway.complete_json(
            system="system",
            user="user",
            response_model=AiAnalysisDraft,
        )

    assert error.value.code == "AI_TIMEOUT"
    assert "secret" not in str(error.value)
    assert len(client.calls) == 2


async def test_gateway_rejects_invalid_json_model_refusal_and_non_2xx() -> None:
    invalid_json_gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="secret",
        model="gpt-4.1-mini",
        timeout_seconds=5,
        client=FakeAsyncClient(responses=(openai_response("{not json"),)),
    )
    with pytest.raises(AiGatewayError) as invalid_json_error:
        await invalid_json_gateway.complete_json(
            system="system",
            user="user",
            response_model=AiAnalysisDraft,
        )
    assert invalid_json_error.value.code == "AI_INVALID_OUTPUT"

    refusal_gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="secret",
        model="gpt-4.1-mini",
        timeout_seconds=5,
        client=FakeAsyncClient(
            responses=(
                httpx.Response(
                    200,
                    request=httpx.Request("POST", "https://llm.test/chat/completions"),
                    json={
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "refusal": "I refuse.",
                                }
                            }
                        ]
                    },
                ),
            ),
        ),
    )
    with pytest.raises(AiGatewayError) as refusal_error:
        await refusal_gateway.complete_json(
            system="system",
            user="user",
            response_model=AiAnalysisDraft,
        )
    assert refusal_error.value.code == "AI_INVALID_OUTPUT"

    unavailable_gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="secret",
        model="gpt-4.1-mini",
        timeout_seconds=5,
        client=FakeAsyncClient(
            responses=(
                httpx.Response(
                    503,
                    request=httpx.Request("POST", "https://llm.test/chat/completions"),
                    json={"error": {"message": "backend unavailable"}},
                ),
                httpx.Response(
                    503,
                    request=httpx.Request("POST", "https://llm.test/chat/completions"),
                    json={"error": {"message": "backend unavailable"}},
                ),
            ),
        ),
    )
    with pytest.raises(AiGatewayError) as unavailable_error:
        await unavailable_gateway.complete_json(
            system="system",
            user="user",
            response_model=AiAnalysisDraft,
        )
    assert unavailable_error.value.code == "AI_UNAVAILABLE"


async def test_gateway_reports_unconfigured_health_and_skips_network() -> None:
    client = FakeAsyncClient()
    gateway = AiGateway(
        enabled=False,
        base_url=None,
        api_key=None,
        model=None,
        timeout_seconds=30,
        client=client,
    )

    assert gateway.health() == AiHealth(status="unconfigured", model=None)
    with pytest.raises(AiGatewayError) as error:
        await gateway.complete_json(
            system="system",
            user="user",
            response_model=AiAnalysisDraft,
        )
    assert error.value.code == "AI_NOT_CONFIGURED"
    assert client.calls == []


async def test_gateway_closes_owned_client() -> None:
    client = FakeAsyncClient()
    gateway = AiGateway(
        enabled=True,
        base_url="https://llm.test",
        api_key="secret",
        model="gpt-4.1-mini",
        timeout_seconds=30,
        client=client,
    )

    await gateway.aclose()

    assert client.closed is True
