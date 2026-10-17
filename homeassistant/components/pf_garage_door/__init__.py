"""The Example Air integration."""

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import GarageDoorConfigEntry, GarageDoorCoordinator
from .pf_garage_door import GarageDoorClient

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: GarageDoorConfigEntry) -> bool:
    """Set up Example Air from a config entry."""
    client = GarageDoorClient(
        entry.data[CONF_HOST],
        session=async_get_clientsession(hass),
        username=entry.data["username"],
        password=entry.data["password"],
    )

    coordinator = GarageDoorCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarageDoorConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
