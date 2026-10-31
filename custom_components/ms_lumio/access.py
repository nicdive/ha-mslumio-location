"""Home Assistant accounts for tenants.

The public auth manager can create users, but it cannot create a group.
A custom group is required because the built-in ``system-users`` policy is
``{"entities": True}`` (every entity, including cameras and locks) and
``system-admin`` can configure the instance. The group is therefore written
through the auth store. This is an internal API: retest it on each major
Home Assistant upgrade.

Passwords are returned to the caller and are never logged here.
"""

from __future__ import annotations

import secrets

from .const import (
    ALLOWED_DOMAINS,
    FORBIDDEN_DOMAINS,
    TENANT_GROUP_ID,
    TENANT_GROUP_NAME,
)

ADMIN_GROUP_ID = "system-admin"


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


def build_tenant_policy(entity_ids: list[str]) -> dict:
    """Policy limited to the chosen climate, cover and light entities.

    ``edit`` is false so a tenant cannot rename or delete the entity.
    An empty selection grants no entity at all.
    """
    allowed: list[str] = []
    for entity_id in entity_ids:
        domain = entity_domain(entity_id)
        if domain in FORBIDDEN_DOMAINS or domain not in ALLOWED_DOMAINS:
            raise TenantAccessError(f"forbidden_domain:{domain or entity_id}")
        if entity_id not in allowed:
            allowed.append(entity_id)
    return {
        "entities": {
            "entity_ids": {
                entity_id: {"read": True, "control": True, "edit": False}
                for entity_id in allowed
            }
        }
    }


def assert_not_privileged(user: object) -> None:
    """Refuse to touch an owner or an administrator."""
    if getattr(user, "is_owner", False) or getattr(user, "is_admin", False):
        raise TenantAccessError("refuse_admin")
    groups = getattr(user, "groups", []) or []
    for group in groups:
        if getattr(group, "id", None) == ADMIN_GROUP_ID:
            raise TenantAccessError("refuse_admin")


async def async_ensure_group(hass: object, entity_ids: list[str]) -> str:
    """Create or update the tenant group and return its id."""
    from homeassistant.auth import models as auth_models

    policy = build_tenant_policy(entity_ids)
    auth = hass.auth  # type: ignore[attr-defined]
    existing = await auth.async_get_group(TENANT_GROUP_ID)
    store = auth._store  # noqa: SLF001 — no public API creates a group
    if existing is None:
        store._groups[TENANT_GROUP_ID] = auth_models.Group(  # noqa: SLF001
            name=TENANT_GROUP_NAME,
            policy=policy,
            id=TENANT_GROUP_ID,
            system_generated=False,
        )
    else:
        if existing.id == ADMIN_GROUP_ID or existing.system_generated:
            # system_generated groups do not persist their policy.
            if existing.id == ADMIN_GROUP_ID:
                raise TenantAccessError("refuse_admin")
        existing.policy = policy
        existing.system_generated = False
    store._async_schedule_save()  # noqa: SLF001
    for user in await auth.async_get_users():
        if any(getattr(group, "id", None) == TENANT_GROUP_ID for group in user.groups):
            user.invalidate_cache()
            assert_not_privileged(user)
    return TENANT_GROUP_ID


async def async_ensure_user(
    hass: object,
    *,
    username: str,
    display_name: str,
    user_id: str | None,
    password: str | None,
    rotate: bool,
    entity_ids: list[str],
) -> dict[str, str | None]:
    """Create or update a non-admin, local-only tenant.

    The returned password is set only when it was just generated.
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

    await async_ensure_group(hass, entity_ids)
    provider = async_get_provider(hass)  # type: ignore[arg-type]
    user = await auth.async_get_user(user_id) if user_id else None
    if user is not None:
        assert_not_privileged(user)

    fresh_password: str | None = None
    if user is None:
        fresh_password = generate_password()
        user = await auth.async_create_user(
            display_name,
            group_ids=[TENANT_GROUP_ID],
            local_only=True,
        )
        try:
            assert_not_privileged(user)
        except TenantAccessError:
            if not user.is_owner:
                await auth.async_remove_user(user)
            raise
        if not user.local_only or not user.is_active:
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
    elif rotate or not password:
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
        group_ids=[TENANT_GROUP_ID],
        local_only=True,
    )
    assert_not_privileged(user)
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
