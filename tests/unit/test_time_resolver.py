#!/usr/bin/env python3
"""
Test script for the TimeResolver utility.

This script demonstrates various use cases and validates the functionality.
"""

from datetime import date, timedelta

from fox_report.time_resolver import TimeResolver


def test_basic_functionality():
    """Test basic TimeResolver functionality."""
    print("=== Testing Basic Functionality ===")

    resolver = TimeResolver("config_template.yaml")

    # Test current night
    print("\n1. Current night (tonight):")
    dusk, dawn = resolver.get_night_range()
    print("   Dusk: {}".format(dusk.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Dawn: {}".format(dawn.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Duration: %s" % (dawn - dusk))

    # Test lookback nights
    print("\n2. Last night (lookback 1):")
    dusk, dawn = resolver.get_night_range(lookback_nights=1)
    print("   Dusk: {}".format(dusk.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Dawn: {}".format(dawn.strftime("%Y-%m-%d %H:%M:%S %Z")))

    # Test specific date
    print("\n3. Specific date (2025-07-01):")
    target_date = date(2025, 7, 1)
    dusk, dawn = resolver.get_night_range(target_date)
    print("   Dusk: {}".format(dusk.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Dawn: {}".format(dawn.strftime("%Y-%m-%d %H:%M:%S %Z")))


def test_multiple_nights():
    """Test multiple nights functionality."""
    print("\n=== Testing Multiple Nights ===")

    resolver = TimeResolver("config_template.yaml")

    # Get 5 nights
    ranges = resolver.get_multiple_night_ranges(nights_count=5)

    print("\nLast 5 nights:")
    for i, (dusk, dawn) in enumerate(ranges):
        night_date = date.today() - timedelta(days=i)
        print(
            "   Night {}: {} → {}".format(
                night_date.strftime("%Y-%m-%d"),
                dusk.strftime("%H:%M:%S %Z"),
                dawn.strftime("%H:%M:%S %Z"),
            )
        )


def test_static_times():
    """Test static times configuration."""
    print("\n=== Testing Static Times ===")

    resolver = TimeResolver("test_static_config.yaml")

    # Test with static times
    dusk, dawn = resolver.get_night_range()
    print("\nUsing static times:")
    print("   Dusk: {}".format(dusk.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Dawn: {}".format(dawn.strftime("%Y-%m-%d %H:%M:%S %Z")))
    print("   Duration: %s" % (dawn - dusk))


def test_different_dates():
    """Test functionality across different seasons."""
    print("\n=== Testing Different Seasons ===")

    resolver = TimeResolver("config_template.yaml")

    test_dates = [
        date(2025, 1, 1),  # Winter
        date(2025, 4, 1),  # Spring
        date(2025, 7, 1),  # Summer
        date(2025, 10, 1),  # Fall
    ]

    for test_date in test_dates:
        dusk, dawn = resolver.get_night_range(test_date)
        duration = dawn - dusk
        print(
            "\n{} ({}):".format(
                test_date.strftime("%Y-%m-%d"), test_date.strftime("%B")
            )
        )
        print("   Dusk: {}".format(dusk.strftime("%H:%M:%S %Z")))
        print("   Dawn: {}".format(dawn.strftime("%H:%M:%S %Z")))
        print(f"   Night duration: {duration}")


def main():
    """Run all tests."""
    print("TimeResolver Test Suite")
    print("======================")

    try:
        test_basic_functionality()

        # Import timedelta here since we need it for multiple nights test
        from datetime import timedelta

        globals()["timedelta"] = timedelta

        test_multiple_nights()
        test_static_times()
        test_different_dates()

        print("\n=== All Tests Completed Successfully ===")

    except Exception as e:
        print("\n=== Test Failed ===")
        print(f"Error: {e!s}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
