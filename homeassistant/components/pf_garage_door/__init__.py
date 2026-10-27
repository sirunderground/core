"""The Example Air integration."""

from datetime import datetime
from http import HTTPStatus
import logging
from typing import Any

from aiohttp import ContentTypeError, web

from homeassistant.components import webhook
from homeassistant.const import CONF_HOST, CONF_WEBHOOK_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.network import NoURLAvailableError

from .const import CONF_SUBSCRIPTION_ID, DOMAIN, SUBSCRIPTION_RENEW_INTERVAL
from .coordinator import GarageDoorConfigEntry, GarageDoorCoordinator
from .pf_garage_door import GarageDoorClient, GarageDoorError

_LOGGER = logging.getLogger(__name__)

_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: GarageDoorConfigEntry) -> bool:
    """Set up Example Air from a config entry."""
    entry_data: dict[str, Any] = {**entry.data}
    if CONF_WEBHOOK_ID not in entry_data:
        entry_data[CONF_WEBHOOK_ID] = webhook.async_generate_id()
    if entry_data != entry.data:
        hass.config_entries.async_update_entry(entry, data=entry_data)

    client = GarageDoorClient(
        entry.data[CONF_HOST],
        session=async_get_clientsession(hass),
        username=entry.data["username"],
        password=entry.data["password"],
    )

    coordinator = GarageDoorCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle a pushed garage door status update."""
        try:
            status = GarageDoorClient.parse_status(await request.json())
        except ValueError, ContentTypeError:
            return web.Response(status=HTTPStatus.BAD_REQUEST)
        except GarageDoorError:
            return web.Response(status=HTTPStatus.UNPROCESSABLE_ENTITY)

        if status.serial_number != coordinator.data.serial_number:
            return web.Response(status=HTTPStatus.UNPROCESSABLE_ENTITY)

        coordinator.async_set_updated_data(status)
        return web.Response(status=HTTPStatus.NO_CONTENT)

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        entry.data[CONF_WEBHOOK_ID],
        handle_webhook,
        local_only=True,
    )

    async def async_renew_subscription(_now: datetime | None = None) -> None:
        """Register the callback and renew its device-side lease."""
        try:
            callback_url = webhook.async_generate_url(
                hass,
                entry.data[CONF_WEBHOOK_ID],
                allow_external=False,
                allow_ip=True,
                prefer_external=False,
            )
        except NoURLAvailableError as err:
            _LOGGER.warning(
                "Unable to determine a local Home Assistant URL for the garage door "
                "status subscription; polling remains active: %s",
                err,
            )
            return

        try:
            subscription_id = await client.register_subscription(callback_url)
        except GarageDoorError as err:
            _LOGGER.warning(
                "Unable to register the garage door status subscription; polling "
                "remains active: %s",
                err,
            )
            return

        previous_subscription_id = entry.data.get(CONF_SUBSCRIPTION_ID)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_SUBSCRIPTION_ID: subscription_id},
        )
        if (
            previous_subscription_id is not None
            and previous_subscription_id != subscription_id
        ):
            try:
                await client.remove_subscription(previous_subscription_id)
            except GarageDoorError as err:
                _LOGGER.warning(
                    "Unable to remove the replaced garage door status subscription: %s",
                    err,
                )

    await async_renew_subscription()
    entry.async_on_unload(
        async_track_time_interval(
            hass,
            async_renew_subscription,
            SUBSCRIPTION_RENEW_INTERVAL,
            name=f"{DOMAIN} subscription renewal",
            cancel_on_shutdown=True,
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarageDoorConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    if subscription_id := entry.data.get(CONF_SUBSCRIPTION_ID):
        try:
            await entry.runtime_data.client.remove_subscription(subscription_id)
        except GarageDoorError as err:
            _LOGGER.warning(
                "Unable to remove the garage door status subscription: %s", err
            )

    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return True
