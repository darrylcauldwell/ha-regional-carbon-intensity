"""The UK Carbon Intensity integration."""

from __future__ import annotations

from pathlib import Path

from aioukcarbon import CarbonIntensityClient, CarbonIntensityConnectionError

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_POSTCODE, DOMAIN
from .coordinator import UKCarbonIntensityConfigEntry, UKCarbonIntensityCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

URL_BASE = "/uk_carbon_intensity"
CARD_URL = f"{URL_BASE}/uk-carbon-intensity-card.js"


async def async_setup_entry(
    hass: HomeAssistant, entry: UKCarbonIntensityConfigEntry
) -> bool:
    """Set up UK Carbon Intensity from a config entry."""
    session = async_get_clientsession(hass)
    client = CarbonIntensityClient(session=session)

    # Validate connectivity before creating coordinator
    try:
        await client.get_regional_intensity(entry.data[CONF_POSTCODE])
    except CarbonIntensityConnectionError as err:
        raise ConfigEntryNotReady from err

    coordinator = UKCarbonIntensityCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register frontend card (idempotent — safe with multiple config entries)
    await _async_register_card(hass)

    # Reload when options change (update interval)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: UKCarbonIntensityConfigEntry
) -> None:
    """Reload integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: UKCarbonIntensityConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the custom Lovelace card static path and JS resource."""
    hass.data.setdefault(DOMAIN + "_frontend", False)
    if hass.data[DOMAIN + "_frontend"]:
        return
    hass.data[DOMAIN + "_frontend"] = True

    frontend_path = str(Path(__file__).parent / "frontend")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, frontend_path, False)]
    )
    add_extra_js_url(hass, CARD_URL)
