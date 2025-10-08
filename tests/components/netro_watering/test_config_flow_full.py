"""Tests for the Netro Watering config flow covering all user scenarios.

This module verifies successful and error paths for user configuration,
including device, sensor, fallback, authentication, connection, and duplicate entry handling.
"""

from unittest import mock

import pytest

from homeassistant import data_entry_flow
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant

from .test_imports import (
    CONF_DEVICE_HW_VERSION,
    CONF_DEVICE_SW_VERSION,
    CONF_SERIAL_NUMBER,
    DOMAIN,
    config_flow,
)

CTRL_SERIAL = "CTRL999"
SENS_SERIAL = "SN123"
DEFAULT_SERIAL = CTRL_SERIAL


@pytest.mark.asyncio
async def test_full_flow_success_device(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_device_ok
) -> None:
    """Test successful config flow for a Netro device.

    This test verifies that the config flow creates an entry with the correct title and data
    when a valid device response is returned.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"] == config_flow.DEVICE_SCHEMA
    assert result["errors"] == {}
    assert result["handler"] == "netro_watering"
    assert result["flow_id"] == mock.ANY

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: CTRL_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Pontaillac"
    data = result["data"]
    assert data[CONF_SERIAL_NUMBER] == CTRL_SERIAL
    assert data[CONF_DEVICE_HW_VERSION] == "1.2"  # From your mock payload
    assert data[CONF_DEVICE_SW_VERSION] == "1.1.1"  # If you specify it
    assert mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_success_sensor(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_sensor_ok
) -> None:
    """Test successful config flow for a Netro sensor.

    This test verifies that the config flow creates an entry with the correct title and data
    when a valid sensor response is returned.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"] == config_flow.DEVICE_SCHEMA
    assert result["errors"] == {}
    assert result["handler"] == "netro_watering"
    assert result["flow_id"] == mock.ANY

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: SENS_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Capteur Hortensia"
    data = result["data"]
    assert data[CONF_SERIAL_NUMBER] == SENS_SERIAL
    assert data[CONF_DEVICE_HW_VERSION] == "3.1"  # From your mock payload
    assert data.get(CONF_DEVICE_SW_VERSION) == "3.1.3"  # If you specify it
    assert mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_invalid_auth(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_invalid_key
) -> None:
    """Test config flow with invalid authentication.

    This test verifies that the config flow returns an error when an invalid API key is provided.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: "BADKEY"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_serial_number"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_netro_exceed_limit(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_netro_exceed_limit
) -> None:
    """Test config flow with NetroExceedLimit exception.

    This test verifies that the config flow returns an error when the Netro API exceeds its limit.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "netro_error_occurred"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_netro_parameter_error(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_netro_parameter_error
) -> None:
    """Test config flow with NetroParameterError exception.

    This test verifies that the config flow returns an error when the Netro API encounters a parameter error.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "netro_error_occurred"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_netro_internal_error(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_netro_internal_error
) -> None:
    """Test config flow with NetroInternalError exception.

    This test verifies that the config flow returns an error when the Netro API encounters an internal error.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "netro_error_occurred"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_netro_invalid_device(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_netro_invalid_device
) -> None:
    """Test config flow with NetroInvalidDevice exception.

    This test verifies that the config flow returns an error when the Netro API encounters an invalid device error.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "netro_error_occurred"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_cannot_connect_native(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_cannot_connect
) -> None:
    """Test config flow when connection to Netro API cannot be established.

    This test verifies that the config flow returns a 'cannot_connect' error when the API is unreachable.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_cannot_connect_response_none(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_return_none
) -> None:
    """Test config flow when Netro API returns None.

    This test verifies that the config flow returns a 'cannot_connect' error when the API response is None.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_full_flow_unknown(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_unknown
) -> None:
    """Test config flow when an unknown error occurs.

    This test verifies that the config flow returns an 'unknown' error when an unexpected error is encountered.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"
    assert not mock_setup_entry.called


@pytest.mark.asyncio
async def test_abort_if_already_configured_same_unique_id(
    hass: HomeAssistant, mock_setup_entry, mock_get_info_device_ok
) -> None:
    """Test that config flow aborts if an entry with the same unique ID already exists.

    This test verifies that a second config flow with the same unique ID is aborted
    with the 'already_configured' reason.
    """
    # First flow -> creates the entry
    res1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    res1 = await hass.config_entries.flow.async_configure(
        res1["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert res1["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    # Second flow with same serial -> abort
    res2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    res2 = await hass.config_entries.flow.async_configure(
        res2["flow_id"], user_input={CONF_SERIAL_NUMBER: DEFAULT_SERIAL}
    )
    assert res2["type"] is data_entry_flow.FlowResultType.ABORT
    assert res2["reason"] == "already_configured"
