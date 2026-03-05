"""Test fixtures for UK Carbon Intensity integration tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from aioukcarbon import (
    AllRegionsData,
    AllRegionsPeriod,
    GenerationFuel,
    Intensity,
    IntensityPeriod,
    NationalGenerationMix,
    NationalIntensity,
    RegionalData,
    RegionSummary,
)

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

POSTCODE = "DE45"
ENTRY_ID = "test_entry_id"

MOCK_REGIONAL_DATA = RegionalData(
    regionid=9,
    dnoregion="WPD East Midlands",
    shortname="East Midlands",
    postcode=POSTCODE,
    periods=[
        IntensityPeriod(
            from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            intensity=Intensity(forecast=261, index="very high"),
            generationmix=[
                GenerationFuel(fuel="biomass", perc=19.4),
                GenerationFuel(fuel="coal", perc=0.0),
                GenerationFuel(fuel="imports", perc=2.3),
                GenerationFuel(fuel="gas", perc=60.2),
                GenerationFuel(fuel="nuclear", perc=1.3),
                GenerationFuel(fuel="other", perc=0.0),
                GenerationFuel(fuel="hydro", perc=0.0),
                GenerationFuel(fuel="solar", perc=0.0),
                GenerationFuel(fuel="wind", perc=16.8),
            ],
        )
    ],
)

MOCK_NATIONAL_INTENSITY = NationalIntensity(
    from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
    to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
    intensity=Intensity(forecast=136, actual=136, index="moderate"),
)

MOCK_GENERATION_MIX = NationalGenerationMix(
    from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
    to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
    generationmix=[
        GenerationFuel(fuel="biomass", perc=8.0),
        GenerationFuel(fuel="coal", perc=0.0),
        GenerationFuel(fuel="imports", perc=14.6),
        GenerationFuel(fuel="gas", perc=29.6),
        GenerationFuel(fuel="nuclear", perc=9.8),
        GenerationFuel(fuel="other", perc=0.0),
        GenerationFuel(fuel="hydro", perc=0.0),
        GenerationFuel(fuel="solar", perc=0.0),
        GenerationFuel(fuel="wind", perc=37.9),
    ],
)

MOCK_FORECAST_DATA = RegionalData(
    regionid=9,
    dnoregion="WPD East Midlands",
    shortname="East Midlands",
    postcode=POSTCODE,
    periods=[
        IntensityPeriod(
            from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            intensity=Intensity(forecast=261, index="very high"),
            generationmix=[
                GenerationFuel(fuel="gas", perc=60.2),
                GenerationFuel(fuel="wind", perc=16.8),
            ],
        ),
        IntensityPeriod(
            from_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 22, 0, tzinfo=UTC),
            intensity=Intensity(forecast=237, index="very high"),
            generationmix=[
                GenerationFuel(fuel="gas", perc=53.6),
                GenerationFuel(fuel="wind", perc=20.7),
            ],
        ),
        IntensityPeriod(
            from_time=datetime(2026, 3, 4, 22, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 22, 30, tzinfo=UTC),
            intensity=Intensity(forecast=180, index="high"),
            generationmix=[
                GenerationFuel(fuel="gas", perc=40.0),
                GenerationFuel(fuel="wind", perc=37.0),
            ],
        ),
    ],
)

MOCK_EMPTY_FORECAST = RegionalData(
    regionid=9,
    dnoregion="WPD East Midlands",
    shortname="East Midlands",
    postcode=POSTCODE,
    periods=[],
)

MOCK_REGIONAL_DATA_MISSING_FUEL = RegionalData(
    regionid=9,
    dnoregion="WPD East Midlands",
    shortname="East Midlands",
    postcode=POSTCODE,
    periods=[
        IntensityPeriod(
            from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            intensity=Intensity(forecast=261, index="very high"),
            generationmix=[
                GenerationFuel(fuel="gas", perc=50.0),
                GenerationFuel(fuel="wind", perc=30.0),
                GenerationFuel(fuel="nuclear", perc=20.0),
            ],
        )
    ],
)


MOCK_ALL_REGIONS_CURRENT = AllRegionsData(
    periods=[
        AllRegionsPeriod(
            from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            regions=[
                RegionSummary(
                    regionid=1,
                    dnoregion="SSE South",
                    shortname="North Scotland",
                    intensity=Intensity(forecast=5, index="very low"),
                    generationmix=[
                        GenerationFuel(fuel="wind", perc=90.0),
                        GenerationFuel(fuel="hydro", perc=10.0),
                    ],
                ),
                RegionSummary(
                    regionid=9,
                    dnoregion="WPD East Midlands",
                    shortname="East Midlands",
                    intensity=Intensity(forecast=261, index="very high"),
                    generationmix=[
                        GenerationFuel(fuel="gas", perc=60.2),
                        GenerationFuel(fuel="wind", perc=16.8),
                    ],
                ),
            ],
        )
    ]
)

MOCK_ALL_REGIONS_FORECAST = AllRegionsData(
    periods=[
        AllRegionsPeriod(
            from_time=datetime(2026, 3, 4, 21, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            regions=[
                RegionSummary(
                    regionid=1,
                    dnoregion="SSE South",
                    shortname="North Scotland",
                    intensity=Intensity(forecast=5, index="very low"),
                    generationmix=[
                        GenerationFuel(fuel="wind", perc=90.0),
                    ],
                ),
                RegionSummary(
                    regionid=9,
                    dnoregion="WPD East Midlands",
                    shortname="East Midlands",
                    intensity=Intensity(forecast=261, index="very high"),
                    generationmix=[
                        GenerationFuel(fuel="gas", perc=60.2),
                    ],
                ),
            ],
        ),
        AllRegionsPeriod(
            from_time=datetime(2026, 3, 4, 21, 30, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 22, 0, tzinfo=UTC),
            regions=[
                RegionSummary(
                    regionid=1,
                    dnoregion="SSE South",
                    shortname="North Scotland",
                    intensity=Intensity(forecast=8, index="very low"),
                    generationmix=[
                        GenerationFuel(fuel="wind", perc=85.0),
                    ],
                ),
                RegionSummary(
                    regionid=9,
                    dnoregion="WPD East Midlands",
                    shortname="East Midlands",
                    intensity=Intensity(forecast=237, index="very high"),
                    generationmix=[
                        GenerationFuel(fuel="gas", perc=53.6),
                    ],
                ),
            ],
        ),
        AllRegionsPeriod(
            from_time=datetime(2026, 3, 4, 22, 0, tzinfo=UTC),
            to_time=datetime(2026, 3, 4, 22, 30, tzinfo=UTC),
            regions=[
                RegionSummary(
                    regionid=1,
                    dnoregion="SSE South",
                    shortname="North Scotland",
                    intensity=Intensity(forecast=3, index="very low"),
                    generationmix=[
                        GenerationFuel(fuel="wind", perc=95.0),
                    ],
                ),
                RegionSummary(
                    regionid=9,
                    dnoregion="WPD East Midlands",
                    shortname="East Midlands",
                    intensity=Intensity(forecast=180, index="high"),
                    generationmix=[
                        GenerationFuel(fuel="gas", perc=40.0),
                    ],
                ),
            ],
        ),
    ]
)


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain="uk_carbon_intensity",
        title="Carbon Intensity (DE45)",
        data={"postcode": POSTCODE},
        unique_id=POSTCODE,
        entry_id=ENTRY_ID,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_config_entry_with_options(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry with custom options."""
    entry = MockConfigEntry(
        domain="uk_carbon_intensity",
        title="Carbon Intensity (DE45)",
        data={"postcode": POSTCODE},
        options={"update_interval": 15},
        unique_id=POSTCODE,
        entry_id="test_entry_options",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Create a mock CarbonIntensityClient."""
    with (
        patch(
            "homeassistant.components.uk_carbon_intensity.CarbonIntensityClient",
            autospec=True,
        ) as mock_cls,
        patch(
            "homeassistant.components.uk_carbon_intensity._async_register_card",
        ),
    ):
        client = mock_cls.return_value
        client.get_regional_intensity = AsyncMock(return_value=MOCK_REGIONAL_DATA)
        client.get_national_intensity = AsyncMock(return_value=MOCK_NATIONAL_INTENSITY)
        client.get_generation_mix = AsyncMock(return_value=MOCK_GENERATION_MIX)
        client.get_regional_forecast = AsyncMock(return_value=MOCK_FORECAST_DATA)
        client.get_all_regions_current = AsyncMock(
            return_value=MOCK_ALL_REGIONS_CURRENT
        )
        client.get_all_regions_forecast = AsyncMock(
            return_value=MOCK_ALL_REGIONS_FORECAST
        )
        yield client


@pytest.fixture
def mock_config_flow_client() -> Generator[AsyncMock]:
    """Create a mock CarbonIntensityClient for config flow tests."""
    with patch(
        "homeassistant.components.uk_carbon_intensity.config_flow.CarbonIntensityClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.get_regional_intensity = AsyncMock(return_value=MOCK_REGIONAL_DATA)
        yield client
