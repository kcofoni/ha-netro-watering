"""Tests for sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.netro_watering.const import (
    CONF_DEVICE_TYPE,
    CONTROLLER_DEVICE_TYPE,
    DOMAIN,
    NETRO_CONTROLLER_BATTERY_LEVEL,
    SENSOR_DEVICE_TYPE,
)
from custom_components.netro_watering.sensor import (
    NETRO_CONTROLLER_BATTERY_DESCRIPTION,
    NETRO_CONTROLLER_DESCRIPTIONS,
    NETRO_CONTROLLER_DESCRIPTIONS_KEYS,
    NETRO_SENSOR_DESCRIPTIONS,
    NETRO_SENSOR_DESCRIPTIONS_KEYS,
    NETRO_ZONE_DESCRIPTIONS,
    NETRO_ZONE_DESCRIPTIONS_KEYS,
    NetroController,
    NetroSensor,
    NetroSensorEntityDescription,
    NetroZone,
    async_setup_entry,
)


class TestSensorAsyncSetupEntry:
    """Test class for sensor async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture
    def mock_sensor_coordinator(self):
        """Create a mock NetroSensorUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.device_name = "Test Sensor"
        coordinator.serial_number = "SENSOR123"
        coordinator.device_info = {"name": "Test Sensor", "model": "Netro Sensor"}
        coordinator.id = "measurement_123"
        coordinator.time = None
        coordinator.update_interval = None
        coordinator.metadata = None
        return coordinator

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator."""
        # Mock zone
        mock_zone = MagicMock()
        mock_zone.serial_number = "ZONE123"
        mock_zone.device_info = {"name": "Test Zone", "model": "Netro Zone"}

        coordinator = MagicMock()
        coordinator.device_name = "Test Controller"
        coordinator.serial_number = "CTRL123"
        coordinator.device_info = {"name": "Test Controller", "model": "Netro Sprite"}
        coordinator.active_zones = {0: mock_zone, 1: mock_zone}
        coordinator.current_slowdown_factor = 1
        coordinator.update_interval = None
        coordinator.metadata = None
        return coordinator

    @pytest.fixture
    def mock_controller_coordinator_with_battery(self, mock_controller_coordinator):
        """Create a controller coordinator with battery attribute."""
        # Add battery level attribute
        setattr(mock_controller_coordinator, NETRO_CONTROLLER_BATTERY_LEVEL, 85)
        return mock_controller_coordinator

    @pytest.fixture
    def mock_config_entry_sensor(self):
        """Create a mock ConfigEntry for sensor."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_config_entry_controller(self):
        """Create a mock ConfigEntry for controller."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE}
        return entry

    @pytest.fixture
    def mock_async_add_entities(self):
        """Create a mock AddEntitiesCallback."""
        return MagicMock(spec=AddEntitiesCallback)

    @pytest.mark.asyncio
    async def test_async_setup_entry_sensor_device(
        self,
        mock_hass,
        mock_config_entry_sensor,
        mock_sensor_coordinator,
        mock_async_add_entities,
    ):
        """Test async_setup_entry for sensor device type."""
        # Setup hass.data with the coordinator
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_sensor_coordinator

        # Call the function
        await async_setup_entry(
            mock_hass,
            mock_config_entry_sensor,
            mock_async_add_entities,
        )

        # Verify async_add_entities was called once
        mock_async_add_entities.assert_called_once()

        # Get the entities that were passed to async_add_entities
        call_args = mock_async_add_entities.call_args[0][0]

        # Should create 5 NetroSensor entities (from NETRO_SENSOR_DESCRIPTIONS)
        assert len(call_args) == 5

        # Verify all entities are NetroSensor instances
        for entity in call_args:
            assert isinstance(entity, NetroSensor)
            assert entity.coordinator == mock_sensor_coordinator

        # Verify entity descriptions
        entity_keys = [entity.entity_description.key for entity in call_args]
        expected_keys = [
            "temperature",
            "humidity",
            "illuminance",
            "battery_percent",
            "token_remaining",
        ]
        assert entity_keys == expected_keys

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_device_without_battery(
        self,
        mock_hass,
        mock_config_entry_controller,
        mock_controller_coordinator,
        mock_async_add_entities,
    ):
        """Test async_setup_entry for controller device without battery."""
        # Setup hass.data with the coordinator (without battery attribute)
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_controller_coordinator

        # Mock hasattr to return False for battery level
        with patch("builtins.hasattr") as mock_hasattr:

            def hasattr_side_effect(obj, name):
                if name == NETRO_CONTROLLER_BATTERY_LEVEL:
                    return False
                return hasattr(type(obj), name)

            mock_hasattr.side_effect = hasattr_side_effect

            # Call the function
            await async_setup_entry(
                mock_hass,
                mock_config_entry_controller,
                mock_async_add_entities,
            )

        # Verify async_add_entities was called 3 times:
        # 1. Controller intrinsic sensors (2 entities)
        # 2. Zone 0 sensors (9 entities)
        # 3. Zone 1 sensors (9 entities)
        assert mock_async_add_entities.call_count == 3

        # First call: controller intrinsic sensors
        first_call_entities = mock_async_add_entities.call_args_list[0][0][0]
        assert len(first_call_entities) == 2
        for entity in first_call_entities:
            assert isinstance(entity, NetroController)

        # Second and third calls: zone sensors
        for call_index in [1, 2]:
            zone_entities = mock_async_add_entities.call_args_list[call_index][0][0]
            assert len(zone_entities) == 9  # All NETRO_ZONE_DESCRIPTIONS
            for entity in zone_entities:
                assert isinstance(entity, NetroZone)

    @pytest.mark.asyncio
    async def test_async_setup_entry_controller_device_with_battery(
        self,
        mock_hass,
        mock_config_entry_controller,
        mock_controller_coordinator_with_battery,
        mock_async_add_entities,
    ):
        """Test async_setup_entry for controller device with battery."""
        # Setup hass.data with the coordinator (with battery attribute)
        mock_hass.data[DOMAIN][
            "test_entry_id"
        ] = mock_controller_coordinator_with_battery

        # Call the function
        await async_setup_entry(
            mock_hass,
            mock_config_entry_controller,
            mock_async_add_entities,
        )

        # Verify async_add_entities was called 4 times:
        # 1. Controller intrinsic sensors (2 entities)
        # 2. Battery sensor (1 entity)
        # 3. Zone 0 sensors (9 entities)
        # 4. Zone 1 sensors (9 entities)
        assert mock_async_add_entities.call_count == 4

        # Second call should be the battery sensor
        battery_call_entities = mock_async_add_entities.call_args_list[1][0][0]
        assert len(battery_call_entities) == 1
        battery_entity = battery_call_entities[0]
        assert isinstance(battery_entity, NetroController)
        assert battery_entity.entity_description == NETRO_CONTROLLER_BATTERY_DESCRIPTION

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_coordinator(
        self,
        mock_hass,
        mock_config_entry_sensor,
        mock_async_add_entities,
    ):
        """Test async_setup_entry when coordinator is missing from hass.data."""
        # Don't add coordinator to hass.data

        with pytest.raises(KeyError):
            await async_setup_entry(
                mock_hass,
                mock_config_entry_sensor,
                mock_async_add_entities,
            )

    @pytest.mark.asyncio
    async def test_async_setup_entry_unknown_device_type(
        self,
        mock_hass,
        mock_async_add_entities,
    ):
        """Test async_setup_entry with unknown device type."""
        # Create config entry with unknown device type
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {CONF_DEVICE_TYPE: "unknown_type"}

        # Call the function
        await async_setup_entry(
            mock_hass,
            entry,
            mock_async_add_entities,
        )

        # Should not call async_add_entities for unknown device type
        mock_async_add_entities.assert_not_called()


class TestSensorEntityDescriptions:
    """Test class for sensor entity descriptions."""

    def test_netro_sensor_descriptions_count(self):
        """Test that NETRO_SENSOR_DESCRIPTIONS has expected count."""
        assert len(NETRO_SENSOR_DESCRIPTIONS) == 5

    def test_netro_sensor_descriptions_keys(self):
        """Test NETRO_SENSOR_DESCRIPTIONS_KEYS matches descriptions."""
        expected_keys = [
            "temperature",
            "humidity",
            "illuminance",
            "battery_percent",
            "token_remaining",
        ]
        assert NETRO_SENSOR_DESCRIPTIONS_KEYS == expected_keys

    def test_netro_controller_descriptions_count(self):
        """Test that NETRO_CONTROLLER_DESCRIPTIONS has expected count."""
        assert len(NETRO_CONTROLLER_DESCRIPTIONS) == 2

    def test_netro_controller_descriptions_keys(self):
        """Test NETRO_CONTROLLER_DESCRIPTIONS_KEYS matches descriptions."""
        expected_keys = ["status", "token_remaining"]
        assert NETRO_CONTROLLER_DESCRIPTIONS_KEYS == expected_keys

    def test_netro_zone_descriptions_count(self):
        """Test that NETRO_ZONE_DESCRIPTIONS has expected count."""
        assert len(NETRO_ZONE_DESCRIPTIONS) == 9

    def test_netro_zone_descriptions_keys(self):
        """Test NETRO_ZONE_DESCRIPTIONS_KEYS matches descriptions."""
        expected_keys = [
            "last_watering_status",
            "last_watering_start_datetime",
            "last_watering_end_datetime",
            "last_watering_source",
            "next_watering_status",
            "next_watering_start_datetime",
            "next_watering_end_datetime",
            "next_watering_source",
            "humidity",
        ]
        assert NETRO_ZONE_DESCRIPTIONS_KEYS == expected_keys

    def test_netro_controller_battery_description_properties(self):
        """Test NETRO_CONTROLLER_BATTERY_DESCRIPTION properties."""
        desc = NETRO_CONTROLLER_BATTERY_DESCRIPTION
        assert desc.key == "battery_percent"
        assert desc.name == "Battery Percent"
        assert desc.device_class == SensorDeviceClass.BATTERY
        assert desc.translation_key == "battery_percent"

    def test_netro_sensor_entity_description_inheritance(self):
        """Test NetroSensorEntityDescription has correct attributes."""
        # Create a test description
        desc = NetroSensorEntityDescription(
            key="test", name="Test", netro_name="test_netro_name"
        )

        # Verify it has all required attributes
        assert hasattr(desc, "key")
        assert hasattr(desc, "name")
        assert hasattr(desc, "netro_name")
        assert hasattr(desc, "device_class")
        assert hasattr(desc, "entity_category")
        assert hasattr(desc, "entity_registry_enabled_default")
        assert hasattr(desc, "icon")
        assert hasattr(desc, "native_unit_of_measurement")
        assert hasattr(desc, "options")
        assert hasattr(desc, "state_class")
        assert hasattr(desc, "translation_key")


class TestNetroSensor:
    """Test class for NetroSensor entity."""

    @pytest.fixture
    def mock_sensor_coordinator(self):
        """Create a mock NetroSensorUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "SENSOR123"
        coordinator.device_info = {"name": "Test Sensor"}
        coordinator.id = "measurement_123"
        coordinator.time = None
        coordinator.update_interval = None
        coordinator.metadata = None
        # Add sensor attributes
        coordinator.NETRO_SENSOR_TEMPERATURE = 22.5
        return coordinator

    @pytest.fixture
    def sensor_description(self):
        """Create a test sensor description."""
        return NetroSensorEntityDescription(
            key="temperature", name="Temperature", netro_name="NETRO_SENSOR_TEMPERATURE"
        )

    @pytest.fixture
    def sensor_entity(self, mock_sensor_coordinator, sensor_description):
        """Create a NetroSensor instance for testing."""
        return NetroSensor(mock_sensor_coordinator, sensor_description)

    def test_netro_sensor_initialization(
        self, sensor_entity, mock_sensor_coordinator, sensor_description
    ):
        """Test NetroSensor initialization."""
        assert sensor_entity.coordinator == mock_sensor_coordinator
        assert sensor_entity.entity_description == sensor_description
        assert sensor_entity._attr_unique_id == "SENSOR123-temperature"
        assert sensor_entity._attr_device_info == mock_sensor_coordinator.device_info
        assert sensor_entity._attr_has_entity_name is True

    def test_native_value(self, sensor_entity, mock_sensor_coordinator):
        """Test native_value property."""
        result = sensor_entity.native_value
        assert result == 22.5

    def test_extra_state_attributes_minimal(
        self, sensor_entity, mock_sensor_coordinator
    ):
        """Test extra_state_attributes with minimal data."""
        attributes = sensor_entity.extra_state_attributes

        # Verify basic attributes
        assert attributes["last measurement id"] == "measurement_123"
        assert attributes["last measurement time"] is None
        assert attributes["update interval"] is None
        assert attributes["request time (UTC)"] is None
        assert attributes["last active date"] is None
        assert attributes["transaction id"] is None
        assert attributes["token limit"] is None
        assert attributes["token remaining"] is None
        assert attributes["token reset"] is None


class TestNetroController:
    """Test class for NetroController entity."""

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "CTRL123"
        coordinator.device_info = {"name": "Test Controller"}
        coordinator.current_slowdown_factor = 1
        coordinator.update_interval = None
        coordinator.metadata = None
        coordinator.NETRO_CONTROLLER_STATUS = "online"
        return coordinator

    @pytest.fixture
    def controller_description(self):
        """Create a test controller description."""
        return NetroSensorEntityDescription(
            key="status",
            name="Status",
            device_class=SensorDeviceClass.ENUM,
            netro_name="NETRO_CONTROLLER_STATUS",
        )

    @pytest.fixture
    def controller_entity(self, mock_controller_coordinator, controller_description):
        """Create a NetroController instance for testing."""
        return NetroController(mock_controller_coordinator, controller_description)

    def test_netro_controller_initialization(
        self, controller_entity, mock_controller_coordinator, controller_description
    ):
        """Test NetroController initialization."""
        assert controller_entity.coordinator == mock_controller_coordinator
        assert controller_entity.entity_description == controller_description
        assert controller_entity._attr_unique_id == "CTRL123-status"
        assert (
            controller_entity._attr_device_info
            == mock_controller_coordinator.device_info
        )
        assert controller_entity._attr_has_entity_name is True

    def test_native_value_enum(self, controller_entity, mock_controller_coordinator):
        """Test native_value property for ENUM device class."""
        result = controller_entity.native_value
        # Should convert to lowercase for ENUM
        assert result == "online"

    def test_native_value_non_enum(self, mock_controller_coordinator):
        """Test native_value property for non-ENUM device class."""
        description = NetroSensorEntityDescription(
            key="token_remaining",
            name="Token Remaining",
            netro_name="NETRO_METADATA_TOKEN_REMAINING",
        )
        mock_controller_coordinator.NETRO_METADATA_TOKEN_REMAINING = 42

        entity = NetroController(mock_controller_coordinator, description)
        result = entity.native_value
        assert result == 42

    def test_extra_state_attributes_no_slowdown(
        self, controller_entity, mock_controller_coordinator
    ):
        """Test extra_state_attributes without slowdown factor."""
        attributes = controller_entity.extra_state_attributes

        # Should not have slowdown factor when it's 1
        assert "slowdown factor" not in attributes
        assert attributes["update interval"] is None


class TestNetroZone:
    """Test class for NetroZone entity."""

    @pytest.fixture
    def mock_controller_coordinator(self):
        """Create a mock NetroControllerUpdateCoordinator with zones."""
        mock_zone = MagicMock()
        mock_zone.serial_number = "ZONE123"
        mock_zone.device_info = {"name": "Test Zone"}
        mock_zone.NETRO_ZONE_LAST_WATERING_STATUS = "executed"

        coordinator = MagicMock()
        coordinator.serial_number = "CTRL123"
        coordinator.active_zones = {0: mock_zone}
        coordinator.current_slowdown_factor = 2
        coordinator.update_interval = None
        coordinator.metadata = None
        return coordinator

    @pytest.fixture
    def zone_description(self):
        """Create a test zone description."""
        return NetroSensorEntityDescription(
            key="last_watering_status",
            name="Last Watering Status",
            device_class=SensorDeviceClass.ENUM,
            netro_name="NETRO_ZONE_LAST_WATERING_STATUS",
        )

    @pytest.fixture
    def zone_entity(self, mock_controller_coordinator, zone_description):
        """Create a NetroZone instance for testing."""
        return NetroZone(mock_controller_coordinator, zone_description, 0)

    def test_netro_zone_initialization(
        self, zone_entity, mock_controller_coordinator, zone_description
    ):
        """Test NetroZone initialization."""
        assert zone_entity.coordinator == mock_controller_coordinator
        assert zone_entity.entity_description == zone_description
        assert zone_entity.zone_id == 0
        assert zone_entity._attr_unique_id == "ZONE123-last_watering_status"
        assert (
            zone_entity._attr_device_info
            == mock_controller_coordinator.active_zones[0].device_info
        )
        assert zone_entity._attr_has_entity_name is True

    def test_native_value_enum(self, zone_entity, mock_controller_coordinator):
        """Test native_value property for ENUM device class."""
        result = zone_entity.native_value
        # Should convert to lowercase for ENUM
        assert result == "executed"

    def test_extra_state_attributes_with_slowdown(
        self, zone_entity, mock_controller_coordinator
    ):
        """Test extra_state_attributes with slowdown factor."""
        attributes = zone_entity.extra_state_attributes

        # Should have slowdown factor when it's > 1
        assert attributes["slowdown factor"] == 2
        assert attributes["zone id"] == 0
        assert attributes["update interval"] is None
