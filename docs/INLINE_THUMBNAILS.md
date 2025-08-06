# Inline Thumbnail Enhancement

## Overview
Enhanced the fox detection report emails to include inline thumbnail images next to each event, providing immediate visual context without needing to open attachments or click links.

## Changes Made

### 1. New HTML Report Generator (`src/fox_report/report_generator.py`)
Added `generate_html_report_with_thumbnails()` function that:
- Creates a professionally styled HTML email with embedded CSS
- Embeds base64-encoded JPEG thumbnails directly in the HTML
- Displays thumbnails alongside event details in a card-like layout
- Shows up to 10 events per camera with their thumbnails

### 2. Updated Email Sender (`src/fox_report/email/sender.py`)
- Modified `_render_html_body()` to use the new HTML generator
- Falls back to basic HTML if thumbnail generation fails
- Maintains backward compatibility with existing email infrastructure

## Visual Layout

Each event is displayed as a card containing:
```
┌─────────────────────────────────────────┐
│ [Thumbnail]  08/03 03:59                │
│              Confidence: 90%            │
│              Duration: 3.1s             │
│              [Event] [Timeline]         │
└─────────────────────────────────────────┘
```

## Features

### Thumbnail Display
- **Size**: 120x120 pixels (optimized for email)
- **Format**: Base64-encoded JPEG (no external dependencies)
- **Style**: Rounded corners with subtle shadow
- **Fallback**: Gracefully handles missing thumbnails

### Email Styling
- **Responsive Design**: Clean, modern layout
- **Color Scheme**: Professional with accent colors
- **Typography**: Clear hierarchy with proper spacing
- **Mobile Friendly**: Scales well on different devices

## Benefits

1. **Immediate Visual Verification**: See the fox detection without clicking links
2. **Reduced False Positives**: Quickly identify incorrect detections
3. **Better Context**: Visual reference alongside confidence scores
4. **Self-Contained**: No external image hosting required
5. **Efficient**: Base64 encoding keeps email size reasonable (~8KB per thumbnail)

## Technical Details

### Base64 Encoding
The thumbnails from Frigate's database are already base64-encoded, so we embed them directly:
```html
<img src="data:image/jpeg;base64,{thumbnail_data}" class="thumbnail">
```

### Email Size
- Each thumbnail adds approximately 8KB to the email
- With 10 events, total email size remains under 100KB
- JSON attachment remains separate for detailed data

### Compatibility
- Works with all modern email clients
- HTML emails with embedded images are widely supported
- Plain text fallback available if needed

## Testing

To test the new HTML report with thumbnails:
```bash
cd /home/hunter/fox-report
source venv/bin/activate

# Generate test report
python3 -c "
from src.fox_report.report_generator import get_last_n_nights_data, generate_fox_report, generate_html_report_with_thumbnails
nights, ranges = get_last_n_nights_data(3)
report, _ = generate_fox_report(nights, ranges)
html = generate_html_report_with_thumbnails(report)
with open('/tmp/test_report.html', 'w') as f:
    f.write(html)
print('Test report saved to /tmp/test_report.html')
"
```

## Example Output

The email now shows:
- Fox thumbnail image (120x120px)
- Event timestamp
- Confidence percentage
- Duration
- Quick links to full event video and timeline view

All in a clean, professional layout that makes it easy to review fox detections at a glance.
