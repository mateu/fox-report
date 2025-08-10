#!/usr/bin/env python3
"""
Fox Detection Report Generator

This module transforms event dictionaries into structured JSON with metadata,
per-camera grouping, and totals. Also generates human-readable Markdown
section for email body.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import settings
from .database_query import get_fox_events
from .time_resolver import TimeResolver

# Configure logging using lazy formatting approach
logger = logging.getLogger(__name__)


def generate_timeline_url(
    camera: str, start_timestamp: float, end_timestamp: float, padding: int = 5
) -> str:
    """
    Generate a Frigate timeline URL with padding.

    Args:
        camera: Camera name (e.g., 'court' or 'pano')
        start_timestamp: Unix timestamp for event start
        end_timestamp: Unix timestamp for event end
        padding: Seconds to pad on either side (default: 5)

    Returns:
        Timeline URL string
    """
    # Add padding to timestamps
    padded_start = int(start_timestamp - padding)
    padded_end = (
        int(end_timestamp + padding)
        if end_timestamp > 0
        else int(start_timestamp + padding + 10)
    )

    # Generate the URL
    return f"https://frig.mso.mt/api/{camera}/start/{padded_start}/end/{padded_end}/clip.mp4"


# Mountain Time timezone
MOUNTAIN_TZ = ZoneInfo("America/Denver")


def utc_to_mountain_time(utc_datetime_str: str) -> datetime:
    """
    Convert UTC datetime string to Mountain Time datetime object.

    Args:
        utc_datetime_str: ISO format UTC datetime string

    Returns:
        datetime object converted to Mountain Time
    """
    # Parse the UTC datetime and add UTC timezone info
    utc_dt = datetime.fromisoformat(utc_datetime_str)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to Mountain Time
    return utc_dt.astimezone(MOUNTAIN_TZ)


def calculate_night_duration(dusk_str: str, dawn_str: str) -> tuple[float, str]:
    """
    Calculate duration between dusk and dawn.

    Args:
        dusk_str: ISO format dusk datetime string
        dawn_str: ISO format dawn datetime string

    Returns:
        Tuple of (duration_hours, formatted_duration_string)
    """
    dusk = datetime.fromisoformat(dusk_str.replace("Z", "+00:00"))
    dawn = datetime.fromisoformat(dawn_str.replace("Z", "+00:00"))

    duration = dawn - dusk
    duration_hours = duration.total_seconds() / 3600

    # Format as hours and minutes
    hours = int(duration_hours)
    minutes = int((duration_hours - hours) * 60)

    duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    return duration_hours, duration_str


def count_events_per_night(events: list[dict]) -> dict[int, int]:
    """
    Count events per night using the night_index field.

    Args:
        events: List of event dictionaries with night_index field

    Returns:
        Dictionary mapping night_index to event count
    """
    night_counts = {}
    for event in events:
        night_idx = event.get("night_index", 0)
        night_counts[night_idx] = night_counts.get(night_idx, 0) + 1

    return night_counts


def generate_fox_report(
    nights: list[int],
    dusk_dawn_ranges: list[tuple[datetime, datetime]],
    output_file: str | None = None,
) -> tuple[dict, str]:
    """
    Generate a comprehensive fox detection report.

    Args:
        nights: List of night identifiers/indices
        dusk_dawn_ranges: List of (dusk_datetime, dawn_datetime) tuples
        output_file: Optional custom output file path

    Returns:
        Tuple of (report_dict, markdown_string)
    """
    logger.info("Generating fox detection report for %d nights", len(nights))

    # Fetch events from database
    events = get_fox_events(nights, dusk_dawn_ranges)

    # Prepare report structure
    report = {
        "metadata": {
            "generated_at": datetime.now(MOUNTAIN_TZ).isoformat(),
            "nights_analyzed": nights,
            "total_nights": len(nights),
            "date_ranges": [
                {"night": night, "dusk": dusk.isoformat(), "dawn": dawn.isoformat()}
                for night, (dusk, dawn) in zip(nights, dusk_dawn_ranges, strict=False)
            ],
        },
        "events_by_camera": {},
        "totals": {
            "total_events": len(events),
            "cameras_with_detections": 0,
            "average_confidence": 0.0,
            "total_duration_seconds": 0.0,
        },
    }

    # Group events by camera
    camera_stats = {}
    total_confidence = 0.0
    total_duration = 0.0

    for event in events:
        camera = event["camera"]
        if camera not in report["events_by_camera"]:
            report["events_by_camera"][camera] = []
            camera_stats[camera] = {
                "count": 0,
                "total_confidence": 0.0,
                "total_duration": 0.0,
            }

        report["events_by_camera"][camera].append(event)
        camera_stats[camera]["count"] += 1
        camera_stats[camera]["total_confidence"] += event["confidence"]
        camera_stats[camera]["total_duration"] += event["duration_seconds"]

        total_confidence += event["confidence"]
        total_duration += event["duration_seconds"]

    # Calculate summary statistics
    report["totals"]["cameras_with_detections"] = len(report["events_by_camera"])
    report["totals"]["average_confidence"] = (
        total_confidence / len(events) if events else 0.0
    )
    report["totals"]["total_duration_seconds"] = total_duration

    # Add per-camera statistics
    for camera, stats in camera_stats.items():
        report["events_by_camera"][camera] = {
            "events": report["events_by_camera"][camera],
            "stats": {
                "event_count": stats["count"],
                "average_confidence": stats["total_confidence"] / stats["count"],
                "total_duration_seconds": stats["total_duration"],
            },
        }

    # Generate Markdown section
    markdown = generate_markdown_report(report)

    # Write JSON to file
    if output_file is None:
        output_file = datetime.now(tz=settings.tz).strftime(
            "/tmp/fox_report_%Y%m%d.json"
        )

    try:
        # Create a copy of the report without thumbnails for JSON output
        import copy

        json_report = copy.deepcopy(report)

        # Remove thumbnails from the JSON version to reduce file size
        for camera_data in json_report.get("events_by_camera", {}).values():
            if isinstance(camera_data, dict) and "events" in camera_data:
                for event in camera_data["events"]:
                    if "thumbnail" in event:
                        del event["thumbnail"]

        with open(output_file, "w") as json_file:
            json.dump(json_report, json_file, indent=2, default=str)
        logger.info("Report written to %s", output_file)
        print(f"✓ JSON report written to: {output_file}")
    except Exception as e:
        logger.error("Failed to write report to %s: %s", output_file, str(e))
        print(f"✗ Failed to write report: {e}")

    return report, markdown


def generate_markdown_report(report: dict) -> str:
    """
    Generate human-readable Markdown report for email body.

    Args:
        report: The structured report dictionary

    Returns:
        Markdown formatted string
    """
    md_lines = []

    # Header
    md_lines.extend(
        [
            f"**Generated:** {datetime.fromisoformat(report['metadata']['generated_at']).strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"**Nights Analyzed:** {report['metadata']['total_nights']} nights",
            f"**Total Events:** {report['totals']['total_events']}",
            f"**Cameras with Detections:** {report['totals']['cameras_with_detections']}",
            f"**Average Confidence:** {report['totals']['average_confidence']:.2f}",
            f"**Total Duration:** {report['totals']['total_duration_seconds']:.1f} seconds",
        ]
    )

    # Time ranges
    md_lines.extend(
        [
            "## 📅 Analysis Time Ranges",
        ]
    )

    # Extract events from report and count per night
    all_events = []
    for camera_data in report.get("events_by_camera", {}).values():
        all_events.extend(camera_data.get("events", []))
    night_event_counts = count_events_per_night(all_events)

    for date_range in report["metadata"]["date_ranges"]:
        night = date_range["night"]
        dusk_time = utc_to_mountain_time(date_range["dusk"]).strftime("%m/%d %H:%M")
        dawn_time = utc_to_mountain_time(date_range["dawn"]).strftime("%H:%M")

        # Calculate duration
        duration_hours, duration_str = calculate_night_duration(
            date_range["dusk"], date_range["dawn"]
        )

        # Get event count for this night
        event_count = night_event_counts.get(night, 0)

        md_lines.append(
            f"- **Night {night}:** {dusk_time} - {dawn_time} "
            f"({duration_str}, {event_count} events)"
        )

    md_lines.append("")

    # Events by camera
    if report["events_by_camera"]:
        md_lines.extend(
            [
                "## 📹 Events by Camera",
            ]
        )

        for camera, camera_data in report["events_by_camera"].items():
            events = camera_data["events"]
            stats = camera_data["stats"]

            md_lines.extend(
                [
                    f"### {camera}",
                    f"- **Events:** {stats['event_count']}",
                    f"- **Average Confidence:** {stats['average_confidence']:.2f}",
                    f"- **Total Duration:** {stats['total_duration_seconds']:.1f} seconds",
                    "",
                ]
            )

            # List individual events
            md_lines.append("**Recent Events:**")
            for event in events[:5]:  # Show up to 5 most recent
                start_time = utc_to_mountain_time(event["start_time"]).strftime(
                    "%m/%d %H:%M"
                )
                confidence_pct = event["confidence"] * 100
                duration_str = (
                    f"{event['duration_seconds']:.1f}s"
                    if event["duration_seconds"] > 0
                    else "N/A"
                )

                # Generate timeline URL if we have timestamps
                timeline_link = ""
                if "start_timestamp" in event and "end_timestamp" in event:
                    timeline_url = generate_timeline_url(
                        event["camera"],
                        event["start_timestamp"],
                        event["end_timestamp"],
                        padding=5,
                    )
                    timeline_link = f" | [Timeline]({timeline_url})"

                md_lines.append(
                    f"- {start_time} | Confidence: {confidence_pct:.0f}% | "
                    f"Duration: {duration_str} | [Event](https://frig.mso.mt/api/events/{event['event_id']}/clip.mp4){timeline_link}"
                )

            if len(events) > 5:
                md_lines.append(f"- ... and {len(events) - 5} more events")

    else:
        md_lines.extend(
            [
                "## 📹 Events by Camera",
                "",
                "No fox detections found in the analyzed time period.",
                "",
            ]
        )

    return "\n".join(md_lines)


def generate_html_report_with_thumbnails(report: dict) -> str:
    """
    Generate HTML report with inline thumbnail images.

    Args:
        report: The structured report dictionary

    Returns:
        HTML formatted string with embedded thumbnails
    """
    html_parts = []

    # HTML header with styling
    html_parts.append("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Fox Detection Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 { color: #333; border-bottom: 2px solid #ff6b35; padding-bottom: 10px; }
            h2 { color: #555; margin-top: 24px; }
            h3 { color: #666;  margin: 4px 0 2px;}
            .summary {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 12px 0;
            }
            .camera-section {
                margin: 6px 0;
                padding: 10px;
                background-color: #fafafa;
                border-radius: 5px;
            }
            .event {
                display: flex;
                align-items: center;
                margin: 6px 0;
                padding: 8px;
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            .thumbnail {
                width: 120px;
                height: 120px;
                margin-right: 15px;
                border-radius: 5px;
                object-fit: cover;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .thumbnail:hover {
                transform: scale(1.05);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            .event-details {
                flex-grow: 1;
            }
            .event-time {
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            .event-info {
                color: #666;
                margin: 3px 0;
             font-size: 13px;}
            .event-links {
                margin-top: 8px;
            }
            .event-links a {
                margin-right: 10px;
                padding: 4px 8px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 3px;
                font-size: 14px;
            }
            .event-links a:hover {
                background-color: #0056b3;
            }
            .footer {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                font-size: 0.9em;
                color: #666;
                text-align: center;
            }
            .no-events {
                text-align: center;
                padding: 40px;
                color: #999;
            }
                    .camera-section:last-child { margin-bottom: 6px; }
            .event:last-child { margin-bottom: 4px; }
</style>
    </head>
    <body>
    <div class="container">
    """)
    # Events by camera (moved to top)
    if report["events_by_camera"]:
        html_parts.append("<h2>📹 Events by Camera</h2>")

        for camera, camera_data in report["events_by_camera"].items():
            events = camera_data["events"]
            stats = camera_data["stats"]

            html_parts.append(f"""
            <div class="camera-section">
                <h3>{camera}</h3>
                <div class="event-info">
                    <strong>Events:</strong> {stats["event_count"]} |
                    <strong>Average Confidence:</strong> {stats["average_confidence"]:.2f} |
                    <strong>Total Duration:</strong> {stats["total_duration_seconds"]:.1f} seconds
                </div>
            """)

            # Show individual events with thumbnails
            for event in events[:10]:  # Show up to 10 events
                start_time = utc_to_mountain_time(event["start_time"]).strftime(
                    "%m/%d %H:%M"
                )
                confidence_pct = event["confidence"] * 100
                duration_str = (
                    f"{event['duration_seconds']:.1f}s"
                    if event["duration_seconds"] > 0
                    else "N/A"
                )

                # Generate timeline URL if we have timestamps
                timeline_link = ""
                if "start_timestamp" in event and "end_timestamp" in event:
                    timeline_url = generate_timeline_url(
                        event["camera"],
                        event["start_timestamp"],
                        event["end_timestamp"],
                        padding=5,
                    )
                    timeline_link = f'<a href="{timeline_url}">Timeline</a>'

                event_link = f'<a href="https://frig.mso.mt/api/events/{event["event_id"]}/clip.mp4">Event</a>'

                # Create event HTML with clickable thumbnail
                thumbnail_html = ""
                event_url = (
                    f"https://frig.mso.mt/api/events/{event['event_id']}/clip.mp4"
                )
                if event.get("thumbnail"):
                    # Make thumbnail clickable - links to event video
                    thumbnail_html = f'<a href="{event_url}" title="Click to view event video"><img src="data:image/jpeg;base64,{event["thumbnail"]}" class="thumbnail" alt="Fox detection thumbnail"></a>'

                html_parts.append(f"""
                <div class="event">
                    {thumbnail_html}
                    <div class="event-details">
                        <div class="event-time">{start_time}</div>
                        <div class="event-info">Confidence: {confidence_pct:.0f}%</div>
                        <div class="event-info">Duration: {duration_str}</div>
                        <div class="event-links">
                            {event_link}
                            {timeline_link}
                        </div>
                    </div>
                </div>
                """)

            if len(events) > 10:
                html_parts.append(
                    f'<p style="text-align: center; color: #999;">... and {len(events) - 10} more events</p>'
                )

            html_parts.append("</div>")
    else:
        html_parts.append("""
        <div class="no-events">
            <h2>No Fox Detections</h2>
            <p>No fox detections were found in the analyzed time period.</p>
        </div>
        """)

    # Summary (moved below events)
    html_parts.append(f"""
    <div class="summary">
        <strong>Generated:</strong> {datetime.fromisoformat(report["metadata"]["generated_at"]).strftime("%Y-%m-%d %H:%M:%S %Z")}<br>
        <strong>Nights Analyzed:</strong> {report["metadata"]["total_nights"]}<br>
        <strong>Total Events:</strong> {report["totals"]["total_events"]}<br>
        <strong>Cameras with Detections:</strong> {report["totals"]["cameras_with_detections"]}<br>
        <strong>Average Confidence:</strong> {report["totals"]["average_confidence"]:.2f}<br>
        <strong>Total Duration:</strong> {report["totals"]["total_duration_seconds"]:.1f} seconds
    </div>
    """)

    # Time ranges (now below summary)
    html_parts.append("<h2>📅 Analysis Time Ranges</h2><ul>")
    # Extract events from report and count per night for HTML
    all_events = []
    for camera_data in report.get("events_by_camera", {}).values():
        all_events.extend(camera_data.get("events", []))
    night_event_counts = count_events_per_night(all_events)

    for date_range in report["metadata"]["date_ranges"]:
        night = date_range["night"]
        dusk_time = utc_to_mountain_time(date_range["dusk"]).strftime("%m/%d %H:%M")
        dawn_time = utc_to_mountain_time(date_range["dawn"]).strftime("%H:%M")

        # Calculate duration
        duration_hours, duration_str = calculate_night_duration(
            date_range["dusk"], date_range["dawn"]
        )

        # Get event count for this night
        event_count = night_event_counts.get(night, 0)

        html_parts.append(
            f"<li><strong>Night {night}:</strong> "
            f"{dusk_time} - {dawn_time} "
            f"({duration_str}, {event_count} events)</li>"
        )
    html_parts.append("</ul>")

    # Footer
    html_parts.append("""
    <div class="footer">
        <p>This report was automatically generated by the Frigate Fox Detection System.</p>
        <p>Full report data is available in the attached JSON file.</p>
    </div>
    </div>
    </body>
    </html>
    """)

    return "".join(html_parts)


def get_last_n_nights_data(
    num_nights: int = 3,
) -> tuple[list[int], list[tuple[datetime, datetime]]]:
    """
    Get night indices and dusk/dawn ranges for the last N nights.

    Args:
        num_nights: Number of nights to analyze (default: 3)

    Returns:
        Tuple of (nights_list, dusk_dawn_ranges_list)
    """
    logger.info("Calculating time ranges for last %d nights", num_nights)

    try:
        # Instantiate TimeResolver and get time ranges
        time_resolver = TimeResolver()
        dusk_dawn_ranges = time_resolver.get_multiple_night_ranges(
            nights_count=num_nights
        )
        nights = list(range(1, num_nights + 1))

        logger.info("Successfully calculated time ranges for nights: %s", nights)
        return nights, dusk_dawn_ranges

    except Exception as e:
        logger.error("Failed to calculate time ranges: %s", str(e))
        return [], []


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🦊 Fox Detection Report Generator")
    print("=" * 40)

    try:
        # Get data for last 3 nights
        nights, dusk_dawn_ranges = get_last_n_nights_data(3)

        if not nights:
            print("✗ Could not retrieve time ranges. Aborting.")
            exit(1)

        print(f"Analyzing {len(nights)} nights:")
        for night, (dusk, dawn) in zip(nights, dusk_dawn_ranges, strict=False):
            print(
                f"  Night {night}: {dusk.strftime('%Y-%m-%d %H:%M')} - {dawn.strftime('%Y-%m-%d %H:%M')}"
            )

        print("\nGenerating report...")

        # Generate the report
        report, markdown = generate_fox_report(nights, dusk_dawn_ranges)

        print("\n" + "=" * 40)
        print("MARKDOWN REPORT:")
        print("=" * 40)
        print(markdown)

        # Also output to stdout for manual use
        json_output = json.dumps(report, indent=2, default=str)
        print("\n" + "=" * 40)
        print("JSON REPORT SUMMARY:")
        print("=" * 40)
        print(f"Total events: {report['totals']['total_events']}")
        print(f"Cameras with detections: {report['totals']['cameras_with_detections']}")
        print(
            f"Report file: /tmp/fox_report_{datetime.now(tz=settings.tz).strftime('%Y%m%d')}.json"
        )

    except Exception as e:
        logger.exception("Failed to generate report: %s", str(e))
        print(f"✗ Error generating report: {e}")
