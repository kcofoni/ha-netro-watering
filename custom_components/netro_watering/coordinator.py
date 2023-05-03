"""Support for Netro watering system."""

from __future__ import annotations

import datetime
import logging

from dateutil.relativedelta import relativedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_WATERING_DELAY,
    DOMAIN,
    MANUFACTURER,
    NETRO_CONTROLLER_BATTERY_LEVEL,
    NETRO_CONTROLLER_STATUS,
    NETRO_CONTROLLER_ZONENUM,
    NETRO_CONTROLLER_ZONES,
    NETRO_DEFAULT_SENSOR_MODEL,
    NETRO_DEFAULT_ZONE_MODEL,
    NETRO_METADATA_LAST_ACTIVE,
    NETRO_METADATA_TID,
    NETRO_METADATA_TIME,
    NETRO_METADATA_TOKEN_LIMIT,
    NETRO_METADATA_TOKEN_REMAINING,
    NETRO_METADATA_TOKEN_RESET,
    NETRO_METADATA_VERSION,
    NETRO_MOISTURE_ZONE,
    NETRO_PIXIE_CONTROLLER_MODEL,
    NETRO_SCHEDULE_END_TIME,
    NETRO_SCHEDULE_EXECUTED,
    NETRO_SCHEDULE_EXECUTING,
    NETRO_SCHEDULE_SOURCE,
    NETRO_SCHEDULE_START_TIME,
    NETRO_SCHEDULE_STATUS,
    NETRO_SCHEDULE_VALID,
    NETRO_SCHEDULE_ZONE,
    NETRO_SENSOR_BATTERY_LEVEL,
    NETRO_SENSOR_CELSIUS,
    NETRO_SENSOR_FAHRENHEIT,
    NETRO_SENSOR_LOCAL_DATE,
    NETRO_SENSOR_LOCAL_TIME,
    NETRO_SENSOR_MOISTURE,
    NETRO_SENSOR_SUNLIGHT,
    NETRO_SENSOR_TIME,
    NETRO_SPRITE_CONTROLLER_MODEL,
    NETRO_STATUS_DISABLE,
    NETRO_STATUS_ENABLE,
    NETRO_STATUS_ONLINE,
    NETRO_STATUS_SETUP,
    NETRO_STATUS_WATERING,
    NETRO_ZONE_ENABLED,
    NETRO_ZONE_ITH,
    NETRO_ZONE_NAME,
    NETRO_ZONE_SMART,
    TZ_OFFSET,
)
from .netrofunction import (
    get_info as netro_get_info,
    get_moistures as netro_get_moistures,
    get_schedules as netro_get_schedules,
    get_sensor_data as netro_get_sensor_data,
    set_status as netro_set_status,
    stop_water as netro_stop_water,
    water as netro_water,
)

_LOGGER = logging.getLogger(__name__)

# pylint: disable=attribute-defined-outside-init,consider-using-dict-items
# mypy: disable-error-code="var-annotated"


class Meta:
    """Meta data returned by any Netro service related to corresponding device/sensor."""

    def __init__(
        self,
        last_active: str,
        time: str,
        tid: str,
        version: str,
        token_limit: int,
        token_remaining: int,
        token_reset: str,
    ) -> None:
        """Create a meta data object."""
        self.version = version
        self.token_limit = token_limit
        self.token_remaining = token_remaining
        self.tid = tid
        self.last_active_date = datetime.datetime.fromisoformat(last_active)
        self.time = datetime.datetime.fromisoformat(time)
        self.token_reset_date = datetime.datetime.fromisoformat(token_reset)


class NetroSensorUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for Netro sensors NPA calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        refresh_interval: int,
        serial_number: str,
        device_type: str,
        device_name: str,
        hw_version: str,
        sw_version: str,
    ) -> None:
        """Initialize my sensor coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=device_name,
            update_interval=datetime.timedelta(minutes=refresh_interval),
        )
        self.serial_number = serial_number
        self.device_type = device_type
        self.device_name = device_name
        self.hw_version = hw_version
        self.sw_version = sw_version

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        return DeviceInfo(
            default_name=f"{self.device_name}",
            identifiers={(DOMAIN, self.serial_number)},
            manufacturer=MANUFACTURER,
            hw_version=self.hw_version,
            sw_version=self.sw_version,
            default_model=NETRO_DEFAULT_SENSOR_MODEL,
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        res = await self.hass.async_add_executor_job(
            netro_get_sensor_data,
            self.serial_number,
            datetime.date.today().strftime("%Y-%m-%d"),
            datetime.date.today().strftime("%Y-%m-%d"),
        )

        # only take the last sensor data report
        if len(res["data"]["sensor_data"]) > 0:
            sensor_data = res["data"]["sensor_data"][0]
            meta_data = res["meta"]

            self._metadata = Meta(
                meta_data[NETRO_METADATA_LAST_ACTIVE],
                meta_data[NETRO_METADATA_TIME],
                meta_data[NETRO_METADATA_TID],
                meta_data[NETRO_METADATA_VERSION],
                meta_data[NETRO_METADATA_TOKEN_LIMIT],
                meta_data[NETRO_METADATA_TOKEN_REMAINING],
                meta_data[NETRO_METADATA_TOKEN_RESET],
            )

            self.time = sensor_data[NETRO_SENSOR_TIME]
            self.local_date = sensor_data[NETRO_SENSOR_LOCAL_DATE]
            self.local_time = sensor_data[NETRO_SENSOR_LOCAL_TIME]
            self.moisture = sensor_data[NETRO_SENSOR_MOISTURE]
            self.sunlight = sensor_data[NETRO_SENSOR_SUNLIGHT]
            self.celsius = sensor_data[NETRO_SENSOR_CELSIUS]
            self.fahrenheit = sensor_data[NETRO_SENSOR_FAHRENHEIT]
            self.battery_level = sensor_data[NETRO_SENSOR_BATTERY_LEVEL]


class NetroControllerUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for Netro controllers NPA calls."""

    class Zone:
        """Zone of a Netro controller.

        lists available :
        past_schedule, coming_schedules, moistures : lists of schedules/moistures, these latter represented by a dictionary : key = str and value = any
        """

        past_schedules = []
        coming_schedules = []
        moistures = []

        def __init__(
            self,
            controller: NetroControllerUpdateCoordinator,
            ith: int,
            enabled: bool,
            smart: str,
            name: str,
            serial_number: str,
        ) -> None:
            """Create a zone (virtual device)."""
            self.ith = ith
            self.enabled = enabled
            self.smart = smart
            self.name = name
            self.serial_number = serial_number + "_" + str(ith)  # virtual serial number
            self.parent_controller = controller

        async def start_watering(self, duration: int) -> None:
            """Start watering for the current zone for given duration in minutes."""
            await self.parent_controller.hass.async_add_executor_job(
                netro_water,
                self.parent_controller.serial_number,
                duration,
                [str(self.ith)],
                DEFAULT_WATERING_DELAY,
            )

        async def stop_watering(self) -> None:
            """Stop watering (all zone included as unexpected - improvement expected)."""
            await self.parent_controller.hass.async_add_executor_job(
                netro_stop_water, self.parent_controller.serial_number
            )

        @property
        def watering(self) -> bool | None:
            """Is the zone currently watering ?."""
            if self.last_run:
                return self.last_run[NETRO_SCHEDULE_STATUS] == NETRO_SCHEDULE_EXECUTING
            return False

        @property
        def last_watering_status(self) -> str | None:
            """Get the status of the last/current watering."""
            if self.last_run:
                return self.last_run[NETRO_SCHEDULE_STATUS]
            return None

        @property
        def last_watering_start(self) -> datetime.datetime | None:
            """Get the start datetime of the last/current watering."""
            if self.last_run:
                return datetime.datetime.fromisoformat(
                    self.last_run[NETRO_SCHEDULE_START_TIME] + TZ_OFFSET
                )
            return None

        @property
        def last_watering_end(self) -> datetime.datetime | None:
            """Get the start datetime of the last/current watering."""
            if self.last_run:
                return datetime.datetime.fromisoformat(
                    self.last_run[NETRO_SCHEDULE_END_TIME] + TZ_OFFSET
                )
            return None

        @property
        def last_watering_source(self) -> str | None:
            """Get the status of the last/current watering."""
            if self.last_run:
                return self.last_run[NETRO_SCHEDULE_SOURCE]
            return None

        @property
        def next_watering_status(self) -> str | None:
            """Get the status of the last/current watering."""
            if self.next_run:
                return self.next_run[NETRO_SCHEDULE_STATUS]
            return None

        @property
        def next_watering_start(self) -> datetime.datetime | None:
            """Get the start datetime of the last/current watering."""
            if self.next_run:
                return datetime.datetime.fromisoformat(
                    self.next_run[NETRO_SCHEDULE_START_TIME] + TZ_OFFSET
                )
            return None

        @property
        def next_watering_end(self) -> datetime.datetime | None:
            """Get the start datetime of the last/current watering."""
            if self.next_run:
                return datetime.datetime.fromisoformat(
                    self.next_run[NETRO_SCHEDULE_END_TIME] + TZ_OFFSET
                )
            return None

        @property
        def next_watering_source(self) -> str | None:
            """Get the status of the last/current watering."""
            if self.next_run:
                return self.next_run[NETRO_SCHEDULE_SOURCE]
            return None

        @property
        def last_run(self) -> dict | None:
            """Get the last executed/executing run."""
            if len(self.past_schedules) != 0:
                return self.past_schedules[0]
            return None

        @property
        def next_run(self) -> dict | None:
            """Get the next valid run to be executed in the future."""
            if len(self.coming_schedules) != 0:
                return self.coming_schedules[0]
            return None

        @property
        def moisture(self) -> dict | None:
            """Get the last reported moisture."""
            if len(self.moistures) != 0:
                return self.moistures[0]
            return None

        @property
        def device_info(self) -> DeviceInfo:
            """Return information about the zone as a device. To be used when creating related entities."""
            return DeviceInfo(
                default_name=f"{self.name}",
                identifiers={(DOMAIN, self.serial_number)},
                manufacturer=MANUFACTURER,
                default_model=NETRO_DEFAULT_ZONE_MODEL,
                via_device=(DOMAIN, self.parent_controller.serial_number),
            )

    # _schedules and _moistures are list of dict whose key = str and value = any
    # _active_zones is a dictionary indexed by the zone ith and whose value is a Zone object
    _active_zones = {}
    _schedules = []
    _moistures = []

    def __init__(
        self,
        hass: HomeAssistant,
        refresh_interval: int,
        schedules_months_before: int,
        schedules_months_after: int,
        serial_number: str,
        device_type: str,
        device_name: str,
        hw_version: str,
        sw_version: str,
    ) -> None:
        """Initialize my sensor coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=device_name,
            update_interval=datetime.timedelta(minutes=refresh_interval),
        )
        self.serial_number = serial_number
        self.device_type = device_type
        self.device_name = device_name
        self.hw_version = hw_version
        self.sw_version = sw_version
        self.schedules_months_before = schedules_months_before
        self.schedules_months_after = schedules_months_after

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the controller as a device. To be used when creating related entities."""
        return DeviceInfo(
            default_name=f"{self.device_name}",
            identifiers={(DOMAIN, self.serial_number)},
            manufacturer=MANUFACTURER,
            hw_version=self.hw_version,
            sw_version=self.sw_version,
            default_model=NETRO_PIXIE_CONTROLLER_MODEL
            if hasattr(self, NETRO_CONTROLLER_BATTERY_LEVEL)
            else NETRO_SPRITE_CONTROLLER_MODEL,
        )

    def _update_from_schedules(
        self,
        schedules,
    ):
        """Schedules are spread over the active zones through two different lists : the past schedules and the coming schedules.

        Each list is ordered so that the first element return the most recent past schedule and coming schedule respectively.
        """
        self._schedules = schedules
        for zone_key in self._active_zones:
            # filtering past schedules, keeping the current zone
            past_schedules_zone_filtered = [
                schedule
                for schedule in schedules
                if schedule[NETRO_SCHEDULE_ZONE] == zone_key
                and schedule[NETRO_SCHEDULE_STATUS]
                in [NETRO_SCHEDULE_EXECUTED, NETRO_SCHEDULE_EXECUTING]
            ]

            # sorting filtered past schedules on start time descending
            past_schedules_zone_sorted = sorted(
                past_schedules_zone_filtered,
                key=(lambda schedule: schedule[NETRO_SCHEDULE_START_TIME]),
                reverse=True,
            )
            # set the zone schedules attribute with the result
            self._active_zones[zone_key].past_schedules = past_schedules_zone_sorted

            # filtering coming schedules, keeping the current zone
            coming_schedules_zone_filtered = [
                schedule
                for schedule in schedules
                if schedule[NETRO_SCHEDULE_ZONE] == zone_key
                and schedule[NETRO_SCHEDULE_STATUS] == NETRO_SCHEDULE_VALID
            ]

            # sorting filtered coming schedules on start time ascending
            coming_schedules_zone_sorted = sorted(
                coming_schedules_zone_filtered,
                key=(lambda schedule: schedule[NETRO_SCHEDULE_START_TIME]),
                reverse=False,
            )
            # set the zone schedules attribute with the result
            self._active_zones[zone_key].coming_schedules = coming_schedules_zone_sorted

    def _update_from_moistures(
        self,
        moistures,
    ):
        """Moistures are spread over the active zones."""
        self._moistures = moistures
        for zone_key in self._active_zones:
            # filtering moistures, keeping the current zone
            moistures_zone_filtered = [
                moisture
                for moisture in moistures
                if moisture[NETRO_MOISTURE_ZONE] == zone_key
            ]
            # set the zone moistures attribute with the result
            self._active_zones[zone_key].moistures = moistures_zone_filtered

    @property
    def enabled(self) -> bool:
        """Is the controller enabled or disabled ?."""
        return self.status in (
            NETRO_STATUS_ONLINE,
            NETRO_STATUS_WATERING,
            NETRO_STATUS_SETUP,
        )

    @property
    def watering(self) -> bool:
        """Is the controller currently watering."""
        return self.status == NETRO_STATUS_WATERING

    @property
    def active_zones(self) -> dict:
        """Return the actives zones of the controller."""
        return self._active_zones

    @property
    def number_of_active_zones(self) -> int | None:
        """Return the number of active zones if available."""
        if self._active_zones:
            return len(self._active_zones)
        return None

    def meta(self) -> object | None:
        """Return the meta data of the controller."""
        if self._metadata:
            return self._metadata
        return None

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.

        I. The following data are actually fetched
        ------------------------------------------
        controller data:
            - name
            - status
            - number of active zone

        zone data
            - name
            - ith (numeric index)
            - smart mode
            - past and coming schedules

        meta data
            - last active time
            - token remaining
            - token limit
            - token reset (date)
            - NPA (Netro Public API) version

        II. The following data are calculated
        -------------------------------------
        common
            - is watering (controller and zone)
            - is enabled (controller and zone)

        zone
            - last run (see zone.get_last_run) : date, status, start time, end time, source
            - next run (see zone.get_next_run) : date, status, start time, end time, source
            - last moisture (see zone.get_moisture)

        controller
            - zones, schedules, moistures

        III. Subsequent platforms
        -------------------------
        devices
            - controller
            - zone

        entities (entity - type - device)
            - status - sensor - controller
            - enabled - binary sensor - controller
            - enabled - binary sensor - zone
            - watering - binary sensor - controller
            - watering - binary sensor - zone
            - last watering start local datetime - sensor - zone
            - last watering end local datetime - sensor - zone
            - last watering status (executing or executed) - sensor - zone
            - last watering event source (smart, fix, manual) - sensor - zone
            - next watering start local datetime - sensor - zone
            - next watering end local datetime - sensor - zone
            - next watering status (executing or executed) - sensor - zone
            - next watering event source (smart, fix, manual) - sensor - zone
            - battery - sensor - controller (only for non standalone controllers (e.g. Pixie))
            - on/off - switch - controller

        services
            - start watering (controller)
            - stop watering (controller)
            - start watering (zone)
            - stop watering (zone)
        """

        # Get main data
        res = await self.hass.async_add_executor_job(
            netro_get_info,
            self.serial_number,
        )

        device_data = res["data"]["device"]
        meta_data = res["meta"]

        # pylint: disable=attribute-defined-outside-init
        self.zone_num = device_data[NETRO_CONTROLLER_ZONENUM]
        self.status = device_data[NETRO_CONTROLLER_STATUS]
        self._metadata = Meta(
            meta_data[NETRO_METADATA_LAST_ACTIVE],
            meta_data[NETRO_METADATA_TIME],
            meta_data[NETRO_METADATA_TID],
            meta_data[NETRO_METADATA_VERSION],
            meta_data[NETRO_METADATA_TOKEN_LIMIT],
            meta_data[NETRO_METADATA_TOKEN_REMAINING],
            meta_data[NETRO_METADATA_TOKEN_RESET],
        )
        if device_data.get(NETRO_CONTROLLER_BATTERY_LEVEL):
            self.battery_level = device_data[NETRO_CONTROLLER_BATTERY_LEVEL]
        for zone in device_data[NETRO_CONTROLLER_ZONES]:
            if zone[NETRO_ZONE_ENABLED]:
                self._active_zones[zone[NETRO_ZONE_ITH]] = self.Zone(
                    self,
                    zone[NETRO_ZONE_ITH],
                    zone[NETRO_ZONE_ENABLED],
                    zone[NETRO_ZONE_SMART],
                    zone[NETRO_ZONE_NAME]
                    if zone[NETRO_ZONE_NAME] is not None
                    else self.device_name + "-" + zone[NETRO_ZONE_ITH],
                    self.serial_number,
                )

        # get moistures
        res = await self.hass.async_add_executor_job(
            netro_get_moistures,
            self.serial_number,
        )

        # update controller and zone attributes from moistures
        self._update_from_moistures(res["data"]["moistures"])

        # get schedules
        res = await self.hass.async_add_executor_job(
            netro_get_schedules,
            self.serial_number,
            None,
            str(
                datetime.date.today()
                - relativedelta(months=self.schedules_months_before)
            ),
            str(
                datetime.date.today()
                + relativedelta(months=self.schedules_months_after)
            ),
        )

        # update controller and zone attributes from schedules
        self._update_from_schedules(res["data"]["schedules"])

    async def enable(self):
        """Enable controller."""
        res = await self.hass.async_add_executor_job(
            netro_set_status,
            self.serial_number,
            NETRO_STATUS_ENABLE,
        )
        return res

    async def disable(self):
        """Disable controller."""
        res = await self.hass.async_add_executor_job(
            netro_set_status,
            self.serial_number,
            NETRO_STATUS_DISABLE,
        )
        return res

    async def start_watering(self, duration: int) -> None:
        """Start watering for the current zone for given duration in minutes."""
        await self.hass.async_add_executor_job(
            netro_water, self.serial_number, duration, None, DEFAULT_WATERING_DELAY
        )

    async def stop_watering(self) -> None:
        """Stop watering (all zone included as expected)."""
        await self.hass.async_add_executor_job(netro_stop_water, self.serial_number)
