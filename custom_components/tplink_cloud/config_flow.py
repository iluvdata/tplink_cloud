"""Config flow for the TPLink Cloud integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from kasa import AuthenticationError
from pykasacloud.kasacloud import KasaCloud
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DurationSelector,
    DurationSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    ACCOUNT_ID,
    DEFAULT_DEVICE_INTERVAL,
    DEFAULT_DEVICE_LIST_INTERVAL,
    DEVICE_INTERVAL,
    DEVICE_LIST_INTERVAL,
    DOMAIN,
    MIN_DEVICE_INTERVAL,
    MIN_DEVICE_LIST_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(autocomplete=CONF_USERNAME, type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(
            DEVICE_LIST_INTERVAL, default={"minutes": DEFAULT_DEVICE_LIST_INTERVAL}
        ): DurationSelector(
            DurationSelectorConfig(enable_millisecond=False, enable_day=False)
        ),
        vol.Required(
            DEVICE_INTERVAL, default={"seconds": DEFAULT_DEVICE_INTERVAL}
        ): DurationSelector(
            DurationSelectorConfig(enable_millisecond=False, enable_day=False)
        ),
    }
)


class OptionsFlowHandler(OptionsFlow):
    """Options flow for integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # validate durations
            if timedelta(**user_input[DEVICE_INTERVAL]) < timedelta(
                seconds=MIN_DEVICE_INTERVAL
            ):
                errors[DEVICE_INTERVAL] = "min_interval"
            if timedelta(**user_input[DEVICE_LIST_INTERVAL]) < timedelta(
                minutes=MIN_DEVICE_LIST_INTERVAL
            ):
                errors[DEVICE_LIST_INTERVAL] = "min_interval"
            if not errors:
                return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
            description_placeholders={
                DEVICE_INTERVAL: str(MIN_DEVICE_INTERVAL),
                DEVICE_LIST_INTERVAL: str(MIN_DEVICE_LIST_INTERVAL),
                "default_interval": str(DEFAULT_DEVICE_INTERVAL),
                "default_list_interval": str(DEFAULT_DEVICE_LIST_INTERVAL),
            },
            errors=errors,
        )


class TpLinkCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TPLink Cloud."""

    VERSION = 1

    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Alert user that reauth is necessary."""
        return await self.async_step_user(entry_data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input:
            try:
                cloud: KasaCloud = await KasaCloud.kasacloud(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
                await self.async_set_unique_id(str(cloud.token[ACCOUNT_ID]))
                await cloud.close()
                if self.source == SOURCE_USER:
                    # Default options
                    options: dict[str, Any] = {
                        DEVICE_INTERVAL: {"seconds": DEFAULT_DEVICE_INTERVAL},
                        DEVICE_LIST_INTERVAL: {"minutes": DEFAULT_DEVICE_LIST_INTERVAL},
                    }
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Account {user_input[CONF_USERNAME]}",
                        data={CONF_TOKEN: cloud.token},
                        options=options,
                    )
                if self.source == SOURCE_REAUTH:
                    entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(
                        entry,
                        title=f"Account {user_input[CONF_USERNAME]}",
                        data={CONF_TOKEN: cloud.token},
                    )

            except AuthenticationError:
                _LOGGER.exception("Authentication error")
                errors["base"] = "auth_error"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
