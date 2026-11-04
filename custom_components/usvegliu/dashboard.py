"""Dedicated Lovelace dashboard for tenants.

Home Assistant 2026 stores Lovelace under a HassKey, not ``hass.data["lovelace"]``.
Cards are written on the live ``LovelaceStorage`` for ``usvegliu-sejour`` when
that dashboard already exists. The dashboard collection is only used to create
the sidebar entry if it is missing.
"""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    ATTR_RESERVATION_KEY,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL,
    DOMAIN,
    OWNER_DASHBOARD_ICON,
    OWNER_DASHBOARD_TITLE,
    OWNER_DASHBOARD_URL,
    SERVICE_REGENERATE_ACCESS,
    SERVICE_REGENERATE_VOUCHER,
    SERVICE_REVOKE_ACCESS,
    SERVICE_REVOKE_VOUCHER,
)

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


def frontend_core_with_tenant_panel(existing: dict[str, Any] | None) -> dict[str, Any]:
    """User frontend data so login opens Séjour instead of Home."""
    core = dict(existing or {})
    core["default_panel"] = DASHBOARD_URL
    return core


async def async_set_tenant_default_panel(
    hass: object,
    user_id: str | None,
    *,
    load_store: Any | None = None,
) -> None:
    """Land a tenant on ``usvegliu-sejour`` after login.

    Home Assistant 2026 opens the Home dashboard. That view walks areas and
    can stay on « Chargement des données… » for a user who may only read a
    handful of entities.
    """
    if not user_id:
        return
    loader = load_store
    if loader is None:
        try:
            from homeassistant.components.frontend.storage import (
                async_user_store as loader,
            )
        except ImportError:
            return
    try:
        store = await loader(hass, user_id)
        core = frontend_core_with_tenant_panel(store.data.get("core"))
        if store.data.get("core") == core:
            return
        await store.async_set_item("core", core)
    except Exception:  # noqa: BLE001 — frontend storage is not worth aborting access
        _LOGGER.debug("Tableau par défaut locataire non enregistré", exc_info=True)


def _jinja_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _service_button(
    name: str,
    icon: str,
    service: str,
    reservation_id: str,
    confirm: str,
) -> dict[str, Any]:
    return {
        "type": "button",
        "name": name,
        "icon": icon,
        "show_icon": True,
        "show_name": True,
        "show_state": False,
        "tap_action": {
            "action": "call-service",
            "service": f"{DOMAIN}.{service}",
            "service_data": {ATTR_RESERVATION_KEY: reservation_id},
            "confirmation": {"text": confirm},
        },
    }


def _stay_markdown(entity_id: str, reservation_id: str) -> str:
    """Live Jinja: passwords stay on the sensor, not in the Lovelace file."""
    entity = _jinja_quote(entity_id)
    key = _jinja_quote(reservation_id)
    return (
        f"{{% set rows = state_attr('{entity}', 'stays') or [] %}}\n"
        f"{{% set found = rows | selectattr('reservation_id', 'equalto', '{key}') | list %}}\n"
        f"{{% set s = found[0] if found else none %}}\n"
        "{% if s %}\n"
        "{% set debut = (s.check_in or '')[:10] %}\n"
        "{% set fin = (s.check_out or '')[:10] %}\n"
        "**{{ debut }} → {{ fin }}**\n"
        "\n"
        "{% if s.essai %}\n"
        "Lien d'essai 24 h — pas de compte HA ni de voucher UniFi.\n"
        "\n"
        "{% if s.lien_maison %}[Ouvrir la maison]({{ s.lien_maison }}){% endif %}\n"
        "{% else %}\n"
        "{% if s.access_revoked %}\n"
        "Compte HA — *révoqué*\n"
        "\n"
        "{% else %}\n"
        "Compte HA\n"
        "`{{ s.username or '—' }}`\n"
        "`{{ s.password or '—' }}`\n"
        "\n"
        "{% endif %}\n"
        "{% if s.voucher_revoked %}\n"
        "Wi-Fi — *révoqué*\n"
        "\n"
        "{% else %}\n"
        "Wi-Fi\n"
        "`{{ s.voucher_code or '—' }}`\n"
        "\n"
        "{% endif %}\n"
        "{% if s.lien_maison %}[Maison]({{ s.lien_maison }}){% endif %}"
        " · [Tableau séjour](/"
        f"{DASHBOARD_URL})\n"
        "{% endif %}\n"
        "{% else %}\n"
        "Séjour clos ou pas encore provisionné.\n"
        "{% endif %}\n"
    )


def build_owner_dashboard_config(
    stays: list[dict[str, Any]],
    *,
    sejours_entity_id: str,
) -> dict[str, Any]:
    """Admin console: live credentials plus regenerate/revoke actions."""
    header = [
        {
            "type": "markdown",
            "content": (
                "# Console Usvegliu\n"
                "Identifiants des séjours encore ouverts. "
                "Chaque action demande confirmation."
            ),
        }
    ]
    if sejours_entity_id:
        header.append(
            {
                "type": "tile",
                "entity": sejours_entity_id,
                "name": "Séjours actifs",
                "icon": "mdi:account-group",
            }
        )
    sections: list[dict[str, Any]] = [
        {"type": "grid", "column_span": 2, "cards": header}
    ]
    if not stays:
        sections.append(
            {
                "type": "grid",
                "column_span": 2,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "Aucun séjour provisionné. Les accès apparaissent ici "
                            "dès qu'une réservation entre dans la fenêtre."
                        ),
                    }
                ],
            }
        )
    for stay in stays:
        reservation_id = str(stay.get("reservation_id") or stay.get("key") or "")
        guest = str(stay.get("guest") or "Séjour")
        cards: list[dict[str, Any]] = [
            {
                "type": "heading",
                "heading": guest,
                "heading_style": "title",
                "icon": "mdi:home-account",
            },
            {
                "type": "markdown",
                "content": _stay_markdown(sejours_entity_id, reservation_id),
            },
        ]
        if not stay.get("essai") and reservation_id:
            cards.append(
                {
                    "type": "grid",
                    "columns": 2,
                    "square": False,
                    "cards": [
                        _service_button(
                            "Nouveau mot de passe",
                            "mdi:account-key",
                            SERVICE_REGENERATE_ACCESS,
                            reservation_id,
                            f"Générer un nouveau mot de passe pour {guest} ?",
                        ),
                        _service_button(
                            "Révoquer le compte",
                            "mdi:account-off",
                            SERVICE_REVOKE_ACCESS,
                            reservation_id,
                            f"Révoquer le compte Home Assistant de {guest} ?",
                        ),
                        _service_button(
                            "Nouveau code Wi-Fi",
                            "mdi:wifi-sync",
                            SERVICE_REGENERATE_VOUCHER,
                            reservation_id,
                            f"Générer un nouveau code Wi-Fi pour {guest} ?",
                        ),
                        _service_button(
                            "Révoquer le Wi-Fi",
                            "mdi:wifi-off",
                            SERVICE_REVOKE_VOUCHER,
                            reservation_id,
                            f"Révoquer le voucher Wi-Fi de {guest} ?",
                        ),
                    ],
                }
            )
        sections.append({"type": "grid", "cards": cards})
    return {
        "views": [
            {
                "type": "sections",
                "title": OWNER_DASHBOARD_TITLE,
                "path": "console",
                "icon": OWNER_DASHBOARD_ICON,
                "max_columns": 2,
                "sections": sections,
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


async def _async_save_named_dashboard(
    hass: object,
    *,
    url: str,
    title: str,
    icon: str,
    require_admin: bool,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create a Lovelace storage dashboard if needed and save its cards."""
    cards = dashboard_card_count(config)
    dashboards = _dashboard_map(hass)
    dashboard = dashboards.get(url)
    collection = find_dashboard_collection(hass)

    if dashboard is None and collection is not None:
        existing = None
        items = getattr(collection, "async_items", None)
        for item in items() if callable(items) else []:
            if item.get("url_path") == url:
                existing = item
                break
        if existing is None:
            try:
                await collection.async_create_item(
                    {
                        "url_path": url,
                        "title": title,
                        "icon": icon,
                        "require_admin": require_admin,
                        "show_in_sidebar": True,
                        "mode": "storage",
                    }
                )
            except Exception:  # noqa: BLE001 — already exists or API drift
                _LOGGER.debug("Création du tableau %s ignorée", url, exc_info=True)
        elif (
            bool(existing.get("require_admin")) != bool(require_admin)
            or not existing.get("show_in_sidebar", True)
        ):
            try:
                await collection.async_update_item(
                    existing["id"],
                    {
                        "require_admin": require_admin,
                        "show_in_sidebar": True,
                    },
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Mise à jour du tableau %s ignorée", url, exc_info=True)
        dashboards = _dashboard_map(hass)
        dashboard = dashboards.get(url)

    if dashboard is None:
        _LOGGER.warning("Tableau %s introuvable : cartes non écrites", url)
        return {"ok": False, "url": url, "cards": cards, "reason": "dashboard_missing"}

    saver = getattr(dashboard, "async_save", None)
    if not callable(saver):
        return {"ok": False, "url": url, "cards": cards, "reason": "save_unavailable"}
    await saver(config)
    return {"ok": True, "url": url, "cards": cards, "reason": "saved"}


async def async_ensure_dashboard(hass: object, entity_ids: list[str]) -> dict[str, Any]:
    """Create ``usvegliu-sejour`` if needed and save its cards."""
    config = build_dashboard_config(entity_ids)
    result = await _async_save_named_dashboard(
        hass,
        url=DASHBOARD_URL,
        title=DASHBOARD_TITLE,
        icon=DASHBOARD_ICON,
        require_admin=False,
        config=config,
    )
    result["entities"] = list(entity_ids)
    return result


async def async_ensure_owner_dashboard(
    hass: object,
    stays: list[dict[str, Any]],
    *,
    sejours_entity_id: str,
) -> dict[str, Any]:
    """Create the admin console dashboard and save its cards."""
    config = build_owner_dashboard_config(stays, sejours_entity_id=sejours_entity_id)
    return await _async_save_named_dashboard(
        hass,
        url=OWNER_DASHBOARD_URL,
        title=OWNER_DASHBOARD_TITLE,
        icon=OWNER_DASHBOARD_ICON,
        require_admin=True,
        config=config,
    )
