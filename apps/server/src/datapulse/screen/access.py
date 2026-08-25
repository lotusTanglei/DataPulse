from __future__ import annotations

import ipaddress
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, field_validator

from datapulse.contracts.common import ContractModel, NonBlankStr


class ScreenAccessPolicyInvalid(ValueError):
    code = "SCREEN_ACCESS_POLICY_INVALID"


def normalize_origin(origin: str) -> str:
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError as error:
        raise ScreenAccessPolicyInvalid("The screen Origin is invalid.") from error
    hostname = parsed.hostname
    local_http = parsed.scheme == "http" and hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if (
        not hostname
        or (parsed.scheme != "https" and not local_http)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ScreenAccessPolicyInvalid("The screen Origin is invalid.")
    default_port = 443 if parsed.scheme == "https" else 80
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    host = f"[{hostname}]" if ":" in hostname else hostname
    return urlunsplit((parsed.scheme, f"{host}{port_suffix}", "", "", ""))


def normalize_ip_rule(value: str) -> str:
    try:
        address: IPv4Address | IPv6Address
        address = ipaddress.ip_address(value)
    except ValueError:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as error:
            raise ScreenAccessPolicyInvalid(
                "Screen IP rules must be valid IP addresses or CIDR networks."
            ) from error
        return str(network)
    return str(address)


class ScreenAccessPolicy(ContractModel):
    allowed_origins: tuple[NonBlankStr, ...] = Field(default_factory=tuple, max_length=64)
    allowed_ips: tuple[NonBlankStr, ...] = Field(default_factory=tuple, max_length=64)

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(normalize_origin(value) for value in values))

    @field_validator("allowed_ips")
    @classmethod
    def validate_ips(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(normalize_ip_rule(value) for value in values))

    @property
    def restricted(self) -> bool:
        return bool(self.allowed_origins or self.allowed_ips)

    def allows_origin(self, origin: str) -> bool:
        if not self.allowed_origins:
            return True
        try:
            normalized = normalize_origin(origin)
        except ScreenAccessPolicyInvalid:
            return False
        return normalized in self.allowed_origins

    def allows_ip(self, client_ip: str | None) -> bool:
        if not self.allowed_ips:
            return True
        if not client_ip:
            return False
        try:
            address = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
        return any(address in ipaddress.ip_network(rule, strict=False) for rule in self.allowed_ips)

    def allows_request(self, *, origin: str | None, client_ip: str | None) -> bool:
        if not self.restricted:
            return True
        origin_allowed = bool(origin and self.allowed_origins and self.allows_origin(origin))
        ip_allowed = bool(self.allowed_ips and self.allows_ip(client_ip))
        return origin_allowed or ip_allowed

    def allows_embed_client(self, *, ticket_origin: str, client_ip: str | None) -> bool:
        if not self.restricted:
            return True
        origin_allowed = bool(self.allowed_origins and self.allows_origin(ticket_origin))
        ip_allowed = bool(self.allowed_ips and self.allows_ip(client_ip))
        return origin_allowed or ip_allowed


def request_origin_from_headers(
    *,
    origin: str | None,
    referer: str | None,
) -> str | None:
    if origin is not None:
        return normalize_origin(origin)
    if referer is None:
        return None
    parsed = urlsplit(referer)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return normalize_origin(urlunsplit((parsed.scheme, parsed.netloc, "", "", "")))


__all__ = [
    "ScreenAccessPolicy",
    "ScreenAccessPolicyInvalid",
    "normalize_ip_rule",
    "normalize_origin",
    "request_origin_from_headers",
]
