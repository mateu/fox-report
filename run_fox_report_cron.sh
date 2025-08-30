#!/bin/bash
# Wrapper script for running fox report from cron with proper environment
# This version uses FOX_REPORT_ROOT from .env with fallback

# Default fallback path (needed to find .env file initially)
DEFAULT_FOX_REPORT_ROOT="/home/hunter/fox-report"

# Use environment variable if already set, otherwise use default
SCRIPT_ROOT="${FOX_REPORT_ROOT:-$DEFAULT_FOX_REPORT_ROOT}"

# Change to project directory
cd "$SCRIPT_ROOT" || exit 1

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

# Now use the FOX_REPORT_ROOT from .env if it was loaded, otherwise keep the default
PROJECT_ROOT="${FOX_REPORT_ROOT:-$SCRIPT_ROOT}"

# Ensure we're in the right directory (in case FOX_REPORT_ROOT differs from our initial guess)
if [ "$PROJECT_ROOT" != "$SCRIPT_ROOT" ]; then
    cd "$PROJECT_ROOT" || exit 1
fi

# Determine UV path - try environment variable first, then common locations
if [ -n "$UV_PATH" ]; then
    UV_BIN="$UV_PATH"
elif [ -f "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
elif [ -f "/home/hunter/.local/bin/uv" ]; then
    UV_BIN="/home/hunter/.local/bin/uv"
else
    UV_BIN="uv"  # Hope it's in PATH
fi

# Run the fox report script using uv
# uv automatically handles the virtual environment
"$UV_BIN" run python send_fox_report_gmail.py --config config/gmail.yaml --nights 1

# Exit with the same status as the python script
exit $?
