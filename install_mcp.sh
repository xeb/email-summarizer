#!/bin/bash

# Exit on error
set -e

# Determine BASE_DIR
if [ -d "${HOME}/projects" ]; then
  BASE_DIR="${HOME}/projects"
elif [ -d "${HOME}/working" ]; then
  BASE_DIR="${HOME}/working"
else
  echo "Error: Neither ${HOME}/projects nor ${HOME}/working directories found."
  exit 1
fi

# Define paths
GEMINI_EXT_DIR="$HOME/.gemini/extensions/email-summarizer"
GEMINI_EXT_JSON="$GEMINI_EXT_DIR/gemini-extension.json"
MCP_COMMAND="${BASE_DIR}/email-summarizer/run_mcp.sh"
MCP_NAME="email-summarizer"

# Initialize status variables
dir_created=false
json_created=false
mcp_added=false
error_occurred=false

# --- 1. Create directory ---
echo "Attempting to create directory: $GEMINI_EXT_DIR"
if mkdir -p "$GEMINI_EXT_DIR"; then
    dir_created=true
else
    error_occurred=true
fi

# --- 2. Create JSON file ---
echo "Creating JSON file: $GEMINI_EXT_JSON"
if cat > "$GEMINI_EXT_JSON" << EOL
{
  "name": "email-summarizer",
  "version": "0.0.1",
  "mcpServers": {
    "email_summarizer": {
        "command": "$MCP_COMMAND"
    }
  }
}
EOL
then
    json_created=true
else
    error_occurred=true
fi

# --- 3. Add MCP server ---
echo "Adding MCP server: $MCP_NAME"
output=$(claude mcp add "$MCP_NAME" "$MCP_COMMAND" 2>&1) || true

if [[ $output == *"already exists"* ]]; then
    echo "MCP server already exists, which is okay."
    mcp_added=true
elif [[ $output == *"Successfully added"* ]]; then
    mcp_added=true
else
    echo "Error adding MCP server: $output"
    error_occurred=true
fi


# --- 4. Print summary ---
echo ""
echo "--- Installation Summary ---"
if [ "$dir_created" = true ]; then
    echo "[✓] Directory created: $GEMINI_EXT_DIR"
else
    echo "[✗] Failed to create directory: $GEMINI_EXT_DIR"
fi

if [ "$json_created" = true ]; then
    echo "[✓] JSON file created: $GEMINI_EXT_JSON"
else
    echo "[✗] Failed to create JSON file: $GEMINI_EXT_JSON"
fi

if [ "$mcp_added" = true ]; then
    echo "[✓] MCP server added: $MCP_NAME"
else
    echo "[✗] Failed to add MCP server: $MCP_NAME"
fi
echo "--------------------------"

if [ "$error_occurred" = true ]; then
    echo "Installation completed with errors."
    exit 1
else
    echo "Installation completed successfully."
fi
