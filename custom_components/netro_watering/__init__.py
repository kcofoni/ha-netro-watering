"""Support for Netro Watering system."""

from __future__ import annotations

from datetime import date
import enum
import logging

import validators
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_MOISTURE,
    ATTR_NOWATER_DAYS,
    ATTR_WEATHER_CONDITION,
    ATTR_WEATHER_DATE,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_RAIN,
    ATTR_WEATHER_RAIN_PROB,
    ATTR_WEATHER_T_DEW,
    ATTR_WEATHER_T_MAX,
    ATTR_WEATHER_T_MIN,
    ATTR_WEATHER_TEMP,
    ATTR_WEATHER_WIND_SPEED,
    ATTR_ZONE_ID,
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
    MAX_MONTHS_AFTER_SCHEDULES,
    MAX_MONTHS_BEFORE_SCHEDULES,
    MAX_REFRESH_INTERVAL_MN,
    MAX_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    MIN_MONTHS_AFTER_SCHEDULES,
    MIN_MONTHS_BEFORE_SCHEDULES,
    MIN_REFRESH_INTERVAL_MN,
    MIN_SENSOR_VALUE_DAYS_BEFORE_TODAY,
    MONTHS_AFTER_SCHEDULES,
    MONTHS_BEFORE_SCHEDULES,
    NETRO_DEFAULT_ZONE_MODEL,
    SENS_REFRESH_INTERVAL_MN,
    SENSOR_DEVICE_TYPE,
)
from .coordinator import (
    NetroControllerUpdateCoordinator,
    NetroSensorUpdateCoordinator,
    prepare_slowdown_factors,
)
from .netrofunction import (
    report_weather as netro_report_weather,
    set_moisture as netro_set_moisture,
    set_netro_base_url,
)

# Here is the list of the platforms that we want to support.
# sensor is for the netro ground sensors, switch is for the zones
# PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.SWITCH,
]


_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="arg-type"

SERVICE_SET_MOISTURE_NAME = "set_moisture"
SERVICE_SET_MOISTURE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ZONE_ID): cv.string,
        vol.Required(ATTR_MOISTURE): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)

SERVICE_REFRESH_NAME = "refresh_data"
SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)

SERVICE_NO_WATER_NAME = "no_water"
SERVICE_NO_WATER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_NOWATER_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
    }
)


class WeatherConditions(enum.Enum):
    """Class to represent the possible weather conditions."""

    clear = 0
    cloudy = 1
    rain = 2
    snow = 3
    wind = 4


SERVICE_REPORT_WEATHER_NAME = "report_weather"
SERVICE_REPORT_WEATHER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_WEATHER_DATE): cv.date,
        vol.Optional(ATTR_WEATHER_CONDITION): cv.enum(WeatherConditions),
        vol.Optional(ATTR_WEATHER_RAIN): cv.positive_float,
        vol.Optional(ATTR_WEATHER_RAIN_PROB): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(ATTR_WEATHER_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=-60, max=60)
        ),
        vol.Optional(ATTR_WEATHER_T_MIN): vol.All(
            vol.Coerce(float), vol.Range(min=-60, max=60)
        ),
        vol.Optional(ATTR_WEATHER_T_MAX): vol.All(
            vol.Coerce(float), vol.Range(min=-60, max=60)
        ),
        vol.Optional(ATTR_WEATHER_T_DEW): vol.All(
            vol.Coerce(float), vol.Range(min=-60, max=60)
        ),
        vol.Optional(ATTR_WEATHER_WIND_SPEED): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=111)
        ),
        vol.Optional(ATTR_WEATHER_HUMIDITY): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(ATTR_WEATHER_PRESSURE): vol.All(
            vol.Coerce(float), vol.Range(min=850.0, max=1100.0)
        ),
    }
)


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: C901
    """Set up Netro Watering from a config entry."""

    _LOGGER.debug(
        "setting up config entry: device_type = %s, serial_number = %s, config_name = %s",
        entry.data[CONF_DEVICE_TYPE],
        entry.data[CONF_SERIAL_NUMBER],
        entry.data[CONF_DEVICE_NAME],
    )

    # access to global parameters
    gp = hass.data.get(DOMAIN, {}).get(GLOBAL_PARAMETERS, {})

    # get global parameters any type of device could be interested in
    slowdown_factors = None
    if gp.get(CONF_SLOWDOWN_FACTOR) is not None:
        slowdown_factors = gp[CONF_SLOWDOWN_FACTOR]

    if entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
        # get sensor specific parameters, look first in the options, next in the global parameters, otherwise use the default value
        val = next(
            v
            for v in (
                entry.options.get(CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY),
                gp.get(CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY),
                DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
            )
            if v is not None
        )

        try:
            sensor_value_days_before_today = int(val)
        except (TypeError, ValueError):
            sensor_value_days_before_today = DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY
            _LOGGER.warning(
                "The value provided for '%s' is invalid, defaulting to %d",
                CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
            )

        if (
            not MIN_SENSOR_VALUE_DAYS_BEFORE_TODAY
            <= sensor_value_days_before_today
            <= MAX_SENSOR_VALUE_DAYS_BEFORE_TODAY
        ):
            sensor_value_days_before_today = DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY
            _LOGGER.warning(
                "The value provided for '%s' is out of range [%d..%d], defaulting to %d",
                CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                MIN_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                MAX_SENSOR_VALUE_DAYS_BEFORE_TODAY,
                DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,
            )

        # --- Sensor refresh_interval (minutes, 1..120) ---
        val = next(
            v
            for v in (
                entry.options.get(CONF_SENS_REFRESH_INTERVAL),
                SENS_REFRESH_INTERVAL_MN,
            )
            if v is not None
        )

        try:
            refresh_interval = int(val)
        except (TypeError, ValueError):
            refresh_interval = SENS_REFRESH_INTERVAL_MN
            _LOGGER.warning(
                "The value provided for '%s' is invalid, defaulting to %d",
                CONF_SENS_REFRESH_INTERVAL,
                SENS_REFRESH_INTERVAL_MN,
            )

        if not MIN_REFRESH_INTERVAL_MN <= refresh_interval <= MAX_REFRESH_INTERVAL_MN:
            refresh_interval = SENS_REFRESH_INTERVAL_MN
            _LOGGER.warning(
                "The value provided for '%s' is out of range [%d..%d], defaulting to %d",
                CONF_SENS_REFRESH_INTERVAL,
                MIN_REFRESH_INTERVAL_MN,
                MAX_REFRESH_INTERVAL_MN,
                SENS_REFRESH_INTERVAL_MN,
            )

        _LOGGER.debug(
            "creating sensor coordinator: device_name = %s, refresh_interval = %s, sensor_value_days_before_today = %s",
            entry.data[CONF_DEVICE_NAME],
            refresh_interval,
            sensor_value_days_before_today,
        )

        sensor_coordinator = NetroSensorUpdateCoordinator(
            hass,
            refresh_interval=refresh_interval,
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
        opt = entry.options

        # --- refresh_interval (minutes, 1..120) ---
        val = next(
            v
            for v in (opt.get(CONF_CTRL_REFRESH_INTERVAL), CTRL_REFRESH_INTERVAL_MN)
            if v is not None
        )
        try:
            refresh_interval = int(val)
        except (TypeError, ValueError):
            refresh_interval = CTRL_REFRESH_INTERVAL_MN
            _LOGGER.warning(
                "The value provided for '%s' is invalid, defaulting to %d",
                CONF_CTRL_REFRESH_INTERVAL,
                CTRL_REFRESH_INTERVAL_MN,
            )

        if not MIN_REFRESH_INTERVAL_MN <= refresh_interval <= MAX_REFRESH_INTERVAL_MN:
            refresh_interval = CTRL_REFRESH_INTERVAL_MN
            _LOGGER.warning(
                "The value provided for '%s' is out of range [%d..%d], defaulting to %d",
                CONF_CTRL_REFRESH_INTERVAL,
                MIN_REFRESH_INTERVAL_MN,
                MAX_REFRESH_INTERVAL_MN,
                CTRL_REFRESH_INTERVAL_MN,
            )

        # --- schedules_months_before ---
        val = next(
            v
            for v in (opt.get(CONF_MONTHS_BEFORE_SCHEDULES), MONTHS_BEFORE_SCHEDULES)
            if v is not None
        )
        try:
            schedules_months_before = int(val)
        except (TypeError, ValueError):
            schedules_months_before = MONTHS_BEFORE_SCHEDULES
            _LOGGER.warning(
                "The value provided for '%s' is invalid, defaulting to %d",
                CONF_MONTHS_BEFORE_SCHEDULES,
                MONTHS_BEFORE_SCHEDULES,
            )

        if (
            not MIN_MONTHS_BEFORE_SCHEDULES
            <= schedules_months_before
            <= MAX_MONTHS_BEFORE_SCHEDULES
        ):
            schedules_months_before = MONTHS_BEFORE_SCHEDULES
            _LOGGER.warning(
                "The value provided for '%s' is out of range [%d..%d], defaulting to %d",
                CONF_MONTHS_BEFORE_SCHEDULES,
                MIN_MONTHS_BEFORE_SCHEDULES,
                MAX_MONTHS_BEFORE_SCHEDULES,
                MONTHS_BEFORE_SCHEDULES,
            )

        # --- schedules_months_after ---
        val = next(
            v
            for v in (opt.get(CONF_MONTHS_AFTER_SCHEDULES), MONTHS_AFTER_SCHEDULES)
            if v is not None
        )
        try:
            schedules_months_after = int(val)
        except (TypeError, ValueError):
            schedules_months_after = MONTHS_AFTER_SCHEDULES
            _LOGGER.warning(
                "The value provided for '%s' is invalid, defaulting to %d",
                CONF_MONTHS_AFTER_SCHEDULES,
                MONTHS_AFTER_SCHEDULES,
            )

        if (
            not MIN_MONTHS_AFTER_SCHEDULES
            <= schedules_months_after
            <= MAX_MONTHS_AFTER_SCHEDULES
        ):
            schedules_months_after = MONTHS_AFTER_SCHEDULES
            _LOGGER.warning(
                "The value provided for '%s' is out of range [%d..%d], defaulting to %d",
                CONF_MONTHS_AFTER_SCHEDULES,
                MIN_MONTHS_AFTER_SCHEDULES,
                MAX_MONTHS_AFTER_SCHEDULES,
                MONTHS_AFTER_SCHEDULES,
            )

        _LOGGER.debug(
            "creating controller: device_name = %s, refresh_interval = %s, schedules_months_before = %s, schedules_months_after = %s",
            entry.data[CONF_DEVICE_NAME],
            refresh_interval,
            schedules_months_before,
            schedules_months_after,
        )

        controller_coordinator = NetroControllerUpdateCoordinator(
            hass,
            refresh_interval=refresh_interval,
            slowdown_factors=slowdown_factors,
            schedules_months_before=schedules_months_before,
            schedules_months_after=schedules_months_after,
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

    if entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:

        async def set_moisture(call: ServiceCall) -> None:
            moisture = call.data[ATTR_MOISTURE]

            # get the device related to the selected zone
            device_id = call.data[ATTR_ZONE_ID]
            device_registry = dr.async_get(hass)
            if (device_entry := device_registry.async_get(device_id)) is None:
                raise HomeAssistantError(
                    f"Invalid Netro Watering device ID: {device_id}"
                )
            if (
                device_entry.model is None
                or device_entry.model != NETRO_DEFAULT_ZONE_MODEL
            ):
                raise HomeAssistantError(
                    f"Invalid Netro Watering device ID: {device_id}, it doesn't seem to be a zone !?"
                )

            # retrieve the config entry related to this device
            for entry_id in device_entry.config_entries:
                if (entry := hass.config_entries.async_get_entry(entry_id)) is None:
                    continue
                if entry.domain == DOMAIN:
                    config_entry = entry
                    break
            if config_entry is None:
                raise HomeAssistantError(
                    f"Cannot find config entry for device ID: {device_id}"
                )

            # get serial number and zone_id
            key = config_entry.data[CONF_SERIAL_NUMBER]
            for identifier in device_entry.identifiers:
                if identifier[1].startswith(key):
                    # assume that device info returned by Zone class is <controller_serial>_<zone_id> as identifiers
                    zone_id = identifier[1].split("_")[1]
                    break

            # set moisture by Netro
            _LOGGER.info(
                "Running custom service 'Set moisture' : the humidity level has been forced to %s%% for zone %s (id = %s)",
                moisture,
                device_entry.name,
                zone_id,
            )
            await hass.async_add_executor_job(
                netro_set_moisture, key, moisture, zone_id
            )

        # only one Set moisture service to be created for all controllers
        if not hass.services.has_service(DOMAIN, SERVICE_SET_MOISTURE_NAME):
            _LOGGER.info("Adding custom service : %s", SERVICE_SET_MOISTURE_NAME)
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_MOISTURE_NAME,
                set_moisture,
                schema=SERVICE_SET_MOISTURE_SCHEMA,
            )

    async def report_weather(call: ServiceCall) -> None:
        weather_asof: date = call.data[ATTR_WEATHER_DATE]
        weather_condition = (
            call.data[ATTR_WEATHER_CONDITION]
            if call.data.get(ATTR_WEATHER_CONDITION) is not None
            else None
        )
        weather_rain = (
            call.data[ATTR_WEATHER_RAIN]
            if call.data.get(ATTR_WEATHER_RAIN) is not None
            else None
        )
        weather_rain_prob = (
            call.data[ATTR_WEATHER_RAIN_PROB]
            if call.data.get(ATTR_WEATHER_RAIN_PROB) is not None
            else None
        )
        weather_temp = (
            call.data[ATTR_WEATHER_TEMP]
            if call.data.get(ATTR_WEATHER_TEMP) is not None
            else None
        )
        weather_t_min = (
            call.data[ATTR_WEATHER_T_MIN]
            if call.data.get(ATTR_WEATHER_T_MIN) is not None
            else None
        )
        weather_t_max = (
            call.data[ATTR_WEATHER_T_MAX]
            if call.data.get(ATTR_WEATHER_T_MAX) is not None
            else None
        )
        weather_t_dew = (
            call.data[ATTR_WEATHER_T_DEW]
            if call.data.get(ATTR_WEATHER_T_DEW) is not None
            else None
        )
        weather_wind_speed = (
            call.data[ATTR_WEATHER_WIND_SPEED]
            if call.data.get(ATTR_WEATHER_WIND_SPEED) is not None
            else None
        )
        weather_humidity = (
            call.data[ATTR_WEATHER_HUMIDITY]
            if call.data.get(ATTR_WEATHER_HUMIDITY) is not None
            else None
        )
        weather_pressure = (
            call.data[ATTR_WEATHER_PRESSURE]
            if call.data.get(ATTR_WEATHER_PRESSURE) is not None
            else None
        )

        # get serial number
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        if entry_id not in hass.data[DOMAIN]:
            raise HomeAssistantError(f"Config entry id does not exist: {entry_id}")
        coordinator = hass.data[DOMAIN][entry_id]

        key = coordinator.serial_number

        # report weather by Netro
        _LOGGER.info(
            "Running custom service report_weather : %s",
            {
                "controller": coordinator.name,
                "date": str(weather_asof) if weather_asof else weather_asof,
                "condition": weather_condition.value
                if weather_condition is not None
                else None,
                "rain": weather_rain,
                "rain_prob": weather_rain_prob,
                "temp": weather_temp,
                "t_min": weather_t_min,
                "t_max": weather_t_max,
                "t_dew": weather_t_dew,
                "wind_speed": weather_wind_speed,
                "humidity": int(weather_humidity)
                if weather_humidity
                else weather_humidity,
                "pressure": weather_pressure,
            },
        )

        if not weather_asof:
            raise HomeAssistantError(
                "'date' parameter is missing when running 'Report weather' service provided by Netro Watering integration"
            )

        await hass.async_add_executor_job(
            netro_report_weather,
            key,
            str(weather_asof),
            weather_condition.value if weather_condition is not None else None,
            weather_rain,
            weather_rain_prob,
            weather_temp,
            weather_t_min,
            weather_t_max,
            weather_t_dew,
            weather_wind_speed,
            weather_humidity,
            weather_pressure,
        )

    # only one Report weather service to be created for all config entries
    if not hass.services.has_service(DOMAIN, SERVICE_REPORT_WEATHER_NAME):
        _LOGGER.info("Adding custom service : %s", SERVICE_REPORT_WEATHER_NAME)
        hass.services.async_register(
            DOMAIN,
            SERVICE_REPORT_WEATHER_NAME,
            report_weather,
            schema=SERVICE_REPORT_WEATHER_SCHEMA,
        )

    async def refresh(call: ServiceCall) -> None:
        """Service call to refresh data of Netro devices."""

        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        if entry_id not in hass.data[DOMAIN]:
            raise HomeAssistantError(f"Config entry id does not exist: {entry_id}")
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry_id]

        _LOGGER.info(
            "Running custom service 'Refresh data' for %s devices", coordinator.name
        )

        await coordinator.async_request_refresh()

    # only one Refresh data service to be created for all config entry
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_NAME):
        _LOGGER.info("Adding custom service : %s", SERVICE_REFRESH_NAME)
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_NAME,
            refresh,
            schema=SERVICE_REFRESH_SCHEMA,
        )

    async def nowater(call: ServiceCall) -> None:
        """Service call to stop watering for a given number of days."""

        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        if entry_id not in hass.data[DOMAIN]:
            raise HomeAssistantError(f"Config entry id does not exist: {entry_id}")
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry_id]

        _LOGGER.info(
            "Running custom service 'Refresh data' for %s devices", coordinator.name
        )

        days: int = call.data[ATTR_NOWATER_DAYS]
        await coordinator.no_water(int(days))
        await coordinator.async_request_refresh()

    # only one nowater data service to be created for all config entry
    if not hass.services.has_service(DOMAIN, SERVICE_NO_WATER_NAME):
        _LOGGER.info("Adding custom service : %s", SERVICE_NO_WATER_NAME)
        hass.services.async_register(
            DOMAIN,
            SERVICE_NO_WATER_NAME,
            nowater,
            schema=SERVICE_NO_WATER_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _LOGGER.info("Deleting %s", hass.data[DOMAIN][entry.entry_id])
        hass.data[DOMAIN].pop(entry.entry_id)

    # the Set moisture service has to be removed if the current entry is a controller and the last one
    if entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        other_loaded_entries = [
            _entry
            for _entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if _entry.entry_id != entry.entry_id
            and _entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE
        ]

        if not other_loaded_entries:
            _LOGGER.info("Removing service %s", SERVICE_SET_MOISTURE_NAME)
            hass.services.async_remove(DOMAIN, SERVICE_SET_MOISTURE_NAME)

    # if there is no more entry after this one, one must remove the config entry level services
    other_loaded_entries = [
        _entry
        for _entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if _entry.entry_id != entry.entry_id
    ]

    if not other_loaded_entries:
        _LOGGER.info("Removing service %s", SERVICE_REPORT_WEATHER_NAME)
        hass.services.async_remove(DOMAIN, SERVICE_REPORT_WEATHER_NAME)
        _LOGGER.info("Removing service %s", SERVICE_REFRESH_NAME)
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_NAME)
        _LOGGER.info("Removing service %s", SERVICE_NO_WATER_NAME)
        hass.services.async_remove(DOMAIN, SERVICE_NO_WATER_NAME)

    return unload_ok
