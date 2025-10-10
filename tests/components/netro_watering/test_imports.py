"""Conditional imports for test environment compatibility."""


# Environment detection
def _is_ha_core_environment() -> bool:
    """Check if running in Home Assistant Core environment."""
    try:
        import homeassistant.components.netro_watering  # type: ignore # noqa: F401, PLC0415 # pylint: disable=W0611
    except ImportError:
        return False
    else:
        return True


# Conditional import
if _is_ha_core_environment():
    # Home Assistant Core environment
    from homeassistant.components.netro_watering import (  # type: ignore
        PLATFORMS,
        async_setup,
        async_setup_entry,
        async_unload_entry,
        config_flow,
    )
    from homeassistant.components.netro_watering.config_flow import (  # type: ignore
        CONF_DEVICE_HW_VERSION,
        CONF_DEVICE_SW_VERSION,
    )
    from homeassistant.components.netro_watering.const import (  # type: ignore
        CONF_SERIAL_NUMBER,
        DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,  # noqa: F401, RUF100
        DOMAIN,
        SENS_REFRESH_INTERVAL_MN,  # noqa: F401, RUF100
        SENSOR_DEVICE_TYPE,  # noqa: F401, RUF100
    )

    # Variables for patches
    INTEGRATION_PATH = "homeassistant.components.netro_watering"

else:
    # Standalone environment (custom_components)
    from custom_components.netro_watering import (  # noqa: F401, RUF100
        PLATFORMS,
        async_setup,
        async_setup_entry,
        async_unload_entry,
        config_flow,
    )
    from custom_components.netro_watering.config_flow import (
        CONF_DEVICE_HW_VERSION,
        CONF_DEVICE_SW_VERSION,
    )
    from custom_components.netro_watering.const import (
        CONF_SERIAL_NUMBER,
        DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY,  # noqa: F401, RUF100
        DOMAIN,
        SENS_REFRESH_INTERVAL_MN,  # noqa: F401, RUF100
        SENSOR_DEVICE_TYPE,  # noqa: F401, RUF100
    )

    # Variables for patches
    INTEGRATION_PATH = "custom_components.netro_watering"

# Export imported modules
__all__ = [
    "CONF_DEVICE_HW_VERSION",
    "CONF_DEVICE_SW_VERSION",
    "CONF_SERIAL_NUMBER",
    "DEFAULT_SENSOR_VALUE_DAYS_BEFORE_TODAY",
    "DOMAIN",
    "INTEGRATION_PATH",
    "PLATFORMS",
    "SENSOR_DEVICE_TYPE",
    "SENS_REFRESH_INTERVAL_MN",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
    "config_flow",
]
