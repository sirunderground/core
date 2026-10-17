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
        self._host = host
        self._username = username
        self._password = password
        self._session = session

    async def get_status(self) -> Status:
        """Return the current status of the monitor."""
        return Status(
            name="Garage Door",
            serial_number="123456789",
            firmware="1.0.0",
            position=0,
            obstruction=False,
        )

    async def move_to(self, position: int) -> None:
        """Move the door to an opening percentage from 0 (closed) to 100 (open).

        Implement the controller's position request here using its HTTP API.
        """
        raise GarageDoorError("Garage door position control is not implemented")

    async def stop(self) -> None:
        """Stop the door using the controller's HTTP API."""
        raise GarageDoorError("Garage door stop control is not implemented")
