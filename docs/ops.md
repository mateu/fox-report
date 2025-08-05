# Operations Documentation

## Cron Job Configuration

### Timezone Handling

**Issue**: Cron jobs by default run in UTC timezone, which caused scheduling issues for the fox report system that needs to run at 6:00 AM Mountain Time.

**Solution**: The crontab entry includes the `CRON_TZ=America/Denver` directive to ensure the job runs at the correct local time.

```bash
# Daily fox report at 6:00 AM Mountain Time
CRON_TZ=America/Denver
0 6 * * * cd /home/hunter/fox-report && source venv/bin/activate && python send_fox_report_gmail.py --config config/gmail.yaml --nights 1 >> /tmp/fox_report_cron.log 2>&1
```

**Why this matters**:
- Without `CRON_TZ`, the job would run at 6:00 AM UTC (12:00 AM or 1:00 AM Mountain Time depending on DST)
- The `CRON_TZ=America/Denver` directive ensures the job runs at 6:00 AM local Mountain Time
- This automatically handles Daylight Saving Time transitions
- Recipients expect the report to arrive at a consistent local time

### Log Rotation

The cron job logs to `/tmp/fox_report_cron.log` which includes:
- Execution timestamps in Mountain Time
- Virtual environment activation status
- Report generation success/failure messages
- Email sending confirmation

**Log Management**:
- Logs are appended to the same file (`>>`)
- System tmpfs cleanup handles old logs automatically
- For production deployments, consider using logrotate for persistent log management

### Current Status

✅ **Active Configuration**: The cron job is currently active and running successfully
✅ **Timezone Fix Applied**: `CRON_TZ=America/Denver` is in place
✅ **No Legacy UTC Entries**: No old UTC-shifted entries found in crontab

### Maintenance Notes

- The cron backup is stored at `/tmp/crontab_backup.txt`
- Virtual environment activation is properly handled in the cron command
- Email configuration uses Gmail SMTP with app passwords
- Reports are generated for the previous night's detections (--nights 1)

### Troubleshooting

If the cron job stops working:

1. **Check cron service**: `systemctl status cron`
2. **Verify crontab**: `crontab -l`
3. **Check logs**: `tail -f /tmp/fox_report_cron.log`
4. **Test manually**: 
   ```bash
   cd /home/hunter/fox-report && source venv/bin/activate && python send_fox_report_gmail.py --config config/gmail.yaml --nights 1
   ```
5. **Verify timezone**: The job should show MDT/MST timestamps in logs

### Future Maintainers

⚠️ **Important**: Do not remove the `CRON_TZ=America/Denver` directive from the crontab. This ensures the fox reports are sent at the expected local time rather than UTC.

## Email Configuration

### Gmail SMTP Authentication

**Issue**: The cron environment doesn't automatically load environment variables from `.env` files, causing Gmail SMTP authentication to fail and falling back to local postfix mail delivery.

**Solution**: Created a wrapper script `/home/hunter/fox-report/run_fox_report_cron.sh` that:
1. Explicitly exports all required environment variables including the Gmail app password
2. Activates the Python virtual environment
3. Runs the fox report script with proper authentication

**Important Notes**:
- The Gmail app password contains spaces and must be properly quoted
- Direct `.env` file sourcing in cron can fail due to parsing issues with quotes and spaces
- The wrapper script hardcodes the credentials for reliability in the cron environment

### Verifying Email Delivery

To verify emails are being sent through Gmail SMTP (not local postfix):

1. Check the email headers - should show `Received: from smtp.gmail.com`
2. Monitor logs: `tail -f /tmp/fox_report_cron.log`
3. Look for: `INFO: Email sent successfully via SMTP to hunter@406mt.org`
4. If you see postfix logs in journalctl during cron execution, the Gmail SMTP is not working

### Wrapper Script

The cron job uses `/home/hunter/fox-report/run_fox_report_cron.sh` which:
- Sets up the complete environment
- Handles password strings with spaces correctly
- Ensures Gmail SMTP authentication works properly
- Provides consistent execution environment

⚠️ **Security Note**: The wrapper script contains credentials. Ensure proper file permissions:
```bash
chmod 700 /home/hunter/fox-report/run_fox_report_cron.sh
```

## Security Best Practices

### Credential Management

The system uses environment variables for sensitive credentials, following these security practices:

1. **Never commit credentials**: The `.env` file containing real credentials is in `.gitignore`
2. **Use `.env.example`**: A template file with placeholder values is committed for reference
3. **Secure file permissions**: Ensure `.env` has restricted permissions:
   ```bash
   chmod 600 .env
   ```
4. **Cron wrapper script**: The `run_fox_report_cron.sh` script safely loads credentials from `.env` without hardcoding them

### Setting Up Credentials

1. Copy the template: `cp .env.example .env`
2. Edit `.env` with your actual Gmail app password
3. Set proper permissions: `chmod 600 .env`
4. The wrapper script will automatically load these variables for cron jobs

### Git Repository Safety

Files that should be committed:
- `run_fox_report_cron.sh` (safe - loads credentials from .env)
- `.env.example` (template with placeholders)
- `.gitignore` (ensures .env is never committed)

Files that should NEVER be committed:
- `.env` (contains actual credentials)
- Any file with hardcoded passwords
