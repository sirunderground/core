"""Config flow for the experimental FLO X3 integration."""

from typing import Any

import aiohttp
import probatio

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import FloX3ApiClient, FloX3ApiError, FloX3AuthError, FloX3NoStationsError
from .const import CONF_API_VERSION, CONF_STATION_ID, DOMAIN


class FloX3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a FLO charger using the unofficial cloud API."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._username = ""
        self._password = ""
        self._api_version = ""
        self._stations: dict[str, str] = {}
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Authenticate and retrieve the user's stations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_create_clientsession(
                self.hass,
                auto_cleanup=False,
                cookie_jar=aiohttp.CookieJar(),
            )
            client = FloX3ApiClient(
                session,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                stations, self._api_version = await client.async_get_stations()
            except FloX3AuthError:
                errors["base"] = "invalid_auth"
            except FloX3NoStationsError:
                return self.async_abort(reason="no_stations")
            except FloX3ApiError, aiohttp.ClientError, TimeoutError:
                errors["base"] = "cannot_connect"
            finally:
                session.detach()

            if not errors:
                self._username = user_input[CONF_USERNAME]
                self._password = user_input[CONF_PASSWORD]
                self._stations = {
                    station["information"]["id"]: station["information"]["name"]
                    for station in stations
                }
                return await self.async_step_station()

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_USERNAME): str,
                    probatio.Required(probatio.Secret(CONF_PASSWORD)): str,
                }
            ),
            errors=errors,
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select a station."""
        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
            await self.async_set_unique_id(station_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._stations[station_id],
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_STATION_ID: station_id,
                    CONF_API_VERSION: self._api_version,
                },
            )

        if not self._stations:
            return self.async_abort(reason="no_stations")

        return self.async_show_form(
            step_id="station",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_STATION_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": station_id, "label": station_name}
                                for station_id, station_name in self._stations.items()
                            ]
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement credentials."""
        errors: dict[str, str] = {}
        if user_input is not None and self._reauth_entry is not None:
            session = async_create_clientsession(
                self.hass,
                auto_cleanup=False,
                cookie_jar=aiohttp.CookieJar(),
            )
            client = FloX3ApiClient(
                session,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                stations, api_version = await client.async_get_stations()
            except FloX3AuthError:
                errors["base"] = "invalid_auth"
            except FloX3ApiError, aiohttp.ClientError, TimeoutError:
                errors["base"] = "cannot_connect"
            finally:
                session.detach()

            if not errors:
                station_id = self._reauth_entry.data[CONF_STATION_ID]
                if not any(
                    station["information"]["id"] == station_id for station in stations
                ):
                    errors["base"] = "station_not_found"
                else:
                    return self.async_update_reload_and_abort(
                        self._reauth_entry,
                        data_updates={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_API_VERSION: api_version,
                        },
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_USERNAME): str,
                    probatio.Required(probatio.Secret(CONF_PASSWORD)): str,
                }
            ),
            errors=errors,
        )
