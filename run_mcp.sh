#!/bin/bash
if [ -d "${HOME}/projects" ]; then
  BASE_DIR="${HOME}/projects"
elif [ -d "${HOME}/working" ]; then
  BASE_DIR="${HOME}/working"
else
  echo "Error: Neither ${HOME}/projects nor ${HOME}/working directories found."
  exit 1
fi
cd "${BASE_DIR}/email-summarizer/"

# Export environment variables if they're not already set
if [ -n "$OPENAI_API_KEY" ]; then
  export OPENAI_API_KEY
fi
if [ -n "$CLAUDE_API_KEY" ]; then
  export CLAUDE_API_KEY
fi

./venv/bin/python mcp_server.py --stdio