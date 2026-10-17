"""Client and status model for the PF Garage Door integration."""

from aiohttp import ClientSession

from homeassistant.components.event import dataclass


@dataclass
class Status:  # noqa: D101
    name: str
    serial_number: str
    firmware: str
    position: int
    obstruction: bool


class GarageDoorError(Exception):
    """Base class for garage door errors."""


class GarageDoorClient:
    """Client for the Garage Door API."""

    def __init__(
        self, host: str, username: str, password: str, session: ClientSession
    ) -> None:
        """Initialize the client."""

    async def get_status(self) -> Status:
        """Return the current status of the monitor."""
