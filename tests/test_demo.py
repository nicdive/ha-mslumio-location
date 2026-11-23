"""Guest web app demo villa (switch, no Home Assistant entities)."""

from custom_components.usvegliu.demo import (
    DEMO_NUKI,
    DEMO_VOUCHER,
    apply_demo_climate,
    apply_demo_command,
    build_demo_villa,
    demo_entity_ids,
    demo_entity_kind,
    is_demo_entity,
    overlay_demo_snapshot,
)


def test_demo_villa_covers_the_guest_app():
    villa = build_demo_villa("cool")
    assert len(villa["climates"]) == 10
    assert {room["name"] for room in villa["climates"]} >= {
        "Salon",
        "Cuisine",
        "Suite",
        "Terrasse",
        "Spa",
    }
    cooling = [room for room in villa["climates"] if room["activity"] == "cooling"]
    assert len(cooling) >= 3
    assert villa["chargers"][0]["state"] == "charging"
    assert villa["chargers"][0]["level"] == 64
    assert villa["locks"][0]["locked"] is True
    assert villa["speakers"][0]["state"] == "playing"
    assert any(item["kind"] == "pool_temp" for item in villa["metrics"])
    assert all(is_demo_entity(entity_id) for entity_id in demo_entity_ids(villa))
    assert demo_entity_kind(villa, villa["climates"][0]["entity_id"]) == "climate"
    assert demo_entity_kind(villa, villa["pool_lights"][0]["entity_id"]) == "pool_light"


def test_demo_commands_mutate_the_villa():
    villa = build_demo_villa("cool")
    room = villa["climates"][0]
    updated = apply_demo_climate(
        villa,
        room["entity_id"],
        {"on": True, "setpoint": 22, "fan": 3},
        house_mode="cool",
    )
    assert updated is not None
    assert updated["setpoint"] == 22
    assert updated["fan"] == 3
    assert updated["activity"] == "cooling"
    lock = apply_demo_command(villa, villa["locks"][0]["entity_id"], "lock", "unlock")
    assert lock is not None and lock["locked"] is False
    light = apply_demo_command(villa, villa["lights"][0]["entity_id"], "light", "toggle")
    assert light is not None and light["on"] is False
    speaker = apply_demo_command(
        villa, villa["speakers"][0]["entity_id"], "speaker", "volume", 10
    )
    assert speaker is not None and speaker["volume"] == 10


def test_overlay_replaces_empty_equipment_and_keeps_the_stay():
    villa = build_demo_villa("cool")
    payload = overlay_demo_snapshot(
        {
            "guest": "Ada",
            "preview": True,
            "informations": {"wifi_ssid": "Usvegliu-Guest"},
            "climates": [],
            "chargers": [],
            "weather": None,
        },
        villa,
        house_mode="cool",
    )
    assert payload["demo"] is True
    assert payload["guest"] == "Ada"
    assert len(payload["climates"]) == 10
    assert payload["chargers"][0]["state"] == "charging"
    assert payload["informations"]["voucher_code"] == DEMO_VOUCHER
    assert payload["informations"]["nuki_code"] == DEMO_NUKI
    assert payload["weather"]["place"] == "Lumio"
    assert payload["mode_label"] == "Climatisation"
