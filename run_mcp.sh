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
./venv/bin/python mcp_server.py --stdio