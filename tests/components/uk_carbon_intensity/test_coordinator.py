"""Tests for UK Carbon Intensity data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aioukcarbon import (
    CarbonIntensityConnectionError,
    CarbonIntensityError,
    CarbonIntensityTimeoutError,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from tests.common import MockConfigEntry

from .conftest import (
    MOCK_ALL_REGIONS_CURRENT,
    MOCK_ALL_REGIONS_FORECAST,
    MOCK_FORECAST_DATA,
    MOCK_GENERATION_MIX,
    MOCK_NATIONAL_INTENSITY,
    MOCK_REGIONAL_DATA,
)


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test successful coordinator update."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.data is not None
    assert coordinator.data.regional.regionid == 9
    assert coordinator.data.national.intensity.forecast == 136
    assert len(coordinator.data.generation_mix.generationmix) == 9
    assert len(coordinator.data.forecast.periods) == 3


async def test_coordinator_update_timeout(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test coordinator handles timeout errors."""
    # First call succeeds (setup), then timeout on refresh
    mock_client.get_regional_intensity.side_effect = [
        MOCK_REGIONAL_DATA,
        CarbonIntensityTimeoutError("Timeout"),
    ]

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_update_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test coordinator handles connection errors."""
    mock_client.get_regional_intensity.side_effect = [
        MOCK_REGIONAL_DATA,
        CarbonIntensityConnectionError("Connection failed"),
    ]

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_update_generic_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test coordinator handles generic API errors."""
    mock_client.get_regional_intensity.side_effect = [
        MOCK_REGIONAL_DATA,
        CarbonIntensityError("Something went wrong"),
    ]

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_partial_failure_forecast(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test forecast failure falls back to previous data."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.data.forecast is not None
    assert len(coordinator.data.forecast.periods) == 3

    # Now make forecast fail on next refresh
    mock_client.get_regional_forecast.side_effect = CarbonIntensityError("Forecast down")

    await coordinator.async_refresh()

    # Should still succeed (regional worked) and forecast falls back
    assert coordinator.last_update_success is True
    assert coordinator.data.forecast is not None
    assert len(coordinator.data.forecast.periods) == 3


async def test_coordinator_partial_failure_national(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test national failure falls back to previous data."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.data.national is not None

    # Now make national fail on next refresh
    mock_client.get_national_intensity.side_effect = CarbonIntensityError(
        "National down"
    )

    await coordinator.async_refresh()

    # Should still succeed and national falls back
    assert coordinator.last_update_success is True
    assert coordinator.data.national is not None
    assert coordinator.data.national.intensity.forecast == 136


async def test_coordinator_all_regions_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test all-regions comparison data is computed correctly."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.data.all_regions is not None
    assert len(coordinator.data.all_regions.regions) == 2

    # North Scotland (region 1) should have current=5
    r1 = next(r for r in coordinator.data.all_regions.regions if r.regionid == 1)
    assert r1.current_forecast == 5
    assert r1.current_index == "very low"
    assert r1.shortname == "North Scotland"
    # avg_24h = (5+8+3)/3 = 5.3, avg_48h = same (only 3 periods)
    assert r1.avg_24h == 5.3
    assert r1.avg_48h == 5.3

    # East Midlands (region 9) should have current=261
    r9 = next(r for r in coordinator.data.all_regions.regions if r.regionid == 9)
    assert r9.current_forecast == 261
    # avg_24h = (261+237+180)/3 = 226.0
    assert r9.avg_24h == 226.0


async def test_coordinator_all_regions_fallback(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test all-regions data falls back on failure."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.data.all_regions is not None

    # Make all-regions fail on next refresh
    mock_client.get_all_regions_current.side_effect = CarbonIntensityError(
        "All regions down"
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.all_regions is not None
    assert len(coordinator.data.all_regions.regions) == 2


async def test_coordinator_regional_failure_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test regional failure raises UpdateFailed."""
    mock_client.get_regional_intensity.side_effect = [
        MOCK_REGIONAL_DATA,
        CarbonIntensityError("Regional down"),
    ]

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
