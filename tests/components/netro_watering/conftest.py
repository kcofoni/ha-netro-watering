"""Pytest fixtures for Netro Watering integration tests."""

from unittest.mock import patch

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
import pytest

from homeassistant.components.netro_watering.config_flow import CannotConnect

DOMAIN = "netro_watering"
CTRL_SERIAL = "CTRL999"
SENSOR_SERIAL = "SN123"


@pytest.fixture
def mock_setup_entry():
    """Prevents actual integration setup after CREATE_ENTRY."""
    with patch(
        "homeassistant.components.netro_watering.async_setup_entry", return_value=True
    ) as m:
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
                "serial": CTRL_SERIAL,  # <- import CTRL_SERIAL from the test or hardcode the same value
                "zone_num": 6,
                "status": "ONLINE",
                "version": "1.2",  # <- IMPORTANT: present
                "sw_version": "1.1.1",
                "last_active": "2025-09-25T10:43:31",
                "zones": [
                    {"name": "Puit", "ith": 1, "enabled": True, "smart": "SMART"},
                    # ... you can leave only one, that's enough
                ],
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_return_none():
    """OK response for device (controller) priority."""
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
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
                "serial": SENSOR_SERIAL,  # <- import SENS_SERIAL from the test or hardcode the same value
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
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
                "serial": SENSOR_SERIAL,  # <- import SENS_SERIAL from the test or hardcode the same value
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_invalid_key():
    """NetroInvalidKey -> invalid_serial_number."""
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=NetroInvalidKey(NETRO_ERROR_CODE_INVALID_KEY, "Invalid key"),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_cannot_connect():
    """CannotConnect -> cannot_connect."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=CannotConnect(),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_exceed_limit():
    """NetroExceedLimit -> token limit exceeded."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=NetroExceedLimit(
            NETRO_ERROR_CODE_EXCEED_LIMIT, "Token limit is exceeded"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_parameter_error():
    """NetroParameterError -> invalid parameter."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=NetroParameterError(
            NETRO_ERROR_CODE_PARAMETER_ERROR, "Invalid parameter"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_internal_error():
    """NetroInternalError -> internal server error."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=NetroInternalError(
            NETRO_ERROR_CODE_INTERNAL_ERROR, "Internal server error"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_netro_invalid_device():
    """NetroInvalidDevice -> invalid device."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=NetroInvalidDevice(
            NETRO_ERROR_CODE_INVALID_DEVICE, "Invalid device"
        ),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_unknown():
    """Unexpected exception -> unknown."""
    with patch(
        "homeassistant.components.netro_watering.config_flow.NetroClient.get_info",
        side_effect=RuntimeError("boom"),
    ) as m:
        yield m
