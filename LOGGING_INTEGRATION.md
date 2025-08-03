# Fox Report Logging Integration

## Overview
Enhanced the `send_fox_report_gmail.py` script with comprehensive logging functionality that obeys command-line flags and uses lazy formatting as requested.

## Features Implemented

### 1. Command Line Flag Support
- `--verbose` / `-v`: Enable DEBUG level logging
- `--quiet` / `-q`: Enable WARNING level only (minimal output)
- Mutually exclusive validation (cannot use both flags together)

### 2. Lazy Formatting (No F-strings in Logging)
All logging calls use the recommended lazy formatting approach:
```python
logger.info("Found %d fox events", count)           # ✓ Good
logger.info(f"Found {count} fox events")            # ✗ Avoided
```

### 3. Rotating File Handler
- Default location: `/tmp/fox_report.log`
- Maximum size: 10MB per file
- Backup count: 5 files
- UTF-8 encoding
- Configurable via YAML config

### 4. Syslog Integration
- Writes to system log (`/dev/log`)
- Custom format: `fox_report[PID]: LEVEL - message`
- Configurable via YAML config (`use_syslog: true`)
- Graceful fallback if syslog unavailable

### 5. Configuration Integration
Updated `config_template.yaml` with logging settings:
```yaml
output:
  log_file: /tmp/fox_report.log
  use_syslog: true
```

## Usage Examples

### Normal Mode
```bash
python send_fox_report_gmail.py --nights 3
# Shows INFO level and above to console + file + syslog
```

### Verbose Mode
```bash
python send_fox_report_gmail.py --verbose --nights 3
# Shows DEBUG level and above (detailed logging)
```

### Quiet Mode
```bash
python send_fox_report_gmail.py --quiet --nights 3
# Shows WARNING level and above only (minimal output)
```

## Log Outputs

### Console Output
- Normal: INFO level messages with simple format
- Verbose: DEBUG level messages included
- Quiet: Minimal output, warnings/errors only

### File Output (Rotating)
- All log levels based on verbosity setting
- Full timestamp and module information
- Format: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`

### Syslog Output
- All log levels based on verbosity setting
- System log integration for monitoring
- Format: `fox_report[PID]: LEVEL - message`

## Implementation Details

### Logging Setup Function
```python
def setup_logging(verbose: bool = False, quiet: bool = False, config: dict = None) -> None:
    """Configure logging with rotating file handler and optional syslog."""
```

### Key Components
1. **RotatingFileHandler**: 10MB max, 5 backups
2. **SysLogHandler**: System log integration
3. **StreamHandler**: Console output
4. **Lazy Formatting**: All logger calls use `%` formatting
5. **Configuration Driven**: Settings from YAML config

### Error Handling
- Graceful fallback if log file cannot be created
- Warning if syslog unavailable
- Console logging always available as backup

## Testing
Created `test_logging.py` to demonstrate all features:
- Different log levels
- File rotation
- Syslog integration
- Lazy formatting examples

## Files Modified
1. `send_fox_report_gmail.py` - Enhanced with logging system
2. `config_template.yaml` - Added logging configuration
3. `test_logging.py` - Created for testing/demonstration

## Compliance with Requirements
✅ Configure logging module obeying --verbose/--quiet  
✅ Use logger.info("Found %d fox events", count) style (no f-strings)  
✅ Write to syslog or rotating file  
✅ All logging calls use lazy formatting approach
