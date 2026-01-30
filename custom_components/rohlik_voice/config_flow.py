"""Config flow for Rohlik Voice Assistant integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_ROHLIK_EMAIL,
    CONF_ROHLIK_PASSWORD,
    CONF_OPENAI_API_KEY,
)
from .mcp_client import RohlikMCPClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ROHLIK_EMAIL): str,
        vol.Required(CONF_ROHLIK_PASSWORD): str,
        vol.Required(CONF_OPENAI_API_KEY): str,
    }
)


async def validate_rohlik_credentials(
    hass: HomeAssistant, email: str, password: str
) -> bool:
    """Validate Rohlik credentials by testing the connection."""
    client = RohlikMCPClient(email, password)
    try:
        result = await client.test_connection()
        return result
    finally:
        await client.close()


async def validate_openai_key(api_key: str) -> bool:
    """Validate OpenAI API key format."""
    # Basic validation - key should start with sk- and be reasonably long
    if not api_key:
        return False
    if not api_key.startswith("sk-"):
        return False
    if len(api_key) < 20:
        return False
    return True


class RohlikVoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rohlik Voice Assistant."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate inputs
            email = user_input[CONF_ROHLIK_EMAIL]
            password = user_input[CONF_ROHLIK_PASSWORD]
            api_key = user_input[CONF_OPENAI_API_KEY]

            # Check if already configured
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            # Validate OpenAI key format
            if not await validate_openai_key(api_key):
                errors["base"] = "invalid_openai_key"
            else:
                # Validate Rohlik credentials
                try:
                    valid = await validate_rohlik_credentials(
                        self.hass, email, password
                    )
                    if not valid:
                        errors["base"] = "invalid_auth"
                except Exception as err:
                    _LOGGER.exception("Unexpected exception during validation")
                    errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"Rohlik ({email})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "rohlik_url": "https://www.rohlik.cz",
                "openai_url": "https://platform.openai.com/api-keys",
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
