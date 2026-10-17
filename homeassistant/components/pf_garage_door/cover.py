"""Cover platform for the PF Garage Door integration."""

from typing import Any, override

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GarageDoorConfigEntry, GarageDoorCoordinator
from .entity import GarageDoorEntity

ENTITY_DESCRIPTION = CoverEntityDescription(
    key="garage_door",
    translation_key="garage_door",
    device_class=CoverDeviceClass.GARAGE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageDoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the garage door cover."""
    async_add_entities([GarageDoorCover(entry.runtime_data)])


class GarageDoorCover(GarageDoorEntity, CoverEntity):
    """Control the garage door cover."""

    entity_description = ENTITY_DESCRIPTION
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: GarageDoorCoordinator) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial_number}_cover"

    @property
    @override
    def current_cover_position(self) -> int:
        """Return the current opening percentage."""
        return self.coordinator.data.position

    @property
    @override
    def is_closed(self) -> bool:
        """Return whether the door is closed."""
        return self.coordinator.data.position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the door fully."""
        await self._move_to(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the door fully."""
        await self._move_to(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the door opening percentage."""
        await self._move_to(kwargs[ATTR_POSITION])

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the door."""
        await self.coordinator.client.stop()
        await self.coordinator.async_request_refresh()

    async def _move_to(self, position: int) -> None:
        """Move the door to a position and refresh its reported state."""
        await self.coordinator.client.move_to(position)
        await self.coordinator.async_request_refresh()
