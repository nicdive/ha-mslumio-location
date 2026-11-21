"""Guest-facing brand themes (U Svegliu vs 49 Ledbury).

One codebase, two HA instances. The theme only changes copy, logos and
CSS tokens in the Maison web app — UniFi / Cambium / stays stay shared.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from .const import (
    CONF_GUEST_THEME,
    DEFAULT_GUEST_THEME,
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
    },
    THEME_LEDBURY: {
        "id": THEME_LEDBURY,
        "name": "49 Ledbury",
        "tagline": "Notting Hill",
        "place": "Notting Hill",
        "team": "The 49 Ledbury team",
        "welcome_house": "49 Ledbury",
        "logo": "/usvegliu/static/logo-ledbury.png",
        "banner": "/usvegliu/static/logo-banner-ledbury.png",
        "theme_color": "#E8EEE6",
        "wifi_ssid_default": "49Ledbury-Guest",
    },
}


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
    return guest_brand(options.get(CONF_GUEST_THEME) or DEFAULT_GUEST_THEME)


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
    "CONF_GUEST_THEME",
    "DEFAULT_GUEST_THEME",
    "THEME_LEDBURY",
    "THEME_USVEGLIU",
    "brand_from_options",
    "guest_brand",
    "normalize_guest_theme",
    "unifi_configured",
)
