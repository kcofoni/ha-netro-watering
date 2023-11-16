"""Support for Netro Watering system."""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_TYPE, CONTROLLER_DEVICE_TYPE, DOMAIN
from .coordinator import NetroControllerUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NETRO_CALENDAR_DESCRIPTION = EntityDescription(
    key="schedules",
    name="Schedules",
    entity_registry_enabled_default=True,
    translation_key="schedules",
    icon="mdi:calendar-clock",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry for the controller calendar."""
    if config_entry.data[CONF_DEVICE_TYPE] == CONTROLLER_DEVICE_TYPE:
        _LOGGER.info("Adding calendar entity")
        # add controller calendar
        async_add_entities(
            [
                NetroCalendar(
                    hass.data[DOMAIN][config_entry.entry_id],
                    NETRO_CALENDAR_DESCRIPTION,
                )
            ]
        )


class NetroCalendar(
    CoordinatorEntity[NetroControllerUpdateCoordinator], CalendarEntity
):
    """A calendar implementation for Netro Controller device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Netro calendar."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def event(self) -> CalendarEvent | None:
        """Return current or next upcoming schedule if any."""
        schedule = self.coordinator.current_calendar_schedule
        return (
            CalendarEvent(
                schedule["start"],
                schedule["end"],
                schedule["summary"],
                schedule["description"],
            )
            if schedule is not None
            else None
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all schedules in a specific time frame."""
        return [
            CalendarEvent(
                schedule["start"],
                schedule["end"],
                schedule["summary"],
                schedule["description"],
            )
            for schedule in self.coordinator.calendar_schedules(start_date, end_date)
        ]
