#!/usr/bin/env python3
"""
Database Query Module

This module provides functions for querying the Frigate database to retrieve
fox detection events within specified time ranges.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text

from .config import settings

# Configure logging using lazy formatting approach
logger = logging.getLogger(__name__)


def get_fox_events(
    nights: list[int], dusk_dawn_ranges: list[tuple[datetime, datetime]]
) -> list[dict]:
    """
    Retrieve fox detection events from the Frigate database for specified nights.

    Args:
        nights: List of night identifiers/indices
        dusk_dawn_ranges: List of (dusk_datetime, dawn_datetime) tuples

    Returns:
        List of dictionaries containing fox event data with keys:
        - confidence: Detection confidence score (0.0-1.0)
        - camera: Camera name that detected the event
        - duration: Event duration in seconds
        - thumbnail: Path to thumbnail image
        - clip: Boolean indicating if video clip is available
        - start_time: Event start timestamp (readable format)
        - end_time: Event end timestamp (readable format)
        - start_timestamp: Raw Unix timestamp for start time
        - end_timestamp: Raw Unix timestamp for end time
        - event_id: Unique event identifier
    """
    # Use SQLAlchemy 2.0 Engine (low-touch; keep raw SQL strings)
    engine = create_engine(settings.db_url, future=True)
    logger.info("Connecting to Frigate database at %s", settings.db_url)

    # Define the SQL query to fetch fox events
    # Note: Frigate stores timestamps as Unix epoch floats
    # Extract confidence from JSON data field
    query = """
        SELECT
            id,
            json_extract(data, '$.score') as confidence_score,
            camera,
            datetime(start_time, 'unixepoch') as start_time_readable,
            datetime(end_time, 'unixepoch') as end_time_readable,
            CASE
                WHEN end_time IS NOT NULL AND start_time IS NOT NULL
                THEN (end_time - start_time)
                ELSE 0.0
            END AS duration_seconds,
            thumbnail,
            has_clip,
            zones,
            sub_label,
            area,
            box,
            start_time as start_timestamp,
            end_time as end_timestamp
        FROM event
        WHERE label='fox'
        AND start_time BETWEEN strftime('%s', :dusk) AND strftime('%s', :dawn)
        ORDER BY start_time DESC
    """

    # Prepare the results list
    results: list[dict[str, Any]] = []

    logger.info("Querying fox events for %d night ranges", len(dusk_dawn_ranges))

    with engine.connect() as conn:
        # Execute the query for each dusk/dawn range
        for i, (dusk, dawn) in enumerate(dusk_dawn_ranges):
            logger.debug(
                "Querying night %d: %s to %s",
                nights[i] if i < len(nights) else i,
                dusk.strftime("%Y-%m-%d %H:%M:%S"),
                dawn.strftime("%Y-%m-%d %H:%M:%S"),
            )

            rows = conn.execute(
                text(query),
                {"dusk": dusk.isoformat(), "dawn": dawn.isoformat()},
            ).all()

            logger.debug(
                "Found %d fox events for night %d",
                len(rows),
                nights[i] if i < len(nights) else i,
            )

            # Process each row
            for row in rows:
                # row is a Row object; access by position
                event = {
                    "event_id": row[0],
                    "confidence": float(row[1]) if row[1] is not None else 0.0,
                    "camera": row[2],
                    "start_time": row[3],
                    "end_time": row[4],
                    "duration_seconds": float(row[5]) if row[5] is not None else 0.0,
                    "thumbnail": row[6],
                    "clip": bool(row[7]),
                    "zones": row[8],  # JSON data
                    "sub_label": row[9],
                    "area": row[10],
                    "box": row[11],  # JSON data for bounding box
                    "start_timestamp": float(row[12]) if row[12] is not None else 0.0,
                    "end_timestamp": float(row[13]) if row[13] is not None else 0.0,
                    "night_index": nights[i] if i < len(nights) else i,
                }
                results.append(event)

    logger.info("Retrieved %d total fox events across all nights", len(results))

    return results


def get_fox_events_with_timeline_segments(
    nights: list[int],
    dusk_dawn_ranges: list[tuple[datetime, datetime]],
    include_timeline: bool = True,
) -> list[dict]:
    """
    Enhanced version that can optionally attach timeline segments if useful.

    Args:
        nights: List of night identifiers/indices
        dusk_dawn_ranges: List of (dusk_datetime, dawn_datetime) tuples
        include_timeline: Whether to include timeline segment data

    Returns:
        List of dictionaries containing fox event data with optional timeline segments
    """
    # Get basic fox events
    events = get_fox_events(nights, dusk_dawn_ranges)

    if not include_timeline or not events:
        return events

    logger.info("Attaching timeline segments to %d fox events", len(events))

    engine = create_engine(settings.db_url, future=True)

    # Query for timeline segments (if the table exists)
    timeline_exists_sql = text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='timeline'"
    )

    with engine.connect() as conn:
        has_timeline_table = conn.execute(timeline_exists_sql).first() is not None

        if has_timeline_table:
            for event in events:
                # Query timeline segments for this event's time range
                segment_query = text(
                    """
                    SELECT timestamp, camera, source_id, class_type, data
                    FROM timeline
                    WHERE camera = :camera
                    AND timestamp BETWEEN strftime('%s', :start_time) AND strftime('%s', :end_time)
                    ORDER BY timestamp
                    """
                )

                segments = conn.execute(
                    segment_query,
                    {
                        "camera": event["camera"],
                        "start_time": event["start_time"],
                        "end_time": event["end_time"],
                    },
                ).all()

                event["timeline_segments"] = [
                    {
                        "timestamp": seg[0],
                        "camera": seg[1],
                        "source_id": seg[2],
                        "class_type": seg[3],
                        "data": seg[4],
                    }
                    for seg in segments
                ]

                logger.debug(
                    "Added %d timeline segments to event %s",
                    len(segments),
                    event["event_id"],
                )
        else:
            logger.warning("Timeline table not found in database")
            for event in events:
                event["timeline_segments"] = []

    return events


def test_database_connection() -> bool:
    """
    Test the connection to the Frigate database.

    Returns:
        True if connection successful, False otherwise
    """
    engine = create_engine(settings.db_url, future=True)

    try:
        with engine.connect() as conn:
            fox_count = conn.execute(
                text("SELECT COUNT(*) FROM event WHERE label='fox'")
            ).scalar_one()
            logger.info(
                "Database connection successful. Found %d fox events total", fox_count
            )
            return True
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return False


if __name__ == "__main__":
    # Simple test when run directly
    logging.basicConfig(level=logging.INFO)

    print("Testing database connection...")
    if test_database_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
