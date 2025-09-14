# Netro Smart Garden Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) ![GitHub repo size](https://img.shields.io/github/repo-size/kcofoni/ha-netro-watering) ![GitHub](https://img.shields.io/github/license/kcofoni/ha-netro-watering)

## About
This is a Home Assistant custom integration for **Netro Smart Garden** devices.

It lets you manage the [Netro](https://netrohome.com) ecosystem —controllers and sensors —to **automate garden watering** in Home Assistant. The integration uses Netro’s [Public API](http://www.netrohome.com/en/shop/articles/10).

**Compatibility:** developed and tested with Home Assistant **2023.4.0** and later.

*This project is community-maintained and not affiliated with Netro, Inc.*

## Description
Netro controllers drive the solenoid valves that irrigate your garden’s **zones** (individual watering circuits). The number of zones available depends on your controller model. Only zones that are physically connected to a solenoid valve are exposed and can be controlled by the integration.

The integration exposes three device types:
- **Controllers**
- **Zones** (controlled by the controllers)
- **Soil sensors** that measure soil moisture, temperature, and light level

With this integration, you can monitor and control your controllers, zones, and sensors in Home Assistant.

**Supported models:** Netro **Sprite**, **Spark**, **Pixie**, and **Whisperer** (currently supported).

## Installation

### From HACS

1. Install HACS if you haven't already (see the [installation guide](https://www.hacs.xyz/docs/use/download/download/#to-download-hacs-container)).
2. In Home Assistant, open **HACS → Integrations**, search for **Netro Watering**, and install it.
3. **Restart** Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for **Netro Watering**, and add it.

---

### Manual

1. Download and unzip the [repo archive](https://github.com/kcofoni/ha-netro-watering/archive/refs/heads/main.zip).  
   *(Alternatively, click **Code → Download ZIP**, or clone the repo.)*
2. Copy the integration into your config so that this path exists:
   ```
   /config/custom_components/netro_watering/
   ```
   If the archive contains `custom_components/netro_watering/`, copy that folder as-is.
3. **Restart** Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for **Netro Watering**, and add it.

---

## Configuration

Repeat step **4** for **each device** you want to include—whether a **soil sensor**, a **multi-zone controller** (*Sprite* or *Spark*), or a **single-zone controller** (*Pixie*).  
Each **zone** managed by a controller is created as a **separate device** linked to that controller.

![add a config entry](https://kcofoni.github.io/ha-netro-watering/images/add_config_entry.png "Setup of a Netro device")
![device is created](https://kcofoni.github.io/ha-netro-watering/images/device_created.png "Success: Netro device added")

After setup, you may see multiple devices and **dozens of entities**, including:
- **Soil sensors:** moisture, temperature, and illuminance.
- **Zones:** current/last/next watering status; switches to start/stop watering.
- **Controllers:** switches to enable/disable controllers; a **calendar** per controller showing watering schedules planned by Netro.

Polling intervals can be configured separately for sensors and controllers. A default watering duration can be set per controller. Advanced settings are available for both sensors and controllers. 

![change controller options](https://kcofoni.github.io/ha-netro-watering/images/controller_options.png "Controller options")
![change sensor options](https://kcofoni.github.io/ha-netro-watering/images/sensor_options.png "Sensor options")

> **Note**
> You no longer need to reload the device after changing options. Changes are applied automatically.
> - Most updates take effect on the **next polling cycle**.
> - `default_watering_delay` and `delay_before_refresh` apply to **subsequent commands**.
> - `sensor_value_days_before_today` is used on the **next sensor update**.
> - No manual reload or restart is required (except for internal fields like `netro_api_url`, if instructed).

## Lovelace cards
Here are some lovelace cards I am presently using to control my watering system with the help of this integration.

![watering](https://kcofoni.github.io/ha-netro-watering/images/watering-controller-main.png "Controller") ![planning](https://kcofoni.github.io/ha-netro-watering/images/planning-arrosage.png "Planning") ![sensors](https://kcofoni.github.io/ha-netro-watering/images/ground-sensors.png "Sensors") 
![charts](https://kcofoni.github.io/ha-netro-watering/images/courbes-capteurs.png "Charts") ![calendar](https://kcofoni.github.io/ha-netro-watering/images/calendar.png "Calendar") ![start](https://kcofoni.github.io/ha-netro-watering/images/start-watering.png "Start")


### Automation
The Netro Watering entities may be integrated into automations. The following integration custom services are available:
- **Start watering** and **Stop watering** services - to be applied to any controller or zone.
- **Enable** and **Disable** services - to be applied to any controller.
- **Refresh data** - allows to update the data of the devices (controller, zones, sensors) when desired
- **Report weather** - for reporting weather data, overriding system default weather data
- **No water** - suspend watering for a given number of days on the specified controller

![call service](https://kcofoni.github.io/ha-netro-watering/images/service_call.png "Developer Tools")

### Set moisture level
The nominal functioning of the Netro ecosystem is based on irrigation planning algorithms that take into account the physiognomy of the areas to be irrigated, the plants that compose them and the properties of the soil, the weather forecast, as well as a certain number of other factors. In addition to this information, Netro needs to know at a given time the temperature and humidity of the areas to be watered in order to precisely determine the watering periods. Soil sensors supplied by Netro (Whisperer model) allow these measurements to be made. If you do not have these sensors which are an integral part of the ecosystem but other external sensors, you can provide Netro with the level of humidity given by these sensors so that it can apply its algorithms in the same way.

The **Set moisture** service provided by the integration and applicable to a particular zone, allows this to be done.

![set moistures](https://kcofoni.github.io/ha-netro-watering/images/set_moisture.png "Developer Tools")

### Report weather
Netro offers to obtain weather data, very useful for establishing automatic watering schedules, from a number of weather providers. In some cases, national services may be more relevant and more precise so that we will want to feed Netro with data from these services instead of the listed providers. The **Report weather** service is offered for this purpose. Each user will be able to establish his own Home Assistant script which will call on this service after having collected custom weather information.

## Advanced configuration
You can configure a few general settings for the Netro Watering integration in Home Assistant’s *configuration.yaml*. These settings are optional and not tied to a specific device. The integration works well without them, but they can optimize behavior or cover specific use cases. If omitted, default values are used.

- **`slowdown_factors`** (default: null) — A mapping of time windows to a multiplier applied to the controllers’ polling interval (sensors are not affected). During matching windows, the effective polling interval becomes: base_interval × multiplier (typically > 1 to slow down).
- **`netro_api_url`** — For internal use only.

The following parameters were previously defined in the configuration file, but the UI options now take precedence for both sensors and controllers. 

- **`delay_before_refresh`** *(default: **5 s**)* — Wait time **before fetching status** from the [Netro Public API (NPA)](http://www.Netrohome.com/en/shop/articles/10) after sending a command (e.g., start watering). In practice, **≥ 4 s** is needed; **5 s** is a safe default. If set too low, you may read stale state.

- **`default_watering_delay`** *(default: **0 s**)* — **Grace period** before actually starting irrigation after a start command. Useful for testing start/stop switches without opening valves. For production, keep **0 s**.

- **`sensor_value_days_before_today`** *(default: **1**, min: **1**)* — **Look-back window (days)** for sensor history used by the integration. If a sensor is temporarily offline, the last value **within this window** can be reused. Larger values increase the risk of stale data.

### About the slowdown factor

As indicated in the documentation, the number of calls to the [Public API of Netro](http://www.Netrohome.com/en/shop/articles/10) is limited. Today, a maximum of 2,000 calls per day and per device is permitted and the counter is reset every day at midnight UTC. Netro does not provide mechanisms that reference a callback function, as do a number of similar systems, so that each event is notified as it occurs. For this reason, it is useful to frequently request the system to obtain a state of the situation, as faithful as possible to reality, at "t" time.

The configuration of a device (controller or sensor) within UI makes it possible to define, as showed above, a specific polling frequency (refresh interval). One may wonder if this refresh period should be the same regardless of the time of day. There are indeed time slots on which there is no gain in polling the system very often (at night for example) and at the opposite times when watering is very likely and which requires close monitoring.

The **slowdown factor** (`sdf`) temporarily **multiplies the controllers’ polling interval** during specified time windows (sensors are not affected).

**Formula:** `effective_polling_interval = base_interval × sdf`

> Times use 24-hour `HH:MM` format and can cross midnight (see first window below).

#### Example (`configuration.yaml`)
```yaml
slowdown_factors:
  - from: '23:00'  # overnight: slow down while everyone sleeps
    to:   '05:55'
    sdf:  15       # polling interval ×15 in this window

  - from: '10:30'  # hottest/sunniest hours: fewer checks or only occasional watering
    to:   '17:00'
    sdf:  5        # e.g., if base is 2 min, becomes 10 min between 10:30 and 17:00
```

**Outside the defined windows, the nominal polling interval is used.** This approach allows a **short nominal interval** while selectively **slowing controller polling** at certain times of day.

### Example of Netro configuration in *configuration.yaml*

```yaml
netro_watering:
  delay_before_refresh: 5            # seconds
  default_watering_delay: 0          # start watering immediately
  sensor_value_days_before_today: 2  # use last readings up to "day before yesterday"
  slowdown_factors:
    - from: '23:00'  # overnight: slow down while everyone sleeps
      to:   '05:55'
      sdf:  15       # polling interval ×15 in this window
    - from: '10:30'  # hottest/sunniest hours: fewer checks
      to:   '17:00'
      sdf:  5        # e.g., base 2 min -> 10 min in this window
```
