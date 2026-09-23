"""Opt-in live TTS provider smoke tests.

These tests deliberately require dedicated, non-production credentials.  They
are skipped unless all provider variables are present and never print the key
or response body.
"""

import os

import httpx
import pytest

from datapulse.speech.providers import ProviderRequest, check_provider, synthesize

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


@pytest.mark.parametrize("provider_type", ["azure", "custom"])
async def test_live_provider_contract(provider_type: str) -> None:
    configured_type = os.getenv("DATAPULSE_LIVE_TTS_PROVIDER_TYPE", "").strip()
    base_url = os.getenv("DATAPULSE_LIVE_TTS_BASE_URL", "").strip()
    api_key = os.getenv("DATAPULSE_LIVE_TTS_API_KEY", "").strip()
    voice = os.getenv("DATAPULSE_LIVE_TTS_VOICE", "").strip()
    language = os.getenv("DATAPULSE_LIVE_TTS_LANGUAGE", "zh-CN").strip()
    if configured_type != provider_type or not all((base_url, api_key, voice)):
        pytest.skip("Set dedicated DATAPULSE_LIVE_TTS_* variables to run live provider checks.")

    async with httpx.AsyncClient() as client:
        request = ProviderRequest(client, 30, api_key)
        voices = await check_provider(provider_type, base_url, request)
        if voices:
            assert voice in voices, "Configured live voice was not returned by the provider."
        audio, mime, response = await synthesize(
            provider_type,
            base_url,
            request,
            text="DataPulse live provider smoke test.",
            language=language,
            voice=voice,
        )
        assert response.status_code < 400
        assert audio
        assert mime.startswith("audio/")
