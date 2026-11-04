"""Unauthenticated guest HTTP API and static web app.

The browser only sends the stay token. Home Assistant admin credentials
never leave the server. Entity ids from the client are checked against
the stay allow-list before any service is called.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .guest_session import (
    GUEST_KIND_ALARM,
    GUEST_KIND_CLIMATE,
    GUEST_KIND_GARAGE,
    GUEST_KIND_GATE,
    GUEST_KIND_LIGHT,
    GUEST_KIND_LOCK,
    GUEST_KIND_OUTDOOR,
    GUEST_KIND_POOL_PH,
    GUEST_KIND_POOL_TEMP,
    GUEST_KIND_SCENE,
    GUEST_KIND_SHUTTER,
    alarm_view_state,
    classify_guest_entity,
    climate_activity,
    climate_is_on,
    cover_is_moving,
    cover_is_open,
    house_mode_label,
    infer_fan_speed,
    map_fan_modes,
    pick_hvac_on,
    resolve_house_mode,
)

_LOGGER = logging.getLogger(__name__)
_WWW = Path(__file__).resolve().parent / "www"
_HTTP_FLAG = f"{DOMAIN}_http"
_GUEST_DOMAINS = frozenset(
    {
        "climate",
        "lock",
        "alarm_control_panel",
        "light",
        "scene",
        "script",
        "cover",
        "switch",
        "sensor",
        "weather",
    }
)
_COMMAND_KINDS = frozenset(
    {
        GUEST_KIND_LOCK,
        GUEST_KIND_ALARM,
        GUEST_KIND_LIGHT,
        GUEST_KIND_SCENE,
        GUEST_KIND_GARAGE,
        GUEST_KIND_GATE,
        GUEST_KIND_SHUTTER,
    }
)


def async_setup_http(hass: Any) -> None:
    """Register views and static files once per Home Assistant instance."""
    if hass.data.get(_HTTP_FLAG):
        return
    from homeassistant.components.http import StaticPathConfig

    hass.http.register_view(GuestPageView())
    hass.http.register_view(GuestStateView())
    hass.http.register_view(GuestStreamView())
    hass.http.register_view(GuestClimateView())
    hass.http.register_view(GuestLockView())
    hass.http.register_view(GuestCommandView())
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


def _serialize_climate(
    hass: Any, entity_id: str, *, house_mode: str
) -> dict[str, Any] | None:
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
    on = climate_is_on(str(state.state))
    return {
        "entity_id": entity_id,
        "name": str(attrs.get("friendly_name") or entity_id),
        "group": _area_name(hass, entity_id),
        "measured": measured_f,
        "setpoint": setpoint_f,
        "on": on,
        "hvac_mode": state.state,
        "activity": climate_activity(
            on=on,
            house_mode=house_mode,
            measured=measured_f,
            setpoint=setpoint_f,
        ),
        "fan": infer_fan_speed(attrs.get("fan_mode"), mapping),
        "min": float(attrs.get("min_temp") or 16),
        "max": float(attrs.get("max_temp") or 28),
    }


def _switch_state(hass: Any, runtime: Any) -> str | None:
    entity_id = runtime.house_mode_entity_id()
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return str(state.state)


def _house_mode(hass: Any, runtime: Any, climates: list[str]) -> str:
    climate_modes = []
    for entity_id in climates:
        state = hass.states.get(entity_id)
        if state is not None:
            climate_modes.append(str(state.state))
    return resolve_house_mode(_switch_state(hass, runtime), climate_modes)


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _entity_kind(hass: Any, entity_id: str) -> str | None:
    state = hass.states.get(entity_id)
    if state is None:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in _GUEST_DOMAINS:
            return None
        return classify_guest_entity(entity_id)
    attrs = state.attributes
    return classify_guest_entity(
        entity_id,
        device_class=attrs.get("device_class"),
        name=str(attrs.get("friendly_name") or entity_id),
        unit=attrs.get("unit_of_measurement"),
    )


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


def _serialize_light(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    brightness = _as_float(state.attributes.get("brightness"))
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "group": _area_name(hass, entity_id),
        "on": str(state.state).casefold() == "on",
        "brightness": None if brightness is None else int(brightness),
    }


def _serialize_scene(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
    }


def _serialize_cover(hass: Any, entity_id: str, kind: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    status = str(state.state)
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "kind": kind,
        "open": cover_is_open(status),
        "moving": cover_is_moving(status),
        "state": status,
    }


def _serialize_alarm(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    raw = str(state.state)
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "state": alarm_view_state(raw),
        "raw": raw,
    }


def _serialize_metric(
    hass: Any, entity_id: str, kind: str, label: str
) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    value: Any = state.state
    unit = str(state.attributes.get("unit_of_measurement") or "")
    domain = entity_id.split(".", 1)[0]
    if domain == "weather" or state.attributes.get("temperature") is not None and kind == GUEST_KIND_OUTDOOR:
        value = state.attributes.get("temperature", value)
        unit = str(state.attributes.get("temperature_unit") or unit or "°C")
    number = _as_float(value)
    if number is None:
        return None
    pretty_unit = "°" if "°" in unit or unit.casefold() in {"c", "f", "celsius"} else unit
    if kind == GUEST_KIND_POOL_PH:
        pretty_unit = ""
    return {
        "entity_id": entity_id,
        "kind": kind,
        "label": label,
        "value": number,
        "unit": pretty_unit,
    }


def _group_entities(hass: Any, entity_ids: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for entity_id in entity_ids:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in _GUEST_DOMAINS:
            continue
        if hass.states.get(entity_id) is None:
            continue
        kind = _entity_kind(hass, entity_id)
        if not kind:
            continue
        grouped.setdefault(kind, []).append(entity_id)
    return grouped


def _ids(grouped: dict[str, list[str]], kind: str) -> list[str]:
    return list(grouped.get(kind) or [])


def _snapshot(hass: Any, runtime: Any, record: dict[str, Any]) -> dict[str, Any]:
    """Stay header plus every allowed guest-facing entity."""
    allowed = runtime.allowed_entity_ids(record)
    grouped = _group_entities(hass, allowed)
    climates = _ids(grouped, GUEST_KIND_CLIMATE)
    house_mode = _house_mode(hass, runtime, climates)
    telemetry = runtime.telemetry_entity_ids()
    metrics: list[dict[str, Any]] = []
    outdoor_id = telemetry.get("outdoor") or next(iter(_ids(grouped, GUEST_KIND_OUTDOOR)), None)
    pool_id = telemetry.get("pool_temp") or next(
        iter(_ids(grouped, GUEST_KIND_POOL_TEMP)), None
    )
    ph_id = telemetry.get("pool_ph") or next(iter(_ids(grouped, GUEST_KIND_POOL_PH)), None)
    for entity_id, kind, label in (
        (outdoor_id, GUEST_KIND_OUTDOOR, "Extérieur"),
        (pool_id, GUEST_KIND_POOL_TEMP, "Piscine"),
        (ph_id, GUEST_KIND_POOL_PH, "pH"),
    ):
        if not entity_id:
            continue
        item = _serialize_metric(hass, entity_id, kind, label)
        if item:
            metrics.append(item)
    return {
        "guest": record.get("guest") or "",
        "check_in": record.get("check_in") or "",
        "check_out": record.get("check_out") or "",
        "preview": bool(record.get("preview")),
        "mode": house_mode,
        "mode_label": house_mode_label(house_mode),
        "metrics": metrics,
        "climates": [
            item
            for entity_id in climates
            if (item := _serialize_climate(hass, entity_id, house_mode=house_mode))
        ],
        "lights": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_LIGHT)
            if (item := _serialize_light(hass, entity_id))
        ],
        "scenes": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_SCENE)
            if (item := _serialize_scene(hass, entity_id))
        ],
        "locks": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_LOCK)
            if (item := _serialize_lock(hass, entity_id))
        ],
        "garages": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_GARAGE)
            if (item := _serialize_cover(hass, entity_id, GUEST_KIND_GARAGE))
        ],
        "gates": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_GATE)
            if (item := _serialize_cover(hass, entity_id, GUEST_KIND_GATE))
        ],
        "shutters": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_SHUTTER)
            if (item := _serialize_cover(hass, entity_id, GUEST_KIND_SHUTTER))
        ],
        "alarms": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_ALARM)
            if (item := _serialize_alarm(hass, entity_id))
        ],
    }


def _partition(hass: Any, entity_ids: list[str]) -> tuple[list[str], list[str]]:
    """Climate and lock ids. Kept for the original guest endpoints."""
    grouped = _group_entities(hass, entity_ids)
    return _ids(grouped, GUEST_KIND_CLIMATE), _ids(grouped, GUEST_KIND_LOCK)


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
        return self.json(_snapshot(hass, runtime, record))


class GuestStreamView(HomeAssistantView):
    """Push climate and lock state as soon as Home Assistant changes."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/stream"
    name = f"api:{DOMAIN}:guest_stream"

    async def get(self, request: Any) -> Any:
        from aiohttp import web

        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        if record is None:
            return _json_error(self, 401, "invalid_token")

        token = _token_from(request)
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream; charset=utf-8",
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=4)

        def notify(kind: str) -> None:
            try:
                queue.put_nowait(kind)
            except asyncio.QueueFull:
                pass

        def listener(event: Any) -> None:
            current = runtime.guest_record(token)
            if current is None:
                notify("expired")
                return
            entity_id = (event.data or {}).get("entity_id")
            if entity_id and entity_id in runtime.guest_watch_ids(current):
                notify("state")

        unsub = hass.bus.async_listen("state_changed", listener)

        async def emit(name: str, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            await response.write(f"event: {name}\ndata: {body}\n\n".encode())

        try:
            await emit("state", _snapshot(hass, runtime, record))
            while True:
                try:
                    kind = await asyncio.wait_for(queue.get(), timeout=20)
                    while not queue.empty():
                        kind = queue.get_nowait()
                except asyncio.TimeoutError:
                    current = runtime.guest_record(token)
                    if current is None:
                        await emit("expired", {"error": "invalid_token"})
                        break
                    await response.write(b": ping\n\n")
                    continue
                current = runtime.guest_record(token)
                if current is None or kind == "expired":
                    await emit("expired", {"error": "invalid_token"})
                    break
                await emit("state", _snapshot(hass, runtime, current))
        except (ConnectionResetError, asyncio.CancelledError, BrokenPipeError):
            pass
        finally:
            unsub()
        return response


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
        house_mode = _house_mode(hass, runtime, climates)
        try:
            if "on" in body:
                if body["on"]:
                    mode = pick_hvac_on(hvac_modes, house_mode)
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
        payload = _serialize_climate(hass, entity_id, house_mode=house_mode)
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


class GuestCommandView(HomeAssistantView):
    """Lights, scenes, covers, garage, gate, alarm — stay allow-list only."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/command"
    name = f"api:{DOMAIN}:guest_command"

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
        action = str(body.get("action") or "")
        allowed = runtime.allowed_entity_ids(record)
        if entity_id not in allowed:
            return _json_error(self, 403, "forbidden")
        kind = _entity_kind(hass, entity_id)
        if kind not in _COMMAND_KINDS:
            return _json_error(self, 403, "forbidden")
        try:
            await _async_guest_command(hass, runtime, entity_id, kind, action)
        except ValueError:
            return _json_error(self, 400, "bad_action")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Guest command failed")
            return _json_error(self, 502, "command_failed")
        return self.json(_serialize_command_result(hass, entity_id, kind) or {"entity_id": entity_id})


async def _async_guest_command(
    hass: Any, runtime: Any, entity_id: str, kind: str, action: str
) -> None:
    domain = entity_id.split(".", 1)[0]
    data: dict[str, Any] = {"entity_id": entity_id}
    if kind == GUEST_KIND_LIGHT:
        if action not in {"on", "off", "toggle"}:
            raise ValueError("bad_action")
        service = {"on": "turn_on", "off": "turn_off", "toggle": "toggle"}[action]
        await hass.services.async_call(domain, service, data, blocking=True)
        return
    if kind == GUEST_KIND_SCENE:
        if action != "activate":
            raise ValueError("bad_action")
        await hass.services.async_call(domain, "turn_on", data, blocking=True)
        return
    if kind in {GUEST_KIND_GARAGE, GUEST_KIND_GATE, GUEST_KIND_SHUTTER}:
        if domain == "switch":
            if action not in {"open", "close", "toggle"}:
                raise ValueError("bad_action")
            service = {"open": "turn_on", "close": "turn_off", "toggle": "toggle"}[action]
            await hass.services.async_call("switch", service, data, blocking=True)
            return
        if action not in {"open", "close", "stop"}:
            raise ValueError("bad_action")
        service = {
            "open": "open_cover",
            "close": "close_cover",
            "stop": "stop_cover",
        }[action]
        await hass.services.async_call("cover", service, data, blocking=True)
        return
    if kind == GUEST_KIND_LOCK:
        if action not in {"lock", "unlock"}:
            raise ValueError("bad_action")
        await hass.services.async_call("lock", action, data, blocking=True)
        return
    if kind == GUEST_KIND_ALARM:
        if action not in {"arm", "disarm"}:
            raise ValueError("bad_action")
        service = "alarm_arm_away" if action == "arm" else "alarm_disarm"
        code = runtime.alarm_code()
        if code:
            data["code"] = code
        await hass.services.async_call("alarm_control_panel", service, data, blocking=True)
        return
    raise ValueError("bad_action")


def _serialize_command_result(hass: Any, entity_id: str, kind: str) -> dict[str, Any] | None:
    if kind == GUEST_KIND_LIGHT:
        return _serialize_light(hass, entity_id)
    if kind == GUEST_KIND_SCENE:
        return _serialize_scene(hass, entity_id)
    if kind in {GUEST_KIND_GARAGE, GUEST_KIND_GATE, GUEST_KIND_SHUTTER}:
        return _serialize_cover(hass, entity_id, kind)
    if kind == GUEST_KIND_LOCK:
        return _serialize_lock(hass, entity_id)
    if kind == GUEST_KIND_ALARM:
        return _serialize_alarm(hass, entity_id)
    return {"entity_id": entity_id}
