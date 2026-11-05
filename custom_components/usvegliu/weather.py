"""Lumio daily weather for the guest home screen.

Open-Meteo, no key. The guest app only sees the already-mapped snapshot.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

LUMIO_LAT = 42.578
LUMIO_LON = 8.834
LUMIO_NAME = "Lumio"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TTL = timedelta(minutes=20)

# WMO weather interpretation codes → icon + French label.
_WMO: dict[int, tuple[str, str]] = {
    0: ("sun", "Ensoleillé"),
    1: ("sun_cloud", "Peu nuageux"),
    2: ("sun_cloud", "Partiellement nuageux"),
    3: ("cloud", "Couvert"),
    45: ("fog", "Brouillard"),
    48: ("fog", "Brouillard givrant"),
    51: ("drizzle", "Bruine"),
    53: ("drizzle", "Bruine"),
    55: ("drizzle", "Bruine"),
    56: ("drizzle", "Bruine verglaçante"),
    57: ("drizzle", "Bruine verglaçante"),
    61: ("rain", "Pluie"),
    63: ("rain", "Pluie"),
    65: ("rain", "Forte pluie"),
    66: ("rain", "Pluie verglaçante"),
    67: ("rain", "Pluie verglaçante"),
    71: ("snow", "Neige"),
    73: ("snow", "Neige"),
    75: ("snow", "Forte neige"),
    77: ("snow", "Grains de neige"),
    80: ("rain", "Averses"),
    81: ("rain", "Averses"),
    82: ("rain", "Fortes averses"),
    85: ("snow", "Averses de neige"),
    86: ("snow", "Averses de neige"),
    95: ("storm", "Orage"),
    96: ("storm", "Orage et grêle"),
    99: ("storm", "Orage et grêle"),
}


def weather_look(code: int | None) -> tuple[str, str]:
    """Return (icon, French label) for a WMO code."""
    if code is None:
        return ("cloud", "Lumio")
    if code in _WMO:
        return _WMO[code]
    if 50 <= code <= 59:
        return ("drizzle", "Bruine")
    if 60 <= code <= 69:
        return ("rain", "Pluie")
    if 70 <= code <= 79:
        return ("snow", "Neige")
    if 80 <= code <= 84:
        return ("rain", "Averses")
    if 95 <= code <= 99:
        return ("storm", "Orage")
    return ("cloud", "Couvert")


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


def parse_open_meteo(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Map an Open-Meteo forecast body to the guest snapshot."""
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    code = _as_int(current.get("weather_code"))
    if code is None:
        codes = daily.get("weather_code") or []
        code = _as_int(codes[0]) if codes else None
    icon, label = weather_look(code)
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    temperature = _as_float(current.get("temperature_2m"))
    if temperature is None and highs:
        temperature = _as_float(highs[0])
    if temperature is None:
        return None
    return {
        "place": LUMIO_NAME,
        "label": label,
        "icon": icon,
        "code": code,
        "temperature": round(temperature),
        "high": _as_int(highs[0]) if highs else None,
        "low": _as_int(lows[0]) if lows else None,
        "wind": _as_int(current.get("wind_speed_10m")),
    }


def open_meteo_params() -> dict[str, str]:
    """Query string for today's Lumio forecast."""
    return {
        "latitude": str(LUMIO_LAT),
        "longitude": str(LUMIO_LON),
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Paris",
        "forecast_days": "1",
    }


async def async_fetch_lumio_weather(session: Any) -> dict[str, Any] | None:
    """GET Open-Meteo. Returns None on any network or parse error."""
    try:
        async with session.get(
            OPEN_METEO_URL,
            params=open_meteo_params(),
            timeout=8,
        ) as response:
            if response.status != 200:
                return None
            payload = await response.json(content_type=None)
    except Exception:  # noqa: BLE001 — weather must never break the stay API
        return None
    if not isinstance(payload, dict):
        return None
    return parse_open_meteo(payload)


def weather_is_fresh(fetched_at: datetime | None, now: datetime) -> bool:
    """True when the cache is still good."""
    if fetched_at is None:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now - fetched_at < WEATHER_TTL
