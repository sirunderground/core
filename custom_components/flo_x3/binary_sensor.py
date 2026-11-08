"""Binary sensors for FLO X3 chargers."""

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FloX3ConfigEntry
from .coordinator import FloX3Coordinator
from .entity import FloX3Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FloX3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FLO X3 binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            FloX3OnlineSensor(coordinator),
            FloX3VehicleConnectedSensor(coordinator),
            FloX3ChargingSensor(coordinator),
        ]
    )


class FloX3BinarySensor(FloX3Entity, BinarySensorEntity):
    """Base FLO X3 binary sensor."""

    def __init__(self, coordinator: FloX3Coordinator, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, key)

    @property
    def _station_status(self) -> dict[str, Any]:
        """Return the station status object."""
        status = self.coordinator.data["station"].get("status", {})
        return status if isinstance(status, dict) else {}


class FloX3OnlineSensor(FloX3BinarySensor):
    """Report whether the charger is online."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "online")

    @property
    def is_on(self) -> bool:
        """Return whether the charger is online."""
        return self._station_status.get("state") in {"Available", "InUse"}


class FloX3VehicleConnectedSensor(FloX3BinarySensor):
    """Report whether a vehicle is connected."""

    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_translation_key = "vehicle_connected"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "vehicle_connected")

    @property
    def is_on(self) -> bool:
        """Return whether a vehicle is connected."""
        return self._station_status.get("pilotSignalState") in {"B", "C"}


class FloX3ChargingSensor(FloX3BinarySensor):
    """Report whether the charger is charging."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = "charging"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging")

    @property
    def is_on(self) -> bool:
        """Return whether a charging session is active."""
        session = self.coordinator.data.get("session")
        return (
            isinstance(session, dict) and session.get("sessionState") == "Charging"
        ) or self._station_status.get("pilotSignalState") == "C"
