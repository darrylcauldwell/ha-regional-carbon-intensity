"""Config flow for UK Carbon Intensity."""

from __future__ import annotations

import logging
import re
from typing import Any

from aioukcarbon import (
    CarbonIntensityClient,
    CarbonIntensityConnectionError,
    CarbonIntensityNoDataError,
)
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_POSTCODE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

POSTCODE_REGEX = re.compile(r"^[A-Z]{1,2}[0-9][0-9A-Z]?$")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POSTCODE): str,
    }
)


async def _validate_postcode(
    hass: HomeAssistant, postcode: str
) -> dict[str, str]:
    """Validate a postcode against the API. Returns errors dict."""
    errors: dict[str, str] = {}

    normalized = postcode.strip().upper()
    if not POSTCODE_REGEX.match(normalized):
        errors["base"] = "invalid_postcode"
        return errors

    session = async_get_clientsession(hass)
    client = CarbonIntensityClient(session=session)
    try:
        await client.get_regional_intensity(normalized)
    except CarbonIntensityNoDataError:
        errors["base"] = "no_data"
    except CarbonIntensityConnectionError:
        errors["base"] = "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected exception during validation")
        errors["base"] = "unknown"

    return errors


class UKCarbonIntensityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UK Carbon Intensity."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry,
    ) -> UKCarbonIntensityOptionsFlow:
        """Create the options flow."""
        return UKCarbonIntensityOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].strip().upper()
            errors = await _validate_postcode(self.hass, postcode)

            if not errors:
                await self.async_set_unique_id(postcode)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Carbon Intensity ({postcode})",
                    data={CONF_POSTCODE: postcode},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class UKCarbonIntensityOptionsFlow(OptionsFlow):
    """Handle options flow for UK Carbon Intensity."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_postcode = user_input[CONF_POSTCODE].strip().upper()
            current_postcode = self.config_entry.data.get(CONF_POSTCODE, "")

            if new_postcode != current_postcode:
                errors = await _validate_postcode(self.hass, new_postcode)

                if not errors:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=f"Carbon Intensity ({new_postcode})",
                        data={**self.config_entry.data, CONF_POSTCODE: new_postcode},
                    )

            if not errors:
                return self.async_create_entry(
                    data={CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL]},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POSTCODE,
                    default=self.config_entry.data.get(CONF_POSTCODE, ""),
                ): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): vol.All(int, vol.Range(min=10, max=120)),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
