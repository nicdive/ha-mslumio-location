"""Fixed guest TV ↔ Apple TV mappings (Pulse-Eight route)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from custom_components.usvegliu.guest_tv import (
    async_ensure_neo_route,
    mapping_for_atv,
    parse_guest_tv_mappings,
)


def test_parse_guest_tv_mappings_skips_empty_slots():
    options = {
        "guest_tv_1_name": "Living",
        "guest_tv_1_atv": "media_player.living_atv",
        "guest_tv_1_neo_output": "media_player.output_living",
        "guest_tv_1_neo_input": "media_player.input_atv_1",
        "guest_tv_2_atv": "",
        "guest_tv_3_name": "Kitchen",
        "guest_tv_3_atv": "media_player.kitchen_atv",
    }
    mapped = parse_guest_tv_mappings(options)
    assert len(mapped) == 2
    assert mapped[0]["slot"] == 1
    assert mapped[0]["name"] == "Living"
    assert mapped[0]["neo_output"] == "media_player.output_living"
    assert mapped[1]["slot"] == 3
    assert mapped[1]["neo_input"] is None
    assert mapping_for_atv(mapped, "media_player.kitchen_atv")["slot"] == 3
    assert mapping_for_atv(mapped, "media_player.other") is None


def test_async_ensure_neo_route_uses_pulse_eight_when_available():
    calls: list[tuple[Any, ...]] = []

    class Hass:
        class services:
            @staticmethod
            def has_service(domain, service):
                return domain == "pulse_eight" and service == "set_route"

            @staticmethod
            async def async_call(domain, service, data, blocking=False):
                calls.append((domain, service, data, blocking))

    mapping = {
        "neo_output": "media_player.output_living",
        "neo_input": "media_player.input_atv_1",
    }
    asyncio.run(async_ensure_neo_route(Hass(), mapping))
    assert calls == [
        (
            "pulse_eight",
            "set_route",
            {
                "output": "media_player.output_living",
                "input": "media_player.input_atv_1",
            },
            True,
        )
    ]


def test_async_ensure_neo_route_falls_back_to_select_source():
    calls: list[tuple[Any, ...]] = []

    class Hass:
        def __init__(self):
            self.states = SimpleNamespace(
                get=lambda entity_id: SimpleNamespace(
                    attributes={"friendly_name": "Apple TV 1"}
                )
            )

        class services:
            @staticmethod
            def has_service(domain, service):
                return False

            @staticmethod
            async def async_call(domain, service, data, blocking=False):
                calls.append((domain, service, data, blocking))

    hass = Hass()
    asyncio.run(
        async_ensure_neo_route(
            hass,
            {
                "neo_output": "media_player.output_living",
                "neo_input": "media_player.input_atv_1",
            },
        )
    )
    assert calls == [
        (
            "media_player",
            "select_source",
            {
                "entity_id": "media_player.output_living",
                "source": "Apple TV 1",
            },
            True,
        )
    ]


def test_async_ensure_neo_route_noop_without_ports():
    class Hass:
        class services:
            @staticmethod
            def has_service(*_a, **_k):
                raise AssertionError("should not run")

    asyncio.run(async_ensure_neo_route(Hass(), {"neo_output": None, "neo_input": None}))
    asyncio.run(async_ensure_neo_route(Hass(), None))
