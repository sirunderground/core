"""Client and status model for the PF Garage Door integration."""

from dataclasses import dataclass
import json
from typing import Any

import aiohttp
from aiohttp import ClientSession

API_VERSION = "/api/v1"
STATUS_ENDPOINT = f"{API_VERSION}/status"
POSITION_ENDPOINT = f"{API_VERSION}/cover/position"
STOP_ENDPOINT = f"{API_VERSION}/cover/stop"


@dataclass
class Status:
    """Status reported by the garage door controller."""

    name: str
    serial_number: str
    firmware: str
    position: int
    obstruction: bool


class GarageDoorError(Exception):
    """Base class for garage door errors."""


class GarageDoorClient:
    """Client for the PF Garage Door REST API.

    The API uses HTTP Basic authentication. It exposes GET /api/v1/status,
    returning ``name``, ``serial_number``, ``firmware``, ``position`` (0-100),
    and ``obstruction`` fields; PUT /api/v1/cover/position accepts a JSON
    ``position`` value, and POST /api/v1/cover/stop stops movement.
    """

    def __init__(
        self, host: str, username: str, password: str, session: ClientSession
    ) -> None:
        """Initialize the client."""
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        self._host = host.rstrip("/")
        self._authorization = aiohttp.encode_basic_auth(username, password)
        self._session = session

    async def get_status(self) -> Status:
        """Return the current status of the garage door."""
        data = await self._async_request("GET", STATUS_ENDPOINT, expect_json=True)
        if not isinstance(data, dict):
            raise GarageDoorError("Invalid status response")

        try:
            name = data["name"]
            serial_number = data["serial_number"]
            firmware = data["firmware"]
            position = data["position"]
            obstruction = data["obstruction"]
        except KeyError as err:
            raise GarageDoorError(f"Missing {err.args[0]} in status response") from err

        if (
            not isinstance(name, str)
            or not isinstance(serial_number, str)
            or not serial_number
            or not isinstance(firmware, str)
            or not isinstance(position, int)
            or isinstance(position, bool)
            or not 0 <= position <= 100
            or not isinstance(obstruction, bool)
        ):
            raise GarageDoorError("Invalid status response")

        return Status(name, serial_number, firmware, position, obstruction)

    async def move_to(self, position: int) -> None:
        """Move the door to an opening percentage from 0 (closed) to 100 (open)."""
        if not 0 <= position <= 100:
            raise ValueError("Position must be between 0 and 100")
        await self._async_request(
            "PUT", POSITION_ENDPOINT, payload={"position": position}
        )

    async def stop(self) -> None:
        """Stop the door."""
        await self._async_request("POST", STOP_ENDPOINT)

    async def _async_request(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, int] | None = None,
        expect_json: bool = False,
    ) -> Any:
        """Send an authenticated request to the controller."""
        try:
            async with self._session.request(
                method,
                f"{self._host}{endpoint}",
                headers={"Authorization": self._authorization},
                json=payload,
            ) as response:
                response.raise_for_status()
                if not expect_json:
                    return None
                return await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise GarageDoorError(f"Unable to {method} {endpoint}") from err
