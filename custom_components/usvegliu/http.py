"""Unauthenticated guest HTTP API and static web app.

The browser only sends the stay token. Home Assistant admin credentials
never leave the server. Entity ids from the client are checked against
the stay allow-list before any service is called.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .guest_session import (
    climate_is_on,
    infer_fan_speed,
    map_fan_modes,
    pick_hvac_on,
)

_LOGGER = logging.getLogger(__name__)
_WWW = Path(__file__).resolve().parent / "www"
_HTTP_FLAG = f"{DOMAIN}_http"
_GUEST_DOMAINS = frozenset({"climate", "lock"})


def async_setup_http(hass: Any) -> None:
    """Register views and static files once per Home Assistant instance."""
    if hass.data.get(_HTTP_FLAG):
        return
    from homeassistant.components.http import StaticPathConfig

    hass.http.register_view(GuestPageView())
    hass.http.register_view(GuestStateView())
    hass.http.register_view(GuestClimateView())
    hass.http.register_view(GuestLockView())
    register = getattr(hass.http, "async_register_static_paths", None)
    if callable(register):
        hass.async_create_task(
            register(
                [StaticPathConfig(f"/{DOMAIN}/static", str(_WWW), False)]
            )
        )
    else:
        hass.http.register_static_path(f"/{DOMAIN}/static", str(_WWW), cache_headers=False)
    hass.data[_HTTP_FLAG] = True


def _runtime(hass: Any) -> Any | None:
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    return runtimes[0] if runtimes else None


def _token_from(request: Any) -> str:
    header = request.headers.get("X-Usvegliu-Token") or ""
    if header:
        return header.strip()
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return str(request.query.get("token") or "").strip()


def _json_error(view: Any, status: int, code: str) -> Any:
    return view.json({"error": code}, status_code=status)


def _area_name(hass: Any, entity_id: str) -> str:
    try:
        from homeassistant.helpers import (
            area_registry as ar,
            device_registry as dr,
            entity_registry as er,
        )

        entity = er.async_get(hass).async_get(entity_id)
        area_id = getattr(entity, "area_id", None) if entity else None
        if not area_id and entity is not None and entity.device_id:
            device = dr.async_get(hass).async_get(entity.device_id)
            area_id = getattr(device, "area_id", None) if device else None
        if area_id:
            area = ar.async_get(hass).async_get_area(area_id)
            if area and area.name:
                return str(area.name)
    except Exception:  # noqa: BLE001
        return "Maison"
    return "Maison"


def _serialize_climate(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    attrs = state.attributes
    fan_modes = [str(mode) for mode in (attrs.get("fan_modes") or [])]
    mapping = map_fan_modes(fan_modes)
    measured = attrs.get("current_temperature")
    setpoint = attrs.get("temperature")
    try:
        measured_f = float(measured) if measured is not None else None
    except (TypeError, ValueError):
        measured_f = None
    try:
        setpoint_f = float(setpoint) if setpoint is not None else None
    except (TypeError, ValueError):
        setpoint_f = None
    return {
        "entity_id": entity_id,
        "name": str(attrs.get("friendly_name") or entity_id),
        "group": _area_name(hass, entity_id),
        "measured": measured_f,
        "setpoint": setpoint_f,
        "on": climate_is_on(str(state.state)),
        "hvac_mode": state.state,
        "fan": infer_fan_speed(attrs.get("fan_mode"), mapping),
        "min": float(attrs.get("min_temp") or 16),
        "max": float(attrs.get("max_temp") or 28),
    }


def _serialize_lock(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    status = str(state.state)
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "locked": status == "locked",
        "state": status,
    }


def _partition(hass: Any, entity_ids: list[str]) -> tuple[list[str], list[str]]:
    climates: list[str] = []
    locks: list[str] = []
    for entity_id in entity_ids:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in _GUEST_DOMAINS:
            continue
        if hass.states.get(entity_id) is None:
            continue
        if domain == "climate":
            climates.append(entity_id)
        else:
            locks.append(entity_id)
    return climates, locks


def _hass(request: Any) -> Any:
    app = request.app
    if "hass" in app:
        return app["hass"]
    try:
        from homeassistant.core import HomeAssistant

        return app[HomeAssistant]
    except Exception:  # noqa: BLE001
        from homeassistant.const import KEY_HASS

        return app[KEY_HASS]


async def _bound(
    request: Any,
) -> tuple[Any, Any, Any] | tuple[None, None, None]:
    hass = _hass(request)
    runtime = _runtime(hass)
    if runtime is None:
        return None, None, None
    record = runtime.guest_record(_token_from(request))
    if record is None:
        return hass, runtime, None
    return hass, runtime, record


class GuestPageView(HomeAssistantView):
    """Serve the web app. The token is validated by the JSON API."""

    requires_auth = False
    cors_allowed = True
    url = f"/{DOMAIN}/s/{{token}}"
    extra_urls = ["/s/{token}"]
    name = f"api:{DOMAIN}:guest_page"

    async def get(self, request: Any, token: str) -> Any:
        from aiohttp import web

        index = _WWW / "index.html"
        if not index.is_file():
            return web.Response(status=404, text="missing")
        return web.FileResponse(index)


class GuestStateView(HomeAssistantView):
    """Stay header plus every allowed climate and lock."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/state"
    name = f"api:{DOMAIN}:guest_state"

    async def get(self, request: Any) -> Any:
        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        if record is None:
            return _json_error(self, 401, "invalid_token")
        allowed = runtime.allowed_entity_ids(record)
        climates, locks = _partition(hass, allowed)
        return self.json(
            {
                "guest": record.get("guest") or "",
                "check_in": record.get("check_in") or "",
                "check_out": record.get("check_out") or "",
                "preview": bool(record.get("preview")),
                "climates": [
                    item
                    for entity_id in climates
                    if (item := _serialize_climate(hass, entity_id))
                ],
                "locks": [
                    item
                    for entity_id in locks
                    if (item := _serialize_lock(hass, entity_id))
                ],
            }
        )


class GuestClimateView(HomeAssistantView):
    """Turn a thermostat on/off, change the setpoint or the fan speed."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/climate"
    name = f"api:{DOMAIN}:guest_climate"

    async def post(self, request: Any) -> Any:
        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        if record is None:
            return _json_error(self, 401, "invalid_token")
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, 400, "bad_json")
        entity_id = str(body.get("entity_id") or "")
        climates, _locks = _partition(hass, runtime.allowed_entity_ids(record))
        if entity_id not in climates:
            return _json_error(self, 403, "forbidden")
        state = hass.states.get(entity_id)
        if state is None:
            return _json_error(self, 404, "missing")
        attrs = state.attributes
        fan_modes = [str(mode) for mode in (attrs.get("fan_modes") or [])]
        mapping = map_fan_modes(fan_modes)
        hvac_modes = [str(mode) for mode in (attrs.get("hvac_modes") or [])]
        try:
            if "on" in body:
                if body["on"]:
                    mode = pick_hvac_on(hvac_modes, str(state.state))
                    await hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": entity_id, "hvac_mode": mode},
                        blocking=True,
                    )
                else:
                    await hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": entity_id, "hvac_mode": "off"},
                        blocking=True,
                    )
            if "setpoint" in body and body["setpoint"] is not None:
                await hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": entity_id,
                        "temperature": float(body["setpoint"]),
                    },
                    blocking=True,
                )
            if "fan" in body and body["fan"] is not None:
                speed = int(body["fan"])
                mode = mapping.get(speed)
                if mode:
                    await hass.services.async_call(
                        "climate",
                        "set_fan_mode",
                        {"entity_id": entity_id, "fan_mode": mode},
                        blocking=True,
                    )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Guest climate command failed")
            return _json_error(self, 502, "command_failed")
        payload = _serialize_climate(hass, entity_id)
        return self.json(payload or {"entity_id": entity_id})


class GuestLockView(HomeAssistantView):
    """Lock or unlock a stay-allowed lock (Nuki)."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/lock"
    name = f"api:{DOMAIN}:guest_lock"

    async def post(self, request: Any) -> Any:
        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        if record is None:
            return _json_error(self, 401, "invalid_token")
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, 400, "bad_json")
        entity_id = str(body.get("entity_id") or "")
        _climates, locks = _partition(hass, runtime.allowed_entity_ids(record))
        if entity_id not in locks:
            return _json_error(self, 403, "forbidden")
        action = str(body.get("action") or "unlock")
        if action not in {"unlock", "lock"}:
            return _json_error(self, 400, "bad_action")
        try:
            await hass.services.async_call(
                "lock",
                action,
                {"entity_id": entity_id},
                blocking=True,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Guest lock command failed")
            return _json_error(self, 502, "command_failed")
        payload = _serialize_lock(hass, entity_id)
        return self.json(payload or {"entity_id": entity_id})
