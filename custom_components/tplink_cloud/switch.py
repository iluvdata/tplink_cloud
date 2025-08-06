"""Kasa Cloud Device Wrapper."""

from typing import cast

from homeassistant.components.tplink import TPLinkConfigEntry
from homeassistant.components.tplink.switch import (  # pylint: disable=hass-component-root-import
    async_setup_entry as async_tplink_entry,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KasaCloudConfigEntry, TPLinkConfigEntrySkelaton


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KasaCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Wrapper function to access base TpLink Device."""
    for data in config_entry.runtime_data.data.values():
        await async_tplink_entry(
            hass,
            cast(TPLinkConfigEntry, TPLinkConfigEntrySkelaton(data)),
            async_add_entities,
        )
