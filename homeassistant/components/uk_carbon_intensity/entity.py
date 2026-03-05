"""Base entity for UK Carbon Intensity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UKCarbonIntensityCoordinator


class UKCarbonIntensityEntity(CoordinatorEntity[UKCarbonIntensityCoordinator]):
    """Base entity for UK Carbon Intensity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UKCarbonIntensityCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="UK Carbon Intensity",
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="National Energy System Operator",
        )
