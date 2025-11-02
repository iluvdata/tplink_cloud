"""Util functions for TPLink Cloud devices."""

from collections.abc import Callable
from typing import cast

from homeassistant.components.tplink import DOMAIN as TPLINK_DOMAIN, TPLinkConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KasaCloudConfigEntry, TPLinkConfigEntrySkelaton


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KasaCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    async_tplink_entry: Callable,
) -> None:
    """Wrapper function to access base TpLink Device."""

    # Is base tplink configured?
    device_registry: dr.DeviceRegistry | None = (
        dr.async_get(hass)
        if hass.config_entries.async_loaded_entries(TPLINK_DOMAIN)
        else None
    )
    for data in config_entry.runtime_data.data:
        # if tplink is configured, check to make sure the device isn't already registered, otherwise we will get duplicates.
        device = (
            device_registry.async_get_device(
                {(TPLINK_DOMAIN, data.parent_coordinator.device.mac)}
            )
            if device_registry
            else None
        )
        # Is the device a tplink_cloud device or is it already configured via the tplink integration?
        device = (
            device
            if device and device.primary_config_entry != config_entry.entry_id
            else None
        )
        if not device_registry or not device:
            await async_tplink_entry(
                hass,
                cast(TPLinkConfigEntry, TPLinkConfigEntrySkelaton(data)),
                async_add_entities,
            )
