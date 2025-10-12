"""Tests for services in __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.netro_watering import (
    _async_register_services,
    async_setup,
    async_unload_entry,
)
from custom_components.netro_watering.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_MOISTURE,
    ATTR_ZONE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_SERIAL_NUMBER,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    NETRO_DEFAULT_ZONE_MODEL,
    SENSOR_DEVICE_TYPE,
)


class TestAsyncSetup:
    """Test class for async_setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_no_config(self, hass):
        """Test async_setup with no configuration."""
        config = {}
        result = await async_setup(hass, config)

        assert result is True
        assert DOMAIN in hass.data
        assert "parameters" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["parameters"] == {}

    @pytest.mark.asyncio
    async def test_async_setup_with_yaml_config(self, hass):
        """Test async_setup with YAML configuration."""
        config = {
            DOMAIN: {
                "delay_before_refresh": 10,
                "default_watering_delay": 5,
                "sensor_value_days_before_today": 2,
                "slowdown_factors": [{"from": "22:00", "to": "06:00", "sdf": 5}],
            }
        }

        result = await async_setup(hass, config)

        assert result is True
        assert DOMAIN in hass.data
        assert "parameters" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["parameters"]["delay_before_refresh"] == 10

    @pytest.mark.asyncio
    async def test_async_setup_invalid_api_url(self, hass):
        """Test async_setup with invalid API URL."""
        config = {DOMAIN: {"netro_api_url": "not-a-valid-url"}}

        with patch("custom_components.netro_watering._LOGGER") as mock_logger:
            result = await async_setup(hass, config)

            assert result is True
            mock_logger.warning.assert_called_once()


class TestServices:
    """Test class for service functions."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock hass instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        hass.services = MagicMock()
        hass.services.has_service.return_value = False
        return hass

    @pytest.fixture
    def mock_controller_entry(self):
        """Create a mock controller config entry."""
        entry = MagicMock()
        entry.entry_id = "test_controller_entry"
        entry.data = {
            CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "CTRL123",
            CONF_DEVICE_NAME: "Test Controller",
        }
        return entry

    @pytest.mark.asyncio
    async def test_set_moisture_service_success(self, mock_hass, mock_controller_entry):
        """Test successful set_moisture service call."""
        # Setup device registry mock
        device_entry = MagicMock()
        device_entry.model = NETRO_DEFAULT_ZONE_MODEL
        device_entry.name = "Test Zone"
        device_entry.identifiers = {(DOMAIN, "CTRL123_1")}
        device_entry.config_entries = {"test_controller_entry"}

        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = device_entry

        # Setup coordinator mock
        mock_coordinator = MagicMock()
        mock_hass.data[DOMAIN]["test_controller_entry"] = mock_coordinator
        mock_hass.config_entries.async_get_entry.return_value = mock_controller_entry

        with patch(
            "custom_components.netro_watering.dr.async_get",
            return_value=mock_device_registry,
        ), patch("custom_components.netro_watering.async_get_clientsession"), patch(
            "custom_components.netro_watering.NetroClient"
        ) as mock_client_class:

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Register services
            await _async_register_services(mock_hass, mock_controller_entry)

            # Verify service was registered
            mock_hass.services.async_register.assert_called()

    @pytest.mark.asyncio
    async def test_set_moisture_invalid_device(self, mock_hass, mock_controller_entry):
        """Test set_moisture with invalid device ID."""
        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = None

        with patch(
            "custom_components.netro_watering.dr.async_get",
            return_value=mock_device_registry,
        ):

            await _async_register_services(mock_hass, mock_controller_entry)

            # Get the registered service function
            service_calls = mock_hass.services.async_register.call_args_list
            set_moisture_call = None
            for call in service_calls:
                if call[0][1] == "set_moisture":  # service name
                    set_moisture_call = call[0][2]  # service function
                    break

            assert set_moisture_call is not None

            # Test with invalid device ID
            call_data = MagicMock()
            call_data.data = {ATTR_ZONE_ID: "invalid_device_id", ATTR_MOISTURE: 50}

            with pytest.raises(
                HomeAssistantError, match="Invalid Netro Watering device ID"
            ):
                await set_moisture_call(call_data)

    @pytest.mark.asyncio
    async def test_refresh_service_success(self, mock_hass):
        """Test successful refresh service call."""
        # Setup coordinator mock
        mock_coordinator = AsyncMock()
        mock_coordinator.name = "Test Device"
        mock_hass.data[DOMAIN]["test_entry"] = mock_coordinator

        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        await _async_register_services(mock_hass, entry)

        # Get the registered refresh service function
        service_calls = mock_hass.services.async_register.call_args_list
        refresh_call = None
        for call in service_calls:
            if call[0][1] == "refresh_data":  # service name
                refresh_call = call[0][2]  # service function
                break

        assert refresh_call is not None

        # Test successful refresh
        call_data = MagicMock()
        call_data.data = {ATTR_CONFIG_ENTRY_ID: "test_entry"}

        await refresh_call(call_data)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_service_invalid_entry(self, mock_hass):
        """Test refresh service with invalid config entry."""
        entry = MagicMock()
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}

        await _async_register_services(mock_hass, entry)

        # Get the registered refresh service function
        service_calls = mock_hass.services.async_register.call_args_list
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


class TestAsyncUnloadEntry:
    """Test class for async_unload_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass instance."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"test_entry": MagicMock()}}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.config_entries.async_loaded_entries = MagicMock(return_value=[])
        hass.services.async_remove = MagicMock()
        return hass

    @pytest.fixture
    def mock_controller_entry(self):
        """Create mock controller entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE}
        return entry

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, mock_hass, mock_controller_entry):
        """Test successful entry unload."""
        result = await async_unload_entry(mock_hass, mock_controller_entry)

        assert result is True
        mock_hass.config_entries.async_unload_platforms.assert_called_once()
        assert "test_entry" not in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_unload_entry_controller_removes_services(
        self, mock_hass, mock_controller_entry
    ):
        """Test that controller unload removes services when it's the last controller."""
        result = await async_unload_entry(mock_hass, mock_controller_entry)

        assert result is True
        # Should remove services since no other controllers loaded
        mock_hass.services.async_remove.assert_called()

    @pytest.mark.asyncio
    async def test_async_unload_entry_failed_unload(
        self, mock_hass, mock_controller_entry
    ):
        """Test handling of failed platform unload."""
        mock_hass.config_entries.async_unload_platforms.return_value = False

        result = await async_unload_entry(mock_hass, mock_controller_entry)

        assert result is False
        # Should not remove data if unload failed
        assert "test_entry" in mock_hass.data[DOMAIN]
