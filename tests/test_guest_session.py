"""Guest stay tokens and climate fan/mode mapping."""

from datetime import datetime, timedelta, timezone

from custom_components.usvegliu.guest_session import (
    PREVIEW_KEY,
    build_preview_record,
    climate_is_on,
    ensure_guest_token,
    find_record_by_token,
    infer_fan_speed,
    map_fan_modes,
    pick_hvac_on,
    public_guest_url,
    stay_is_open,
)

UTC = timezone.utc


def test_token_is_kept_on_later_sync():
    record: dict = {}
    first = ensure_guest_token(record)
    second = ensure_guest_token(record)
    assert first == second
    assert len(first) >= 16


def test_stay_open_until_checkout_including_before_arrival():
    now = datetime(2026, 7, 1, 10, tzinfo=UTC)
    record = {
        "check_in": "2026-07-10T00:00:00+00:00",
        "check_out": "2026-07-17T00:00:00+00:00",
        "guest_token": "a" * 24,
    }
    assert stay_is_open(record, now) is True
    assert stay_is_open(record, datetime(2026, 7, 17, 0, tzinfo=UTC)) is False


def test_find_token_prefers_live_stay_over_expired_preview():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    token = "T" * 24
    stays = {
        "a": {
            "guest_token": token,
            "check_in": "2026-07-10T00:00:00+00:00",
            "check_out": "2026-07-17T00:00:00+00:00",
        }
    }
    preview = {
        "guest_token": token,
        "check_out": "2026-07-01T00:00:00+00:00",
        "preview": True,
    }
    found = find_record_by_token(stays, preview, token, now)
    assert found is stays["a"]


def test_expired_preview_is_rejected():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    preview = build_preview_record(now - timedelta(hours=30), hours=24)
    assert find_record_by_token({}, preview, preview["guest_token"], now) is None
    assert preview["key"] == PREVIEW_KEY


def test_fan_mapping_mh8_style():
    mapping = map_fan_modes(["auto", "low", "medium", "high"])
    assert mapping == {1: "low", 2: "medium", 3: "high"}
    assert infer_fan_speed("medium", mapping) == 2


def test_fan_mapping_numeric_and_partial():
    mapping = map_fan_modes(["1", "3"])
    assert mapping[1] == "1"
    assert mapping[3] == "3"


def test_hvac_helpers():
    assert climate_is_on("heat") is True
    assert climate_is_on("off") is False
    assert pick_hvac_on(["off", "cool", "heat"], None) == "heat"
    assert pick_hvac_on(["off", "fan_only"], "fan_only") == "fan_only"


def test_public_url_uses_s_path():
    assert public_guest_url("https://www.usvegliu.fr", "Ab3") == (
        "https://www.usvegliu.fr/s/Ab3"
    )
    assert public_guest_url("", "Ab3") == "/usvegliu/s/Ab3"
