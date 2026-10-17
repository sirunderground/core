from typing import Any

from aiohttp import ClientSession

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.components.event import dataclass


@dataclass
class Status:  # noqa: D101
    name: str
    firmware: str
    position: int
    obstruction: bool


class GarageDoorError(Exception):
    """Base class for garage door errors."""


class GarageDoorClient:
    def __init__(
        self, host: str, username: str, password: str, session: ClientSession
    ) -> None:
        """Initialize the client."""

    async def get_status(self) -> Status:
        """Return the current status of the monitor."""


class PFGarageDoor(CoverEntity):
    """A garage that moves to a position."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, device: Controller) -> None:
        """Set up the blind."""
        self._device = device
        self._attr_unique_id = device.serial

    @property
    def current_cover_position(self) -> int:
        """Return the position, 0 is closed."""
        return self._device.position

    @property
    def is_closed(self) -> bool:
        """Return if the blind is closed."""
        return self._device.position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the blind."""
        await self._device.move_to(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the blind."""
        await self._device.move_to(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the blind to a position."""
        await self._device.move_to(kwargs[ATTR_POSITION])

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the blind."""
        await self._device.stop()
