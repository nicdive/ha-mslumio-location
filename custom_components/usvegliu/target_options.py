"""Normalize the Options Target picker into entity/device id lists."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .const import (
    CONF_CLIMATE_ENTITIES,
    CONF_COVER_ENTITIES,
    CONF_LIGHT_ENTITIES,
    CONF_TENANT_DEVICES,
    CONF_TENANT_ENTITIES,
    CONF_TENANT_TARGET,
    TENANT_BULK_DOMAINS,
)


def as_id_list(value: Any) -> list[str]:
    """Normalize a selector value to a list of non-empty ids."""
    if value is None or value is False:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
        return out
    return []


def merge_unique(existing: Iterable[str], extra: Iterable[str]) -> list[str]:
    """Append new ids while keeping order and uniqueness."""
    out: list[str] = []
    seen: set[str] = set()
    for item in list(existing) + list(extra):
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def entity_ids_for_domains(hass: Any, domains: Iterable[str]) -> list[str]:
    """List live entity ids for the chosen domains (enabled only)."""
    wanted = {
        str(domain or "").strip()
        for domain in domains
        if str(domain or "").strip() in TENANT_BULK_DOMAINS
    }
    if not wanted or hass is None:
        return []
    found: list[str] = []
    seen: set[str] = set()
    try:
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        for entry in registry.entities.values():
            entity_id = entry.entity_id
            domain = entity_id.split(".", 1)[0]
            if domain not in wanted or entry.disabled:
                continue
            if entity_id not in seen:
                seen.add(entity_id)
                found.append(entity_id)
    except Exception:  # noqa: BLE001 — registry optional in tests
        pass
    if found:
        return sorted(found)
    if not hasattr(hass, "states"):
        return []
    for domain in sorted(wanted):
        try:
            for entity_id in hass.states.async_entity_ids(domain):
                if entity_id not in seen:
                    seen.add(entity_id)
                    found.append(entity_id)
        except Exception:  # noqa: BLE001
            continue
    return sorted(found)


def default_entities(defaults: Mapping[str, Any]) -> list[str]:
    """Keep a previous climate/cover/light selection visible after the upgrade."""
    selected = as_id_list(defaults.get(CONF_TENANT_ENTITIES))
    if selected:
        return selected
    legacy: list[str] = []
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        legacy.extend(as_id_list(defaults.get(key)))
    return legacy


def tenant_target_default(defaults: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the Target selector value from stored entity/device lists."""
    if isinstance(defaults.get(CONF_TENANT_TARGET), Mapping):
        return dict(defaults[CONF_TENANT_TARGET])
    out: dict[str, Any] = {}
    entities = default_entities(defaults)
    devices = as_id_list(defaults.get(CONF_TENANT_DEVICES))
    if entities:
        out["entity_id"] = entities
    if devices:
        out["device_id"] = devices
    return out


def expand_tenant_target(
    hass: Any, target: Mapping[str, Any] | None
) -> tuple[list[str], list[str]]:
    """Turn a Target selector payload into entity ids + device ids."""
    target = target or {}
    entities = as_id_list(target.get("entity_id"))
    devices = as_id_list(target.get("device_id"))
    areas = as_id_list(target.get("area_id"))
    if not areas or hass is None:
        return entities, devices
    try:
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er
    except ImportError:
        return entities, devices
    area_set = set(areas)
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    device_areas = {
        entry.id: entry.area_id
        for entry in device_reg.devices.values()
        if entry.area_id
    }
    seen_e = set(entities)
    for entry in entity_reg.entities.values():
        area_id = entry.area_id or device_areas.get(entry.device_id or "")
        if area_id not in area_set:
            continue
        if entry.entity_id not in seen_e:
            seen_e.add(entry.entity_id)
            entities.append(entry.entity_id)
    return entities, devices
