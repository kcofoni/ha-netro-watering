# Netro Smart Garden Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

## About
This is a Home Assistant integration for Netro Smart Garden devices

This custom component allows you to manage the [*Netro*](https://Netrohome.com/) ecosystem, ensuring the automatic watering of the garden, thanks to the controllers and sensors of the brand. It relies on *Netro*'s [Public API](http://www.Netrohome.com/en/shop/articles/10).

It has been developed from Home Assistant 2023.4.0 version.

## Description
The *Netro* controller is connected to the solenoid valves which will each water a particular area of your garden. The maximum number of zones that can be managed depends on the controller model you have. Only the zones actually connected to the solenoid valves can be managed by the *Netro* system and therefore by the integration.

The integration defines three types of devices:

* controllers
* zones controlled by the controllers
* soil sensors that measure the humidity and temperature of the soil as well as the amount of light received

The integration allows you to manage the controllers and all the zones and sensors that are part of your system.
Netro products *Sprite*, *Spark*, *Pixie* and *Whisperer* are actually supported.

## Installation

### From HACS

1. Install HACS if you haven't already (see [installation guide](https://hacs.netlify.com/docs/installation/manual)).
2. Add custom repository "https://github.com/kcofoni/ha-netro-watering.git" as "Integration" in the settings tab of HACS.
3. Find and install "Netro Watering" integration in HACS's "Integrations" tab.
4. Restart your Home Assistant.
5. Add "Netro Watering" integration in Home Assistant's "Configuration -> Integrations" tab.

### Manual

1. Download and unzip the [repo archive](https://github.com/kcofoni/ha-netro-watering/archive/refs/heads/main.zip). (You could also click "Download ZIP" after pressing the green button in the repo, alternatively, you could clone the repo from SSH add-on).
2. Copy contents of the archive/repo into your `/config` directory.
3. Restart your Home Assistant.
4. Add "Netro Watering" integration in Home Assistant's "Configuration -> Integrations" tab.

## Configuration

Please repeat step 4. as mentioned above for each device you want to include, whatever it is a ground sensor, a multi-zone controller (Sprite or Spark) or a single-zone controler (Pixie). Each zone of a controller will be represented by separate device related to the controller it depends on.

At this point, several devices may have been created related to ten's of entity. This latter are representing the humidity, temperature, illuminance of the sensors as well as the current/last/next status of each zone. Switches have been created allowing to start/stop watering and enable/disable controllers.

Options may be changed related to polling refresh interval of sensors and controllers independently. Default watering duration and schedules options may also be changed specifically for the controllers. 

**IMPORTANT: to be effective, each time options have been changed the related device must be reloaded.**

## Running
No dedicated card has been implemented yet but perhaps there will be user contributions in this direction. In the meantime can be displayed in a very classical layout.

### Automation
The Netro Watering entities may be integrated into automations. The following integration custom services are available:
- **start watering** and **stop watering** services - to be applied to any controller or zone
- **enable** and **disable** services - to be applied to any controller

### Force moisture level
The nominal functioning of the Netro ecosystem is based on irrigation planning algorithms that take into account the physiognomy of the areas to be irrigated, the plants that compose them and the properties of the soil as well as a certain number of other factors. In addition to this information, Netro needs to know at a given time the temperature and humidity of the areas to be watered in order to precisely determine the watering periods. Soil sensors supplied by Netro (Whisperer model) allow these measurements to be made. If you do not have these sensors which are an integral part of the ecosystem but other external sensors, you can provide Netro with the level of humidity given by these sensors so that it can apply its algorithms in the same way.

The **set moisture**"** service provided by the integration and applicable to a particular zone, allows this to be done.

## Advanced configuration
Some general settings can be set for the Netro Watering integration in the Home Assistant configuration file (*configuration.yaml*). They correspond to both optional and non-device specific parameters. The integration works well without its parameters which can nevertheless provide optimizations and respond to specific situations. If not set, the default values are applied.

  - **delay_before_refresh** [default value = 5]: This is the **time to wait, in seconds, before getting a status feedback** from [NPA](http://www.Netrohome.com/en/shop/articles/10) after executing a given action (i.e. start watering). My experience shows that at least 4 secondes are needed, so I personally put 5 to be comfortable.
  - **default_watering_delay** [default value = 0]: This is the **time to wait before actually proceeding when starting the irrigation**. I don't see much point in setting this parameter in production. I use it to test start/stop irrigation switches without having to actually run my solenoid valves each time.
  - **sensor_value_days_before_today** [default value = 1, must be > 1]: This is the depth of the history of the values ​​reported by the sensors, used by the integration. Useful when a sensor is inoperative for a while and you still want to retrieve its last values.
  - **slowdown_factors** [default value = None]: It is a dictionary that defines time slots during which the polling process of controllers (not applicable for sensors) will be slowed down by applying a multiplier coefficient to the refresh period (see explanations below)
  - **netro_api_url**: internal use

### About the slowdown factor

As indicated in the documentation, the number of calls to the [Public API of Netro](http://www.Netrohome.com/en/shop/articles/10) is limited. Today, a maximum of 2,000 calls per day and per device is permitted and the counter is reset every day at midnight UTC. Netro does not provide mechanisms that reference a callback function, as do a number of similar systems, so that each event is notified as it occurs. For this reason, it is useful to frequently request the system to obtain a state of the situation, as faithful as possible to reality, at "t" time.

The configuration of a device (controller or sensor) within UI makes it possible to define, as showed above, a specific polling frequency (refresh interval). One may wonder if this refresh period should be the same regardless of the time of day. There are indeed time slots on which there is no gain in polling the system very often (at night for example) and at the opposite times when watering is very likely and which requires close monitoring.

The slowdown factor parameter (sdf) reduce the refresh rate at certain times. Let us take an example:

    slowdown_factors:
    - from: '23:00' # everybody sleeps during the night, isn't it ?
        to: '05:55'
        sdf: 15     # the refresh period will be multiplied by 15 during the given time slot
    - from: '10:30' # it is too hot and sunny to reasonably decide to water (or very ponctual watering)
        to: '17:00'
        sdf: 5      # that means that if the nominal refresh period is 2 mn for a given controller it becomes 10 mn between 10:30am and 5pm

**The rest of the time, the nominal refresh period is applied**. Thanks to this mechanism of slowing down at certain times of the day, **one can decide on a fairly short polling period**.

### Example of Netro Configuration in *configuration.yaml*

    netro_watering:
        delay_before_refresh: 5 # in seconds
        default_watering_delay: 0 # starting watering right now
        sensor_value_days_before_today: 2 # getting values of the sensors until the day before yesterday
        slowdown_factors:
            - from: '23:00' # everybody sleeps during the night...
            to: '05:55'
            sdf: 15
            - from: '10:30' # it is too hot and sunny to reasonably decide to water (or very ponctual watering)
            to: '17:00'
            sdf: 5
