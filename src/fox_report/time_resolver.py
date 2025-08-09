#!/usr/bin/env python3
"""
Dusk/Dawn Time Resolver

This module provides utilities for calculating dusk and dawn times using
either the astral library with geographic coordinates or static fallback times.
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Tuple, Optional, Dict, Any
import yaml
import pytz
from astral import LocationInfo
from astral.sun import sun


class TimeResolver:
    """
    Utility class for resolving dusk and dawn times for astronomical observations.

    Uses astral library with lat/lon from config, or falls back to static times.
    """

    def __init__(self, config_file: str = "config/template.yaml"):
        """
        Initialize the TimeResolver with configuration.

        Args:
            config_file: Path to the YAML configuration file
        """
        self.config = self._load_config(config_file)
        self.logger = self._setup_logging()

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError("Configuration file %s not found" % config_file)
        except yaml.YAMLError as e:
            raise ValueError("Error parsing configuration file: %s" % str(e))

    def _setup_logging(self) -> logging.Logger:
        """Set up logging based on configuration."""
        logger = logging.getLogger(__name__)

        verbosity = self.config.get('output', {}).get('verbosity', 1)
        log_levels = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG, 3: logging.DEBUG}
        logger.setLevel(log_levels.get(verbosity, logging.INFO))

        # Create handler if not already exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _get_timezone(self) -> pytz.BaseTzInfo:
        """Get timezone from config or calculate based on coordinates."""
        location_config = self.config.get('location', {})

        # Use configured timezone if available
        if 'timezone' in location_config:
            tz_name = location_config['timezone']
            try:
                return pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                self.logger.warning("Unknown timezone %s, falling back to UTC", tz_name)
                return pytz.UTC

        # Fallback to UTC if no timezone configured
        self.logger.info("No timezone configured, using UTC")
        return pytz.UTC

    def _calculate_astral_times(self, target_date: date) -> Tuple[datetime, datetime]:
        """
        Calculate dusk and dawn times using astral library.

        Args:
            target_date: The date for which to calculate times

        Returns:
            Tuple of (dusk_datetime, dawn_datetime)
        """
        location_config = self.config.get('location', {})

        if not location_config:
            raise ValueError("No location configuration found")

        latitude = location_config.get('latitude')
        longitude = location_config.get('longitude')
        elevation = location_config.get('elevation', 0)

        if latitude is None or longitude is None:
            raise ValueError("Latitude and longitude must be configured")

        self.logger.debug("Using coordinates: lat=%s, lon=%s, elevation=%s",
                         latitude, longitude, elevation)

        # Create location info
        location = LocationInfo(
            timezone=self._get_timezone(),
            latitude=latitude,
            longitude=longitude
        )

        # Get twilight type from advanced settings
        twilight_type = self.config.get('advanced', {}).get('twilight_type', 'nautical')
        buffer_minutes = self.config.get('advanced', {}).get('buffer_minutes', 15)

        self.logger.debug("Using twilight type: %s, buffer: %s minutes",
                         twilight_type, buffer_minutes)

        # Calculate sun times for the target date
        s = sun(location.observer, date=target_date)

        # Select appropriate twilight times based on configuration
        if twilight_type == 'civil':
            dusk = s['dusk']
            dawn = s['dawn']
        elif twilight_type == 'nautical':
            dusk = s['dusk']  # astral uses nautical by default for dusk/dawn
            dawn = s['dawn']
        elif twilight_type == 'astronomical':
            dusk = s['dusk']
            dawn = s['dawn']
        else:
            self.logger.warning("Unknown twilight type %s, using nautical", twilight_type)
            dusk = s['dusk']
            dawn = s['dawn']

        # Apply buffer
        buffer_delta = timedelta(minutes=buffer_minutes)
        dusk_with_buffer = dusk - buffer_delta
        dawn_with_buffer = dawn + buffer_delta

        self.logger.debug("Calculated times - Dusk: %s, Dawn: %s (with %s min buffer)",
                         dusk_with_buffer, dawn_with_buffer, buffer_minutes)

        return dusk_with_buffer, dawn_with_buffer

    def _calculate_static_times(self, target_date: date, timezone: pytz.BaseTzInfo) -> Tuple[datetime, datetime]:
        """
        Calculate times using static configuration.

        Args:
            target_date: The date for which to calculate times
            timezone: Timezone to use for the static times

        Returns:
            Tuple of (dusk_datetime, dawn_datetime)
        """
        static_config = self.config.get('static_times', {})

        if not static_config or not static_config.get('enabled', False):
            raise ValueError("Static times not enabled or configured")

        start_time_str = static_config.get('start_time')
        end_time_str = static_config.get('end_time')

        if not start_time_str or not end_time_str:
            raise ValueError("Static start_time and end_time must be configured")

        # Parse time strings (expected format: "HH:MM")
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError as e:
            raise ValueError("Invalid time format in static_times configuration: %s" % str(e))

        # Create datetime objects for the target date
        dusk_dt = timezone.localize(datetime.combine(target_date, start_time))

        # Handle end time that crosses midnight
        if end_time < start_time:
            # End time is next day
            dawn_dt = timezone.localize(datetime.combine(target_date + timedelta(days=1), end_time))
        else:
            # End time is same day
            dawn_dt = timezone.localize(datetime.combine(target_date, end_time))

        self.logger.debug("Using static times - Dusk: %s, Dawn: %s", dusk_dt, dawn_dt)

        return dusk_dt, dawn_dt

    def get_night_range(self, current_date: Optional[date] = None,
                       lookback_nights: int = 0) -> Tuple[datetime, datetime]:
        """
        Get the dusk-to-dawn datetime range for a specific night.

        Args:
            current_date: Reference date (defaults to today)
            lookback_nights: Number of nights to look back (0 = tonight, 1 = last night, etc.)

        Returns:
            Tuple of (dusk_datetime, dawn_datetime) representing the observation window

        Raises:
            ValueError: If configuration is invalid or incomplete
        """
        if current_date is None:
            current_date = date.today()

        # Calculate target date by going back the specified number of nights
        target_date = current_date - timedelta(days=lookback_nights)

        self.logger.info("Calculating night range for %s (lookback: %s nights)",
                        target_date, lookback_nights)

        timezone = self._get_timezone()

        # Check if static times are enabled
        static_config = self.config.get('static_times', {})
        if static_config and static_config.get('enabled', False):
            self.logger.info("Using static times from configuration")
            return self._calculate_static_times(target_date, timezone)

        # Use astral calculations
        try:
            self.logger.info("Using astral calculations with geographic coordinates")
            return self._calculate_astral_times(target_date)
        except Exception as e:
            self.logger.error("Failed to calculate astral times: %s", str(e))

            # Fallback to static times if available
            if static_config:
                self.logger.warning("Falling back to static times")
                # Temporarily enable static times for fallback
                static_config['enabled'] = True
                return self._calculate_static_times(target_date, timezone)
            else:
                raise ValueError("Unable to calculate times and no static fallback available: %s" % str(e))

    def get_multiple_night_ranges(self, current_date: Optional[date] = None,
                                 nights_count: Optional[int] = None) -> list[Tuple[datetime, datetime]]:
        """
        Get night ranges for multiple consecutive nights.

        Args:
            current_date: Reference date (defaults to today)
            nights_count: Number of nights to include (defaults to config value)

        Returns:
            List of (dusk_datetime, dawn_datetime) tuples, ordered from most recent to oldest
        """
        if current_date is None:
            current_date = date.today()

        if nights_count is None:
            nights_count = self.config.get('nights', {}).get('count', 7)

        night_ranges = []
        for lookback in range(nights_count):
            try:
                night_range = self.get_night_range(current_date, lookback)
                night_ranges.append(night_range)
            except Exception as e:
                self.logger.error("Failed to calculate night range for lookback %s: %s", lookback, str(e))

        return night_ranges


def main():
    """Example usage of the TimeResolver."""
    import argparse

    parser = argparse.ArgumentParser(description='Calculate dusk/dawn times for observations')
    parser.add_argument('--config', default='config/template.yaml',
                       help='Configuration file path')
    parser.add_argument('--date', type=str,
                       help='Target date (YYYY-MM-DD format, defaults to today)')
    parser.add_argument('--lookback', type=int, default=0,
                       help='Number of nights to look back (default: 0)')
    parser.add_argument('--nights', type=int,
                       help='Number of consecutive nights to calculate')

    args = parser.parse_args()

    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")
            return 1

    try:
        resolver = TimeResolver(args.config)

        if args.nights:
            # Calculate multiple nights
            ranges = resolver.get_multiple_night_ranges(target_date, args.nights)
            print("Night observation ranges:")
            for i, (dusk, dawn) in enumerate(ranges):
                lookback = i
                print("  Night %s (lookback %s): %s → %s" % (
                    (target_date or date.today()) - timedelta(days=lookback),
                    lookback, dusk.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    dawn.strftime('%Y-%m-%d %H:%M:%S %Z')
                ))
        else:
            # Calculate single night
            dusk, dawn = resolver.get_night_range(target_date, args.lookback)
            target = (target_date or date.today()) - timedelta(days=args.lookback)
            print("Night range for %s (lookback %s nights):" % (target, args.lookback))
            print("  Dusk:  %s" % dusk.strftime('%Y-%m-%d %H:%M:%S %Z'))
            print("  Dawn:  %s" % dawn.strftime('%Y-%m-%d %H:%M:%S %Z'))
            print("  Duration: %s" % (dawn - dusk))

    except Exception as e:
        print("Error: %s" % str(e))
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
