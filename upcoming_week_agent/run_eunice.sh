#!/bin/bash

# Exit on error
set -e

# Determine BASE_DIR using same logic as install_mcp.sh
if [ -d "${HOME}/projects" ]; then
  BASE_DIR="${HOME}/projects"
elif [ -d "${HOME}/working" ]; then
  BASE_DIR="${HOME}/working"
else
  echo "Error: Neither ${HOME}/projects nor ${HOME}/working directories found."
  exit 1
fi

# Define the correct email-summarizer path
CORRECT_EMAIL_SUMMARIZER_PATH="${BASE_DIR}/email-summarizer/run_mcp.sh"
EUNICE_JSON_PATH="$(dirname "$0")/eunice.json"

# Check if eunice.json exists
if [ ! -f "$EUNICE_JSON_PATH" ]; then
  echo "Error: eunice.json not found at $EUNICE_JSON_PATH"
  exit 1
fi

# Read current path from eunice.json
CURRENT_PATH=$(python3 -c "
import json
import sys
try:
    with open('$EUNICE_JSON_PATH', 'r') as f:
        data = json.load(f)
    print(data['mcpServers']['email_summarizer']['command'])
except Exception as e:
    print('ERROR', file=sys.stderr)
    sys.exit(1)
")

if [ "$CURRENT_PATH" = "ERROR" ]; then
  echo "Error: Could not read current path from eunice.json"
  exit 1
fi

# Check if current path is correct and update if needed
if [ "$CURRENT_PATH" != "$CORRECT_EMAIL_SUMMARIZER_PATH" ]; then
  echo "Updating eunice.json path from '$CURRENT_PATH' to '$CORRECT_EMAIL_SUMMARIZER_PATH'"

  # Update the JSON file
  python3 -c "
import json
with open('$EUNICE_JSON_PATH', 'r') as f:
    data = json.load(f)
data['mcpServers']['email_summarizer']['command'] = '$CORRECT_EMAIL_SUMMARIZER_PATH'
with open('$EUNICE_JSON_PATH', 'w') as f:
    json.dump(data, f, indent=2)
"
  echo "eunice.json updated successfully"
else
  echo "eunice.json path is already correct: $CURRENT_PATH"
fi

# Run eunice with the corrected configuration
time uvx git+https://github.com/xeb/eunice --verbose --model=gemini-2.5-pro "Read prompt.txt and do what it says"
