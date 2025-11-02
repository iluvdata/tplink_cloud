"""Coordinators for Kasa Cloud."""

from collections.abc import Callable, Coroutine
from datetime import timedelta
import logging
from typing import Any, cast

from kasa import AuthenticationError, Device, KasaException
from pykasacloud import DeviceDict, KasaCloud

from homeassistant.components.tplink import (
    DOMAIN as TPLINK_DOMAIN,
    TPLinkConfigEntry,
    TPLinkData,
    TPLinkDataUpdateCoordinator,
)
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_ALIAS, CONF_DEVICE, CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import discovery_flow
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONFIG_ENTRY,
    DEFAULT_DEVICE_INTERVAL,
    DEFAULT_DEVICE_LIST_INTERVAL,
    DEVICE_INTERVAL,
    DEVICE_LIST_INTERVAL,
    DOMAIN,
)
from .exceptions import CloudConnectionError

_LOGGER = logging.getLogger(__name__)


type KasaCloudConfigEntry = ConfigEntry[KasaCloudCoordinator]


def device_is_registered(hass: HomeAssistant, formatted_mac: str) -> bool:
    """Check if the device is already registered."""
    # first check the device registries:
    dev_reg: dr.DeviceRegistry = dr.async_get(hass)
    device = dev_reg.async_get_device({(TPLINK_DOMAIN, formatted_mac.upper())})
    return device is not None


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


class KasaCloudCoordinator(DataUpdateCoordinator[list[TPLinkData]]):
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
        self.data = []

    def new_interval(self, value: timedelta) -> None:
        """Set interval between updates."""
        self.update_interval = value
        # update the sub coordinators
        poll_interval: timedelta = timedelta(
            **self.config_entry.options[DEVICE_INTERVAL]
        )
        for tplinkdata in self.data:
            tplinkdata.parent_coordinator.update_interval = poll_interval

    async def _async_setup(self) -> None:
        data: list[DeviceDict] = await self._async_get_device_list()
        poll_interval: timedelta = timedelta(
            **self.config_entry.data.get(
                DEVICE_INTERVAL, {"seconds": DEFAULT_DEVICE_INTERVAL}
            )
        )
        for device in data:
            formatted_mac: str = dr.format_mac(device["deviceMac"]).upper()
            if not device_is_registered(self.hass, formatted_mac):
                if formatted_mac in self.config_entry.data.get("devices", []):
                    kasadevice: Device = await self.cloud.get_device(device)
                    coordinator: TPLinkDataUpdateCoordinator = (
                        TPLinkDataUpdateCoordinator(
                            hass=self.hass,
                            device=kasadevice,
                            update_interval=poll_interval,
                            config_entry=cast(TPLinkConfigEntry, self.config_entry),
                        )
                    )
                    self.data.append(
                        TPLinkData(
                            parent_coordinator=coordinator,
                            camera_credentials=None,
                            live_view=None,
                        )
                    )

    async def _async_get_device_list(self) -> list[DeviceDict]:
        try:
            return await self.cloud.get_device_list()
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
                translation_placeholders={"exc": str(ex)},
            ) from ex
        except KasaException as ex:
            raise CloudConnectionError(
                translation_domain=DOMAIN, translation_key="connection_error"
            ) from ex

    def _trigger_discover_flow(self, device: DeviceDict) -> None:
        discovery_flow.async_create_flow(
            self.hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_ALIAS: device.get(CONF_ALIAS, device["deviceName"]),
                CONF_MAC: dr.format_mac(device["deviceMac"]),
                CONF_DEVICE: device,
                CONFIG_ENTRY: self.config_entry,
            },
        )

    async def _async_update_data(self) -> list[TPLinkData]:
        data: list[DeviceDict] = await self._async_get_device_list()

        if len(data) != len(self.data):
            # we have new devices?
            for device in data:
                formatted_mac: str = dr.format_mac(device["deviceMac"])
                if formatted_mac not in self.config_entry.data.get(
                    "devices", []
                ) and not device_is_registered(self.hass, formatted_mac):
                    self._trigger_discover_flow(device)

        return self.data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        for data in self.data:
            await data.parent_coordinator.async_shutdown()
        await self.cloud.close()
        return await super().async_shutdown()
