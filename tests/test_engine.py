"""Idempotent voucher and account synchronization."""

from datetime import date, datetime, timezone

import pytest

from custom_components.usvegliu.engine import async_synchronize
from custom_components.usvegliu.nuki import NukiError, is_valid_nuki_pin
from custom_components.usvegliu.planning import build_plan, normalize_event
from custom_components.usvegliu.unifi import UnifiError

UTC = timezone.utc
LEAD = datetime(2026, 7, 8, tzinfo=UTC)
ARRIVAL = datetime(2026, 7, 10, tzinfo=UTC)
AFTER_CHECKOUT = datetime(2026, 7, 18, 12, tzinfo=UTC)
WIFI_GONE = datetime(2026, 7, 19, 0, 1, tzinfo=UTC)


class _Voucher:
    def __init__(self, voucher_id: str, code: str, name: str) -> None:
        self.id = voucher_id
        self.code = code
        self.name = name


class FakeUnifi:
    def __init__(self) -> None:
        self.vouchers: list[_Voucher] = []
        self.created = 0
        self.deleted: list[str] = []
        self.fail = False

    async def async_list_vouchers(self) -> list[_Voucher]:
        if self.fail:
            raise UnifiError("cannot_connect")
        return list(self.vouchers)

    async def async_create_voucher(self, **kwargs: object) -> _Voucher:
        self.created += 1
        voucher = _Voucher(f"id-{self.created}", f"CODE{self.created}", str(kwargs["name"]))
        self.vouchers.append(voucher)
        return voucher

    async def async_delete_voucher(self, voucher_id: str) -> None:
        self.deleted.append(voucher_id)
        self.vouchers = [voucher for voucher in self.vouchers if voucher.id != voucher_id]


class FakeAccounts:
    def __init__(self) -> None:
        self.created = 0
        self.revoked: list[str] = []
        self.users: dict[str, str] = {}
        self.active: dict[str, bool] = {}

    async def async_ensure_user(self, **kwargs: object) -> dict[str, str | None]:
        user_id = kwargs.get("user_id")
        rotate = bool(kwargs.get("rotate"))
        is_active = bool(kwargs.get("is_active", True))
        if user_id and user_id in self.users and not rotate:
            self.active[str(user_id)] = is_active
            return {
                "user_id": str(user_id),
                "username": str(kwargs["username"]),
                "password": None,
            }
        self.created += 1
        uid = str(user_id or f"user-{self.created}")
        password = f"pw-{self.created}"
        self.users[uid] = password
        self.active[uid] = is_active
        return {"user_id": uid, "username": str(kwargs["username"]), "password": password}

    async def async_revoke_user(self, user_id: str) -> None:
        self.revoked.append(user_id)
        self.users.pop(user_id, None)


class _Auth:
    def __init__(self, auth_id: str, name: str, code: str) -> None:
        self.id = auth_id
        self.name = name
        self.code = code


class FakeKeypad:
    def __init__(self) -> None:
        self.auths: list[_Auth] = []
        self.created = 0
        self.deleted: list[str] = []
        self.fail_create = False
        self.fail_delete = False
        self.fail_list = False

    async def async_list_codes(self) -> list[_Auth]:
        if self.fail_list:
            raise NukiError("nuki unreachable")
        return list(self.auths)

    async def async_create_code(self, **kwargs: object) -> _Auth:
        if self.fail_create:
            raise NukiError("nuki down")
        self.created += 1
        auth = _Auth(f"nuki-{self.created}", str(kwargs["name"]), str(kwargs["code"]))
        self.auths.append(auth)
        return auth

    async def async_delete_code(self, auth_id: str) -> None:
        if self.fail_delete:
            raise NukiError("nuki down")
        self.deleted.append(auth_id)
        self.auths = [auth for auth in self.auths if auth.id != auth_id]


def _plan(now: datetime, stays: list | None = None, known: list[str] | None = None):
    if stays is None:
        stay = normalize_event(
            summary="Jean Dupont",
            start=date(2026, 7, 10),
            end=date(2026, 7, 17),
            uid="airbnb-1",
            tz=UTC,
        )
        assert stay is not None
        stays = [stay]
    return build_plan(stays, now=now, lead_days=3, known_keys=known or [])


@pytest.mark.asyncio
async def test_second_cycle_does_not_duplicate_voucher_or_account():
    unifi = FakeUnifi()
    accounts = FakeAccounts()
    now = ARRIVAL
    plan = _plan(now)
    first = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert unifi.created == 1
    assert accounts.created == 1
    assert first.stays[plan.ensure[0].key]["voucher_code"] == "CODE1"
    assert first.events[0]["code_masque"] == "…E1"
    assert "CODE1" not in str(first.events)
    for event in first.events:
        assert "password" not in event
        assert "pw-" not in str(event.values())

    second = await async_synchronize(
        plan,
        first.stays,
        first.shared_user,
        now=now,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert unifi.created == 1
    assert accounts.created == 1
    assert unifi.deleted == []
    assert second.stays[plan.ensure[0].key]["voucher_id"] == "id-1"
    token = first.stays[plan.ensure[0].key]["guest_token"]
    assert len(token) >= 16
    assert second.stays[plan.ensure[0].key]["guest_token"] == token
    assert second.notifications == []
    assert "pw-" not in str(first.journal)
    assert "pw-" not in str(second.journal)
    assert first.notifications[0]["password"].startswith("pw-")
    key = plan.ensure[0].key
    assert first.stays[key]["password"] == "pw-1"
    assert second.stays[key]["password"] == "pw-1"


@pytest.mark.asyncio
async def test_existing_voucher_with_the_same_name_is_adopted():
    unifi = FakeUnifi()
    name = "Jean Dupont 2026-07-10/2026-07-17"
    unifi.vouchers.append(_Voucher("already", "KEEPME", name))
    unifi.vouchers.append(_Voucher("dup", "DROPME", name))
    now = ARRIVAL
    plan = _plan(now)
    result = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    assert unifi.created == 0
    assert "dup" in unifi.deleted
    assert result.stays[plan.ensure[0].key]["voucher_id"] == "already"
    assert result.stays[plan.ensure[0].key]["voucher_code"] == "KEEPME"


@pytest.mark.asyncio
async def test_cancellation_deletes_voucher_and_user_once():
    unifi = FakeUnifi()
    accounts = FakeAccounts()
    now = ARRIVAL
    plan = _plan(now)
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    key = plan.ensure[0].key
    cancelled = _plan(now, stays=[], known=[key])
    removed = await async_synchronize(
        cancelled,
        created.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert unifi.deleted == ["id-1"]
    assert accounts.revoked == ["user-1"]
    assert removed.stays == {}

    again = await async_synchronize(
        cancelled,
        removed.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert unifi.deleted == ["id-1"]
    assert accounts.revoked == ["user-1"]
    assert again.journal == []


@pytest.mark.asyncio
async def test_shortened_stay_replaces_the_voucher():
    unifi = FakeUnifi()
    now = ARRIVAL
    original = _plan(now)
    created = await async_synchronize(
        original,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    shortened_stay = normalize_event(
        summary="Jean Dupont",
        start=date(2026, 7, 10),
        end=date(2026, 7, 12),
        uid="airbnb-1",
        tz=UTC,
    )
    assert shortened_stay is not None
    updated = build_plan(
        [shortened_stay],
        now=now,
        lead_days=3,
        known_keys=[shortened_stay.key],
    )
    result = await async_synchronize(
        updated,
        created.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    assert unifi.created == 2
    assert "id-1" in unifi.deleted
    record = result.stays[shortened_stay.key]
    assert record["voucher_code"] == "CODE2"
    assert "2026-07-12" in record["voucher_name"]
    assert any(row["action"] == "voucher_cree" for row in result.journal)


@pytest.mark.asyncio
async def test_controller_outage_does_not_revoke():
    unifi = FakeUnifi()
    now = ARRIVAL
    plan = _plan(now)
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    unifi.fail = True
    with pytest.raises(UnifiError):
        await async_synchronize(
            _plan(now, known=[plan.ensure[0].key]),
            created.stays,
            None,
            now=now,
        vouchers=unifi,
            accounts=None,
            enable_vouchers=True,
            enable_access=False,
        )
    assert unifi.deleted == []
    assert len(unifi.vouchers) == 1


@pytest.mark.asyncio
async def test_regenerate_issues_a_new_code():
    unifi = FakeUnifi()
    now = ARRIVAL
    plan = _plan(now)
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    key = plan.ensure[0].key
    again = await async_synchronize(
        plan,
        created.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
        force_voucher_keys={key},
    )
    assert again.stays[key]["voucher_code"] == "CODE2"
    assert any(row["action"] == "voucher_regenere" for row in again.journal)
    assert again.print_events == []


@pytest.mark.asyncio
async def test_remote_access_and_entity_override_reach_the_account():
    class Recording(FakeAccounts):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[dict] = []

        async def async_ensure_user(self, **kwargs: object) -> dict[str, str | None]:
            self.calls.append(dict(kwargs))
            return await super().async_ensure_user(**kwargs)

    accounts = Recording()
    now = ARRIVAL
    plan = _plan(now)
    key = plan.ensure[0].key
    first = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
        allow_remote=True,
        entity_ids=["light.salon"],
        device_ids=["dev-1"],
    )
    assert accounts.calls[-1]["local_only"] is False
    assert accounts.calls[-1]["entity_ids"] == ["light.salon"]
    assert accounts.calls[-1]["device_ids"] == ["dev-1"]
    second = await async_synchronize(
        plan,
        first.stays,
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
        allow_remote=True,
        entity_ids=["light.salon"],
        device_ids=["dev-1"],
        overrides={key: {"entity_ids": ["cover.x"], "allow_remote": False}},
    )
    assert accounts.calls[-1]["local_only"] is True
    assert accounts.calls[-1]["entity_ids"] == ["cover.x"]
    assert accounts.calls[-1]["device_ids"] == []
    assert "pw-" not in str(second.journal)


@pytest.mark.asyncio
async def test_revoke_access_holds_until_regenerate():
    accounts = FakeAccounts()
    now = ARRIVAL
    plan = _plan(now)
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
    )
    assert created.stays[key]["password"] == "pw-1"
    revoked = await async_synchronize(
        plan,
        created.stays,
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
        force_revoke_access_keys={key},
    )
    assert revoked.stays[key].get("access_revoked") is True
    assert revoked.stays[key].get("user_id") is None
    assert revoked.stays[key].get("password") is None
    assert accounts.revoked == ["user-1"]
    held = await async_synchronize(
        plan,
        revoked.stays,
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
    )
    assert held.stays[key].get("access_revoked") is True
    assert accounts.created == 1
    restored = await async_synchronize(
        plan,
        held.stays,
        None,
        now=now,
        vouchers=None,
        accounts=accounts,
        enable_vouchers=False,
        enable_access=True,
        force_rotate_keys={key},
    )
    assert restored.stays[key].get("access_revoked") is None
    assert restored.stays[key]["password"] == "pw-2"


@pytest.mark.asyncio
async def test_revoke_voucher_holds_until_regenerate():
    unifi = FakeUnifi()
    now = ARRIVAL
    plan = _plan(now)
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    revoked = await async_synchronize(
        plan,
        created.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
        force_revoke_voucher_keys={key},
    )
    assert revoked.stays[key].get("voucher_revoked") is True
    assert revoked.stays[key].get("voucher_code") is None
    assert unifi.deleted == ["id-1"]
    held = await async_synchronize(
        plan,
        revoked.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    assert held.stays[key].get("voucher_revoked") is True
    assert unifi.created == 1
    restored = await async_synchronize(
        plan,
        held.stays,
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
        force_voucher_keys={key},
    )
    assert restored.stays[key].get("voucher_revoked") is None
    assert restored.stays[key]["voucher_code"] == "CODE2"


@pytest.mark.asyncio
async def test_voucher_is_ready_in_the_lead_window_login_waits():
    unifi = FakeUnifi()
    accounts = FakeAccounts()
    lead_plan = _plan(LEAD)
    held = await async_synchronize(
        lead_plan,
        {},
        None,
        now=LEAD,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    key = lead_plan.ensure[0].key
    assert unifi.created == 1
    assert held.stays[key]["voucher_code"] == "CODE1"
    assert len(held.stays[key]["guest_token"]) >= 16
    assert accounts.created == 1
    uid = str(held.stays[key]["user_id"])
    assert accounts.active[uid] is False

    live = await async_synchronize(
        _plan(ARRIVAL, known=[key]),
        held.stays,
        None,
        now=ARRIVAL,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert unifi.created == 1
    assert live.stays[key]["voucher_code"] == "CODE1"
    assert accounts.created == 1
    assert accounts.active[uid] is True

    leftover = await async_synchronize(
        _plan(AFTER_CHECKOUT, known=[key]),
        live.stays,
        None,
        now=AFTER_CHECKOUT,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert leftover.stays[key]["voucher_code"] == "CODE1"
    assert accounts.active[uid] is False
    assert unifi.created == 1

    gone = await async_synchronize(
        _plan(WIFI_GONE, known=[key]),
        leftover.stays,
        None,
        now=WIFI_GONE,
        vouchers=unifi,
        accounts=accounts,
        enable_vouchers=True,
        enable_access=True,
    )
    assert gone.stays == {}
    assert uid in accounts.revoked
    assert unifi.deleted == ["id-1"]


@pytest.mark.asyncio
async def test_nuki_pin_is_created_in_lead_window_and_revoked_at_maison_close():
    unifi = FakeUnifi()
    keypad = FakeKeypad()
    lead_plan = _plan(LEAD)
    key = lead_plan.ensure[0].key
    first = await async_synchronize(
        lead_plan,
        {},
        None,
        now=LEAD,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    pin = first.stays[key]["nuki_code"]
    assert keypad.created == 1
    assert is_valid_nuki_pin(pin)
    assert pin not in str(first.journal)
    assert pin not in str(first.events)
    assert first.notifications[0]["nuki_code"] == pin
    assert first.journal[0]["code"] == "CODE1"
    assert all(row.get("code") != pin for row in first.journal)

    second = await async_synchronize(
        lead_plan,
        first.stays,
        None,
        now=LEAD,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    assert keypad.created == 1
    assert second.stays[key]["nuki_code"] == pin
    assert second.notifications == []

    leftover = await async_synchronize(
        _plan(AFTER_CHECKOUT, known=[key]),
        second.stays,
        None,
        now=AFTER_CHECKOUT,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    assert leftover.stays[key]["voucher_code"] == "CODE1"
    assert leftover.stays[key].get("nuki_code") is None
    assert keypad.deleted == ["nuki-1"]

    gone = await async_synchronize(
        _plan(WIFI_GONE, known=[key]),
        leftover.stays,
        None,
        now=WIFI_GONE,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    assert gone.stays == {}
    assert unifi.deleted == ["id-1"]


@pytest.mark.asyncio
async def test_nuki_revoke_holds_until_regenerate():
    keypad = FakeKeypad()
    now = ARRIVAL
    plan = _plan(now)
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=None,
        accounts=None,
        keypad=keypad,
        enable_vouchers=False,
        enable_access=False,
        enable_nuki=True,
    )
    pin = created.stays[key]["nuki_code"]
    revoked = await async_synchronize(
        plan,
        created.stays,
        None,
        now=now,
        vouchers=None,
        accounts=None,
        keypad=keypad,
        enable_vouchers=False,
        enable_access=False,
        enable_nuki=True,
        force_revoke_nuki_keys={key},
    )
    assert revoked.stays[key].get("nuki_revoked") is True
    assert revoked.stays[key].get("nuki_code") is None
    assert keypad.deleted == ["nuki-1"]
    held = await async_synchronize(
        plan,
        revoked.stays,
        None,
        now=now,
        vouchers=None,
        accounts=None,
        keypad=keypad,
        enable_vouchers=False,
        enable_access=False,
        enable_nuki=True,
    )
    assert held.stays[key].get("nuki_revoked") is True
    assert keypad.created == 1
    restored = await async_synchronize(
        plan,
        held.stays,
        None,
        now=now,
        vouchers=None,
        accounts=None,
        keypad=keypad,
        enable_vouchers=False,
        enable_access=False,
        enable_nuki=True,
        force_nuki_keys={key},
    )
    assert restored.stays[key].get("nuki_revoked") is None
    assert restored.stays[key]["nuki_code"] != pin
    assert is_valid_nuki_pin(restored.stays[key]["nuki_code"])
    assert keypad.created == 2


@pytest.mark.asyncio
async def test_nuki_failure_does_not_block_unifi():
    unifi = FakeUnifi()
    keypad = FakeKeypad()
    keypad.fail_create = True
    now = ARRIVAL
    plan = _plan(now)
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
        now=now,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    assert unifi.created == 1
    assert created.stays[key]["voucher_code"] == "CODE1"
    assert created.stays[key].get("nuki_code") is None

    keypad.fail_create = False
    keypad.fail_delete = True
    created.stays[key]["nuki_auth_id"] = "nuki-leftover"
    created.stays[key]["nuki_code"] = "345678"
    gone = await async_synchronize(
        _plan(WIFI_GONE, known=[key]),
        created.stays,
        None,
        now=WIFI_GONE,
        vouchers=unifi,
        accounts=None,
        keypad=keypad,
        enable_vouchers=True,
        enable_access=False,
        enable_nuki=True,
    )
    assert gone.stays == {}
    assert unifi.deleted == ["id-1"]
