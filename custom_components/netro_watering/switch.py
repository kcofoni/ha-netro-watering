"""Support for Netro Watering system."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntFlag
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_WATERING_DELAY,
    ATTR_WATERING_DURATION,
    ATTR_WATERING_START_TIME,
    CONF_DEFAULT_WATERING_DELAY,
    CONF_DELAY_BEFORE_REFRESH,
    CONF_DEVICE_TYPE,
    CONF_DURATION,
    CONTROLLER_DEVICE_TYPE,
    DEFAULT_WATERING_DELAY,
    DEFAULT_WATERING_DURATION,
    DELAY_BEFORE_REFRESH,
    DOMAIN,
    GLOBAL_PARAMETERS,
)
from .coordinator import NetroControllerUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="arg-type"

SERVICE_START_WATERING = "start_watering"
SERVICE_STOP_WATERING = "stop_watering"
SERVICE_ENABLE = "enable"
SERVICE_DISABLE = "disable"

SERVICE_SCHEMA_WATERING = {
    vol.Required(ATTR_WATERING_DURATION): cv.positive_int,
    vol.Optional(ATTR_WATERING_DELAY): cv.positive_int,
    vol.Optional(ATTR_WATERING_START_TIME): cv.datetime,
}


class NetroSwitchEntityFeature(IntFlag):
    """Supported features of the Netro Watering switch."""

    ENABLE_DISABLE = 1
    START_STOP_WATERING = 2


@dataclass
class NetroRequiredKeysMixin:
    """Mixin for required keys."""

    netro_on_name: str
    netro_off_name: str


@dataclass
class NetroSwitchEntityDescription(SwitchEntityDescription, NetroRequiredKeysMixin):
    """Defines Netro entity description."""


# description of the start/stop watering switch
NETRO_WATERING_SWITCH_DESCRIPTION = NetroSwitchEntityDescription(
    key="watering",
    name="Watering",
    device_class=SwitchDeviceClass.SWITCH,
    translation_key="watering",
    netro_on_name="start_watering",
    netro_off_name="stop_watering",
    icon="mdi:sprinkler",
)

# description of the enable/disable switch
NETRO_ENABLED_SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="enabled",
    name="Enabled",
    device_class=SwitchDeviceClass.SWITCH,
    translation_key="enabled",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry for all controller switches."""
    if config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        controller: NetroControllerUpdateCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
        ]

        # get the configuration options we are interested in
        default_watering_duration = (
            (config_entry.options.get(CONF_DURATION))
            if (config_entry.options.get(CONF_DURATION) is not None)
            else DEFAULT_WATERING_DURATION
        )

        # get the parameters we are interested in
        default_watering_delay = DEFAULT_WATERING_DELAY
        delay_before_refresh = DELAY_BEFORE_REFRESH
        if hass.data[DOMAIN].get(GLOBAL_PARAMETERS) is not None:
            if (
                hass.data[DOMAIN][GLOBAL_PARAMETERS].get(CONF_DEFAULT_WATERING_DELAY)
                is not None
            ):
                default_watering_delay = hass.data[DOMAIN][GLOBAL_PARAMETERS][
                    CONF_DEFAULT_WATERING_DELAY
                ]
            if (
                hass.data[DOMAIN][GLOBAL_PARAMETERS].get(CONF_DELAY_BEFORE_REFRESH)
                is not None
            ):
                delay_before_refresh = hass.data[DOMAIN][GLOBAL_PARAMETERS][
                    CONF_DELAY_BEFORE_REFRESH
                ]

        _LOGGER.info("Adding switch entities")

        # enable/disable controller switch
        async_add_entities(
            [
                ControllerEnablingSwitch(
                    controller,
                    NETRO_ENABLED_SWITCH_DESCRIPTION,
                )
            ]
        )

        # start/stop watering switch for each zone
        for zone_key in controller.active_zones:  # iterating over the active zones
            async_add_entities(
                [
                    ZoneWateringSwitch(
                        controller,
                        NETRO_WATERING_SWITCH_DESCRIPTION,
                        zone_key,
                        default_watering_duration,
                        default_watering_delay,
                        delay_before_refresh,
                    )
                ]
            )

        # start/stop watering switch for the controller
        async_add_entities(
            [
                ControllerWateringSwitch(
                    controller,
                    NETRO_WATERING_SWITCH_DESCRIPTION,
                    default_watering_duration,
                    default_watering_delay,
                    delay_before_refresh,
                )
            ]
        )

        platform = entity_platform.async_get_current_platform()

        _LOGGER.info("Adding custom service : %s", SERVICE_START_WATERING)
        platform.async_register_entity_service(
            SERVICE_START_WATERING,
            SERVICE_SCHEMA_WATERING,
            "async_turn_on",
            [NetroSwitchEntityFeature.START_STOP_WATERING],
        )

        _LOGGER.info("Adding custom service : %s", SERVICE_STOP_WATERING)
        platform.async_register_entity_service(
            SERVICE_STOP_WATERING,
            {},
            "async_turn_off",
            [NetroSwitchEntityFeature.START_STOP_WATERING],
        )

        _LOGGER.info("Adding custom service : %s", SERVICE_ENABLE)
        platform.async_register_entity_service(
            SERVICE_ENABLE,
            {},
            "async_turn_on",
            [NetroSwitchEntityFeature.ENABLE_DISABLE],
        )

        _LOGGER.info("Adding custom service : %s", SERVICE_DISABLE)
        platform.async_register_entity_service(
            SERVICE_DISABLE,
            {},
            "async_turn_off",
            [NetroSwitchEntityFeature.ENABLE_DISABLE],
        )


class ControllerEnablingSwitch(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SwitchEntity
):
    """A switch implementation for switching on or off a controller."""

    _attr_has_entity_name = True
    _attr_assumed_state = False
    _attr_supported_features = NetroSwitchEntityFeature.ENABLE_DISABLE

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the on/off controller switch."""
        super().__init__(coordinator)
        self._state = None
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.enable()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.disable()
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.enabled


# ruff: noqa
class ZoneWateringSwitch(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SwitchEntity
):
    """A switch implementation for start/stopping watering."""

    _attr_has_entity_name = True
    _attr_assumed_state = True
    _attr_supported_features = NetroSwitchEntityFeature.START_STOP_WATERING
    entity_description: NetroSwitchEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSwitchEntityDescription,
        zone_id,
        duration_minutes: int,
        delay_minutes: int,
        before_refresh_seconds: int,
    ) -> None:
        """Initialize the start/stop watering switch."""
        super().__init__(coordinator)
        self._state = None
        self.entity_description = description
        self._zone_id = zone_id
        self._duration_minutes = duration_minutes
        self._delay_minutes = delay_minutes
        self._before_refresh_seconds = before_refresh_seconds
        self._attr_unique_id = (
            f"{coordinator.serial_number}-{zone_id}-{description.key}"
        )
        self._attr_device_info = coordinator.active_zones[zone_id].device_info

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {"zone": self._zone_id}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        start_time = kwargs.get(ATTR_WATERING_START_TIME, None)
        await getattr(
            self.coordinator.active_zones[self._zone_id],
            self.entity_description.netro_on_name,
        )(
            int(duration := kwargs.get(ATTR_WATERING_DURATION, self._duration_minutes)),
            int(delay := kwargs.get(ATTR_WATERING_DELAY, self._delay_minutes)),
            dt_util.as_utc(start_time) if start_time is not None else None,
        )
        if delay == 0 and start_time is None:
            _LOGGER.info(
                'Watering of zone "%s" has been started right now for %s minutes',
                self.coordinator.active_zones[self._zone_id].name,
                self._duration_minutes,
            )
        else:
            if (
                start_time is not None
            ):  # start_time is higher priority than delay if both provided
                _LOGGER.info(
                    "Watering of zone %s will start on %s and will last %s minutes",
                    self.coordinator.active_zones[self._zone_id].name,
                    start_time,
                    duration,
                )
            else:  # delay is necessarily not 0
                _LOGGER.info(
                    "Watering of zone %s will start in %s minutes and will last %s minutes",
                    self.coordinator.active_zones[self._zone_id].name,
                    delay,
                    duration,
                )

        _LOGGER.info(
            "Waiting for %s seconds before refreshing info (time it takes for Netro to return the status)",
            self._before_refresh_seconds,
        )
        await asyncio.sleep(self._before_refresh_seconds)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await getattr(
            self.coordinator.active_zones[self._zone_id],
            self.entity_description.netro_off_name,
        )()
        _LOGGER.info(
            "Watering of zone %s has just been stopped, waiting for %s seconds before refreshing info (time it takes for Netro to return the status)",
            self.coordinator.active_zones[self._zone_id].name,
            self._before_refresh_seconds,
        )
        await asyncio.sleep(self._before_refresh_seconds)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.active_zones[self._zone_id].watering


class ControllerWateringSwitch(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SwitchEntity
):
    """A switch implementation for starting/stopping watering at controller level."""

    _attr_has_entity_name = True
    _attr_assumed_state = True
    _attr_supported_features = NetroSwitchEntityFeature.START_STOP_WATERING
    entity_description: NetroSwitchEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSwitchEntityDescription,
        duration_minutes: int,
        delay_minutes: int,
        before_refresh_seconds: int,
    ) -> None:
        """Initialize the start/stop watering switch."""
        super().__init__(coordinator)
        self._state = None
        self.entity_description = description
        self._duration_minutes = duration_minutes
        self._delay_minutes = delay_minutes
        self._before_refresh_seconds = before_refresh_seconds
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        start_time = kwargs.get(ATTR_WATERING_START_TIME, None)
        await getattr(
            self.coordinator,
            self.entity_description.netro_on_name,
        )(
            int(duration := kwargs.get(ATTR_WATERING_DURATION, self._duration_minutes)),
            int(delay := kwargs.get(ATTR_WATERING_DELAY, self._delay_minutes)),
            dt_util.as_utc(start_time) if start_time is not None else None,
        )
        if delay == 0 and start_time is None:
            _LOGGER.info(
                "Watering of all zones has been started right now for %s minutes for each zone",
                duration,
            )
        else:
            if (
                start_time is not None
            ):  # start_time is higher priority than delay if both provided
                _LOGGER.info(
                    "Watering of all zones will start on %s and will last %s minutes for each zone",
                    start_time,
                    duration,
                )
            else:  # delay is necessarily not 0
                _LOGGER.info(
                    "Watering of all zones will start in %s minutes and will last %s minutes for each zone",
                    delay,
                    duration,
                )

        _LOGGER.info(
            "Waiting for %s seconds before refreshing info (time it takes for Netro to return the status)",
            self._before_refresh_seconds,
        )
        await asyncio.sleep(self._before_refresh_seconds)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await getattr(
            self.coordinator,
            self.entity_description.netro_off_name,
        )()
        _LOGGER.info(
            "Watering of all zone has just been stopped, waiting for %s seconds before refreshing info (time it takes for Netro to return the status)",
            self._before_refresh_seconds,
        )
        await asyncio.sleep(self._before_refresh_seconds)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.watering
