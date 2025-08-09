#!/usr/bin/env python3
"""
Test script for the database query module.
"""

import logging
from datetime import datetime, timedelta
from fox_report.time_resolver import TimeResolver
from fox_report.database_query import get_fox_events, get_fox_events_with_timeline_segments

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_get_fox_events():
    """Test the get_fox_events function with real time ranges."""
    print("=== Testing get_fox_events Function ===")

    # Initialize time resolver
    resolver = TimeResolver("config_template.yaml")

    # Get dusk/dawn ranges for the last 7 nights
    nights = list(range(7))  # [0, 1, 2, 3, 4, 5, 6] for last 7 nights
    dusk_dawn_ranges = []

    print("\nGenerating time ranges for last 7 nights:")
    for night in nights:
        dusk, dawn = resolver.get_night_range(lookback_nights=night)
        dusk_dawn_ranges.append((dusk, dawn))
        print("  Night %d: %s to %s" % (
            night,
            dusk.strftime('%Y-%m-%d %H:%M'),
            dawn.strftime('%Y-%m-%d %H:%M')
        ))

    # Query fox events
    print("\nQuerying fox events...")
    fox_events = get_fox_events(nights, dusk_dawn_ranges)

    print("\nResults:")
    print("Found %d fox events across %d nights" % (len(fox_events), len(nights)))

    if fox_events:
        print("\nFirst few events:")
        for i, event in enumerate(fox_events[:3]):  # Show first 3 events
            print("  Event %d:" % (i + 1))
            print("    ID: %s" % event['event_id'])
            print("    Camera: %s" % event['camera'])
            print("    Confidence: %.2f" % event['confidence'])
            print("    Duration: %.1f minutes" % event['duration'])
            print("    Start: %s" % event['start_time'])
            print("    Has clip: %s" % event['clip'])
            print("    Night index: %d" % event['night_index'])
            print()
    else:
        print("  No fox events found in the specified time ranges")


def test_get_fox_events_with_timeline():
    """Test the enhanced function with timeline segments."""
    print("\n=== Testing get_fox_events_with_timeline_segments Function ===")

    # Initialize time resolver
    resolver = TimeResolver("config_template.yaml")

    # Get just the last 2 nights for this test
    nights = [0, 1]  # Last 2 nights
    dusk_dawn_ranges = []

    for night in nights:
        dusk, dawn = resolver.get_night_range(lookback_nights=night)
        dusk_dawn_ranges.append((dusk, dawn))

    # Query fox events with timeline segments
    fox_events = get_fox_events_with_timeline_segments(nights, dusk_dawn_ranges, include_timeline=True)

    print("Found %d fox events with timeline data" % len(fox_events))

    if fox_events:
        for event in fox_events[:2]:  # Show first 2 events
            print("\nEvent %s:" % event['event_id'])
            print("  Timeline segments: %d" % len(event.get('timeline_segments', [])))


if __name__ == "__main__":
    test_get_fox_events()
    test_get_fox_events_with_timeline()
