"""Tests for calendar platform."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.netro_watering.calendar import (
    NETRO_CALENDAR_DESCRIPTION,
    NetroCalendar,
    async_setup_entry,
)
from custom_components.netro_watering.const import (
    CONF_DEVICE_TYPE,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    SENSOR_DEVICE_TYPE,
)


class TestCalendarAsyncSetupEntry:
    """Test class for calendar async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.device_name = "Test Controller"
        coordinator.serial_number = "CTRL123"
        coordinator.device_info = {"name": "Test Controller", "model": "Netro Sprite"}
        coordinator.current_calendar_schedule = None
        coordinator.calendar_schedules = MagicMock(return_value=[])
        # Mock any potential async methods that might be called
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry_controller(self):
        """Create a mock ConfigEntry for controller."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_config_entry_sensor(self):
        """Create a mock ConfigEntry for sensor (not controller)."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_async_add_entities(self):
        """Create a mock AddEntitiesCallback."""
        return MagicMock(spec=AddEntitiesCallback)

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_success(
        self,
        mock_hass,
        mock_config_entry_controller,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test successful async_setup_entry for calendar platform with controller."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][
            mock_config_entry_controller.entry_id
        ] = mock_controller_coordinator

        with patch("custom_components.netro_watering.calendar._LOGGER") as mock_logger:
            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_config_entry_controller,
                mock_async_add_entities,
            )

            # Verify logger was called
            mock_logger.info.assert_called_once_with("Adding calendar entity")

            # Verify async_add_entities was called
            mock_async_add_entities.assert_called_once()

            # Get the entities that were passed to async_add_entities
            call_args = mock_async_add_entities.call_args[0][0]

            # Should create 1 NetroCalendar entity
            assert len(call_args) == 1

            # Verify it's a NetroCalendar instance
            calendar_entity = call_args[0]
            assert isinstance(calendar_entity, NetroCalendar)
            assert calendar_entity.entity_description == NETRO_CALENDAR_DESCRIPTION

    @pytest.mark.asyncio
    async def test_async_setup_entry_sensor_device_no_calendar(
        self,
        mock_hass,
        mock_config_entry_sensor,
        mock_async_add_entities,
    ):
        """Test async_setup_entry with sensor device type - should not create calendar."""
        # Call the function with sensor device type
        await async_setup_entry(
            mock_hass,
            mock_config_entry_sensor,
            mock_async_add_entities,
        )

        # Verify async_add_entities was NOT called for sensor devices
        mock_async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_coordinator(
        self,
        mock_hass,
        mock_config_entry_controller,
        mock_async_add_entities,
    ):
        """Test async_setup_entry when coordinator is missing from hass.data."""
        # Don't add coordinator to hass.data

        with pytest.raises(KeyError):
            await async_setup_entry(
                mock_hass,
                mock_config_entry_controller,
                mock_async_add_entities,
            )

    @pytest.mark.asyncio
    async def test_netro_calendar_creation_parameters(
        self,
        mock_hass,
        mock_config_entry_controller,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test that NetroCalendar is created with correct parameters."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][
            mock_config_entry_controller.entry_id
        ] = mock_controller_coordinator

        await async_setup_entry(
            mock_hass,
            mock_config_entry_controller,
            mock_async_add_entities,
        )

        # Get the created entity
        call_args = mock_async_add_entities.call_args[0][0]
        calendar_entity = call_args[0]

        # Verify the entity has the correct coordinator and description
        assert calendar_entity.coordinator == mock_controller_coordinator
        assert calendar_entity.entity_description == NETRO_CALENDAR_DESCRIPTION

        # Verify unique_id is constructed correctly
        expected_unique_id = f"{mock_controller_coordinator.serial_number}-{NETRO_CALENDAR_DESCRIPTION.key}"
        assert calendar_entity._attr_unique_id == expected_unique_id

        # Verify device_info is set correctly
        assert (
            calendar_entity._attr_device_info == mock_controller_coordinator.device_info
        )

    @pytest.mark.asyncio
    async def test_calendar_entity_description_properties(self):
        """Test that NETRO_CALENDAR_DESCRIPTION has correct properties."""
        assert NETRO_CALENDAR_DESCRIPTION.key == "schedules"
        assert NETRO_CALENDAR_DESCRIPTION.name == "Schedules"
        assert NETRO_CALENDAR_DESCRIPTION.entity_registry_enabled_default is True
        assert NETRO_CALENDAR_DESCRIPTION.translation_key == "schedules"
        assert NETRO_CALENDAR_DESCRIPTION.icon == "mdi:calendar-clock"


class TestNetroCalendar:
    """Test class for NetroCalendar entity."""

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "CTRL123"
        coordinator.device_info = {"name": "Test Controller"}
        coordinator.current_calendar_schedule = None
        coordinator.calendar_schedules = MagicMock(return_value=[])
        # Mock any potential async methods that might be called
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def calendar_entity(self, mock_controller_coordinator):
        """Create a NetroCalendar instance for testing."""
        return NetroCalendar(mock_controller_coordinator, NETRO_CALENDAR_DESCRIPTION)

    def test_netro_calendar_initialization(
        self, calendar_entity, mock_controller_coordinator
    ):
        """Test NetroCalendar initialization."""
        assert calendar_entity.coordinator == mock_controller_coordinator
        assert calendar_entity.entity_description == NETRO_CALENDAR_DESCRIPTION
        assert calendar_entity._attr_unique_id == "CTRL123-schedules"
        assert (
            calendar_entity._attr_device_info == mock_controller_coordinator.device_info
        )
        assert calendar_entity._attr_has_entity_name is True

    def test_event_property_no_schedule(
        self, calendar_entity, mock_controller_coordinator
    ):
        """Test event property when no current schedule."""
        mock_controller_coordinator.current_calendar_schedule = None

        result = calendar_entity.event

        assert result is None

    def test_event_property_with_schedule(
        self, calendar_entity, mock_controller_coordinator
    ):
        """Test event property when current schedule exists."""
        # Use timezone-aware datetime objects
        start_time = datetime.datetime(2023, 10, 1, 6, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2023, 10, 1, 6, 30, tzinfo=datetime.timezone.utc)

        test_schedule = {
            "start": start_time,
            "end": end_time,
            "summary": "Zone 1 Watering",
            "description": "Scheduled watering for Zone 1",
        }
        mock_controller_coordinator.current_calendar_schedule = test_schedule

        result = calendar_entity.event

        assert isinstance(result, CalendarEvent)
        assert result.start == test_schedule["start"]
        assert result.end == test_schedule["end"]
        assert result.summary == test_schedule["summary"]
        assert result.description == test_schedule["description"]

    @pytest.mark.asyncio
    async def test_async_get_events_empty(
        self, calendar_entity, mock_controller_coordinator
    ):
        """Test async_get_events when no schedules."""
        mock_controller_coordinator.calendar_schedules.return_value = []

        start_date = datetime.datetime(2023, 10, 1)
        end_date = datetime.datetime(2023, 10, 31)

        result = await calendar_entity.async_get_events(None, start_date, end_date)

        assert result == []
        mock_controller_coordinator.calendar_schedules.assert_called_once_with(
            start_date, end_date
        )

    @pytest.mark.asyncio
    async def test_async_get_events_with_schedules(
        self, calendar_entity, mock_controller_coordinator
    ):
        """Test async_get_events when schedules exist."""
        # Use timezone-aware datetime objects
        test_schedules = [
            {
                "start": datetime.datetime(
                    2023, 10, 1, 6, 0, tzinfo=datetime.timezone.utc
                ),
                "end": datetime.datetime(
                    2023, 10, 1, 6, 30, tzinfo=datetime.timezone.utc
                ),
                "summary": "Zone 1 Watering",
                "description": "Scheduled watering for Zone 1",
            },
            {
                "start": datetime.datetime(
                    2023, 10, 2, 7, 0, tzinfo=datetime.timezone.utc
                ),
                "end": datetime.datetime(
                    2023, 10, 2, 7, 15, tzinfo=datetime.timezone.utc
                ),
                "summary": "Zone 2 Watering",
                "description": "Scheduled watering for Zone 2",
            },
        ]
        mock_controller_coordinator.calendar_schedules.return_value = test_schedules

        start_date = datetime.datetime(2023, 10, 1)
        end_date = datetime.datetime(2023, 10, 31)

        result = await calendar_entity.async_get_events(None, start_date, end_date)

        assert len(result) == 2

        # Verify first event
        assert isinstance(result[0], CalendarEvent)
        assert result[0].start == test_schedules[0]["start"]
        assert result[0].end == test_schedules[0]["end"]
        assert result[0].summary == test_schedules[0]["summary"]
        assert result[0].description == test_schedules[0]["description"]

        # Verify second event
        assert isinstance(result[1], CalendarEvent)
        assert result[1].start == test_schedules[1]["start"]
        assert result[1].end == test_schedules[1]["end"]
        assert result[1].summary == test_schedules[1]["summary"]
        assert result[1].description == test_schedules[1]["description"]

    @pytest.mark.asyncio
    async def test_async_create_event_not_supported(self, calendar_entity):
        """Test async_create_event raises HomeAssistantError."""
        with pytest.raises(
            HomeAssistantError,
            match="Creating events is not supported for Netro calendars",
        ):
            await calendar_entity.async_create_event(
                dtstart=datetime.datetime(2023, 10, 1, 6, 0),
                dtend=datetime.datetime(2023, 10, 1, 6, 30),
                summary="Test Event",
            )

    @pytest.mark.asyncio
    async def test_async_delete_event_not_supported(self, calendar_entity):
        """Test async_delete_event raises HomeAssistantError."""
        with pytest.raises(
            HomeAssistantError,
            match="Deleting events is not supported for Netro calendars",
        ):
            await calendar_entity.async_delete_event("test_uid")

    @pytest.mark.asyncio
    async def test_async_update_event_not_supported(self, calendar_entity):
        """Test async_update_event raises HomeAssistantError."""
        with pytest.raises(
            HomeAssistantError,
            match="Updating events is not supported for Netro calendars",
        ):
            await calendar_entity.async_update_event(
                "test_uid", {"summary": "Updated Event"}
            )
