"""Tests for diagnostics module."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.netro_watering.const import CONF_SERIAL_NUMBER, DOMAIN
from custom_components.netro_watering.diagnostics import (
    TO_REDACT,
    _mask_token,
    _safe,
    _scrub_strings,
    async_get_config_entry_diagnostics,
)


class TestDiagnosticsUtilityFunctions:
    """Test class for diagnostics utility functions."""

    def test_safe_with_dict(self):
        """Test _safe function with dict input."""
        test_dict = {"key1": "value1", "key2": 42}
        result = _safe(test_dict)
        assert result == test_dict

    def test_safe_with_list(self):
        """Test _safe function with list input."""
        test_list = ["item1", 2, True]
        result = _safe(test_list)
        assert result == test_list

    def test_safe_with_primitives(self):
        """Test _safe function with primitive types."""
        assert _safe("string") == "string"
        assert _safe(42) == 42
        assert _safe(3.14) == 3.14
        assert _safe(True) is True
        assert _safe(None) is None

    def test_safe_with_object_fallback(self):
        """Test _safe function with complex object that falls back to str."""

        class TestObject:  # pylint: disable=C0115
            def __str__(self):
                return "test_object_str"

        test_obj = TestObject()
        result = _safe(test_obj)
        assert result == "test_object_str"

    def test_safe_with_dict_like_object(self):
        """Test _safe function with object that can be converted to dict."""

        class DictLikeObject:  # pylint: disable=C0115
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        # This should fall back to str() since dict() conversion will fail
        test_obj = DictLikeObject()
        result = _safe(test_obj)
        # Should fall back to str representation
        assert isinstance(result, str)
        assert "DictLikeObject" in result

    def test_mask_token_empty_string(self):
        """Test _mask_token with empty string."""
        assert _mask_token("") == ""

    def test_mask_token_short_strings(self):
        """Test _mask_token with strings <= 2 characters."""
        assert _mask_token("a") == "★"
        assert _mask_token("ab") == "★★"

    def test_mask_token_normal_strings(self):
        """Test _mask_token with normal strings."""
        assert _mask_token("abc") == "★bc"
        assert _mask_token("test123") == "★★★★★23"
        assert _mask_token("serial12345") == "★★★★★★★★★45"

    def test_scrub_strings_simple_string(self):
        """Test _scrub_strings with simple string."""
        secrets = {"secret123"}
        result = _scrub_strings("This contains secret123 inside", secrets)
        assert result == "This contains ★★★★★★★23 inside"

    def test_scrub_strings_list(self):
        """Test _scrub_strings with list."""
        secrets = {"secret"}
        test_list = ["no secrets here", "this has secret in it", "normal"]
        result = _scrub_strings(test_list, secrets)
        assert result == ["no ★★★★ets here", "this has ★★★★et in it", "normal"]

    def test_scrub_strings_dict(self):
        """Test _scrub_strings with dict."""
        secrets = {"ABC123"}
        test_dict = {
            "key1": "value with ABC123",
            "key2": {"nested": "ABC123 appears here"},
            "key3": 42,
        }
        result = _scrub_strings(test_dict, secrets)
        assert result["key1"] == "value with ★★★★23"
        assert result["key2"]["nested"] == "★★★★23 appears here"
        assert result["key3"] == 42

    def test_scrub_strings_tuple(self):
        """Test _scrub_strings with tuple."""
        secrets = {"test"}
        test_tuple = ("no secrets", "test appears", "normal")
        result = _scrub_strings(test_tuple, secrets)
        assert result == ("no secrets", "★★st appears", "normal")

    def test_scrub_strings_empty_secrets(self):
        """Test _scrub_strings with empty secrets."""
        secrets = {"", "valid_secret"}
        result = _scrub_strings("This has valid_secret in it", secrets)
        assert result == "This has ★★★★★★★★★★et in it"

    def test_to_redact_contains_expected_keys(self):
        """Test that TO_REDACT contains expected sensitive keys."""
        expected_keys = {
            "token",
            "api_key",
            "authorization",
            "Authorization",
            "access_token",
            "refresh_token",
            "password",
            "serial",
            "serial_number",
        }
        assert expected_keys.issubset(TO_REDACT)


class TestDiagnosticsMainFunction:
    """Test class for async_get_config_entry_diagnostics function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        hass.states = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN
        entry.title = "Test Netro Device"
        entry.version = 1
        entry.source = "user"
        entry.unique_id = "test_unique_id"
        entry.pref_disable_new_entities = False
        entry.data = {CONF_SERIAL_NUMBER: "SERIAL123"}
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.__class__.__name__ = "NetroControllerUpdateCoordinator"
        coordinator.name = "Test Controller"
        coordinator.update_interval = "60 seconds"
        coordinator.last_update_success = True
        coordinator.last_update_time = "2023-10-01 12:00:00"
        coordinator.serial_number = "SERIAL123"
        coordinator.device_type = "controller"
        coordinator.device_name = "Test Device"
        coordinator.hw_version = "1.0"
        coordinator.sw_version = "2.0"
        coordinator.data = {"test": "data"}
        return coordinator

    @pytest.fixture
    def mock_device_registry(self):
        """Create a mock device registry."""
        device = MagicMock()
        device.id = "device_uuid_123"
        device.name = "Test Device"
        device.model = "Netro Sprite"
        device.manufacturer = "Netro"
        device.hw_version = "1.0"
        device.sw_version = "2.0"
        device.identifiers = {(DOMAIN, "SERIAL123")}
        device.connections = set()
        device.via_device_id = None
        device.area_id = None
        device.config_entries = {"test_entry_id"}

        registry = MagicMock()
        registry.devices = {"device_id": device}
        return registry

    @pytest.fixture
    def mock_entity_registry(self):
        """Create a mock entity registry."""
        entity = MagicMock()
        entity.entity_id = "sensor.test_device_moisture"
        entity.unique_id = "SERIAL123-moisture"
        entity.platform = DOMAIN
        entity.original_name = "Moisture"
        entity.original_device_class = "humidity"
        entity.device_id = "device_uuid_123"
        entity.disabled_by = None
        entity.capabilities = {}
        entity.config_entry_id = "test_entry_id"

        registry = MagicMock()
        registry.entities = {"entity_id": entity}
        return registry

    @pytest.fixture
    def mock_state(self):
        """Create a mock state."""
        state = MagicMock()
        state.state = "50"
        state.attributes = {"unit_of_measurement": "%", "device_class": "humidity"}
        return state

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_full(
        self,
        mock_hass,
        mock_config_entry,
        mock_coordinator,
        mock_device_registry,
        mock_entity_registry,
        mock_state,
    ):
        """Test async_get_config_entry_diagnostics with full data."""
        # Setup mocks
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_coordinator
        mock_hass.states.get.return_value = mock_state

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            # Mock async_redact_data to return input unchanged for simplicity
            mock_redact.side_effect = lambda data, keys: data

            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            # Verify structure
            assert "entry" in result
            assert "coordinator" in result
            assert "entities" in result
            assert "devices" in result

            # Verify entry data
            entry_data = result["entry"]
            assert entry_data["entry_id"] == "test_entry_id"
            assert entry_data["domain"] == DOMAIN
            assert entry_data["title"] == "Test Netro Device"

            # Verify coordinator data
            coord_data = result["coordinator"]
            assert "info" in coord_data
            assert "data" in coord_data
            assert coord_data["info"]["class"] == "NetroControllerUpdateCoordinator"
            assert coord_data["info"]["name"] == "Test Controller"

            # Verify entities
            assert len(result["entities"]) == 1
            entity = result["entities"][0]
            assert entity["entity_id"] == "sensor.test_device_moisture"
            assert entity["platform"] == DOMAIN

            # Verify devices
            assert len(result["devices"]) == 1
            device = result["devices"][0]
            assert device["name"] == "Test Device"
            assert device["model"] == "Netro Sprite"

            # Verify redaction was called
            mock_redact.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_no_coordinator(
        self,
        mock_hass,
        mock_config_entry,
        mock_device_registry,
        mock_entity_registry,
    ):
        """Test async_get_config_entry_diagnostics without coordinator."""
        # Don't add coordinator to hass.data

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            mock_redact.side_effect = lambda data, keys: data

            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            # Verify coordinator section is empty but present
            assert "coordinator" in result
            coord_data = result["coordinator"]
            assert coord_data["info"] == {}
            assert coord_data["data"] is None

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_serial_scrubbing(
        self,
        mock_hass,
        mock_config_entry,
        mock_coordinator,
        mock_device_registry,
        mock_entity_registry,
        mock_state,
    ):
        """Test that serial numbers are properly scrubbed from strings."""
        # Setup mocks with serial in various places
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_coordinator
        mock_hass.states.get.return_value = mock_state

        # Entity with serial in unique_id
        entity = MagicMock()
        entity.entity_id = "sensor.test_SERIAL123_moisture"
        entity.unique_id = "SERIAL123-moisture"
        entity.platform = DOMAIN
        entity.original_name = "Moisture"
        entity.original_device_class = "humidity"
        entity.device_id = "device_uuid_123"
        entity.disabled_by = None
        entity.capabilities = {}
        entity.config_entry_id = "test_entry_id"

        entity_registry = MagicMock()
        entity_registry.entities = {"entity_id": entity}

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            mock_redact.side_effect = lambda data, keys: data

            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            # Verify serial numbers are scrubbed (★★★★★★★★★23)
            entity_result = result["entities"][0]
            assert "★★★★★★★23" in entity_result["entity_id"]
            assert "★★★★★★★23" in entity_result["unique_id"]

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_exception_handling(
        self,
        mock_hass,
        mock_config_entry,
    ):
        """Test exception handling in diagnostics collection."""
        # Setup config entry with problematic data
        mock_config_entry.data = None  # This might cause exceptions

        mock_device_registry = MagicMock()
        mock_device_registry.devices = {}

        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = {}

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            mock_redact.side_effect = lambda data, keys: data

            # Should not raise exception despite problematic data
            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            assert "entry" in result
            assert "coordinator" in result
            assert "entities" in result
            assert "devices" in result

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_entity_no_state(
        self,
        mock_hass,
        mock_config_entry,
        mock_coordinator,
        mock_device_registry,
        mock_entity_registry,
    ):
        """Test diagnostics with entity that has no state."""
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_coordinator
        mock_hass.states.get.return_value = None  # No state available

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            mock_redact.side_effect = lambda data, keys: data

            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            # Verify entity data handles missing state
            entity = result["entities"][0]
            assert entity["state"] is None
            assert entity["attributes"] is None

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_filters_non_domain_entities(
        self,
        mock_hass,
        mock_config_entry,
        mock_coordinator,
        mock_device_registry,
    ):
        """Test that only entities from our domain are included."""
        mock_hass.data[DOMAIN]["test_entry_id"] = mock_coordinator

        # Create entity registry with entities from different domains
        netro_entity = MagicMock()
        netro_entity.config_entry_id = "test_entry_id"
        netro_entity.platform = DOMAIN
        netro_entity.entity_id = "sensor.netro_moisture"

        other_entity = MagicMock()
        other_entity.config_entry_id = "test_entry_id"
        other_entity.platform = "other_domain"
        other_entity.entity_id = "sensor.other_sensor"

        entity_registry = MagicMock()
        entity_registry.entities = {
            "netro_entity": netro_entity,
            "other_entity": other_entity,
        }

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ), patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=entity_registry,
        ), patch(
            "custom_components.netro_watering.diagnostics.async_redact_data"
        ) as mock_redact:

            mock_redact.side_effect = lambda data, keys: data
            mock_hass.states.get.return_value = None

            result = await async_get_config_entry_diagnostics(
                mock_hass, mock_config_entry
            )

            # Should only include the netro entity
            assert len(result["entities"]) == 1
            assert result["entities"][0]["platform"] == DOMAIN
