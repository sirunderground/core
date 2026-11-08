"""The FLO Home X3 integration."""

from dataclasses import dataclass

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import FloX3ApiClient, FloX3ApiError, FloX3AuthError
from .const import CONF_API_VERSION, CONF_STATION_ID
from .coordinator import FloX3Coordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class FloX3RuntimeData:
    """Runtime data for the config entry."""

    client: FloX3ApiClient
    coordinator: FloX3Coordinator


type FloX3ConfigEntry = ConfigEntry[FloX3RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: FloX3ConfigEntry) -> None:
    """Set up a FLO X3 config entry."""
    session = async_create_clientsession(
        hass,
        auto_cleanup=False,
        cookie_jar=aiohttp.CookieJar(),
    )
    entry.async_on_unload(session.detach)
    client = FloX3ApiClient(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_API_VERSION],
    )
    coordinator = FloX3Coordinator(
        hass,
        entry,
        client,
        entry.data[CONF_STATION_ID],
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except (ConfigEntryAuthFailed, FloX3AuthError) as err:
        session.detach()
        raise ConfigEntryAuthFailed from err
    except (FloX3ApiError, aiohttp.ClientError, TimeoutError) as err:
        session.detach()
        raise ConfigEntryNotReady from err

    entry.runtime_data = FloX3RuntimeData(
        client=client,
        coordinator=coordinator,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: FloX3ConfigEntry) -> bool:
    """Unload a FLO X3 config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    return True
