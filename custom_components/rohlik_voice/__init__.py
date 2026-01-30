"""Rohlik Voice Assistant integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    CONF_ROHLIK_EMAIL,
    CONF_ROHLIK_PASSWORD,
    CONF_OPENAI_API_KEY,
    PLATFORMS,
)
from .mcp_client import RohlikMCPClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rohlik Voice Assistant from a config entry."""
    _LOGGER.info("Setting up Rohlik Voice Assistant v2.0")

    # Get credentials from config entry (stored encrypted)
    email = entry.data[CONF_ROHLIK_EMAIL]
    password = entry.data[CONF_ROHLIK_PASSWORD]
    api_key = entry.data[CONF_OPENAI_API_KEY]

    # Create MCP client
    mcp_client = RohlikMCPClient(email, password)

    # Test connection
    try:
        if not await mcp_client.test_connection():
            raise ConfigEntryNotReady("Failed to connect to Rohlik MCP server")
    except Exception as err:
        await mcp_client.close()
        raise ConfigEntryNotReady(f"Error connecting to Rohlik: {err}") from err

    # Store in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "mcp_client": mcp_client,
        "openai_api_key": api_key,
    }

    # Set up platforms (conversation agent)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Rohlik Voice Assistant setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Rohlik Voice Assistant")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Close MCP client
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        mcp_client = hass.data[DOMAIN][entry.entry_id].get("mcp_client")
        if mcp_client:
            await mcp_client.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
