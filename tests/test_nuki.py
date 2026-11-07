"""Keypad PIN rules and Nuki payload parsing."""

from datetime import datetime, timezone

from custom_components.usvegliu.nuki import (
    AUTH_TYPE_KEYPAD,
    extract_auths,
    generate_nuki_pin,
    is_valid_nuki_pin,
    keypad_auth_name,
    nuki_datetime,
)


def test_generated_pins_follow_keypad_rules():
    seen: set[str] = set()
    for _ in range(80):
        pin = generate_nuki_pin(seen)
        assert is_valid_nuki_pin(pin)
        assert "0" not in pin
        assert not pin.startswith("12")
        seen.add(pin)
    blocked = generate_nuki_pin({"111111", "222222"})
    assert blocked not in {"111111", "222222"}
    assert is_valid_nuki_pin(blocked)


def test_invalid_pins_are_rejected():
    assert not is_valid_nuki_pin("123456")
    assert not is_valid_nuki_pin("120345")
    assert not is_valid_nuki_pin("12345")
    assert not is_valid_nuki_pin("1234567")
    assert not is_valid_nuki_pin("123450")
    assert not is_valid_nuki_pin("abcdef")
    assert is_valid_nuki_pin("345678")


def test_auth_name_is_short_and_stable():
    first = keypad_auth_name("Jean Dupont", "airbnb-1|2026-07-10")
    second = keypad_auth_name("Jean Dupont", "airbnb-1|2026-07-10")
    other = keypad_auth_name("Ada Lovelace", "airbnb-1|2026-07-10")
    assert first == second
    assert first != other
    assert len(first) <= 20
    assert " " in first


def test_extract_auths_keeps_keypad_codes_only():
    auths = extract_auths(
        [
            {"id": "app-1", "name": "Owner", "type": 0},
            {"id": "pad-1", "name": "Jean 1a2b3c4d", "type": AUTH_TYPE_KEYPAD, "code": 345678},
            {"id": "pad-2", "name": "Ada", "type": 13, "code": "987654"},
            {"name": "no-id", "type": 13, "code": "345678"},
        ]
    )
    assert [auth.id for auth in auths] == ["pad-1", "pad-2"]
    assert auths[0].code == "345678"
    assert auths[1].name == "Ada"


def test_nuki_datetime_is_utc_millis():
    stamp = datetime(2026, 7, 10, 8, 30, tzinfo=timezone.utc)
    assert nuki_datetime(stamp) == "2026-07-10T08:30:00.000Z"
