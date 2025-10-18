#!/bin/bash
#
# Test script for email_summarizer.py
#
# This script tests the standalone email summarizer with various queries and filters.
#

set -e  # Exit on error

echo "=========================================="
echo "Email Summarizer Test Suite"
echo "=========================================="
echo ""

# Check if credentials exist
if [ ! -f "credentials.json" ]; then
    echo "Error: credentials.json not found"
    echo "Please place your Gmail OAuth2 credentials in credentials.json"
    exit 1
fi

# Check if token exists
if [ ! -f "token.json" ]; then
    echo "Error: token.json not found"
    echo "Please run: uv run email_summarizer_auth.py"
    exit 1
fi

echo "✓ Credentials and token found"
echo ""

# Test 1: Search by query - unread emails
echo "Test 1: Search unread emails"
echo "----------------------------"
uv run email_summarizer.py --query "is:unread" --max-results 5
echo ""

# Test 2: Search by query - important emails
echo "Test 2: Search important emails"
echo "--------------------------------"
uv run email_summarizer.py --query "is:important" --max-results 5
echo ""

# Test 3: Search by filter - unread emails from specific sender
echo "Test 3: Search by filter (unread)"
echo "----------------------------------"
uv run email_summarizer.py --filter '{"is_unread": true}' --max-results 5
echo ""

# Test 4: Search by filter - important and unread
echo "Test 4: Search by filter (important + unread)"
echo "----------------------------------------------"
uv run email_summarizer.py --filter '{"is_important": true, "is_unread": true}' --max-results 5
echo ""

# Test 5: Search by filter - emails with attachments
echo "Test 5: Search by filter (has attachment)"
echo "------------------------------------------"
uv run email_summarizer.py --filter '{"has_attachment": true}' --max-results 3
echo ""

# Test 6: Search by filter - newer than 7 days
echo "Test 6: Search by filter (newer than 7 days)"
echo "---------------------------------------------"
uv run email_summarizer.py --filter '{"newer_than": "7d"}' --max-results 10
echo ""

# Test 7: Export to JSON
echo "Test 7: Export results to JSON"
echo "-------------------------------"
uv run email_summarizer.py --query "is:unread" --max-results 3 --output test_results.json

if [ -f "test_results.json" ]; then
    echo "✓ JSON export successful"
    echo "File contents:"
    cat test_results.json | head -20
    echo ""
    echo "(truncated...)"
    rm test_results.json
else
    echo "✗ JSON export failed"
fi

echo ""
echo "=========================================="
echo "Test Suite Complete"
echo "=========================================="
