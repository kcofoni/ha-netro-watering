"""Tests for button platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.netro_watering.button import (
    NETRO_CONTROLLER_BUTTON_DESCRIPTION,
    NetroRefreshButton,
    async_setup_entry,
)
from custom_components.netro_watering.const import DOMAIN


class TestButtonAsyncSetupEntry:
    """Test class for button async_setup_entry function."""

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
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.fixture
    def mock_async_add_entities(self):
        """Create a mock AddEntitiesCallback."""
        return MagicMock(spec=AddEntitiesCallback)

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(
        self,
        mock_hass,
        mock_config_entry,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test successful async_setup_entry for button platform."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = mock_controller_coordinator

        with patch("custom_components.netro_watering.button._LOGGER") as mock_logger:
            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_config_entry,
                mock_async_add_entities,
            )

            # Verify logger was called
            mock_logger.info.assert_called_once_with(
                "Adding button entity for device = %s", "Test Controller"
            )

            # Verify async_add_entities was called
            mock_async_add_entities.assert_called_once()

            # Get the entities that were passed to async_add_entities
            call_args = mock_async_add_entities.call_args[0][0]

            # Should create 1 NetroRefreshButton entity
            assert len(call_args) == 1

            # Verify it's a NetroRefreshButton instance
            button_entity = call_args[0]
            assert isinstance(button_entity, NetroRefreshButton)
            assert (
                button_entity.entity_description == NETRO_CONTROLLER_BUTTON_DESCRIPTION
            )

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_coordinator(
        self,
        mock_hass,
        mock_config_entry,
        mock_async_add_entities,
    ):
        """Test async_setup_entry when coordinator is missing from hass.data."""
        # Don't add coordinator to hass.data

        with pytest.raises(KeyError):
            await async_setup_entry(
                mock_hass,
                mock_config_entry,
                mock_async_add_entities,
            )

    @pytest.mark.asyncio
    async def test_netro_refresh_button_creation_parameters(
        self,
        mock_hass,
        mock_config_entry,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test that NetroRefreshButton is created with correct parameters."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = mock_controller_coordinator

        await async_setup_entry(
            mock_hass,
            mock_config_entry,
            mock_async_add_entities,
        )

        # Get the created entity
        call_args = mock_async_add_entities.call_args[0][0]
        button_entity = call_args[0]

        # Verify the entity has the correct coordinator and description
        assert button_entity.coordinator == mock_controller_coordinator
        assert button_entity.entity_description == NETRO_CONTROLLER_BUTTON_DESCRIPTION

        # Verify unique_id is constructed correctly
        expected_unique_id = f"{mock_controller_coordinator.serial_number}-{NETRO_CONTROLLER_BUTTON_DESCRIPTION.key}"
        assert button_entity._attr_unique_id == expected_unique_id

        # Verify device_info is set correctly
        assert (
            button_entity._attr_device_info == mock_controller_coordinator.device_info
        )

    @pytest.mark.asyncio
    async def test_button_entity_description_properties(self):
        """Test that NETRO_CONTROLLER_BUTTON_DESCRIPTION has correct properties."""
        assert NETRO_CONTROLLER_BUTTON_DESCRIPTION.key == "refresh"
        assert NETRO_CONTROLLER_BUTTON_DESCRIPTION.name == "Refresh"
        assert (
            NETRO_CONTROLLER_BUTTON_DESCRIPTION.entity_registry_enabled_default is True
        )
        assert NETRO_CONTROLLER_BUTTON_DESCRIPTION.translation_key == "refresh"
        assert NETRO_CONTROLLER_BUTTON_DESCRIPTION.icon == "mdi:refresh"


class TestNetroRefreshButton:
    """Test class for NetroRefreshButton entity."""

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "CTRL123"
        coordinator.device_info = {"name": "Test Controller"}
        coordinator.async_request_refresh = MagicMock()
        return coordinator

    @pytest.fixture
    def button_entity(self, mock_controller_coordinator):
        """Create a NetroRefreshButton instance for testing."""
        return NetroRefreshButton(
            mock_controller_coordinator, NETRO_CONTROLLER_BUTTON_DESCRIPTION
        )

    def test_netro_refresh_button_initialization(
        self, button_entity, mock_controller_coordinator
    ):
        """Test NetroRefreshButton initialization."""
        assert button_entity.coordinator == mock_controller_coordinator
        assert button_entity.entity_description == NETRO_CONTROLLER_BUTTON_DESCRIPTION
        assert button_entity._attr_unique_id == "CTRL123-refresh"
        assert (
            button_entity._attr_device_info == mock_controller_coordinator.device_info
        )
        assert button_entity._attr_has_entity_name is True

    @pytest.mark.asyncio
    async def test_async_press(self, button_entity, mock_controller_coordinator):
        """Test async_press method."""

        # Make async_request_refresh an async mock
        async def mock_refresh():
            return None

        mock_controller_coordinator.async_request_refresh = MagicMock(
            side_effect=mock_refresh
        )

        with patch("custom_components.netro_watering.button._LOGGER") as mock_logger:
            # Call async_press
            await button_entity.async_press()

            # Verify logger was called with masked serial number
            mock_logger.debug.assert_called_once_with(
                "Netro: refresh button pressed for %s", "CT********23"
            )

            # Verify coordinator refresh was requested
            mock_controller_coordinator.async_request_refresh.assert_called_once()

    def test_press_method_calls_async_press(self, button_entity):
        """Test that press method calls async_press using asyncio.run."""
        with patch("asyncio.run") as mock_asyncio_run, patch.object(
            button_entity, "async_press"
        ) as mock_async_press:

            # Call the synchronous press method
            button_entity.press()

            # Verify asyncio.run was called once
            mock_asyncio_run.assert_called_once()

            # Verify that async_press was called (it's the coroutine passed to asyncio.run)
            mock_async_press.assert_called_once()
