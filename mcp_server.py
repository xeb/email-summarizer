#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp",
# ]
# ///

"""
Gmail Email Summarizer MCP Server

Exposes the email summarizer functionality as an MCP server with tools for:
- Searching emails by query
- Managing search configurations
- Fetching and summarizing emails
- Testing AI connections
"""

import json
import logging
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from email.utils import parsedate_to_datetime

from fastmcp import FastMCP

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

# Import application modules
from config.settings import load_config, validate_gmail_credentials
from config.search_configs import SearchConfigManager, SearchConfig, SearchConfigError
from auth.gmail_auth import GmailAuthError
from gmail_email.fetcher import create_email_fetcher, EmailFetchError
from gmail_email.processor import EmailProcessor, EmailData
from summarization.summarizer import EmailSummarizer
from storage.yaml_writer import YAMLWriter
from utils.error_handling import ErrorCategory, create_user_friendly_message

# Configure logging with both file and console output
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("mcp_server.log", mode="a"),
        logging.StreamHandler()
    ],
)

# Create a separate logger for detailed debugging
file_logger = logging.getLogger("mcp_server_debug")
file_handler = logging.FileHandler("mcp_server_debug.log", mode="a")
file_handler.setFormatter(logging.Formatter(log_format))
file_logger.addHandler(file_handler)
file_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Gmail Email Summarizer 📧")

# Global configuration and managers
config = None
search_manager = None

def initialize_services():
    """Initialize the configuration and search manager."""
    global config, search_manager
    try:
        config = load_config()
        search_manager = SearchConfigManager()
        logger.info("Services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

# Root endpoint for basic server info
@mcp.custom_route("/", methods=["GET"])
async def read_root():
    return {"message": "Gmail Email Summarizer MCP Server", "status": "running", "tools": ["search_by_query", "search_by_config", "create_config", "list_configs", "delete_config", "test_ai", "get_status"]}


async def _search_by_query_impl(
    query: str,
    max_emails: int = 50,
    summarize: bool = True,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Search emails using a custom Gmail query and optionally summarize them.

    Args:
        query: Gmail search query (e.g., "from:boss@company.com is:unread")
        max_emails: Maximum number of emails to process (default: 50)
        summarize: Whether to generate AI summaries (default: True)
        output_dir: Output directory for summaries (optional)

    Returns:
        Dictionary with search results, summaries, and metadata
    """
    if not config:
        raise ValueError("Server not properly initialized. Please check configuration.")

    try:
        logger.info(f"Starting search_by_query with query: {query}, max_emails: {max_emails}")
        file_logger.debug(f"Detailed search parameters - query: {query}, max_emails: {max_emails}, summarize: {summarize}, output_dir: {output_dir}")
        # Create email fetcher
        email_fetcher = create_email_fetcher(headless=True)

        # Fetch emails
        emails = email_fetcher.fetch_emails_with_query(
            query=query,
            max_results=max_emails
        )

        logger.info(f"Successfully fetched {len(emails)} emails")
        file_logger.debug(f"Fetched emails count: {len(emails)}")

        result = {
            "query": query,
            "total_found": len(emails),
            "max_requested": max_emails,
            "timestamp": datetime.now().isoformat(),
            "emails": []
        }

        if not emails:
            result["message"] = "No emails found matching the query"
            return result

        # Process emails similar to main.py
        processor = EmailProcessor()
        processed_emails = []

        for email in emails:
            try:
                # Parse the date
                date_str = email.get('date', '')
                try:
                    if date_str:
                        email_date = parsedate_to_datetime(date_str)
                    else:
                        email_date = datetime.now()
                except (ValueError, TypeError):
                    email_date = datetime.now()

                # Clean the body content using the processor
                body_content = email.get('body', '')
                if body_content:
                    # Use the processor's HTML cleaning capabilities
                    cleaned_body = processor.clean_html_content(body_content)
                    if not cleaned_body or cleaned_body.strip() == "":
                        cleaned_body = processor._clean_plain_text(body_content)
                else:
                    cleaned_body = "No readable content found"

                # Create EmailData object with the already-extracted data
                email_data = EmailData(
                    subject=email.get('subject', 'No Subject'),
                    sender=email.get('sender', 'Unknown Sender'),
                    date=email_date,
                    body=cleaned_body,
                    message_id=email.get('message_id', '')
                )

                processed_emails.append(email_data)

                # Add basic email info to result
                result["emails"].append({
                    "message_id": email_data.message_id,
                    "subject": email_data.subject,
                    "sender": email_data.sender,
                    "date": email_data.date.isoformat() if email_data.date else None,
                    "snippet": email.get('snippet', '')
                })
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                continue

        # Generate summaries if requested
        if summarize and processed_emails:
            try:
                summarizer = EmailSummarizer(config)
                summaries = summarizer.batch_summarize_emails(processed_emails)

                result["summaries"] = []
                for summary in summaries:
                    result["summaries"].append({
                        "subject": summary.subject,
                        "sender": summary.sender,
                        "date": summary.date,
                        "key_points": summary.key_points,
                        "action_items": summary.action_items,
                        "summary": summary.summary,
                        "priority": summary.priority
                    })

                # Optionally save to file
                if output_dir:
                    writer = YAMLWriter(output_dir)
                    yaml_file = writer.write_summaries(summaries, datetime.now())
                    result["saved_to"] = str(yaml_file)

            except Exception as e:
                logger.error(f"Error generating summaries: {e}")
                result["summary_error"] = str(e)

        return result

    except Exception as e:
        logger.error(f"Error in _search_by_query_impl: {e}")
        file_logger.exception("Full traceback for search_by_query error:")
        raise ValueError(f"Search failed: {str(e)}")

@mcp.tool
async def search_by_query(
    query: str,
    max_emails: int = 50,
    summarize: bool = True,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Search emails using a custom Gmail query and optionally summarize them.

    Args:
        query: Gmail search query (e.g., "from:boss@company.com is:unread")
        max_emails: Maximum number of emails to process (default: 50)
        summarize: Whether to generate AI summaries (default: True)
        output_dir: Output directory for summaries (optional)

    Returns:
        Dictionary with search results, summaries, and metadata
    """
    return await _search_by_query_impl(query, max_emails, summarize, output_dir)

@mcp.tool
async def search_by_config(
    config_name: str,
    max_emails: int = 50,
    summarize: bool = True,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Search emails using a saved search configuration.

    Args:
        config_name: Name of the saved search configuration
        max_emails: Maximum number of emails to process (default: 50)
        summarize: Whether to generate AI summaries (default: True)
        output_dir: Output directory for summaries (optional)

    Returns:
        Dictionary with search results, summaries, and metadata
    """
    if not search_manager:
        raise ValueError("Search manager not initialized")

    try:
        # Load the search configuration
        search_config = search_manager.load_config(config_name)

        # Use the configuration's query
        return await _search_by_query_impl(
            query=search_config.query,
            max_emails=max_emails,
            summarize=summarize,
            output_dir=output_dir
        )

    except Exception as e:
        logger.error(f"Error in search_by_config: {e}")
        raise ValueError(f"Failed to search with config '{config_name}': {str(e)}")

@mcp.tool
async def create_config(
    name: str,
    query: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    Create a new search configuration.

    Args:
        name: Name for the configuration
        query: Gmail search query
        description: Optional description of the configuration

    Returns:
        Dictionary with creation status and configuration details
    """
    if not search_manager:
        raise ValueError("Search manager not initialized")

    try:
        # Create the configuration
        search_config = SearchConfig(
            name=name,
            query=query,
            description=description,
            created_at=datetime.now(),
            last_used=None
        )

        # Save it
        search_manager.save_config(search_config)

        return {
            "status": "success",
            "message": f"Configuration '{name}' created successfully",
            "config": {
                "name": name,
                "query": query,
                "description": description,
                "created_at": search_config.created_at.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error creating config: {e}")
        raise ValueError(f"Failed to create configuration: {str(e)}")

@mcp.tool
async def list_configs() -> Dict[str, Any]:
    """
    List all saved search configurations.

    Returns:
        Dictionary with all configurations and their details
    """
    if not search_manager:
        raise ValueError("Search manager not initialized")

    try:
        configs = search_manager.list_configs()

        result = {
            "total_configs": len(configs),
            "configs": []
        }

        for config_data in configs:
            result["configs"].append({
                "name": config_data.name,
                "query": config_data.query,
                "description": getattr(config_data, "description", ""),
                "created_at": config_data.created_at.isoformat() if config_data.created_at else None,
                "last_used": config_data.last_used.isoformat() if config_data.last_used else None
            })

        return result

    except Exception as e:
        logger.error(f"Error listing configs: {e}")
        raise ValueError(f"Failed to list configurations: {str(e)}")

@mcp.tool
async def delete_config(name: str) -> Dict[str, Any]:
    """
    Delete a search configuration.

    Args:
        name: Name of the configuration to delete

    Returns:
        Dictionary with deletion status
    """
    if not search_manager:
        raise ValueError("Search manager not initialized")

    try:
        search_manager.delete_config(name)

        return {
            "status": "success",
            "message": f"Configuration '{name}' deleted successfully"
        }

    except Exception as e:
        logger.error(f"Error deleting config: {e}")
        raise ValueError(f"Failed to delete configuration '{name}': {str(e)}")

@mcp.tool
async def test_ai() -> Dict[str, Any]:
    """
    Test the AI service connection.

    Returns:
        Dictionary with test results for available AI providers
    """
    if not config:
        raise ValueError("Configuration not loaded")

    try:
        summarizer = EmailSummarizer(config)

        # Test with a simple prompt
        test_prompt = "This is a test. Please respond with 'AI connection successful'."

        # Create a dummy email for testing
        from gmail_email.processor import EmailData
        test_email = EmailData(
            subject="Test Email",
            sender="test@example.com",
            date=datetime.now(),
            body=test_prompt,
            message_id="test_message_123"
        )

        # Try to generate a summary
        summaries = summarizer.batch_summarize_emails([test_email])

        if summaries and len(summaries) > 0:
            return {
                "status": "success",
                "message": "AI service connection successful",
                "provider": config.ai_provider,
                "test_response": summaries[0].summary
            }
        else:
            return {
                "status": "error",
                "message": "AI service did not return expected response"
            }

    except Exception as e:
        logger.error(f"AI test failed: {e}")
        return {
            "status": "error",
            "message": f"AI test failed: {str(e)}"
        }

@mcp.tool
async def get_status() -> Dict[str, Any]:
    """
    Get the current status of the MCP server and its services.

    Returns:
        Dictionary with server status and configuration info
    """
    try:
        status = {
            "server": "Gmail Email Summarizer MCP Server",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }

        # Check configuration
        if config:
            status["services"]["config"] = {
                "status": "loaded",
                "ai_provider": getattr(config, 'ai_provider', 'unknown'),
                "output_dir": getattr(config, 'output_dir', 'unknown')
            }
        else:
            status["services"]["config"] = {"status": "not_loaded"}

        # Check search manager
        if search_manager:
            try:
                configs = search_manager.list_configs()
                status["services"]["search_manager"] = {
                    "status": "loaded",
                    "total_configs": len(configs)
                }
            except Exception as e:
                status["services"]["search_manager"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            status["services"]["search_manager"] = {"status": "not_loaded"}

        return status

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "server": "Gmail Email Summarizer MCP Server",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_arg_parser():
    """Get argument parser for MCP server."""
    parser = argparse.ArgumentParser(description="Gmail Email Summarizer MCP Server")
    parser.add_argument(
        "--stdio", action="store_true", help="Run server with STDIO transport"
    )
    return parser


if __name__ == "__main__":
    parser = get_arg_parser()
    args = parser.parse_args()

    logging.info("Starting Gmail Email Summarizer MCP Server")

    # Initialize services
    if not initialize_services():
        logging.error("Failed to initialize services. Server may not function properly.")

    # Run the server
    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", host="0.0.0.0", port=8775)