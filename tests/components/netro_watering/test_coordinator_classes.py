"""Tests for coordinator classes."""

import datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.netro_watering.const import (
    NETRO_STATUS_DISABLE,
    NETRO_STATUS_ENABLE,
)
from custom_components.netro_watering.coordinator import (
    NetroControllerUpdateCoordinator,
    NetroSensorUpdateCoordinator,
)


class TestNetroSensorUpdateCoordinator:
    """Test suite for NetroSensorUpdateCoordinator class."""

    @pytest.fixture
    def sensor_data_reference(self):
        """Load reference sensor data from JSON file."""
        reference_file = Path(__file__).parent / "reference_data" / "sensor_data.json"
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def coordinator(self, hass: HomeAssistant):
        """Create a NetroSensorUpdateCoordinator instance for testing."""
        return NetroSensorUpdateCoordinator(
            hass=hass,
            refresh_interval=30,
            sensor_value_days_before_today=2,
            serial_number="TEST_SENSOR_123",
            device_type="sensor",
            device_name="Test Sensor",
            hw_version="1.0",
            sw_version="2.0",
        )

    @pytest.fixture
    def empty_sensor_data(self):
        """Create sensor data with empty sensor_data array."""
        return {
            "status": "OK",
            "meta": {
                "time": "2025-10-10T20:58:13",
                "tid": "1760129893_EMPTY",
                "version": "1.0",
                "token_limit": 2000,
                "token_remaining": 1950,
                "last_active": "2025-10-10T20:58:13",
                "token_reset": "2025-10-11T00:00:00",
            },
            "data": {"sensor_data": []},
        }

    async def test_async_update_data_with_valid_data(
        self, coordinator, sensor_data_reference, snapshot
    ):
        """Test _async_update_data with valid sensor data."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_sensor_data.return_value = sensor_data_reference
            mock_client_class.return_value = mock_client

            # Execute the update - THIS calls client.get_sensor_data() internally
            await coordinator._async_update_data()

            # Just verify the method was called with correct coordinator details
            # (dates will vary daily so we focus on structure)
            assert mock_client.get_sensor_data.call_count == 1
            call_args = mock_client.get_sensor_data.call_args

            # Verify the call structure
            assert call_args[0][0] == coordinator.serial_number  # First positional arg
            assert "start_date" in call_args[1]  # keyword argument
            assert "end_date" in call_args[1]  # keyword argument

            # Verify coordinator attributes are properly set
            result = {
                "serial_number": coordinator.serial_number,
                "device_name": coordinator.device_name,
                "id": coordinator.id,
                "moisture": coordinator.moisture,
                "sunlight": coordinator.sunlight,
                "celsius": coordinator.celsius,
                "fahrenheit": coordinator.fahrenheit,
                "battery_level": coordinator.battery_level,
                "time_iso": coordinator.time.isoformat(),
                "local_date_iso": coordinator.local_date.isoformat(),
                "local_time_str": coordinator.local_time.isoformat(),
                "metadata_version": coordinator.metadata.version,
                "metadata_token_limit": coordinator.metadata.token_limit,
                "metadata_token_remaining": coordinator.metadata.token_remaining,
                "metadata_tid": coordinator.metadata.tid,
                "token_remaining": coordinator.token_remaining,
            }

            assert result == snapshot

    async def test_async_update_data_date_calculation(
        self, coordinator, sensor_data_reference, snapshot
    ):
        """Test that _async_update_data calculates dates correctly."""
        import datetime

        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_sensor_data.return_value = sensor_data_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await coordinator._async_update_data()

            # Get the actual call arguments
            call_args = mock_client.get_sensor_data.call_args
            start_date_called = call_args[1]["start_date"]
            end_date_called = call_args[1]["end_date"]

            # Parse the dates to validate the calculation logic
            start_date_obj = datetime.datetime.strptime(
                start_date_called, "%Y-%m-%d"
            ).date()
            end_date_obj = datetime.datetime.strptime(
                end_date_called, "%Y-%m-%d"
            ).date()

            # Calculate expected difference in days
            days_difference = (end_date_obj - start_date_obj).days

            result = {
                "sensor_value_days_before_today": coordinator.sensor_value_days_before_today,
                "actual_days_difference": days_difference,
                "date_calculation_correct": days_difference
                == coordinator.sensor_value_days_before_today,
                "mock_was_called": mock_client.get_sensor_data.called,
                "call_count": mock_client.get_sensor_data.call_count,
            }

            assert result == snapshot

    async def test_async_update_data_with_empty_sensor_data(
        self, coordinator, empty_sensor_data, snapshot
    ):
        """Test _async_update_data with empty sensor data array."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_sensor_data.return_value = empty_sensor_data
            mock_client_class.return_value = mock_client

            # Execute the update
            await coordinator._async_update_data()

            # With empty sensor_data, sensor attributes should remain None
            result = {
                "metadata_exists": coordinator.metadata is not None,
                "metadata_version": (
                    coordinator.metadata.version if coordinator.metadata else None
                ),
                "metadata_token_remaining": (
                    coordinator.metadata.token_remaining
                    if coordinator.metadata
                    else None
                ),
                "id": coordinator.id,
                "moisture": coordinator.moisture,
                "sunlight": coordinator.sunlight,
                "celsius": coordinator.celsius,
                "fahrenheit": coordinator.fahrenheit,
                "battery_level": coordinator.battery_level,
                "time": coordinator.time,
                "local_date": coordinator.local_date,
                "local_time": coordinator.local_time,
                "token_remaining": coordinator.token_remaining,
            }

            assert result == snapshot

    async def test_async_update_data_metadata_processing(
        self, coordinator, sensor_data_reference, snapshot
    ):
        """Test that metadata is correctly processed."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_sensor_data.return_value = sensor_data_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await coordinator._async_update_data()

            # Verify metadata attributes
            metadata = coordinator.metadata
            result = {
                "version": metadata.version,
                "token_limit": metadata.token_limit,
                "token_remaining": metadata.token_remaining,
                "tid": metadata.tid,
                "last_active_date_iso": metadata.last_active_date.isoformat(),
                "time_iso": metadata.time.isoformat(),
                "token_reset_date_iso": metadata.token_reset_date.isoformat(),
            }

            assert result == snapshot

    async def test_async_update_data_sensor_data_processing(
        self, coordinator, sensor_data_reference, snapshot
    ):
        """Test that sensor data (first element) is correctly processed."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_sensor_data.return_value = sensor_data_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await coordinator._async_update_data()

            # Verify sensor data attributes (should be from first element)
            expected_first_sensor = sensor_data_reference["data"]["sensor_data"][0]
            result = {
                "id": coordinator.id,
                "expected_id": expected_first_sensor["id"],
                "moisture": coordinator.moisture,
                "expected_moisture": expected_first_sensor["moisture"],
                "sunlight": coordinator.sunlight,
                "expected_sunlight": expected_first_sensor["sunlight"],
                "celsius": coordinator.celsius,
                "expected_celsius": expected_first_sensor["celsius"],
                "fahrenheit": coordinator.fahrenheit,
                "expected_fahrenheit": expected_first_sensor["fahrenheit"],
                "battery_level": coordinator.battery_level,
                "expected_battery_level": expected_first_sensor["battery_level"],
                "local_date_str": coordinator.local_date.isoformat(),
                "expected_local_date": expected_first_sensor["local_date"],
                "local_time_str": coordinator.local_time.isoformat(),
                "expected_local_time": expected_first_sensor["local_time"],
            }

            assert result == snapshot

    async def test_async_update_data_with_api_error(self, coordinator, snapshot):
        """Test _async_update_data when API call fails."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock to raise an exception
            mock_client = AsyncMock()
            mock_client.get_sensor_data.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            # Execute the update and expect an exception
            with pytest.raises(Exception) as exc_info:
                await coordinator._async_update_data()

            result = {
                "exception_type": type(exc_info.value).__name__,
                "exception_message": str(exc_info.value),
            }

            assert result == snapshot

    def test_device_info_property(self, coordinator, snapshot):
        """Test the device_info property."""
        device_info = coordinator.device_info

        result = {
            "name": device_info["name"],
            "identifiers": list(device_info["identifiers"]),
            "manufacturer": device_info["manufacturer"],
            "hw_version": device_info["hw_version"],
            "sw_version": device_info["sw_version"],
            "model": device_info["model"],
        }

        assert result == snapshot

    def test_metadata_property_when_none(self, coordinator, snapshot):
        """Test metadata property when _metadata is None."""
        # Ensure _metadata is None
        coordinator._metadata = None

        result = {
            "metadata": coordinator.metadata,
        }

        assert result == snapshot

    def test_token_remaining_property_when_metadata_none(self, coordinator, snapshot):
        """Test token_remaining property when metadata is None."""
        # Ensure _metadata is None
        coordinator._metadata = None

        result = {
            "token_remaining": coordinator.token_remaining,
        }

        assert result == snapshot

    def test_str_representation(self, coordinator, snapshot):
        """Test the __str__ method."""
        result = {
            "str_representation": str(coordinator),
        }

        assert result == snapshot


class TestNetroControllerUpdateCoordinator:
    """Test suite for NetroControllerUpdateCoordinator class."""

    @pytest.fixture
    def controller_info_reference(self):
        """Load reference controller info data from JSON file."""
        reference_file = (
            Path(__file__).parent / "reference_data" / "controller_info.json"
        )
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def moistures_reference(self):
        """Load reference moistures data from JSON file."""
        reference_file = Path(__file__).parent / "reference_data" / "moistures.json"
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def schedules_reference(self):
        """Load reference schedules data from JSON file."""
        reference_file = Path(__file__).parent / "reference_data" / "schedules.json"
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def controller_coordinator(self, hass: HomeAssistant):
        """Create a NetroControllerUpdateCoordinator instance for testing."""
        return NetroControllerUpdateCoordinator(
            hass=hass,
            refresh_interval=15,
            slowdown_factors=[
                {"from": 8.0, "to": 12.0, "sdf": 2},
                {"from": 14.0, "to": 18.0, "sdf": 3},
            ],
            schedules_months_before=6,
            schedules_months_after=2,
            serial_number="E4********38",
            device_type="controller",
            device_name="Test Controller",
            hw_version="1.2",
            sw_version="1.1.1",
        )

    async def test_async_update_data_with_valid_data(
        self,
        controller_coordinator,
        controller_info_reference,
        moistures_reference,
        schedules_reference,
        snapshot,
    ):
        """Test _async_update_data with valid controller data."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await controller_coordinator._async_update_data()

            # Verify all three API calls were made
            assert mock_client.get_info.call_count == 1
            assert mock_client.get_moistures.call_count == 1
            assert mock_client.get_schedules.call_count == 1

            # Verify get_info was called correctly
            mock_client.get_info.assert_called_with(
                controller_coordinator.serial_number
            )

            # Verify get_moistures was called correctly
            mock_client.get_moistures.assert_called_with(
                controller_coordinator.serial_number
            )

            # Verify coordinator attributes are properly set
            result = {
                "serial_number": controller_coordinator.serial_number,
                "device_name": controller_coordinator.device_name,
                "zone_num": controller_coordinator.zone_num,
                "status": controller_coordinator.status,
                "metadata_version": controller_coordinator.metadata.version,
                "metadata_token_remaining": controller_coordinator.metadata.token_remaining,
                "number_of_active_zones": controller_coordinator.number_of_active_zones,
                "active_zones_keys": list(controller_coordinator.active_zones.keys()),
                "enabled": controller_coordinator.enabled,
                "watering": controller_coordinator.watering,
                "current_slowdown_factor": controller_coordinator.current_slowdown_factor,
            }

            assert result == snapshot

    async def test_async_update_data_zone_processing(
        self,
        controller_coordinator,
        controller_info_reference,
        moistures_reference,
        schedules_reference,
        snapshot,
    ):
        """Test that zones are correctly processed and created."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await controller_coordinator._async_update_data()

            # Get zones data for verification
            zones = controller_coordinator.active_zones

            result = {
                "number_of_zones": len(zones),
                "zone_data": {
                    zone_id: {
                        "name": zone.name,
                        "ith": zone.ith,
                        "enabled": zone.enabled,
                        "smart": zone.smart,
                        "serial_number": zone.serial_number,
                        "has_moistures": len(zone.moistures) > 0,
                        "has_past_schedules": len(zone.past_schedules) > 0,
                        "has_coming_schedules": len(zone.coming_schedules) > 0,
                    }
                    for zone_id, zone in zones.items()
                },
            }

            assert result == snapshot

    async def test_async_update_data_schedules_processing(
        self,
        controller_coordinator,
        controller_info_reference,
        moistures_reference,
        schedules_reference,
        snapshot,
    ):
        """Test that schedules are correctly processed and distributed to zones."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await controller_coordinator._async_update_data()

            # Verify schedules processing
            zones = controller_coordinator.active_zones
            result = {
                "total_schedules_in_coordinator": len(
                    controller_coordinator._schedules
                ),
                "schedules_per_zone": {
                    zone_id: {
                        "past_schedules_count": len(zone.past_schedules),
                        "coming_schedules_count": len(zone.coming_schedules),
                        "first_past_schedule_status": (
                            zone.past_schedules[0]["status"]
                            if zone.past_schedules
                            else None
                        ),
                        "first_coming_schedule_status": (
                            zone.coming_schedules[0]["status"]
                            if zone.coming_schedules
                            else None
                        ),
                    }
                    for zone_id, zone in zones.items()
                },
            }

            assert result == snapshot

    async def test_async_update_data_moistures_processing(
        self,
        controller_coordinator,
        controller_info_reference,
        moistures_reference,
        schedules_reference,
        snapshot,
    ):
        """Test that moistures are correctly processed and distributed to zones."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Execute the update
            await controller_coordinator._async_update_data()

            # Verify moistures processing
            zones = controller_coordinator.active_zones
            result = {
                "total_moistures_in_coordinator": len(
                    controller_coordinator._moistures
                ),
                "moistures_per_zone": {
                    zone_id: {
                        "moistures_count": len(zone.moistures),
                        "current_moisture": zone.moisture,
                        "first_moisture_date": (
                            zone.moistures[0]["date"] if zone.moistures else None
                        ),
                    }
                    for zone_id, zone in zones.items()
                },
            }

            assert result == snapshot

    async def test_async_update_data_slowdown_factor_calculation(
        self,
        controller_coordinator,
        controller_info_reference,
        moistures_reference,
        schedules_reference,
        snapshot,
    ):
        """Test that slowdown factor is correctly calculated and applied."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Mock datetime.datetime.now() to return a specific time for predictable slowdown factor
            with patch(
                "custom_components.netro_watering.coordinator.datetime"
            ) as mock_datetime:
                # Create a real datetime object for time 10:00
                real_datetime = datetime.datetime(2025, 10, 11, 10, 0, 0)
                mock_datetime.datetime.now.return_value = real_datetime
                mock_datetime.timedelta = datetime.timedelta  # Keep real timedelta
                mock_datetime.date = datetime.date  # Keep real date
                mock_datetime.time = datetime.time  # Keep real time

                # Execute the update
                await controller_coordinator._async_update_data()

                result = {
                    "refresh_interval": controller_coordinator.refresh_interval,
                    "current_slowdown_factor": controller_coordinator.current_slowdown_factor,
                    "update_interval_minutes": controller_coordinator.update_interval.total_seconds()
                    / 60,
                    "expected_update_interval": controller_coordinator.refresh_interval
                    * controller_coordinator.current_slowdown_factor,
                }

                assert result == snapshot

    async def test_async_update_data_with_api_error_get_info(
        self, controller_coordinator, snapshot
    ):
        """Test _async_update_data when get_info API call fails."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            # Configure the mock to raise an exception on get_info
            mock_client = AsyncMock()
            mock_client.get_info.side_effect = Exception("API Error on get_info")
            mock_client_class.return_value = mock_client

            # Execute the update and expect an exception
            with pytest.raises(Exception) as exc_info:
                await controller_coordinator._async_update_data()

            result = {
                "exception_type": type(exc_info.value).__name__,
                "exception_message": str(exc_info.value),
                "get_info_called": mock_client.get_info.called,
                "get_moistures_called": mock_client.get_moistures.called,
                "get_schedules_called": mock_client.get_schedules.called,
            }

            assert result == snapshot

    def test_device_info_property(self, controller_coordinator, snapshot):
        """Test the device_info property."""
        device_info = controller_coordinator.device_info

        result = {
            "identifiers": list(device_info["identifiers"]),
        }

        assert result == snapshot

    def test_properties_when_not_initialized(self, controller_coordinator, snapshot):
        """Test properties when coordinator hasn't been updated yet."""
        result = {}

        # Test properties that should handle missing status
        try:
            result["enabled"] = controller_coordinator.enabled
        except AttributeError as e:
            result["enabled_error"] = str(e)

        try:
            result["watering"] = controller_coordinator.watering
        except AttributeError as e:
            result["watering_error"] = str(e)

        # These properties might also fail before initialization
        try:
            result["number_of_active_zones"] = (
                controller_coordinator.number_of_active_zones
            )
        except AttributeError as e:
            result["number_of_active_zones_error"] = str(e)

        try:
            result["metadata"] = controller_coordinator.metadata
        except AttributeError as e:
            result["metadata_error"] = str(e)

        try:
            result["token_remaining"] = controller_coordinator.token_remaining
        except AttributeError as e:
            result["token_remaining_error"] = str(e)

        assert result == snapshot

    def test_str_representation_controller(self, controller_coordinator, snapshot):
        """Test the __str__ method for controller."""
        result = {
            "str_representation": str(controller_coordinator),
        }

        assert result == snapshot


class TestNetroControllerActionMethods:
    """Tests for NetroControllerUpdateCoordinator action methods (POST operations)."""

    @pytest.fixture
    def controller_coordinator(self, hass):
        """Create a NetroControllerUpdateCoordinator for testing action methods."""
        return NetroControllerUpdateCoordinator(
            hass=hass,
            device_name="Test Controller Actions",
            serial_number="TEST_CONTROLLER_ACTIONS_123",
            refresh_interval=15,
            slowdown_factors=[{"from": 8.0, "to": 12.0, "sdf": 2}],
            schedules_months_before=6,
            schedules_months_after=2,
            device_type="controller",
            hw_version="1.0",
            sw_version="1.0.0",
        )

    async def test_enable_controller(self, controller_coordinator):
        """Test enable method calls API correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.enable()

            # Verify client creation and method call
            mock_client.set_status.assert_called_once_with(
                controller_coordinator.serial_number,
                enabled=NETRO_STATUS_ENABLE,
            )

    async def test_disable_controller(self, controller_coordinator):
        """Test disable method calls API correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.disable()

            # Verify client creation and method call
            mock_client.set_status.assert_called_once_with(
                controller_coordinator.serial_number,
                enabled=NETRO_STATUS_DISABLE,
            )

    async def test_no_water_default_days(self, controller_coordinator):
        """Test no_water method with default days parameter."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.no_water()

            # Verify default value is used (1 day)
            mock_client.no_water.assert_called_once_with(
                controller_coordinator.serial_number,
                days=1,
            )

    async def test_no_water_specific_days(self, controller_coordinator):
        """Test no_water method with specific days parameter."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.no_water(days=5)

            # Verify specific days value is used
            mock_client.no_water.assert_called_once_with(
                controller_coordinator.serial_number,
                days=5,
            )

    async def test_start_watering_with_datetime_formatting(
        self, controller_coordinator
    ):
        """Test start_watering formats datetime correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            test_time = datetime.time(14, 30)  # 2:30 PM

            await controller_coordinator.start_watering(
                duration=15, delay=5, start_time=test_time
            )

            # Verify datetime formatting (time object uses default date 1900-01-01)
            mock_client.water.assert_called_once_with(
                controller_coordinator.serial_number,
                duration_minutes=15,
                delay_minutes=5,
                start_time="1900-01-01 14:30",  # time object uses default date
            )

    async def test_start_watering_with_none_start_time(self, controller_coordinator):
        """Test start_watering handles None start_time correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.start_watering(
                duration=20, delay=0, start_time=None
            )

            # Verify None is passed through
            mock_client.water.assert_called_once_with(
                controller_coordinator.serial_number,
                duration_minutes=20,
                delay_minutes=0,
                start_time=None,
            )

    async def test_stop_watering_controller(self, controller_coordinator):
        """Test stop_watering method calls API correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await controller_coordinator.stop_watering()

            # Verify client creation and method call
            mock_client.stop_water.assert_called_once_with(
                controller_coordinator.serial_number,
            )


class TestNetroZoneActionMethods:
    """Tests for NetroControllerUpdateCoordinator.Zone action methods (POST operations)."""

    @pytest.fixture
    def zone_coordinator(self, hass):
        """Create a Zone for testing action methods."""
        # Create a parent controller first
        parent_controller = NetroControllerUpdateCoordinator(
            hass=hass,
            device_name="Parent Controller",
            serial_number="PARENT_CONTROLLER_123",
            refresh_interval=15,
            slowdown_factors=[],
            schedules_months_before=6,
            schedules_months_after=2,
            device_type="controller",
            hw_version="1.0",
            sw_version="1.0.0",
        )

        # Create zone coordinator (nested class)
        return parent_controller.Zone(
            controller=parent_controller,
            ith=2,  # Zone 2
            enabled=True,
            smart="smart",
            name="Test Zone",
            serial_number="PARENT_CONTROLLER_123",
        )

    async def test_zone_start_watering_with_datetime_formatting(self, zone_coordinator):
        """Test zone start_watering formats datetime and includes zone parameter."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            test_time = datetime.time(9, 15)  # 9:15 AM

            await zone_coordinator.start_watering(
                duration=10, delay=2, start_time=test_time
            )

            # Verify datetime formatting and zone parameter
            mock_client.water.assert_called_once_with(
                zone_coordinator.parent_controller.serial_number,
                duration_minutes=10,
                zones=["2"],  # Zone number as string
                delay_minutes=2,
                start_time="1900-01-01 09:15",  # time object uses default date
            )

    async def test_zone_start_watering_with_none_start_time(self, zone_coordinator):
        """Test zone start_watering handles None start_time correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await zone_coordinator.start_watering(duration=25, delay=1, start_time=None)

            # Verify None is passed through and zone is included
            mock_client.water.assert_called_once_with(
                zone_coordinator.parent_controller.serial_number,
                duration_minutes=25,
                zones=["2"],  # Zone number as string
                delay_minutes=1,
                start_time=None,
            )

    async def test_zone_stop_watering(self, zone_coordinator):
        """Test zone stop_watering method calls API correctly."""
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await zone_coordinator.stop_watering()

            # Verify client creation and method call uses parent controller serial
            mock_client.stop_water.assert_called_once_with(
                zone_coordinator.parent_controller.serial_number,
            )

    def test_zone_properties_and_relationships(self, zone_coordinator, snapshot):
        """Test zone coordinator properties and parent relationship."""
        result = {
            "zone_ith": zone_coordinator.ith,
            "zone_serial": zone_coordinator.serial_number,
            "parent_serial": zone_coordinator.parent_controller.serial_number,
            "parent_name": zone_coordinator.parent_controller.device_name,
            "zone_enabled": zone_coordinator.enabled,
        }

        assert result == snapshot


class TestNetroControllerCalendarMethods:
    """Tests for NetroControllerUpdateCoordinator calendar methods requiring fully initialized coordinator."""

    @pytest.fixture
    def controller_info_reference(self):
        """Load reference controller info data from JSON file."""
        reference_file = (
            Path(__file__).parent / "reference_data" / "controller_info.json"
        )
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def moistures_reference(self):
        """Load reference moistures data from JSON file."""
        reference_file = Path(__file__).parent / "reference_data" / "moistures.json"
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    def schedules_reference(self):
        """Load reference schedules data from JSON file."""
        reference_file = Path(__file__).parent / "reference_data" / "schedules.json"
        with reference_file.open() as f:
            return json.load(f)

    @pytest.fixture
    async def initialized_controller_coordinator(
        self, hass, controller_info_reference, moistures_reference, schedules_reference
    ):
        """Create a fully initialized NetroControllerUpdateCoordinator with real data."""
        coordinator = NetroControllerUpdateCoordinator(
            hass=hass,
            refresh_interval=15,
            slowdown_factors=[
                {"from": 8.0, "to": 12.0, "sdf": 2},
                {"from": 14.0, "to": 18.0, "sdf": 3},
            ],
            schedules_months_before=6,
            schedules_months_after=2,
            serial_number="E4********38",
            device_type="controller",
            device_name="Test Controller",
            hw_version="1.2",
            sw_version="1.1.1",
        )

        # Mock the API calls to initialize the coordinator with real data
        with patch(
            "custom_components.netro_watering.coordinator.NetroClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_info.return_value = controller_info_reference
            mock_client.get_moistures.return_value = moistures_reference
            mock_client.get_schedules.return_value = schedules_reference
            mock_client_class.return_value = mock_client

            # Initialize the coordinator with full data
            await coordinator._async_update_data()

        return coordinator

    async def test_calendar_schedule_formatting(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test _calendar_schedule formats a single schedule correctly."""
        # Get a sample schedule from the initialized coordinator
        if initialized_controller_coordinator._schedules:
            sample_schedule = initialized_controller_coordinator._schedules[0]

            # Test the calendar formatting
            calendar_event = initialized_controller_coordinator._calendar_schedule(
                sample_schedule
            )

            # Verify the structure and format
            result = {
                "event_keys": list(calendar_event.keys()),
                "start_type": type(calendar_event["start"]).__name__,
                "end_type": type(calendar_event["end"]).__name__,
                "summary_contains_zone_name": len(calendar_event["summary"]) > 0,
                "description_contains_duration": "Duration:"
                in calendar_event["description"],
                "description_contains_source": any(
                    source in calendar_event["description"]
                    for source in [
                        "schedule from programs",
                        "Netro generated schedule",
                        "manual watering",
                    ]
                ),
                "description_contains_status": any(
                    status in calendar_event["description"]
                    for status in [
                        "has been executed",
                        "currently being executed",
                        "is planned",
                    ]
                ),
            }

            assert result == snapshot

    async def test_current_calendar_schedule_with_future_schedules(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test current_calendar_schedule returns next schedule when schedules exist."""
        with patch(
            "custom_components.netro_watering.coordinator.strftime"
        ) as mock_strftime:
            # Mock current time to be before all schedules (October 1, 2025)
            mock_strftime.return_value = "2025-10-01T12:00:00"

            current_schedule = (
                initialized_controller_coordinator.current_calendar_schedule
            )

            result = {
                "has_current_schedule": current_schedule is not None,
                "schedule_keys": (
                    list(current_schedule.keys()) if current_schedule else None
                ),
                "has_start_time": current_schedule and "start" in current_schedule,
                "has_end_time": current_schedule and "end" in current_schedule,
                "has_summary": current_schedule and "summary" in current_schedule,
                "has_description": current_schedule
                and "description" in current_schedule,
            }

            assert result == snapshot

    async def test_current_calendar_schedule_no_future_schedules(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test current_calendar_schedule returns None when no future schedules exist."""
        with patch(
            "custom_components.netro_watering.coordinator.strftime"
        ) as mock_strftime:
            # Mock current time to be after all schedules (December 31, 2025)
            mock_strftime.return_value = "2025-12-31T23:59:59"

            current_schedule = (
                initialized_controller_coordinator.current_calendar_schedule
            )

            result = {
                "current_schedule": current_schedule,
            }

            assert result == snapshot

    async def test_calendar_schedules_date_filtering(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test calendar_schedules filters by date range correctly."""
        # Test with a specific date range (timezone-aware to match schedule data)
        start_date = datetime.datetime(2025, 9, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2025, 10, 31, tzinfo=datetime.timezone.utc)

        filtered_schedules = initialized_controller_coordinator.calendar_schedules(
            start_date=start_date, end_date=end_date
        )

        result = {
            "number_of_filtered_schedules": len(filtered_schedules),
            "all_have_required_keys": all(
                all(
                    key in schedule
                    for key in ["start", "end", "summary", "description"]
                )
                for schedule in filtered_schedules
            ),
            "all_within_date_range": (
                all(
                    start_date <= schedule["start"] <= end_date
                    for schedule in filtered_schedules
                )
                if filtered_schedules
                else True
            ),
        }

        assert result == snapshot

    async def test_calendar_schedules_no_date_filtering(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test calendar_schedules returns all schedules when no date filter is applied."""
        all_schedules = initialized_controller_coordinator.calendar_schedules()

        result = {
            "total_schedules": len(all_schedules),
            "first_schedule_keys": (
                list(all_schedules[0].keys()) if all_schedules else None
            ),
            "has_schedules": len(all_schedules) > 0,
        }

        assert result == snapshot

    async def test_calendar_schedule_description_formatting(
        self, initialized_controller_coordinator, snapshot
    ):
        """Test that calendar schedule descriptions are formatted correctly for different sources and statuses."""
        if initialized_controller_coordinator._schedules:
            # Test multiple schedules to cover different sources and statuses
            descriptions = []
            for i, schedule in enumerate(
                initialized_controller_coordinator._schedules[:3]
            ):  # Test first 3
                calendar_event = initialized_controller_coordinator._calendar_schedule(
                    schedule
                )
                descriptions.append(
                    {
                        f"schedule_{i}_description": calendar_event["description"],
                        f"schedule_{i}_source": schedule.get("source", "unknown"),
                        f"schedule_{i}_status": schedule.get("status", "unknown"),
                    }
                )

            result = {
                "descriptions_tested": len(descriptions),
                "descriptions": descriptions,
            }

            assert result == snapshot
