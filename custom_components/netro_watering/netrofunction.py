"""python API of the Netro Public API (NPA).

It may be used for implementing a home automation system plugin.

Please refer to http://www.netrohome.com/en/shop/articles/10 for further
details
"""

from asyncio import timeout
import json
import logging
import re
from typing import Any

# requests module providing http request API that is fully used
# in this module
from aiohttp import ClientResponse
import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# requests constants
REQUESTS_TIMEOUT = 30

# configure logging very simply, only one specific logger and a null handler
# in order to prevent the logged events in this library being output to
# sys.stderr in the absence of logging configuration
logger = logging.getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# netro public api url
netro_base_url = "https://api.netrohome.com/npa/v1/"  # pylint: disable=invalid-name


def _join_url(base: str, path: str) -> str:
    # robust to missing/extra slashes
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


# netro constants as defined by the netro api (NPA)
NETRO_GET_SCHEDULES = "schedules.json"
NETRO_GET_INFO = "info.json"
NETRO_GET_MOISTURES = "moistures.json"
NETRO_GET_SENSORDATA = "sensor_data.json"
NETRO_POST_REPORTWEATHER = "report_weather.json"
NETRO_POST_MOISTURE = "set_moisture.json"
NETRO_POST_WATER = "water.json"
NETRO_POST_STOPWATER = "stop_water.json"
NETRO_POST_NOWATER = "no_water.json"
NETRO_POST_STATUS = "set_status.json"
NETRO_GET_EVENTS = "events.json"

NETRO_STATUS_ENABLE = 1
NETRO_STATUS_DISABLE = 0
NETRO_STATUS_STANDBY = "STANDBY"
NETRO_STATUS_WATERING = "WATERING"
NETRO_SCHEDULE_EXECUTED = "EXECUTED"
NETRO_SCHEDULE_EXECUTING = "EXECUTING"
NETRO_SCHEDULE_VALID = "VALID"
NETRO_ERROR = "ERROR"
NETRO_OK = "OK"
NETRO_EVENT_DEVICEOFFLINE = 1
NETRO_EVENT_DEVICEONLINE = 2
NETRO_EVENT_SCHEDULESTART = 3
NETRO_EVENT_SCHEDULEEND = 4

NETRO_ERROR_CODE_INVALID_KEY = 1
NETRO_ERROR_CODE_EXCEED_LIMIT = 3
NETRO_ERROR_CODE_INVALID_DEVICE_OR_SENSOR = 4
NETRO_ERROR_CODE_INTERNAL_ERROR = 5
NETRO_ERROR_CODE_PARAMETER_ERROR = 6


def set_netro_base_url(url: str):
    """Change the Netro Public API url."""
    global netro_base_url  # pylint: disable=global-statement  # noqa: PLW0603
    netro_base_url = url


class NetroException(Exception):
    """standard Netro exception for raising any NPA application error."""

    def __init__(self, result) -> None:
        """Make an exception from any result error code and message."""
        self.message = result["errors"][0]["message"]
        self.code = result["errors"][0]["code"]

    def __str__(self):
        """Return a literal error message related to the current exception."""
        return (
            f"a netro (NPA) error occurred -- error code #{self.code} -> {self.message}"
        )


def mask(s: str) -> str:
    """Mask a key/serial in logs (keep first 2/last 2 characters)."""
    return re.sub(r"(?<=..).*(?=..)", "****", s) if s and len(s) > 4 else "****"


def _validate_netro_payload(payload: dict[str, Any]) -> None:
    # Basic types
    if not isinstance(payload.get("status"), str):
        raise TypeError("Netro: missing/invalid 'status'")
    if not isinstance(payload.get("meta"), dict):
        raise TypeError("Netro: missing/invalid 'meta'")

    # Expected values
    status = payload["status"]
    if status not in ("OK", "ERROR"):
        raise ValueError(f"Netro: unexpected status '{status}'")

    if status == "OK":
        if "data" not in payload:
            raise ValueError("Netro: missing 'data' for OK")
    else:  # ERROR
        errs = payload.get("errors")
        if not (isinstance(errs, list) and errs and isinstance(errs[0], dict)):
            raise TypeError("Netro: missing/invalid 'errors' for ERROR")


async def _read_json_dict_or_raise(resp: ClientResponse) -> dict[str, Any]:
    """Read the body (text), parse as JSON, check root is a dict, then validate Netro envelope schema.

    Raises an explicit error if validation fails.
    """
    content_type = resp.headers.get("Content-Type")
    status = resp.status
    raw = await resp.text()

    if not raw:
        # If 4xx/5xx, let HTTP error be raised; otherwise, abnormal format.
        resp.raise_for_status()
        raise ValueError("Netro API returned empty body (JSON dict expected)")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        snippet = raw[:200].replace("\n", " ")
        raise ValueError(
            f"Netro non-JSON (HTTP {status}, Content-Type={content_type!r}): {snippet}"
        ) from e

    if not isinstance(data, dict):
        snippet = raw[:200].replace("\n", " ")
        raise TypeError(
            f"Netro root must be a dict, got {type(data).__name__} "
            f"(HTTP {status}, Content-Type={content_type!r}): {snippet}"
        )

    _validate_netro_payload(data)
    return data


def _safe_log_url(url: str, params: dict[str, str] | None) -> str:
    if not params:
        return url
    parts = []
    for k, v in params.items():
        if k == "key" and isinstance(v, str):
            parts.append(f"{k}={mask(v)}")  # e.g.: 34****A4 (not encoded)
        else:
            parts.append(f"{k}={v}")  # raw for logging
    return f"{url}?{'&'.join(parts)}"


async def _netro_request(
    hass: HomeAssistant,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    method: str = "GET",
) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    url = _join_url(netro_base_url, path)

    # URL safe for logs (masks key if present)
    safe_url = _safe_log_url(url, params)

    async with timeout(REQUESTS_TIMEOUT):
        if method == "GET":
            async with session.get(url, params=params) as resp:
                logger.info("Netro --> %s", safe_url)
                logger.debug("Netro --> status=%s", resp.status)
                data = await _read_json_dict_or_raise(resp)
        else:
            async with session.request(method, url, json=params) as resp:
                logger.info("Netro --> %s", safe_url)
                logger.debug("Netro --> status=%s", resp.status)
                data = await _read_json_dict_or_raise(resp)

    if data.get("status") == NETRO_ERROR:
        raise NetroException(data)
    return data


async def async_get_info(hass: HomeAssistant, key: str) -> dict[str, Any]:
    """Get basic information of the device asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.

    Returns:
    -------
    dict[str, Any]
        The device information returned by the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(hass, "info.json", params={"key": key})


def get_info(key):
    """Get basic information of the device."""
    payload = {"key": key}
    res = requests.get(
        netro_base_url + NETRO_GET_INFO, params=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("getInfo --> url = %s", res.url)
    logger.debug(
        "getInfo --> GET request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_set_status(
    hass: HomeAssistant, key: str, status: str
) -> dict[str, Any]:
    """Update status to online or standby asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    status : str
        The status to set (NETRO_STATUS_ENABLE or NETRO_STATUS_DISABLE).

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_POST_STATUS,
        params={"key": key, "status": status},
        method="POST",
    )


def set_status(key, status):
    """Update status to online or standby."""
    payload = {"key": key, "status": status}
    res = requests.post(
        netro_base_url + NETRO_POST_STATUS, data=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("setStatus --> url = %s", res.url)
    logger.debug("setStatus --> data = %s", payload)
    logger.debug(
        "setStatus --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_get_schedules(
    hass: HomeAssistant, key: str, zone_ids=None, start_date="", end_date=""
) -> dict[str, Any]:
    """Get schedules of the given zones (all zones if not specified) asynchronously. yyyy-mm-dd is the date format.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    zone_ids : list[str] | None
        The list of zone IDs to get schedules for (all zones if not specified).
    start_date : str
        The start date for the schedules (yyyy-mm-dd).
    end_date : str
        The end date for the schedules (yyyy-mm-dd).

    Returns:
    -------
    dict[str, Any]
        The schedules returned by the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_GET_SCHEDULES,
        params={
            "key": key,
            "zones": f"[{','.join(zone_ids)}]" if zone_ids else None,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def get_schedules(key, zone_ids=None, start_date="", end_date=""):
    """Get schedules of the given zones (all zones if not specified). yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    res = requests.get(
        netro_base_url + NETRO_GET_SCHEDULES, params=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("getSchedules --> url = %s", res.url)
    logger.debug(
        "getSchedules --> GET request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_get_moistures(
    hass: HomeAssistant, key: str, zone_ids=None, start_date="", end_date=""
) -> dict[str, Any]:
    """Get moisture data of the given zones (all zones if not specified) asynchronously. yyyy-mm-dd is the date format.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    zone_ids : list[str] | None
        The list of zone IDs to get moisture data for (all zones if not specified).
    start_date : str
        The start date for the moisture data (yyyy-mm-dd).
    end_date : str
        The end date for the moisture data (yyyy-mm-dd).

    Returns:
    -------
    dict[str, Any]
        The moisture data returned by the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_GET_MOISTURES,
        params={
            "key": key,
            "zones": f"[{','.join(zone_ids)}]" if zone_ids else None,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def get_moistures(key, zone_ids=None, start_date="", end_date=""):
    """Get moisture data of the given zones (all zones if not specified). yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    res = requests.get(
        netro_base_url + NETRO_GET_MOISTURES, params=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("getMoistures --> url = %s", res.url)
    logger.debug(
        "getMoistures --> GET request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_report_weather(
    hass: HomeAssistant,
    key: str,
    date: str,
    condition: str | None = None,
    rain: float | None = None,
    rain_prob: float | None = None,
    temp: float | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    t_dew: float | None = None,
    wind_speed: float | None = None,
    humidity: float | None = None,
    pressure: float | None = None,
) -> dict[str, Any]:
    """Report weather asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    date : str
        The date of the weather report (yyyy-mm-dd).
    condition : str | None
        The weather condition (optional).
    rain : float | None
        The amount of rain in mm (optional).
    rain_prob : float | None
        The probability of rain in percentage (optional).
    temp : float | None
        The temperature in Celsius (optional).
    t_min : float | None
        The minimum temperature in Celsius (optional).
    t_max : float | None
        The maximum temperature in Celsius (optional).
    t_dew : float | None
        The dew point temperature in Celsius (optional).
    wind_speed : float | None
        The wind speed in km/h (optional).
    humidity : float | None
        The humidity in percentage (optional).
    pressure : float | None
        The atmospheric pressure in hPa (optional).

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    payload = {"key": key, "date": date}
    if condition:
        payload["condition"] = condition
    if rain is not None:
        payload["rain"] = rain
    if rain_prob is not None:
        payload["rain_prob"] = rain_prob
    if temp is not None:
        payload["temp"] = temp
    if t_min is not None:
        payload["t_min"] = t_min
    if t_max is not None:
        payload["t_max"] = t_max
    if t_dew is not None:
        payload["t_dew"] = t_dew
    if wind_speed is not None:
        payload["wind_speed"] = wind_speed
    if humidity is not None:
        payload["humidity"] = humidity
    if pressure is not None:
        payload["pressure"] = pressure

    return await _netro_request(
        hass,
        NETRO_POST_REPORTWEATHER,
        params=payload,
        method="POST",
    )


def report_weather(
    key,
    date,
    condition,
    rain,
    rain_prob,
    temp,
    t_min,
    t_max,
    t_dew,
    wind_speed,
    humidity,
    pressure,
):
    """Report weather."""
    payload = {"key": key, "date": date}
    if condition:
        payload["condition"] = condition
    if rain:
        payload["rain"] = rain
    if rain_prob:
        payload["rain_prob"] = rain_prob
    if temp:
        payload["temp"] = temp
    if t_min:
        payload["t_min"] = t_min
    if t_max:
        payload["t_max"] = t_max
    if t_dew:
        payload["t_dew"] = t_dew
    if wind_speed:
        payload["wind_speed"] = wind_speed
    if humidity:
        payload["humidity"] = humidity
    if pressure:
        payload["pressure"] = pressure
    res = requests.post(
        netro_base_url + NETRO_POST_REPORTWEATHER,
        data=payload,
        timeout=REQUESTS_TIMEOUT,
    )

    logger.info("reportWeather --> url = %s", res.url)
    logger.debug("reportWeather --> data = %s", payload)
    logger.debug(
        "reportWeather --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_set_moisture(
    hass: HomeAssistant, key: str, moisture: float, zone_ids=None
) -> dict[str, Any]:
    """Set moisture to the given zones (all zones if not specified) asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    moisture : float
        The moisture level to set (0-100).
    zone_ids : list[str] | None
        The list of zone IDs to set the moisture level for (optional).

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.
    """
    payload = {"key": key, "moisture": moisture}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    return await _netro_request(
        hass,
        NETRO_POST_MOISTURE,
        params=payload,
        method="POST",
    )


def set_moisture(key, moisture, zone_ids=None):
    """Set moisture to the given zones (all zones if not specified)."""
    payload = {"key": key, "moisture": moisture}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    res = requests.post(
        netro_base_url + NETRO_POST_MOISTURE, data=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("setMoisture --> url = %s", res.url)
    logger.debug("setMoisture --> data = %s", payload)
    logger.debug(
        "setMoisture --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_water(
    hass: HomeAssistant, key: str, duration: int, zone_ids=None, delay=0, start_time=""
) -> dict[str, Any]:
    """Start watering of the given zones (all zones consecutively if not specified) asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    duration : int
        The duration of the watering in seconds.
    zone_ids : list[str] | None
        The list of zone IDs to water (optional).
    delay : int
        The delay before starting the watering (optional).
    start_time : str
        The start time for the watering (optional).

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.
    """
    payload = {"key": key, "duration": duration}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    if delay > 0:
        payload["delay"] = delay
    if start_time:
        payload["start_time"] = start_time
    return await _netro_request(
        hass,
        NETRO_POST_WATER,
        params=payload,
        method="POST",
    )


def water(key, duration, zone_ids=None, delay=0, start_time=""):
    """Start watering of the given zones (all zones consecutively if not specified)."""
    payload = {"key": key, "duration": duration}
    if zone_ids is not None:
        payload["zones"] = f"[{','.join(zone_ids)}]"
    if delay > 0:
        payload["delay"] = delay
    if start_time:
        payload["start_time"] = start_time
    res = requests.post(
        netro_base_url + NETRO_POST_WATER, data=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("water --> url = %s", res.url)
    logger.debug("water --> data = %s", payload)
    logger.debug(
        "water --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_stop_water(hass: HomeAssistant, key: str) -> dict[str, Any]:
    """Stop watering (all currently watering zones) asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_POST_STOPWATER,
        params={"key": key},
        method="POST",
    )


def stop_water(key):
    """Stop watering (all currently watering zones)."""
    payload = {"key": key}
    res = requests.post(
        netro_base_url + NETRO_POST_STOPWATER, data=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("stopWater --> url = %s", res.url)
    logger.debug("stopWater --> data = %s", payload)
    logger.debug(
        "stopWater --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_no_water(
    hass: HomeAssistant, key: str, days: int | None = None
) -> dict[str, Any]:
    """Do not water for several days (one day if not specified) asynchronously.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    days : int | None
        The number of days to not water (optional).

    Returns:
    -------
    dict[str, Any]
        The response from the Netro API.
    """
    payload = {"key": key}
    if days is not None:
        payload["days"] = round(days)
    return await _netro_request(
        hass,
        NETRO_POST_NOWATER,
        params=payload,
        method="POST",
    )


def no_water(key, days=None):
    """Do not water for several days (one day if not specified)."""
    payload = {"key": key}
    if days is not None:
        payload["days"] = round(days)

    res = requests.post(
        netro_base_url + NETRO_POST_NOWATER, data=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("noWater --> url = %s", res.url)
    logger.debug("noWater --> data = %s", payload)
    logger.debug(
        "noWater --> POST request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_get_sensor_data(
    hass: HomeAssistant, key: str, start_date="", end_date=""
) -> dict[str, Any]:
    """Get sensor data asynchronously. yyyy-mm-dd is the date format.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    start_date : str
        The start date for the sensor data (yyyy-mm-dd).
    end_date : str
        The end date for the sensor data (yyyy-mm-dd).

    Returns:
    -------
    dict[str, Any]
        The sensor data returned by the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_GET_SENSORDATA,
        params={
            "key": key,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def get_sensor_data(key, start_date="", end_date=""):
    """Get sensor data. yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    res = requests.get(
        netro_base_url + NETRO_GET_SENSORDATA, params=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("getSensorData --> url = %s", res.url)
    logger.debug(
        "getSensorData --> GET request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None


async def async_get_events(
    hass: HomeAssistant, key: str, type_of_event=0, start_date="", end_date=""
) -> dict[str, Any]:
    """Get events (return all types of events if not specified) asynchronously. yyyy-mm-dd is the date format.

    Parameters
    ----------
    hass : HomeAssistant
        The Home Assistant instance.
    key : str
        The Netro API key.
    type_of_event : int
        The type of event to retrieve (0 for all types).
    start_date : str
        The start date for the events (yyyy-mm-dd).
    end_date : str
        The end date for the events (yyyy-mm-dd).

    Returns:
    -------
    dict[str, Any]
        The events returned by the Netro API.

    Raises:
    ------
    NetroException
        If the Netro API returns an error.
    """
    return await _netro_request(
        hass,
        NETRO_GET_EVENTS,
        params={
            "key": key,
            "event": type_of_event,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def get_events(key, type_of_event=0, start_date="", end_date=""):
    """Get events (return all types of events if not specified). yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if type_of_event > 0:
        payload["event"] = type_of_event
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    res = requests.get(
        netro_base_url + NETRO_GET_EVENTS, params=payload, timeout=REQUESTS_TIMEOUT
    )

    logger.info("getEvents --> url = %s", res.url)
    logger.debug(
        "getEvents --> GET request status code = %s, json result = %s",
        res.status_code,
        res.json(),
    )

    # is there a netro error ?
    if res.json()["status"] == NETRO_ERROR:
        raise NetroException(res.json())
    # is there an http error ?
    if not res.ok:
        res.raise_for_status()
    # so, it seems everything is ok !
    else:
        return res.json()
    return None
