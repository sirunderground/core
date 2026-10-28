"""Base entity for the Example Air integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GarageDoorCoordinator


class GarageDoorEntity(CoordinatorEntity[GarageDoorCoordinator]):
    """Base class for Example Air entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GarageDoorCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        status = coordinator.data

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, status.serial_number)},
            manufacturer="AmbiQuébec",
            model="PF Garage Door",
            name=status.name,
            serial_number=status.serial_number,
            sw_version=status.firmware,
        )
