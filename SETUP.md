# Fox Report Setup Guide

This guide will help you set up the Fox Detection Report system for your own Frigate installation.

## Prerequisites

- A working Frigate installation with fox detections
- Python 3.8 or higher
- Access to your Frigate database and web interface
- Gmail account with app password (for email notifications)

## Quick Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd fox-report
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the System

Copy the example configuration:
```bash
cp config/example.yaml config/config.yaml
```

Edit `config/config.yaml` and update these key settings:

#### Required Settings:
```yaml
frigate:
  # Path to your Frigate database
  database_path: "/path/to/your/frigate/config/frigate.db"
  
  # Your Frigate web interface URL
  base_url: "https://your-frigate-host.com"

email:
  # Your email address
  recipient: "your-email@example.com"
  
  smtp:
    username: "your-email@gmail.com"

location:
  # Your coordinates (get from https://www.latlong.net/)
  latitude: 40.7128
  longitude: -74.0060
  timezone: "America/New_York"
```

### 3. Set Up Email Authentication

Create a Gmail app password:
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Generate a new app password for "Mail"
3. Set the environment variable:

```bash
export GMAIL_APP_PASSWORD="your-16-character-app-password"
```

Or create a `.env` file in the project root:
```bash
echo "GMAIL_APP_PASSWORD=your-16-character-app-password" > .env
```

### 4. Test the Setup

Run a test report:
```bash
source venv/bin/activate
python send_fox_report_gmail.py --nights 3 --config config/config.yaml
```

## Configuration Options

### Environment Variables

You can override config settings with environment variables:

- `FRIGATE_DB_PATH` - Path to Frigate database
- `FRIGATE_BASE_URL` - Frigate web interface URL
- `FOX_REPORT_TEMP_DIR` - Directory for temporary files
- `GMAIL_APP_PASSWORD` - Gmail app password

### Database Path Discovery

The system will automatically search for your Frigate database in common locations:
- `/opt/frigate/config/frigate.db`
- `/var/lib/frigate/frigate.db`
- `./config/frigate.db`

### Timezone Configuration

Use standard timezone names like:
- `America/New_York`
- `America/Chicago` 
- `America/Denver`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`

## Scheduling (Optional)

Set up a cron job to run reports automatically:

```bash
# Edit crontab
crontab -e

# Add line to run daily at 8 AM
0 8 * * * cd /path/to/fox-report && source venv/bin/activate && python send_fox_report_gmail.py --config config/config.yaml
```

## Troubleshooting

### Common Issues

1. **Database not found**
   - Check the `frigate.database_path` in your config
   - Ensure the file exists and is readable
   - Try setting `FRIGATE_DB_PATH` environment variable

2. **No fox detections**
   - Verify Frigate is detecting objects labeled as "fox"
   - Check the time range (adjust `nights.count`)
   - Ensure your timezone is correct

3. **Email not sending**
   - Verify Gmail app password is correct
   - Check `email.smtp.username` matches your Gmail account
   - Ensure "Less secure app access" is disabled (use app passwords)

4. **Links don't work**
   - Verify `frigate.base_url` is correct and accessible
   - Test the URL in your browser
   - Check firewall/network settings

### Debug Mode

Run with verbose logging to troubleshoot:
```bash
python send_fox_report_gmail.py --verbose --config config/config.yaml
```

### Log Files

Check the log file for detailed error information:
```bash
tail -f /tmp/fox_report.log
```

## Customization

### Detection Labels

To detect other animals, modify the database query in `src/fox_report/database_query.py`:
```python
# Change this line:
WHERE label='fox'

# To detect multiple animals:
WHERE label IN ('fox', 'bear', 'deer')
```

### Email Template

Customize the HTML email template in `src/fox_report/report_generator.py` in the `generate_html_report_with_thumbnails()` function.

### Time Ranges

Adjust dusk/dawn calculations in your config:
```yaml
advanced:
  twilight_type: "civil"      # Earlier/later detection
  buffer_minutes: 30          # Extend time range
```

## Docker Setup (Advanced)

For Docker deployments, mount your config and Frigate database:

```yaml
version: '3'
services:
  fox-report:
    build: .
    volumes:
      - ./config:/app/config
      - /path/to/frigate/config:/frigate/config:ro
    environment:
      - GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD}
      - FRIGATE_DB_PATH=/frigate/config/frigate.db
```

## Support

If you encounter issues:
1. Check the logs: `tail -f /tmp/fox_report.log`
2. Run with `--verbose` flag for detailed output
3. Verify your Frigate installation is working
4. Test email settings with a simple test

## Security Notes

- Never commit your `.env` file or config with real credentials
- Use Gmail app passwords, not your main password
- Consider firewall rules if exposing Frigate externally
- Keep your Frigate installation updated
