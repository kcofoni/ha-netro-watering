import datetime
import logging


from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)



from homeassistant.core import  HomeAssistant
from homeassistant.config_entries import ConfigEntry



from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import NetroControllerUpdateCoordinator

from .const import (
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

IRRIGATION_CALENDAR_DESCRIPTION = EntityDescription(
        key="irrigation",
        name="Irrigation",
        entity_registry_enabled_default=True,
        translation_key="irrigation",
    )

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback):

    controller: NetroControllerUpdateCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
    ]
    # add controller intrinsic sensors
    async_add_entities(
        [
            NetroCalendar(
                controller,
                IRRIGATION_CALENDAR_DESCRIPTION,
            )
        ]
    )

    return True



class NetroCalendar(CoordinatorEntity[NetroControllerUpdateCoordinator],CalendarEntity):
    _attr_icon: str = "mdi:calendar-clock"
    
    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Netro sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

        
    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        return [CalendarEvent(
            e["start"],
            e["end"],
            e["summary"],
            e["description"],
        ) for e in self.coordinator.calendar_schedules(
            start_date=start_date,
            end_date=end_date,
        )]
    
    
    @property
    def event(self) -> CalendarEvent | None:
        e = self.coordinator.current_calendar_event
        return CalendarEvent(
            e["start"],
            e["end"],
            e["summary"],
            e["description"],
        ) if e is not None else None
    
    

