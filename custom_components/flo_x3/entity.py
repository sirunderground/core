"""Base entity for FLO X3 entities."""

from typing import override

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FloX3Coordinator


class FloX3Entity(CoordinatorEntity[FloX3Coordinator]):
    """Base class for FLO X3 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FloX3Coordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.station_id}_{key}"

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        info = self.coordinator.data["station"]["information"]
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.station_id)},
            manufacturer="FLO",
            model=info.get("model", "FLO Home X3"),
            name=info.get("name"),
            sw_version=info.get("firmware"),
        )
