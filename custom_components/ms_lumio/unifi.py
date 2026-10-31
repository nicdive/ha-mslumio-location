"""Client for the local UniFi Network Integration API.

Verified against the official Network API reference v11.0.97
(https://developer.ui.com/network/v11.0.97/createvouchers):

* header ``X-API-KEY``
* ``POST /v1/sites/{siteId}/hotspot/vouchers``
* body fields ``name``, ``timeLimitMinutes``, ``count``,
  ``authorizedGuestLimit``, ``rxRateLimitKbps``, ``txRateLimitKbps``

On UniFi OS (UDM Pro Max) the application is mounted at
``/proxy/network/integration``. Some references also document ``/integration``.
The client probes both and keeps the first that answers.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import ssl
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import UNIFI_API_HEADER, UNIFI_BASE_CANDIDATES

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


class UnifiError(Exception):
    """Base error. The message never includes the response body or the key."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Store a safe message and the HTTP status when there is one."""
        super().__init__(message)
        self.status = status


class UnifiAuthError(UnifiError):
    """The API key was rejected (HTTP 401 or 403)."""


class UnifiConnectionError(UnifiError):
    """The controller could not be reached, or TLS failed."""


class UnifiNotFound(UnifiError):
    """The resource does not exist."""


@dataclass(frozen=True)
class Voucher:
    """One hotspot voucher returned by the Integration API."""

    id: str
    code: str
    name: str
    time_limit_minutes: int | None = None
    authorized_guest_limit: int | None = None
    rx_rate_limit_kbps: int | None = None
    tx_rate_limit_kbps: int | None = None


@dataclass(frozen=True)
class Site:
    """A site managed by this Network application."""

    id: str
    name: str


def normalize_host(value: str) -> str:
    """Strip a scheme and a path from a controller address."""
    text = value.strip()
    text = re.sub(r"^https?://", "", text, flags=re.IGNORECASE)
    text = text.split("/")[0].strip()
    return text


def split_host_port(value: str, default_port: int) -> tuple[str, int]:
    """Accept ``host``, ``host:port`` or a pasted URL."""
    host = normalize_host(value)
    if host.startswith("["):
        return host, default_port
    if host.count(":") == 1:
        name, port_text = host.rsplit(":", 1)
        if port_text.isdigit():
            return name, int(port_text)
    return host, default_port


def _voucher_from_payload(payload: dict[str, Any]) -> Voucher | None:
    voucher_id = payload.get("id")
    if not voucher_id:
        return None
    return Voucher(
        id=str(voucher_id),
        code=str(payload.get("code") or ""),
        name=str(payload.get("name") or ""),
        time_limit_minutes=_optional_int(payload.get("timeLimitMinutes")),
        authorized_guest_limit=_optional_int(payload.get("authorizedGuestLimit")),
        rx_rate_limit_kbps=_optional_int(payload.get("rxRateLimitKbps")),
        tx_rate_limit_kbps=_optional_int(payload.get("txRateLimitKbps")),
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_vouchers(payload: Any) -> list[Voucher]:
    """Accept the envelopes documented or observed for this endpoint.

    The official create call is described as ``{"vouchers": [...]}``.
    List calls use the standard page envelope ``{"data": [...]}``.
    """
    items: list[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        found: list[Any] | None = None
        for key in ("vouchers", "data", "items"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                found = candidate
                break
        if found is None and "id" in payload:
            found = [payload]
        items = found or []
    else:
        return []
    vouchers: list[Voucher] = []
    for item in items:
        if isinstance(item, dict):
            parsed = _voucher_from_payload(item)
            if parsed is not None:
                vouchers.append(parsed)
    return vouchers


def extract_sites(payload: Any) -> list[Site]:
    """Parse a list-sites response."""
    items: list[Any]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        items = payload["data"]
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    sites: list[Site] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        sites.append(Site(id=str(item["id"]), name=str(item.get("name") or item["id"])))
    return sites


def page_total(payload: Any, fetched: int) -> int:
    """Read totalCount, falling back to the current page size."""
    if isinstance(payload, dict) and payload.get("totalCount") is not None:
        try:
            return int(payload["totalCount"])
        except (TypeError, ValueError):
            return fetched
    return fetched


class UnifiClient:
    """Async client. The API key is sent as a header and never logged."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        host: str,
        port: int,
        api_key: str,
        verify_ssl: bool,
        base_path: str = "",
        site_id: str = "",
        scheme: str = "https",
    ) -> None:
        """Store connection parameters. ``scheme`` is https except in tests."""
        self._session = session
        self.host = host
        self.port = port
        self._api_key = api_key
        self.verify_ssl = verify_ssl
        self.base_path = base_path.rstrip("/")
        self.site_id = site_id
        self.scheme = scheme

    def _ssl(self) -> ssl.SSLContext | bool | None:
        if self.scheme != "https":
            return None
        if self.verify_ssl:
            return None
        return False

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        host = self.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        prefix = self.base_path
        return f"{self.scheme}://{host}:{self.port}{prefix}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        headers = {
            UNIFI_API_HEADER: self._api_key,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with self._session.request(
                method,
                self._url(path),
                headers=headers,
                json=json_body,
                params=params,
                ssl=self._ssl(),
                allow_redirects=False,
                timeout=_DEFAULT_TIMEOUT,
            ) as response:
                status = response.status
                raw = await response.text()
        except aiohttp.ClientSSLError as err:
            raise UnifiConnectionError("tls_error") from err
        except aiohttp.ClientError as err:
            raise UnifiConnectionError("cannot_connect") from err
        except TimeoutError as err:
            raise UnifiConnectionError("timeout") from err

        if status in {301, 302, 303, 307, 308}:
            # Redirects are refused so the API key header cannot leave the host.
            raise UnifiConnectionError("redirect_refused", status=status)
        if status in {401, 403}:
            raise UnifiAuthError("invalid_auth", status=status)
        if status == 404:
            raise UnifiNotFound("not_found", status=status)
        if status >= 400:
            raise UnifiError(f"http_{status}", status=status)

        if status == 204 or not raw.strip():
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise UnifiError("invalid_json", status=status) from err

    async def async_probe_base_path(self) -> str:
        """Find the local integration prefix and remember it."""
        if self.base_path:
            await self._request("GET", "/v1/info")
            return self.base_path
        last_error: UnifiError | None = None
        for candidate in UNIFI_BASE_CANDIDATES:
            self.base_path = candidate
            try:
                await self._request("GET", "/v1/info")
            except UnifiAuthError:
                raise
            except UnifiError as err:
                last_error = err
                self.base_path = ""
                continue
            return candidate
        self.base_path = ""
        raise last_error or UnifiConnectionError("cannot_connect")

    async def async_get_info(self) -> Any:
        """Return application info. Used as a connectivity check."""
        if not self.base_path:
            await self.async_probe_base_path()
        return await self._request("GET", "/v1/info")

    async def async_list_sites(self) -> list[Site]:
        """List sites (paginated)."""
        if not self.base_path:
            await self.async_probe_base_path()
        return [
            Site(id=item.id, name=item.name)
            for item in await self._paginate("/v1/sites", extract_sites)
        ]

    async def async_list_vouchers(self) -> list[Voucher]:
        """List every hotspot voucher of the configured site."""
        path = f"/v1/sites/{quote(self.site_id, safe='')}/hotspot/vouchers"
        return await self._paginate(path, extract_vouchers)

    async def async_create_voucher(
        self,
        *,
        name: str,
        time_limit_minutes: int,
        authorized_guest_limit: int,
        rx_rate_limit_kbps: int,
        tx_rate_limit_kbps: int,
    ) -> Voucher:
        """Create a single multi-use voucher. ``count`` is always 1."""
        path = f"/v1/sites/{quote(self.site_id, safe='')}/hotspot/vouchers"
        payload = {
            "name": name,
            "count": 1,
            "timeLimitMinutes": int(time_limit_minutes),
            "authorizedGuestLimit": int(authorized_guest_limit),
            "rxRateLimitKbps": int(rx_rate_limit_kbps),
            "txRateLimitKbps": int(tx_rate_limit_kbps),
        }
        body = await self._request("POST", path, json_body=payload)
        vouchers = extract_vouchers(body)
        if not vouchers:
            raise UnifiError("empty_voucher_response")
        return vouchers[0]

    async def async_delete_voucher(self, voucher_id: str) -> None:
        """Delete one voucher. HTTP 404 is an idempotent success."""
        path = (
            f"/v1/sites/{quote(self.site_id, safe='')}/hotspot/vouchers/"
            f"{quote(voucher_id, safe='')}"
        )
        try:
            await self._request("DELETE", path)
        except UnifiNotFound:
            return

    async def _paginate(self, path: str, parser: Any) -> list[Any]:
        offset = 0
        limit = 200
        collected: list[Any] = []
        while offset <= 2000:
            payload = await self._request(
                "GET",
                path,
                params={"offset": offset, "limit": limit},
            )
            page = parser(payload)
            collected.extend(page)
            total = page_total(payload, offset + len(page))
            offset += len(page)
            if not page or offset >= total:
                break
        return collected
