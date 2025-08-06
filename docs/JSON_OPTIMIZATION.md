# JSON Attachment Optimization

## Overview
Removed base64-encoded thumbnail images from the JSON attachment to significantly reduce file size while keeping them available for the HTML email display.

## Change Details

### Before
- JSON attachment included base64-encoded thumbnails
- File size: ~13KB for 2 events
- Thumbnails were redundant (already in email body)

### After  
- JSON attachment excludes thumbnails
- File size: ~2.3KB for 2 events (82% reduction!)
- Thumbnails still available in email HTML

## Implementation

The `generate_fox_report()` function now:
1. Keeps thumbnails in the report object for email generation
2. Creates a deep copy of the report for JSON output
3. Removes thumbnail fields from the JSON copy
4. Saves the cleaned JSON to file

## Benefits

1. **Smaller Attachments**: 80%+ reduction in JSON file size
2. **Faster Email Delivery**: Smaller attachments transmit faster
3. **Cleaner Data**: JSON contains only analytical data, not display assets
4. **No Redundancy**: Thumbnails only stored where needed (email HTML)
5. **Storage Efficient**: If archiving JSON files, saves significant space

## File Size Comparison

| Events | With Thumbnails | Without Thumbnails | Reduction |
|--------|----------------|-------------------|-----------|
| 2 | 13 KB | 2.3 KB | 82% |
| 10 | ~65 KB | ~11 KB | 83% |
| 50 | ~325 KB | ~55 KB | 83% |

## Data Availability

- **In Email HTML**: Thumbnails ✅ (embedded with Content-ID)
- **In JSON Attachment**: Thumbnails ❌ (removed to save space)
- **For Analysis**: All event data except thumbnails ✅

The JSON attachment remains complete for data analysis purposes, containing:
- Event IDs, timestamps, confidence scores
- Camera names, zones, durations
- All metadata and statistics
- Just no thumbnail image data

This optimization makes the system more efficient while maintaining all functionality.
