"""Apply a sync plan to UniFi vouchers and tenant accounts.

The network and Home Assistant details sit behind small callables so this
module can be tested with fakes. A failed UniFi call aborts the cycle before
any revocation: an offline controller must not lock guests out or duplicate
vouchers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .planning import StayPlan, SyncPlan, VoucherSpec
from .redact import mask_code


class VoucherDirectory(Protocol):
    """The slice of the UniFi client the engine needs."""

    async def async_list_vouchers(self) -> list[Any]:
        """Return vouchers currently on the controller."""

    async def async_create_voucher(
        self,
        *,
        name: str,
        time_limit_minutes: int,
        authorized_guest_limit: int,
        rx_rate_limit_kbps: int,
        tx_rate_limit_kbps: int,
    ) -> Any:
        """Create one voucher."""

    async def async_delete_voucher(self, voucher_id: str) -> None:
        """Delete one voucher. Missing vouchers are not an error."""


class AccountDirectory(Protocol):
    """Tenant account operations."""

    async def async_ensure_user(
        self,
        *,
        username: str,
        display_name: str,
        user_id: str | None,
        password: str | None,
        rotate: bool,
    ) -> dict[str, str | None]:
        """Return user_id, username and password (password is None if unchanged)."""

    async def async_revoke_user(self, user_id: str) -> None:
        """Disable or delete a tenant. Must refuse admin accounts."""


@dataclass
class CycleResult:
    """Outcome of one synchronization cycle."""

    stays: dict[str, dict[str, Any]]
    shared_user: dict[str, Any] | None
    journal: list[dict[str, str]] = field(default_factory=list)
    notifications: list[dict[str, str]] = field(default_factory=list)
    events: list[dict[str, str]] = field(default_factory=list)
    print_events: list[dict[str, str]] = field(default_factory=list)
    created_vouchers: int = 0
    deleted_vouchers: int = 0


def _iso(value: Any) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _journal_row(
    action: str,
    stay: dict[str, Any] | None,
    *,
    detail: str = "",
    password: str = "",
) -> dict[str, str]:
    stay = stay or {}
    return {
        "action": action,
        "reservation_id": str(stay.get("key") or ""),
        "locataire": str(stay.get("guest") or ""),
        "debut": str(stay.get("check_in") or ""),
        "fin": str(stay.get("check_out") or ""),
        "voucher_id": str(stay.get("voucher_id") or ""),
        "code": str(stay.get("voucher_code") or ""),
        "utilisateur_ha": str(stay.get("username") or ""),
        "mot_de_passe": password,
        "detail": detail,
    }


def _event_from(action: str, stay: dict[str, Any]) -> dict[str, str]:
    """Bus payload. The full code is replaced by a short mask."""
    return {
        "action": action,
        "reservation_id": str(stay.get("key") or ""),
        "guest": str(stay.get("guest") or ""),
        "check_in": str(stay.get("check_in") or ""),
        "check_out": str(stay.get("check_out") or ""),
        "voucher_id": str(stay.get("voucher_id") or ""),
        "code_masque": mask_code(stay.get("voucher_code")),
        "username": str(stay.get("username") or ""),
    }


def _match_name(vouchers: list[Any], name: str) -> list[Any]:
    return [voucher for voucher in vouchers if getattr(voucher, "name", None) == name]


def _find_id(vouchers: list[Any], voucher_id: str | None) -> Any | None:
    if not voucher_id:
        return None
    for voucher in vouchers:
        if getattr(voucher, "id", None) == voucher_id:
            return voucher
    return None


async def async_synchronize(
    plan: SyncPlan,
    stored_stays: dict[str, dict[str, Any]],
    shared_user: dict[str, Any] | None,
    *,
    vouchers: VoucherDirectory | None,
    accounts: AccountDirectory | None,
    enable_vouchers: bool,
    enable_access: bool,
    force_rotate_keys: set[str] | None = None,
    force_voucher_keys: set[str] | None = None,
    print_keys: set[str] | None = None,
    resend_keys: set[str] | None = None,
    emit_print_on_create: bool = False,
    on_progress: Callable[[dict[str, dict[str, Any]], dict[str, Any] | None], Awaitable[None]]
    | None = None,
) -> CycleResult:
    """Converge stored state to the plan.

    ``stored_stays`` is copied. Callers persist the returned mapping even when
    this function later raises, if they pass the same objects — this function
    does not mutate the input dict.
    """
    stays = {key: dict(value) for key, value in stored_stays.items()}
    shared = dict(shared_user) if shared_user else None
    result = CycleResult(stays=stays, shared_user=shared)
    rotate_keys = force_rotate_keys or set()
    recreate_keys = force_voucher_keys or set()
    resend = resend_keys or set()
    to_print = set(print_keys or set())

    listed: list[Any] | None = None
    if enable_vouchers and vouchers is not None and (plan.ensure or plan.revoke_keys):
        listed = list(await vouchers.async_list_vouchers())

    for key in plan.revoke_keys:
        record = stays.get(key)
        if record is None:
            continue
        if plan.shared_username is not None:
            # Other stays still use the shared account.
            account_action = "detach"
        elif enable_access:
            account_action = "revoke"
        else:
            account_action = "keep"
        finished = await _revoke_stay(
            record,
            result,
            vouchers=vouchers if enable_vouchers else None,
            accounts=accounts,
            listed=listed,
            account_action=account_action,
        )
        if finished:
            stays.pop(key, None)
        await _progress(on_progress, stays, result.shared_user)

    for item in plan.ensure:
        record = stays.get(item.key, {"key": item.key})
        record["key"] = item.key
        record["guest"] = item.guest
        record["check_in"] = _iso(item.check_in)
        record["check_out"] = _iso(item.check_out)
        record["username"] = item.username
        if enable_vouchers and vouchers is not None and listed is not None:
            await _ensure_voucher(
                record,
                item,
                result,
                vouchers=vouchers,
                listed=listed,
                recreate=item.key in recreate_keys,
                emit_print_on_create=emit_print_on_create,
            )
        if enable_access and accounts is not None and plan.shared_username is None:
            await _ensure_account(
                record,
                result,
                accounts=accounts,
                display_name=f"Locataire — {item.guest}",
                rotate=item.key in rotate_keys or not record.get("password"),
            )
        if item.key in resend or item.key in to_print:
            _queue_notification(result, record, password=str(record.get("password") or ""))
        if item.key in to_print and record.get("voucher_code"):
            result.print_events.append(
                {
                    "reservation_id": item.key,
                    "guest": item.guest,
                    "check_in": record["check_in"],
                    "check_out": record["check_out"],
                    "code": str(record.get("voucher_code") or ""),
                    "username": str(record.get("username") or ""),
                }
            )
        stays[item.key] = record
        await _progress(on_progress, stays, result.shared_user)

    if enable_access and accounts is not None and plan.shared_username:
        await _ensure_shared(
            result,
            accounts=accounts,
            username=plan.shared_username,
            rotate=bool(rotate_keys) or not (shared or {}).get("password"),
            display_name=_shared_display(plan),
        )
        await _progress(on_progress, stays, result.shared_user)
    elif enable_access and accounts is not None and shared and shared.get("user_id"):
        if plan.shared_username is None:
            await accounts.async_revoke_user(str(shared["user_id"]))
            result.journal.append(
                _journal_row(
                    "acces_desactive",
                    {"username": shared.get("username"), "key": "shared"},
                    detail="compte partagé",
                )
            )
            result.events.append(
                _event_from(
                    "acces_desactive",
                    {"username": shared.get("username"), "key": "shared"},
                )
            )
            result.shared_user = None
            await _progress(on_progress, stays, result.shared_user)

    return result


async def _progress(
    callback: Callable[[dict[str, dict[str, Any]], dict[str, Any] | None], Awaitable[None]]
    | None,
    stays: dict[str, dict[str, Any]],
    shared: dict[str, Any] | None,
) -> None:
    if callback is not None:
        await callback(stays, shared)


def _shared_display(plan: SyncPlan) -> str:
    if not plan.ensure:
        return "Locataire"
    guest = plan.ensure[0].guest
    if len(plan.ensure) == 1:
        return f"Locataire — {guest}"
    return f"Locataire — {guest} (+{len(plan.ensure) - 1})"


async def _ensure_voucher(
    record: dict[str, Any],
    item: StayPlan,
    result: CycleResult,
    *,
    vouchers: VoucherDirectory,
    listed: list[Any],
    recreate: bool,
    emit_print_on_create: bool,
) -> None:
    spec = item.voucher
    signature = spec.signature()
    current = _find_id(listed, record.get("voucher_id"))
    same = (
        not recreate
        and current is not None
        and record.get("signature") == signature
        and getattr(current, "name", None) == spec.name
    )
    if same:
        record["voucher_code"] = getattr(current, "code", None) or record.get(
            "voucher_code"
        )
        record["voucher_name"] = spec.name
        return

    created, adopted = await _replace_voucher(record, spec, vouchers, listed, recreate)
    record["voucher_id"] = created.id
    record["voucher_code"] = created.code
    record["voucher_name"] = spec.name
    record["signature"] = signature
    action = "voucher_regenere" if recreate else "voucher_cree"
    if adopted and not recreate:
        action = "voucher_adopte"
    detail = "séjour mis à jour" if record.get("notified") else ""
    result.journal.append(_journal_row(action, record, detail=detail))
    result.events.append(_event_from(action, record))
    if action != "voucher_adopte":
        result.created_vouchers += 1
        record["notified"] = False
    if not record.get("notified"):
        _queue_notification(result, record, password=str(record.get("password") or ""))
        record["notified"] = True
    if emit_print_on_create and created.code and action != "voucher_adopte":
        result.print_events.append(
            {
                "reservation_id": item.key,
                "guest": item.guest,
                "check_in": record.get("check_in", ""),
                "check_out": record.get("check_out", ""),
                "code": created.code,
                "username": str(record.get("username") or ""),
            }
        )


async def _replace_voucher(
    record: dict[str, Any],
    spec: VoucherSpec,
    vouchers: VoucherDirectory,
    listed: list[Any],
    recreate: bool,
) -> tuple[Any, bool]:
    """Delete stale vouchers, then adopt or create the named one.

    Adoption is what makes a restart idempotent: a voucher that already
    carries this stay's name is reused instead of creating a second code.
    Regeneration deletes that voucher first, so a fresh code is issued.
    """
    previous = str(record["voucher_id"]) if record.get("voucher_id") else ""
    same_name = _match_name(listed, spec.name)

    if not recreate and same_name:
        chosen = same_name[0]
        chosen_id = str(getattr(chosen, "id", ""))
        stale = [previous] if previous and previous != chosen_id else []
        for voucher in same_name[1:]:
            extra = str(getattr(voucher, "id", ""))
            if extra and extra not in stale:
                stale.append(extra)
        for voucher_id in stale:
            await vouchers.async_delete_voucher(voucher_id)
            _drop_listed(listed, voucher_id)
        return chosen, True

    stale = []
    if previous:
        stale.append(previous)
    for voucher in same_name:
        voucher_id = str(getattr(voucher, "id", ""))
        if voucher_id and voucher_id not in stale:
            stale.append(voucher_id)
    for voucher_id in stale:
        await vouchers.async_delete_voucher(voucher_id)
        _drop_listed(listed, voucher_id)

    created = await vouchers.async_create_voucher(
        name=spec.name,
        time_limit_minutes=spec.time_limit_minutes,
        authorized_guest_limit=spec.authorized_guest_limit,
        rx_rate_limit_kbps=spec.rx_rate_limit_kbps,
        tx_rate_limit_kbps=spec.tx_rate_limit_kbps,
    )
    listed.append(created)
    return created, False


def _drop_listed(listed: list[Any], voucher_id: str) -> None:
    listed[:] = [voucher for voucher in listed if getattr(voucher, "id", None) != voucher_id]


async def _ensure_account(
    record: dict[str, Any],
    result: CycleResult,
    *,
    accounts: AccountDirectory,
    display_name: str,
    rotate: bool,
) -> None:
    before = record.get("user_id")
    ensured = await accounts.async_ensure_user(
        username=str(record.get("username") or ""),
        display_name=display_name,
        user_id=record.get("user_id"),
        password=record.get("password"),
        rotate=rotate,
    )
    record["user_id"] = ensured.get("user_id")
    record["username"] = ensured.get("username") or record.get("username")
    new_password = ensured.get("password")
    if new_password:
        record["password"] = new_password
        result.journal.append(
            _journal_row(
                "acces_cree" if not before else "acces_regenere",
                record,
                password=str(new_password),
            )
        )
        result.events.append(
            _event_from("acces_cree" if not before else "acces_regenere", record)
        )
        _queue_notification(result, record, password=str(new_password))


async def _ensure_shared(
    result: CycleResult,
    *,
    accounts: AccountDirectory,
    username: str,
    rotate: bool,
    display_name: str,
) -> None:
    current = result.shared_user or {}
    ensured = await accounts.async_ensure_user(
        username=username,
        display_name=display_name,
        user_id=current.get("user_id"),
        password=current.get("password"),
        rotate=rotate,
    )
    updated = {
        "user_id": ensured.get("user_id"),
        "username": ensured.get("username") or username,
        "password": ensured.get("password") or current.get("password"),
    }
    result.shared_user = updated
    for record in result.stays.values():
        record["username"] = updated["username"]
        # The shared account is stored once, on shared_user. A stay record
        # must not point at it, or ending that stay would delete the account
        # while another stay is still using it.
        record["user_id"] = None
        if updated.get("password"):
            record["password"] = updated["password"]
    if ensured.get("password"):
        anchor = next(iter(result.stays.values()), {"key": "shared"})
        row_stay = {
            "key": "shared",
            "guest": anchor.get("guest", ""),
            "check_in": anchor.get("check_in", ""),
            "check_out": anchor.get("check_out", ""),
            "username": updated["username"],
        }
        result.journal.append(
            _journal_row(
                "acces_cree",
                row_stay,
                password=str(ensured["password"]),
                detail="compte partagé",
            )
        )
        result.events.append(_event_from("acces_cree", row_stay))
        for record in result.stays.values():
            _queue_notification(result, record, password=str(updated["password"]))


async def _revoke_stay(
    record: dict[str, Any],
    result: CycleResult,
    *,
    vouchers: VoucherDirectory | None,
    accounts: AccountDirectory | None,
    listed: list[Any] | None,
    account_action: str,
) -> bool:
    """Revoke a stay.

    ``account_action`` is ``revoke`` (delete the per-stay user), ``keep``
    (access is disabled, remember the user) or ``detach`` (shared account,
    owned by the top-level record).
    """
    voucher_id = record.get("voucher_id")
    if voucher_id:
        if vouchers is None:
            return False
        await vouchers.async_delete_voucher(str(voucher_id))
        if listed is not None:
            _drop_listed(listed, str(voucher_id))
        result.deleted_vouchers += 1
        result.journal.append(_journal_row("voucher_supprime", record))
        result.events.append(_event_from("voucher_supprime", record))
        record["voucher_id"] = None
        record["voucher_code"] = None
    if record.get("user_id"):
        if account_action == "keep":
            return False
        if account_action == "revoke":
            if accounts is None:
                return False
            await accounts.async_revoke_user(str(record["user_id"]))
            result.journal.append(_journal_row("acces_supprime", record))
            result.events.append(_event_from("acces_supprime", record))
        record["user_id"] = None
        record["password"] = None
    return True


def _queue_notification(result: CycleResult, record: dict[str, Any], *, password: str) -> None:
    """Queue an owner notification. Duplicates for the same code are skipped."""
    code = str(record.get("voucher_code") or "")
    key = str(record.get("key") or "")
    for existing in result.notifications:
        if existing.get("reservation_id") == key and existing.get("code") == code:
            if password and not existing.get("password"):
                existing["password"] = password
            return
    result.notifications.append(
        {
            "reservation_id": key,
            "guest": str(record.get("guest") or ""),
            "check_in": str(record.get("check_in") or ""),
            "check_out": str(record.get("check_out") or ""),
            "code": code,
            "username": str(record.get("username") or ""),
            "password": password,
            "voucher_id": str(record.get("voucher_id") or ""),
        }
    )


NotifyCallback = Callable[[dict[str, str]], Awaitable[None]]
