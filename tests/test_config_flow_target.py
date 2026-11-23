"""Tenant Target selector expands to entity/device id lists."""

from custom_components.usvegliu.const import (
    CONF_TENANT_DEVICES,
    CONF_TENANT_ENTITIES,
    CONF_TENANT_TARGET,
)
from custom_components.usvegliu.target_options import (
    as_id_list,
    expand_tenant_target,
    tenant_target_default,
)


def test_as_id_list_normalizes_string_and_list():
    assert as_id_list(None) == []
    assert as_id_list("") == []
    assert as_id_list("light.salon") == ["light.salon"]
    assert as_id_list(["light.a", "light.a", " light.b "]) == ["light.a", "light.b"]


def test_tenant_target_default_from_stored_lists():
    target = tenant_target_default(
        {
            CONF_TENANT_ENTITIES: ["climate.bath", "light.hall"],
            CONF_TENANT_DEVICES: ["abc123"],
        }
    )
    assert target["entity_id"] == ["climate.bath", "light.hall"]
    assert target["device_id"] == ["abc123"]


def test_expand_tenant_target_without_hass():
    entities, devices = expand_tenant_target(
        None,
        {
            "entity_id": ["climate.bath", "light.hall"],
            "device_id": "dev-1",
            "area_id": ["area-ignored-without-hass"],
        },
    )
    assert entities == ["climate.bath", "light.hall"]
    assert devices == ["dev-1"]
    assert CONF_TENANT_TARGET == "tenant_target"
