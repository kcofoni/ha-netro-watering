"""Support for Netro Watering system."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_TYPE,
    CONF_DURATION,
    CONTROLLER_DEVICE_TYPE,
    DEFAULT_WATERING_DURATION,
    DELAY_BEFORE_REFRESH,
    DOMAIN,
)
from .coordinator import NetroControllerUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# mypy: disable-error-code="arg-type"

SERVICE_ENABLE_CONTROLLER = "enable_controller"


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
)

# description of the start/stop watering switch
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
                )
            ]
        )


#        platform = entity_platform.async_get_current_platform()
#        platform.async_register_entity_service(
#            SERVICE_ENABLE_CONTROLLER,
#            {},
#            "async_turn_on",
#        )


class ControllerEnablingSwitch(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SwitchEntity
):
    """A switch implementation for switching on or off a controller."""

    _attr_has_entity_name = True
    _attr_assumed_state = False

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


class ZoneWateringSwitch(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SwitchEntity
):
    """A switch implementation for start/stopping watering."""

    _attr_has_entity_name = True
    _attr_assumed_state = True
    entity_description: NetroSwitchEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSwitchEntityDescription,
        zone_id,
        duration_minutes: int,
    ) -> None:
        """Initialize the start/stop watering switch."""
        super().__init__(coordinator)
        self._state = None
        self.entity_description = description
        self._zone_id = zone_id
        self._duration_minutes = duration_minutes
        self._attr_unique_id = (
            f"{coordinator.serial_number}-{zone_id}-{description.key}"
        )
        self._attr_device_info = coordinator.active_zones[zone_id].device_info

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await getattr(
            self.coordinator.active_zones[self._zone_id],
            self.entity_description.netro_on_name,
        )(self._duration_minutes)
        await asyncio.sleep(DELAY_BEFORE_REFRESH)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await getattr(
            self.coordinator.active_zones[self._zone_id],
            self.entity_description.netro_off_name,
        )()
        await asyncio.sleep(DELAY_BEFORE_REFRESH)
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
    entity_description: NetroSwitchEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSwitchEntityDescription,
        duration_minutes: int,
    ) -> None:
        """Initialize the start/stop watering switch."""
        super().__init__(coordinator)
        self._state = None
        self.entity_description = description
        self._duration_minutes = duration_minutes
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await getattr(
            self.coordinator,
            self.entity_description.netro_on_name,
        )(self._duration_minutes)
        await asyncio.sleep(DELAY_BEFORE_REFRESH)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await getattr(
            self.coordinator,
            self.entity_description.netro_off_name,
        )()
        await asyncio.sleep(DELAY_BEFORE_REFRESH)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.watering
