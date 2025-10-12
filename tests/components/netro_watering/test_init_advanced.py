"""Additional tests for __init__.py to reach 70% coverage."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.netro_watering import (
    WeatherConditions,
    _async_register_services,
    async_setup,
    async_setup_entry,
)
from custom_components.netro_watering.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_NOWATER_DAYS,
    ATTR_WEATHER_CONDITION,
    ATTR_WEATHER_DATE,
    ATTR_WEATHER_TEMP,
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SW_VERSION,
    CONF_DEVICE_TYPE,
    CONF_SERIAL_NUMBER,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    SENSOR_DEVICE_TYPE,
)


class TestAsyncSetupAdvanced:
    """Advanced tests for async_setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_valid_api_url(self, hass):
        """Test async_setup with valid API URL."""
        config = {DOMAIN: {"netro_api_url": "https://api.custom-netro.com/v1"}}

        with patch(
            "custom_components.netro_watering.validators.url", return_value=True
        ), patch("custom_components.netro_watering.NetroConfig") as mock_config:

            result = await async_setup(hass, config)

            assert result is True
            # Verify that the custom URL was set
            assert mock_config.default_base_url == "https://api.custom-netro.com/v1"


class TestAsyncSetupEntry:
    """Test class for async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {"parameters": {}}}
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        return hass

    @pytest.fixture
    def mock_sensor_entry(self):
        """Create mock sensor config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "sensor_entry_123"
        entry.data = {
            CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "SENS123",
            CONF_DEVICE_NAME: "Test Sensor",
            CONF_DEVICE_HW_VERSION: "1.0",
            CONF_DEVICE_SW_VERSION: "2.0",
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_controller_entry(self):
        """Create mock controller config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "controller_entry_123"
        entry.data = {
            CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "CTRL123",
            CONF_DEVICE_NAME: "Test Controller",
            CONF_DEVICE_HW_VERSION: "1.0",
            CONF_DEVICE_SW_VERSION: "2.0",
        }
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_sensor_success(self, mock_hass, mock_sensor_entry):
        """Test successful async_setup_entry for sensor."""
        with patch(
            "custom_components.netro_watering.NetroSensorUpdateCoordinator"
        ) as mock_coordinator_class, patch(
            "custom_components.netro_watering._async_register_services",
            new_callable=AsyncMock,
        ):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(mock_hass, mock_sensor_entry)

            assert result is True
            mock_coordinator_class.assert_called_once()
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            assert mock_hass.data[DOMAIN]["sensor_entry_123"] == mock_coordinator

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_success(
        self, mock_hass, mock_controller_entry
    ):
        """Test successful async_setup_entry for controller."""
        with patch(
            "custom_components.netro_watering.NetroControllerUpdateCoordinator"
        ) as mock_coordinator_class, patch(
            "custom_components.netro_watering.dr.async_get"
        ) as mock_device_registry, patch(
            "custom_components.netro_watering._async_register_services",
            new_callable=AsyncMock,
        ):

            mock_coordinator = AsyncMock()
            mock_coordinator.serial_number = "CTRL123"
            mock_coordinator.device_name = "Test Controller"
            mock_coordinator.sw_version = "2.0"
            mock_coordinator.hw_version = "1.0"
            mock_coordinator_class.return_value = mock_coordinator

            mock_dev_reg = MagicMock()
            mock_device_registry.return_value = mock_dev_reg

            result = await async_setup_entry(mock_hass, mock_controller_entry)

            assert result is True
            mock_coordinator_class.assert_called_once()
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            mock_dev_reg.async_get_or_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_invalid_device_type(self, mock_hass):
        """Test async_setup_entry with invalid device type."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            CONF_DEVICE_TYPE: "invalid_type",
            CONF_SERIAL_NUMBER: "TEST123",
            CONF_DEVICE_NAME: "Test Device",
        }

        with pytest.raises(
            HomeAssistantError, match="Config entry netro device type does not exist"
        ):
            await async_setup_entry(mock_hass, entry)


class TestServicesAdvanced:
    """Advanced tests for service functions."""

    @pytest.fixture
    def mock_hass_with_coordinator(self):
        """Create mock hass with coordinator."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}

        # Mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.serial_number = "CTRL123"
        mock_coordinator.name = "Test Controller"
        mock_coordinator.no_water = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        hass.data[DOMAIN]["test_entry"] = mock_coordinator

        hass.services = MagicMock()
        hass.services.has_service.return_value = False

        return hass, mock_coordinator

    @pytest.mark.asyncio
    async def test_report_weather_service_complete(self, mock_hass_with_coordinator):
        """Test report_weather service with all parameters."""
        hass, _ = mock_hass_with_coordinator

        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        with patch("custom_components.netro_watering.async_get_clientsession"), patch(
            "custom_components.netro_watering.NetroClient"
        ) as mock_client_class:

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await _async_register_services(hass, entry)

            # Get the report_weather service function
            service_calls = hass.services.async_register.call_args_list
            report_weather_call = None
            for call in service_calls:
                if call[0][1] == "report_weather":
                    report_weather_call = call[0][2]
                    break

            assert report_weather_call is not None

            # Test service call with full weather data
            call_data = MagicMock()
            call_data.data = {
                ATTR_CONFIG_ENTRY_ID: "test_entry",
                ATTR_WEATHER_DATE: date(2023, 10, 15),
                ATTR_WEATHER_CONDITION: WeatherConditions.rain,
                ATTR_WEATHER_TEMP: 22.5,
                "weather_rain": 5.2,
                "weather_humidity": 80,
                "weather_pressure": 1013.25,
            }

            await report_weather_call(call_data)

            mock_client.report_weather.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_weather_missing_date(self, mock_hass_with_coordinator):
        """Test report_weather service with missing date."""
        hass, _ = mock_hass_with_coordinator

        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        await _async_register_services(hass, entry)

        # Get the report_weather service function
        service_calls = hass.services.async_register.call_args_list
        report_weather_call = None
        for call in service_calls:
            if call[0][1] == "report_weather":
                report_weather_call = call[0][2]
                break

        # Test with missing date (None)
        call_data = MagicMock()
        call_data.data = {ATTR_CONFIG_ENTRY_ID: "test_entry", ATTR_WEATHER_DATE: None}

        with pytest.raises(HomeAssistantError, match="'date' parameter is missing"):
            await report_weather_call(call_data)

    @pytest.mark.asyncio
    async def test_nowater_service_success(self, mock_hass_with_coordinator):
        """Test no_water service success."""
        hass, coordinator = mock_hass_with_coordinator

        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        await _async_register_services(hass, entry)

        # Get the no_water service function
        service_calls = hass.services.async_register.call_args_list
        nowater_call = None
        for call in service_calls:
            if call[0][1] == "no_water":
                nowater_call = call[0][2]
                break

        assert nowater_call is not None

        # Test successful no_water call
        call_data = MagicMock()
        call_data.data = {ATTR_CONFIG_ENTRY_ID: "test_entry", ATTR_NOWATER_DAYS: 7}

        await nowater_call(call_data)

        coordinator.no_water.assert_called_once_with(7)
        coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_invalid_config_entry(self, mock_hass_with_coordinator):
        """Test services with invalid config entry ID."""
        hass, _ = mock_hass_with_coordinator

        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        await _async_register_services(hass, entry)

        # Get the refresh service function
        service_calls = hass.services.async_register.call_args_list
        refresh_call = None
        for call in service_calls:
            if call[0][1] == "refresh_data":
                refresh_call = call[0][2]
                break

        # Test with invalid entry ID
        call_data = MagicMock()
        call_data.data = {ATTR_CONFIG_ENTRY_ID: "nonexistent_entry"}

        with pytest.raises(HomeAssistantError, match="Config entry id does not exist"):
            await refresh_call(call_data)


class TestAsyncSetupEntryParameterValidation:
    """Test parameter validation in async_setup_entry."""

    @pytest.mark.asyncio
    async def test_sensor_invalid_parameters(self, hass):
        """Test sensor setup with invalid parameters."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        entry.data = {
            CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "SENS123",
            CONF_DEVICE_NAME: "Test Sensor",
            CONF_DEVICE_HW_VERSION: "1.0",
            CONF_DEVICE_SW_VERSION: "2.0",
        }
        # Invalid options
        entry.options = {
            "sensor_value_days_before_today": "invalid_string",
            "sensor_refresh_interval": 999,  # out of range
        }

        hass.data = {DOMAIN: {"parameters": {}}}
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with patch(
            "custom_components.netro_watering.NetroSensorUpdateCoordinator"
        ) as mock_coordinator_class, patch(
            "custom_components.netro_watering._async_register_services",
            new_callable=AsyncMock,
        ), patch(
            "custom_components.netro_watering._LOGGER"
        ) as mock_logger:

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(hass, entry)

            assert result is True
            # Verify warnings were logged for invalid parameters
            assert mock_logger.warning.call_count >= 1

    @pytest.mark.asyncio
    async def test_controller_invalid_parameters(self, hass):
        """Test controller setup with invalid parameters."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        entry.data = {
            CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "CTRL123",
            CONF_DEVICE_NAME: "Test Controller",
            CONF_DEVICE_HW_VERSION: "1.0",
            CONF_DEVICE_SW_VERSION: "2.0",
        }
        # Invalid options
        entry.options = {
            "controller_refresh_interval": "not_a_number",
            "schedules_months_before": -5,  # out of range
            "schedules_months_after": 999,  # out of range
        }

        hass.data = {DOMAIN: {"parameters": {}}}
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with patch(
            "custom_components.netro_watering.NetroControllerUpdateCoordinator"
        ) as mock_coordinator_class, patch(
            "custom_components.netro_watering.dr.async_get"
        ), patch(
            "custom_components.netro_watering._async_register_services",
            new_callable=AsyncMock,
        ), patch(
            "custom_components.netro_watering._LOGGER"
        ) as mock_logger:

            mock_coordinator = AsyncMock()
            mock_coordinator.serial_number = "CTRL123"
            mock_coordinator.device_name = "Test Controller"
            mock_coordinator.sw_version = "2.0"
            mock_coordinator.hw_version = "1.0"
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(hass, entry)

            assert result is True
            # Verify warnings were logged for invalid parameters
            assert mock_logger.warning.call_count >= 1
