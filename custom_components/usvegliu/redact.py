"""Redaction helpers.

The UniFi API key, voucher codes and tenant passwords must never appear in
logs, diagnostics or bus events. The CSV journal is the only on-disk archive
that keeps the full code, and it is documented as sensitive.
"""

from __future__ import annotations

import logging
from typing import Any

REDACTED: str = "**REDACTED**"

# Compared case-insensitively. Empty values are left untouched so a missing
# secret is still visible as "not set".
SECRET_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "password",
        "mot_de_passe",
        "code_compte",
        "voucher_code",
        "code",
        "alarm_code",
        "token",
        "guest_token",
        "lien_maison",
        "qr_svg",
        "message_invite",
        "guest_email",
        "email",
        "access_token",
        "refresh_token",
        "x-api-key",
        "guest",
        "locataire",
        "username",
        "name",
    }
)


def redact(data: Any) -> Any:
    """Return a copy of data with secret keys replaced."""
    if isinstance(data, dict):
        redacted: dict[Any, Any] = {}
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in SECRET_KEYS:
                if value in (None, ""):
                    redacted[key] = value
                else:
                    redacted[key] = REDACTED
            else:
                redacted[key] = redact(value)
        return redacted
    if isinstance(data, list):
        return [redact(item) for item in data]
    if isinstance(data, tuple):
        return tuple(redact(item) for item in data)
    return data


def mask_code(code: str | None) -> str:
    """Return a non-reversible hint (last two characters only)."""
    if not code:
        return ""
    if len(code) <= 2:
        return "…"
    return f"…{code[-2:]}"


class SecretLogFilter(logging.Filter):
    """Replace known secret values in log records.

    Defense in depth: the integration never logs these values on purpose.
    The filter covers a header or payload that a dependency might log.
    """

    def __init__(self) -> None:
        """Initialize an empty secret list."""
        super().__init__()
        self._secrets: list[str] = []
        self._by_owner: dict[str, list[str]] = {}

    def update(self, secrets: list[str], owner: str = "default") -> None:
        """Replace one owner's secrets. Short values are ignored."""
        cleaned: list[str] = []
        for secret in secrets:
            if not secret or len(secret) < 6:
                continue
            if secret not in cleaned:
                cleaned.append(secret)
        self._by_owner[owner] = cleaned
        self._rebuild()

    def clear(self, owner: str | None = None) -> None:
        """Forget one owner's secrets, or every secret when owner is omitted."""
        if owner is None:
            self._by_owner.clear()
        else:
            self._by_owner.pop(owner, None)
        self._rebuild()

    def _rebuild(self) -> None:
        merged: list[str] = []
        for secrets in self._by_owner.values():
            for secret in secrets:
                if secret not in merged:
                    merged.append(secret)
        self._secrets = merged

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the formatted message. The record is always kept."""
        if not self._secrets:
            return True
        message = record.getMessage()
        redacted = message
        for secret in self._secrets:
            if secret in redacted:
                redacted = redacted.replace(secret, REDACTED)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
