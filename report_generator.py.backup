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
from typing import List, Dict, Tuple
from database_query import get_fox_events
from time_resolver import TimeResolver

# Configure logging using lazy formatting approach
logger = logging.getLogger(__name__)


def generate_fox_report(nights: List[int], 
                       dusk_dawn_ranges: List[Tuple[datetime, datetime]],
                       output_file: str = None) -> Tuple[Dict, str]:
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
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'nights_analyzed': nights,
            'total_nights': len(nights),
            'date_ranges': [
                {
                    'night': night,
                    'dusk': dusk.isoformat(),
                    'dawn': dawn.isoformat()
                }
                for night, (dusk, dawn) in zip(nights, dusk_dawn_ranges)
            ]
        },
        'events_by_camera': {},
        'totals': {
            'total_events': len(events),
            'cameras_with_detections': 0,
            'average_confidence': 0.0,
            'total_duration_minutes': 0.0
        }
    }
    
    # Group events by camera
    camera_stats = {}
    total_confidence = 0.0
    total_duration = 0.0
    
    for event in events:
        camera = event['camera']
        if camera not in report['events_by_camera']:
            report['events_by_camera'][camera] = []
            camera_stats[camera] = {
                'count': 0,
                'total_confidence': 0.0,
                'total_duration': 0.0
            }
        
        report['events_by_camera'][camera].append(event)
        camera_stats[camera]['count'] += 1
        camera_stats[camera]['total_confidence'] += event['confidence']
        camera_stats[camera]['total_duration'] += event['duration']
        
        total_confidence += event['confidence']
        total_duration += event['duration']
    
    # Calculate summary statistics
    report['totals']['cameras_with_detections'] = len(report['events_by_camera'])
    report['totals']['average_confidence'] = (
        total_confidence / len(events) if events else 0.0
    )
    report['totals']['total_duration_minutes'] = total_duration
    
    # Add per-camera statistics
    for camera, stats in camera_stats.items():
        report['events_by_camera'][camera] = {
            'events': report['events_by_camera'][camera],
            'stats': {
                'event_count': stats['count'],
                'average_confidence': stats['total_confidence'] / stats['count'],
                'total_duration_minutes': stats['total_duration']
            }
        }
    
    # Generate Markdown section
    markdown = generate_markdown_report(report)
    
    # Write JSON to file
    if output_file is None:
        output_file = datetime.now().strftime('/tmp/fox_report_%Y%m%d.json')
    
    try:
        with open(output_file, 'w') as json_file:
            json.dump(report, json_file, indent=2, default=str)
        logger.info("Report written to %s", output_file)
        print(f"✓ JSON report written to: {output_file}")
    except Exception as e:
        logger.error("Failed to write report to %s: %s", output_file, str(e))
        print(f"✗ Failed to write report: {e}")
    
    return report, markdown


def generate_markdown_report(report: Dict) -> str:
    """
    Generate human-readable Markdown report for email body.
    
    Args:
        report: The structured report dictionary
        
    Returns:
        Markdown formatted string
    """
    md_lines = []
    
    # Header
    md_lines.extend([
        "# 🦊 Fox Detection Report",
        "",
        f"**Generated:** {datetime.fromisoformat(report['metadata']['generated_at']).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Nights Analyzed:** {report['metadata']['total_nights']} nights",
        f"**Total Events:** {report['totals']['total_events']}",
        f"**Cameras with Detections:** {report['totals']['cameras_with_detections']}",
        f"**Average Confidence:** {report['totals']['average_confidence']:.2f}",
        f"**Total Duration:** {report['totals']['total_duration_minutes']:.1f} minutes",
        ""
    ])
    
    # Time ranges
    md_lines.extend([
        "## 📅 Analysis Time Ranges",
        ""
    ])
    
    for date_range in report['metadata']['date_ranges']:
        dusk = datetime.fromisoformat(date_range['dusk'])
        dawn = datetime.fromisoformat(date_range['dawn'])
        md_lines.append(
            f"- **Night {date_range['night']}:** "
            f"{dusk.strftime('%m/%d %H:%M')} - {dawn.strftime('%m/%d %H:%M')}"
        )
    
    md_lines.append("")
    
    # Events by camera
    if report['events_by_camera']:
        md_lines.extend([
            "## 📹 Events by Camera",
            ""
        ])
        
        for camera, camera_data in report['events_by_camera'].items():
            events = camera_data['events']
            stats = camera_data['stats']
            
            md_lines.extend([
                f"### {camera}",
                f"- **Events:** {stats['event_count']}",
                f"- **Average Confidence:** {stats['average_confidence']:.2f}",
                f"- **Total Duration:** {stats['total_duration_minutes']:.1f} minutes",
                ""
            ])
            
            # List individual events
            md_lines.append("**Recent Events:**")
            for event in events[:5]:  # Show up to 5 most recent
                start_time = datetime.fromisoformat(event['start_time']).strftime('%m/%d %H:%M')
                confidence_pct = event['confidence'] * 100
                duration_str = f"{event['duration']:.1f}min" if event['duration'] > 0 else "N/A"
                
                md_lines.append(
                    f"- {start_time} | Confidence: {confidence_pct:.0f}% | "
                    f"Duration: {duration_str} | ID: {event['event_id']}"
                )
            
            if len(events) > 5:
                md_lines.append(f"- ... and {len(events) - 5} more events")
            
            md_lines.append("")
    else:
        md_lines.extend([
            "## 📹 Events by Camera",
            "",
            "No fox detections found in the analyzed time period.",
            ""
        ])
    
    return "\n".join(md_lines)


def get_last_n_nights_data(num_nights: int = 3) -> Tuple[List[int], List[Tuple[datetime, datetime]]]:
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
        dusk_dawn_ranges = time_resolver.get_multiple_night_ranges(nights_count=num_nights)
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        for night, (dusk, dawn) in zip(nights, dusk_dawn_ranges):
            print(f"  Night {night}: {dusk.strftime('%Y-%m-%d %H:%M')} - {dawn.strftime('%Y-%m-%d %H:%M')}")
        
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
        print(f"Report file: /tmp/fox_report_{datetime.now().strftime('%Y%m%d')}.json")
        
    except Exception as e:
        logger.exception("Failed to generate report: %s", str(e))
        print(f"✗ Error generating report: {e}")
        
