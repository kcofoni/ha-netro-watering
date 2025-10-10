"""Config flow for Netro Watering integration."""

from __future__ import annotations

import logging
from typing import Any

from pynetro import NetroClient, NetroConfig, NetroException, NetroInvalidKey
from pynetro.client import mask
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CTRL_REFRESH_INTERVAL,
    CONF_DEFAULT_WATERING_DELAY,
    CONF_DELAY_BEFORE_REFRESH,
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SW_VERSION,
    CONF_DEVICE_TYPE,
    CONF_DURATION,
    CONF_MONTHS_AFTER_SCHEDULES,
    CONF_MONTHS_BEFORE_SCHEDULES,
    CONF_SENS_REFRESH_INTERVAL,
    CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    CONF_SERIAL_NUMBER,
    CONTROLLER_ADVANCED_OPTIONS_COLLAPSED,
    CONTROLLER_DEVICE_TYPE,
    CTRL_REFRESH_INTERVAL_MN,
    DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    DEFAULT_WATERING_DELAY,
    DEFAULT_WATERING_DURATION,
    DELAY_BEFORE_REFRESH,
    DOMAIN,
    GLOBAL_PARAMETERS,
    MAX_DELAY_BEFORE_REFRESH,
    MAX_MONTHS_AFTER_SCHEDULES,
    MAX_MONTHS_BEFORE_SCHEDULES,
    MAX_REFRESH_INTERVAL_MN,
    MAX_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    MAX_WATERING_DELAY,
    MAX_WATERING_DURATION,
    MIN_DELAY_BEFORE_REFRESH,
    MIN_MONTHS_AFTER_SCHEDULES,
    MIN_MONTHS_BEFORE_SCHEDULES,
    MIN_REFRESH_INTERVAL_MN,
    MIN_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    MIN_WATERING_DELAY,
    MIN_WATERING_DURATION,
    MONTHS_AFTER_SCHEDULES,
    MONTHS_BEFORE_SCHEDULES,
    SENS_REFRESH_INTERVAL_MN,
    SENSOR_ADVANCED_OPTIONS_COLLAPSED,
    SENSOR_DEVICE_TYPE,
)
from .http_client import AiohttpClient

_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="return"

# a "serial number" has to be provided for identifying the device.
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_NUMBER): selector.TextSelector(),
    }
)


class PlaceholderHub:
    """Temporary class used for testing Netro device information retrieval.

    Simulates device API calls and provides access to device attributes.
    """

    def __init__(self, serial: str) -> None:
        """Initialize."""
        self.serial = serial
        self.info: dict[str, Any] | None = None

    async def check(self, hass: HomeAssistant) -> bool:
        """Check if we can get information from the serial number."""
        session = async_get_clientsession(hass)
        client = NetroClient(http=AiohttpClient(session), config=NetroConfig())
        self.info = await client.get_info(self.serial)
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


def _normalize_serial(value: str) -> str:
    """Normalize the serial number for comparisons."""
    return str(value).strip().replace(" ", "").upper()


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

    serial = _normalize_serial(data[CONF_SERIAL_NUMBER])
    hub = PlaceholderHub(serial)
    ok = await hub.check(hass)
    if not ok:
        raise CannotConnect
    return {
        CONF_DEVICE_TYPE: hub.get_device_type(),
        CONF_SERIAL_NUMBER: serial,
        CONF_DEVICE_NAME: hub.get_name(),
        CONF_DEVICE_HW_VERSION: hub.get_hw_version(),
        CONF_DEVICE_SW_VERSION: hub.get_sw_version(),
    }


class NetroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netro Watering."""

    VERSION = 1

    def is_matching(self, other_flow: dict[str, Any]) -> bool:
        """Check if this integration matches the discovery info."""
        # As this integration does not support automatic discovery,
        # we return False

        return False

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            serial = _normalize_serial(user_input[CONF_SERIAL_NUMBER])

            # 1) Prevent duplicates across device types: compare to the serial stored in data
            for entry in self._async_current_entries():
                if _normalize_serial(entry.data.get(CONF_SERIAL_NUMBER, "")) == serial:
                    return self.async_abort(reason="already_configured")

            try:
                config_item = await validate_input(self.hass, user_input)
            except NetroInvalidKey:
                _LOGGER.warning("Invalid serial number: %s", mask(serial))
                errors["base"] = "invalid_serial_number"
            except NetroException:
                _LOGGER.exception(
                    "Unexpected Netro API exception for serial: %s", mask(serial)
                )
                errors["base"] = "netro_error_occurred"
            except CannotConnect:
                _LOGGER.exception("Cannot connect for serial: %s", mask(serial))
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception for serial: %s", mask(serial))
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=config_item[CONF_DEVICE_NAME], data=config_item
                )

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate a connection failure."""


class OptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Netro Watering options flow with automatic reload."""

    def _gp(self) -> dict[str, Any]:
        """Retrieve already loaded YAML parameters (fallback for defaults)."""
        return self.hass.data.get(DOMAIN, {}).get(GLOBAL_PARAMETERS, {})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step of the options flow.

        Presents the options form to the user and processes input to update config entry options.
        """
        if user_input is not None:
            # Extract and flatten the section
            advanced = user_input.pop("advanced", {})
            if isinstance(advanced, dict):
                user_input.update(advanced)

            # No manual reload needed: OptionsFlowWithReload will do it.
            new_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        # Fallbacks from options or YAML (backward compatibility)
        gp = self._gp()
        opt = self.config_entry.options

        if self.config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
            advanced_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_DELAY_BEFORE_REFRESH,
                        default=opt.get(
                            CONF_DELAY_BEFORE_REFRESH,
                            gp.get(CONF_DELAY_BEFORE_REFRESH, DELAY_BEFORE_REFRESH),
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_DELAY_BEFORE_REFRESH,
                            max=MAX_DELAY_BEFORE_REFRESH,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_WATERING_DELAY,
                        default=opt.get(
                            CONF_DEFAULT_WATERING_DELAY,
                            gp.get(CONF_DEFAULT_WATERING_DELAY, DEFAULT_WATERING_DELAY),
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_WATERING_DELAY,
                            max=MAX_WATERING_DELAY,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MONTHS_BEFORE_SCHEDULES,
                        default=self.config_entry.options.get(
                            CONF_MONTHS_BEFORE_SCHEDULES, MONTHS_BEFORE_SCHEDULES
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_MONTHS_BEFORE_SCHEDULES,
                            max=MAX_MONTHS_BEFORE_SCHEDULES,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MONTHS_AFTER_SCHEDULES,
                        default=self.config_entry.options.get(
                            CONF_MONTHS_AFTER_SCHEDULES, MONTHS_AFTER_SCHEDULES
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_MONTHS_AFTER_SCHEDULES,
                            max=MAX_MONTHS_AFTER_SCHEDULES,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            )
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_CTRL_REFRESH_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_CTRL_REFRESH_INTERVAL, CTRL_REFRESH_INTERVAL_MN
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_REFRESH_INTERVAL_MN,
                            max=MAX_REFRESH_INTERVAL_MN,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_DURATION,
                        default=self.config_entry.options.get(
                            CONF_DURATION, DEFAULT_WATERING_DURATION
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_WATERING_DURATION,
                            max=MAX_WATERING_DURATION,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required("advanced"): section(
                        advanced_schema,
                        {"collapsed": CONTROLLER_ADVANCED_OPTIONS_COLLAPSED},
                    ),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        if self.config_entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
            # For a sensor device, only certain advanced fields are relevant
            advanced_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                        default=opt.get(
                            CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                            gp.get(
                                CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                                DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                            ),
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                            max=MAX_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            )
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SENS_REFRESH_INTERVAL,
                        default=opt.get(
                            CONF_SENS_REFRESH_INTERVAL, SENS_REFRESH_INTERVAL_MN
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_REFRESH_INTERVAL_MN,
                            max=MAX_REFRESH_INTERVAL_MN,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required("advanced"): section(
                        advanced_schema,
                        {"collapsed": SENSOR_ADVANCED_OPTIONS_COLLAPSED},
                    ),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        return self.async_abort(reason="unknown_device_type")
