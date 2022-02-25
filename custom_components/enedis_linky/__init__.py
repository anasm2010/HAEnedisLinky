"""The EnedisLinky integration."""
import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_DOMAIN_DEVICE

from datetime import timedelta


CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["sensor"]  # , "teleinfo"]

SCAN_INTERVAL = timedelta(seconds=10)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the EnedisLinky component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up EnedisLinky from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
    print(entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = "None"

    print("async_setup_entry", entry)
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    print("async_unload_entry")
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        del hass.data[DOMAIN]

    return unload_ok
