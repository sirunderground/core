"""Sensors for FLO X3 chargers."""

from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
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
    """Set up FLO X3 sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            FloX3AmperageSensor(coordinator),
            FloX3AmperageOfferedSensor(coordinator),
            FloX3VoltageSensor(coordinator),
            FloX3EnergySensor(coordinator),
        ]
    )


class FloX3SessionSensor(FloX3Entity, SensorEntity):
    """Base sensor for session telemetry."""

    def __init__(self, coordinator: FloX3Coordinator, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, key)

    @property
    def _session(self) -> dict[str, Any]:
        """Return the current session, if available."""
        session = self.coordinator.data.get("session")
        return session if isinstance(session, dict) else {}

    def _number(self, key: str) -> float | None:
        """Return a numeric value from the active session."""
        value = self._session.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return None


class FloX3AmperageSensor(FloX3SessionSensor):
    """Measure current draw."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "amperage"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "amperage")

    @property
    @override
    def native_value(self) -> float | None:
        """Return current draw in amperes."""
        return self._number("amperage")


class FloX3AmperageOfferedSensor(FloX3SessionSensor):
    """Measure current offered to the vehicle."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "amperage_offered"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "amperage_offered")

    @property
    @override
    def native_value(self) -> float | None:
        """Return offered current in amperes."""
        return self._number("amperageOffer")


class FloX3VoltageSensor(FloX3SessionSensor):
    """Measure charging voltage."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "voltage"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "voltage")

    @property
    @override
    def native_value(self) -> float | None:
        """Return voltage."""
        return self._number("voltage")


class FloX3EnergySensor(FloX3SessionSensor):
    """Measure energy transferred in the current session."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_translation_key = "energy_transferred"

    def __init__(self, coordinator: FloX3Coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "energy_transferred")

    @property
    @override
    def native_value(self) -> float | None:
        """Return session energy in kilowatt-hours."""
        watt_hours = self._number("energyTransferredWh")
        return watt_hours / 1000 if watt_hours is not None else None
