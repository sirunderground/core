"""Data update coordinator for FLO X3 chargers."""

import asyncio
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FloX3ApiClient, FloX3ApiError, FloX3AuthError
from .const import DOMAIN, LOGGER


class FloX3Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch FLO charger and session data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: FloX3ApiClient,
        station_id: str,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.station_id = station_id
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current data from FLO."""
        try:
            async with asyncio.timeout(30):
                station, session = await self.client.async_get_charger_data(
                    self.station_id
                )
        except FloX3AuthError as err:
            raise ConfigEntryAuthFailed from err
        except (FloX3ApiError, aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed from err
        return {"station": station, "session": session}
