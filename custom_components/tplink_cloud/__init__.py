"""The TPLink Cloud integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from kasa import AuthenticationError
from pykasacloud import KasaCloud, Token

from homeassistant.components.tplink import create_async_tplink_clientsession
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.helpers.device_registry as dr

from .const import DEVICE_LIST_INTERVAL, PLATFORMS, TOKEN
from .coordinator import KasaCloudConfigEntry, KasaCloudCoordinator
from .exceptions import TokenUpdateError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: KasaCloudConfigEntry) -> bool:
    """Set up TPLink Cloud from a config entry."""

    async def update_token(token: Token) -> None:
        data = entry.data | {TOKEN: token}
        result = hass.config_entries.async_update_entry(
            entry=entry, data=data, unique_id=entry.unique_id
        )
        if not result:
            raise TokenUpdateError("Unable to update token in config entry")

    try:
        cloud: KasaCloud = await KasaCloud.kasacloud(
            client_session=create_async_tplink_clientsession(hass),
            token=entry.data.get(TOKEN),
            token_update_callback=update_token,
        )
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed(err) from err

    coordinator: KasaCloudCoordinator = KasaCloudCoordinator(hass, entry, cloud)

    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: KasaCloudConfigEntry) -> None:
    """Config Entry Update Listener."""
    coordinator: KasaCloudCoordinator = entry.runtime_data
    if entry.options and DEVICE_LIST_INTERVAL in entry.options:
        coordinator.new_interval(timedelta(**entry.options[DEVICE_LIST_INTERVAL]))


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: KasaCloudConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Delete device if selected from UI."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KasaCloudConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
