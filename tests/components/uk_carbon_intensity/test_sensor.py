"""Tests for UK Carbon Intensity sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

from .conftest import MOCK_EMPTY_FORECAST, MOCK_REGIONAL_DATA_MISSING_FUEL


async def test_sensor_regional_intensity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test regional intensity sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_regional_carbon_intensity")
    assert state is not None
    assert state.state == "261"


async def test_sensor_regional_index(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test regional index sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_regional_carbon_index")
    assert state is not None
    assert state.state == "very_high"


async def test_sensor_national_intensity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test national intensity sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_national_carbon_intensity")
    assert state is not None
    assert state.state == "136"


async def test_sensor_national_index(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test national index sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_national_carbon_index")
    assert state is not None
    assert state.state == "moderate"


async def test_sensor_lowest_forecast(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test lowest forecast intensity sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.uk_carbon_intensity_lowest_forecast_intensity"
    )
    assert state is not None
    assert state.state == "180"


async def test_sensor_generation_wind(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test wind generation sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_wind_generation")
    assert state is not None
    assert state.state == "16.8"


async def test_sensor_generation_gas(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test gas generation sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_gas_generation")
    assert state is not None
    assert state.state == "60.2"


async def test_sensor_generation_solar(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test solar generation sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_solar_generation")
    assert state is not None
    assert state.state == "0.0"


async def test_sensor_generation_nuclear(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test nuclear generation sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_nuclear_generation")
    assert state is not None
    assert state.state == "1.3"


async def test_sensor_regional_intensity_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test regional intensity sensor extra attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_regional_carbon_intensity")
    assert state is not None
    attrs = state.attributes

    # Region name
    assert attrs["region"] == "East Midlands"

    # Generation mix
    assert isinstance(attrs["generationmix"], list)
    assert len(attrs["generationmix"]) == 9
    assert attrs["generationmix"][0] == {"fuel": "biomass", "perc": 19.4}

    # Forecast
    assert isinstance(attrs["forecast"], list)
    assert len(attrs["forecast"]) == 3
    assert attrs["forecast"][0]["forecast"] == 261
    assert attrs["forecast"][0]["index"] == "very high"
    assert attrs["forecast"][0]["from"] == "2026-03-04T21:00:00+00:00"
    assert attrs["forecast"][0]["to"] == "2026-03-04T21:30:00+00:00"


async def test_sensor_lowest_forecast_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test lowest forecast sensor extra attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.uk_carbon_intensity_lowest_forecast_intensity"
    )
    assert state is not None
    attrs = state.attributes

    # The lowest forecast in mock data is 180 at 22:00-22:30
    assert attrs["optimal_window_start"] == "2026-03-04T22:00:00+00:00"
    assert attrs["optimal_window_end"] == "2026-03-04T22:30:00+00:00"


async def test_sensor_empty_forecast_returns_unknown(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test lowest forecast returns unknown when forecast has no periods."""
    mock_client.get_regional_forecast = AsyncMock(return_value=MOCK_EMPTY_FORECAST)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.uk_carbon_intensity_lowest_forecast_intensity"
    )
    assert state is not None
    assert state.state == "unknown"


async def test_sensor_empty_forecast_no_optimal_window(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test lowest forecast has no optimal_window attributes with empty forecast."""
    mock_client.get_regional_forecast = AsyncMock(return_value=MOCK_EMPTY_FORECAST)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.uk_carbon_intensity_lowest_forecast_intensity"
    )
    assert state is not None
    assert "optimal_window_start" not in state.attributes
    assert "optimal_window_end" not in state.attributes


async def test_sensor_missing_fuel_type_returns_unknown(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test fuel type sensor returns unknown when fuel is missing from mix."""
    mock_client.get_regional_intensity = AsyncMock(
        return_value=MOCK_REGIONAL_DATA_MISSING_FUEL
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Solar is not in the missing fuel fixture
    state = hass.states.get("sensor.uk_carbon_intensity_solar_generation")
    assert state is not None
    assert state.state == "unknown"


async def test_sensor_without_attrs_fn(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test sensors without attrs_fn return no custom attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_wind_generation")
    assert state is not None
    # Should not have forecast or region attributes
    assert "region" not in state.attributes
    assert "forecast" not in state.attributes


async def test_sensor_low_carbon_percentage(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test low carbon percentage sensor computes correctly."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_low_carbon_percentage")
    assert state is not None
    # wind(16.8) + solar(0.0) + nuclear(1.3) + hydro(0.0) = 18.1
    assert state.state == "18.1"


async def test_sensor_fossil_percentage(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test fossil percentage sensor computes correctly."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.uk_carbon_intensity_fossil_fuel_percentage")
    assert state is not None
    # gas(60.2) + coal(0.0) = 60.2
    assert state.state == "60.2"
