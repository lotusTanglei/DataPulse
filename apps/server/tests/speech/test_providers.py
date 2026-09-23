import json

import httpx
import pytest

from datapulse.speech.providers import (
    ProviderRequest,
    list_voices,
    synthesize,
)
from datapulse.speech.providers import (
    check_provider as provider_test,
)

pytestmark = pytest.mark.anyio


async def test_azure_adapter_uses_ssml_and_subscription_header() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cognitiveservices/v1"
        assert request.headers["Ocp-Apim-Subscription-Key"] == "azure-key"
        assert request.headers["Content-Type"] == "application/ssml+xml"
        assert request.headers["X-Microsoft-OutputFormat"].startswith("audio-")
        assert b'voice name="zh-CN-XiaoxiaoNeural"' in request.content
        assert b"<value>" not in request.content
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"mp3")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        audio, mime, response = await synthesize(
            "azure",
            "https://eastus.tts.speech.microsoft.com",
            ProviderRequest(client, 3, "azure-key"),
            text="当前值 <value>",
            language="zh-CN",
            voice="zh-CN-XiaoxiaoNeural",
        )
        assert response.status_code == 200
        assert audio == b"mp3"
        assert mime == "audio/mpeg"
    finally:
        await client.aclose()


async def test_azure_adapter_lists_short_names() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cognitiveservices/voices/list"
        assert request.headers["Ocp-Apim-Subscription-Key"] == "azure-key"
        return httpx.Response(200, json=[{"ShortName": "zh-CN-XiaoxiaoNeural"}, {"ShortName": ""}])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        request = ProviderRequest(client, 3, "azure-key")
        assert await list_voices("azure", "https://eastus.tts.speech.microsoft.com", request) == (
            "zh-CN-XiaoxiaoNeural",
        )
        assert await provider_test("azure", "https://eastus.tts.speech.microsoft.com", request) == (
            "zh-CN-XiaoxiaoNeural",
        )
    finally:
        await client.aclose()


async def test_custom_adapter_posts_documented_json_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tts"
        assert request.headers["X-API-Key"] == "custom-key"
        assert json.loads(request.content) == {
            "text": "Hello",
            "language": "en-US",
            "voice": "demo",
            "rate": 1,
            "pitch": 1,
            "volume": 1,
            "response_format": "mp3",
        }
        return httpx.Response(200, headers={"content-type": "audio/wav"}, content=b"wav")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        audio, mime, response = await synthesize(
            "custom",
            "https://tts.example.com/tts",
            ProviderRequest(client, 3, "custom-key"),
            text="Hello",
            language="en-US",
            voice="demo",
        )
        assert (audio, mime, response.status_code) == (b"wav", "audio/wav", 200)
    finally:
        await client.aclose()
