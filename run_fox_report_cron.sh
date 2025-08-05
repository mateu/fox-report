#!/bin/bash
# Wrapper script for running fox report from cron with proper environment
# This version loads credentials from a separate file for security

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

# Activate virtual environment
source venv/bin/activate

# Run the fox report script
python send_fox_report_gmail.py --config config/gmail.yaml --nights 1

# Exit with the same status as the python script
exit $?
