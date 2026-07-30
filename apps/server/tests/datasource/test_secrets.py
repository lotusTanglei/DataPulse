import base64

import pytest

from datapulse.datasource.secrets import (
    SecretBox,
    SecretDecryptionError,
    SecretKeyInvalid,
)
from datapulse.settings import Settings


@pytest.fixture
def master_key() -> str:
    return base64.urlsafe_b64encode(b"k" * 32).decode()


def test_secret_box_uses_random_nonce_and_datasource_aad(master_key: str) -> None:
    box = SecretBox(master_key)

    first = box.encrypt("source-a", "password")
    second = box.encrypt("source-a", "password")

    assert first != second
    assert box.decrypt("source-a", first) == "password"
    with pytest.raises(SecretDecryptionError):
        box.decrypt("source-b", first)


def test_wrong_key_cannot_decrypt_and_error_contains_no_secret(master_key: str) -> None:
    envelope = SecretBox(master_key).encrypt("source-a", "very-secret-password")
    wrong_key = base64.urlsafe_b64encode(b"x" * 32).decode()

    with pytest.raises(SecretDecryptionError) as captured:
        SecretBox(wrong_key).decrypt("source-a", envelope)

    message = str(captured.value)
    assert "very-secret-password" not in message
    assert envelope.ciphertext not in message
    assert envelope.nonce not in message


@pytest.mark.parametrize(
    "master_key",
    [
        "not base64!",
        base64.urlsafe_b64encode(b"short").decode(),
        base64.urlsafe_b64encode(b"x" * 33).decode(),
    ],
)
def test_secret_box_rejects_malformed_or_wrong_length_keys(master_key: str) -> None:
    with pytest.raises(SecretKeyInvalid):
        SecretBox(master_key)


def test_secret_box_from_settings_allows_missing_key() -> None:
    assert SecretBox.from_settings(Settings(environment="test", master_key=None)) is None


def test_secret_box_from_settings_validates_configured_key(master_key: str) -> None:
    box = SecretBox.from_settings(Settings(environment="test", master_key=master_key))

    assert box is not None
    envelope = box.encrypt("source-a", "password")
    assert box.decrypt("source-a", envelope) == "password"


def test_secret_box_accepts_unpadded_urlsafe_base64_key(master_key: str) -> None:
    box = SecretBox(master_key.rstrip("="))

    envelope = box.encrypt("source-a", "password")
    assert box.decrypt("source-a", envelope) == "password"
