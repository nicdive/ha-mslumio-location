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

from .branding import brand_climate_fans, brand_heat_only
from .const import DOMAIN, EVENT_DEMO
from .demo import (
    apply_demo_climate,
    apply_demo_command,
    demo_entity_kind,
    is_demo_entity,
    overlay_demo_snapshot,
)
from .guest_session import (
    HOUSE_HEAT,
    format_arrival_day,
    ip_is_lan,
    stay_activation_start,
    stay_is_active,
    GUEST_KIND_ALARM,
    GUEST_KIND_CAMERA,
    GUEST_KIND_CHARGER,
    GUEST_KIND_CLIMATE,
    GUEST_KIND_DOORBELL,
    GUEST_KIND_GARAGE,
    GUEST_KIND_GATE,
    GUEST_KIND_LIGHT,
    GUEST_KIND_LOCK,
    GUEST_KIND_OUTDOOR,
    GUEST_KIND_POOL_LIGHT,
    GUEST_KIND_POOL_PH,
    GUEST_KIND_POOL_TEMP,
    GUEST_KIND_SCENE,
    GUEST_KIND_SHUTTER,
    GUEST_KIND_SPEAKER,
    alarm_view_state,
    charger_charge_level,
    charger_view_state,
    classify_guest_entity,
    combine_charger_views,
    climate_activity,
    climate_is_on,
    climate_power_via,
    cover_is_moving,
    cover_is_open,
    doorbell_is_ringing,
    guest_alarm_service,
    speaker_view_state,
    house_mode_label,
    TYDOM_DOMAIN,
    TYDOM_SET_MODE,
    infer_fan_speed,
    map_fan_modes,
    pick_hvac_on,
    pick_preset_off,
    pick_preset_on,
    resolve_house_mode,
)
from .qr import guest_share_url, make_share_qr_svg

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
        "binary_sensor",
        "event",
        "camera",
        "weather",
        "media_player",
    }
)
_COMMAND_KINDS = frozenset(
    {
        GUEST_KIND_LOCK,
        GUEST_KIND_ALARM,
        GUEST_KIND_LIGHT,
        GUEST_KIND_POOL_LIGHT,
        GUEST_KIND_SCENE,
        GUEST_KIND_GARAGE,
        GUEST_KIND_GATE,
        GUEST_KIND_SHUTTER,
        GUEST_KIND_SPEAKER,
    }
)


def async_setup_http(hass: Any) -> None:
    """Register views and static files once per Home Assistant instance."""
    if hass.data.get(_HTTP_FLAG):
        return
    from homeassistant.components.http import StaticPathConfig

    hass.http.register_view(GuestPageView())
    hass.http.register_view(HousePageView())
    hass.http.register_view(GuestServiceWorkerView())
    hass.http.register_view(GuestManifestView())
    hass.http.register_view(GuestStateView())
    hass.http.register_view(GuestStreamView())
    hass.http.register_view(GuestClimateView())
    hass.http.register_view(GuestLockView())
    hass.http.register_view(GuestCommandView())
    hass.http.register_view(GuestSnapshotView())
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


def _json_error(view: Any, status: int, code: str, **extra: Any) -> Any:
    payload = {"error": code, **extra}
    return view.json(payload, status_code=status)


def _guest_not_ready(view: Any, record: dict[str, Any] | None) -> Any | None:
    """401 if the token is unknown or the stay is over, 403 until arrival."""
    if record is None:
        return _json_error(view, 401, "invalid_token")
    if record.get("house"):
        return None
    from homeassistant.util import dt as dt_util

    now = dt_util.now()
    if stay_is_active(record, now):
        return None
    begin = stay_activation_start(record, now)
    if begin is not None and now < begin:
        opens = format_arrival_day(str(record.get("check_in") or ""))
        return _json_error(
            view,
            403,
            "too_early",
            check_in=record.get("check_in") or "",
            opens_on=opens,
        )
    return _json_error(view, 401, "invalid_token")


def _request_host(request: Any) -> str:
    return str(getattr(request, "host", None) or request.headers.get("Host") or "")


def _client_ip(request: Any) -> str:
    """Best-effort client IP (peer, then first X-Forwarded-For hop)."""
    peer = str(getattr(request, "remote", None) or "").strip()
    forwarded = str(request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first and (not peer or ip_is_lan(peer)):
            return first
    return peer


def _public_hostnames(runtime: Any) -> set[str]:
    """Hosts that must not serve the house-tablet token."""
    hosts: set[str] = set()
    from urllib.parse import urlparse

    from .const import CONF_GUEST_BASE_URL

    candidates = [
        str(runtime.entry.options.get(CONF_GUEST_BASE_URL) or ""),
        str(getattr(runtime.hass.config, "external_url", None) or ""),
    ]
    for raw in candidates:
        text = raw.strip()
        if not text:
            continue
        if "://" not in text:
            text = f"https://{text}"
        host = (urlparse(text).hostname or "").casefold()
        if host:
            hosts.add(host)
    return hosts


def house_lan_allowed(request: Any, runtime: Any) -> bool:
    """Tablets: LAN / private IP only — block public Host and WAN clients."""
    host = _request_host(request).split(":")[0].casefold()
    if host and host in _public_hostnames(runtime):
        return False
    return ip_is_lan(_client_ip(request))


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
    hass: Any,
    entity_id: str,
    *,
    house_mode: str,
    allow_fans: bool = True,
) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    attrs = state.attributes
    fan_modes = [str(mode) for mode in (attrs.get("fan_modes") or [])]
    mapping = map_fan_modes(fan_modes)
    supports_fan = bool(allow_fans and mapping)
    hvac_modes = [str(mode) for mode in (attrs.get("hvac_modes") or [])]
    preset_modes = [str(mode) for mode in (attrs.get("preset_modes") or [])]
    preset = attrs.get("preset_mode")
    preset_s = str(preset).strip() if preset is not None else ""
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
    on = climate_is_on(str(state.state), preset_s or None)
    power_via = climate_power_via(hvac_modes, preset_modes)
    return {
        "entity_id": entity_id,
        "name": str(attrs.get("friendly_name") or entity_id),
        "group": _area_name(hass, entity_id),
        "measured": measured_f,
        "setpoint": setpoint_f,
        "on": on,
        "hvac_mode": state.state,
        "preset_mode": preset_s or None,
        "power_via": power_via,
        "activity": climate_activity(
            on=on,
            house_mode=house_mode,
            measured=measured_f,
            setpoint=setpoint_f,
        ),
        "supports_fan": supports_fan,
        "fan": infer_fan_speed(attrs.get("fan_mode"), mapping) if supports_fan else None,
        "min": float(attrs.get("min_temp") or 16),
        "max": float(attrs.get("max_temp") or 28),
    }


def _theme_climate_snapshot(payload: dict[str, Any], brand: dict[str, Any]) -> dict[str, Any]:
    """Ledbury = UFH/radiators: heat-only, no soufflante controls."""
    out = dict(payload)
    fans = brand_climate_fans(brand)
    heat_only = brand_heat_only(brand)
    if heat_only:
        out["mode"] = HOUSE_HEAT
        out["mode_label"] = house_mode_label(HOUSE_HEAT)
    climates: list[dict[str, Any]] = []
    for room in out.get("climates") or []:
        item = dict(room)
        if not fans:
            item["supports_fan"] = False
            item["fan"] = None
        else:
            item["supports_fan"] = bool(item.get("supports_fan", True))
        climates.append(item)
    out["climates"] = climates
    brand_out = dict(out.get("brand") or {})
    brand_out["climate_fans"] = "1" if fans else "0"
    brand_out["climate_heat_only"] = "1" if heat_only else "0"
    out["brand"] = brand_out
    return out


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


def _serialize_charger(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    raw = str(state.state)
    unit = str(state.attributes.get("unit_of_measurement") or "")
    level = charger_charge_level(raw, unit=unit, attributes=state.attributes)
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "state": charger_view_state(raw, unit=unit, level=level),
        "level": level,
        "raw": raw,
    }


def _serialize_camera(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
    }


def _serialize_speaker(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    volume = _as_float(state.attributes.get("volume_level"))
    muted = bool(state.attributes.get("is_volume_muted"))
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "state": speaker_view_state(str(state.state)),
        "volume": 0 if volume is None else int(round(max(0.0, min(1.0, volume)) * 100)),
        "muted": muted,
    }


def _serialize_doorbell(hass: Any, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    raw = str(state.state)
    ringing = doorbell_is_ringing(raw)
    return {
        "entity_id": entity_id,
        "name": str(state.attributes.get("friendly_name") or entity_id),
        "ringing": ringing,
        "state": "ringing" if ringing else "idle",
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


def _guest_share_url(request: Any | None, record: dict[str, Any]) -> str:
    """Absolute Maison URL for the host that served this request."""
    token = str(record.get("guest_token") or "")
    if request is None:
        return guest_share_url(token)
    headers = getattr(request, "headers", None) or {}
    proto = headers.get("X-Forwarded-Proto") if hasattr(headers, "get") else None
    host = headers.get("X-Forwarded-Host") if hasattr(headers, "get") else None
    return guest_share_url(
        token,
        proto or getattr(request, "scheme", None),
        host or getattr(request, "host", None),
    )


def _snapshot(
    hass: Any,
    runtime: Any,
    record: dict[str, Any],
    request: Any | None = None,
) -> dict[str, Any]:
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
    revoked = bool(record.get("voucher_revoked"))
    voucher = "" if revoked else str(record.get("voucher_code") or "")
    if not voucher and not revoked:
        voucher = str(runtime.manual_wifi_code() or "")
    nuki_revoked = bool(record.get("nuki_revoked"))
    nuki_code = "" if nuki_revoked else str(record.get("nuki_code") or "")
    share = None if record.get("house") else _guest_share_url(request, record)
    brand = runtime.guest_brand()
    allow_fans = brand_climate_fans(brand)
    if brand_heat_only(brand):
        house_mode = HOUSE_HEAT
    payload = {
        "guest": record.get("guest") or "",
        "check_in": record.get("check_in") or "",
        "check_out": record.get("check_out") or "",
        "preview": bool(record.get("preview")),
        "house": bool(record.get("house")),
        "brand": {
            "id": brand["id"],
            "name": brand["name"],
            "tagline": brand["tagline"],
            "place": brand["place"],
            "logo": brand["logo"],
            "banner": brand["banner"],
            "theme_color": brand["theme_color"],
            "locale": brand.get("locale", "fr"),
            "climate_fans": brand.get("climate_fans", "1"),
            "climate_heat_only": brand.get("climate_heat_only", "0"),
        },
        "informations": {
            "wifi_ssid": runtime.wifi_ssid(),
            "voucher_code": voucher or None,
            "voucher_revoked": revoked,
            "nuki_code": nuki_code or None,
            "nuki_revoked": nuki_revoked,
            "lien_maison": share or None,
            "qr_svg": make_share_qr_svg(share) if share else None,
        },
        "mode": house_mode,
        "mode_label": house_mode_label(house_mode),
        "metrics": metrics,
        "weather": runtime.weather(),
        "climates": [
            item
            for entity_id in climates
            if (
                item := _serialize_climate(
                    hass,
                    entity_id,
                    house_mode=house_mode,
                    allow_fans=allow_fans,
                )
            )
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
        "pool_lights": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_POOL_LIGHT)
            if (item := _serialize_light(hass, entity_id))
        ],
        "chargers": combine_charger_views(
            [
                item
                for entity_id in _ids(grouped, GUEST_KIND_CHARGER)
                if (item := _serialize_charger(hass, entity_id))
            ]
        ),
        "doorbells": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_DOORBELL)
            if (item := _serialize_doorbell(hass, entity_id))
        ],
        "cameras": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_CAMERA)
            if (item := _serialize_camera(hass, entity_id))
        ],
        "speakers": [
            item
            for entity_id in _ids(grouped, GUEST_KIND_SPEAKER)
            if (item := _serialize_speaker(hass, entity_id))
        ],
    }
    villa = runtime.demo_villa() if runtime.demo_mode() else None
    if villa:
        demo_mode = HOUSE_HEAT if brand_heat_only(brand) else house_mode
        payload = overlay_demo_snapshot(payload, villa, house_mode=demo_mode)
    return _theme_climate_snapshot(payload, brand)


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
    token = _token_from(request)
    if runtime.is_house_token(token):
        if not house_lan_allowed(request, runtime):
            return hass, runtime, {"house": True, "lan_denied": True}
        return hass, runtime, runtime.house_session_record()
    record = runtime.guest_record(token, require_active=False)
    if record is None:
        return hass, runtime, None
    return hass, runtime, record


def _lan_denied(view: Any, record: dict[str, Any] | None) -> Any | None:
    if record and record.get("lan_denied"):
        return _json_error(view, 403, "lan_only")
    return None


def _package_version() -> str:
    """Integration version for Maison asset cache-busting."""
    try:
        data = json.loads(
            (_WWW.parent / "manifest.json").read_text(encoding="utf-8")
        )
        return str(data.get("version") or "0")
    except (OSError, ValueError, TypeError):
        return "0"


class GuestPageView(HomeAssistantView):
    """Serve the web app. The token is validated by the JSON API."""

    requires_auth = False
    cors_allowed = True
    url = f"/{DOMAIN}/s/{{token}}"
    extra_urls = ["/s/{token}"]
    name = f"api:{DOMAIN}:guest_page"

    async def get(self, request: Any, token: str) -> Any:
        from aiohttp import web

        from .branding import brand_from_options, guest_brand

        index = _WWW / "index.html"
        if not index.is_file():
            return web.Response(status=404, text="missing")
        html = index.read_text(encoding="utf-8")
        ver = _package_version()
        html = html.replace("/usvegliu/static/app.css", f"/usvegliu/static/app.css?v={ver}")
        html = html.replace("/usvegliu/static/app.js", f"/usvegliu/static/app.js?v={ver}")
        # First paint must already have the stay URL + villa name, otherwise
        # “Add to Home Screen” installs the static Maison manifest (403, wrong title).
        runtime = _runtime(request.app["hass"])
        brand = (
            brand_from_options(runtime.entry.options)
            if runtime is not None
            else guest_brand()
        )
        brand_name = str(brand.get("name") or "Maison")
        brand_id = str(brand.get("id") or "usvegliu")
        brand_logo = str(brand.get("logo") or f"/{DOMAIN}/static/logo.png")
        brand_color = str(brand.get("theme_color") or "#F1EBE2")
        if brand.get("id") == "ledbury":
            touch_icon = f"/{DOMAIN}/static/logo-ledbury-180.png"
        else:
            touch_icon = brand_logo
        start_path = str(request.path or "").strip() or f"/{DOMAIN}/s/{token}"
        from urllib.parse import quote

        manifest_qs = (
            f"token={quote(token, safe='')}"
            f"&start={quote(start_path, safe='')}"
            f"&v={quote(ver, safe='')}"
        )
        # Seed the client brand before app.js runs — otherwise the first render
        # falls back to Usvegliu and macOS/Safari grabs the wrong dock icon.
        brand_boot = {
            "id": brand_id,
            "name": brand_name,
            "tagline": str(brand.get("tagline") or ""),
            "place": str(brand.get("place") or ""),
            "logo": brand_logo,
            "banner": str(brand.get("banner") or brand_logo),
            "theme_color": brand_color,
            "locale": str(brand.get("locale") or "fr"),
            "climate_fans": str(brand.get("climate_fans") or "1"),
            "climate_heat_only": str(brand.get("climate_heat_only") or "0"),
        }
        html = html.replace(
            "window.__USVEGLIU_BRAND__ = window.__USVEGLIU_BRAND__ || null;",
            f"window.__USVEGLIU_BRAND__ = {json.dumps(brand_boot, ensure_ascii=False)};",
        )
        html = html.replace(
            '<html lang="fr">',
            f'<html lang="fr" data-theme="{brand_id}">',
        )
        html = html.replace("<body>", f'<body data-theme="{brand_id}">')
        html = html.replace(
            'href="/usvegliu/static/manifest.webmanifest"',
            f'href="/{DOMAIN}/manifest.webmanifest?{manifest_qs}"',
        )
        html = html.replace(
            'content="Maison"',
            f'content="{brand_name}"',
        )
        html = html.replace("<title>Maison</title>", f"<title>{brand_name}</title>")
        html = html.replace('content="#F1EBE2"', f'content="{brand_color}"')
        html = html.replace(
            '<link rel="icon" href="/usvegliu/static/logo.png" type="image/png" />',
            f'<link rel="icon" href="{brand_logo}?v={ver}" type="image/png" />',
        )
        html = html.replace(
            '<link rel="apple-touch-icon" href="/usvegliu/static/logo.png" />',
            f'<link rel="apple-touch-icon" sizes="180x180" href="{touch_icon}?v={ver}" />',
        )
        return web.Response(
            text=html,
            content_type="text/html",
            charset="utf-8",
            headers={"Cache-Control": "no-cache"},
        )


class HousePageView(GuestPageView):
    """Always-on wall tablets — same app, stable token, LAN only."""

    url = f"/{DOMAIN}/house/{{token}}"
    extra_urls = ["/house/{token}"]
    name = f"api:{DOMAIN}:house_page"

    async def get(self, request: Any, token: str) -> Any:
        from aiohttp import web

        runtime = _runtime(request.app["hass"])
        if runtime is None or not runtime.is_house_token(token):
            return web.Response(status=404, text="missing")
        if not house_lan_allowed(request, runtime):
            return web.Response(
                status=403,
                text="Tablettes: réseau local uniquement",
                content_type="text/plain; charset=utf-8",
            )
        return await GuestPageView.get(self, request, token)


class GuestServiceWorkerView(HomeAssistantView):
    """Service worker at /usvegliu/sw.js with site-wide scope for PWA install."""

    requires_auth = False
    cors_allowed = True
    url = f"/{DOMAIN}/sw.js"
    name = f"api:{DOMAIN}:guest_sw"

    async def get(self, request: Any) -> Any:
        from aiohttp import web

        path = _WWW / "sw.js"
        if not path.is_file():
            return web.Response(status=404, text="missing")
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "application/javascript; charset=utf-8",
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )


class GuestManifestView(HomeAssistantView):
    """HTTPS web app manifest — blob: URLs block Chrome's install prompt."""

    requires_auth = False
    cors_allowed = True
    url = f"/{DOMAIN}/manifest.webmanifest"
    name = f"api:{DOMAIN}:guest_manifest"

    async def get(self, request: Any) -> Any:
        from aiohttp import web

        from .branding import (
            brand_from_options,
            guest_brand,
            pwa_short_name,
            safe_manifest_start,
        )

        hass = request.app["hass"]
        runtime = _runtime(hass)
        brand = (
            brand_from_options(runtime.entry.options)
            if runtime is not None
            else guest_brand()
        )
        token = str(request.query.get("token") or "").strip()
        start = safe_manifest_start(
            str(request.query.get("start") or "").strip(),
            token=token,
        )
        scope = f"/{DOMAIN}/" if start.startswith(f"/{DOMAIN}/") else "/"
        logo = str(brand.get("logo") or f"/{DOMAIN}/static/logo.png")
        if brand.get("id") == "ledbury":
            icon_base = f"/{DOMAIN}/static/logo-ledbury"
        else:
            icon_base = f"/{DOMAIN}/static/logo"
        theme = str(brand.get("theme_color") or "#F1EBE2")
        app_name = str(brand.get("name") or "Maison")
        short = pwa_short_name(brand)
        ver = _package_version()
        bust = f"?v={ver}"
        payload = {
            "id": start,
            "name": app_name,
            "short_name": short,
            "description": brand.get("tagline") or app_name,
            "start_url": start,
            "scope": scope,
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": theme,
            "theme_color": theme,
            "lang": brand.get("locale") or "fr",
            "icons": [
                {
                    "src": f"{icon_base}-192.png{bust}",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": f"{icon_base}-512.png{bust}",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": f"{icon_base}-512.png{bust}",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
                {
                    "src": f"{logo}{bust}",
                    "sizes": "256x256",
                    "type": "image/png",
                    "purpose": "any",
                },
            ],
        }
        return web.Response(
            text=json.dumps(payload, ensure_ascii=False),
            content_type="application/manifest+json",
            charset="utf-8",
            headers={"Cache-Control": "no-cache"},
        )


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
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied
        await runtime.async_ensure_weather()
        return self.json(_snapshot(hass, runtime, record, request))


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
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied

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
            current = runtime.session_for_token(token, require_active=False)
            if current is None:
                notify("expired")
                return
            entity_id = (event.data or {}).get("entity_id")
            if entity_id and entity_id in runtime.guest_watch_ids(current):
                notify("state")

        unsub = hass.bus.async_listen("state_changed", listener)
        unsub_demo = hass.bus.async_listen(EVENT_DEMO, lambda _event: notify("state"))

        async def emit(name: str, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            await response.write(f"event: {name}\ndata: {body}\n\n".encode())

        try:
            await runtime.async_ensure_weather()
            await emit("state", _snapshot(hass, runtime, record, request))
            while True:
                try:
                    kind = await asyncio.wait_for(queue.get(), timeout=20)
                    while not queue.empty():
                        kind = queue.get_nowait()
                except asyncio.TimeoutError:
                    current = runtime.session_for_token(token, require_active=False)
                    if current is None:
                        await emit("expired", {"error": "invalid_token"})
                        break
                    # House tablets: refresh greeting when the stay rolls over.
                    if runtime.is_house_token(token):
                        await emit("state", _snapshot(hass, runtime, current, request))
                    else:
                        await response.write(b": ping\n\n")
                    continue
                current = runtime.session_for_token(token, require_active=False)
                if current is None or kind == "expired":
                    await emit("expired", {"error": "invalid_token"})
                    break
                await emit("state", _snapshot(hass, runtime, current, request))
        except (ConnectionResetError, asyncio.CancelledError, BrokenPipeError):
            pass
        finally:
            unsub()
            unsub_demo()
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
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, 400, "bad_json")
        entity_id = str(body.get("entity_id") or "")
        brand = runtime.guest_brand()
        allow_fans = brand_climate_fans(brand)
        heat_only = brand_heat_only(brand)
        if runtime.demo_mode() and is_demo_entity(entity_id):
            villa = runtime.demo_villa()
            if villa is None:
                return _json_error(self, 404, "missing")
            house_mode = HOUSE_HEAT if heat_only else _house_mode(hass, runtime, [])
            if not allow_fans:
                body = {key: value for key, value in body.items() if key != "fan"}
            item = apply_demo_climate(villa, entity_id, body, house_mode=house_mode)
            if item is None:
                return _json_error(self, 404, "missing")
            item = dict(item)
            item["supports_fan"] = False if not allow_fans else bool(item.get("supports_fan", True))
            if not allow_fans:
                item["fan"] = None
            hass.bus.async_fire(EVENT_DEMO)
            return self.json(item)
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
        preset_modes = [str(mode) for mode in (attrs.get("preset_modes") or [])]
        house_mode = HOUSE_HEAT if heat_only else _house_mode(hass, runtime, climates)
        power_via = climate_power_via(hvac_modes, preset_modes)
        try:
            if "on" in body:
                if body["on"]:
                    if power_via == "preset":
                        preset = pick_preset_on(preset_modes)
                        if preset:
                            await hass.services.async_call(
                                "climate",
                                "set_preset_mode",
                                {
                                    "entity_id": entity_id,
                                    "preset_mode": preset,
                                },
                                blocking=True,
                            )
                        if hvac_modes:
                            mode = pick_hvac_on(hvac_modes, house_mode)
                            await hass.services.async_call(
                                "climate",
                                "set_hvac_mode",
                                {"entity_id": entity_id, "hvac_mode": mode},
                                blocking=True,
                            )
                    else:
                        mode = pick_hvac_on(hvac_modes, house_mode)
                        await hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": entity_id, "hvac_mode": mode},
                            blocking=True,
                        )
                elif power_via == "preset":
                    preset = pick_preset_off(preset_modes)
                    if preset:
                        await hass.services.async_call(
                            "climate",
                            "set_preset_mode",
                            {
                                "entity_id": entity_id,
                                "preset_mode": preset,
                            },
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
            if allow_fans and "fan" in body and body["fan"] is not None:
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
        payload = _serialize_climate(
            hass, entity_id, house_mode=house_mode, allow_fans=allow_fans
        )
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
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, 400, "bad_json")
        entity_id = str(body.get("entity_id") or "")
        action = str(body.get("action") or "unlock")
        if runtime.demo_mode() and is_demo_entity(entity_id):
            if action not in {"unlock", "lock"}:
                return _json_error(self, 400, "bad_action")
            villa = runtime.demo_villa()
            if villa is None:
                return _json_error(self, 404, "missing")
            try:
                item = apply_demo_command(villa, entity_id, "lock", action)
            except ValueError:
                return _json_error(self, 400, "bad_action")
            if item is None:
                return _json_error(self, 404, "missing")
            hass.bus.async_fire(EVENT_DEMO)
            return self.json(item)
        _climates, locks = _partition(hass, runtime.allowed_entity_ids(record))
        if entity_id not in locks:
            return _json_error(self, 403, "forbidden")
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
    """Lights, scenes, covers, garage, gate, alarm, speakers — stay allow-list only."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/command"
    name = f"api:{DOMAIN}:guest_command"

    async def post(self, request: Any) -> Any:
        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, 400, "bad_json")
        entity_id = str(body.get("entity_id") or "")
        action = str(body.get("action") or "")
        value = body.get("value")
        if runtime.demo_mode() and is_demo_entity(entity_id):
            villa = runtime.demo_villa()
            kind = demo_entity_kind(villa, entity_id)
            if kind not in _COMMAND_KINDS:
                return _json_error(self, 403, "forbidden")
            try:
                item = apply_demo_command(villa or {}, entity_id, kind, action, value)
            except ValueError:
                return _json_error(self, 400, "bad_action")
            if item is None:
                return _json_error(self, 404, "missing")
            hass.bus.async_fire(EVENT_DEMO)
            return self.json(item)
        allowed = runtime.allowed_entity_ids(record)
        if entity_id not in allowed:
            return _json_error(self, 403, "forbidden")
        kind = _entity_kind(hass, entity_id)
        if kind not in _COMMAND_KINDS:
            return _json_error(self, 403, "forbidden")
        try:
            await _async_guest_command(hass, runtime, entity_id, kind, action, value)
        except ValueError:
            return _json_error(self, 400, "bad_action")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Guest command failed")
            return _json_error(self, 502, "command_failed")
        return self.json(_serialize_command_result(hass, entity_id, kind) or {"entity_id": entity_id})


async def _async_guest_command(
    hass: Any,
    runtime: Any,
    entity_id: str,
    kind: str,
    action: str,
    value: Any = None,
) -> None:
    domain = entity_id.split(".", 1)[0]
    data: dict[str, Any] = {"entity_id": entity_id}
    if kind in {GUEST_KIND_LIGHT, GUEST_KIND_POOL_LIGHT}:
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
        has_tydom = hass.services.has_service(TYDOM_DOMAIN, TYDOM_SET_MODE)
        domain, service, payload = guest_alarm_service(
            action,
            entity_id,
            has_tydom=has_tydom,
            code=runtime.alarm_code(),
        )
        await hass.services.async_call(domain, service, payload, blocking=True)
        return
    if kind == GUEST_KIND_SPEAKER:
        await _async_speaker_command(hass, entity_id, action, value)
        return
    raise ValueError("bad_action")


async def _async_speaker_command(
    hass: Any, entity_id: str, action: str, value: Any
) -> None:
    data: dict[str, Any] = {"entity_id": entity_id}
    if action == "volume":
        level = _as_float(value)
        if level is None:
            raise ValueError("bad_action")
        volume = max(0.0, min(100.0, level)) / 100.0
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {**data, "volume_level": volume},
            blocking=True,
        )
        return
    if action == "mute":
        await hass.services.async_call(
            "media_player",
            "volume_mute",
            {**data, "is_volume_muted": True},
            blocking=True,
        )
        return
    if action == "unmute":
        await hass.services.async_call(
            "media_player",
            "volume_mute",
            {**data, "is_volume_muted": False},
            blocking=True,
        )
        return
    service = {
        "play": "media_play",
        "pause": "media_pause",
        "stop": "media_stop",
    }.get(action)
    if not service:
        raise ValueError("bad_action")
    await hass.services.async_call("media_player", service, data, blocking=True)


def _serialize_command_result(hass: Any, entity_id: str, kind: str) -> dict[str, Any] | None:
    if kind in {GUEST_KIND_LIGHT, GUEST_KIND_POOL_LIGHT}:
        return _serialize_light(hass, entity_id)
    if kind == GUEST_KIND_SCENE:
        return _serialize_scene(hass, entity_id)
    if kind in {GUEST_KIND_GARAGE, GUEST_KIND_GATE, GUEST_KIND_SHUTTER}:
        return _serialize_cover(hass, entity_id, kind)
    if kind == GUEST_KIND_LOCK:
        return _serialize_lock(hass, entity_id)
    if kind == GUEST_KIND_ALARM:
        return _serialize_alarm(hass, entity_id)
    if kind == GUEST_KIND_SPEAKER:
        return _serialize_speaker(hass, entity_id)
    return {"entity_id": entity_id}


class GuestSnapshotView(HomeAssistantView):
    """Still from an allowed visio camera. Token in the query for <img>."""

    requires_auth = False
    cors_allowed = True
    url = f"/api/{DOMAIN}/guest/snapshot"
    name = f"api:{DOMAIN}:guest_snapshot"

    async def get(self, request: Any) -> Any:
        from aiohttp import web

        hass, runtime, record = await _bound(request)
        if runtime is None:
            return _json_error(self, 503, "not_loaded")
        denied = _lan_denied(self, record) or _guest_not_ready(self, record)
        if denied is not None:
            return denied
        entity_id = str(request.query.get("entity_id") or "")
        allowed = runtime.allowed_entity_ids(record)
        if entity_id not in allowed:
            return _json_error(self, 403, "forbidden")
        if _entity_kind(hass, entity_id) != GUEST_KIND_CAMERA:
            return _json_error(self, 403, "forbidden")
        try:
            from homeassistant.components.camera import async_get_image

            image = await async_get_image(hass, entity_id, timeout=10)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Guest snapshot failed")
            return _json_error(self, 502, "snapshot_failed")
        content_type = getattr(image, "content_type", None) or "image/jpeg"
        return web.Response(
            body=image.content,
            content_type=content_type,
            headers={"Cache-Control": "no-store"},
        )
