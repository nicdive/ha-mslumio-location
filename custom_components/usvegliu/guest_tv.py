"""Fixed guest TV ↔ Apple TV pairings (Pulse-Eight neo as backbone).

Control4 can still free-route sources on the matrix. Maison never does:
each guest TV is locked to one Apple TV in Usvegliu options. When the
guest opens that TV, we force the neo route (output ← ATV input) then
drive the Apple TV ``media_player`` / ``remote``.
"""

from __future__ import annotations

from typing import Any, Mapping

GUEST_TV_SLOTS = 4


def guest_tv_name_key(slot: int) -> str:
    return f"guest_tv_{slot}_name"


def guest_tv_atv_key(slot: int) -> str:
    return f"guest_tv_{slot}_atv"


def guest_tv_neo_output_key(slot: int) -> str:
    return f"guest_tv_{slot}_neo_output"


def guest_tv_neo_input_key(slot: int) -> str:
    return f"guest_tv_{slot}_neo_input"


def guest_tv_option_keys() -> tuple[str, ...]:
    keys: list[str] = []
    for slot in range(1, GUEST_TV_SLOTS + 1):
        keys.extend(
            (
                guest_tv_name_key(slot),
                guest_tv_atv_key(slot),
                guest_tv_neo_output_key(slot),
                guest_tv_neo_input_key(slot),
            )
        )
    return tuple(keys)


def parse_guest_tv_mappings(options: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return configured guest TVs (slot order). Empty slots are skipped."""
    opts = options or {}
    mapped: list[dict[str, Any]] = []
    for slot in range(1, GUEST_TV_SLOTS + 1):
        atv = str(opts.get(guest_tv_atv_key(slot)) or "").strip()
        if not atv:
            continue
        name = str(opts.get(guest_tv_name_key(slot)) or "").strip()
        neo_output = str(opts.get(guest_tv_neo_output_key(slot)) or "").strip()
        neo_input = str(opts.get(guest_tv_neo_input_key(slot)) or "").strip()
        mapped.append(
            {
                "slot": slot,
                "name": name,
                "atv_entity_id": atv,
                "neo_output": neo_output or None,
                "neo_input": neo_input or None,
            }
        )
    return mapped


def mapping_for_atv(
    mappings: list[dict[str, Any]], entity_id: str
) -> dict[str, Any] | None:
    fold = str(entity_id or "").strip()
    for item in mappings:
        if item.get("atv_entity_id") == fold:
            return item
    return None


async def async_ensure_neo_route(hass: Any, mapping: Mapping[str, Any] | None) -> None:
    """Force Pulse-Eight output ← fixed ATV input. No-op when unset."""
    if not mapping:
        return
    output_id = str(mapping.get("neo_output") or "").strip()
    input_id = str(mapping.get("neo_input") or "").strip()
    if not output_id or not input_id:
        return
    if hass.services.has_service("pulse_eight", "set_route"):
        await hass.services.async_call(
            "pulse_eight",
            "set_route",
            {"output": output_id, "input": input_id},
            blocking=True,
        )
        return
    # Fallback when the Pulse-Eight integration is absent: select_source by name.
    source = _neo_source_label(hass, input_id)
    if not source:
        return
    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": output_id, "source": source},
        blocking=True,
    )


def _neo_source_label(hass: Any, input_id: str) -> str | None:
    state = hass.states.get(input_id)
    if state is None:
        return None
    name = str(state.attributes.get("friendly_name") or "").strip()
    if name:
        return name
    if "." in input_id:
        return input_id.split(".", 1)[1].replace("_", " ")
    return None
