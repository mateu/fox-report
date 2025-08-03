# Dusk/Dawn Time Resolver

This utility provides functions for calculating dusk and dawn times for astronomical observations using either the `astral` library with geographic coordinates or static fallback times from configuration.

## Features

- **Astral Calculations**: Uses the `astral` library with latitude/longitude coordinates to calculate precise dusk and dawn times
- **Static Time Fallback**: Falls back to configured static times when geographic calculations are not available or preferred
- **Flexible Date Handling**: Calculate times for any date, with support for looking back a specified number of nights
- **Multiple Night Support**: Get time ranges for multiple consecutive nights
- **Configurable Twilight Types**: Supports civil, nautical, and astronomical twilight
- **Timezone Support**: Handles timezone conversions properly
- **Buffer Time**: Adds configurable buffer time before dusk and after dawn

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your location and preferences in `config_template.yaml`

## Usage

### Command Line Interface

```bash
# Calculate tonight's observation window
python time_resolver.py

# Calculate last night's window (1 night back)
python time_resolver.py --lookback 1

# Calculate for a specific date
python time_resolver.py --date 2025-07-01

# Calculate multiple consecutive nights
python time_resolver.py --nights 7

# Use a different configuration file
python time_resolver.py --config my_config.yaml
```

### Python API

```python
from time_resolver import TimeResolver
from datetime import date

# Initialize with default config
resolver = TimeResolver("config_template.yaml")

# Get tonight's dusk/dawn times
dusk, dawn = resolver.get_night_range()
print(f"Tonight: {dusk} → {dawn}")

# Get last night's times (lookback 1 night)
dusk, dawn = resolver.get_night_range(lookback_nights=1)
print(f"Last night: {dusk} → {dawn}")

# Get times for a specific date
target_date = date(2025, 7, 1)
dusk, dawn = resolver.get_night_range(target_date)
print(f"July 1st: {dusk} → {dawn}")

# Get multiple nights
ranges = resolver.get_multiple_night_ranges(nights_count=7)
for i, (dusk, dawn) in enumerate(ranges):
    print(f"Night {i}: {dusk} → {dawn}")
```

## Configuration

The configuration is stored in YAML format. Key sections:

### Location Settings (for Astral calculations)
```yaml
location:
  latitude: 46.9080      # Decimal degrees
  longitude: -114.0722   # Decimal degrees  
  timezone: "America/Denver"
  elevation: 980         # Meters above sea level
```

### Static Times (fallback)
```yaml
static_times:
  enabled: false         # Set to true to use static times instead of astral
  start_time: "20:00"    # 24-hour format
  end_time: "06:00"      # 24-hour format (can be next day)
```

### Advanced Settings
```yaml
advanced:
  twilight_type: "nautical"    # civil, nautical, or astronomical
  buffer_minutes: 15           # Extra minutes before dusk and after dawn
```

## Examples

### Example 1: Basic Usage
```python
resolver = TimeResolver()
dusk, dawn = resolver.get_night_range()
duration = dawn - dusk
print(f"Observation window: {duration}")
```

### Example 2: Multiple Nights for Planning
```python
resolver = TimeResolver()
ranges = resolver.get_multiple_night_ranges(nights_count=14)

print("Next two weeks of observation windows:")
for i, (dusk, dawn) in enumerate(ranges):
    night_date = date.today() - timedelta(days=i)
    duration = dawn - dusk
    print(f"{night_date}: {duration} ({dusk.strftime('%H:%M')} → {dawn.strftime('%H:%M')})")
```

### Example 3: Seasonal Comparison
```python
resolver = TimeResolver()
seasons = [
    ("Winter Solstice", date(2025, 12, 21)),
    ("Spring Equinox", date(2025, 3, 20)),
    ("Summer Solstice", date(2025, 6, 21)),
    ("Fall Equinox", date(2025, 9, 23)),
]

for season_name, season_date in seasons:
    dusk, dawn = resolver.get_night_range(season_date)
    duration = dawn - dusk
    print(f"{season_name}: {duration}")
```

## Error Handling

The utility includes robust error handling:

- If astral calculations fail, it automatically falls back to static times (if configured)
- Invalid configuration files produce clear error messages
- Missing required configuration values are detected and reported
- Invalid date formats are handled gracefully

## Logging

The utility uses Python's logging module with configurable verbosity levels:

- `0`: Warnings only
- `1`: Normal info (default)
- `2`: Verbose/debug information
- `3`: Maximum debug output

Configure in the YAML file:
```yaml
output:
  verbosity: 1
  log_file: /tmp/time_resolver.log  # Optional
```

## Twilight Types

- **Civil Twilight**: Sun is 6° below horizon (good for general observations)
- **Nautical Twilight**: Sun is 12° below horizon (darker, better for most astronomy)
- **Astronomical Twilight**: Sun is 18° below horizon (darkest, best for deep-sky work)

## Timezone Handling

The utility properly handles timezones:
- Uses configured timezone from the YAML file
- Falls back to UTC if no timezone is specified
- All returned datetime objects include timezone information
- Handles daylight saving time transitions automatically
