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

# class PlaceholderHub:
#     """Placeholder class to make tests pass.

#     TODO Remove this placeholder class and replace with things from your PyPI package.
#     """

#     def __init__(self, host):
#         """Initialize."""
#         self.host = host

#     async def authenticate(self, username, password) -> bool:
#         """Test if we can authenticate with the host."""
#         return True


# async def validate_input(hass: core.HomeAssistant, data):
#     """Validate the user input allows us to connect.

#     Data has the keys from DATA_SCHEMA with values provided by the user.
#     """
#     # TODO validate the data can be used to set up a connection.

#     # If your PyPI package is not built with async, pass your methods
#     # to the executor:
#     # await hass.async_add_executor_job(
#     #     your_validate_func, data["username"], data["password"]
#     # )

#     hub = PlaceholderHub(data["host"])

#     if not await hub.authenticate(data["username"], data["password"]):
#         raise InvalidAuth

#     # If you cannot connect:
#     # throw CannotConnect
#     # If the authentication is wrong:
#     # InvalidAuth

#     # Return info that you want to store in the config entry.
#     return {"title": "EDF TeleInfo"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnedisLinky."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_UNKNOWN

    def __init__(self):
        """Initialize flow instance."""
        self._device_path = None
        self._radio_type = None

    # async def async_step_user(self, user_input=None):
    #     """Handle the initial step."""
    #     errors = {}
    #     if user_input is not None:
    #         try:
    #             info = await validate_input(self.hass, user_input)

    #             return self.async_create_entry(title=info["title"], data=user_input)
    #         except CannotConnect:
    #             errors["base"] = "cannot_connect"
    #         except InvalidAuth:
    #             errors["base"] = "invalid_auth"
    #         except Exception:  # pylint: disable=broad-except
    #             _LOGGER.exception("Unexpected exception")
    #             errors["base"] = "unknown"

    #     return self.async_show_form(
    #         step_id="user", data_schema=DATA_SCHEMA, errors=errors
    #     )

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
            # auto_detected_data = await detect_radios(dev_path)
            # if auto_detected_data is not None:
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


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path


# async def detect_radios(dev_path: str) -> Optional[Dict[str, Any]]:
#     """Probe all radio types on the device port."""
#     for radio in RadioType:
#         dev_config = radio.controller.SCHEMA_DEVICE({CONF_DEVICE_PATH: dev_path})
#         if await radio.controller.probe(dev_config):
#             return {CONF_RADIO_TYPE: radio.name, CONF_DEVICE: dev_config}

#     return None