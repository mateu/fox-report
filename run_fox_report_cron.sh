#!/bin/bash
# Wrapper script for running fox report from cron with proper environment
# This version uses uv for Python package management

# Change to project directory
cd /home/hunter/fox-report || exit 1

# Load environment variables from .env file if it exists
# Using a more robust method that handles quotes and spaces
if [ -f .env ]; then
    # Read .env file line by line and export variables
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
            # Export the variable (handles values with spaces properly)
            export "$line"
        fi
    done < .env
fi

# Run the fox report script using uv
# uv automatically handles the virtual environment
/home/hunter/.local/bin/uv run python send_fox_report_gmail.py --config config/gmail.yaml --nights 1

# Exit with the same status as the python script
exit $?
