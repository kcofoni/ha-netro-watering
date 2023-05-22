"""Support for Netro Watering system."""
from __future__ import annotations

import logging

import validators

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CTRL_REFRESH_INTERVAL,
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SW_VERSION,
    CONF_DEVICE_TYPE,
    CONF_MONTHS_AFTER_SCHEDULES,
    CONF_MONTHS_BEFORE_SCHEDULES,
    CONF_SENS_REFRESH_INTERVAL,
    CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    CONF_SERIAL_NUMBER,
    CONF_SLOWDOWN_FACTOR,
    CONTROLLER_DEVICE_TYPE,
    CTRL_REFRESH_INTERVAL_MN,
    DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    DOMAIN,
    GLOBAL_PARAMETERS,
    MONTHS_AFTER_SCHEDULES,
    MONTHS_BEFORE_SCHEDULES,
    SENS_REFRESH_INTERVAL_MN,
    SENSOR_DEVICE_TYPE,
)
from .coordinator import (
    NetroControllerUpdateCoordinator,
    NetroSensorUpdateCoordinator,
    prepare_slowdown_factors,
)
from .netrofunction import set_netro_base_url

# Here is the list of the platforms that we want to support.
# sensor is for the netro ground sensors, switch is for the zones
# PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR]


_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="arg-type"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Init of the integration."""
    _LOGGER.info(
        "Initializing %s integration with platforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        config.get(DOMAIN),
    )

    # reset configuration dictionary
    hass.data.setdefault(DOMAIN, {})

    # access to configuration.yaml
    if (netro_watering_config := config.get(DOMAIN)) is not None:
        if netro_watering_config.get("netro_api_url") is not None:
            if validators.url(netro_watering_config["netro_api_url"]):
                set_netro_base_url(netro_watering_config["netro_api_url"])
                _LOGGER.info(
                    "Set Netro Public API url to %s",
                    netro_watering_config["netro_api_url"],
                )
            else:
                _LOGGER.warning(
                    "The URL provided for Netro Public API is ignored since it is not properly formed, please check '%s' section in the home assistant configuration file and correct the 'netrop_api_url' entry",
                    DOMAIN,
                )

    # set global config into the integration shared space
    hass.data[DOMAIN][GLOBAL_PARAMETERS] = netro_watering_config

    # prepare slow down factor
    if hass.data[DOMAIN].get(GLOBAL_PARAMETERS) is not None:
        if hass.data[DOMAIN][GLOBAL_PARAMETERS].get(CONF_SLOWDOWN_FACTOR) is not None:
            prepare_slowdown_factors(
                hass.data[DOMAIN][GLOBAL_PARAMETERS][CONF_SLOWDOWN_FACTOR]
            )

    # Return boolean to indicate that initialization was successful.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Netro Watering from a config entry."""

    _LOGGER.debug(
        "setting up config entry: device_type = %s, serial_number = %s, config_name = %s",
        entry.data[CONF_DEVICE_TYPE],
        entry.data[CONF_SERIAL_NUMBER],
        entry.data[CONF_DEVICE_NAME],
    )

    # get global parameters any type of device could be interested in
    slowdown_factors = None
    if hass.data[DOMAIN].get(GLOBAL_PARAMETERS) is not None:
        if hass.data[DOMAIN][GLOBAL_PARAMETERS].get(CONF_SLOWDOWN_FACTOR) is not None:
            slowdown_factors = hass.data[DOMAIN][GLOBAL_PARAMETERS][
                CONF_SLOWDOWN_FACTOR
            ]

    if entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
        # get global parameters we are intested in
        sensor_value_days_before_today = DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY
        if hass.data[DOMAIN].get(GLOBAL_PARAMETERS) is not None:
            if (
                hass.data[DOMAIN][GLOBAL_PARAMETERS].get(
                    CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY
                )
                is not None
            ):
                sensor_value_days_before_today = hass.data[DOMAIN][GLOBAL_PARAMETERS][
                    CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY
                ]

        sensor_coordinator = NetroSensorUpdateCoordinator(
            hass,
            refresh_interval=(
                entry.options.get(CONF_SENS_REFRESH_INTERVAL)
                if entry.options.get(CONF_SENS_REFRESH_INTERVAL) is not None
                else SENS_REFRESH_INTERVAL_MN
            ),
            sensor_value_days_before_today=sensor_value_days_before_today,
            serial_number=entry.data[CONF_SERIAL_NUMBER],
            device_type=entry.data[CONF_DEVICE_TYPE],
            device_name=entry.data[CONF_DEVICE_NAME],
            hw_version=entry.data[CONF_DEVICE_HW_VERSION],
            sw_version=entry.data[CONF_DEVICE_SW_VERSION],
        )
        await sensor_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id] = sensor_coordinator
        _LOGGER.info("Just created : %s", sensor_coordinator)
    elif entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        controller_coordinator = NetroControllerUpdateCoordinator(
            hass,
            refresh_interval=(
                entry.options.get(CONF_CTRL_REFRESH_INTERVAL)
                if entry.options.get(CONF_CTRL_REFRESH_INTERVAL) is not None
                else CTRL_REFRESH_INTERVAL_MN
            ),
            slowdown_factors=slowdown_factors,
            schedules_months_before=(
                entry.options.get(CONF_MONTHS_BEFORE_SCHEDULES)
                if entry.options.get(CONF_MONTHS_BEFORE_SCHEDULES) is not None
                else MONTHS_BEFORE_SCHEDULES
            ),
            schedules_months_after=(
                entry.options.get(CONF_MONTHS_AFTER_SCHEDULES)
                if entry.options.get(CONF_MONTHS_AFTER_SCHEDULES) is not None
                else MONTHS_AFTER_SCHEDULES
            ),
            serial_number=entry.data[CONF_SERIAL_NUMBER],
            device_type=entry.data[CONF_DEVICE_TYPE],
            device_name=entry.data[CONF_DEVICE_NAME],
            hw_version=entry.data[CONF_DEVICE_HW_VERSION],
            sw_version=entry.data[CONF_DEVICE_SW_VERSION],
        )
        await controller_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id] = controller_coordinator
        _LOGGER.info("Just created : %s", controller_coordinator)
    else:
        raise HomeAssistantError(
            f"Config entry netro device type does not exist: {entry.data[CONF_DEVICE_TYPE]}"
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _LOGGER.info("Deleting %s", hass.data[DOMAIN][entry.entry_id])
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
