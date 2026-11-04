"""Dedicated Lovelace dashboard for tenants.

Home Assistant 2026 stores Lovelace under a HassKey, not ``hass.data["lovelace"]``.
Cards are written on the live ``LovelaceStorage`` for ``usvegliu-sejour`` when
that dashboard already exists. The dashboard collection is only used to create
the sidebar entry if it is missing.
"""

from __future__ import annotations

import logging
from typing import Any

from .const import DASHBOARD_ICON, DASHBOARD_TITLE, DASHBOARD_URL

_LOGGER = logging.getLogger(__name__)


def build_dashboard_config(entity_ids: list[str]) -> dict[str, Any]:
    """Return a sections-view Lovelace config limited to the selected entities."""
    climate = [entity for entity in entity_ids if entity.startswith("climate.")]
    covers = [entity for entity in entity_ids if entity.startswith("cover.")]
    lights = [entity for entity in entity_ids if entity.startswith("light.")]
    others = [
        entity
        for entity in entity_ids
        if entity not in climate and entity not in covers and entity not in lights
    ]
    cards: list[dict[str, Any]] = [
        {
            "type": "markdown",
            "content": (
                "Bienvenue. Ce tableau montre uniquement les équipements "
                "autorisés pour le séjour."
            ),
        }
    ]
    for entity_id in climate:
        cards.append({"type": "thermostat", "entity": entity_id})
    if covers:
        cards.append({"type": "entities", "title": "Volets", "entities": covers})
    if lights:
        cards.append({"type": "entities", "title": "Éclairage", "entities": lights})
    if others:
        cards.append({"type": "entities", "title": "Équipements", "entities": others})
    return {
        "views": [
            {
                "type": "sections",
                "title": DASHBOARD_TITLE,
                "path": "sejour",
                "icon": DASHBOARD_ICON,
                "max_columns": 2,
                "sections": [{"type": "grid", "cards": cards}],
            }
        ]
    }


def dashboard_card_count(config: dict[str, Any]) -> int:
    """How many cards the config will show."""
    views = config.get("views") or []
    if not views:
        return 0
    view = views[0]
    cards = list(view.get("cards") or [])
    for section in view.get("sections") or []:
        cards.extend(section.get("cards") or [])
    return len(cards)


def _lovelace_bundle(hass: object) -> Any:
    data = getattr(hass, "data", None)
    if data is None:
        return None
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        bundle = data.get(LOVELACE_DATA)
        if bundle is not None:
            return bundle
    except Exception:  # noqa: BLE001 — HA is optional in unit tests
        pass
    getter = getattr(data, "get", None)
    if callable(getter):
        return getter("lovelace")
    return None


def _dashboard_map(hass: object) -> dict[Any, Any]:
    bundle = _lovelace_bundle(hass)
    if bundle is None:
        return {}
    dashboards = getattr(bundle, "dashboards", None)
    if isinstance(dashboards, dict):
        return dashboards
    if isinstance(bundle, dict):
        inner = bundle.get("dashboards")
        if isinstance(inner, dict):
            return inner
    return {}


def find_dashboard_collection(hass: object):
    """Return the live Lovelace dashboard collection, or None."""
    data = getattr(hass, "data", None)
    if data is None:
        return None
    handlers = None
    getter = getattr(data, "get", None)
    if callable(getter):
        handlers = getter("websocket_api")
    if isinstance(handlers, dict):
        entry = handlers.get("lovelace/dashboards/create")
        owner = None
        if isinstance(entry, tuple) and entry:
            owner = getattr(entry[0], "__self__", None)
        elif entry is not None:
            owner = getattr(entry, "__self__", None)
        collection = getattr(owner, "storage_collection", None)
        if collection is not None:
            return collection
    bundle = _lovelace_bundle(hass)
    for name in ("dashboards_collection", "storage_collection"):
        collection = getattr(bundle, name, None)
        if collection is not None:
            return collection
    return None


async def async_ensure_dashboard(hass: object, entity_ids: list[str]) -> dict[str, Any]:
    """Create ``usvegliu-sejour`` if needed and save its cards."""
    config = build_dashboard_config(entity_ids)
    cards = dashboard_card_count(config)
    dashboards = _dashboard_map(hass)
    dashboard = dashboards.get(DASHBOARD_URL)
    collection = find_dashboard_collection(hass)

    if dashboard is None and collection is not None:
        existing = None
        items = getattr(collection, "async_items", None)
        for item in items() if callable(items) else []:
            if item.get("url_path") == DASHBOARD_URL:
                existing = item
                break
        if existing is None:
            try:
                await collection.async_create_item(
                    {
                        "url_path": DASHBOARD_URL,
                        "title": DASHBOARD_TITLE,
                        "icon": DASHBOARD_ICON,
                        "require_admin": False,
                        "show_in_sidebar": True,
                        "mode": "storage",
                    }
                )
            except Exception:  # noqa: BLE001 — already exists or API drift
                _LOGGER.debug("Création du tableau %s ignorée", DASHBOARD_URL, exc_info=True)
        elif existing.get("require_admin"):
            await collection.async_update_item(
                existing["id"],
                {"require_admin": False, "show_in_sidebar": True},
            )
        dashboards = _dashboard_map(hass)
        dashboard = dashboards.get(DASHBOARD_URL)

    if dashboard is None:
        _LOGGER.warning(
            "Tableau %s introuvable : cartes non écrites (%s entités)",
            DASHBOARD_URL,
            len(entity_ids),
        )
        return {
            "ok": False,
            "url": DASHBOARD_URL,
            "cards": cards,
            "entities": list(entity_ids),
            "reason": "dashboard_missing",
        }

    saver = getattr(dashboard, "async_save", None)
    if not callable(saver):
        return {
            "ok": False,
            "url": DASHBOARD_URL,
            "cards": cards,
            "entities": list(entity_ids),
            "reason": "save_unavailable",
        }
    await saver(config)
    return {
        "ok": True,
        "url": DASHBOARD_URL,
        "cards": cards,
        "entities": list(entity_ids),
        "reason": "saved",
    }
