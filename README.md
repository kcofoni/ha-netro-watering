
# Netro Smart Garden Integration for Home Assistant


[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![CI](https://github.com/kcofoni/ha-netro-watering/workflows/CI/badge.svg)](https://github.com/kcofoni/ha-netro-watering/actions) [![codecov](https://codecov.io/gh/kcofoni/ha-netro-watering/branch/main/graph/badge.svg)](https://codecov.io/gh/kcofoni/ha-netro-watering) [![GitHub release](https://img.shields.io/github/v/release/kcofoni/ha-netro-watering)](https://github.com/kcofoni/ha-netro-watering/releases) ![GitHub repo size](https://img.shields.io/github/repo-size/kcofoni/ha-netro-watering) ![GitHub](https://img.shields.io/github/license/kcofoni/ha-netro-watering)


## 📑 Table of Contents

- [ℹ️ About](#ℹ️-about)
- [📖 Description](#📖-description)
- [🌱 Installation](#🌱-installation)
- [⚙️ Configuration](#⚙️-configuration)
- [🌦️ Netro Weather Sync Blueprint](#🌦️-netro-weather-sync-blueprint)
- [🖼️ Lovelace cards](#🖼️-lovelace-cards)
- [🛠️ Advanced configuration](#🛠️-advanced-configuration)

## ℹ️ About
Home Assistant integration for Netro Smart Garden devices. It lets you manage Netro controllers and soil sensors to monitor conditions, control zones, and automate watering from Home Assistant.

The integration uses [Netro’s Public API](https://www.netrohome.com/en/shop/articles/10) for device access and scheduling.

**Compatibility:** developed and tested with Home Assistant 2023.4.0 and later.

*This project is community-maintained and not affiliated with Netro, Inc.*

## 📖 Description
This integration connects your Netro controller and sensors to Home Assistant so you can view soil moisture and temperature and control watering schedules.

What you get:
- Devices: Controllers, Zones (one device per physically connected valve), and Soil sensors (moisture, temperature, illuminance).
- Entities: per-zone switches to start/stop watering, controller-level enable/disable switches, sensor readings, and a calendar entity showing Netro’s planned watering schedule.
- Services: start/stop watering, enable/disable controller, refresh data, report weather, set moisture level, and suspend watering for N days.

Why use it
- Monitor real-time soil moisture and environmental data to fine-tune irrigation.
- Manually start or stop watering zones from Home Assistant or include them in automations and scenes.
- Combine Netro’s scheduling with Home Assistant weather and sensors to build smarter, water-saving automations.

Notes
- The number of zones exposed depends on your controller model; only valves physically connected to the controller are shown.
- Supported models (Netro): *Sprite*, *Spark*, *Pixie* and *Whisperer*.
- Requires a Netro account and valid _serial keys_ configured during integration setup.

## 🌱 Installation

### 🛒 From HACS

1. Install HACS if you haven't already (see the [installation guide](https://www.hacs.xyz/docs/use/download/download/#to-download-hacs-container)).
2. In Home Assistant, open **HACS → Integrations**, search for **Netro Watering**, and install it.
3. **Restart** Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for **Netro Watering**, and add it.

### 📦 Manual

1. Download and unzip the [repo archive](https://github.com/kcofoni/ha-netro-watering/archive/refs/heads/main.zip).  
   *(Alternatively, click **Code → Download ZIP**, or clone the repo.)*
2. Copy the integration into your config so that this path exists:
   ```
   /config/custom_components/netro_watering/
   ```
   If the archive contains `custom_components/netro_watering/`, copy that folder as-is.
3. **Restart** Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**, search for **Netro Watering**, and add it.

## ⚙️ Configuration

Repeat step **4** for **each device** you want to include — whether a **soil sensor**, a **multi-zone controller** (*Sprite* or *Spark*), or a **single-zone controller** (*Pixie*).  

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


> **ℹ️ Note**
> You no longer need to reload the device after changing options. Changes are applied automatically.
> - Most updates take effect on the **next polling cycle**.
> - `default_watering_delay` and `delay_before_refresh` apply to **subsequent commands**.
> - `sensor_value_days_before_today` is used on the **next sensor update**.
> - No manual reload or restart is required (except for internal fields like `netro_api_url`, if instructed).

## 🌦️ Netro Weather Sync Blueprint

This blueprint allows you to synchronize your **Netro smart watering** system with current weather conditions using Home Assistant data. It dynamically adjusts watering schedules to prevent watering during rain or when humidity is high, helping you save water efficiently.

### Installation (Import the Blueprint)

You can easily import this blueprint into your Home Assistant instance.

**Quick import (recommended):**  
[![Import Blueprint into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fkcofoni%2Fha-netro-watering%2Fmain%2Fblueprints%2Fscript%2Fkcofoni%2Fnetro_weather_sync.yaml)

**Manual import (alternative):**
1. In Home Assistant, open **Settings → Automations & Scenes → Blueprints → Import Blueprint**.
2. Paste the following URL into the *Blueprint address* field:
  ```
  https://raw.githubusercontent.com/kcofoni/ha-netro-watering/main/blueprints/script/kcofoni/netro_weather_sync.yaml
  ```
3. Click **Preview**, then **Import**.

### How to Use

After importing the blueprint:

1. Go to **Settings → Automations & Scenes → Scripts**.  
2. Click **➕ Create Script → Use Blueprint**.  
3. Select **Netro Weather Sync** from the list.  
4. Configure the required inputs:
- **Netro Controller**: select the controller entity to sync.
- **Weather Entity**: select the source weather entity (e.g. `weather.paris`).
- **Rain Probability Entity (Optional)**: sensor entity for rain probability if available.
5. Save the script, then run it manually or call it from an automation.

#### 💡 Tips

> - Schedule this script to run **once or twice per day** (for example, at sunrise or in the evening).
> - Combine it with the built-in **Weather integration** or your preferred local provider.
> - You can trigger it anytime via **Developer Tools → Services → script.netro_weather_sync**.
> - Ensure your Netro integration is properly configured and authenticated before running the script.

## 🖼️ Lovelace cards
Here are some Lovelace cards used to control the watering system with this integration.

![watering](https://kcofoni.github.io/ha-netro-watering/images/watering-controller-main.png "Controller") ![planning](https://kcofoni.github.io/ha-netro-watering/images/planning-arrosage.png "Planning") ![sensors](https://kcofoni.github.io/ha-netro-watering/images/ground-sensors.png "Sensors") 
![charts](https://kcofoni.github.io/ha-netro-watering/images/courbes-capteurs.png "Charts") ![calendar](https://kcofoni.github.io/ha-netro-watering/images/calendar.png "Calendar") ![start](https://kcofoni.github.io/ha-netro-watering/images/start-watering.png "Start")


## ⏰ Example Automation
The Netro Watering entities may be integrated into automations. The following integration custom services are available:
- **Start watering** and **Stop watering** - to be applied to any controller or zone.
- **Enable** and **Disable** - to be applied to any controller.
- **Refresh data** - allows to update the data of the devices (controller, zones, sensors) when desired
- **Report weather** - for reporting weather data, overriding system default weather data
- **No water** - suspend watering for a given number of days on the specified controller

![call service](https://kcofoni.github.io/ha-netro-watering/images/service_call.png "Developer Tools")

### 💧 Set moisture level
Netro’s irrigation planning algorithms use area layout, plant types, soil properties, weather forecasts, and current temperature and soil moisture to calculate watering. Netro’s soil sensors (the *Whisperer* model) provide the required moisture readings. If you don’t have Netro sensors but have other reliable soil sensors, you can provide their moisture level to Netro so it can use that information in its calculations.

The **Set moisture** service exposed by the integration can be called for a specific zone to report a custom moisture level.

![set moistures](https://kcofoni.github.io/ha-netro-watering/images/set_moisture.png "Developer Tools")

### 🌦️ Report weather
Netro supports receiving custom weather data, which can improve the accuracy of its watering schedules. The integration exposes a **Report weather** service that accepts common weather fields (temperature, humidity, rain amount, rain probability, min/max temperatures, wind speed, etc.).

You can create a small Home Assistant script or automation that gathers data from your preferred weather sensors or provider and calls this service. See the [Netro Weather Sync Blueprint](#🌦️-netro-weather-sync-blueprint) for a ready-to-use example that collects weather data and forwards it to Netro.

Note: the example below calls the script created by the Netro Weather Sync blueprint (for instance `script.netro_weather_sync_meteo_france`). If you imported the blueprint and created a script from it, use the script entity name generated by Home Assistant. Otherwise, create a script with that name or adapt the automation to call your own script/service.

Example automation (YAML)
```yaml
alias: Synchro Netro Météo France
description: Update Netro with Météo France data twice daily
triggers:
  - at: "06:00:00"
    trigger: time
  - at: "18:00:00"
    trigger: time
actions:
  - action: script.netro_weather_sync_meteo_france
    data:
      number_of_days_forecast: "{{ number_of_days_forecast }}"
variables:
  number_of_days_forecast: 5
```

## 🛠️ Advanced configuration

You can configure a few general settings for the Netro Watering integration in Home Assistant’s *configuration.yaml*. These settings are **optional** and not tied to a specific device. The integration works well without them, but they can optimize behavior or cover specific use cases. If omitted, default values are used.

- **`slowdown_factors`** (default: null) — A mapping of time windows to a multiplier applied to the controllers’ polling interval (sensors are not affected). During matching windows, the effective polling interval becomes: base_interval × multiplier (typically > 1 to slow down).
- **`netro_api_url`** — For internal use only.

The following parameters were previously defined in the configuration file, but the UI options now take precedence for both sensors and controllers. 

- **`delay_before_refresh`** *(default: **5 s**)* — Wait time **before fetching status** from the [Netro Public API (NPA)](https://www.netrohome.com/en/shop/articles/10) after sending a command (e.g., start watering). In practice, **≥ 4 s** is needed; **5 s** is a safe default. If set too low, you may read stale state.

- **`default_watering_delay`** *(default: **0 s**)* — **Grace period** before actually starting irrigation after a start command. Useful for testing start/stop switches without opening valves. For production, keep **0 s**.

- **`sensor_value_days_before_today`** *(default: **1**, min: **1**)* — **Look-back window (days)** for sensor history used by the integration. If a sensor is temporarily offline, the last value **within this window** can be reused. Larger values increase the risk of stale data.

### About the slowdown factor

As indicated in the documentation, the number of calls to the [Public API of Netro](https://www.netrohome.com/en/shop/articles/10) is limited. Today, a maximum of 2,000 calls per day and per device is permitted and the counter is reset every day at midnight UTC. Netro does not provide mechanisms that reference a callback function, as do a number of similar systems, so that each event is notified as it occurs. For this reason, it is useful to frequently request the system to obtain a state of the situation, as faithful as possible to reality, at "t" time.


The configuration of a device (controller or sensor) within the UI makes it possible to define, as shown above, a specific polling frequency (refresh interval). One may wonder if this refresh period should be the same regardless of the time of day. There are indeed time slots on which there is no gain in polling the system very often (at night for example) and, conversely, times when watering is very likely and which requires close monitoring.

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
