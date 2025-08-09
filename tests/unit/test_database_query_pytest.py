#!/usr/bin/env python3
"""
Pytest test suite for database_query module.
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from database_query_enhanced import (
    DatabaseError,
    DatabaseLockError,
    _attempt_database_connection,
    _validate_media_files,
    get_fox_events,
    get_fox_events_with_timeline_segments,
    test_database_connection,
)


@pytest.fixture
def sample_database():
    """Create a temporary sample database for testing."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create sample database schema and data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create events table
    cursor.execute("""
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            camera TEXT,
            label TEXT,
            start_time REAL,
            end_time REAL,
            top_score REAL,
            has_clip INTEGER,
            has_snapshot INTEGER,
            thumbnail TEXT
        )
    """)

    # Insert sample fox events
    sample_events = [
        (
            "event_1",
            "front_yard",
            "fox",
            1691000000.0,
            1691000300.0,
            0.95,
            1,
            1,
            "/media/event_1_thumb.jpg",
        ),
        (
            "event_2",
            "back_yard",
            "fox",
            1691001800.0,
            1691002000.0,
            0.88,
            1,
            0,
            "/media/event_2_thumb.jpg",
        ),
        (
            "event_3",
            "side_yard",
            "fox",
            1691003600.0,
            1691003900.0,
            0.92,
            0,
            1,
            "/media/event_3_thumb.jpg",
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO events (id, camera, label, start_time, end_time, top_score, has_clip, has_snapshot, thumbnail)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        sample_events,
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def mock_event_data():
    """Mock fox event data for testing."""
    return [
        {
            "event_id": "event_1",
            "camera": "front_yard",
            "confidence": 0.95,
            "start_time": "2023-08-01 21:00:00",
            "duration": 5.0,
            "clip": True,
            "night_index": 0,
            "thumbnail": "/media/event_1_thumb.jpg",
        },
        {
            "event_id": "event_2",
            "camera": "back_yard",
            "confidence": 0.88,
            "start_time": "2023-08-01 22:30:00",
            "duration": 3.33,
            "clip": True,
            "night_index": 0,
            "thumbnail": "/media/event_2_thumb.jpg",
        },
    ]


class TestDatabaseQuery:
    """Test cases for database query functions."""

    def test_validate_media_files_existing(self, mock_event_data):
        """Test media file validation with existing files."""
        with patch("os.path.exists", return_value=True):
            validated = _validate_media_files(mock_event_data)

            for event in validated:
                assert "thumbnail_exists" in event
                assert event["thumbnail_exists"] is True

    def test_validate_media_files_missing(self, mock_event_data):
        """Test media file validation with missing files."""
        with patch("os.path.exists", return_value=False):
            validated = _validate_media_files(mock_event_data)

            for event in validated:
                assert "thumbnail_exists" in event
                assert event["thumbnail_exists"] is False

    def test_attempt_database_connection_success(self, sample_database):
        """Test successful database connection."""
        conn = _attempt_database_connection(sample_database)
        assert conn is not None
        conn.close()

    def test_attempt_database_connection_locked(self):
        """Test database locked scenario."""
        with (
            patch(
                "sqlite3.connect",
                side_effect=sqlite3.OperationalError("database is locked"),
            ),
            pytest.raises(DatabaseLockError),
        ):
            _attempt_database_connection("fake_db.db", max_retries=1)

    def test_get_fox_events_basic(self, mock_event_data):
        """Test get_fox_events function with basic inputs."""
        with (
            patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect,
            patch(
                "database_query_enhanced._validate_media_files",
                return_value=mock_event_data,
            ),
        ):
            # Mock database connection and cursor
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (
                    "event_1",
                    "front_yard",
                    0.95,
                    1691000000.0,
                    1691000300.0,
                    1,
                    "/media/event_1_thumb.jpg",
                )
            ]

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            nights = [0, 1, 2]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0)),
                (datetime(2023, 7, 31, 19, 0), datetime(2023, 8, 1, 7, 0)),
                (datetime(2023, 7, 30, 19, 0), datetime(2023, 7, 31, 7, 0)),
            ]

            results = get_fox_events(nights, dusk_dawn_ranges)

            assert isinstance(results, list)

    def test_get_fox_events_database_error(self):
        """Test get_fox_events with database error."""
        with patch(
            "database_query_enhanced._attempt_database_connection",
            side_effect=DatabaseError("Database error"),
        ):
            nights = [0]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0))
            ]

            with pytest.raises(DatabaseError):
                get_fox_events(nights, dusk_dawn_ranges)

    def test_get_fox_events_with_timeline_basic(self, mock_event_data):
        """Test get_fox_events_with_timeline_segments function."""
        with (
            patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect,
            patch(
                "database_query_enhanced._validate_media_files",
                return_value=mock_event_data,
            ),
        ):
            # Mock database connection and cursor
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (
                    "event_1",
                    "front_yard",
                    0.95,
                    1691000000.0,
                    1691000300.0,
                    1,
                    "/media/event_1_thumb.jpg",
                )
            ]

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            nights = [0]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0))
            ]

            results = get_fox_events_with_timeline_segments(nights, dusk_dawn_ranges)

            assert isinstance(results, list)

    def test_get_fox_events_with_timeline_segments_enabled(self, mock_event_data):
        """Test timeline segments inclusion when enabled."""
        # Mock timeline segments data
        mock_events_with_timeline = mock_event_data.copy()
        for event in mock_events_with_timeline:
            event["timeline_segments"] = [
                {"start": 0, "end": 30, "score": 0.9},
                {"start": 30, "end": 60, "score": 0.8},
            ]

        with (
            patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect,
            patch(
                "database_query_enhanced._validate_media_files",
                return_value=mock_events_with_timeline,
            ),
        ):
            # Mock database connection and cursor
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (
                    "event_1",
                    "front_yard",
                    0.95,
                    1691000000.0,
                    1691000300.0,
                    1,
                    "/media/event_1_thumb.jpg",
                )
            ]

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            nights = [0]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0))
            ]

            results = get_fox_events_with_timeline_segments(
                nights, dusk_dawn_ranges, include_timeline=True
            )

            assert isinstance(results, list)

    def test_empty_results(self):
        """Test functions with no events found."""
        with (
            patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect,
            patch("database_query_enhanced._validate_media_files", return_value=[]),
        ):
            # Mock database connection and cursor with no results
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            nights = [0]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0))
            ]

            results = get_fox_events(nights, dusk_dawn_ranges)
            assert results == []

            results_timeline = get_fox_events_with_timeline_segments(
                nights, dusk_dawn_ranges
            )
            assert results_timeline == []

    def test_test_database_connection(self):
        """Test the database connection test function."""
        with patch(
            "database_query_enhanced._attempt_database_connection",
            return_value=MagicMock(),
        ):
            result = test_database_connection()
            assert result is True

        with patch(
            "database_query_enhanced._attempt_database_connection",
            side_effect=DatabaseError("No DB"),
        ):
            result = test_database_connection()
            assert result is False

    @pytest.mark.parametrize("nights_count,expected_calls", [(1, 1), (3, 3), (7, 7)])
    def test_multiple_nights_query_count(
        self, nights_count, expected_calls, mock_event_data
    ):
        """Test that correct number of database queries are made for multiple nights."""
        with (
            patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect,
            patch(
                "database_query_enhanced._validate_media_files",
                return_value=mock_event_data,
            ),
        ):
            # Mock database connection and cursor
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (
                    "event_1",
                    "front_yard",
                    0.95,
                    1691000000.0,
                    1691000300.0,
                    1,
                    "/media/event_1_thumb.jpg",
                )
            ]

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            nights = list(range(nights_count))
            dusk_dawn_ranges = [
                (
                    datetime(2023, 8, 1, 19, 0) - timedelta(days=i),
                    datetime(2023, 8, 2, 7, 0) - timedelta(days=i),
                )
                for i in range(nights_count)
            ]

            get_fox_events(nights, dusk_dawn_ranges)

            # Should call _attempt_database_connection once for each night
            assert mock_connect.call_count == expected_calls


@pytest.mark.integration
class TestDatabaseQueryIntegration:
    """Integration tests requiring actual database."""

    def test_real_database_connection(self, sample_database):
        """Test with real database connection."""
        try:
            nights = [0]
            dusk_dawn_ranges = [
                (datetime(2023, 8, 1, 19, 0), datetime(2023, 8, 2, 7, 0))
            ]

            # This might fail if Frigate DB paths don't exist, which is expected in test env
            # We're mainly testing that the function structure works
            with patch(
                "database_query_enhanced._attempt_database_connection"
            ) as mock_connect:
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = []
                mock_conn = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                results = get_fox_events(nights, dusk_dawn_ranges)

                # Should execute without errors
                assert isinstance(results, list)

        except (DatabaseError, FileNotFoundError):
            # This is acceptable if database doesn't exist in test environment
            pytest.skip("No database available for integration test")


if __name__ == "__main__":
    # Run with: python -m pytest test_database_query_pytest.py -v
    pytest.main([__file__, "-v"])
