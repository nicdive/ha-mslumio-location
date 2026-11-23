"""Guest-facing brand themes (U Svegliu vs 49 Ledbury).

One codebase, two HA instances. The theme only changes copy, logos and
CSS tokens in the Maison web app — UniFi / Cambium / stays stay shared.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from .const import (
    CONF_GUEST_LOCALE,
    CONF_GUEST_THEME,
    DEFAULT_GUEST_THEME,
    LOCALE_EN,
    LOCALE_FR,
    THEME_LEDBURY,
    THEME_USVEGLIU,
)

_THEMES: Final[dict[str, dict[str, str]]] = {
    THEME_USVEGLIU: {
        "id": THEME_USVEGLIU,
        "name": "U Svegliu",
        "tagline": "Villa Lumio, Corse",
        "place": "Lumio",
        "team": "L'équipe Usvegliu",
        "welcome_house": "Usvegliu",
        "logo": "/usvegliu/static/logo.png",
        "banner": "/usvegliu/static/logo-banner.png",
        "theme_color": "#F1EBE2",
        "wifi_ssid_default": "Usvegliu-Guest",
        "locale": "fr",
        # Fan-coil / soufflante speeds in Maison.
        "climate_fans": "1",
        "climate_heat_only": "0",
        "weather_place": "lumio",
    },
    THEME_LEDBURY: {
        "id": THEME_LEDBURY,
        "name": "49 Ledbury",
        "tagline": "Notting Hill · Portobello",
        "place": "London",
        "team": "The 49 Ledbury team",
        "welcome_house": "49 Ledbury",
        "logo": "/usvegliu/static/logo-ledbury.png",
        "banner": "/usvegliu/static/logo-banner-ledbury.png",
        "theme_color": "#E8F4EE",
        "wifi_ssid_default": "49Ledbury-Guest",
        "locale": "en",
        # Underfloor heating + radiators — no blower UI.
        "climate_fans": "0",
        "climate_heat_only": "1",
        "weather_place": "london",
    },
}


def brand_locale(brand: Mapping[str, Any] | None) -> str:
    """Guest app language: fr (default) or en."""
    brand = brand or {}
    value = str(brand.get("locale") or "").strip().casefold()
    if value.startswith("en"):
        return LOCALE_EN
    return LOCALE_FR


def normalize_guest_locale(raw: object, *, theme: object = None) -> str:
    """Return fr or en; empty/unknown falls back to the theme default."""
    value = str(raw or "").strip().casefold()
    if value.startswith("en"):
        return LOCALE_EN
    if value.startswith("fr"):
        return LOCALE_FR
    return brand_locale(guest_brand(theme))


def brand_climate_fans(brand: Mapping[str, Any] | None) -> bool:
    """True when Maison should show fan / soufflante controls."""
    brand = brand or {}
    return str(brand.get("climate_fans") or "1").strip() not in {"0", "false", "no"}


def brand_heat_only(brand: Mapping[str, Any] | None) -> bool:
    """True when the house is heating-only (UFH / radiators)."""
    brand = brand or {}
    return str(brand.get("climate_heat_only") or "0").strip() in {"1", "true", "yes"}


def normalize_guest_theme(raw: object) -> str:
    """Return a known theme id; unknown values fall back to U Svegliu."""
    value = str(raw or "").strip().casefold()
    if value in {THEME_LEDBURY, "49ledbury", "ledbury", "49 ledbury"}:
        return THEME_LEDBURY
    return THEME_USVEGLIU


def guest_brand(theme: object = None) -> dict[str, str]:
    """Public brand payload for the guest app and welcome mail."""
    key = normalize_guest_theme(theme)
    return dict(_THEMES[key])


def brand_from_options(options: Mapping[str, Any] | None) -> dict[str, str]:
    """Resolve the brand from a config entry options mapping."""
    options = options or {}
    brand = guest_brand(options.get(CONF_GUEST_THEME) or DEFAULT_GUEST_THEME)
    brand["locale"] = normalize_guest_locale(
        options.get(CONF_GUEST_LOCALE), theme=brand["id"]
    )
    return brand


def unifi_configured(data: Mapping[str, Any] | None) -> bool:
    """True when this entry has a UniFi host and API key."""
    from .const import CONF_API_KEY, CONF_HOST

    data = data or {}
    return bool(
        str(data.get(CONF_HOST) or "").strip()
        and str(data.get(CONF_API_KEY) or "").strip()
    )

# Re-export for callers that import theme ids from this module.
__all__ = (
    "CONF_GUEST_LOCALE",
    "CONF_GUEST_THEME",
    "DEFAULT_GUEST_THEME",
    "LOCALE_EN",
    "LOCALE_FR",
    "THEME_LEDBURY",
    "THEME_USVEGLIU",
    "brand_climate_fans",
    "brand_from_options",
    "brand_heat_only",
    "brand_locale",
    "guest_brand",
    "normalize_guest_locale",
    "normalize_guest_theme",
    "unifi_configured",
)
