"""Simplified tests for OptionsFlowHandler methods."""

from custom_components.netro_watering.config_flow import OptionsFlowHandler
from custom_components.netro_watering.const import (
    CONF_DELAY_BEFORE_REFRESH,
    DOMAIN,
    GLOBAL_PARAMETERS,
)


class TestOptionsFlowHandlerMethods:
    """Test individual methods of OptionsFlowHandler."""

    def test_gp_method_with_data(self, hass):
        """Test _gp method retrieves global parameters correctly."""
        # Set up test data
        test_params = {"test_param": "test_value", CONF_DELAY_BEFORE_REFRESH: 5}
        hass.data = {DOMAIN: {GLOBAL_PARAMETERS: test_params}}

        # Create handler instance and set hass manually
        handler = OptionsFlowHandler()
        handler.hass = hass

        # Test _gp method
        result = handler._gp()
        assert result == test_params
        assert result[CONF_DELAY_BEFORE_REFRESH] == 5
        assert result["test_param"] == "test_value"

    def test_gp_method_empty_domain(self, hass):
        """Test _gp method with empty domain data."""
        # Set up hass with empty domain data
        hass.data = {DOMAIN: {}}

        # Create handler and test
        handler = OptionsFlowHandler()
        handler.hass = hass

        result = handler._gp()
        assert result == {}

    def test_gp_method_no_domain(self, hass):
        """Test _gp method with no domain data at all."""
        # Set up hass with no domain
        hass.data = {}

        # Create handler and test
        handler = OptionsFlowHandler()
        handler.hass = hass

        result = handler._gp()
        assert result == {}

    def test_gp_method_no_global_params(self, hass):
        """Test _gp method with domain but no global parameters."""
        # Set up hass with domain but no GLOBAL_PARAMETERS key
        hass.data = {DOMAIN: {"other_key": "other_value"}}

        # Create handler and test
        handler = OptionsFlowHandler()
        handler.hass = hass

        result = handler._gp()
        assert result == {}
