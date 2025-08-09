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

## Installation & Setup

### 1. Create Virtual Environment

**IMPORTANT**: This project requires a virtual environment to ensure all dependencies are properly isolated and available.

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment (Linux/macOS)
source venv/bin/activate

# Activate virtual environment (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Make sure virtual environment is activated first!
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
# Edit .env with your specific configuration
```

### 4. Configure Location Settings

Configure your location and preferences in `config_template.yaml`

## Usage

**IMPORTANT**: Always activate the virtual environment before running any scripts:

```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

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

## Gmail Email Sending Setup

This project includes functionality to send automated email reports using Gmail SMTP. The implementation includes proper authentication, spam prevention headers, and deliverability optimization.

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Gmail Configuration (required for email sending)
GMAIL_APP_PASSWORD=your_gmail_app_password_here
GMAIL_EMAIL=your-email@gmail.com

# SMTP Configuration (required for deliverability testing)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your_gmail_app_password_here
DOMAIN=yourdomain.com

# Logging Configuration (optional)
# LOG_LEVEL options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

### Gmail Setup Instructions

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings → Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this password in `GMAIL_APP_PASSWORD` (not your regular Gmail password)
3. **Copy `.env.example`** to `.env` and fill in your credentials

### Email Headers Implementation

The email sender automatically includes these essential headers for deliverability and spam prevention:

- **Message-ID**: Unique identifier using UUID4 format (`<uuid@domain>`)
- **Date**: RFC-2822 formatted timestamp with timezone
- **Reply-To**: Configurable support email address
- **X-Mailer**: Application identifier (`FoxReport/1.0 (Python smtplib)`)
- **Content-Type**: Proper multipart/alternative with UTF-8 charset
- **Plain-text alternative**: HTML emails include auto-generated plain-text version


### Usage Examples

**IMPORTANT**: Always activate the virtual environment before running scripts:

```bash
# Activate virtual environment first
source venv/bin/activate

# Send report with default settings (INFO level logging)
python send_fox_report_gmail.py

# Send with debug logging for troubleshooting
LOG_LEVEL=DEBUG python send_fox_report_gmail.py

# Test email functionality
python email_sender_gmail.py
```

### Logging Control

The email system supports environment variable controlled logging:

- `LOG_LEVEL=DEBUG`: Maximum verbosity for troubleshooting
- `LOG_LEVEL=INFO`: Standard operational logging (default)
- `LOG_LEVEL=WARNING`: Only warnings and errors
- `LOG_LEVEL=ERROR`: Only error messages

### Troubleshooting

If emails are being sent via system mail instead of Gmail SMTP, ensure:

1. **Virtual environment is activated**: `source venv/bin/activate`
2. **All dependencies are installed**: `pip install -r requirements.txt`
3. **Environment variables are configured**: Check `.env` file
4. **Gmail app password is correct**: 16-character space-separated format
