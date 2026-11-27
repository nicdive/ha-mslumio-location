"""Stable LAN tablet URL — always on, greeting follows the stay."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.usvegliu.branding import safe_manifest_start
from custom_components.usvegliu.guest_session import (
    HOUSE_KEY,
    house_path,
    ip_is_lan,
    select_active_stay,
)


def test_house_path_and_manifest():
    token = "tablet-token-abcdefghijklmnopqrst"
    assert house_path(token) == f"/usvegliu/house/{token}"
    assert (
        safe_manifest_start(f"/usvegliu/house/{token}", token=token)
        == f"/usvegliu/house/{token}"
    )
    assert (
        safe_manifest_start("/usvegliu/static/", token=token).endswith(f"/s/{token}")
        or safe_manifest_start("/usvegliu/static/", token=token)
        == f"/usvegliu/s/{token}"
    )


def test_ip_is_lan_ranges():
    assert ip_is_lan("127.0.0.1")
    assert ip_is_lan("192.168.1.20")
    assert ip_is_lan("10.0.0.5")
    assert ip_is_lan("::1")
    assert not ip_is_lan("8.8.8.8")
    assert not ip_is_lan("home.49ledbury.com")


def test_select_active_stay_prefers_current_window():
    now = datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc)
    stays = {
        "a": {
            "key": "a",
            "guest": "Ada",
            "check_in": "2026-11-20T00:00:00+00:00",
            "check_out": "2026-11-25T00:00:00+00:00",
        },
        "b": {
            "key": "b",
            "guest": "Bob",
            "check_in": "2026-12-01T00:00:00+00:00",
            "check_out": "2026-12-05T00:00:00+00:00",
        },
    }
    current = select_active_stay(stays, now)
    assert current is not None
    assert current["guest"] == "Ada"
    assert select_active_stay(stays, datetime(2026, 11, 26, 12, tzinfo=timezone.utc)) is None


def test_house_key_constant():
    assert HOUSE_KEY.startswith("__usvegliu_")
