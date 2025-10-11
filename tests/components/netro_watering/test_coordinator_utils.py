"""Tests for coordinator utility functions."""

import datetime

import pytest

from custom_components.netro_watering.coordinator import (
    Meta,
    get_slowdown_factor,
    prepare_slowdown_factors,
)


class TestPrepareSlowdownFactors:
    """Test suite for prepare_slowdown_factors function."""

    def test_prepare_slowdown_factors_basic_case(self, snapshot):
        """Test basic case with simple time windows."""
        input_data = [
            {"from": "08:30", "to": "12:00", "sdf": 2},
            {"from": "14:15:30", "to": "18:45", "sdf": 3},
            {"from": "22:00", "to": "06:30", "sdf": 4},  # Crosses midnight
        ]

        result = prepare_slowdown_factors(input_data)

        # Snapshot test - will create reference on first run
        assert result == snapshot

    def test_prepare_slowdown_factors_empty_list(self, snapshot):
        """Test with empty list."""
        input_data = []

        result = prepare_slowdown_factors(input_data)

        assert result == snapshot

    def test_prepare_slowdown_factors_none_input(self, snapshot):
        """Test with None input."""
        result = prepare_slowdown_factors(None)

        assert result == snapshot

    def test_prepare_slowdown_factors_complex_case(self, snapshot):
        """Test with complex time windows including various formats."""
        input_data = [
            {"from": "00:00", "to": "06:00", "sdf": 1},
            {"from": "06:30:15", "to": "09:45:30", "sdf": 2},
            {"from": "12:00:00", "to": "14:30:45", "sdf": 3},
            {"from": "18:15", "to": "23:59:59", "sdf": 4},
            {"from": "23:30", "to": "02:15", "sdf": 5},  # Crosses midnight
        ]

        result = prepare_slowdown_factors(input_data)

        assert result == snapshot

    def test_prepare_slowdown_factors_midnight_crossing(self, snapshot):
        """Test specifically for midnight crossing scenarios."""
        input_data = [
            {"from": "22:30", "to": "06:30", "sdf": 2},
            {"from": "23:45:30", "to": "01:15:45", "sdf": 3},
        ]

        result = prepare_slowdown_factors(input_data)

        assert result == snapshot

    def test_prepare_slowdown_factors_with_seconds(self, snapshot):
        """Test with time formats including seconds."""
        input_data = [
            {"from": "08:30:15", "to": "12:45:30", "sdf": 2},
            {"from": "14:00:00", "to": "18:30:59", "sdf": 3},
        ]

        result = prepare_slowdown_factors(input_data)

        assert result == snapshot


class TestGetSlowdownFactor:
    """Test suite for get_slowdown_factor function."""

    def test_get_slowdown_factor_default_no_factors(self, snapshot):
        """Test that default factor 1 is returned when no slowdown factors are provided."""
        test_time = datetime.time(10, 30, 0)

        result = get_slowdown_factor(None, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_empty_list(self, snapshot):
        """Test that default factor 1 is returned when empty list is provided."""
        test_time = datetime.time(10, 30, 0)

        result = get_slowdown_factor([], test_time)

        assert result == snapshot

    def test_get_slowdown_factor_time_in_window(self, snapshot):
        """Test factor is returned when time falls within a defined window."""
        slowdown_factors = [
            {"from": 8.5, "to": 12.0, "sdf": 2},  # 08:30 - 12:00
            {"from": 14.0, "to": 18.0, "sdf": 3},  # 14:00 - 18:00
        ]

        # Time within first window (10:15 = 10.25)
        test_time = datetime.time(10, 15, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_time_outside_windows(self, snapshot):
        """Test default factor 1 is returned when time is outside all windows."""
        slowdown_factors = [
            {"from": 8.5, "to": 12.0, "sdf": 2},  # 08:30 - 12:00
            {"from": 14.0, "to": 18.0, "sdf": 3},  # 14:00 - 18:00
        ]

        # Time outside windows (13:00 = 13.0)
        test_time = datetime.time(13, 0, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_exact_boundary_start(self, snapshot):
        """Test factor is returned when time is exactly at window start."""
        slowdown_factors = [
            {"from": 8.5, "to": 12.0, "sdf": 2},  # 08:30 - 12:00
        ]

        # Time exactly at start (08:30 = 8.5)
        test_time = datetime.time(8, 30, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_exact_boundary_end(self, snapshot):
        """Test factor is returned when time is exactly at window end."""
        slowdown_factors = [
            {"from": 8.5, "to": 12.0, "sdf": 2},  # 08:30 - 12:00
        ]

        # Time exactly at end (12:00 = 12.0)
        test_time = datetime.time(12, 0, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_midnight_crossing_positive(self, snapshot):
        """Test factor is returned for midnight crossing window (positive time)."""
        slowdown_factors = [
            {"from": -2.0, "to": 6.5, "sdf": 4},  # 22:00 - 06:30 (crosses midnight)
        ]

        # Time in positive part (01:00 = 1.0)
        test_time = datetime.time(1, 0, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_midnight_crossing_negative(self, snapshot):
        """Test factor is returned for midnight crossing window (negative time)."""
        slowdown_factors = [
            {"from": -2.0, "to": 6.5, "sdf": 4},  # 22:00 - 06:30 (crosses midnight)
        ]

        # Time in negative part (23:00 = 23.0, converts to -1.0)
        test_time = datetime.time(23, 0, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_with_seconds(self, snapshot):
        """Test factor calculation with seconds precision."""
        slowdown_factors = [
            {
                "from": 8.504166666666666,
                "to": 12.758333333333333,
                "sdf": 2,
            },  # 08:30:15 - 12:45:30
        ]

        # Time with seconds (08:45:30 = 8.758333...)
        test_time = datetime.time(8, 45, 30)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot

    def test_get_slowdown_factor_first_match_wins(self, snapshot):
        """Test that first matching window is used when multiple windows overlap."""
        slowdown_factors = [
            {"from": 8.0, "to": 12.0, "sdf": 2},  # 08:00 - 12:00
            {"from": 10.0, "to": 14.0, "sdf": 3},  # 10:00 - 14:00 (overlaps)
        ]

        # Time in both windows (11:00 = 11.0) - should return first match (sdf=2)
        test_time = datetime.time(11, 0, 0)
        result = get_slowdown_factor(slowdown_factors, test_time)

        assert result == snapshot


class TestMeta:
    """Test suite for Meta class."""

    def test_meta_initialization_valid_data(self, snapshot):
        """Test Meta initialization with valid ISO datetime strings."""
        meta = Meta(
            last_active="2024-10-10T08:30:15",
            time="2024-10-10T10:45:30",
            tid="TID123456",
            version="1.2.3",
            token_limit=1000,
            token_remaining=750,
            token_reset="2024-10-11T00:00:00",
        )

        result = {
            "version": meta.version,
            "token_limit": meta.token_limit,
            "token_remaining": meta.token_remaining,
            "tid": meta.tid,
            "last_active_date": meta.last_active_date.isoformat(),
            "time": meta.time.isoformat(),
            "token_reset_date": meta.token_reset_date.isoformat(),
        }

        assert result == snapshot

    def test_meta_datetime_conversion_with_microseconds(self, snapshot):
        """Test Meta handles ISO datetime strings with microseconds."""
        meta = Meta(
            last_active="2024-10-10T08:30:15.123456",
            time="2024-10-10T10:45:30.987654",
            tid="TID789",
            version="2.0.0",
            token_limit=500,
            token_remaining=250,
            token_reset="2024-10-11T00:00:00.000000",
        )

        result = {
            "last_active_microseconds": meta.last_active_date.microsecond,
            "time_microseconds": meta.time.microsecond,
            "token_reset_microseconds": meta.token_reset_date.microsecond,
        }

        assert result == snapshot

    def test_meta_datetime_conversion_with_timezone(self, snapshot):
        """Test Meta handles ISO datetime strings with timezone info."""
        meta = Meta(
            last_active="2024-10-10T08:30:15+02:00",
            time="2024-10-10T10:45:30Z",
            tid="TID_TZ",
            version="1.0.0",
            token_limit=2000,
            token_remaining=1500,
            token_reset="2024-10-11T00:00:00-05:00",
        )

        result = {
            "last_active_tz": str(meta.last_active_date.tzinfo),
            "time_tz": str(meta.time.tzinfo),
            "token_reset_tz": str(meta.token_reset_date.tzinfo),
            "last_active_utc_offset": meta.last_active_date.utcoffset(),
            "time_utc_offset": meta.time.utcoffset(),
        }

        assert result == snapshot

    def test_meta_edge_case_midnight(self, snapshot):
        """Test Meta with midnight times."""
        meta = Meta(
            last_active="2024-10-10T00:00:00",
            time="2024-10-10T00:00:00",
            tid="MIDNIGHT",
            version="0.0.1",
            token_limit=100,
            token_remaining=0,
            token_reset="2024-10-11T00:00:00",
        )

        result = {
            "hour": meta.last_active_date.hour,
            "minute": meta.time.minute,
            "second": meta.token_reset_date.second,
            "token_remaining_zero": meta.token_remaining,
        }

        assert result == snapshot

    def test_meta_invalid_datetime_format(self, snapshot):
        """Test Meta raises ValueError for invalid datetime format."""
        with pytest.raises(ValueError) as exc_info:
            Meta(
                last_active="invalid-date-format",
                time="2024-10-10T10:45:30",
                tid="ERROR_TEST",
                version="1.0.0",
                token_limit=1000,
                token_remaining=500,
                token_reset="2024-10-11T00:00:00",
            )

        result = {
            "exception_type": type(exc_info.value).__name__,
            "exception_message_contains_invalid": "Invalid isoformat string"
            in str(exc_info.value),
        }

        assert result == snapshot

    def test_meta_invalid_time_format(self, snapshot):
        """Test Meta raises ValueError for invalid time format."""
        with pytest.raises(ValueError) as exc_info:
            Meta(
                last_active="2024-10-10T08:30:15",
                time="not-a-time",
                tid="TIME_ERROR",
                version="1.0.0",
                token_limit=1000,
                token_remaining=500,
                token_reset="2024-10-11T00:00:00",
            )

        result = {
            "exception_type": type(exc_info.value).__name__,
            "has_error_message": len(str(exc_info.value)) > 0,
        }

        assert result == snapshot

    def test_meta_invalid_token_reset_format(self, snapshot):
        """Test Meta raises ValueError for invalid token_reset format."""
        with pytest.raises(ValueError) as exc_info:
            Meta(
                last_active="2024-10-10T08:30:15",
                time="2024-10-10T10:45:30",
                tid="RESET_ERROR",
                version="1.0.0",
                token_limit=1000,
                token_remaining=500,
                token_reset="bad-reset-time",
            )

        result = {
            "exception_type": type(exc_info.value).__name__,
            "exception_occurred": True,
        }

        assert result == snapshot

    def test_meta_extreme_values(self, snapshot):
        """Test Meta with extreme but valid values."""
        meta = Meta(
            last_active="1970-01-01T00:00:00",  # Unix epoch
            time="2099-12-31T23:59:59",  # Far future
            tid="EXTREME_TEST_" + "X" * 100,  # Long TID
            version="999.999.999",
            token_limit=999999,
            token_remaining=0,
            token_reset="2024-12-31T23:59:59.999999",
        )

        result = {
            "last_active_year": meta.last_active_date.year,
            "time_year": meta.time.year,
            "tid_length": len(meta.tid),
            "version": meta.version,
            "token_limit": meta.token_limit,
            "token_remaining": meta.token_remaining,
            "token_reset_microsecond": meta.token_reset_date.microsecond,
        }

        assert result == snapshot
