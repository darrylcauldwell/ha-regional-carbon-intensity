"""Tests for UK Carbon Intensity diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test diagnostics output with postcode redaction."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.components.uk_carbon_intensity.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Postcode should be redacted in config entry data
    assert diagnostics["config_entry"]["data"]["postcode"] == "**REDACTED**"

    # Coordinator data should be present
    assert "coordinator_data" in diagnostics
    assert diagnostics["coordinator_data"]["regional"]["regionid"] == 9

    # Coordinator info fields
    assert "coordinator_info" in diagnostics
    assert "last_updated" in diagnostics["coordinator_info"]
    assert diagnostics["coordinator_info"]["update_interval_minutes"] == 30
    assert diagnostics["coordinator_info"]["last_update_success"] is True

    # Full forecast data (not just count)
    assert diagnostics["coordinator_data"]["forecast"] is not None
    assert len(diagnostics["coordinator_data"]["forecast"]) == 3
    assert diagnostics["coordinator_data"]["forecast"][0]["forecast"] == 261

    # Validation section
    assert "validation" in diagnostics
    assert diagnostics["validation"]["generation_mix_total"] is not None
    # National gen mix total: 8.0+0.0+14.6+29.6+9.8+0.0+0.0+0.0+37.9 = 99.9
    assert 99.0 <= diagnostics["validation"]["generation_mix_total"] <= 101.0
    assert diagnostics["validation"]["generation_mix_valid"] is True
