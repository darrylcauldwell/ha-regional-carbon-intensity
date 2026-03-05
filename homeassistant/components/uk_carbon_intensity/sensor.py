"""Sensor platform for UK Carbon Intensity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import (
    UKCarbonIntensityConfigEntry,
    UKCarbonIntensityCoordinator,
    UKCarbonIntensityData,
)
from .entity import UKCarbonIntensityEntity

PARALLEL_UPDATES = 0

CARBON_INTENSITY_UNIT = "gCO2eq/kWh"

LOW_CARBON_FUELS = {"wind", "solar", "nuclear", "hydro"}
FOSSIL_FUELS = {"gas", "coal"}


def _get_fuel_perc(
    data: UKCarbonIntensityData, fuel: str
) -> float | None:
    """Get the percentage for a fuel type from the regional generation mix."""
    for gen in data.regional.periods[0].generationmix:
        if gen.fuel == fuel:
            return gen.perc
    return None


def _get_low_carbon_percentage(data: UKCarbonIntensityData) -> float | None:
    """Get the total low-carbon percentage from the regional generation mix."""
    total = 0.0
    found = False
    for gen in data.regional.periods[0].generationmix:
        if gen.fuel in LOW_CARBON_FUELS:
            total += gen.perc
            found = True
    return total if found else None


def _get_fossil_percentage(data: UKCarbonIntensityData) -> float | None:
    """Get the total fossil fuel percentage from the regional generation mix."""
    total = 0.0
    found = False
    for gen in data.regional.periods[0].generationmix:
        if gen.fuel in FOSSIL_FUELS:
            total += gen.perc
            found = True
    return total if found else None


def _get_lowest_forecast(data: UKCarbonIntensityData) -> int | None:
    """Get the lowest forecast intensity from the 24h forecast."""
    if not data.forecast or not data.forecast.periods:
        return None
    return min(p.intensity.forecast for p in data.forecast.periods)


def _get_regional_attrs(data: UKCarbonIntensityData) -> dict[str, Any]:
    """Get extra attributes for the regional intensity sensor."""
    attrs: dict[str, Any] = {
        "region": data.regional.shortname,
        "generationmix": [
            {"fuel": g.fuel, "perc": g.perc}
            for g in data.regional.periods[0].generationmix
        ],
    }
    if data.forecast and data.forecast.periods:
        attrs["forecast"] = [
            {
                "from": p.from_time.isoformat(),
                "to": p.to_time.isoformat(),
                "forecast": p.intensity.forecast,
                "index": p.intensity.index,
            }
            for p in data.forecast.periods
        ]
    return attrs


def _get_lowest_forecast_attrs(data: UKCarbonIntensityData) -> dict[str, Any]:
    """Get extra attributes for the lowest forecast sensor."""
    if not data.forecast or not data.forecast.periods:
        return {}
    lowest = min(data.forecast.periods, key=lambda p: p.intensity.forecast)
    return {
        "optimal_window_start": lowest.from_time.isoformat(),
        "optimal_window_end": lowest.to_time.isoformat(),
    }


@dataclass(frozen=True, kw_only=True)
class UKCarbonIntensitySensorDescription(SensorEntityDescription):
    """Describes a UK Carbon Intensity sensor entity."""

    value_fn: Callable[[UKCarbonIntensityData], StateType]
    attrs_fn: Callable[[UKCarbonIntensityData], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[UKCarbonIntensitySensorDescription, ...] = (
    # Regional intensity
    UKCarbonIntensitySensorDescription(
        key="regional_intensity",
        translation_key="regional_intensity",
        native_unit_of_measurement=CARBON_INTENSITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.regional.periods[0].intensity.forecast,
        attrs_fn=_get_regional_attrs,
    ),
    UKCarbonIntensitySensorDescription(
        key="regional_index",
        translation_key="regional_index",
        device_class=SensorDeviceClass.ENUM,
        options=["very_low", "low", "moderate", "high", "very_high"],
        value_fn=lambda data: data.regional.periods[0].intensity.index.replace(
            " ", "_"
        ),
    ),
    # National intensity
    UKCarbonIntensitySensorDescription(
        key="national_intensity",
        translation_key="national_intensity",
        native_unit_of_measurement=CARBON_INTENSITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.national.intensity.forecast
        if data.national
        else None,
    ),
    UKCarbonIntensitySensorDescription(
        key="national_index",
        translation_key="national_index",
        device_class=SensorDeviceClass.ENUM,
        options=["very_low", "low", "moderate", "high", "very_high"],
        value_fn=lambda data: data.national.intensity.index.replace(" ", "_")
        if data.national
        else None,
    ),
    # Lowest forecast
    UKCarbonIntensitySensorDescription(
        key="lowest_forecast_intensity",
        translation_key="lowest_forecast_intensity",
        native_unit_of_measurement=CARBON_INTENSITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_get_lowest_forecast,
        attrs_fn=_get_lowest_forecast_attrs,
    ),
    # Computed aggregate sensors
    UKCarbonIntensitySensorDescription(
        key="low_carbon_percentage",
        translation_key="low_carbon_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_get_low_carbon_percentage,
    ),
    UKCarbonIntensitySensorDescription(
        key="fossil_percentage",
        translation_key="fossil_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_get_fossil_percentage,
    ),
    # Generation mix - enabled by default
    UKCarbonIntensitySensorDescription(
        key="generation_wind",
        translation_key="generation_wind",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: _get_fuel_perc(data, "wind"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_solar",
        translation_key="generation_solar",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: _get_fuel_perc(data, "solar"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_gas",
        translation_key="generation_gas",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: _get_fuel_perc(data, "gas"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_nuclear",
        translation_key="generation_nuclear",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: _get_fuel_perc(data, "nuclear"),
    ),
    # Generation mix - disabled by default (diagnostic)
    UKCarbonIntensitySensorDescription(
        key="generation_biomass",
        translation_key="generation_biomass",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_fuel_perc(data, "biomass"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_coal",
        translation_key="generation_coal",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_fuel_perc(data, "coal"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_imports",
        translation_key="generation_imports",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_fuel_perc(data, "imports"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_hydro",
        translation_key="generation_hydro",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_fuel_perc(data, "hydro"),
    ),
    UKCarbonIntensitySensorDescription(
        key="generation_other",
        translation_key="generation_other",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_fuel_perc(data, "other"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UKCarbonIntensityConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up UK Carbon Intensity sensor entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        UKCarbonIntensitySensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class UKCarbonIntensitySensor(UKCarbonIntensityEntity, SensorEntity):
    """Sensor entity for UK Carbon Intensity."""

    entity_description: UKCarbonIntensitySensorDescription

    def __init__(
        self,
        coordinator: UKCarbonIntensityCoordinator,
        description: UKCarbonIntensitySensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
