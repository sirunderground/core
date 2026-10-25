"""Tests for the PF Garage Door integration setup and webhook."""

from datetime import timedelta
from http import HTTPStatus

from homeassistant.components.pf_garage_door.const import CONF_SUBSCRIPTION_ID, DOMAIN
from homeassistant.components.pf_garage_door.pf_garage_door import Status
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed, async_setup_component
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

HOST = "garage-door.local"
API_ROOT = f"http://{HOST}"
WEBHOOK_ID = "0123456789abcdef" * 4
SUBSCRIPTION_ID = "abcdef0123456789" * 4
STATUS_RESPONSE = {
    "name": "Garage Door",
    "serial_number": "123456789",
    "firmware": "1.0.0",
    "position": 35,
    "obstruction": False,
}


async def test_webhook_updates_status(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test pushed status updates are accepted and update the coordinator."""
    assert await async_setup_component(hass, "http", {})
    await async_process_ha_core_config(
        hass, {"internal_url": "http://homeassistant.local:8123"}
    )
    aioclient_mock.get(f"http://{HOST}/api/v1/status", json=STATUS_RESPONSE)
    aioclient_mock.put(
        f"{API_ROOT}/api/v1/subscriptions",
        status=HTTPStatus.NO_CONTENT,
    )
    aioclient_mock.delete(
        f"{API_ROOT}/api/v1/subscriptions",
        status=HTTPStatus.NO_CONTENT,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": HOST,
            "username": "username",
            "password": "password",
            CONF_WEBHOOK_ID: WEBHOOK_ID,
            CONF_SUBSCRIPTION_ID: SUBSCRIPTION_ID,
        },
        unique_id=STATUS_RESPONSE["serial_number"],
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = entry.runtime_data
    assert aioclient_mock.mock_calls[1][0] == "PUT"
    assert str(aioclient_mock.mock_calls[1][1]) == f"{API_ROOT}/api/v1/subscriptions"
    assert aioclient_mock.mock_calls[1][2] == {
        "subscription_id": SUBSCRIPTION_ID,
        "callback_url": f"http://homeassistant.local:8123/api/webhook/{WEBHOOK_ID}",
    }

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1, seconds=1))
    await hass.async_block_till_done()
    assert [call[0] for call in aioclient_mock.mock_calls if call[0] == "PUT"] == [
        "PUT",
        "PUT",
    ]

    client = await hass_client_no_auth()
    pushed_status = {
        **STATUS_RESPONSE,
        "position": 100,
        "obstruction": True,
    }
    response = await client.post(
        f"/api/webhook/{WEBHOOK_ID}",
        json=pushed_status,
    )

    assert response.status == HTTPStatus.NO_CONTENT
    assert coordinator.data == Status(
        name="Garage Door",
        serial_number="123456789",
        firmware="1.0.0",
        position=100,
        obstruction=True,
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert aioclient_mock.mock_calls[-1][0] == "DELETE"
    assert str(aioclient_mock.mock_calls[-1][1]) == (f"{API_ROOT}/api/v1/subscriptions")
    assert aioclient_mock.mock_calls[-1][2] == {"subscription_id": SUBSCRIPTION_ID}
    response = await client.post(
        f"/api/webhook/{WEBHOOK_ID}",
        json={**pushed_status, "position": 20},
    )
    assert response.status == HTTPStatus.OK
    assert coordinator.data.position == 100


async def test_webhook_rejects_invalid_status(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test invalid pushed status payloads are rejected."""
    assert await async_setup_component(hass, "http", {})
    await async_process_ha_core_config(
        hass, {"internal_url": "http://homeassistant.local:8123"}
    )
    aioclient_mock.get(f"http://{HOST}/api/v1/status", json=STATUS_RESPONSE)
    aioclient_mock.put(
        f"{API_ROOT}/api/v1/subscriptions",
        status=HTTPStatus.NO_CONTENT,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": HOST,
            "username": "username",
            "password": "password",
            CONF_WEBHOOK_ID: WEBHOOK_ID,
            CONF_SUBSCRIPTION_ID: SUBSCRIPTION_ID,
        },
        unique_id=STATUS_RESPONSE["serial_number"],
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    client = await hass_client_no_auth()
    response = await client.post(
        f"/api/webhook/{WEBHOOK_ID}",
        json={**STATUS_RESPONSE, "position": 101},
    )

    assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert entry.runtime_data.data.position == 35
