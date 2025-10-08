"""Pytest fixtures for Netro Watering integration tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.common import MockConfigEntry

# Conditional import
try:
    # Home Assistant Core environment
    from homeassistant.components.netro_watering.config_flow import CannotConnect
    from homeassistant.components.netro_watering.const import (
        CONF_DEVICE_HW_VERSION,
        CONF_DEVICE_NAME,
        CONF_DEVICE_SW_VERSION,
        CONF_DEVICE_TYPE,
        CONF_SENS_REFRESH_INTERVAL,
        CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
        CONF_SERIAL_NUMBER,
        CONTROLLER_DEVICE_TYPE,
        DOMAIN,
        SENSOR_DEVICE_TYPE,
    )

    INTEGRATION_PATCH_PATH = "homeassistant.components.netro_watering"
except ImportError:
    # Standalone environment
    from custom_components.netro_watering.config_flow import CannotConnect
    from custom_components.netro_watering.const import (
        CONF_DEVICE_HW_VERSION,
        CONF_DEVICE_NAME,
        CONF_DEVICE_SW_VERSION,
        CONF_DEVICE_TYPE,
        CONF_SENS_REFRESH_INTERVAL,
        CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY,
        CONF_SERIAL_NUMBER,
        CONTROLLER_DEVICE_TYPE,
        DOMAIN,
        SENSOR_DEVICE_TYPE,
    )

    INTEGRATION_PATCH_PATH = "custom_components.netro_watering"

from pynetro.client import (
    NETRO_ERROR_CODE_EXCEED_LIMIT,
    NETRO_ERROR_CODE_INTERNAL_ERROR,
    NETRO_ERROR_CODE_INVALID_DEVICE,
    NETRO_ERROR_CODE_INVALID_KEY,
    NETRO_ERROR_CODE_PARAMETER_ERROR,
    NetroExceedLimit,
    NetroInternalError,
    NetroInvalidDevice,
    NetroInvalidKey,
    NetroParameterError,
)

CTRL_SERIAL = "CTRL999"
SENSOR_SERIAL = "SN123"


@pytest.fixture
def mock_setup_entry():
    """Prevent actual integration setup after CREATE_ENTRY."""
    with patch(f"{INTEGRATION_PATCH_PATH}.async_setup_entry", return_value=True) as m:
        yield m


@pytest.fixture
def mock_get_info_device_ok():
    """OK response for device (controller) priority."""
    payload = {
        "status": "OK",
        "meta": {"time": "2025-09-25T11:23:20"},
        "data": {
            "device": {
                "name": "Pontaillac",
                "serial": CTRL_SERIAL,
                "zone_num": 6,
                "status": "ONLINE",
                "version": "1.2",
                "sw_version": "1.1.1",
                "last_active": "2025-09-25T10:43:31",
                "zones": [
                    {"name": "Puit", "ith": 1, "enabled": True, "smart": "SMART"},
                ],
            }
        },
    }
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_return_none():
    """Return None response for device (controller) priority."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        return_value=None,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_sensor_ok():
    """OK response via sensor (soil sensor)."""
    payload = {
        "status": "OK",
        "meta": {},
        "data": {
            "sensor": {
                "name": "Capteur Hortensia",
                "serial": SENSOR_SERIAL,
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_unknown_device_type():
    """OK response with unknown device type."""
    payload = {
        "status": "OK",
        "meta": {},
        "data": {
            "badtype": {
                "name": "Capteur Hortensia",
                "serial": SENSOR_SERIAL,
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_invalid_key():
    """NetroInvalidKey -> invalid_serial_number."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=NetroInvalidKey(NETRO_ERROR_CODE_INVALID_KEY, "Invalid key"),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_cannot_connect():
    """CannotConnect -> cannot_connect."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=CannotConnect(),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_exceed_limit():
    """NetroExceedLimit -> token limit exceeded."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=NetroExceedLimit(
            NETRO_ERROR_CODE_EXCEED_LIMIT, "Token limit is exceeded"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_parameter_error():
    """NetroParameterError -> invalid parameter."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=NetroParameterError(
            NETRO_ERROR_CODE_PARAMETER_ERROR, "Invalid parameter"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_internal_error():
    """NetroInternalError -> internal server error."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=NetroInternalError(
            NETRO_ERROR_CODE_INTERNAL_ERROR, "Internal server error"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_invalid_device():
    """NetroInvalidDevice -> invalid device."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=NetroInvalidDevice(
            NETRO_ERROR_CODE_INVALID_DEVICE, "Invalid device"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_unknown():
    """Unexpected exception -> unknown."""
    with patch(
        f"{INTEGRATION_PATCH_PATH}.config_flow.NetroClient.get_info",
        side_effect=RuntimeError("boom"),
    ) as m:
        yield m


@pytest.fixture
def mock_sensor_config_entry() -> MockConfigEntry:
    """Return a mock config entry for a sensor device."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "SENSOR123",
            CONF_DEVICE_NAME: "Test Sensor",
            CONF_DEVICE_HW_VERSION: "1.0.0",
            CONF_DEVICE_SW_VERSION: "1.0.0",
        },
        options={},
        unique_id="sensor_test_123",
        entry_id="test_sensor_entry",
    )


@pytest.fixture
def mock_sensor_config_entry_with_options() -> MockConfigEntry:
    """Return a mock config entry for a sensor device with custom options."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DEVICE_TYPE: SENSOR_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "SENSOR456",
            CONF_DEVICE_NAME: "Test Sensor with Options",
            CONF_DEVICE_HW_VERSION: "2.0.0",
            CONF_DEVICE_SW_VERSION: "2.0.0",
        },
        options={
            CONF_SENS_REFRESH_INTERVAL: 30,
            CONF_SENSOR_VALUE_DAYS_BEFORE_TODAY: 3,
        },
        unique_id="sensor_test_456",
        entry_id="test_sensor_options_entry",
    )


@pytest.fixture
def mock_controller_config_entry() -> MockConfigEntry:
    """Return a mock config entry for a controller device."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE,
            CONF_SERIAL_NUMBER: "CTRL123",
            CONF_DEVICE_NAME: "Test Controller",
            CONF_DEVICE_HW_VERSION: "1.0.0",
            CONF_DEVICE_SW_VERSION: "1.0.0",
        },
        options={},
        unique_id="controller_test_123",
        entry_id="test_controller_entry",
    )


@pytest.fixture
def mock_netro_sensor_coordinator():
    """Return a mocked NetroSensorUpdateCoordinator."""
    # ✅ Use INTEGRATION_PATCH_PATH instead of hardcoded path
    with patch(f"{INTEGRATION_PATCH_PATH}.NetroSensorUpdateCoordinator") as mock_class:
        coordinator = MagicMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_class.return_value = coordinator
        yield mock_class, coordinator


@pytest.fixture
def mock_netro_controller_coordinator():
    """Return a mocked NetroControllerUpdateCoordinator."""
    # ✅ Use INTEGRATION_PATCH_PATH instead of hardcoded path
    with patch(
        f"{INTEGRATION_PATCH_PATH}.NetroControllerUpdateCoordinator"
    ) as mock_class:
        coordinator = MagicMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        coordinator.serial_number = "CTRL123"
        coordinator.device_name = "Test Controller"
        coordinator.sw_version = "1.0.0"
        coordinator.hw_version = "1.0.0"
        # Simulate attribute to determine controller type
        setattr(coordinator, "NETRO_CONTROLLER_BATTERY_LEVEL", True)
        mock_class.return_value = coordinator
        yield mock_class, coordinator
