"""Config flow for Netro Watering integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_CTRL_REFRESH_INTERVAL,
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SW_VERSION,
    CONF_DEVICE_TYPE,
    CONF_DURATION,
    CONF_MONTHS_AFTER_SCHEDULES,
    CONF_MONTHS_BEFORE_SCHEDULES,
    CONF_SENS_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    CONTROLLER_DEVICE_TYPE,
    CTRL_REFRESH_INTERVAL_MN,
    DEFAULT_WATERING_DURATION,
    DOMAIN,
    MONTHS_AFTER_SCHEDULES,
    MONTHS_BEFORE_SCHEDULES,
    SENS_REFRESH_INTERVAL_MN,
    SENSOR_DEVICE_TYPE,
)
from .netrofunction import (
    NETRO_ERROR_CODE_INVALID_KEY,
    NetroException,
    get_info as netro_get_info,
)

_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="return"

# a "serial number" has to be provided for identifying the device.
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_NUMBER): selector.TextSelector(),
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass."""

    def __init__(self, serial: str) -> None:
        """Initialize."""
        self.serial = serial

    async def check(self, hass: HomeAssistant) -> bool:
        """Check if we can get information from the serial number."""
        # pylint: disable=[attribute-defined-outside-init]
        self.info = await hass.async_add_executor_job(netro_get_info, self.serial)
        return self.info is not None

    def is_a_controller(self) -> bool:
        """Check if the device is a controller."""
        return self.info["data"].get("device") is not None

    def is_a_sensor(self) -> bool:
        """Check if the device is a sensor."""
        return self.info["data"].get("sensor") is not None

    def get_device_type(self) -> str | None:
        """Give the type of the device, controller or sensor."""
        if self.is_a_sensor():
            return SENSOR_DEVICE_TYPE
        if self.is_a_controller():
            return CONTROLLER_DEVICE_TYPE
        return None

    def get_name(self) -> str:
        """Give the name of the device, if any."""
        name: str
        if self.is_a_sensor():
            name = self.info["data"]["sensor"]["name"]
        elif self.is_a_controller():
            name = self.info["data"]["device"]["name"]
        return name

    def get_hw_version(self) -> str:
        """Give the software version of the device."""
        hw_version: str
        if self.is_a_sensor():
            hw_version = self.info["data"]["sensor"]["version"]
        elif self.is_a_controller():
            hw_version = self.info["data"]["device"]["version"]
        return hw_version

    def get_sw_version(self) -> str:
        """Give the software version of the device."""
        sw_version: str
        if self.is_a_sensor():
            sw_version = self.info["data"]["sensor"]["sw_version"]
        elif self.is_a_controller():
            sw_version = self.info["data"]["device"]["sw_version"]
        return sw_version


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    1. Check that the serial number is correct by requesting Netro Public API
    4. Determine the type of the device (controller or sensor) and fulfill the returned dict with it
    5. also return the name to be given to the config entry (config name).

    Data has the keys from DEVICE_SCHEMA with values provided by the user.
    """
    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func
    # )

    config_item = {}
    hub = PlaceholderHub(data[CONF_SERIAL_NUMBER])
    try:
        await hub.check(hass)
        if hub.get_device_type() is not None:
            config_item[CONF_DEVICE_TYPE] = hub.get_device_type()
            config_item[CONF_SERIAL_NUMBER] = data[CONF_SERIAL_NUMBER]
            config_item[CONF_DEVICE_NAME] = f"{hub.get_name()}"
            config_item[CONF_DEVICE_HW_VERSION] = hub.get_hw_version()
            config_item[CONF_DEVICE_SW_VERSION] = hub.get_sw_version()
        else:
            raise UnknownDeviceType

    except NetroException as netro_error:
        if netro_error.code == NETRO_ERROR_CODE_INVALID_KEY:
            raise InvalidSerialNumber from netro_error
        raise NetroDeviceError from netro_error

    return config_item


class NetroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netro Watering."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                config_item = await validate_input(self.hass, user_input)
            except InvalidSerialNumber:
                errors["base"] = "invalid_serial_number"
            except UnknownDeviceType:
                errors["base"] = "unknown_device_type"
            except NetroDeviceError:
                _LOGGER.exception("Unexpected Netro API exception")
                errors["base"] = "netro_error_occurred"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=config_item[CONF_DEVICE_NAME], data=config_item
                )

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )


class InvalidSerialNumber(HomeAssistantError):
    """Error to indicate there is invalid serial number."""


class UnknownDeviceType(HomeAssistantError):
    """Error to indicate an unknown device type."""


class NetroDeviceError(HomeAssistantError):
    """Error to indicate a netro error."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a Netro Watering options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        if self.config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_DURATION,
                            default=self.config_entry.options.get(
                                CONF_DURATION, DEFAULT_WATERING_DURATION
                            ),
                        ): vol.All(int, vol.Range(min=1, max=120)),
                        vol.Optional(
                            CONF_CTRL_REFRESH_INTERVAL,
                            default=self.config_entry.options.get(
                                CONF_CTRL_REFRESH_INTERVAL, CTRL_REFRESH_INTERVAL_MN
                            ),
                        ): vol.All(int, vol.Range(min=1, max=120)),
                        vol.Optional(
                            CONF_MONTHS_BEFORE_SCHEDULES,
                            default=self.config_entry.options.get(
                                CONF_MONTHS_BEFORE_SCHEDULES, MONTHS_BEFORE_SCHEDULES
                            ),
                        ): vol.All(int, vol.Range(min=1, max=6)),
                        vol.Optional(
                            CONF_MONTHS_AFTER_SCHEDULES,
                            default=self.config_entry.options.get(
                                CONF_MONTHS_AFTER_SCHEDULES, MONTHS_AFTER_SCHEDULES
                            ),
                        ): vol.All(int, vol.Range(min=1, max=6)),
                    }
                ),
            )

        if self.config_entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_SENS_REFRESH_INTERVAL,
                            default=self.config_entry.options.get(
                                CONF_SENS_REFRESH_INTERVAL, SENS_REFRESH_INTERVAL_MN
                            ),
                        ): vol.All(int, vol.Range(min=1, max=120)),
                    }
                ),
            )

        # Ensure a return value in case no conditions are met
        return self.async_abort(reason="unknown_device_type")

    async def _update_options(self) -> FlowResult:
        """Update config entry options."""
        return self.async_create_entry(title="", data=self.options)
