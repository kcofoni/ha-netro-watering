"""Support for Netro watering system."""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import (
    CONF_DEVICE_TYPE,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    EXTRA_STATE_ATTRIBUTE_SEP_LEFT,
    EXTRA_STATE_ATTRIBUTE_SEP_RIGHT,
)
from .coordinator import NetroControllerUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class NetroRequiredKeysMixin:
    """Mixin for required keys."""

    netro_name: str


@dataclass
class NetroBinarySensorEntityDescription(
    BinarySensorEntityDescription, NetroRequiredKeysMixin
):
    """Defines Netro entity description."""


NETRO_ZONE_WATERING_DESCRIPTION = NetroBinarySensorEntityDescription(
    key="iswatering",
    name="Is it watering ?",
    device_class=BinarySensorDeviceClass.RUNNING,
    translation_key="iswatering",
    netro_name="watering",
    icon="mdi:watering-can-outline",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry for a Netro sensors."""
    if config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        controller: NetroControllerUpdateCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
        ]
        # add zone binary sensors
        async_add_entities(
            [
                NetroZone(
                    controller,
                    NETRO_ZONE_WATERING_DESCRIPTION,
                    zone_key,
                )
                for zone_key in controller.active_zones
            ]
        )


class NetroZone(
    CoordinatorEntity[NetroControllerUpdateCoordinator], BinarySensorEntity
):
    """A sensor implementation for Netro Zone device."""

    entity_description: NetroBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroBinarySensorEntityDescription,
        zone_id: int,
    ) -> None:
        """Initialize the Netro sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.zone_id = zone_id
        self._attr_unique_id = (
            f"{coordinator.active_zones[zone_id].serial_number}-{description.key}"
        )
        self._attr_device_info = coordinator.active_zones[zone_id].device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if the current zone is currently watering."""
        return getattr(
            self.coordinator.active_zones[self.zone_id],
            self.entity_description.netro_name,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        zone_attributes = {
            "zone id": self.zone_id,
            "update interval": f"{round(self.coordinator.update_interval.total_seconds() / 60)} mn"
            if self.coordinator.update_interval is not None
            else None,
        }
        if self.coordinator.current_slowdown_factor > 1:
            zone_attributes[
                "slowdown factor"
            ] = self.coordinator.current_slowdown_factor
        meta_attributes = {
            EXTRA_STATE_ATTRIBUTE_SEP_LEFT: EXTRA_STATE_ATTRIBUTE_SEP_RIGHT,
            "request time (UTC)": self.coordinator.metadata.time
            if self.coordinator.metadata is not None
            else None,
            "last active date": dt_util.as_local(
                self.coordinator.metadata.last_active_date.replace(
                    tzinfo=datetime.UTC
                )
            )
            if self.coordinator.metadata is not None
            else None,
            "transaction id": self.coordinator.metadata.tid
            if self.coordinator.metadata is not None
            else None,
            "token limit": self.coordinator.metadata.token_limit
            if self.coordinator.metadata is not None
            else None,
            "token remaining": self.coordinator.metadata.token_remaining
            if self.coordinator.metadata is not None
            else None,
            "token reset": dt_util.as_local(
                self.coordinator.metadata.token_reset_date.replace(
                    tzinfo=datetime.UTC
                )
            )
            if self.coordinator.metadata is not None
            else None,
        }
        return zone_attributes | meta_attributes
