"""Support for Netro Watering system."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_CTRL_REFRESH_INTERVAL,
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SW_VERSION,
    CONF_DEVICE_TYPE,
    CONF_MONTHS_AFTER_SCHEDULES,
    CONF_MONTHS_BEFORE_SCHEDULES,
    CONF_SENS_REFRESH_INTERVAL,
    CONF_SERIAL_NUMBER,
    CONTROLLER_DEVICE_TYPE,
    CTRL_REFRESH_INTERVAL_MN,
    DOMAIN,
    MONTHS_AFTER_SCHEDULES,
    MONTHS_BEFORE_SCHEDULES,
    SENS_REFRESH_INTERVAL_MN,
    SENSOR_DEVICE_TYPE,
)
from .coordinator import NetroControllerUpdateCoordinator, NetroSensorUpdateCoordinator

# Here is the list of the platforms that we want to support.
# sensor is for the netro ground sensors, switch is for the zones
# PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR]


_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="arg-type"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Netro Watering from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.debug(
        "setting up config entry: device_type = %s, serial_number = %s, config_name = %s",
        entry.data[CONF_DEVICE_TYPE],
        entry.data[CONF_SERIAL_NUMBER],
        entry.data[CONF_DEVICE_NAME],
    )

    if entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
        sensor_coordinator = NetroSensorUpdateCoordinator(
            hass,
            refresh_interval=(
                entry.options.get(CONF_SENS_REFRESH_INTERVAL)
                if entry.options.get(CONF_SENS_REFRESH_INTERVAL) is not None
                else SENS_REFRESH_INTERVAL_MN
            ),
            serial_number=entry.data[CONF_SERIAL_NUMBER],
            device_type=entry.data[CONF_DEVICE_TYPE],
            device_name=entry.data[CONF_DEVICE_NAME],
            hw_version=entry.data[CONF_DEVICE_HW_VERSION],
            sw_version=entry.data[CONF_DEVICE_SW_VERSION],
        )
        await sensor_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id] = sensor_coordinator
    elif entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        controller_coordinator = NetroControllerUpdateCoordinator(
            hass,
            refresh_interval=(
                entry.options.get(CONF_CTRL_REFRESH_INTERVAL)
                if entry.options.get(CONF_CTRL_REFRESH_INTERVAL) is not None
                else CTRL_REFRESH_INTERVAL_MN
            ),
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
    else:
        raise HomeAssistantError(
            f"Config entry netro device type does not exist: {entry.data[CONF_DEVICE_TYPE]}"
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
