"""Guest home-screen weather via Open-Meteo (no API key).

U Svegliu → Lumio (French labels). 49 Ledbury → London (English).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Final

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TTL = timedelta(minutes=20)

_PLACES: Final[dict[str, dict[str, Any]]] = {
    "lumio": {
        "lat": 42.578,
        "lon": 8.834,
        "name_fr": "Lumio",
        "name_en": "Lumio",
        "timezone": "Europe/Paris",
    },
    "london": {
        # Notting Hill / Portobello — shown as London in Maison.
        "lat": 51.5165,
        "lon": -0.2005,
        "name_fr": "Londres",
        "name_en": "London",
        "timezone": "Europe/London",
    },
}

# WMO weather interpretation codes → icon + (fr, en) labels.
_WMO: dict[int, tuple[str, str, str]] = {
    0: ("sun", "Ensoleillé", "Sunny"),
    1: ("sun_cloud", "Peu nuageux", "Mostly clear"),
    2: ("sun_cloud", "Partiellement nuageux", "Partly cloudy"),
    3: ("cloud", "Couvert", "Overcast"),
    45: ("fog", "Brouillard", "Fog"),
    48: ("fog", "Brouillard givrant", "Rime fog"),
    51: ("drizzle", "Bruine", "Drizzle"),
    53: ("drizzle", "Bruine", "Drizzle"),
    55: ("drizzle", "Bruine", "Drizzle"),
    56: ("drizzle", "Bruine verglaçante", "Freezing drizzle"),
    57: ("drizzle", "Bruine verglaçante", "Freezing drizzle"),
    61: ("rain", "Pluie", "Rain"),
    63: ("rain", "Pluie", "Rain"),
    65: ("rain", "Forte pluie", "Heavy rain"),
    66: ("rain", "Pluie verglaçante", "Freezing rain"),
    67: ("rain", "Pluie verglaçante", "Freezing rain"),
    71: ("snow", "Neige", "Snow"),
    73: ("snow", "Neige", "Snow"),
    75: ("snow", "Forte neige", "Heavy snow"),
    77: ("snow", "Grains de neige", "Snow grains"),
    80: ("rain", "Averses", "Showers"),
    81: ("rain", "Averses", "Showers"),
    82: ("rain", "Fortes averses", "Heavy showers"),
    85: ("snow", "Averses de neige", "Snow showers"),
    86: ("snow", "Averses de neige", "Snow showers"),
    95: ("storm", "Orage", "Thunderstorm"),
    96: ("storm", "Orage et grêle", "Thunderstorm"),
    99: ("storm", "Orage et grêle", "Thunderstorm"),
}

# Back-compat aliases used by older callers / tests.
LUMIO_LAT = _PLACES["lumio"]["lat"]
LUMIO_LON = _PLACES["lumio"]["lon"]
LUMIO_NAME = _PLACES["lumio"]["name_fr"]


def normalize_weather_place(raw: object) -> str:
    """Known place id; unknown values fall back to Lumio."""
    value = str(raw or "").strip().casefold().replace(" ", "_").replace("-", "_")
    if value in {
        "london",
        "londres",
        "notting_hill",
        "nottinghill",
        "ledbury",
        "portobello",
    }:
        return "london"
    return "lumio"


def weather_look(code: int | None, *, locale: str = "fr") -> tuple[str, str]:
    """Return (icon, label) for a WMO code."""
    english = str(locale or "fr").casefold().startswith("en")
    if code is None:
        return ("cloud", "Overcast" if english else "Couvert")

    def _pick(row: tuple[str, str, str]) -> tuple[str, str]:
        return (row[0], row[2] if english else row[1])

    if code in _WMO:
        return _pick(_WMO[code])
    if 50 <= code <= 59:
        return ("drizzle", "Drizzle" if english else "Bruine")
    if 60 <= code <= 69:
        return ("rain", "Rain" if english else "Pluie")
    if 70 <= code <= 79:
        return ("snow", "Snow" if english else "Neige")
    if 80 <= code <= 84:
        return ("rain", "Showers" if english else "Averses")
    if 95 <= code <= 99:
        return ("storm", "Thunderstorm" if english else "Orage")
    return ("cloud", "Overcast" if english else "Couvert")


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(round(number))


def parse_open_meteo(
    payload: dict[str, Any],
    *,
    place: str = "lumio",
    locale: str = "fr",
) -> dict[str, Any] | None:
    """Map an Open-Meteo forecast body to the guest snapshot."""
    place_id = normalize_weather_place(place)
    meta = _PLACES[place_id]
    english = str(locale or "fr").casefold().startswith("en")
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    code = _as_int(current.get("weather_code"))
    if code is None:
        codes = daily.get("weather_code") or []
        code = _as_int(codes[0]) if codes else None
    icon, label = weather_look(code, locale=locale)
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    temperature = _as_float(current.get("temperature_2m"))
    if temperature is None and highs:
        temperature = _as_float(highs[0])
    if temperature is None:
        return None
    return {
        "place": meta["name_en"] if english else meta["name_fr"],
        "label": label,
        "icon": icon,
        "code": code,
        "temperature": round(temperature),
        "high": _as_int(highs[0]) if highs else None,
        "low": _as_int(lows[0]) if lows else None,
        "wind": _as_int(current.get("wind_speed_10m")),
    }


def open_meteo_params(place: str = "lumio") -> dict[str, str]:
    """Query string for today's forecast at the house location."""
    meta = _PLACES[normalize_weather_place(place)]
    return {
        "latitude": str(meta["lat"]),
        "longitude": str(meta["lon"]),
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": str(meta["timezone"]),
        "forecast_days": "1",
    }


async def async_fetch_lumio_weather(session: Any) -> dict[str, Any] | None:
    """Back-compat: Lumio, French labels."""
    return await async_fetch_weather(session, place="lumio", locale="fr")


async def async_fetch_weather(
    session: Any,
    *,
    place: str = "lumio",
    locale: str = "fr",
) -> dict[str, Any] | None:
    """GET Open-Meteo. Returns None on any network or parse error."""
    try:
        async with session.get(
            OPEN_METEO_URL,
            params=open_meteo_params(place),
            timeout=8,
        ) as response:
            if response.status != 200:
                return None
            payload = await response.json(content_type=None)
    except Exception:  # noqa: BLE001 — weather must never break the stay API
        return None
    if not isinstance(payload, dict):
        return None
    return parse_open_meteo(payload, place=place, locale=locale)


def weather_is_fresh(fetched_at: datetime | None, now: datetime) -> bool:
    """True when the cache is still good."""
    if fetched_at is None:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now - fetched_at < WEATHER_TTL
