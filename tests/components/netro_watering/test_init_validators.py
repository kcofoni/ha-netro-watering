"""Tests for validator functions in __init__.py."""

import pytest
import voluptuous as vol

from custom_components.netro_watering import _validate_slowdown_factors, hhmm_or_hhmmss


class TestValidateSlowdownFactors:
    """Test suite for _validate_slowdown_factors function."""

    def test_validate_slowdown_factors_none_input(self, snapshot):
        """Test _validate_slowdown_factors with None input."""
        result = _validate_slowdown_factors(None)

        assert result == snapshot

    def test_validate_slowdown_factors_empty_list(self, snapshot):
        """Test _validate_slowdown_factors with empty list."""
        result = _validate_slowdown_factors([])

        assert result == snapshot

    def test_validate_slowdown_factors_invalid_type(self, snapshot):
        """Test _validate_slowdown_factors with non-list input."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors("not a list")

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_valid_basic_case(self, snapshot):
        """Test _validate_slowdown_factors with valid basic slowdown factors."""
        input_data = [
            {"from": "08:00", "to": "12:00", "sdf": 2},
            {"from": "14:00", "to": "18:00", "sdf": 3},
        ]

        result = _validate_slowdown_factors(input_data)

        # Verify original input is returned unchanged
        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_valid_with_seconds(self, snapshot):
        """Test _validate_slowdown_factors with HH:MM:SS format."""
        input_data = [
            {"from": "08:00:30", "to": "12:30:45", "sdf": 2},
            {"from": "20:15:00", "to": "23:59:59", "sdf": 4},
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_midnight_crossing(self, snapshot):
        """Test _validate_slowdown_factors with midnight crossing (allowed)."""
        input_data = [
            {"from": "22:00", "to": "06:00", "sdf": 2},  # Crosses midnight
            {"from": "23:30", "to": "01:30", "sdf": 3},  # Crosses midnight
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_character_cleaning(self, snapshot):
        """Test _validate_slowdown_factors cleans NBSP and ZWSP characters."""
        input_data = [
            {
                "from": "08:00\u00a0",  # NBSP at end
                "to": "\u200b12:00",  # ZWSP at start
                "sdf": 2,
            },
            {
                "from": " 14:00 ",  # Regular spaces
                "to": "18:00\u00a0\u200b",  # Both special chars
                "sdf": 3,
            },
        ]

        result = _validate_slowdown_factors(input_data)

        # Original input should be preserved despite cleaning for validation
        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_invalid_time_format(self, snapshot):
        """Test _validate_slowdown_factors with invalid time formats."""
        input_data = [
            {"from": "25:00", "to": "12:00", "sdf": 2},  # Invalid hour
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_invalid_time_format_minutes(self, snapshot):
        """Test _validate_slowdown_factors with invalid minutes."""
        input_data = [
            {"from": "08:60", "to": "12:00", "sdf": 2},  # Invalid minutes
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_malformed_time_string(self, snapshot):
        """Test _validate_slowdown_factors with malformed time strings."""
        input_data = [
            {
                "from": "8:0",
                "to": "12:00",
                "sdf": 2,
            },  # Actually valid - Python accepts it
        ]

        # This should work since Python's strptime is flexible
        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_non_time_string(self, snapshot):
        """Test _validate_slowdown_factors with completely invalid time strings."""
        input_data = [
            {"from": "not a time", "to": "12:00", "sdf": 2},
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_sdf_less_than_one(self, snapshot):
        """Test _validate_slowdown_factors with sdf < 1."""
        input_data = [
            {"from": "08:00", "to": "12:00", "sdf": 0},  # sdf = 0 invalid
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_negative_sdf(self, snapshot):
        """Test _validate_slowdown_factors with negative sdf."""
        input_data = [
            {"from": "08:00", "to": "12:00", "sdf": -1},  # Negative sdf
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_identical_times(self, snapshot):
        """Test _validate_slowdown_factors with identical from and to times."""
        input_data = [
            {"from": "12:00", "to": "12:00", "sdf": 2},  # Identical times forbidden
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_identical_times_with_seconds(self, snapshot):
        """Test _validate_slowdown_factors with identical times including seconds."""
        input_data = [
            {"from": "12:30:45", "to": "12:30:45", "sdf": 2},  # Identical with seconds
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_multiple_items_valid(self, snapshot):
        """Test _validate_slowdown_factors with multiple valid items."""
        input_data = [
            {"from": "06:00", "to": "09:00", "sdf": 1},
            {"from": "09:30", "to": "12:30", "sdf": 2},
            {"from": "14:00:00", "to": "17:30:30", "sdf": 3},
            {"from": "20:00", "to": "23:59", "sdf": 4},
            {"from": "23:30", "to": "02:00", "sdf": 2},  # Crosses midnight
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_error_includes_index(self, snapshot):
        """Test _validate_slowdown_factors error messages include correct index."""
        input_data = [
            {"from": "08:00", "to": "12:00", "sdf": 2},  # Valid
            {"from": "14:00", "to": "18:00", "sdf": 3},  # Valid
            {
                "from": "20:00",
                "to": "20:00",
                "sdf": 2,
            },  # Invalid (identical times) - index 2
        ]

        with pytest.raises(vol.Invalid) as exc_info:
            _validate_slowdown_factors(input_data)

        result = {
            "error_message": str(exc_info.value),
            "contains_index_2": "[2]" in str(exc_info.value),
        }

        assert result == snapshot

    def test_validate_slowdown_factors_mixed_time_formats(self, snapshot):
        """Test _validate_slowdown_factors with mixed HH:MM and HH:MM:SS formats."""
        input_data = [
            {"from": "08:00", "to": "12:30:45", "sdf": 2},  # Mixed formats
            {"from": "14:15:30", "to": "18:00", "sdf": 3},  # Mixed formats
            {"from": "20:00:00", "to": "23:59:59", "sdf": 1},  # Both with seconds
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_boundary_times(self, snapshot):
        """Test _validate_slowdown_factors with boundary time values."""
        input_data = [
            {"from": "00:00", "to": "23:59", "sdf": 1},  # Full day range
            {"from": "00:00:00", "to": "23:59:59", "sdf": 2},  # Full day with seconds
            {"from": "23:59", "to": "00:01", "sdf": 3},  # Minute crossing midnight
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot

    def test_validate_slowdown_factors_sdf_edge_values(self, snapshot):
        """Test _validate_slowdown_factors with edge sdf values."""
        input_data = [
            {"from": "08:00", "to": "12:00", "sdf": 1},  # Minimum valid sdf
            {"from": "14:00", "to": "18:00", "sdf": 100},  # Large valid sdf
        ]

        result = _validate_slowdown_factors(input_data)

        assert result is input_data
        assert result == snapshot


class TestHhmm_or_hhmmss:
    """Test suite for hhmm_or_hhmmss function."""

    def test_hhmm_or_hhmmss_valid_hhmm_format(self, snapshot):
        """Test hhmm_or_hhmmss with valid HH:MM format."""
        test_cases = [
            "00:00",
            "08:30",
            "12:00",
            "23:59",
            "09:15",
        ]

        results = []
        for test_time in test_cases:
            result = hhmm_or_hhmmss(test_time)
            # Verify original string is returned unchanged
            assert result is test_time
            results.append(result)

        assert results == snapshot

    def test_hhmm_or_hhmmss_valid_hhmmss_format(self, snapshot):
        """Test hhmm_or_hhmmss with valid HH:MM:SS format."""
        test_cases = [
            "00:00:00",
            "08:30:45",
            "12:00:30",
            "23:59:59",
            "09:15:22",
        ]

        results = []
        for test_time in test_cases:
            result = hhmm_or_hhmmss(test_time)
            # Verify original string is returned unchanged
            assert result is test_time
            results.append(result)

        assert results == snapshot

    def test_hhmm_or_hhmmss_with_special_characters(self, snapshot):
        """Test hhmm_or_hhmmss with special characters that get cleaned."""
        test_cases = [
            " 08:30 ",  # Leading/trailing spaces
            "\u00a008:30\u00a0",  # NBSP characters
            "\u200b08:30\u200b",  # ZWSP characters
            " \u00a0\u200b08:30\u200b\u00a0 ",  # Mixed special chars
        ]

        results = []
        for test_time in test_cases:
            result = hhmm_or_hhmmss(test_time)
            # Verify original string is returned unchanged (not cleaned)
            assert result is test_time
            results.append(result)

        assert results == snapshot

    def test_hhmm_or_hhmmss_invalid_non_string_types(self, snapshot):
        """Test hhmm_or_hhmmss with non-string input types."""
        test_cases = [
            123,
            12.34,
            None,
            [],
            {},
            True,
        ]

        results = []
        for test_input in test_cases:
            with pytest.raises(vol.Invalid) as exc_info:
                hhmm_or_hhmmss(test_input)
            results.append(
                {
                    "input": str(test_input),
                    "input_type": type(test_input).__name__,
                    "error_message": str(exc_info.value),
                }
            )

        assert results == snapshot

    def test_hhmm_or_hhmmss_invalid_time_formats(self, snapshot):
        """Test hhmm_or_hhmmss with invalid time format strings."""
        test_cases = [
            "24:00",  # Invalid hour (24)
            "12:60",  # Invalid minute (60)
            "12:30:60",  # Invalid second (60)
            "8:30",  # Missing leading zero for hour
            "08:5",  # Missing leading zero for minute
            "12:30:5",  # Missing leading zero for second
            "abc:def",  # Non-numeric
            "12:30:45:00",  # Too many parts
            "12",  # Missing minute
            ":30",  # Missing hour
            "12:",  # Missing minute after colon
            "12:30:",  # Missing second after colon
            "",  # Empty string
            "25:30",  # Hour > 23
            "12:70",  # Minute > 59
            "12:30:70",  # Second > 59
            "-1:30",  # Negative hour
            "12:-5",  # Negative minute
            "12:30:-1",  # Negative second
        ]

        results = []
        for test_time in test_cases:
            with pytest.raises(vol.Invalid) as exc_info:
                hhmm_or_hhmmss(test_time)
            results.append(
                {
                    "input": test_time,
                    "error_message": str(exc_info.value),
                }
            )

        assert results == snapshot

    def test_hhmm_or_hhmmss_edge_cases(self, snapshot):
        """Test hhmm_or_hhmmss with edge cases."""
        # Valid edge cases
        valid_cases = [
            "00:00",  # Midnight
            "23:59",  # One minute before midnight
            "00:00:00",  # Midnight with seconds
            "23:59:59",  # Last second of day
        ]

        valid_results = []
        for test_time in valid_cases:
            result = hhmm_or_hhmmss(test_time)
            assert result is test_time
            valid_results.append(result)

        # Invalid edge cases
        invalid_cases = [
            "24:00",  # Invalid midnight representation
            "23:60",  # Invalid minute
            "24:00:00",  # Invalid midnight with seconds
            "23:59:60",  # Invalid second
        ]

        invalid_results = []
        for test_time in invalid_cases:
            with pytest.raises(vol.Invalid) as exc_info:
                hhmm_or_hhmmss(test_time)
            invalid_results.append(
                {
                    "input": test_time,
                    "error_message": str(exc_info.value),
                }
            )

        result = {
            "valid_cases": valid_results,
            "invalid_cases": invalid_results,
        }

        assert result == snapshot

    def test_hhmm_or_hhmmss_preserves_original_string(self, snapshot):
        """Test that hhmm_or_hhmmss always returns the exact original string."""
        # Test cases with various formatting that should be cleaned but original preserved
        test_cases = [
            "08:30",  # Clean format
            " 08:30 ",  # With spaces
            "\u00a008:30\u00a0",  # With NBSP
            "\u200b08:30\u200b",  # With ZWSP
            " \u00a008:30\u00a0 ",  # Mixed whitespace
        ]

        results = []
        for original in test_cases:
            result = hhmm_or_hhmmss(original)
            # Critical test: result must be the EXACT same object
            assert result is original
            # And also equal in value
            assert result == original
            results.append(
                {
                    "original": repr(original),
                    "result": repr(result),
                    "is_same_object": result is original,
                    "is_equal_value": result == original,
                }
            )

        assert results == snapshot
