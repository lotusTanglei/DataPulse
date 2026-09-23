import pytest
from pydantic import ValidationError

from datapulse.contracts.speech import (
    DigitalHumanProviderCreate,
    DigitalHumanProviderUpdate,
    DigitalHumanSettingsUpdate,
    SpeechPlanRequest,
)


def test_provider_contract_never_accepts_plain_external_url_or_unbounded_values() -> None:
    with pytest.raises(ValidationError):
        DigitalHumanProviderCreate(name="tts", provider_type="custom", base_url="file:///secret")
    with pytest.raises(ValidationError):
        DigitalHumanProviderCreate(name="tts", provider_type="custom", language="bad language")
    with pytest.raises(ValidationError):
        DigitalHumanProviderUpdate(base_url="javascript:alert(1)")


def test_provider_secret_is_not_serialized() -> None:
    provider = DigitalHumanProviderCreate(
        name="tts", provider_type="openai_compatible", api_key="secret-value"
    )
    assert "secret-value" not in provider.model_dump_json()
    assert provider.api_key is not None


def test_speech_plan_is_bounded_and_content_is_explicit() -> None:
    plan = SpeechPlanRequest(
        screen_id="screen",
        component_id="speaker",
        text="当前值 123",
        data_fingerprint="generation-1",
    )
    assert plan.text == "当前值 123"
    with pytest.raises(ValidationError):
        SpeechPlanRequest(screen_id="screen", component_id="speaker", text="")


def test_content_governance_patterns_are_validated_and_bounded() -> None:
    settings = DigitalHumanSettingsUpdate(
        forbidden_words=("内部机密",),
        sensitive_patterns=(r"\b\d{16}\b",),
        manual_review_required=True,
    )
    assert settings.forbidden_words == ("内部机密",)
    assert settings.manual_review_required is True
    with pytest.raises(ValidationError):
        DigitalHumanSettingsUpdate(sensitive_patterns=("[",))
