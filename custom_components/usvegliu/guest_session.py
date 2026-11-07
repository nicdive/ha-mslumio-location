"""Stay tokens and climate/lock helpers for the guest web app.

Pure Python: no Home Assistant import, so the mapping can be unit-tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import secrets
from typing import Any

from .const import DEFAULT_EXTRA_DAYS, DEFAULT_WIFI_SSID, DOMAIN
from .planning import maison_closes_at, wifi_revokes_at

PREVIEW_KEY = "__usvegliu_preview__"
PREVIEW_HOURS = 24
TOKEN_MIN_LENGTH = 16

_MONTHS_FR = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)

_OFF_HVAC = frozenset({"off", "idle"})
_HVAC_ON_ORDER = ("heat", "cool", "heat_cool", "fan_only", "dry", "auto")
HOUSE_HEAT = "heat"
HOUSE_COOL = "cool"
_COOL_STATES = frozenset(
    {"on", "true", "1", "cool", "cooling", "climatisation", "clim", "cold"}
)
_HEAT_STATES = frozenset(
    {"off", "false", "0", "heat", "heating", "chauffage", "hot"}
)
_FAN_ALIASES: dict[int, tuple[str, ...]] = {
    1: ("low", "low_breeze", "min", "1", "level_1", "level1", "doux"),
    2: ("medium", "mid", "middle", "med", "2", "level_2", "level2", "moyen"),
    3: ("high", "max", "3", "level_3", "level3", "fort"),
}
_FAN_SKIP = frozenset({"auto", "off", "on"})


def generate_guest_token() -> str:
    """Opaque stay token. Long enough to share in a URL."""
    return secrets.token_urlsafe(24)


def ensure_guest_token(record: dict[str, Any]) -> str:
    """Keep an existing token; mint one when the stay is first provisioned."""
    token = record.get("guest_token")
    if isinstance(token, str) and len(token) >= TOKEN_MIN_LENGTH:
        return token
    minted = generate_guest_token()
    record["guest_token"] = minted
    return minted


def parse_iso(value: Any, tzinfo: timezone | None = None) -> datetime | None:
    """Parse an ISO datetime stored on a stay record."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None and tzinfo is not None:
        return parsed.replace(tzinfo=tzinfo)
    return parsed


def stay_access_end(record: dict[str, Any], now: datetime) -> datetime | None:
    """Maison link and HA login stop at the end of the departure day."""
    end = parse_iso(record.get("check_out"), now.tzinfo)
    if end is None:
        return None
    if record.get("preview"):
        return end
    return maison_closes_at(end)


def stay_wifi_end(
    record: dict[str, Any],
    now: datetime,
    extra_days: int = DEFAULT_EXTRA_DAYS,
) -> datetime | None:
    """UniFi voucher is deleted one extra day after departure, by default."""
    end = parse_iso(record.get("check_out"), now.tzinfo)
    if end is None:
        return None
    if record.get("preview"):
        return end
    return wifi_revokes_at(end, extra_days)


def stay_is_issued(
    record: dict[str, Any],
    now: datetime,
    extra_days: int = DEFAULT_EXTRA_DAYS,
) -> bool:
    """True while the stay is still on the owner Console (Wi-Fi window)."""
    close = stay_wifi_end(record, now, extra_days)
    return close is not None and now < close


def stay_is_open(
    record: dict[str, Any],
    now: datetime,
    extra_days: int = DEFAULT_EXTRA_DAYS,
) -> bool:
    """Issued stay, including the days before arrival. Owner Console."""
    return stay_is_issued(record, now, extra_days)


def stay_activation_start(record: dict[str, Any], now: datetime) -> datetime | None:
    """Local midnight of the arrival day. A preview starts at once."""
    start = parse_iso(record.get("check_in"), now.tzinfo)
    if start is None:
        return None
    if record.get("preview"):
        return start
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def stay_is_active(record: dict[str, Any], now: datetime) -> bool:
    """True when the Maison link and HA login may be used.

    From local midnight of the arrival day through the end of the planned
    departure day. A 24 h preview is usable as soon as it is minted.
    """
    begin = stay_activation_start(record, now)
    close = stay_access_end(record, now)
    if begin is None or close is None:
        return False
    return begin <= now < close


def open_issued_records(
    stays: dict[str, dict[str, Any]],
    preview: dict[str, Any] | None,
    now: datetime,
    extra_days: int = DEFAULT_EXTRA_DAYS,
) -> list[dict[str, Any]]:
    """Provisioned stays still listed, then a live preview, by check-in."""
    records = [
        record for record in stays.values() if stay_is_issued(record, now, extra_days)
    ]
    records.sort(key=lambda record: str(record.get("check_in") or ""))
    if isinstance(preview, dict) and stay_is_issued(preview, now, extra_days):
        records.append(preview)
    return records


def credential_attribute_key(reservation_id: str) -> str:
    """Top-level sensor attribute Lovelace can display without the name ``password``.

    The Home Assistant frontend hides attributes named ``password`` in
    markdown templates and more-info. ``compte_<id>`` stays visible.
    """
    safe = re.sub(r"[^0-9A-Za-z]+", "_", str(reservation_id or "")).strip("_")
    if not safe:
        safe = "sejour"
    return f"compte_{safe[:48]}"


def _parse_stay_date(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_arrival_day(check_in: str) -> str:
    """``7 novembre``, or empty when the date cannot be parsed."""
    start = _parse_stay_date(check_in)
    if start is None:
        return ""
    return f"{start.day} {_MONTHS_FR[start.month - 1]}"


def format_stay_span(check_in: str, check_out: str) -> str:
    """Human stay window in French, or empty if the dates are missing."""
    start = _parse_stay_date(check_in)
    end = _parse_stay_date(check_out)
    if start is None or end is None:
        return ""
    if start.month == end.month and start.year == end.year:
        return f"{start.day} au {end.day} {_MONTHS_FR[start.month - 1]}"
    if start.year == end.year:
        return (
            f"{start.day} {_MONTHS_FR[start.month - 1]} au "
            f"{end.day} {_MONTHS_FR[end.month - 1]}"
        )
    return (
        f"{start.day} {_MONTHS_FR[start.month - 1]} {start.year} au "
        f"{end.day} {_MONTHS_FR[end.month - 1]} {end.year}"
    )


def guest_first_name(guest: str) -> str:
    """First word of the calendar title, for a short greeting."""
    return str(guest or "").strip().split()[0] if str(guest or "").strip() else ""


def guest_welcome_message(
    *,
    guest: str,
    check_in: str,
    check_out: str,
    lien_maison: str,
    wifi_ssid: str,
    voucher_code: str | None,
    voucher_revoked: bool,
    preview: bool,
) -> str:
    """Copy-ready note for the guest. No Home Assistant login."""
    name = guest_first_name(guest)
    hello = f"Bonjour {name}," if name else "Bonjour,"
    span = format_stay_span(check_in, check_out)
    stay = f" pour votre séjour du {span}" if span else ""
    link = str(lien_maison or "").strip()
    ssid = str(wifi_ssid or "").strip() or DEFAULT_WIFI_SSID
    code = "" if voucher_revoked else str(voucher_code or "").strip()
    if preview:
        lines = [
            hello,
            "",
            "Voici un lien d'essai, valable 24 heures, pour découvrir la maison :",
            "",
            link or "—",
            "",
            "Nous vous souhaitons une belle visite.",
            "",
            "L'équipe Usvegliu",
        ]
        return "\n".join(lines)
    lines = [
        hello,
        "",
        f"Nous avons le plaisir de vous accueillir à Usvegliu{stay}.",
        "",
        "Votre maison s'ouvre ici, sur votre lien personnel :",
        "",
        link or "—",
        "",
    ]
    lines.append(f"Réseau Wi-Fi : {ssid}")
    if code:
        lines.append(f"Code d'accès : {code}")
    elif voucher_revoked:
        lines.append("Le code Wi-Fi a été révoqué. Nous vous en ferons parvenir un autre.")
    if ssid or code:
        lines.extend(
            [
                "",
                "Ouvrez le lien depuis votre téléphone, rejoignez le réseau, "
                "puis saisissez le code sur la page d'accueil Wi-Fi.",
            ]
        )
    lines.extend(
        [
            "",
            "Nous vous souhaitons un séjour d'exception.",
            "",
            "L'équipe Usvegliu",
        ]
    )
    return "\n".join(lines)


def issued_account_view(
    record: dict[str, Any],
    *,
    username: str | None,
    password: str | None,
    lien_maison: str,
    path: str,
    tableau: str,
    wifi_ssid: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Admin row for one issued stay, including the HA password.

    The guest HTTP API never uses this mapping. Diagnostics and the CSV
    journal still redact or drop the password.
    """
    secret = str(password or record.get("password") or "") or None
    preview = bool(record.get("preview"))
    revoked = bool(record.get("voucher_revoked"))
    active = True if now is None or preview else stay_is_active(record, now)
    code = str(record.get("voucher_code") or "") or None
    ssid = str(wifi_ssid or "").strip() or DEFAULT_WIFI_SSID
    return {
        "guest": str(record.get("guest") or ""),
        "check_in": str(record.get("check_in") or ""),
        "check_out": str(record.get("check_out") or ""),
        "username": str(username or record.get("username") or ""),
        "password": secret,
        # Lovelace / the frontend hide the attribute name ``password``.
        "mot_de_passe": secret,
        "code_compte": secret,
        "voucher_code": code,
        "wifi_ssid": ssid,
        "reseau_wifi": ssid,
        "prenom": guest_first_name(str(record.get("guest") or "")),
        "sejour_libelle": format_stay_span(
            str(record.get("check_in") or ""),
            str(record.get("check_out") or ""),
        ),
        "lien_maison": lien_maison,
        "message_invite": guest_welcome_message(
            guest=str(record.get("guest") or ""),
            check_in=str(record.get("check_in") or ""),
            check_out=str(record.get("check_out") or ""),
            lien_maison=lien_maison,
            wifi_ssid=ssid,
            voucher_code=code,
            voucher_revoked=revoked,
            preview=preview,
        ),
        "path": path,
        "reservation_id": str(record.get("key") or ""),
        "essai": preview,
        "tableau": tableau,
        "access_revoked": bool(record.get("access_revoked")),
        "voucher_revoked": revoked,
        "acces_actif": active,
    }


def find_record_by_token(
    stays: dict[str, dict[str, Any]],
    preview: dict[str, Any] | None,
    token: str,
    now: datetime,
    *,
    require_active: bool = True,
    extra_days: int = DEFAULT_EXTRA_DAYS,
) -> dict[str, Any] | None:
    """Return the stay or preview bound to ``token``.

    ``require_active`` is True for guest use (arrival day). False still
    finds a token issued in the lead window so the API can answer
    ``too_early`` instead of ``invalid_token``.
    """
    if not token or len(token) < TOKEN_MIN_LENGTH:
        return None
    found: dict[str, Any] | None = None
    if isinstance(preview, dict) and preview.get("guest_token") == token:
        if stay_is_issued(preview, now, extra_days):
            found = preview
    if found is None:
        for record in stays.values():
            if record.get("guest_token") == token and stay_is_issued(
                record, now, extra_days
            ):
                found = record
                break
    if found is None:
        return None
    if require_active and not stay_is_active(found, now):
        return None
    return found


def build_preview_record(now: datetime, hours: int = PREVIEW_HOURS) -> dict[str, Any]:
    """Admin test session, independent from the calendar."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    end = now + timedelta(hours=hours)
    record: dict[str, Any] = {
        "key": PREVIEW_KEY,
        "guest": "Essai",
        "check_in": now.isoformat(),
        "check_out": end.isoformat(),
        "preview": True,
    }
    ensure_guest_token(record)
    return record


def normalize_fan_label(value: str) -> str:
    """Compare fan mode names without punctuation."""
    return value.casefold().replace(" ", "_").replace("-", "_")


def map_fan_modes(available: list[str]) -> dict[int, str]:
    """Map guest speeds 1/2/3 onto the climate entity's fan_mode values."""
    mapping: dict[int, str] = {}
    unused = [
        mode
        for mode in available
        if mode and normalize_fan_label(mode) not in _FAN_SKIP
    ]
    for speed, aliases in _FAN_ALIASES.items():
        for mode in unused:
            if normalize_fan_label(mode) in aliases:
                mapping[speed] = mode
                break
    leftovers = [mode for mode in unused if mode not in mapping.values()]
    for speed in (1, 2, 3):
        if speed not in mapping and leftovers:
            mapping[speed] = leftovers.pop(0)
    return mapping


def infer_fan_speed(current: str | None, mapping: dict[int, str]) -> int:
    """Best-effort 1/2/3 from the live fan_mode."""
    if current:
        needle = normalize_fan_label(current)
        for speed, mode in mapping.items():
            if normalize_fan_label(mode) == needle:
                return speed
    return 2 if 2 in mapping else next(iter(mapping), 2)


def climate_is_on(hvac_mode: str | None) -> bool:
    """Treat off/idle as stopped."""
    if not hvac_mode:
        return False
    return hvac_mode.casefold() not in _OFF_HVAC


def house_mode_from_state(state: str | None) -> str | None:
    """Map a house switch or select onto heat/cool.

    Switch/boolean: on = climatisation, off = chauffage.
    Select: chauffage/heat vs climatisation/cool.
    """
    if not state:
        return None
    fold = state.casefold().strip()
    if fold in {"unavailable", "unknown", "none"}:
        return None
    if fold in _COOL_STATES:
        return HOUSE_COOL
    if fold in _HEAT_STATES:
        return HOUSE_HEAT
    return None


def resolve_house_mode(
    switch_state: str | None,
    climate_modes: list[str] | None = None,
) -> str:
    """House-wide heat/cool. The owner switch wins over live climate modes."""
    from_switch = house_mode_from_state(switch_state)
    if from_switch:
        return from_switch
    on_modes = [
        str(mode).casefold()
        for mode in climate_modes or []
        if climate_is_on(str(mode))
    ]
    heat = any(mode == HOUSE_HEAT for mode in on_modes)
    cool = any(mode == HOUSE_COOL for mode in on_modes)
    if heat and not cool:
        return HOUSE_HEAT
    if cool and not heat:
        return HOUSE_COOL
    return HOUSE_COOL


def house_mode_label(mode: str) -> str:
    """French title shown on the guest web app."""
    return "Chauffage" if mode == HOUSE_HEAT else "Climatisation"


def climate_activity(
    *,
    on: bool,
    house_mode: str,
    measured: float | None,
    setpoint: float | None,
) -> str:
    """Whether this room is actively heating, cooling, or idle.

    Red on the web app: heating and setpoint > measured.
    Blue: cooling and setpoint < measured.
    Otherwise idle (neutral).
    """
    if not on:
        return "off"
    if measured is None or setpoint is None:
        return "idle"
    if house_mode == HOUSE_HEAT and setpoint > measured:
        return "heating"
    if house_mode == HOUSE_COOL and setpoint < measured:
        return "cooling"
    return "idle"


def pick_hvac_on(available: list[str], preferred: str | None = None) -> str:
    """Choose a non-off HVAC mode when the guest turns the unit on."""
    by_fold = {mode.casefold(): mode for mode in available if mode}
    if preferred:
        fold = preferred.casefold()
        if fold not in _OFF_HVAC and fold in by_fold:
            return by_fold[fold]
    for candidate in _HVAC_ON_ORDER:
        if candidate in by_fold:
            return by_fold[candidate]
    for mode in available:
        if mode and mode.casefold() not in _OFF_HVAC:
            return mode
    return "heat"


GUEST_KIND_CLIMATE = "climate"
GUEST_KIND_LOCK = "lock"
GUEST_KIND_ALARM = "alarm"
GUEST_KIND_LIGHT = "light"
GUEST_KIND_SCENE = "scene"
GUEST_KIND_GARAGE = "garage"
GUEST_KIND_GATE = "gate"
GUEST_KIND_SHUTTER = "shutter"
GUEST_KIND_OUTDOOR = "outdoor"
GUEST_KIND_POOL_TEMP = "pool_temp"
GUEST_KIND_POOL_PH = "pool_ph"
GUEST_KIND_POOL_LIGHT = "pool_light"
GUEST_KIND_CHARGER = "charger"
GUEST_KIND_DOORBELL = "doorbell"
GUEST_KIND_CAMERA = "camera"
GUEST_KIND_SPEAKER = "speaker"
TYDOM_DOMAIN = "deltadore_tydom"
TYDOM_SET_MODE = "set_mode_using_stored_pin"

_POOL_NEEDLES = ("piscine", "pool", "bassin")
_CHARGER_NEEDLES = (
    "borne",
    "evlink",
    "evse",
    "wallbox",
    "recharge",
    "charger",
    "ocpp",
    "véhicule",
    "vehicule",
    "voiture",
)
_DOORBELL_NEEDLES = (
    "sonnette",
    "visiophone",
    "doorbell",
    "interphone",
    "portier",
    "linea 3000",
    "300eos",
    "classe 300",
)
_TV_CLASSES = ("tv", "receiver")
_CHARGING_STATES = ("charging", "charge", "en_charge", "en charge")
_PLUGGED_STATES = (
    "preparing",
    "suspendedev",
    "suspendedevse",
    "finishing",
    "connected",
    "plugged",
    "ready",
    "occupied",
    "b1",
    "b2",
)
_FAULT_STATES = ("faulted", "fault", "error")
_IDLE_STATES = ("off", "false", "available", "idle", "a1", "a2", "unavailable")
_RINGING_STATES = ("on", "true", "ringing", "pressed", "detected", "1")
_OUTDOOR_NEEDLES = (
    "extérieur",
    "exterieur",
    "outdoor",
    "outside",
    "jardin",
    "terrasse",
    "meteo",
    "météo",
    "weather",
)
_GARAGE_NEEDLES = ("garage",)
_GATE_NEEDLES = ("portail", "portal", "gate", "portillon")
_LIGHT_NEEDLES = ("lumière", "lumiere", "light", "eclairage", "éclairage")
_PH_NEEDLES = ("ph", "p.h")
_TEMP_UNITS = ("°c", "°f", "c", "f", "celsius", "fahrenheit")


def _fold_name(*parts: str | None) -> str:
    return " ".join(str(part or "") for part in parts).casefold()


def _has_needle(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def classify_guest_entity(
    entity_id: str,
    *,
    device_class: str | None = None,
    name: str | None = None,
    unit: str | None = None,
) -> str | None:
    """How the guest web app should present one allowed entity."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else entity_id
    label = _fold_name(entity_id, name)
    klass = str(device_class or "").casefold()
    measure = str(unit or "").casefold().replace(" ", "")
    if domain == "climate":
        return GUEST_KIND_CLIMATE
    if domain == "lock":
        return GUEST_KIND_LOCK
    if domain == "alarm_control_panel":
        return GUEST_KIND_ALARM
    if domain == "camera":
        return GUEST_KIND_CAMERA
    if domain == "media_player":
        if klass in _TV_CLASSES:
            return None
        return GUEST_KIND_SPEAKER
    if domain == "light":
        if _has_needle(label, _POOL_NEEDLES):
            return GUEST_KIND_POOL_LIGHT
        return GUEST_KIND_LIGHT
    if domain in {"scene", "script"}:
        return GUEST_KIND_SCENE
    if domain == "cover":
        if klass in {"garage", "garage_door"} or _has_needle(label, _GARAGE_NEEDLES):
            return GUEST_KIND_GARAGE
        if klass == "gate" or _has_needle(label, _GATE_NEEDLES):
            return GUEST_KIND_GATE
        return GUEST_KIND_SHUTTER
    if domain == "switch":
        if _has_needle(label, _POOL_NEEDLES):
            return GUEST_KIND_POOL_LIGHT
        if _has_needle(label, _GARAGE_NEEDLES):
            return GUEST_KIND_GARAGE
        if _has_needle(label, _GATE_NEEDLES):
            return GUEST_KIND_GATE
        if _has_needle(label, _LIGHT_NEEDLES):
            return GUEST_KIND_LIGHT
        return None
    if domain == "weather":
        return GUEST_KIND_OUTDOOR
    if domain == "binary_sensor":
        if klass == "doorbell" or _has_needle(label, _DOORBELL_NEEDLES):
            return GUEST_KIND_DOORBELL
        if klass == "battery_charging" or _has_needle(label, _CHARGER_NEEDLES):
            return GUEST_KIND_CHARGER
        return None
    if domain == "event":
        if klass == "doorbell" or _has_needle(label, _DOORBELL_NEEDLES):
            return GUEST_KIND_DOORBELL
        return None
    if domain == "sensor":
        if (
            klass in {"ph", "volatile_acid"}
            or measure == "ph"
            or _has_needle(label, _PH_NEEDLES)
        ):
            return GUEST_KIND_POOL_PH
        is_temp = klass == "temperature" or measure in _TEMP_UNITS
        if is_temp:
            if _has_needle(label, _POOL_NEEDLES):
                return GUEST_KIND_POOL_TEMP
            if _has_needle(label, _OUTDOOR_NEEDLES):
                return GUEST_KIND_OUTDOOR
            return None
        if _has_needle(label, _CHARGER_NEEDLES):
            return GUEST_KIND_CHARGER
        return None
    return None


def speaker_view_state(raw: str | None) -> str:
    """playing / paused / idle for a Sonos Amp or other media_player."""
    fold = str(raw or "").casefold().strip()
    if fold in {"playing", "buffering"}:
        return "playing"
    if fold == "paused":
        return "paused"
    return "idle"


def charger_view_state(
    raw: str | None, *, unit: str | None = None
) -> str:
    """idle / plugged / charging / fault for a wallbox entity."""
    fold = str(raw or "").casefold().strip()
    measure = str(unit or "").casefold().replace(" ", "")
    if fold in _FAULT_STATES:
        return "fault"
    if fold in _CHARGING_STATES or fold in {"on", "true", "c2", "d2"}:
        return "charging"
    if fold in _PLUGGED_STATES:
        return "plugged"
    if fold in _IDLE_STATES:
        return "idle"
    number: float | None
    try:
        number = float(fold.replace(",", "."))
    except ValueError:
        number = None
    if number is not None:
        if measure in {"w", "kw"}:
            watts = number * 1000 if measure == "kw" else number
            return "charging" if watts >= 50 else "idle"
        if measure == "a":
            return "charging" if number >= 1 else "idle"
        if number in {8, 9}:
            return "charging"
        if number in {3, 4, 5, 7}:
            return "plugged"
        if number in {0, 1, 2, 6}:
            return "idle"
    return "idle"


def doorbell_is_ringing(raw: str | None, now: datetime | None = None) -> bool:
    """True while a doorbell binary sensor is on, or a last-ring event is fresh."""
    fold = str(raw or "").casefold().strip()
    if fold in _RINGING_STATES:
        return True
    if fold in {"off", "false", "idle", "unknown", "unavailable", "0", "none"}:
        return False
    stamped = parse_iso(raw, None if now is None else now.tzinfo)
    if stamped is None:
        return False
    if now is None:
        now = datetime.now(stamped.tzinfo or timezone.utc)
    if now.tzinfo is None and stamped.tzinfo is not None:
        now = now.replace(tzinfo=stamped.tzinfo)
    return abs((now - stamped).total_seconds()) < 45


def guest_alarm_service(
    action: str, entity_id: str, *, has_tydom: bool, code: str | None
) -> tuple[str, str, dict[str, Any]]:
    """Domain, service and data to arm or disarm from the Maison app.

    A Tydom 2 box (HACS Delta Dore Tydom) keeps the PIN on the integration
    and exposes ``set_mode_using_stored_pin``. Other panels use the stock
    Home Assistant alarm services and the code stored in Usvegliu options.
    """
    if action not in {"arm", "disarm"}:
        raise ValueError("bad_action")
    if has_tydom:
        return (
            TYDOM_DOMAIN,
            TYDOM_SET_MODE,
            {
                "entity_id": entity_id,
                "mode": "away" if action == "arm" else "disarm",
            },
        )
    data: dict[str, Any] = {"entity_id": entity_id}
    if code:
        data["code"] = code
    service = "alarm_arm_away" if action == "arm" else "alarm_disarm"
    return "alarm_control_panel", service, data


def alarm_view_state(raw: str | None) -> str:
    """Collapse Home Assistant alarm states for the guest UI."""
    fold = str(raw or "").casefold()
    if fold == "disarmed":
        return "disarmed"
    if fold == "triggered":
        return "triggered"
    if fold in {"pending", "arming", "armed_away_pending"}:
        return "pending"
    if fold.startswith("armed"):
        return "armed"
    return "disarmed"


def cover_is_open(state: str | None) -> bool:
    fold = str(state or "").casefold()
    return fold in {"open", "opening", "on"}


def cover_is_moving(state: str | None) -> bool:
    return str(state or "").casefold() in {"opening", "closing"}


def guest_path(token: str) -> str:
    """Path served by this integration (local HA test URL)."""
    return f"/{DOMAIN}/s/{token}"


def public_guest_url(base_url: str | None, token: str) -> str:
    """Public locataire URL. ``base_url`` is the vitrine origin, without /s."""
    path = guest_path(token)
    origin = (base_url or "").strip().rstrip("/")
    if not origin:
        return path
    if origin.endswith("/s"):
        return f"{origin}/{token}"
    return f"{origin}/s/{token}"
