import pytest

from datapulse.auth.password import hash_password, verify_password


def test_password_hash_uses_argon2_and_verifies() -> None:
    encoded = hash_password("correct horse battery staple")

    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_password_rejects_less_than_ten_characters() -> None:
    with pytest.raises(ValueError, match="at least 10"):
        hash_password("too-short")
