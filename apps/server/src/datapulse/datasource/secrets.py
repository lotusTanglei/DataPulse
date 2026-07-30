import base64
import binascii
import secrets
from typing import Literal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from datapulse.contracts.common import ContractModel
from datapulse.settings import Settings


class SecretKeyInvalid(ValueError):
    pass


class SecretDecryptionError(ValueError):
    pass


class SecretEnvelope(ContractModel):
    version: Literal[1] = 1
    nonce: str
    ciphertext: str


def _decode_base64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise SecretKeyInvalid("The configured master key is invalid.") from error


def _encode_base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode_envelope_value(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise SecretDecryptionError("The datasource secret cannot be decrypted.") from error


class SecretBox:
    def __init__(self, master_key: str) -> None:
        decoded = _decode_base64(master_key)
        if len(decoded) != 32:
            raise SecretKeyInvalid("The configured master key must decode to 32 bytes.")
        self._cipher = AESGCM(decoded)

    @classmethod
    def from_settings(cls, settings: Settings) -> "SecretBox | None":
        if settings.master_key is None:
            return None
        return cls(settings.master_key)

    @staticmethod
    def _aad(datasource_id: str) -> bytes:
        return f"datapulse:datasource:{datasource_id}:password:v1".encode()

    def encrypt(self, datasource_id: str, password: str) -> SecretEnvelope:
        nonce = secrets.token_bytes(12)
        ciphertext = self._cipher.encrypt(
            nonce,
            password.encode(),
            self._aad(datasource_id),
        )
        return SecretEnvelope(
            nonce=_encode_base64(nonce),
            ciphertext=_encode_base64(ciphertext),
        )

    def decrypt(self, datasource_id: str, envelope: SecretEnvelope) -> str:
        try:
            plaintext = self._cipher.decrypt(
                _decode_envelope_value(envelope.nonce),
                _decode_envelope_value(envelope.ciphertext),
                self._aad(datasource_id),
            )
            return plaintext.decode()
        except (InvalidTag, UnicodeDecodeError, ValueError) as error:
            raise SecretDecryptionError("The datasource secret cannot be decrypted.") from error
