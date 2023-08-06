"""python API of the Netro Public API (NPA).

It may be used for implementing a home automation system plugin.

Please refer to http://www.netrohome.com/en/shop/articles/10 for further
details
"""

# requests module providing http request API that is fully used
# in this module
import logging

import requests

# requests constants
REQUESTS_TIMEOUT = 30

# configure logging very simply, only one specific logger and a null handler
# in order to prevent the logged events in this library being output to
# sys.stderr in the absence of logging configuration
logger = logging.getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# netro public api url
netro_base_url = "https://api.netrohome.com/npa/v1/"  # pylint: disable=invalid-name

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


# ruff: noqa
def set_netro_base_url(url: str):
    """Change the Netro Public API url."""
    global netro_base_url  # pylint: disable=global-statement
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


def get_schedules(key, zone_ids=None, start_date="", end_date=""):
    """Get schedules of the given zones (all zones if not specified). yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if zone_ids is not None:
        payload["zones"] = f'[{",".join(zone_ids)}]'
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


def get_moistures(key, zone_ids=None, start_date="", end_date=""):
    """Get moisture data of the given zones (all zones if not specified). yyyy-mm-dd is the date format."""
    payload = {"key": key}
    if zone_ids is not None:
        payload["zones"] = f'[{",".join(zone_ids)}]'
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


def set_moisture(key, moisture, zone_ids=None):
    """Set moisture to the given zones (all zones if not specified)."""
    payload = {"key": key, "moisture": moisture}
    if zone_ids is not None:
        payload["zones"] = f'[{",".join(zone_ids)}]'
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


def water(key, duration, zone_ids=None, delay=0, start_time=""):
    """Start watering of the given zones (all zones consecutively if not specified)."""
    payload = {"key": key, "duration": duration}
    if zone_ids is not None:
        payload["zones"] = f'[{",".join(zone_ids)}]'
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
