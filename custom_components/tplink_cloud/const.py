"""Constants for the TPLink Cloud integration."""

from homeassistant.const import Platform

DOMAIN = "tplink_cloud"
TOKEN = "token"
DEVICE_LIST_INTERVAL = "device_list_interval"
DEFAULT_DEVICE_LIST_INTERVAL = 30  # minutes
MIN_DEVICE_LIST_INTERVAL = 1  # minute
DEVICE_INTERVAL = "device_interval"
DEFAULT_DEVICE_INTERVAL = 60  # seconds
MIN_DEVICE_INTERVAL = 5  # seconds
REFRESH_TOKEN = "refresh_token"
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]
