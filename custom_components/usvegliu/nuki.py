"""Nuki Web API client for per-stay keypad PINs.

The official Home Assistant Nuki / Matter lock entities cannot manage
Keypad codes. This talks to api.nuki.io with a Web API token. PINs are
six digits 1–9, never 0, and must not start with 12.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
import re
import secrets
from typing import Any

import aiohttp

from .planning import sanitize_guest

_LOGGER = logging.getLogger(__name__)

NUKI_API = "https://api.nuki.io"
AUTH_TYPE_KEYPAD = 13
PIN_LENGTH = 6
_PIN_DIGITS = "123456789"
_NAME_MAX = 20


class NukiError(Exception):
    """Nuki Web API failure. Callers must not abort UniFi or HA revoke."""


class NukiAuthError(NukiError):
    """HTTP 401/403: the Web API token was refused."""


@dataclass(frozen=True)
class KeypadAuth:
    """One keypad authorization on a Nuki smartlock."""

    id: str
    name: str
    code: str = ""


def is_valid_nuki_pin(code: str) -> bool:
    """True for a 6-digit Keypad PIN that Nuki will accept."""
    return (
        len(code) == PIN_LENGTH
        and all(digit in _PIN_DIGITS for digit in code)
        and not code.startswith("12")
    )


def generate_nuki_pin(existing: set[str] | None = None) -> str:
    """Return a unique Keypad PIN that is not already listed."""
    taken = {pin for pin in (existing or set()) if pin}
    for _ in range(400):
        pin = "".join(secrets.choice(_PIN_DIGITS) for _ in range(PIN_LENGTH))
        if pin.startswith("12") or pin in taken:
            continue
        return pin
    raise NukiError("nuki pin space exhausted")


def keypad_auth_name(guest: str, key: str) -> str:
    """Stable Nuki auth name (≤20 chars) unique to this stay."""
    digest = hashlib.sha1(f"{guest}|{key}".encode("utf-8")).hexdigest()[:8]
    base = re.sub(r"[^A-Za-z0-9]", "", sanitize_guest(guest))[:11] or "Loc"
    return f"{base} {digest}"[:_NAME_MAX]


def nuki_datetime(value: datetime) -> str:
    """UTC instant in the form Nuki documents for allowedFrom/UntilDate."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def extract_auths(payload: Any) -> list[KeypadAuth]:
    """Parse GET /smartlock/{id}/auth. Keypad PINs only (type 13)."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        items = payload["data"]
    else:
        items = []
    found: list[KeypadAuth] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = _auth_from_payload(item)
        if parsed is not None:
            found.append(parsed)
    return found


def _auth_from_payload(payload: dict[str, Any]) -> KeypadAuth | None:
    auth_id = payload.get("id")
    if not auth_id:
        return None
    auth_type = payload.get("type")
    try:
        auth_type_int = int(auth_type) if auth_type is not None else None
    except (TypeError, ValueError):
        auth_type_int = None
    code = str(payload.get("code") or "")
    if auth_type_int != AUTH_TYPE_KEYPAD and not is_valid_nuki_pin(code):
        return None
    return KeypadAuth(id=str(auth_id), name=str(payload.get("name") or ""), code=code)


def _smartlock_id_from(payload: dict[str, Any]) -> int | None:
    raw = payload.get("smartlockId")
    if raw is None:
        raw = payload.get("id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class NukiClient:
    """Async Nuki Web API client. The token is never logged."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        *,
        smartlock_id: int | None = None,
    ) -> None:
        """Store the Bearer token and optional lock id."""
        self._session = session
        self._token = token
        self._smartlock_id = smartlock_id

    async def async_list_codes(self) -> list[KeypadAuth]:
        """Keypad authorizations on the configured (or first paired) lock."""
        lock_id = await self.async_smartlock_id()
        payload = await self._request("GET", f"/smartlock/{lock_id}/auth")
        return extract_auths(payload)

    async def async_create_code(
        self,
        *,
        name: str,
        code: str,
        valid_from: datetime,
        valid_until: datetime,
    ) -> KeypadAuth:
        """Create a keypad PIN. The API returns 204; the id is read back."""
        if not is_valid_nuki_pin(code):
            raise NukiError("invalid keypad pin")
        lock_id = await self.async_smartlock_id()
        label = name[:_NAME_MAX]
        await self._request(
            "PUT",
            "/smartlock/auth",
            json={
                "name": label,
                "smartlockIds": [lock_id],
                "type": AUTH_TYPE_KEYPAD,
                "code": int(code),
                "allowedFromDate": nuki_datetime(valid_from),
                "allowedUntilDate": nuki_datetime(valid_until),
                "allowedWeekDays": 127,
                "remoteAllowed": False,
            },
        )
        try:
            auths = await self.async_list_codes()
        except NukiError:
            _LOGGER.warning("Code porte créé, identifiant Nuki non relu")
            return KeypadAuth(id="", name=label, code=code)
        for auth in auths:
            if auth.name == label:
                return KeypadAuth(id=auth.id, name=label, code=code)
        return KeypadAuth(id="", name=label, code=code)

    async def async_delete_code(self, auth_id: str) -> None:
        """Delete one authorization. Missing ids are not an error."""
        if not auth_id:
            return
        try:
            await self._request("DELETE", f"/smartlock/auth/{auth_id}")
        except NukiError as err:
            if "404" in str(err):
                return
            raise

    async def async_smartlock_id(self) -> int:
        """Return the configured lock, or the first lock with a Keypad."""
        if self._smartlock_id:
            return self._smartlock_id
        payload = await self._request("GET", "/smartlock")
        items: list[Any]
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            items = payload["data"]
        else:
            items = []
        paired: list[int] = []
        any_lock: list[int] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            lock_id = _smartlock_id_from(item)
            if lock_id is None:
                continue
            any_lock.append(lock_id)
            config = item.get("config") if isinstance(item.get("config"), dict) else {}
            if config.get("keypadPaired") or config.get("keypad2Paired"):
                paired.append(lock_id)
        chosen = (paired or any_lock or [None])[0]
        if chosen is None:
            raise NukiError("no smartlock")
        self._smartlock_id = chosen
        return chosen

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{NUKI_API}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status in (401, 403):
                    raise NukiAuthError("nuki auth refused")
                if response.status == 404:
                    raise NukiError("nuki 404")
                if response.status >= 400:
                    raise NukiError(f"nuki http {response.status}")
                if response.status in (204, 205):
                    return None
                if response.content_type == "application/json":
                    return await response.json(content_type=None)
                text = await response.text()
                return text or None
        except NukiError:
            raise
        except aiohttp.ClientError as err:
            raise NukiError("nuki unreachable") from err
