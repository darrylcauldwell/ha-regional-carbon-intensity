"""Tests for UK Carbon Intensity config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aioukcarbon import (
    CarbonIntensityConnectionError,
    CarbonIntensityNoDataError,
)

from homeassistant import config_entries
from homeassistant.components.uk_carbon_intensity.const import CONF_POSTCODE, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_user_flow_success(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "DE45"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Carbon Intensity (DE45)"
    assert result["data"] == {CONF_POSTCODE: "DE45"}
    assert result["result"].unique_id == "DE45"


async def test_user_flow_normalizes_postcode(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test that postcode is normalized to uppercase."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: " de45 "},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_POSTCODE: "DE45"}


async def test_user_flow_invalid_postcode(hass: HomeAssistant) -> None:
    """Test invalid postcode format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "INVALID"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_postcode"}


async def test_user_flow_invalid_postcode_too_short(hass: HomeAssistant) -> None:
    """Test postcode that's too short."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "D"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_postcode"}


async def test_user_flow_no_data(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test postcode with no data available."""
    mock_config_flow_client.get_regional_intensity.side_effect = (
        CarbonIntensityNoDataError("No data")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "ZZ9"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_data"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test connection error during config flow."""
    mock_config_flow_client.get_regional_intensity.side_effect = (
        CarbonIntensityConnectionError("Connection failed")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "DE45"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unknown_error(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test unexpected error during config flow."""
    mock_config_flow_client.get_regional_intensity.side_effect = RuntimeError(
        "Unexpected"
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "DE45"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_flow_client: AsyncMock
) -> None:
    """Test that duplicate postcodes are rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_POSTCODE: "DE45"},
        unique_id="DE45",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "DE45"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_config_flow_client: AsyncMock,
) -> None:
    """Test successful reconfigure flow."""
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "SW1"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_POSTCODE] == "SW1"


async def test_reconfigure_flow_invalid_postcode(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure with invalid postcode."""
    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "INVALID"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_postcode"}


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_config_flow_client: AsyncMock,
) -> None:
    """Test reconfigure with connection error."""
    mock_config_flow_client.get_regional_intensity.side_effect = (
        CarbonIntensityConnectionError("Connection failed")
    )

    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "SW1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow_no_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_config_flow_client: AsyncMock,
) -> None:
    """Test reconfigure with no data error."""
    mock_config_flow_client.get_regional_intensity.side_effect = (
        CarbonIntensityNoDataError("No data")
    )

    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "ZZ9"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_data"}


async def test_reconfigure_flow_unknown_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_config_flow_client: AsyncMock,
) -> None:
    """Test reconfigure with unexpected error."""
    mock_config_flow_client.get_regional_intensity.side_effect = RuntimeError(
        "Unexpected"
    )

    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_POSTCODE: "SW1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test options flow sets update interval."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"update_interval": 15},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {"update_interval": 15}
