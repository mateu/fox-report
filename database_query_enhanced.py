#!/usr/bin/env python3
"""
Database Query Module - Enhanced with Robust Error Handling

This module provides functions for querying the Frigate database to retrieve
fox detection events within specified time ranges. Now includes comprehensive
error handling for database locks, connectivity issues, and missing media files.
"""

import sqlite3
import logging
import os
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Configure logging using lazy formatting approach
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class DatabaseLockError(DatabaseError):
    """Exception raised when database is locked or unavailable."""
    pass


def _validate_media_files(events: List[Dict]) -> List[Dict]:
    """
    Validate that media files referenced in events actually exist.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        List of events with validated media file status
    """
    validated_events = []
    
    for event in events:
        # Check thumbnail file
        thumbnail_path = event.get('thumbnail')
        if thumbnail_path:
            event['thumbnail_exists'] = os.path.exists(thumbnail_path)
            if not event['thumbnail_exists']:
                logger.warning("Missing thumbnail file for event %s: %s", 
                             event.get('event_id', 'unknown'), thumbnail_path)
        else:
            event['thumbnail_exists'] = False
            
        # For clip availability, we trust the database flag but could add file check
        clip_available = event.get('clip', False)
        event['clip_validated'] = clip_available
        
        # Log missing media but don't exclude the event
        if not event['thumbnail_exists'] and not clip_available:
            logger.info("Event %s has no available media files", 
                       event.get('event_id', 'unknown'))
            
        validated_events.append(event)
    
    return validated_events


def _attempt_database_connection(db_path: str, max_retries: int = 3, 
                               timeout: int = 30) -> sqlite3.Connection:
    """
    Attempt to connect to database with retries and proper timeout handling.
    
    Args:
        db_path: Path to SQLite database
        max_retries: Maximum number of connection attempts
        timeout: Timeout in seconds for each connection attempt
        
    Returns:
        SQLite connection object
        
    Raises:
        DatabaseLockError: If database is locked after retries
        DatabaseError: If database is inaccessible or corrupted
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.debug("Database connection attempt %d of %d", attempt + 1, max_retries)
            
            # Connect with timeout and enable WAL mode for better concurrency
            conn = sqlite3.connect(
                db_path,
                timeout=timeout,
                check_same_thread=False
            )
            
            # Set pragmas for better error handling and performance
            conn.execute("PRAGMA busy_timeout = %d" % (timeout * 1000))
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Test the connection with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            logger.debug("Database connection successful on attempt %d", attempt + 1)
            return conn
            
        except sqlite3.OperationalError as e:
            last_error = e
            error_msg = str(e).lower()
            
            if "database is locked" in error_msg or "disk i/o error" in error_msg:
                logger.warning("Database locked on attempt %d: %s", attempt + 1, str(e))
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.info("Waiting %d seconds before retry", wait_time)
                    time.sleep(wait_time)
                    continue
                else:
                    raise DatabaseLockError("Database remains locked after %d attempts: %s" % 
                                          (max_retries, str(e)))
            else:
                # Non-lock error, don't retry
                raise DatabaseError("Database connection failed: %s" % str(e))
                
        except Exception as e:
            last_error = e
            logger.error("Unexpected error connecting to database: %s", str(e))
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                raise DatabaseError("Failed to connect after %d attempts: %s" % 
                                  (max_retries, str(e)))
    
    # If we get here, all retries failed
    raise DatabaseError("Database connection failed after %d attempts. Last error: %s" % 
                       (max_retries, str(last_error)))


def get_fox_events(nights: List[int], dusk_dawn_ranges: List[Tuple[datetime, datetime]]) -> List[Dict]:
    """
    Retrieve fox detection events from the Frigate database for specified nights.
    Enhanced with robust error handling for database locks, empty results, and missing media.
    
    Args:
        nights: List of night identifiers/indices
        dusk_dawn_ranges: List of (dusk_datetime, dawn_datetime) tuples
        
    Returns:
        List of dictionaries containing fox event data with keys:
        - confidence: Detection confidence score (0.0-1.0)
        - camera: Camera name that detected the event
        - duration: Event duration in minutes
        - thumbnail: Path to thumbnail image
        - thumbnail_exists: Boolean indicating if thumbnail file exists
        - clip: Boolean indicating if video clip is available
        - clip_validated: Boolean indicating if clip status was validated
        - start_time: Event start timestamp (readable format)
        - end_time: Event end timestamp (readable format)
        - event_id: Unique event identifier
        
    Raises:
        DatabaseLockError: If database is locked and cannot be accessed
        DatabaseError: If database is corrupted or inaccessible
        ValueError: If input parameters are invalid
    """
    # Input validation
    if not nights:
        logger.warning("No nights specified for query")
        return []
        
    if not dusk_dawn_ranges:
        logger.warning("No dusk/dawn ranges specified for query")
        return []
        
    if len(nights) != len(dusk_dawn_ranges):
        raise ValueError("Number of nights (%d) must match number of dusk/dawn ranges (%d)" % 
                        (len(nights), len(dusk_dawn_ranges)))
    
    # Path to Frigate database with fallback options
    possible_db_paths = [
        '/home/hunter/frigate/config/frigate.db',
        '/opt/frigate/config/frigate.db',
        './frigate.db',
        os.path.expanduser('~/frigate/config/frigate.db')
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        raise DatabaseError("Frigate database not found. Searched paths: %s" % 
                          ', '.join(possible_db_paths))
    
    logger.info("Connecting to Frigate database at %s", db_path)
    
    conn = None
    try:
        # Attempt database connection with retries
        conn = _attempt_database_connection(db_path)
        cursor = conn.cursor()
        
        # Validate database schema
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event'")
            if not cursor.fetchone():
                raise DatabaseError("Database missing required 'event' table")
        except sqlite3.Error as e:
            raise DatabaseError("Failed to validate database schema: %s" % str(e))
        
        # Define the SQL query to fetch fox events
        query = """
        SELECT 
            id,
            top_score,
            camera,
            datetime(start_time, 'unixepoch') as start_time_readable,
            datetime(end_time, 'unixepoch') as end_time_readable,
            CASE 
                WHEN end_time IS NOT NULL AND start_time IS NOT NULL 
                THEN (end_time - start_time) / 60.0 
                ELSE 0.0 
            END AS duration_minutes,
            thumbnail,
            has_clip,
            zones,
            sub_label,
            area,
            box
        FROM event 
        WHERE label='fox' 
        AND start_time BETWEEN strftime('%s', ?) AND strftime('%s', ?)
        ORDER BY start_time DESC
        """
        
        # Prepare the results list
        results = []
        
        logger.info("Querying fox events for %d night ranges", len(dusk_dawn_ranges))
        
        # Execute the query for each dusk/dawn range
        for i, (dusk, dawn) in enumerate(dusk_dawn_ranges):
            try:
                logger.debug("Querying night %d: %s to %s", 
                            nights[i] if i < len(nights) else i, 
                            dusk.strftime('%Y-%m-%d %H:%M:%S'), 
                            dawn.strftime('%Y-%m-%d %H:%M:%S'))
                
                cursor.execute(query, (dusk.isoformat(), dawn.isoformat()))
                rows = cursor.fetchall()
                
                logger.debug("Found %d fox events for night %d", len(rows), 
                            nights[i] if i < len(nights) else i)
                
                # Process each row with error handling
                for row in rows:
                    try:
                        event = {
                            'event_id': row[0],
                            'confidence': float(row[1]) if row[1] is not None else 0.0,
                            'camera': row[2] if row[2] else 'unknown',
                            'start_time': row[3] if row[3] else 'unknown',
                            'end_time': row[4] if row[4] else 'unknown',
                            'duration': float(row[5]) if row[5] is not None else 0.0,
                            'thumbnail': row[6],
                            'clip': bool(row[7]) if row[7] is not None else False,
                            'zones': row[8],  # JSON data
                            'sub_label': row[9],
                            'area': row[10] if row[10] is not None else 0,
                            'box': row[11],  # JSON data for bounding box
                            'night_index': nights[i] if i < len(nights) else i
                        }
                        results.append(event)
                    except (ValueError, TypeError) as e:
                        logger.warning("Skipping malformed event row: %s", str(e))
                        continue
                        
            except sqlite3.Error as e:
                logger.error("Error querying night %d: %s", i, str(e))
                # Continue with other nights rather than failing completely
                continue
        
        if not results:
            logger.info("No fox events found in database for specified time ranges")
        else:
            logger.info("Retrieved %d total fox events across all nights", len(results))
            
            # Validate media files for all events
            results = _validate_media_files(results)
        
        return results
        
    except DatabaseLockError:
        # Re-raise database lock errors as-is
        raise
    except DatabaseError:
        # Re-raise database errors as-is
        raise
    except sqlite3.Error as e:
        logger.error("Database error occurred: %s", str(e))
        raise DatabaseError("SQLite error: %s" % str(e))
    except Exception as e:
        logger.error("Unexpected error occurred: %s", str(e))
        raise DatabaseError("Unexpected error: %s" % str(e))
    finally:
        # Ensure database connection is closed
        if conn:
            try:
                conn.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning("Error closing database connection: %s", str(e))


def get_fox_events_with_timeline_segments(nights: List[int], 
                                        dusk_dawn_ranges: List[Tuple[datetime, datetime]],
                                        include_timeline: bool = True) -> List[Dict]:
    """
    Enhanced version that can optionally attach timeline segments if useful.
    Includes comprehensive error handling for missing timeline table and data corruption.
    
    Args:
        nights: List of night identifiers/indices
        dusk_dawn_ranges: List of (dusk_datetime, dawn_datetime) tuples
        include_timeline: Whether to include timeline segment data
        
    Returns:
        List of dictionaries containing fox event data with optional timeline segments
    """
    # Get basic fox events with enhanced error handling
    try:
        events = get_fox_events(nights, dusk_dawn_ranges)
    except Exception as e:
        logger.error("Failed to retrieve basic fox events: %s", str(e))
        raise
    
    if not include_timeline or not events:
        return events
    
    logger.info("Attaching timeline segments to %d fox events", len(events))
    
    # Find database path
    possible_db_paths = [
        '/home/hunter/frigate/config/frigate.db',
        '/opt/frigate/config/frigate.db',
        './frigate.db',
        os.path.expanduser('~/frigate/config/frigate.db')
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        logger.warning("Database not found for timeline segments, continuing without them")
        for event in events:
            event['timeline_segments'] = []
        return events
    
    conn = None
    try:
        conn = _attempt_database_connection(db_path)
        cursor = conn.cursor()
        
        # Check if timeline table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='timeline'
        """)
        has_timeline_table = cursor.fetchone() is not None
        
        if not has_timeline_table:
            logger.warning("Timeline table not found in database")
            for event in events:
                event['timeline_segments'] = []
            return events
        
        # Process timeline segments for each event
        for event in events:
            try:
                # Query timeline segments for this event's time range
                segment_query = """
                SELECT timestamp, camera, source_id, class_type, data
                FROM timeline 
                WHERE camera = ? 
                AND timestamp BETWEEN strftime('%s', ?) AND strftime('%s', ?)
                ORDER BY timestamp
                """
                
                cursor.execute(segment_query, (
                    event['camera'],
                    event['start_time'],
                    event['end_time']
                ))
                
                segments = cursor.fetchall()
                event['timeline_segments'] = []
                
                for seg in segments:
                    try:
                        segment_data = {
                            'timestamp': seg[0] if seg[0] else 'unknown',
                            'camera': seg[1] if seg[1] else 'unknown',
                            'source_id': seg[2] if seg[2] else 'unknown',
                            'class_type': seg[3] if seg[3] else 'unknown',
                            'data': seg[4]  # May be JSON or None
                        }
                        event['timeline_segments'].append(segment_data)
                    except (ValueError, TypeError) as e:
                        logger.warning("Skipping malformed timeline segment: %s", str(e))
                        continue
                
                logger.debug("Added %d timeline segments to event %s", 
                           len(event['timeline_segments']), event['event_id'])
                           
            except sqlite3.Error as e:
                logger.warning("Error querying timeline for event %s: %s", 
                             event['event_id'], str(e))
                event['timeline_segments'] = []
                continue
                
    except Exception as e:
        logger.error("Error querying timeline segments: %s", str(e))
        # Continue without timeline segments rather than failing
        for event in events:
            event['timeline_segments'] = []
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning("Error closing database connection: %s", str(e))
    
    return events


def test_database_connection() -> bool:
    """
    Test the connection to the Frigate database with comprehensive error handling.
    
    Returns:
        True if connection successful, False otherwise
    """
    possible_db_paths = [
        '/home/hunter/frigate/config/frigate.db',
        '/opt/frigate/config/frigate.db',
        './frigate.db',
        os.path.expanduser('~/frigate/config/frigate.db')
    ]
    
    for db_path in possible_db_paths:
        if not os.path.exists(db_path):
            continue
            
        logger.info("Testing database connection to %s", db_path)
        
        try:
            conn = _attempt_database_connection(db_path, max_retries=1)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT COUNT(*) FROM event WHERE label='fox'")
            fox_count = cursor.fetchone()[0]
            
            # Test database integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            conn.close()
            
            if integrity_result.lower() == 'ok':
                logger.info("Database connection successful. Found %d fox events total", fox_count)
                return True
            else:
                logger.error("Database integrity check failed: %s", integrity_result)
                return False
                
        except DatabaseLockError:
            logger.error("Database is locked and cannot be accessed")
            return False
        except DatabaseError as e:
            logger.error("Database error: %s", str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error testing database: %s", str(e))
            return False
    
    logger.error("No accessible Frigate database found in any of the expected locations")
    return False


if __name__ == "__main__":
    # Simple test when run directly
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Testing enhanced database connection...")
    if test_database_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
        
    # Test empty result handling
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        future_range = [(now + timedelta(days=365), now + timedelta(days=366))]
        
        print("\nTesting empty result handling...")
        events = get_fox_events([999], future_range)
        print("✓ Empty result handling successful (%d events returned)" % len(events))
        
    except Exception as e:
        print("✗ Error testing empty results: %s" % str(e))
