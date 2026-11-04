"""Home Assistant accounts for tenants.

The public auth manager can create users, but it cannot create a group.
A custom group is required because the built-in ``system-users`` policy is
``{"entities": True}`` (every entity, including cameras and locks) and
``system-admin`` can configure the instance. The group is therefore written
through the auth store. This is an internal API: retest it on each major
Home Assistant upgrade.

Passwords are returned to the caller and are never logged here.
The tenant's default Lovelace panel is Séjour, not the Home overview.
"""

from __future__ import annotations

import re
import secrets

from .const import GROUP_PREFIX, SENSITIVE_DOMAINS, TENANT_GROUP_ID, TENANT_GROUP_NAME

ADMIN_GROUP_ID = "system-admin"
USERS_GROUP_ID = "system-users"
READ_ONLY_GROUP_ID = "system-read-only"


class TenantAccessError(Exception):
    """A tenant account would have been too privileged, or the input is invalid."""


def generate_password() -> str:
    """Return a password that fits the 72-byte bcrypt limit."""
    return secrets.token_urlsafe(12)


def entity_domain(entity_id: str) -> str:
    """Return the domain portion of an entity id."""
    if "." not in entity_id:
        return ""
    return entity_id.split(".", 1)[0]


def sensitive_entity_ids(entity_ids: list[str]) -> list[str]:
    """Return the cameras, locks and alarm panels in a selection."""
    return [entity_id for entity_id in entity_ids if entity_domain(entity_id) in SENSITIVE_DOMAINS]


def group_id_for_username(username: str) -> str:
    """One group per tenant account, so two stays cannot share a policy."""
    safe = re.sub(r"[^a-z0-9-]", "", username.casefold())[:48] or "locataire"
    return f"{GROUP_PREFIX}{safe}"


def unique_strings(values: list[str] | None) -> list[str]:
    """Drop empties and duplicates, keeping order."""
    result: list[str] = []
    for value in values or []:
        if value and value not in result:
            result.append(value)
    return result


def resolve_stay_access(
    key: str,
    *,
    overrides: dict[str, dict] | None,
    entity_ids: list[str],
    device_ids: list[str],
    allow_remote: bool,
) -> tuple[list[str], list[str], bool]:
    """Global selection, replaced by a per-stay override when one is stored."""
    override = (overrides or {}).get(key) or {}
    if "entity_ids" in override or "device_ids" in override:
        entities = unique_strings(list(override.get("entity_ids") or []))
        devices = unique_strings(list(override.get("device_ids") or []))
    else:
        entities = unique_strings(entity_ids)
        devices = unique_strings(device_ids)
    if "allow_remote" in override:
        remote = bool(override["allow_remote"])
    else:
        remote = allow_remote
    return entities, devices, remote


def resolve_shared_access(
    keys: list[str],
    *,
    overrides: dict[str, dict] | None,
    entity_ids: list[str],
    device_ids: list[str],
    allow_remote: bool,
) -> tuple[list[str], list[str], bool]:
    """Union of every active stay. One shared login cannot hold two policies."""
    if not keys:
        return [], [], False
    entities: list[str] = []
    devices: list[str] = []
    remote = False
    for key in keys:
        stay_entities, stay_devices, stay_remote = resolve_stay_access(
            key,
            overrides=overrides,
            entity_ids=entity_ids,
            device_ids=device_ids,
            allow_remote=allow_remote,
        )
        entities = unique_strings(entities + stay_entities)
        devices = unique_strings(devices + stay_devices)
        remote = remote or stay_remote
    return entities, devices, remote


def build_tenant_policy(
    entity_ids: list[str],
    device_ids: list[str] | None = None,
) -> dict:
    """Read and control only the chosen entities and devices.

    ``edit`` is false so a tenant cannot rename or delete them.
    Nothing else is granted: no ``all``, no whole domain.
    An empty selection grants no entity at all.
    """
    entities = unique_strings(entity_ids)
    devices = unique_strings(device_ids)
    policy: dict = {"entities": {}}
    if entities:
        policy["entities"]["entity_ids"] = {
            entity_id: {"read": True, "control": True, "edit": False}
            for entity_id in entities
        }
    if devices:
        policy["entities"]["device_ids"] = {
            device_id: {"read": True, "control": True, "edit": False}
            for device_id in devices
        }
    if not policy["entities"]:
        policy["entities"]["entity_ids"] = {}
    return policy


def user_group_ids(user: object) -> set[str]:
    """Return the auth group ids attached to a Home Assistant user."""
    groups = getattr(user, "groups", None) or []
    return {
        str(group_id)
        for group in groups
        if (group_id := getattr(group, "id", None))
    }


def is_tenant_user(user: object) -> bool:
    """True when the account is a stay login created by Usvegliu."""
    if user is None:
        return False
    return any(
        group_id == TENANT_GROUP_ID or group_id.startswith(GROUP_PREFIX)
        for group_id in user_group_ids(user)
    )


def user_can_manage_stays(user: object) -> bool:
    """Admins and Users (control rights) may open the owner console.

    Tenant accounts and read-only users cannot. Automations pass a separate
    empty-context check in the service handler.
    """
    if user is None or getattr(user, "system_generated", False):
        return False
    if is_tenant_user(user):
        return False
    if getattr(user, "is_owner", False) or getattr(user, "is_admin", False):
        return True
    groups = user_group_ids(user)
    if ADMIN_GROUP_ID in groups or USERS_GROUP_ID in groups:
        return True
    if READ_ONLY_GROUP_ID in groups:
        return False
    return False


def assert_not_privileged(user: object) -> None:
    """Refuse to touch an owner, an administrator, or a Users account."""
    if user_can_manage_stays(user):
        raise TenantAccessError("refuse_admin")
    groups = user_group_ids(user)
    if ADMIN_GROUP_ID in groups:
        raise TenantAccessError("refuse_admin")


async def async_ensure_group(
    hass: object,
    group_id: str,
    entity_ids: list[str],
    device_ids: list[str] | None = None,
) -> str:
    """Create or update one tenant group and return its id."""
    from homeassistant.auth import models as auth_models

    if group_id == ADMIN_GROUP_ID or not group_id.startswith(GROUP_PREFIX):
        raise TenantAccessError("refuse_admin")
    policy = build_tenant_policy(entity_ids, device_ids)
    auth = hass.auth  # type: ignore[attr-defined]
    existing = await auth.async_get_group(group_id)
    store = auth._store  # noqa: SLF001 — no public API creates a group
    if existing is None:
        store._groups[group_id] = auth_models.Group(  # noqa: SLF001
            name=TENANT_GROUP_NAME,
            policy=policy,
            id=group_id,
            system_generated=False,
        )
    else:
        if existing.id == ADMIN_GROUP_ID:
            raise TenantAccessError("refuse_admin")
        existing.policy = policy
        existing.system_generated = False
    store._async_schedule_save()  # noqa: SLF001
    for user in await auth.async_get_users():
        if any(getattr(group, "id", None) == group_id for group in user.groups):
            user.invalidate_cache()
            assert_not_privileged(user)
    return group_id


async def async_ensure_user(
    hass: object,
    *,
    username: str,
    display_name: str,
    user_id: str | None,
    rotate: bool,
    local_only: bool,
    entity_ids: list[str],
    device_ids: list[str] | None = None,
) -> dict[str, str | None]:
    """Create or update a non-admin tenant.

    ``local_only`` is false only while a stay explicitly allows remote login.
    The returned password is set only when it was just generated. It is not
    stored by this function.
    """
    from homeassistant.auth.providers.homeassistant import (
        InvalidUsername,
        async_get_provider,
    )

    if username != username.casefold() or not username:
        raise TenantAccessError("username")
    auth = hass.auth  # type: ignore[attr-defined]
    owner = await auth.async_get_owner()
    if owner is None:
        # Creating the first user makes them the owner. Never do that.
        raise TenantAccessError("no_owner")

    group_id = await async_ensure_group(
        hass, group_id_for_username(username), entity_ids, device_ids
    )
    provider = async_get_provider(hass)  # type: ignore[arg-type]
    user = await auth.async_get_user(user_id) if user_id else None
    if user is not None:
        assert_not_privileged(user)

    fresh_password: str | None = None
    if user is None:
        fresh_password = generate_password()
        user = await auth.async_create_user(
            display_name,
            group_ids=[group_id],
            local_only=local_only,
        )
        try:
            assert_not_privileged(user)
        except TenantAccessError:
            if not user.is_owner:
                await auth.async_remove_user(user)
            raise
        if not user.is_active:
            raise TenantAccessError("user_flags")
        credentials = await provider.async_get_or_create_credentials(
            {"username": username}
        )
        linked = await auth.async_get_user_by_credentials(credentials)
        if linked is not None and linked.id != user.id:
            # Drop the empty user before touching the existing account,
            # and never change the password of an owner or an admin.
            await auth.async_remove_user(user)
            assert_not_privileged(linked)
            user = linked
        try:
            await provider.async_add_auth(username, fresh_password)
        except InvalidUsername:
            await provider.async_change_password(username, fresh_password)
        if linked is None:
            await auth.async_link_user(user, credentials)
    elif rotate:
        known_username = provider.async_get_username(user)
        if known_username is not None and known_username != username:
            raise TenantAccessError("username_mismatch")
        fresh_password = generate_password()
        try:
            await provider.async_change_password(username, fresh_password)
        except Exception as err:  # noqa: BLE001 — provider raises InvalidUser
            if type(err).__name__ not in {"InvalidUser", "InvalidUsername"}:
                raise
            await provider.async_add_auth(username, fresh_password)

    await auth.async_update_user(
        user,
        name=display_name,
        is_active=True,
        group_ids=[group_id],
        local_only=local_only,
    )
    assert_not_privileged(user)
    from .dashboard import async_set_tenant_default_panel

    await async_set_tenant_default_panel(hass, user.id)
    return {
        "user_id": user.id,
        "username": username,
        "password": fresh_password,
    }


async def async_revoke_user(hass: object, user_id: str) -> None:
    """Delete a tenant account. Owners and administrators are never removed."""
    auth = hass.auth  # type: ignore[attr-defined]
    user = await auth.async_get_user(user_id)
    if user is None:
        return
    assert_not_privileged(user)
    if user.is_owner or user.is_admin:
        raise TenantAccessError("refuse_admin")
    await auth.async_remove_user(user)
