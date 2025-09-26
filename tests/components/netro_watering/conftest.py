"""Pytest fixtures for Netro Watering integration tests."""

import asyncio
from unittest.mock import patch

import pytest

from homeassistant.components.netro_watering import netrofunction as nf

DOMAIN = "netro_watering"
CTRL_SERIAL = "CTRL999"
SENSOR_SERIAL = "SN123"


@pytest.fixture
def mock_setup_entry():
    """Empêche le setup réel de l'intégration après CREATE_ENTRY."""
    with patch(
        "homeassistant.components.netro_watering.async_setup_entry", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_device_ok():
    """Réponse OK prioritaire device (controller)."""
    payload = {
        "status": "OK",
        "meta": {"time": "2025-09-25T11:23:20"},
        "data": {
            "device": {
                "name": "Pontaillac",
                "serial": CTRL_SERIAL,  # <- importe CTRL_SERIAL depuis le test ou hardcode la même valeur
                "zone_num": 6,
                "status": "ONLINE",
                "version": "1.2",  # <- IMPORTANT: présent
                "sw_version": "1.1.1",
                "last_active": "2025-09-25T10:43:31",
                "zones": [
                    {"name": "Puit", "ith": 1, "enabled": True, "smart": "SMART"},
                    # ... je peux en laisser 1 seule, ça suffit
                ],
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_sensor_ok():
    """Réponse OK via sensor (capteur de sol)."""
    payload = {
        "status": "OK",
        "meta": {},
        "data": {
            "sensor": {
                "name": "Capteur Hortensia",
                "serial": SENSOR_SERIAL,  # <- importe SENS_SERIAL depuis le test ou hardcode la même valeur
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_unknown_device_type():
    """Réponse OK via sensor (capteur de sol)."""
    payload = {
        "status": "OK",
        "meta": {},
        "data": {
            "badtype": {
                "name": "Capteur Hortensia",
                "serial": SENSOR_SERIAL,  # <- importe SENS_SERIAL depuis le test ou hardcode la même valeur
                "status": "ONLINE",
                "version": "3.1",
                "sw_version": "3.1.3",
                "last_active": "2025-09-25T10:22:22",
            }
        },
    }
    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        return_value=payload,
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_invalid_key():
    """NetroException(code=1) -> invalid_auth."""

    class E(nf.NetroException):
        def __init__(self) -> None:
            super().__init__(
                {
                    "errors": [
                        {
                            "code": nf.NETRO_ERROR_CODE_INVALID_KEY,
                            "message": "Invalid key",
                        }
                    ]
                }
            )

    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        side_effect=E(),
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_cannot_connect():
    """Timeout (ou autre erreur réseau) -> cannot_connect."""

    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        side_effect=asyncio.TimeoutError(),  # noqa: UP041
    ) as m:
        yield m


@pytest.fixture
def mock_get_info_unknown():
    """Exception inattendue -> unknown."""
    with patch(
        "homeassistant.components.netro_watering.config_flow.async_get_info",
        side_effect=RuntimeError("boom"),
    ) as m:
        yield m
