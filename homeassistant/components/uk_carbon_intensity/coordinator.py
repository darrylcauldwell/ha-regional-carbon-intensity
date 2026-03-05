"""Data update coordinator for UK Carbon Intensity."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from aioukcarbon import (
    AllRegionsData,
    CarbonIntensityClient,
    CarbonIntensityConnectionError,
    CarbonIntensityError,
    CarbonIntensityTimeoutError,
    NationalGenerationMix,
    NationalIntensity,
    RegionalData,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_POSTCODE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type UKCarbonIntensityConfigEntry = ConfigEntry[UKCarbonIntensityCoordinator]

DNO_REGION_IDS = range(1, 15)  # IDs 1-14 are DNO regions; 15-18 are aggregates


@dataclass
class RegionComparisonEntry:
    """Comparison data for a single region."""

    regionid: int
    shortname: str
    current_forecast: int
    current_index: str
    avg_24h: float
    avg_48h: float


@dataclass
class AllRegionsComparisonData:
    """Comparison data across all regions."""

    regions: list[RegionComparisonEntry]
    updated_at: str


@dataclass
class UKCarbonIntensityData:
    """Data class for UK Carbon Intensity coordinator."""

    regional: RegionalData
    national: NationalIntensity | None = None
    generation_mix: NationalGenerationMix | None = None
    forecast: RegionalData | None = None
    all_regions: AllRegionsComparisonData | None = None


class UKCarbonIntensityCoordinator(DataUpdateCoordinator[UKCarbonIntensityData]):
    """Coordinator for fetching UK Carbon Intensity data."""

    config_entry: UKCarbonIntensityConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: UKCarbonIntensityConfigEntry,
        client: CarbonIntensityClient,
    ) -> None:
        """Initialize the coordinator."""
        interval = config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
        )
        self.client = client

    async def _async_update_data(self) -> UKCarbonIntensityData:
        """Fetch data from the Carbon Intensity API."""
        postcode = self.config_entry.data[CONF_POSTCODE]

        try:
            regional = await self.client.get_regional_intensity(postcode)
        except CarbonIntensityTimeoutError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="timeout_error",
            ) from err
        except CarbonIntensityConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        except CarbonIntensityError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"error": str(err)},
            ) from err

        # Fetch optional data concurrently; failures fall back to previous data
        results = await asyncio.gather(
            self.client.get_national_intensity(),
            self.client.get_generation_mix(),
            self.client.get_regional_forecast(postcode, hours=48),
            self.client.get_all_regions_current(),
            self.client.get_all_regions_forecast(hours=48),
            return_exceptions=True,
        )

        previous = self.data

        national = results[0]
        if isinstance(national, BaseException):
            _LOGGER.warning("Failed to fetch national intensity: %s", national)
            national = previous.national if previous else None

        generation_mix = results[1]
        if isinstance(generation_mix, BaseException):
            _LOGGER.warning("Failed to fetch generation mix: %s", generation_mix)
            generation_mix = previous.generation_mix if previous else None

        forecast = results[2]
        if isinstance(forecast, BaseException):
            _LOGGER.warning("Failed to fetch regional forecast: %s", forecast)
            forecast = previous.forecast if previous else None

        all_regions_current = results[3]
        all_regions_forecast = results[4]
        all_regions: AllRegionsComparisonData | None = None

        if isinstance(all_regions_current, BaseException) or isinstance(
            all_regions_forecast, BaseException
        ):
            if isinstance(all_regions_current, BaseException):
                _LOGGER.warning(
                    "Failed to fetch all-regions current: %s", all_regions_current
                )
            if isinstance(all_regions_forecast, BaseException):
                _LOGGER.warning(
                    "Failed to fetch all-regions forecast: %s", all_regions_forecast
                )
            all_regions = previous.all_regions if previous else None
        else:
            all_regions = self._compute_region_comparison(
                all_regions_current, all_regions_forecast
            )

        return UKCarbonIntensityData(
            regional=regional,
            national=national,
            generation_mix=generation_mix,
            forecast=forecast,
            all_regions=all_regions,
        )

    @staticmethod
    def _compute_region_comparison(
        current: AllRegionsData,
        forecast: AllRegionsData,
    ) -> AllRegionsComparisonData:
        """Compute region comparison from current and forecast data."""
        # Build current intensity map from first period
        current_map: dict[int, tuple[int, str]] = {}
        if current.periods:
            for region in current.periods[0].regions:
                if region.regionid in DNO_REGION_IDS:
                    current_map[region.regionid] = (
                        region.intensity.forecast,
                        region.intensity.index,
                    )

        # Build forecast averages per region
        # 48 periods = 24h, all periods = 48h (96 periods at 30min each)
        forecast_sums: dict[int, list[int]] = {}
        shortnames: dict[int, str] = {}

        for period in forecast.periods:
            for region in period.regions:
                if region.regionid not in DNO_REGION_IDS:
                    continue
                shortnames[region.regionid] = region.shortname
                forecast_sums.setdefault(region.regionid, []).append(
                    region.intensity.forecast
                )

        entries = []
        for rid in sorted(shortnames):
            forecasts = forecast_sums.get(rid, [])
            total = len(forecasts)
            half = min(total, 48)  # First 48 periods = 24h

            avg_24h = sum(forecasts[:half]) / half if half > 0 else 0.0
            avg_48h = sum(forecasts) / total if total > 0 else 0.0

            current_forecast, current_index = current_map.get(rid, (0, "unknown"))

            entries.append(
                RegionComparisonEntry(
                    regionid=rid,
                    shortname=shortnames[rid],
                    current_forecast=current_forecast,
                    current_index=current_index,
                    avg_24h=round(avg_24h, 1),
                    avg_48h=round(avg_48h, 1),
                )
            )

        return AllRegionsComparisonData(
            regions=entries,
            updated_at=current.periods[0].from_time.isoformat()
            if current.periods
            else "",
        )
