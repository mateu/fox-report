#!/usr/bin/env python3
"""
Pytest test suite for time_resolver module.
"""

import pytest
import tempfile
import yaml
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import pytz

from time_resolver_enhanced import TimeResolver


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return {
        'location': {
            'latitude': 46.9080,
            'longitude': -114.0722,
            'timezone': 'America/Denver',
            'elevation': 980
        },
        'output': {
            'verbosity': 1,
            'log_file': '/tmp/test_fox_report.log'
        },
        'advanced': {
            'twilight_type': 'nautical',
            'buffer_minutes': 15
        }
    }


@pytest.fixture
def static_config():
    """Create a static time configuration for testing."""
    return {
        'static_times': {
            'enabled': True,
            'start_time': '20:00',
            'end_time': '06:00'
        },
        'location': {
            'timezone': 'America/Denver'
        },
        'output': {
            'verbosity': 1
        }
    }


@pytest.fixture
def config_file(sample_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        return f.name


@pytest.fixture
def static_config_file(static_config):
    """Create a temporary static config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(static_config, f)
        return f.name


class TestTimeResolver:
    """Test cases for TimeResolver class."""

    def test_init_with_valid_config(self, config_file):
        """Test TimeResolver initialization with valid config."""
        resolver = TimeResolver(config_file)
        assert resolver.config is not None
        assert 'location' in resolver.config
        assert resolver.logger is not None

    def test_init_with_missing_config(self):
        """Test TimeResolver initialization with missing config file."""
        with pytest.raises(FileNotFoundError):
            TimeResolver("nonexistent_config.yaml")

    def test_load_config_invalid_yaml(self):
        """Test config loading with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError):
            TimeResolver(f.name)

    def test_get_night_range_current_night(self, config_file):
        """Test getting current night's dusk/dawn times."""
        resolver = TimeResolver(config_file)
        dusk, dawn = resolver.get_night_range()

        assert isinstance(dusk, datetime)
        assert isinstance(dawn, datetime)
        assert dusk < dawn
        assert dusk.tzinfo is not None
        assert dawn.tzinfo is not None

    def test_get_night_range_lookback(self, config_file):
        """Test getting previous night's times with lookback."""
        resolver = TimeResolver(config_file)

        # Current night
        current_dusk, current_dawn = resolver.get_night_range()

        # Previous night
        prev_dusk, prev_dawn = resolver.get_night_range(lookback_nights=1)

        # Previous night should be before current night
        assert prev_dusk < current_dusk
        assert prev_dawn < current_dawn

    def test_get_night_range_specific_date(self, config_file):
        """Test getting night range for specific date."""
        resolver = TimeResolver(config_file)
        target_date = date(2025, 7, 1)

        dusk, dawn = resolver.get_night_range(target_date)

        assert dusk.date() == target_date
        assert dawn.date() == target_date + timedelta(days=1)

    def test_static_times_configuration(self, static_config_file):
        """Test static times configuration."""
        resolver = TimeResolver(static_config_file)
        dusk, dawn = resolver.get_night_range()

        # Should use static times (20:00 and 06:00)
        assert dusk.hour == 20
        assert dusk.minute == 0
        assert dawn.hour == 6
        assert dawn.minute == 0

    def test_get_multiple_night_ranges(self, config_file):
        """Test getting multiple night ranges."""
        resolver = TimeResolver(config_file)
        ranges = resolver.get_multiple_night_ranges(nights_count=3)

        assert len(ranges) == 3

        # Each range should be a tuple of (dusk, dawn)
        for dusk, dawn in ranges:
            assert isinstance(dusk, datetime)
            assert isinstance(dawn, datetime)
            assert dusk < dawn

        # Ranges should be in reverse chronological order (most recent first)
        for i in range(len(ranges) - 1):
            current_dusk, _ = ranges[i]
            next_dusk, _ = ranges[i + 1]
            assert current_dusk > next_dusk

    def test_timezone_handling(self, config_file):
        """Test proper timezone handling."""
        resolver = TimeResolver(config_file)
        dusk, dawn = resolver.get_night_range()

        # Should be in the configured timezone
        expected_tz = pytz.timezone('America/Denver')
        assert dusk.tzinfo.zone == expected_tz.zone
        assert dawn.tzinfo.zone == expected_tz.zone

    @patch('time_resolver_enhanced.sun')
    def test_astral_calculation_error_fallback(self, mock_sun, config_file):
        """Test fallback to static times when astral calculation fails."""
        # Mock astral to raise an exception
        mock_sun.side_effect = Exception("Astral calculation failed")

        resolver = TimeResolver(config_file)

        # Should still return valid times (fallback)
        dusk, dawn = resolver.get_night_range()
        assert isinstance(dusk, datetime)
        assert isinstance(dawn, datetime)

    def test_buffer_minutes_application(self, config_file):
        """Test that buffer minutes are applied correctly."""
        resolver = TimeResolver(config_file)

        # Get times with and without buffer (modify config temporarily)
        original_buffer = resolver.config['advanced']['buffer_minutes']

        # Test with buffer
        dusk_with_buffer, dawn_with_buffer = resolver.get_night_range()

        # Modify buffer to 0 and test
        resolver.config['advanced']['buffer_minutes'] = 0
        dusk_no_buffer, dawn_no_buffer = resolver.get_night_range()

        # With buffer, dusk should be earlier and dawn should be later
        time_diff = timedelta(minutes=original_buffer)
        expected_dusk_diff = abs((dusk_with_buffer - dusk_no_buffer) - time_diff)
        expected_dawn_diff = abs((dawn_with_buffer - dawn_no_buffer) - time_diff)

        # Allow for small timing differences (within 1 minute)
        assert expected_dusk_diff < timedelta(minutes=1)
        assert expected_dawn_diff < timedelta(minutes=1)

    def test_seasonal_variation(self, config_file):
        """Test that times vary across seasons."""
        resolver = TimeResolver(config_file)

        # Test different seasons
        winter_date = date(2025, 12, 21)  # Winter solstice
        summer_date = date(2025, 6, 21)   # Summer solstice

        winter_dusk, winter_dawn = resolver.get_night_range(winter_date)
        summer_dusk, summer_dawn = resolver.get_night_range(summer_date)

        # Winter nights should be longer
        winter_duration = winter_dawn - winter_dusk
        summer_duration = summer_dawn - summer_dusk

        assert winter_duration > summer_duration

        # Winter dusk should be earlier (in day time, not hour)
        # and winter dawn should be later
        assert winter_dusk.hour < summer_dusk.hour or winter_dusk.hour > 20
        assert winter_dawn.hour > summer_dawn.hour or winter_dawn.hour < 8


@pytest.mark.integration
class TestTimeResolverIntegration:
    """Integration tests requiring actual astral calculations."""

    def test_real_astral_calculation(self, config_file):
        """Test with real astral library calculations."""
        resolver = TimeResolver(config_file)

        # Should work with real coordinates
        dusk, dawn = resolver.get_night_range()

        # Basic sanity checks
        assert dusk.hour >= 18 or dusk.hour <= 6  # Reasonable dusk time
        assert dawn.hour >= 4 and dawn.hour <= 8  # Reasonable dawn time

        # Night should be reasonable duration (4-18 hours)
        duration = dawn - dusk
        assert timedelta(hours=4) <= duration <= timedelta(hours=18)


if __name__ == '__main__':
    # Run with: python -m pytest test_time_resolver_pytest.py -v
    pytest.main([__file__, '-v'])
