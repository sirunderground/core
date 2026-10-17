"""Sensor platform for the Example Air integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfRatio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GarageDoorConfigEntry, GarageDoorCoordinator
from .entity import GarageDoorEntity
from .pf_garage_door import Status


@dataclass(frozen=True, kw_only=True)
class GarageDoorSensorEntityDescription(SensorEntityDescription):
    """Describe a Garage Door sensor."""

    value_fn: Callable[[Status], float | int]


SENSORS: tuple[GarageDoorSensorEntityDescription, ...] = (
    GarageDoorSensorEntityDescription(
        key="position",
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.position,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageDoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Garage Door sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        GarageDoorSensor(coordinator, description) for description in SENSORS
    )


class GarageDoorSensor(GarageDoorEntity, SensorEntity):
    """A sensor of a Garage Door."""

    entity_description: GarageDoorSensorEntityDescription

    def __init__(
        self,
        coordinator: GarageDoorCoordinator,
        description: GarageDoorSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}_{description.key}"

    @property
    @override
    def native_value(self) -> float | int:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
