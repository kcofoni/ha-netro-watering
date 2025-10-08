"""Test suite for the netro_watering integration."""

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def init_integration(
    hass: HomeAssistant, entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the netro_watering integration for testing.

    Adds the mock config entry to Home Assistant and completes setup.
    """
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
