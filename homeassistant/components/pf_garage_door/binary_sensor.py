"""Binary sensor platform for the PF Garage Door integration."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GarageDoorConfigEntry, GarageDoorCoordinator
from .entity import GarageDoorEntity

ENTITY_DESCRIPTION = BinarySensorEntityDescription(
    key="obstruction",
    translation_key="obstruction",
    device_class=BinarySensorDeviceClass.PROBLEM,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageDoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Garage Door binary sensor."""
    async_add_entities([GarageDoorObstructionSensor(entry.runtime_data)])


class GarageDoorObstructionSensor(GarageDoorEntity, BinarySensorEntity):
    """Represent whether the garage door has an obstruction."""

    entity_description = ENTITY_DESCRIPTION

    def __init__(self, coordinator: GarageDoorCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial_number}_obstruction"

    @property
    @override
    def is_on(self) -> bool:
        """Return whether an obstruction is detected."""
        return self.coordinator.data.obstruction
