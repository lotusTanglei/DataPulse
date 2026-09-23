"""HTTP adapters for the supported digital-human speech provider protocols.

The provider record intentionally stores only a base URL and one secret.  The
wire protocols therefore stay small and deterministic:

* ``openai_compatible``: OpenAI ``/audio/speech`` and ``/voices`` endpoints.
* ``azure``: Azure Speech REST at ``/cognitiveservices/v1`` and
  ``/cognitiveservices/voices/list``.
* ``custom``: a direct POST to ``base_url`` with the documented JSON payload;
  the response must be an audio media type.
"""

from dataclasses import dataclass
from typing import Any

import httpx


class ProviderProtocolError(RuntimeError):
    """A provider response did not satisfy its selected wire protocol."""


@dataclass(frozen=True)
class ProviderRequest:
    client: httpx.AsyncClient
    timeout_seconds: float
    api_key: str


def _audio_content_type(response: httpx.Response) -> str:
    value = response.headers.get("content-type", "audio/mpeg").split(";", 1)[0].strip().lower()
    if not value.startswith("audio/"):
        raise ProviderProtocolError("SPEECH_PROVIDER_INVALID_AUDIO")
    return value


def _voices_from_payload(payload: Any, *, azure: bool = False) -> tuple[str, ...]:
    if azure:
        values = payload if isinstance(payload, list) else []
        result = [item.get("ShortName") for item in values if isinstance(item, dict)]
    else:
        values = payload.get("data") if isinstance(payload, dict) else payload
        result = (
            [item.get("id") if isinstance(item, dict) else item for item in values]
            if isinstance(values, list)
            else []
        )
    voices = [
        value.strip()
        for value in result
        if isinstance(value, str) and value.strip() and len(value.strip()) <= 120
    ]
    return tuple(dict.fromkeys(voices))


async def check_provider(
    provider_type: str, base_url: str, request: ProviderRequest
) -> tuple[str, ...]:
    if provider_type == "openai_compatible":
        response = await request.client.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {request.api_key}"},
            timeout=request.timeout_seconds,
        )
        if response.status_code >= 400:
            raise ProviderProtocolError("SPEECH_PROVIDER_UNAVAILABLE")
        return ()
    if provider_type == "azure":
        response = await request.client.get(
            f"{base_url}/cognitiveservices/voices/list",
            headers={"Ocp-Apim-Subscription-Key": request.api_key},
            timeout=request.timeout_seconds,
        )
        if response.status_code >= 400:
            raise ProviderProtocolError("SPEECH_PROVIDER_UNAVAILABLE")
        try:
            return _voices_from_payload(response.json(), azure=True)
        except (ValueError, TypeError):
            raise ProviderProtocolError("SPEECH_PROVIDER_VOICES_INVALID") from None
    if provider_type == "custom":
        response = await request.client.get(
            f"{base_url}/voices",
            headers={"X-API-Key": request.api_key},
            timeout=request.timeout_seconds,
        )
        if response.status_code >= 400:
            raise ProviderProtocolError("SPEECH_PROVIDER_UNAVAILABLE")
        try:
            return _voices_from_payload(response.json())
        except (ValueError, TypeError):
            raise ProviderProtocolError("SPEECH_PROVIDER_VOICES_INVALID") from None
    raise ProviderProtocolError("SPEECH_PROVIDER_TYPE_UNSUPPORTED")


async def list_voices(
    provider_type: str, base_url: str, request: ProviderRequest
) -> tuple[str, ...]:
    if provider_type == "openai_compatible":
        response = await request.client.get(
            f"{base_url}/voices",
            headers={"Authorization": f"Bearer {request.api_key}"},
            timeout=request.timeout_seconds,
        )
    elif provider_type == "azure":
        response = await request.client.get(
            f"{base_url}/cognitiveservices/voices/list",
            headers={"Ocp-Apim-Subscription-Key": request.api_key},
            timeout=request.timeout_seconds,
        )
    elif provider_type == "custom":
        response = await request.client.get(
            f"{base_url}/voices",
            headers={"X-API-Key": request.api_key},
            timeout=request.timeout_seconds,
        )
    else:
        raise ProviderProtocolError("SPEECH_PROVIDER_TYPE_UNSUPPORTED")
    if response.status_code >= 400:
        raise ProviderProtocolError("SPEECH_PROVIDER_VOICES_UNAVAILABLE")
    try:
        return _voices_from_payload(response.json(), azure=provider_type == "azure")
    except (ValueError, TypeError):
        raise ProviderProtocolError("SPEECH_PROVIDER_VOICES_INVALID") from None


async def synthesize(
    provider_type: str,
    base_url: str,
    request: ProviderRequest,
    *,
    text: str,
    language: str,
    voice: str,
    rate: float = 1,
    pitch: float = 1,
    volume: float = 1,
) -> tuple[bytes, str, httpx.Response]:
    if provider_type == "openai_compatible":
        response = await request.client.post(
            f"{base_url}/audio/speech",
            headers={"Authorization": f"Bearer {request.api_key}"},
            json={
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "language": language,
                "speed": rate,
                "response_format": "mp3",
            },
            timeout=request.timeout_seconds,
        )
    elif provider_type == "azure":
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        ssml = (
            f'<speak version="1.0" xml:lang="{language}">'
            f'<voice name="{voice}"><prosody rate="{(rate - 1) * 100:+.0f}%" '
            f'pitch="{(pitch - 1) * 100:+.0f}%" volume="{volume * 100:.0f}%">'
            f"{escaped}</prosody></voice></speak>"
        )
        response = await request.client.post(
            f"{base_url}/cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": request.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            },
            content=ssml.encode("utf-8"),
            timeout=request.timeout_seconds,
        )
    elif provider_type == "custom":
        response = await request.client.post(
            base_url,
            headers={"X-API-Key": request.api_key},
            json={
                "text": text,
                "language": language,
                "voice": voice,
                "rate": rate,
                "pitch": pitch,
                "volume": volume,
                "response_format": "mp3",
            },
            timeout=request.timeout_seconds,
        )
    else:
        raise ProviderProtocolError("SPEECH_PROVIDER_TYPE_UNSUPPORTED")
    if response.status_code >= 400:
        return b"", "", response
    return response.content, _audio_content_type(response), response
