"""Dedicated Lovelace dashboard for tenants.

Home Assistant does not expose the dashboard collection on ``hass.data``.
The live collection is the one registered on the websocket command
``lovelace/dashboards/create``. Using a second collection would overwrite
``.storage/lovelace_dashboards`` with a stale copy, so this module refuses
to create a dashboard when that live collection cannot be found.
"""

from __future__ import annotations

from typing import Any

from .const import DASHBOARD_ICON, DASHBOARD_TITLE, DASHBOARD_URL


def build_dashboard_config(
    climate: list[str],
    covers: list[str],
    lights: list[str],
) -> dict[str, Any]:
    """Return a storage-mode Lovelace config limited to the selected entities."""
    cards: list[dict[str, Any]] = [
        {
            "type": "markdown",
            "content": (
                "Bienvenue. Ce tableau permet de régler le chauffage, "
                "les volets et l'éclairage du séjour."
            ),
        }
    ]
    for entity_id in climate:
        cards.append({"type": "thermostat", "entity": entity_id})
    if covers:
        cards.append({"type": "entities", "title": "Volets", "entities": list(covers)})
    if lights:
        cards.append(
            {"type": "entities", "title": "Éclairage", "entities": list(lights)}
        )
    return {
        "views": [
            {
                "title": DASHBOARD_TITLE,
                "path": "sejour",
                "icon": DASHBOARD_ICON,
                "cards": cards,
            }
        ]
    }


def find_dashboard_collection(hass: object):
    """Return the live Lovelace dashboard collection, or None."""
    data = getattr(hass, "data", None)
    if not isinstance(data, dict):
        return None
    handlers = data.get("websocket_api")
    if not isinstance(handlers, dict):
        return None
    entry = handlers.get("lovelace/dashboards/create")
    if not isinstance(entry, tuple) or not entry:
        return None
    owner = getattr(entry[0], "__self__", None)
    return getattr(owner, "storage_collection", None)


async def async_ensure_dashboard(
    hass: object,
    *,
    climate: list[str],
    covers: list[str],
    lights: list[str],
) -> bool:
    """Create ``ms-lumio`` if needed and save its cards. False if Lovelace is unavailable."""
    collection = find_dashboard_collection(hass)
    if collection is None:
        return False
    config = build_dashboard_config(climate, covers, lights)
    existing = None
    for item in collection.async_items():
        if item.get("url_path") == DASHBOARD_URL:
            existing = item
            break
    if existing is None:
        existing = await collection.async_create_item(
            {
                "url_path": DASHBOARD_URL,
                "title": DASHBOARD_TITLE,
                "icon": DASHBOARD_ICON,
                "require_admin": False,
                "show_in_sidebar": True,
                "mode": "storage",
            }
        )
    elif existing.get("require_admin"):
        await collection.async_update_item(
            existing["id"],
            {"require_admin": False, "show_in_sidebar": True},
        )
    data = getattr(hass, "data", {})
    lovelace = data.get("lovelace")
    dashboard = None
    if lovelace is not None:
        dashboard = getattr(lovelace, "dashboards", {}).get(DASHBOARD_URL)
    if dashboard is None:
        return False
    await dashboard.async_save(config)
    return True
