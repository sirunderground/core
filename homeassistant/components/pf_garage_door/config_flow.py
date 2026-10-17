"""Config flow for the Example Air integration."""

import logging
from typing import Any, override

import probatio

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .pf_garage_door import GarageDoorClient, GarageDoorError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): str,
        probatio.Required(CONF_USERNAME): str,
        probatio.Required(CONF_PASSWORD): str,
    }
)


class ExampleAirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Example Air."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow started by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = GarageDoorClient(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                session=async_get_clientsession(self.hass),
            )

            try:
                status = await client.get_status()
            except GarageDoorError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(status.serial_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=status.name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
