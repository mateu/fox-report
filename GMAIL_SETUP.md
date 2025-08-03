# Gmail SMTP Setup Guide

This guide explains how to set up Gmail SMTP authentication for the fox-report project using environment variables.

## Prerequisites

1. A Gmail account
2. App Password (not your regular Gmail password)

## Step 1: Generate Gmail App Password

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to Security → 2-Step Verification (must be enabled)
3. At the bottom, select "App passwords"
4. Generate a new app password for "Mail"
5. Save the 16-character password (format: xxxx-xxxx-xxxx-xxxx)

## Step 2: Configure Environment Variables

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Gmail app password:
   ```bash
   GMAIL_APP_PASSWORD=your_16_character_app_password_here
   ```

3. The `.env` file is automatically ignored by git and won't be committed.

## Step 3: Install Dependencies

Install the required packages:
```bash
pip install -r requirements.txt
```

## Step 4: Configure Gmail Settings

Edit `config_gmail.yaml` and set:
```yaml
email:
  smtp:
    enabled: true
    server: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "your_email@gmail.com"
    password: ""  # Leave empty - uses GMAIL_APP_PASSWORD env var
```

## Usage

The application will automatically:
1. Load the `.env` file at startup
2. Use the `GMAIL_APP_PASSWORD` environment variable
3. Fall back to the password field in config if env var is not set

## Security Notes

- Never commit your `.env` file to version control
- Use App Passwords, not your regular Gmail password
- The password is loaded securely from environment variables
- Config files contain no sensitive information

## Troubleshooting

- Ensure 2-factor authentication is enabled on your Gmail account
- Verify the app password is exactly 16 characters
- Check that `.env` file is in the project root directory
- Confirm `python-dotenv` is installed
