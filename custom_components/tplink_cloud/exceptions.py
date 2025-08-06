"""TPLink Cloud Exceptions."""

from homeassistant.exceptions import ConfigEntryError, IntegrationError


class TokenUpdateError(ConfigEntryError):
    """Unable to update token in config entry."""


class CloudConnectionError(IntegrationError):
    """Unable to connect to Cloud API."""
