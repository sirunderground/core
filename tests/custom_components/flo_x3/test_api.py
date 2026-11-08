"""Tests for the experimental FLO X3 API client."""

import time
from typing import Any, Self

from custom_components.flo_x3.api import FloX3ApiClient
import pytest


class MockResponse:
    """Minimal aiohttp response stub."""

    def __init__(self, data: Any, status: int = 200) -> None:
        """Initialize the response."""
        self.data = data
        self.status = status

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the response context."""

    async def json(self) -> Any:
        """Return the response payload."""
        return self.data


class MockSession:
    """Provide canned responses for client requests."""

    def __init__(self, responses: list[MockResponse]) -> None:
        """Initialize the session."""
        self.responses = iter(responses)
        self.urls: list[str] = []

    def get(self, url: str, **kwargs: Any) -> MockResponse:
        """Return the next response."""
        self.urls.append(url)
        return next(self.responses)


def _client(session: MockSession, version: str | None = None) -> FloX3ApiClient:
    """Create an authenticated client for request tests."""
    client = FloX3ApiClient(session, "user@example.com", "password", version)
    client._access_token = "test-token"
    client._token_expires_at = time.monotonic() + 60
    return client


@pytest.mark.asyncio
async def test_get_stations_falls_back_to_api_v30() -> None:
    """Use v3.0 when the newer API endpoint is not available."""
    station = {"information": {"id": "station-1", "name": "Garage"}}
    session = MockSession([MockResponse({}, 404), MockResponse([station])])
    client = _client(session)

    stations, version = await client.async_get_stations()

    assert stations == [station]
    assert version == "v3.0"
    assert session.urls == [
        "https://emobility.flo.ca/v3.1/user/stations",
        "https://emobility.flo.ca/v3.0/user/stations",
    ]


@pytest.mark.asyncio
async def test_get_charger_data_matches_station_session() -> None:
    """Return station and associated session payloads."""
    station = {
        "information": {"id": "station-1", "name": "Garage"},
        "status": {"state": "InUse", "pilotSignalState": "C"},
    }
    session_data = {
        "station": {"id": "station-1"},
        "sessionState": "Charging",
        "energyTransferredWh": 1250,
    }
    other_session = {"station": {"id": "other-station"}}
    session = MockSession(
        [MockResponse([station]), MockResponse([other_session, session_data])]
    )
    client = _client(session, "v3.1")

    actual_station, actual_session = await client.async_get_charger_data("station-1")

    assert actual_station == station
    assert actual_session == session_data


@pytest.mark.asyncio
async def test_get_charger_data_prefers_active_session() -> None:
    """Prefer a current session over an older completed session."""
    station = {"information": {"id": "station-1", "name": "Garage"}}
    old_session = {
        "station": {"id": "station-1"},
        "sessionState": "Completed",
    }
    active_session = {
        "station": {"id": "station-1"},
        "sessionState": "NotCharging",
    }
    session = MockSession(
        [
            MockResponse([station]),
            MockResponse([old_session, active_session]),
        ]
    )
    client = _client(session, "v3.0")

    _, actual_session = await client.async_get_charger_data("station-1")

    assert actual_session == active_session
