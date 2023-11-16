"""Support for Netro watering system."""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import (
    CONF_DEVICE_TYPE,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    EXTRA_STATE_ATTRIBUTE_SEP_LEFT,
    EXTRA_STATE_ATTRIBUTE_SEP_RIGHT,
    NETRO_CONTROLLER_BATTERY_LEVEL,
    NETRO_CONTROLLER_STATUS,
    NETRO_METADATA_TOKEN_REMAINING,
    NETRO_MOISTURE_MOISTURE,
    NETRO_SENSOR_BATTERY_LEVEL,
    NETRO_SENSOR_MOISTURE,
    NETRO_SENSOR_SUNLIGHT,
    NETRO_SENSOR_TEMPERATURE,
    NETRO_ZONE_LAST_WATERING_END,
    NETRO_ZONE_LAST_WATERING_SOURCE,
    NETRO_ZONE_LAST_WATERING_START,
    NETRO_ZONE_LAST_WATERING_STATUS,
    NETRO_ZONE_NEXT_WATERING_END,
    NETRO_ZONE_NEXT_WATERING_SOURCE,
    NETRO_ZONE_NEXT_WATERING_START,
    NETRO_ZONE_NEXT_WATERING_STATUS,
    SENSOR_DEVICE_TYPE,
)
from .coordinator import NetroControllerUpdateCoordinator, NetroSensorUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class NetroRequiredKeysMixin:
    """Mixin for required keys."""

    netro_name: str


@dataclass
class NetroSensorEntityDescription(SensorEntityDescription, NetroRequiredKeysMixin):
    """Defines Netro entity description."""


# description of the sensors of the Netro ground sensors
NETRO_SENSOR_DESCRIPTIONS: tuple[NetroSensorEntityDescription, ...] = (
    NetroSensorEntityDescription(
        key="temperature",
        name="Temperature",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        translation_key="temperature",
        netro_name=NETRO_SENSOR_TEMPERATURE,
    ),
    NetroSensorEntityDescription(
        key="humidity",
        name="Humidity",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        translation_key="humidity",
        netro_name=NETRO_SENSOR_MOISTURE,
    ),
    NetroSensorEntityDescription(
        key="illuminance",
        name="Illuminance",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ILLUMINANCE,
        translation_key="illuminance",
        netro_name=NETRO_SENSOR_SUNLIGHT,
    ),
    NetroSensorEntityDescription(
        key="battery_percent",
        name="Battery Percent",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        translation_key="battery_percent",
        netro_name=NETRO_SENSOR_BATTERY_LEVEL,
    ),
    NetroSensorEntityDescription(
        key="token_remaining",
        name="Token Remaining",
        state_class=SensorStateClass.TOTAL,
        translation_key="token_remaining",
        icon="mdi:hand-coin",
        netro_name=NETRO_METADATA_TOKEN_REMAINING,
    ),
)

NETRO_SENSOR_DESCRIPTIONS_KEYS = [desc.key for desc in NETRO_SENSOR_DESCRIPTIONS]

# description of the sensors of the Netro controller
NETRO_CONTROLLER_DESCRIPTIONS: tuple[NetroSensorEntityDescription, ...] = (
    NetroSensorEntityDescription(
        key="status",
        name="Status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "standby",
            "setup",
            "online",
            "watering",
            "offline",
            "sleeping",
            "poweroff",
        ],
        translation_key="status",
        netro_name=NETRO_CONTROLLER_STATUS,
    ),
    NetroSensorEntityDescription(
        key="token_remaining",
        name="Token Remaining",
        state_class=SensorStateClass.TOTAL,
        translation_key="token_remaining",
        icon="mdi:hand-coin",
        netro_name=NETRO_METADATA_TOKEN_REMAINING,
    ),
)
# description of the battery level sensor of the controller when relevant
NETRO_CONTROLLER_BATTERY_DESCRIPTION = NetroSensorEntityDescription(
    key="battery_percent",
    name="Battery Percent",
    entity_registry_enabled_default=True,
    entity_category=EntityCategory.DIAGNOSTIC,
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    device_class=SensorDeviceClass.BATTERY,
    netro_name=NETRO_CONTROLLER_BATTERY_LEVEL,
)

NETRO_CONTROLLER_DESCRIPTIONS_KEYS = [
    desc.key for desc in NETRO_CONTROLLER_DESCRIPTIONS
]

# description of the sensors of each zone
NETRO_ZONE_DESCRIPTIONS: tuple[NetroSensorEntityDescription, ...] = (
    NetroSensorEntityDescription(
        key="last_watering_status",
        name="Last Watering Status",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        options=[
            "executed",
            "executing",
            "valid",
            "none",
        ],
        translation_key="last_watering_status",
        netro_name=NETRO_ZONE_LAST_WATERING_STATUS,
    ),
    NetroSensorEntityDescription(
        key="last_watering_start_datetime",
        name="Last watering start time",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="last_watering_start_datetime",
        netro_name=NETRO_ZONE_LAST_WATERING_START,
    ),
    NetroSensorEntityDescription(
        key="last_watering_end_datetime",
        name="Last watering end time",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="last_watering_end_datetime",
        netro_name=NETRO_ZONE_LAST_WATERING_END,
    ),
    NetroSensorEntityDescription(
        key="last_watering_source",
        name="Last watering source",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        options=[
            "smart",
            "fix",
            "manual",
            "none",
        ],
        translation_key="last_watering_source",
        netro_name=NETRO_ZONE_LAST_WATERING_SOURCE,
    ),
    NetroSensorEntityDescription(
        key="next_watering_status",
        name="Next watering status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "executed",
            "executing",
            "valid",
            "none",
        ],
        translation_key="next_watering_status",
        netro_name=NETRO_ZONE_NEXT_WATERING_STATUS,
    ),
    NetroSensorEntityDescription(
        key="next_watering_start_datetime",
        name="Next watering start time",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="next_watering_start_datetime",
        netro_name=NETRO_ZONE_NEXT_WATERING_START,
    ),
    NetroSensorEntityDescription(
        key="next_watering_end_datetime",
        name="Next watering end time",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="next_watering_end_datetime",
        netro_name=NETRO_ZONE_NEXT_WATERING_END,
    ),
    NetroSensorEntityDescription(
        key="next_watering_source",
        name="Next watering source",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        options=[
            "smart",
            "fix",
            "manual",
            "none",
        ],
        translation_key="next_watering_source",
        netro_name=NETRO_ZONE_NEXT_WATERING_SOURCE,
    ),
    NetroSensorEntityDescription(
        key="humidity",
        name="Humidity",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        translation_key="humidity",
        netro_name=NETRO_MOISTURE_MOISTURE,
    ),
)

NETRO_ZONE_DESCRIPTIONS_KEYS = [desc.key for desc in NETRO_ZONE_DESCRIPTIONS]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry for a Netro sensors."""
    if config_entry.data[CONF_DEVICE_TYPE] == SENSOR_DEVICE_TYPE:
        async_add_entities(
            [
                NetroSensor(
                    hass.data[DOMAIN][config_entry.entry_id],
                    description,
                )
                for description in NETRO_SENSOR_DESCRIPTIONS
            ]
        )
    elif config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        controller: NetroControllerUpdateCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
        ]
        # add controller intrinsic sensors
        async_add_entities(
            [
                NetroController(
                    controller,
                    description,
                )
                for description in NETRO_CONTROLLER_DESCRIPTIONS
            ]
        )
        # add battery sensor if the controller has a battery level
        if hasattr(controller, NETRO_CONTROLLER_BATTERY_LEVEL):
            async_add_entities(
                [
                    NetroController(
                        controller,
                        NETRO_CONTROLLER_BATTERY_DESCRIPTION,
                    )
                ]
            )
        # add zone sensors
        for zone_key in controller.active_zones:  # iterating over the active zones
            async_add_entities(
                [
                    NetroZone(
                        controller,
                        description,
                        zone_key,
                    )
                    for description in NETRO_ZONE_DESCRIPTIONS
                ]
            )


class NetroSensor(CoordinatorEntity[NetroSensorUpdateCoordinator], SensorEntity):
    """A sensor implementation for Netro Sensor device."""

    _attr_has_entity_name = True
    entity_description: NetroSensorEntityDescription

    def __init__(
        self,
        coordinator: NetroSensorUpdateCoordinator,
        description: NetroSensorEntityDescription,
    ) -> None:
        """Initialize the Netro sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return getattr(self.coordinator, self.entity_description.netro_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            "last measurement id": self.coordinator.id,
            "last measurement time": dt_util.as_local(self.coordinator.time)
            if self.coordinator.time is not None
            else None,
            "update interval": f"{round(self.coordinator.update_interval.total_seconds() / 60)} mn"
            if self.coordinator.update_interval is not None
            else None,
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


class NetroController(
    CoordinatorEntity[NetroControllerUpdateCoordinator], SensorEntity
):
    """A sensor implementation for Netro Sensor device."""

    _attr_has_entity_name = True
    entity_description: NetroSensorEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSensorEntityDescription,
    ) -> None:
        """Initialize the Netro sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            return str(
                getattr(self.coordinator, self.entity_description.netro_name)
            ).lower()
        return getattr(self.coordinator, self.entity_description.netro_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        return super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        zone_attributes = {
            "update interval": f"{round(self.coordinator.update_interval.total_seconds() / 60)} mn"
            if self.coordinator.update_interval is not None
            else None,
        }
        if self.coordinator.current_slowdown_factor > 1:
            zone_attributes[
                "slowdown factor"
            ] = self.coordinator.current_slowdown_factor  # type: ignore[assignment]
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


class NetroZone(CoordinatorEntity[NetroControllerUpdateCoordinator], SensorEntity):
    """A sensor implementation for Netro Sensor device."""

    _attr_has_entity_name = True
    entity_description: NetroSensorEntityDescription

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: NetroSensorEntityDescription,
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
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            return str(
                getattr(
                    self.coordinator.active_zones[self.zone_id],
                    self.entity_description.netro_name,
                )
            ).lower()
        return getattr(
            self.coordinator.active_zones[self.zone_id],
            self.entity_description.netro_name,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        return super()._handle_coordinator_update()

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
