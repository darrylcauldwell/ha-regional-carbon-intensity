"""Data update coordinator for UK Carbon Intensity."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from aioukcarbon import (
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


@dataclass
class UKCarbonIntensityData:
    """Data class for UK Carbon Intensity coordinator."""

    regional: RegionalData
    national: NationalIntensity | None = None
    generation_mix: NationalGenerationMix | None = None
    forecast: RegionalData | None = None


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
            self.client.get_regional_forecast(postcode),
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

        return UKCarbonIntensityData(
            regional=regional,
            national=national,
            generation_mix=generation_mix,
            forecast=forecast,
        )
