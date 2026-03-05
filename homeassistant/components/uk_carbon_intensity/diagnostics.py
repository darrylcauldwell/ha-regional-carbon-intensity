"""Diagnostics support for UK Carbon Intensity."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_POSTCODE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .coordinator import UKCarbonIntensityConfigEntry

TO_REDACT = {CONF_POSTCODE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: UKCarbonIntensityConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data
    data = coordinator.data

    # Generation mix validation
    gen_total = None
    gen_valid = None
    if data.generation_mix:
        gen_total = sum(g.perc for g in data.generation_mix.generationmix)
        gen_valid = 99.0 <= gen_total <= 101.0

    # Build forecast data
    forecast_data: list[dict[str, Any]] | None = None
    if data.forecast and data.forecast.periods:
        forecast_data = [
            {
                "from": p.from_time.isoformat(),
                "to": p.to_time.isoformat(),
                "forecast": p.intensity.forecast,
                "index": p.intensity.index,
            }
            for p in data.forecast.periods
        ]

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "coordinator_info": {
            "last_updated": coordinator.last_update_success_time.isoformat()
            if coordinator.last_update_success_time
            else None,
            "update_interval_minutes": config_entry.options.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            ),
            "last_update_success": coordinator.last_update_success,
        },
        "coordinator_data": {
            "regional": asdict(data.regional),
            "national": asdict(data.national) if data.national else None,
            "generation_mix": asdict(data.generation_mix)
            if data.generation_mix
            else None,
            "forecast": forecast_data,
        },
        "validation": {
            "generation_mix_total": gen_total,
            "generation_mix_valid": gen_valid,
        },
    }
