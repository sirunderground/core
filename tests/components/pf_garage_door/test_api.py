"""Tests for the PF Garage Door REST client."""

from http import HTTPStatus

import pytest

from homeassistant.components.pf_garage_door.pf_garage_door import (
    GarageDoorClient,
    GarageDoorError,
    Status,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from tests.test_util.aiohttp import AiohttpClientMocker

HOST = "garage-door.local"
API_ROOT = f"http://{HOST}"
STATUS_RESPONSE = {
    "name": "Garage Door",
    "serial_number": "123456789",
    "firmware": "1.0.0",
    "position": 35,
    "obstruction": False,
}


def create_client(hass: HomeAssistant) -> GarageDoorClient:
    """Create a garage door client for tests."""
    return GarageDoorClient(
        HOST,
        "username",
        "password",
        async_get_clientsession(hass),
    )


async def test_get_status(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test status retrieval and parsing."""
    aioclient_mock.get(f"{API_ROOT}/api/v1/status", json=STATUS_RESPONSE)

    status = await create_client(hass).get_status()

    assert status == Status(
        name="Garage Door",
        serial_number="123456789",
        firmware="1.0.0",
        position=35,
        obstruction=False,
    )
    assert aioclient_mock.mock_calls[0][0] == "GET"
    assert str(aioclient_mock.mock_calls[0][1]) == f"{API_ROOT}/api/v1/status"
    assert aioclient_mock.mock_calls[0][3]["Authorization"].startswith("Basic ")


async def test_cover_commands(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test position and stop requests."""
    aioclient_mock.put(
        f"{API_ROOT}/api/v1/cover/position", status=HTTPStatus.NO_CONTENT
    )
    aioclient_mock.post(f"{API_ROOT}/api/v1/cover/stop", status=HTTPStatus.NO_CONTENT)
    client = create_client(hass)

    await client.move_to(65)
    await client.stop()

    assert aioclient_mock.mock_calls[0][0] == "PUT"
    assert str(aioclient_mock.mock_calls[0][1]) == f"{API_ROOT}/api/v1/cover/position"
    assert aioclient_mock.mock_calls[0][2] == {"position": 65}
    assert aioclient_mock.mock_calls[1][0] == "POST"
    assert str(aioclient_mock.mock_calls[1][1]) == f"{API_ROOT}/api/v1/cover/stop"


async def test_subscription(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test subscription registration and removal."""
    subscription_id = "subscription-123"
    aioclient_mock.put(
        f"{API_ROOT}/api/v1/subscriptions",
        json={"id": subscription_id},
        status=HTTPStatus.CREATED,
    )
    aioclient_mock.delete(
        f"{API_ROOT}/api/v1/subscriptions",
        status=HTTPStatus.NO_CONTENT,
    )
    client = create_client(hass)

    assert (
        await client.register_subscription(
            "http://homeassistant.local:8123/api/webhook/webhook-123"
        )
        == subscription_id
    )
    await client.remove_subscription(subscription_id)

    assert aioclient_mock.mock_calls[0][0] == "PUT"
    assert str(aioclient_mock.mock_calls[0][1]) == f"{API_ROOT}/api/v1/subscriptions"
    assert aioclient_mock.mock_calls[0][2] == {
        "callback_url": "http://homeassistant.local:8123/api/webhook/webhook-123",
    }
    assert aioclient_mock.mock_calls[1][0] == "DELETE"
    assert str(aioclient_mock.mock_calls[1][1]) == f"{API_ROOT}/api/v1/subscriptions"
    assert aioclient_mock.mock_calls[1][2] == {"subscription_id": subscription_id}


async def test_invalid_subscription_response(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test malformed subscription responses are rejected."""
    aioclient_mock.put(
        f"{API_ROOT}/api/v1/subscriptions",
        json={"id": ""},
        status=HTTPStatus.CREATED,
    )

    with pytest.raises(GarageDoorError, match="Invalid subscription response"):
        await create_client(hass).register_subscription(
            "http://homeassistant.local:8123/api/webhook/webhook-123"
        )


async def test_invalid_status(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test malformed status responses are rejected."""
    aioclient_mock.get(
        f"{API_ROOT}/api/v1/status",
        json={**STATUS_RESPONSE, "position": 101},
    )

    with pytest.raises(GarageDoorError, match="Invalid status response"):
        await create_client(hass).get_status()


async def test_request_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test failed HTTP requests are reported."""
    aioclient_mock.get(
        f"{API_ROOT}/api/v1/status",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )

    with pytest.raises(GarageDoorError, match="Unable to GET"):
        await create_client(hass).get_status()
