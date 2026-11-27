"""In-memory villa for the guest web app demo switch.

No Home Assistant import: the snapshot overlay and guest commands are
unit-tested against this catalog.
"""

from __future__ import annotations

from typing import Any

from .guest_session import HOUSE_COOL, climate_activity, house_mode_label

DEMO_MARKER = "usvegliu_demo_"
DEMO_VOUCHER = "DEMO12"
DEMO_NUKI = "258369"

_LIST_KEYS = (
    "climates",
    "lights",
    "scenes",
    "locks",
    "garages",
    "gates",
    "shutters",
    "alarms",
    "pool_lights",
    "chargers",
    "doorbells",
    "cameras",
    "speakers",
    "tvs",
    "metrics",
)


def is_demo_entity(entity_id: str) -> bool:
    """True for the synthetic ids used only while the demo switch is on."""
    return DEMO_MARKER in str(entity_id or "")


def _eid(domain: str, slug: str) -> str:
    return f"{domain}.{DEMO_MARKER}{slug}"


def _climate(
    slug: str,
    name: str,
    *,
    measured: float,
    setpoint: float,
    on: bool,
    fan: int,
    house_mode: str,
) -> dict[str, Any]:
    hvac = house_mode if on else "off"
    return {
        "entity_id": _eid("climate", slug),
        "name": name,
        "group": name,
        "measured": measured,
        "setpoint": setpoint,
        "on": on,
        "hvac_mode": hvac,
        "activity": climate_activity(
            on=on, house_mode=house_mode, measured=measured, setpoint=setpoint
        ),
        "supports_fan": True,
        "fan": fan,
        "min": 16,
        "max": 28,
    }


def _refresh_climates(
    climates: list[dict[str, Any]], house_mode: str
) -> list[dict[str, Any]]:
    refreshed: list[dict[str, Any]] = []
    for room in climates:
        item = dict(room)
        on = bool(item.get("on"))
        measured = item.get("measured")
        setpoint = item.get("setpoint")
        item["on"] = on
        item["hvac_mode"] = house_mode if on else "off"
        item["activity"] = climate_activity(
            on=on,
            house_mode=house_mode,
            measured=None if measured is None else float(measured),
            setpoint=None if setpoint is None else float(setpoint),
        )
        refreshed.append(item)
    return refreshed


def build_demo_villa(house_mode: str = HOUSE_COOL) -> dict[str, Any]:
    """A full U Svegliu-shaped guest snapshot: ten rooms, car, pool, sound."""
    mode = house_mode if house_mode in {"heat", "cool"} else HOUSE_COOL
    climates = [
        _climate("salon", "Salon", measured=26.5, setpoint=24, on=True, fan=2, house_mode=mode),
        _climate("cuisine", "Cuisine", measured=25.0, setpoint=24, on=True, fan=1, house_mode=mode),
        _climate(
            "salle_a_manger",
            "Salle à manger",
            measured=25.5,
            setpoint=24,
            on=False,
            fan=2,
            house_mode=mode,
        ),
        _climate("suite", "Suite", measured=27.0, setpoint=23, on=True, fan=3, house_mode=mode),
        _climate(
            "chambre_2", "Chambre 2", measured=24.0, setpoint=24, on=True, fan=1, house_mode=mode
        ),
        _climate(
            "chambre_3", "Chambre 3", measured=26.0, setpoint=25, on=False, fan=2, house_mode=mode
        ),
        _climate("bureau", "Bureau", measured=26.0, setpoint=24, on=True, fan=2, house_mode=mode),
        _climate(
            "sport", "Salle de sport", measured=28.0, setpoint=22, on=True, fan=3, house_mode=mode
        ),
        _climate("spa", "Spa", measured=25.0, setpoint=26, on=True, fan=1, house_mode=mode),
        _climate(
            "terrasse", "Terrasse", measured=29.0, setpoint=26, on=False, fan=2, house_mode=mode
        ),
    ]
    return {
        "mode": mode,
        "mode_label": house_mode_label(mode),
        "climates": climates,
        "lights": [
            {
                "entity_id": _eid("light", "salon_plafond"),
                "name": "Plafond",
                "group": "Salon",
                "on": True,
                "brightness": 180,
                "brightness_pct": 71,
                "dimmable": True,
            },
            {
                "entity_id": _eid("light", "salon_applique"),
                "name": "Applique",
                "group": "Salon",
                "on": False,
                "brightness": 40,
                "brightness_pct": 16,
                "dimmable": True,
            },
            {
                "entity_id": _eid("light", "cuisine"),
                "name": "Îlot",
                "group": "Cuisine",
                "on": False,
                "brightness": 40,
                "brightness_pct": 16,
                "dimmable": True,
            },
            {
                "entity_id": _eid("light", "terrasse"),
                "name": "Extérieur",
                "group": "Terrasse",
                "on": True,
                "brightness": 120,
                "brightness_pct": 47,
                "dimmable": True,
            },
            {
                "entity_id": _eid("light", "suite"),
                "name": "Chevet",
                "group": "Suite",
                "on": False,
                "brightness": 0,
                "brightness_pct": 0,
                "dimmable": True,
            },
        ],
        "scenes": [
            {"entity_id": _eid("scene", "soiree"), "name": "Soirée"},
            {"entity_id": _eid("scene", "nuit"), "name": "Nuit"},
        ],
        "locks": [
            {
                "entity_id": _eid("lock", "porte"),
                "name": "Porte d'entrée",
                "locked": True,
                "state": "locked",
            }
        ],
        "garages": [
            {
                "entity_id": _eid("cover", "garage"),
                "name": "Garage",
                "kind": "garage",
                "open": False,
                "moving": False,
                "state": "closed",
            }
        ],
        "gates": [
            {
                "entity_id": _eid("cover", "portail"),
                "name": "Portail",
                "kind": "gate",
                "open": False,
                "moving": False,
                "state": "closed",
            }
        ],
        "shutters": [
            {
                "entity_id": _eid("cover", "volet_salon"),
                "name": "Volet salon",
                "kind": "shutter",
                "open": True,
                "moving": False,
                "state": "open",
            },
            {
                "entity_id": _eid("cover", "volet_suite"),
                "name": "Volet suite",
                "kind": "shutter",
                "open": False,
                "moving": False,
                "state": "closed",
            },
        ],
        "alarms": [
            {
                "entity_id": _eid("alarm_control_panel", "alarme"),
                "name": "Alarme",
                "state": "disarmed",
                "raw": "disarmed",
            }
        ],
        "pool_lights": [
            {
                "entity_id": _eid("light", "piscine"),
                "name": "Lumière piscine",
                "group": "Piscine",
                "on": False,
                "brightness": 0,
                "brightness_pct": 0,
                "dimmable": True,
            }
        ],
        "chargers": [
            {
                "entity_id": _eid("sensor", "borne"),
                "name": "Borne",
                "state": "charging",
                "level": 64,
                "raw": "Charging",
            }
        ],
        "doorbells": [
            {
                "entity_id": _eid("binary_sensor", "sonnette"),
                "name": "Visiophone",
                "ringing": False,
                "state": "idle",
                "raw": "off",
            }
        ],
        "cameras": [],
        "speakers": [
            {
                "entity_id": _eid("media_player", "salon"),
                "name": "Salon",
                "state": "playing",
                "volume": 38,
                "muted": False,
            },
            {
                "entity_id": _eid("media_player", "terrasse"),
                "name": "Terrasse",
                "state": "paused",
                "volume": 22,
                "muted": False,
            },
            {
                "entity_id": _eid("media_player", "piscine"),
                "name": "Piscine",
                "state": "idle",
                "volume": 15,
                "muted": False,
            },
        ],
        "tvs": [
            {
                "entity_id": _eid("media_player", "living_atv"),
                "name": "Living room",
                "state": "on",
                "volume": 28,
                "muted": False,
                "remote_entity_id": _eid("remote", "living_atv"),
                "supports_remote": True,
            },
            {
                "entity_id": _eid("media_player", "kitchen_atv"),
                "name": "Kitchen",
                "state": "off",
                "volume": 18,
                "muted": False,
                "remote_entity_id": _eid("remote", "kitchen_atv"),
                "supports_remote": True,
            },
            {
                "entity_id": _eid("media_player", "master_atv"),
                "name": "Master bedroom",
                "state": "on",
                "volume": 22,
                "muted": False,
                "remote_entity_id": _eid("remote", "master_atv"),
                "supports_remote": True,
            },
        ],
        "metrics": [
            {
                "entity_id": _eid("sensor", "exterieur"),
                "kind": "outdoor",
                "label": "Extérieur",
                "value": 24.0,
                "unit": "°",
            },
            {
                "entity_id": _eid("sensor", "eau"),
                "kind": "pool_temp",
                "label": "Piscine",
                "value": 27.5,
                "unit": "°",
            },
            {
                "entity_id": _eid("sensor", "ph"),
                "kind": "pool_ph",
                "label": "pH",
                "value": 7.2,
                "unit": "",
            },
        ],
        "weather": {
            "place": "Lumio",
            "label": "Ensoleillé",
            "icon": "sun",
            "code": 0,
            "temperature": 24,
            "high": 27,
            "low": 19,
            "wind": 12,
        },
    }


def demo_entity_ids(villa: dict[str, Any] | None) -> list[str]:
    """Every synthetic entity id currently in the demo villa."""
    ids: list[str] = []
    for key in _LIST_KEYS:
        for item in (villa or {}).get(key) or []:
            entity_id = str(item.get("entity_id") or "")
            if entity_id:
                ids.append(entity_id)
    return ids


def demo_entity_kind(villa: dict[str, Any] | None, entity_id: str) -> str | None:
    """Guest kind for one demo entity, or None."""
    mapping = {
        "climates": "climate",
        "lights": "light",
        "scenes": "scene",
        "locks": "lock",
        "garages": "garage",
        "gates": "gate",
        "shutters": "shutter",
        "alarms": "alarm",
        "pool_lights": "pool_light",
        "chargers": "charger",
        "doorbells": "doorbell",
        "cameras": "camera",
        "speakers": "speaker",
        "tvs": "tv",
    }
    for key, kind in mapping.items():
        for item in (villa or {}).get(key) or []:
            if item.get("entity_id") == entity_id:
                return kind
    return None


def _find(villa: dict[str, Any], entity_id: str) -> tuple[str, dict[str, Any]] | None:
    for key in _LIST_KEYS:
        items = villa.get(key) or []
        for item in items:
            if item.get("entity_id") == entity_id:
                return key, item
    return None


def apply_demo_climate(
    villa: dict[str, Any],
    entity_id: str,
    body: dict[str, Any],
    *,
    house_mode: str,
) -> dict[str, Any] | None:
    """Mutate one demo thermostat. Returns the updated room view."""
    found = _find(villa, entity_id)
    if found is None or found[0] != "climates":
        return None
    _, room = found
    if "on" in body:
        room["on"] = bool(body["on"])
    if "setpoint" in body and body["setpoint"] is not None:
        try:
            value = float(body["setpoint"])
        except (TypeError, ValueError):
            value = float(room.get("setpoint") or 22)
        room["setpoint"] = max(16.0, min(28.0, round(value, 1)))
    if "fan" in body and body["fan"] is not None:
        try:
            fan = int(body["fan"])
        except (TypeError, ValueError):
            fan = 2
        room["fan"] = max(1, min(3, fan))
    villa["climates"] = _refresh_climates(list(villa.get("climates") or []), house_mode)
    for item in villa["climates"]:
        if item.get("entity_id") == entity_id:
            return item
    return room


def apply_demo_command(
    villa: dict[str, Any],
    entity_id: str,
    kind: str,
    action: str,
    value: Any = None,
) -> dict[str, Any] | None:
    """Mutate a demo light, cover, lock, alarm or speaker. Raises ValueError."""
    found = _find(villa, entity_id)
    if found is None:
        return None
    _key, item = found
    if kind in {"light", "pool_light"}:
        if action == "brightness":
            try:
                pct = int(round(float(value) / 10.0) * 10)
            except (TypeError, ValueError) as exc:
                raise ValueError("bad_action") from exc
            pct = max(0, min(100, pct))
            item["on"] = pct > 0
            item["brightness"] = int(round(pct / 100.0 * 255.0)) if pct else 0
            item["brightness_pct"] = pct
            item["dimmable"] = True
            return item
        if action not in {"on", "off", "toggle"}:
            raise ValueError("bad_action")
        if action == "toggle":
            item["on"] = not bool(item.get("on"))
        else:
            item["on"] = action == "on"
        if item["on"]:
            current = int(item.get("brightness") or 0)
            item["brightness"] = current if current > 0 else 180
            item["brightness_pct"] = int(round(item["brightness"] / 255.0 * 100.0))
        else:
            item["brightness"] = 0
            item["brightness_pct"] = 0
        item["dimmable"] = True
        return item
    if kind == "scene":
        if action != "activate":
            raise ValueError("bad_action")
        return item
    if kind in {"garage", "gate", "shutter"}:
        if action not in {"open", "close", "stop"}:
            raise ValueError("bad_action")
        if action == "stop":
            item["moving"] = False
        else:
            item["open"] = action == "open"
            item["moving"] = False
            item["state"] = "open" if item["open"] else "closed"
        return item
    if kind == "lock":
        if action not in {"lock", "unlock"}:
            raise ValueError("bad_action")
        item["locked"] = action == "lock"
        item["state"] = "locked" if item["locked"] else "unlocked"
        return item
    if kind == "alarm":
        if action not in {"arm", "disarm"}:
            raise ValueError("bad_action")
        item["state"] = "armed" if action == "arm" else "disarmed"
        item["raw"] = "armed_away" if action == "arm" else "disarmed"
        return item
    if kind == "speaker":
        return _apply_demo_speaker(item, action, value)
    if kind == "tv":
        return _apply_demo_tv(item, action, value)
    raise ValueError("bad_action")


def _apply_demo_speaker(item: dict[str, Any], action: str, value: Any) -> dict[str, Any]:
    if action == "volume":
        try:
            level = float(value)
        except (TypeError, ValueError) as err:
            raise ValueError("bad_action") from err
        item["volume"] = int(max(0, min(100, round(level))))
        return item
    if action == "mute":
        item["muted"] = True
        return item
    if action == "unmute":
        item["muted"] = False
        return item
    if action == "play":
        item["state"] = "playing"
        item["muted"] = False
        return item
    if action in {"pause", "stop"}:
        item["state"] = "paused" if action == "pause" else "idle"
        return item
    raise ValueError("bad_action")


def _apply_demo_tv(item: dict[str, Any], action: str, value: Any) -> dict[str, Any]:
    fold = str(action or "").casefold().strip()
    if fold == "volume":
        try:
            level = float(value)
        except (TypeError, ValueError) as err:
            raise ValueError("bad_action") from err
        item["volume"] = int(max(0, min(100, round(level))))
        return item
    if fold == "volume_up":
        item["volume"] = int(min(100, int(item.get("volume") or 0) + 5))
        return item
    if fold == "volume_down":
        item["volume"] = int(max(0, int(item.get("volume") or 0) - 5))
        return item
    if fold == "mute":
        item["muted"] = True
        return item
    if fold == "unmute":
        item["muted"] = False
        return item
    if fold in {"on", "turn_on", "power_on", "wakeup"}:
        item["state"] = "on"
        return item
    if fold in {"off", "turn_off", "power_off", "suspend"}:
        item["state"] = "off"
        return item
    if fold in {
        "up",
        "down",
        "left",
        "right",
        "select",
        "menu",
        "home",
        "home_hold",
        "top_menu",
        "play",
        "pause",
        "stop",
        "next",
        "previous",
        "skip_forward",
        "skip_backward",
    }:
        # Navigation is fire-and-forget in demo; keep TV awake.
        item["state"] = "on"
        item["last_remote"] = fold
        return item
    raise ValueError("bad_action")


def overlay_demo_snapshot(
    payload: dict[str, Any],
    villa: dict[str, Any],
    *,
    house_mode: str,
) -> dict[str, Any]:
    """Replace guest equipment with the demo villa. Keep stay identity."""
    out = dict(payload)
    mode = house_mode if house_mode in {"heat", "cool"} else str(villa.get("mode") or HOUSE_COOL)
    out["demo"] = True
    out["mode"] = mode
    out["mode_label"] = house_mode_label(mode)
    out["climates"] = _refresh_climates(list(villa.get("climates") or []), mode)
    for key in _LIST_KEYS:
        if key == "climates":
            continue
        if key in villa:
            out[key] = list(villa.get(key) or [])
    if villa.get("metrics"):
        out["metrics"] = list(villa["metrics"])
    if not out.get("weather") and villa.get("weather"):
        out["weather"] = dict(villa["weather"])
    info = dict(out.get("informations") or {})
    if not info.get("voucher_code") and not info.get("voucher_revoked"):
        info["voucher_code"] = DEMO_VOUCHER
    if not info.get("nuki_code") and not info.get("nuki_revoked"):
        info["nuki_code"] = DEMO_NUKI
    out["informations"] = info
    if not str(out.get("guest") or "").strip():
        out["guest"] = "Essai"
    return out
