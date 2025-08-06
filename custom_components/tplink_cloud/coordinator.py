"""Coordinators for Kasa Cloud."""

from collections.abc import Callable, Coroutine
from datetime import timedelta
import logging
from typing import Any, cast

from kasa import AuthenticationError, Device, KasaException
from pykasacloud import KasaCloud

from homeassistant.components.tplink import (
    TPLinkConfigEntry,
    TPLinkData,
    TPLinkDataUpdateCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_DEVICE_INTERVAL,
    DEFAULT_DEVICE_LIST_INTERVAL,
    DEVICE_INTERVAL,
    DEVICE_LIST_INTERVAL,
    DOMAIN,
)
from .exceptions import CloudConnectionError

_LOGGER = logging.getLogger(__name__)


type KasaCloudConfigEntry = ConfigEntry[KasaCloudCoordinator]


class TPLinkConfigEntrySkelaton:
    """Helper class to allow us to reuse code in Platform setups."""

    def __init__(self, data: TPLinkData) -> None:
        """Init for this class."""
        self.runtime_data = data

    @callback
    def async_on_unload(
        self, func: Callable[[], Coroutine[Any, Any, None] | None]
    ) -> None:
        """Placeholder method that does nothing."""


class KasaCloudCoordinator(DataUpdateCoordinator[dict[str, TPLinkData]]):
    """KasaCloud Coordinator for refreshing device list."""

    config_entry: KasaCloudConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, cloud: KasaCloud
    ) -> None:
        """Initialize device list coordiator."""
        self._poll_interval: dict[str, int] = entry.data.get(
            DEVICE_LIST_INTERVAL, {"minutes": DEFAULT_DEVICE_LIST_INTERVAL}
        )
        self.cloud: KasaCloud = cloud
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Kasa Cloud {entry.unique_id}",
            update_interval=timedelta(**self._poll_interval),
        )
        self.data = {}

    def new_interval(self, value: timedelta) -> None:
        """Set interval between updates."""
        super().update_interval = value
        # update the sub coordinators
        poll_interval: timedelta = timedelta(
            **self.config_entry.options[DEVICE_INTERVAL]
        )
        for tplinkdata in self.data.values():
            tplinkdata.parent_coordinator.update_interval = poll_interval

    async def _async_update_data(self) -> dict[str, TPLinkData]:
        try:
            data: dict[str, Any] = await self.cloud.get_device_list()
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed(ex) from ex
        except KasaException as ex:
            raise CloudConnectionError(
                translation_domain=DOMAIN, translation_key="connection_error"
            ) from ex

        poll_interval: timedelta = timedelta(
            **self.config_entry.data.get(
                DEVICE_INTERVAL, {"seconds": DEFAULT_DEVICE_INTERVAL}
            )
        )

        if not self.data:
            # first run.
            for device_id, device in data.items():
                kasadevice: Device = await self.cloud.get_device(device)
                coordinator: TPLinkDataUpdateCoordinator = TPLinkDataUpdateCoordinator(
                    hass=self.hass,
                    device=kasadevice,
                    update_interval=poll_interval,
                    config_entry=cast(TPLinkConfigEntry, self.config_entry),
                )
                self.data[device_id] = TPLinkData(
                    parent_coordinator=coordinator,
                    camera_credentials=None,
                    live_view=None,
                )
            return self.data

        if list(data.keys() - self.data.keys()):
            # new device
            if not await self.hass.config_entries.async_reload(
                self.config_entry.entry_id
            ):
                raise ConfigEntryError("Found a new device, please reload manually")

        return self.data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        for data in self.data.values():
            await data.parent_coordinator.async_shutdown()
        await self.cloud.close()
        return await super().async_shutdown()
