"""Idempotent voucher and account synchronization."""

from datetime import date, datetime, timezone

import pytest

from custom_components.usvegliu.engine import async_synchronize
from custom_components.usvegliu.planning import build_plan, normalize_event
from custom_components.usvegliu.unifi import UnifiError

UTC = timezone.utc


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

    async def async_ensure_user(self, **kwargs: object) -> dict[str, str | None]:
        user_id = kwargs.get("user_id")
        rotate = bool(kwargs.get("rotate"))
        if user_id and user_id in self.users and not rotate:
            return {
                "user_id": str(user_id),
                "username": str(kwargs["username"]),
                "password": None,
            }
        self.created += 1
        uid = str(user_id or f"user-{self.created}")
        password = f"pw-{self.created}"
        self.users[uid] = password
        return {"user_id": uid, "username": str(kwargs["username"]), "password": password}

    async def async_revoke_user(self, user_id: str) -> None:
        self.revoked.append(user_id)
        self.users.pop(user_id, None)


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
    now = datetime(2026, 7, 8, tzinfo=UTC)
    plan = _plan(now)
    first = await async_synchronize(
        plan,
        {},
        None,
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
    plan = _plan(datetime(2026, 7, 8, tzinfo=UTC))
    result = await async_synchronize(
        plan,
        {},
        None,
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
    now = datetime(2026, 7, 8, tzinfo=UTC)
    plan = _plan(now)
    created = await async_synchronize(
        plan,
        {},
        None,
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
    now = datetime(2026, 7, 8, tzinfo=UTC)
    original = _plan(now)
    created = await async_synchronize(
        original,
        {},
        None,
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
    now = datetime(2026, 7, 8, tzinfo=UTC)
    plan = _plan(now)
    created = await async_synchronize(
        plan,
        {},
        None,
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
    plan = _plan(datetime(2026, 7, 8, tzinfo=UTC))
    created = await async_synchronize(
        plan,
        {},
        None,
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
    plan = _plan(datetime(2026, 7, 8, tzinfo=UTC))
    key = plan.ensure[0].key
    first = await async_synchronize(
        plan,
        {},
        None,
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
    plan = _plan(datetime(2026, 7, 8, tzinfo=UTC))
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
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
    plan = _plan(datetime(2026, 7, 8, tzinfo=UTC))
    key = plan.ensure[0].key
    created = await async_synchronize(
        plan,
        {},
        None,
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
    )
    revoked = await async_synchronize(
        plan,
        created.stays,
        None,
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
        vouchers=unifi,
        accounts=None,
        enable_vouchers=True,
        enable_access=False,
        force_voucher_keys={key},
    )
    assert restored.stays[key].get("voucher_revoked") is None
    assert restored.stays[key]["voucher_code"] == "CODE2"
