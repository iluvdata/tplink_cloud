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
from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigEntry,
)
from homeassistant.const import CONF_DEVICE, CONF_MAC
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
    KASA_MAC,
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


@callback
def async_is_active_tplink_device(hass: HomeAssistant, device_dict: DeviceDict) -> bool:
    """Check if the device is already registered in another config entry."""

    formatted_mac = dr.format_mac(device_dict[KASA_MAC])
    if config_entry := hass.config_entries.async_entry_for_domain_unique_id(
        TPLINK_DOMAIN, formatted_mac
    ):
        return config_entry.source != SOURCE_IGNORE and config_entry.disabled_by is None
    return False


@callback
def async_is_active_cloud_device(
    hass: HomeAssistant, entry_id: str, device_dict: DeviceDict
) -> bool:
    """Check if the device is a cloud device."""

    formatted_mac = dr.format_mac(device_dict[KASA_MAC])
    dev_reg = dr.async_get(hass)
    return (
        dev_reg.async_get_device_by_connection(
            (dr.CONNECTION_NETWORK_MAC, formatted_mac), entry_id
        )
        is not None
    )


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
            **self.config_entry.options.get(
                DEVICE_INTERVAL, {"seconds": DEFAULT_DEVICE_INTERVAL}
            )
        )
        for device in data:
            if async_is_active_cloud_device(
                self.hass, self.config_entry.entry_id, device
            ):
                kasadevice: Device = await self.cloud.get_device(device)
                coordinator: TPLinkDataUpdateCoordinator = TPLinkDataUpdateCoordinator(
                    hass=self.hass,
                    device=kasadevice,
                    update_interval=poll_interval,
                    config_entry=cast(TPLinkConfigEntry, self.config_entry),
                )
                self.data.append(
                    TPLinkData(
                        parent_coordinator=coordinator,
                        camera_credentials=None,
                        live_view=None,
                    )
                )
                continue
            self._trigger_discover_flow(device)

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
        # check if the device hasn't been ignored, disabled, or otherwise configured
        mac = dr.format_mac(device[KASA_MAC])
        if config_entry := self.hass.config_entries.async_entry_for_domain_unique_id(
            self.config_entry, mac
        ):
            if config_entry.source == SOURCE_IGNORE:
                return
        if async_is_active_tplink_device(self.hass, device):
            return

        discovery_flow.async_create_flow(
            self.hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_DEVICE: device, CONFIG_ENTRY: self.config_entry},
            discovery_key=discovery_flow.DiscoveryKey(
                domain=DOMAIN,
                key=(CONF_MAC, dr.format_mac(device[KASA_MAC])),
                version=1,
            ),
        )

    async def _async_update_data(self) -> list[TPLinkData]:
        data: list[DeviceDict] = await self._async_get_device_list()

        if len(data) != len(self.data):
            # we have new devices?
            for device in data:
                if not async_is_active_cloud_device(
                    self.hass, self.config_entry.entry_id, device
                ):
                    self._trigger_discover_flow(device)

        return self.data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        for data in self.data:
            await data.parent_coordinator.async_shutdown()
        await self.cloud.close()
        return await super().async_shutdown()
