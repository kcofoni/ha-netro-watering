"""Tests for switch module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.netro_watering.const import (
    CONF_DEFAULT_WATERING_DELAY,
    CONF_DELAY_BEFORE_REFRESH,
    CONF_DEVICE_TYPE,
    CONF_DURATION,
    CONTROLLER_DEVICE_TYPE,
    DEFAULT_WATERING_DELAY,
    DEFAULT_WATERING_DURATION,
    DELAY_BEFORE_REFRESH,
    DOMAIN,
    GLOBAL_PARAMETERS,
    SENSOR_DEVICE_TYPE,
)
from custom_components.netro_watering.switch import (
    NETRO_ENABLED_SWITCH_DESCRIPTION,
    NETRO_WATERING_SWITCH_DESCRIPTION,
    ControllerEnablingSwitch,
    ControllerWateringSwitch,
    NetroRequiredKeysMixin,
    NetroSwitchEntityDescription,
    ZoneWateringSwitch,
    async_setup_entry,
)


class TestSwitchAsyncSetupEntry:
    """Test class for async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture
    def mock_controller_entry(self):
        """Create a mock ConfigEntry for controller device."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_controller_entry"
        entry.data = {CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_sensor_entry(self):
        """Create a mock ConfigEntry for sensor device."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_sensor_entry"
        entry.data = {CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "test_serial"
        coordinator.device_name = "Test Controller"
        coordinator.device_info = {"identifiers": {("netro", "test_serial")}}
        coordinator.active_zones = {
            "zone1": MagicMock(device_info={"identifiers": {("netro", "zone1")}}),
            "zone2": MagicMock(device_info={"identifiers": {("netro", "zone2")}}),
        }
        return coordinator

    @pytest.fixture
    def mock_add_entities(self):
        """Create a mock AddEntitiesCallback."""
        return MagicMock(spec=AddEntitiesCallback)

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_controller_device_default_values(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test async_setup_entry with controller device using default values."""
        # Setup
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_hass.data[DOMAIN][mock_controller_entry.entry_id] = mock_coordinator

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify
        # Should be called 4 times: 1 for controller enable/disable + 2 for zones + 1 for controller watering
        assert mock_add_entities.call_count == 4

        # Verify the types of entities created
        call_args_list = mock_add_entities.call_args_list

        # First call: ControllerEnablingSwitch
        controller_enabling_entities = call_args_list[0][0][0]
        assert len(controller_enabling_entities) == 1
        assert isinstance(controller_enabling_entities[0], ControllerEnablingSwitch)

        # Second and third calls: ZoneWateringSwitch (for each zone)
        zone_entities_1 = call_args_list[1][0][0]
        zone_entities_2 = call_args_list[2][0][0]
        assert len(zone_entities_1) == 1
        assert len(zone_entities_2) == 1
        assert isinstance(zone_entities_1[0], ZoneWateringSwitch)
        assert isinstance(zone_entities_2[0], ZoneWateringSwitch)

        # Fourth call: ControllerWateringSwitch
        controller_watering_entities = call_args_list[3][0][0]
        assert len(controller_watering_entities) == 1
        assert isinstance(controller_watering_entities[0], ControllerWateringSwitch)

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_controller_device_custom_values(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test async_setup_entry with controller device using custom configuration values."""
        # Setup with custom options
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_controller_entry.options = {
            CONF_DURATION: 30,
            CONF_DEFAULT_WATERING_DELAY: 5,
            CONF_DELAY_BEFORE_REFRESH: 10,
        }
        mock_hass.data[DOMAIN][mock_controller_entry.entry_id] = mock_coordinator

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify entities were created with custom values
        assert mock_add_entities.call_count == 4

        # Check that ZoneWateringSwitch entities were created with custom values
        zone_entity_1 = mock_add_entities.call_args_list[1][0][0][0]
        zone_entity_2 = mock_add_entities.call_args_list[2][0][0][0]

        assert zone_entity_1._duration_minutes == 30
        assert zone_entity_1._delay_minutes == 5
        assert zone_entity_1._before_refresh_seconds == 10

        assert zone_entity_2._duration_minutes == 30
        assert zone_entity_2._delay_minutes == 5
        assert zone_entity_2._before_refresh_seconds == 10

        # Check ControllerWateringSwitch entity
        controller_entity = mock_add_entities.call_args_list[3][0][0][0]
        assert controller_entity._duration_minutes == 30
        assert controller_entity._delay_minutes == 5
        assert controller_entity._before_refresh_seconds == 10

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_controller_device_global_parameters(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test async_setup_entry with controller device using global parameters."""
        # Setup with global parameters
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_hass.data[DOMAIN] = {
            mock_controller_entry.entry_id: mock_coordinator,
            GLOBAL_PARAMETERS: {
                CONF_DEFAULT_WATERING_DELAY: 15,
                CONF_DELAY_BEFORE_REFRESH: 20,
            },
        }

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify entities were created with global parameter values
        assert mock_add_entities.call_count == 4

        # Check that entities use global parameter values
        zone_entity = mock_add_entities.call_args_list[1][0][0][0]
        assert zone_entity._delay_minutes == 15
        assert zone_entity._before_refresh_seconds == 20

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_controller_device_invalid_values(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test async_setup_entry with controller device using invalid configuration values."""
        # Setup with invalid options
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_controller_entry.options = {
            CONF_DURATION: "invalid",
            CONF_DEFAULT_WATERING_DELAY: -5,
            CONF_DELAY_BEFORE_REFRESH: "not_a_number",
        }
        mock_hass.data[DOMAIN][mock_controller_entry.entry_id] = mock_coordinator

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify entities were created with default values due to invalid config
        assert mock_add_entities.call_count == 4

        # Check that entities use default values when invalid values are provided
        zone_entity = mock_add_entities.call_args_list[1][0][0][0]
        assert zone_entity._duration_minutes == DEFAULT_WATERING_DURATION
        assert zone_entity._delay_minutes == DEFAULT_WATERING_DELAY
        assert zone_entity._before_refresh_seconds == DELAY_BEFORE_REFRESH

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_controller_device_out_of_range_duration(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test async_setup_entry with controller device using out-of-range duration."""
        # Setup with out-of-range duration
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_controller_entry.options = {
            CONF_DURATION: 200,  # Above MAX_WATERING_DURATION
        }
        mock_hass.data[DOMAIN][mock_controller_entry.entry_id] = mock_coordinator

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify entities were created with default duration due to out-of-range value
        assert mock_add_entities.call_count == 4

        zone_entity = mock_add_entities.call_args_list[1][0][0][0]
        assert zone_entity._duration_minutes == DEFAULT_WATERING_DURATION

    async def test_async_setup_entry_sensor_device(
        self, mock_hass, mock_sensor_entry, mock_add_entities
    ):
        """Test async_setup_entry with sensor device (should not create any entities)."""
        # Execute
        await async_setup_entry(mock_hass, mock_sensor_entry, mock_add_entities)

        # Verify no entities were created for sensor device
        mock_add_entities.assert_not_called()

    @patch(
        "custom_components.netro_watering.switch.entity_platform.async_get_current_platform"
    )
    async def test_async_setup_entry_services_registration(
        self,
        mock_get_platform,
        mock_hass,
        mock_controller_entry,
        mock_coordinator,
        mock_add_entities,
    ):
        """Test that custom services are properly registered."""
        # Setup
        mock_platform = MagicMock()
        mock_get_platform.return_value = mock_platform
        mock_hass.data[DOMAIN][mock_controller_entry.entry_id] = mock_coordinator

        # Execute
        await async_setup_entry(mock_hass, mock_controller_entry, mock_add_entities)

        # Verify services were registered
        assert mock_platform.async_register_entity_service.call_count == 4

        # Verify service names
        service_calls = mock_platform.async_register_entity_service.call_args_list
        service_names = [call[0][0] for call in service_calls]
        assert "start_watering" in service_names
        assert "stop_watering" in service_names
        assert "enable" in service_names
        assert "disable" in service_names


class TestSwitchEntityDescriptions:
    """Test class for switch entity descriptions."""

    def test_netro_required_keys_mixin(self):
        """Test NetroRequiredKeysMixin dataclass."""
        mixin = NetroRequiredKeysMixin(
            netro_on_name="test_on", netro_off_name="test_off"
        )
        assert mixin.netro_on_name == "test_on"
        assert mixin.netro_off_name == "test_off"

    def test_netro_switch_entity_description_inheritance(self):
        """Test NetroSwitchEntityDescription inherits from both parent classes."""
        assert issubclass(NetroSwitchEntityDescription, NetroRequiredKeysMixin)
        from homeassistant.components.switch import SwitchEntityDescription

        assert issubclass(NetroSwitchEntityDescription, SwitchEntityDescription)

    def test_netro_watering_switch_description_properties(self):
        """Test NETRO_WATERING_SWITCH_DESCRIPTION has correct properties."""
        desc = NETRO_WATERING_SWITCH_DESCRIPTION
        assert desc.key == "watering"
        assert desc.name == "Watering"
        assert desc.device_class == SwitchDeviceClass.SWITCH
        assert desc.translation_key == "watering"
        assert desc.netro_on_name == "start_watering"
        assert desc.netro_off_name == "stop_watering"
        assert desc.icon == "mdi:sprinkler"

    def test_netro_enabled_switch_description_properties(self):
        """Test NETRO_ENABLED_SWITCH_DESCRIPTION has correct properties."""
        desc = NETRO_ENABLED_SWITCH_DESCRIPTION
        assert desc.key == "enabled"
        assert desc.name == "Enabled"
        assert desc.device_class == SwitchDeviceClass.SWITCH
        assert desc.translation_key == "enabled"


class TestControllerEnablingSwitch:
    """Test class for ControllerEnablingSwitch."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "test_serial"
        coordinator.device_info = {"identifiers": {("netro", "test_serial")}}
        coordinator.enabled = True
        coordinator.enable = AsyncMock()
        coordinator.disable = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    def test_controller_enabling_switch_initialization(self, mock_coordinator):
        """Test ControllerEnablingSwitch initialization."""
        switch = ControllerEnablingSwitch(
            mock_coordinator, NETRO_ENABLED_SWITCH_DESCRIPTION
        )

        assert switch.coordinator == mock_coordinator
        assert switch.entity_description == NETRO_ENABLED_SWITCH_DESCRIPTION
        assert switch._attr_unique_id == "test_serial-enabled"
        assert switch._attr_device_info == mock_coordinator.device_info
        assert switch._attr_has_entity_name is True
        assert switch._attr_assumed_state is False

    def test_is_on_property(self, mock_coordinator):
        """Test is_on property returns coordinator.enabled."""
        switch = ControllerEnablingSwitch(
            mock_coordinator, NETRO_ENABLED_SWITCH_DESCRIPTION
        )

        mock_coordinator.enabled = True
        assert switch.is_on is True

        mock_coordinator.enabled = False
        assert switch.is_on is False

    async def test_async_turn_on(self, mock_coordinator):
        """Test async_turn_on calls coordinator.enable and refresh."""
        switch = ControllerEnablingSwitch(
            mock_coordinator, NETRO_ENABLED_SWITCH_DESCRIPTION
        )

        await switch.async_turn_on()

        mock_coordinator.enable.assert_called_once()
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_async_turn_off(self, mock_coordinator):
        """Test async_turn_off calls coordinator.disable and refresh."""
        switch = ControllerEnablingSwitch(
            mock_coordinator, NETRO_ENABLED_SWITCH_DESCRIPTION
        )

        await switch.async_turn_off()

        mock_coordinator.disable.assert_called_once()
        mock_coordinator.async_request_refresh.assert_called_once()


class TestZoneWateringSwitch:
    """Test class for ZoneWateringSwitch."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "test_serial"
        coordinator.async_request_refresh = AsyncMock()
        mock_zone = MagicMock()
        mock_zone.device_info = {"identifiers": {("netro", "zone1")}}
        mock_zone.name = "Test Zone"
        mock_zone.watering = False
        mock_zone.start_watering = AsyncMock()
        mock_zone.stop_watering = AsyncMock()
        coordinator.active_zones = {"zone1": mock_zone}
        return coordinator

    def test_zone_watering_switch_initialization(self, mock_coordinator):
        """Test ZoneWateringSwitch initialization."""
        switch = ZoneWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, "zone1", 30, 5, 10
        )

        assert switch.coordinator == mock_coordinator
        assert switch.entity_description == NETRO_WATERING_SWITCH_DESCRIPTION
        assert switch._zone_id == "zone1"
        assert switch._duration_minutes == 30
        assert switch._delay_minutes == 5
        assert switch._before_refresh_seconds == 10
        assert switch._attr_unique_id == "test_serial-zone1-watering"
        assert switch._attr_has_entity_name is True
        assert switch._attr_assumed_state is True

    def test_extra_state_attributes(self, mock_coordinator):
        """Test extra_state_attributes returns zone information."""
        switch = ZoneWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, "zone1", 30, 5, 10
        )

        attrs = switch.extra_state_attributes
        assert attrs == {"zone": "zone1"}

    def test_is_on_property(self, mock_coordinator):
        """Test is_on property returns zone watering status."""
        switch = ZoneWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, "zone1", 30, 5, 10
        )

        mock_coordinator.active_zones["zone1"].watering = True
        assert switch.is_on is True

        mock_coordinator.active_zones["zone1"].watering = False
        assert switch.is_on is False

    @patch("asyncio.sleep")
    async def test_async_turn_on_immediate(self, mock_sleep, mock_coordinator):
        """Test async_turn_on with immediate start (no delay, no start_time)."""
        switch = ZoneWateringSwitch(
            mock_coordinator,
            NETRO_WATERING_SWITCH_DESCRIPTION,
            "zone1",
            30,
            0,  # No delay
            10,
        )

        await switch.async_turn_on()

        # Verify the start_watering method was called
        zone_mock = mock_coordinator.active_zones["zone1"]
        zone_mock.start_watering.assert_called_once_with(30, 0, None)

        # Verify sleep and refresh
        mock_sleep.assert_called_once_with(10)
        mock_coordinator.async_request_refresh.assert_called_once()

    @patch("asyncio.sleep")
    async def test_async_turn_off(self, mock_sleep, mock_coordinator):
        """Test async_turn_off calls stop_watering."""
        switch = ZoneWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, "zone1", 30, 5, 10
        )

        await switch.async_turn_off()

        # Verify the stop_watering method was called
        zone_mock = mock_coordinator.active_zones["zone1"]
        zone_mock.stop_watering.assert_called_once()

        # Verify sleep and refresh
        mock_sleep.assert_called_once_with(10)
        mock_coordinator.async_request_refresh.assert_called_once()


class TestControllerWateringSwitch:
    """Test class for ControllerWateringSwitch."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.serial_number = "test_serial"
        coordinator.device_info = {"identifiers": {("netro", "test_serial")}}
        coordinator.watering = False
        coordinator.start_watering = AsyncMock()
        coordinator.stop_watering = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    def test_controller_watering_switch_initialization(self, mock_coordinator):
        """Test ControllerWateringSwitch initialization."""
        switch = ControllerWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, 30, 5, 10
        )

        assert switch.coordinator == mock_coordinator
        assert switch.entity_description == NETRO_WATERING_SWITCH_DESCRIPTION
        assert switch._duration_minutes == 30
        assert switch._delay_minutes == 5
        assert switch._before_refresh_seconds == 10
        assert switch._attr_unique_id == "test_serial-watering"
        assert switch._attr_device_info == mock_coordinator.device_info

    def test_is_on_property(self, mock_coordinator):
        """Test is_on property returns coordinator watering status."""
        switch = ControllerWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, 30, 5, 10
        )

        mock_coordinator.watering = True
        assert switch.is_on is True

        mock_coordinator.watering = False
        assert switch.is_on is False

    @patch("asyncio.sleep")
    async def test_async_turn_on(self, mock_sleep, mock_coordinator):
        """Test async_turn_on calls coordinator start_watering."""
        switch = ControllerWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, 30, 5, 10
        )

        await switch.async_turn_on()

        mock_coordinator.start_watering.assert_called_once_with(30, 5, None)
        mock_sleep.assert_called_once_with(10)
        mock_coordinator.async_request_refresh.assert_called_once()

    @patch("asyncio.sleep")
    async def test_async_turn_off(self, mock_sleep, mock_coordinator):
        """Test async_turn_off calls coordinator stop_watering."""
        switch = ControllerWateringSwitch(
            mock_coordinator, NETRO_WATERING_SWITCH_DESCRIPTION, 30, 5, 10
        )

        await switch.async_turn_off()

        mock_coordinator.stop_watering.assert_called_once()
        mock_sleep.assert_called_once_with(10)
        mock_coordinator.async_request_refresh.assert_called_once()
