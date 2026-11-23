"""cnMaestro Cloud EasyPass vouchers (hotspot codes).

Auth: OAuth2 client credentials against cloud.cambiumnetworks.com.
Vouchers live under an EasyPass portal + voucher plan. Duration and device
limits come from the plan in cnMaestro, not from each generate call.

The client implements the same surface as UniFi for the stay engine:
list / create / delete, returning objects with ``id``, ``code``, ``name``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

_LOGGER = logging.getLogger(__name__)

CLOUD_TOKEN_URL = "https://cloud.cambiumnetworks.com/api/v2/access/token"
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


class CambiumError(Exception):
    """Safe error. Never includes tokens or response bodies in logs by design."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class CambiumAuthError(CambiumError):
    """Client id/secret rejected or token invalid."""


class CambiumNotFound(CambiumError):
    """Portal, plan or voucher missing."""


@dataclass(frozen=True)
class CambiumVoucher:
    """One EasyPass voucher, shaped like UniFi's Voucher for the engine."""

    id: str
    code: str
    name: str
    mac: str = ""


def _as_list(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "vouchers", "voucher", "result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _as_list(value)
            if nested:
                return nested
    return []


def _voucher_from_payload(payload: dict[str, Any], *, fallback_name: str = "") -> CambiumVoucher | None:
    if not isinstance(payload, dict):
        return None
    code = str(
        payload.get("code")
        or payload.get("voucher_code")
        or payload.get("voucherCode")
        or payload.get("passcode")
        or ""
    ).strip()
    voucher_id = str(
        payload.get("id")
        or payload.get("voucher_id")
        or payload.get("voucherId")
        or code
        or ""
    ).strip()
    if not voucher_id and not code:
        return None
    name = str(
        payload.get("name")
        or payload.get("comment")
        or payload.get("note")
        or payload.get("description")
        or fallback_name
        or ""
    ).strip()
    return CambiumVoucher(
        id=voucher_id or code,
        code=code or voucher_id,
        name=name,
    )


def extract_vouchers(payload: Any, *, fallback_name: str = "") -> list[CambiumVoucher]:
    """Parse list/generate responses into CambiumVoucher rows."""
    found: list[CambiumVoucher] = []
    for item in _as_list(payload):
        if not isinstance(item, dict):
            continue
        voucher = _voucher_from_payload(item, fallback_name=fallback_name)
        if voucher is not None:
            found.append(voucher)
    if not found and isinstance(payload, dict):
        single = _voucher_from_payload(payload, fallback_name=fallback_name)
        if single is not None:
            found.append(single)
    return found


class CambiumClient:
    """Async EasyPass voucher client for cnMaestro Cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        client_id: str,
        client_secret: str,
        portal_name: str,
        voucher_plan: str,
        token_url: str = CLOUD_TOKEN_URL,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self.portal_name = portal_name.strip()
        self.voucher_plan = voucher_plan.strip()
        self._token_url = token_url
        self._access_token: str | None = None
        self._base_url: str | None = None

    def _portal_root(self) -> str:
        portal = quote(self.portal_name, safe="")
        plan = quote(self.voucher_plan, safe="")
        return f"/api/v2/easypass/{portal}/voucher_plans/{plan}/vouchers"

    async def async_ensure_token(self) -> str:
        """Fetch or reuse a bearer token. Returns the access token."""
        if self._access_token and self._base_url:
            return self._access_token
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        try:
            async with self._session.post(
                self._token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=_DEFAULT_TIMEOUT,
            ) as response:
                status = response.status
                raw = await response.text()
        except aiohttp.ClientError as err:
            raise CambiumError("cannot_connect") from err
        except TimeoutError as err:
            raise CambiumError("timeout") from err
        if status in {401, 403}:
            raise CambiumAuthError("invalid_auth", status=status)
        if status >= 400:
            raise CambiumError(f"http_{status}", status=status)
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as err:
            raise CambiumError("invalid_json", status=status) from err
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise CambiumAuthError("missing_token", status=status)
        redirect = str(payload.get("redirect_uri") or "").rstrip("/")
        self._access_token = token
        self._base_url = redirect or "https://cloud.cambiumnetworks.com"
        return token

    def _clear_token(self) -> None:
        self._access_token = None
        self._base_url = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        token = await self.async_ensure_token()
        base = self._base_url or "https://cloud.cambiumnetworks.com"
        if not path.startswith("/"):
            path = "/" + path
        url = f"{base}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=_DEFAULT_TIMEOUT,
            ) as response:
                status = response.status
                raw = await response.text()
        except aiohttp.ClientError as err:
            raise CambiumError("cannot_connect") from err
        except TimeoutError as err:
            raise CambiumError("timeout") from err

        if status in {401, 403} and retry_auth:
            self._clear_token()
            return await self._request(
                method,
                path,
                json_body=json_body,
                params=params,
                retry_auth=False,
            )
        if status in {401, 403}:
            raise CambiumAuthError("invalid_auth", status=status)
        if status == 404:
            raise CambiumNotFound("not_found", status=status)
        if status >= 400:
            raise CambiumError(f"http_{status}", status=status)
        if status == 204 or not raw.strip():
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise CambiumError("invalid_json", status=status) from err

    async def async_list_vouchers(self) -> list[CambiumVoucher]:
        """List vouchers for the configured EasyPass plan."""
        body = await self._request("GET", self._portal_root())
        return extract_vouchers(body)

    async def async_create_voucher(
        self,
        *,
        name: str,
        time_limit_minutes: int,
        authorized_guest_limit: int,
        rx_rate_limit_kbps: int,
        tx_rate_limit_kbps: int,
    ) -> CambiumVoucher:
        """Generate one voucher. Plan limits apply; UniFi rate args are ignored."""
        del time_limit_minutes, authorized_guest_limit, rx_rate_limit_kbps, tx_rate_limit_kbps
        # cnMaestro plans own duration/device caps. We still send a stay label
        # when the API accepts comment/name fields (ignored otherwise).
        payload: dict[str, Any] = {
            "count": 1,
            "comment": name,
            "name": name,
            "note": name,
        }
        path = f"{self._portal_root()}/generate"
        try:
            body = await self._request("PUT", path, json_body=payload)
        except CambiumError:
            # Some builds only accept count.
            body = await self._request("PUT", path, json_body={"count": 1})
        vouchers = extract_vouchers(body, fallback_name=name)
        if not vouchers:
            # Generate succeeded but body was empty: list and pick the newest
            # unused label match, else the last voucher.
            listed = await self.async_list_vouchers()
            named = [item for item in listed if item.name == name]
            if named:
                return named[-1]
            if listed:
                chosen = listed[-1]
                return CambiumVoucher(id=chosen.id, code=chosen.code, name=name)
            raise CambiumError("empty_voucher_response")
        created = vouchers[0]
        if not created.name:
            return CambiumVoucher(id=created.id, code=created.code, name=name)
        return created

    async def async_delete_voucher(self, voucher_id: str) -> None:
        """Remove one voucher by id or code. Missing vouchers are fine."""
        if not voucher_id:
            return
        path = f"{self._portal_root()}/remove"
        bodies = (
            {"ids": [voucher_id]},
            {"id": [voucher_id]},
            {"vouchers": [voucher_id]},
            {"codes": [voucher_id]},
            {"voucher_ids": [voucher_id]},
        )
        last_error: CambiumError | None = None
        for body in bodies:
            try:
                await self._request("PUT", path, json_body=body)
                return
            except CambiumNotFound:
                return
            except CambiumError as err:
                last_error = err
                continue
        if last_error is not None and last_error.status not in {400, 404, 422}:
            raise last_error
        _LOGGER.debug("Cambium voucher remove skipped after alternate bodies")
