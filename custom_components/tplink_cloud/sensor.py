"""Kasa Cloud Sensor Wrapper."""

from homeassistant.components.tplink.sensor import (  # pylint: disable=hass-component-root-import
    async_setup_entry as async_tplink_entry,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import HomeAssistant

from .coordinator import KasaCloudConfigEntry
from .util import async_setup_entry as async_util_entry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KasaCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TPLink Cloud Switches."""
    await async_util_entry(
        hass,
        config_entry,
        async_add_entities,
        async_tplink_entry,
    )
