"""Config flow for EnedisLinky integration."""
from homeassistant.core import T
import logging
import os
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from .const import (
    DOMAIN,
    CONF_DEVICE_PATH,
    CONF_DEVICE_NAME,
)  # pylint:disable=unused-import

import serial.tools.list_ports


_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnedisLinky."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_UNKNOWN

    def __init__(self):
        """Initialize flow instance."""
        self._device_path = None
        self._radio_type = None

    async def async_step_user(self, user_input=None):
        """Handle a teleinfo config flow start."""
        errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)

        list_of_ports = [
            f"{p}, s/n: {p.serial_number or 'n/a'}"
            + (f" - {p.manufacturer}" if p.manufacturer else "")
            for p in ports
        ]
        list_of_ports.append("Testing")
        print("list_of_ports", list_of_ports)
        if len(list_of_ports) == 0:
            errors[
                "base"
            ] = "No serial device is detected, please plug the teleinfo dongle"

        if user_input is not None:
            print("user input", user_input)
            user_selection = user_input[CONF_DEVICE_PATH]

            if not user_selection == "Testing":

                port = ports[list_of_ports.index(user_selection)]
                dev_path = await self.hass.async_add_executor_job(
                    get_serial_by_id, port.device
                )
            else:

                class Port(object):
                    def __init__(self) -> None:
                        self.description = "FTDI"
                        self.serial_number = "XXXX"
                        self.manufacturer = "ANas"

                port = Port()

            auto_detected_data = {
                CONF_DEVICE_NAME: "TATA",
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
            }

            if True:
                title = f"EDF TeleInfo : {port.description}, s/n: {port.serial_number or 'n/a'}"
                title += f" - {port.manufacturer}" if port.manufacturer else ""
                return self.async_create_entry(
                    title=title,
                    data=auto_detected_data,
                )

        DATA_SCHEMA = vol.Schema(
            {vol.Required(CONF_DEVICE_PATH): vol.In(list_of_ports)}
        )
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path
