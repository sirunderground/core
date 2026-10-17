"""Coordinator for the Example Air integration."""

from datetime import timedelta
import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .pf_garage_door import GarageDoorClient, GarageDoorError, Status

_LOGGER = logging.getLogger(__name__)

type GarageDoorConfigEntry = ConfigEntry[GarageDoorCoordinator]


class GarageDoorCoordinator(DataUpdateCoordinator[Status]):
    """Fetch the status of an Garage Door Monitor."""

    config_entry: GarageDoorConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: GarageDoorConfigEntry,
        client: GarageDoorClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.client = client

    @override
    async def _async_update_data(self) -> Status:
        """Fetch the latest status from the monitor."""
        try:
            return await self.client.get_status()
        except GarageDoorError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
            ) from err
