# Timeline Links Enhancement

## Overview
Added timeline video links to the fox detection report emails, providing a broader context view of each event with 5-second padding on either side.

## Changes Made

### 1. Database Query Enhancement (`src/fox_report/database_query.py`)
- Added `start_timestamp` and `end_timestamp` fields to capture raw Unix timestamps
- Modified SQL query to include these fields: `start_time as start_timestamp, end_time as end_timestamp`
- Updated event dictionary to include these new fields

### 2. Report Generator Enhancement (`src/fox_report/report_generator.py`)
- Added `generate_timeline_url()` helper function that:
  - Takes camera name and Unix timestamps
  - Adds configurable padding (default 5 seconds) on each side
  - Generates the timeline URL in format: `https://frig.mso.mt/api/{camera}/start/{start_ts}/end/{end_ts}/clip.mp4`

- Updated markdown report generation to include both links:
  - **Event link**: Direct link to the specific event clip
  - **Timeline link**: Broader context view with 5-second padding

## Link Format Examples

### Event Link (existing)
```
https://frig.mso.mt/api/events/1754215152.129619-ttj6ra/clip.mp4
```

### Timeline Link (new)
```
https://frig.mso.mt/api/pano/start/1754215147/end/1754215160/clip.mp4
```
Where:
- `pano` = camera name
- `1754215147` = event start time minus 5 seconds
- `1754215160` = event end time plus 5 seconds

## Report Output Example
```markdown
**Recent Events:**
- 08/03 03:59 | Confidence: 90% | Duration: 3.1s | [Event](https://frig.mso.mt/api/events/.../clip.mp4) | [Timeline](https://frig.mso.mt/api/pano/start/.../end/.../clip.mp4)
```

## Benefits
1. **Context**: Timeline view shows what happened before and after the fox detection
2. **Verification**: Helps verify if the detection was accurate
3. **Convenience**: Two viewing options - quick event clip or extended timeline view
4. **Customizable**: Padding can be adjusted if needed (currently 5 seconds)

## Testing
Run the report generator to test:
```bash
cd /home/hunter/fox-report
source venv/bin/activate
python3 src/fox_report/report_generator.py
```

The generated report will include both Event and Timeline links for each fox detection.
