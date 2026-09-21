"""Util functions for TPLink Cloud devices."""

from collections.abc import Callable
from typing import cast

from homeassistant.components.tplink import DOMAIN as TPLINK_DOMAIN, TPLinkConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KasaCloudConfigEntry, TPLinkConfigEntrySkelaton


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KasaCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    async_tplink_entry: Callable,
) -> None:
    """Wrapper function to access base TpLink Device."""

    for data in config_entry.runtime_data.data:
        # if tplink is configured, check to make sure the device isn't already registered, otherwise we will get duplicates.
        if (
            hass.config_entries.async_entry_for_domain_unique_id(
                TPLINK_DOMAIN, data.parent_coordinator.device.mac
            )
            is None
        ):
            # Is the device a tplink_cloud device or is it already configured via the tplink integration?
            await async_tplink_entry(
                hass,
                cast(TPLinkConfigEntry, TPLinkConfigEntrySkelaton(data)),
                async_add_entities,
            )
