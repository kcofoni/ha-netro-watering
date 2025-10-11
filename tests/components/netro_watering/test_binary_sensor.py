"""Tests for binary_sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.netro_watering.binary_sensor import (
    NETRO_ZONE_WATERING_DESCRIPTION,
    NetroZone,
    async_setup_entry,
)
from custom_components.netro_watering.const import (
    CONF_DEVICE_TYPE,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    SENSOR_DEVICE_TYPE,
)


class TestBinarySensorAsyncSetupEntry:
    """Test class for binary_sensor async_setup_entry function."""

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
        coordinator.active_zones = {
            1: MagicMock(serial_number="CTRL123_1", device_info={"name": "Zone 1"}),
            2: MagicMock(serial_number="CTRL123_2", device_info={"name": "Zone 2"}),
            3: MagicMock(serial_number="CTRL123_3", device_info={"name": "Zone 3"}),
        }
        return coordinator

    @pytest.fixture
    def mock_controller_config_entry(self):
        """Create a mock ConfigEntry for a controller."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_controller_entry_id"
        entry.data = {CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_sensor_config_entry(self):
        """Create a mock ConfigEntry for a sensor."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_sensor_entry_id"
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_async_add_entities(self):
        """Create a mock AddEntitiesCallback."""
        return MagicMock(spec=AddEntitiesCallback)

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_with_zones(
        self,
        mock_hass,
        mock_controller_config_entry,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test async_setup_entry with a controller that has active zones."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][
            mock_controller_config_entry.entry_id
        ] = mock_controller_coordinator

        with patch(
            "custom_components.netro_watering.binary_sensor._LOGGER"
        ) as mock_logger:
            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_controller_config_entry,
                mock_async_add_entities,
            )

            # Verify logger calls
            mock_logger.info.assert_called_once_with(
                "Adding binary sensor entities for zones"
            )
            mock_logger.debug.assert_called_once_with(
                "creating binary sensor entities: controller = %s, active_zones = %s",
                "Test Controller",
                mock_controller_coordinator.active_zones,
            )

            # Verify async_add_entities was called
            mock_async_add_entities.assert_called_once()

            # Get the entities that were passed to async_add_entities
            call_args = mock_async_add_entities.call_args[0][0]

            # Should create 3 NetroZone entities (for zones 1, 2, 3)
            assert len(call_args) == 3

            # Verify all entities are NetroZone instances
            for entity in call_args:
                assert isinstance(entity, NetroZone)
                assert entity.entity_description == NETRO_ZONE_WATERING_DESCRIPTION

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_no_zones(
        self,
        mock_hass,
        mock_controller_config_entry,
        mock_async_add_entities,
    ):
        """Test async_setup_entry with a controller that has no active zones."""
        # Create coordinator with no active zones
        coordinator = MagicMock()
        coordinator.device_name = "Empty Controller"
        coordinator.active_zones = {}

        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][mock_controller_config_entry.entry_id] = coordinator

        with patch(
            "custom_components.netro_watering.binary_sensor._LOGGER"
        ) as mock_logger:
            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_controller_config_entry,
                mock_async_add_entities,
            )

            # Verify logger calls
            mock_logger.info.assert_called_once_with(
                "Adding binary sensor entities for zones"
            )
            mock_logger.debug.assert_called_once_with(
                "creating binary sensor entities: controller = %s, active_zones = %s",
                "Empty Controller",
                {},
            )

            # Verify async_add_entities was called with empty list
            mock_async_add_entities.assert_called_once()
            call_args = mock_async_add_entities.call_args[0][0]
            assert len(call_args) == 0

    @pytest.mark.asyncio
    async def test_async_setup_entry_sensor_device(
        self,
        mock_hass,
        mock_sensor_config_entry,
        mock_async_add_entities,
    ):
        """Test async_setup_entry with a sensor device (should do nothing)."""
        with patch(
            "custom_components.netro_watering.binary_sensor._LOGGER"
        ) as mock_logger:
            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_sensor_config_entry,
                mock_async_add_entities,
            )

            # For sensor devices, nothing should happen
            mock_logger.info.assert_not_called()
            mock_logger.debug.assert_not_called()
            mock_async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_coordinator(
        self,
        mock_hass,
        mock_controller_config_entry,
        mock_async_add_entities,
    ):
        """Test async_setup_entry when coordinator is missing from hass.data."""
        # Don't add coordinator to hass.data

        with pytest.raises(KeyError):
            await async_setup_entry(
                mock_hass,
                mock_controller_config_entry,
                mock_async_add_entities,
            )

    @pytest.mark.asyncio
    async def test_netro_zone_creation_parameters(
        self,
        mock_hass,
        mock_controller_config_entry,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test that NetroZone entities are created with correct parameters."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN][
            mock_controller_config_entry.entry_id
        ] = mock_controller_coordinator

        await async_setup_entry(
            mock_hass,
            mock_controller_config_entry,
            mock_async_add_entities,
        )

        # Get the created entities
        call_args = mock_async_add_entities.call_args[0][0]

        # Check that entities were created with correct zone keys
        zone_ids = [entity.zone_id for entity in call_args]
        assert sorted(zone_ids) == [1, 2, 3]

        # Verify each entity has the correct coordinator and description
        for entity in call_args:
            assert entity.coordinator == mock_controller_coordinator
            assert entity.entity_description == NETRO_ZONE_WATERING_DESCRIPTION
