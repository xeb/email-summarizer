#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "google-api-python-client",
#     "google-auth-httplib2",
#     "google-auth-oauthlib",
# ]
# ///
"""
Standalone Gmail Email Summarizer Script

This script provides a self-contained email summarization tool that can be run with:
    uv run scripts/email_summarizer.py

It includes two main functions:
- search_by_query: Search emails using a Gmail search query
- search_by_filter: Search emails using a filter dict (from, subject, is_unread, etc.)
"""

import os
import sys
import pickle
import base64
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# Third-party imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build, Resource
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Required Google API packages not found.")
    print("Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Disable OAuth2 HTTPS requirement for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def find_file(filename: str) -> str:
    """
    Find a file by searching in multiple locations.

    Search order:
    1. Current working directory
    2. Parent directory
    3. Script's directory
    4. Parent of script's directory (project root)

    Args:
        filename: Name of the file to find

    Returns:
        Full path to the file, or the original filename if not found
    """
    # Check current directory
    if os.path.exists(filename):
        return filename

    # Check parent directory
    parent_path = os.path.join('..', filename)
    if os.path.exists(parent_path):
        return parent_path

    # Check script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, filename)
    if os.path.exists(script_path):
        return script_path

    # Check parent of script's directory (project root)
    project_root = os.path.dirname(script_dir)
    root_path = os.path.join(project_root, filename)
    if os.path.exists(root_path):
        return root_path

    # Return original filename if not found (will trigger proper error handling)
    return filename


@dataclass
class EmailSummary:
    """Simple email summary data structure."""
    subject: str
    sender: str
    date: str
    snippet: str
    message_id: str
    body: str = ""  # Full body content (optional, only fetched with --full flag)


class EmailSummarizer:
    """Standalone email summarizer for Gmail."""

    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        """
        Initialize the email summarizer.

        Args:
            credentials_file: Path to OAuth2 credentials file
            token_file: Path to stored authentication token
        """
        # Resolve file paths by searching in multiple locations
        self.credentials_file = find_file(credentials_file)
        self.token_file = find_file(token_file)
        self.service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using stored credentials.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Error loading token: {e}")
                return False

        # If no valid credentials, fail (use auth script instead)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed credentials
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    os.chmod(self.token_file, 0o600)
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    print("Please run: uv run scripts/email_summarizer_auth.py")
                    return False
            else:
                print("No valid credentials found.")
                print("Please run: uv run scripts/email_summarizer_auth.py")
                return False

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            # Test connection
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"✓ Authenticated as: {profile.get('emailAddress', 'unknown')}")
            return True
        except Exception as e:
            print(f"Error building Gmail service: {e}")
            return False

    def search_by_query(self, query: str, max_results: int = 10, fetch_full: bool = False) -> List[EmailSummary]:
        """
        Search emails using a Gmail search query.

        Args:
            query: Gmail search query (e.g., "from:example@gmail.com is:unread")
            max_results: Maximum number of emails to return
            fetch_full: If True, fetch full message body instead of just snippet

        Returns:
            List of EmailSummary objects

        Example:
            summaries = summarizer.search_by_query("from:boss@company.com is:unread", max_results=5)
        """
        if not self.service:
            print("Error: Not authenticated. Call authenticate() first.")
            return []

        try:
            print(f"Searching with query: {query}")

            # Get message IDs
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = result.get('messages', [])

            if not messages:
                print("No emails found matching query.")
                return []

            print(f"Found {len(messages)} email(s)")

            # Fetch email details
            summaries = []
            for i, msg in enumerate(messages, 1):
                message_id = msg['id']
                email = self._get_email_details(message_id, fetch_full=fetch_full)
                if email:
                    summaries.append(email)
                    print(f"  [{i}] {email.sender}: {email.subject}")

            return summaries

        except HttpError as e:
            print(f"Gmail API error: {e}")
            return []
        except Exception as e:
            print(f"Error searching emails: {e}")
            return []

    def search_by_filter(self, filter_dict: Dict[str, Any], max_results: int = 10, fetch_full: bool = False) -> List[EmailSummary]:
        """
        Search emails using a filter dictionary.

        Args:
            filter_dict: Dictionary with filter criteria:
                - from: Sender email address (str)
                - to: Recipient email address (str)
                - subject: Subject keywords (str)
                - is_unread: Only unread emails (bool)
                - is_important: Only important emails (bool)
                - is_starred: Only starred emails (bool)
                - has_attachment: Only emails with attachments (bool)
                - after: Date in YYYY/MM/DD or YYYY-MM-DD format (str)
                - before: Date in YYYY/MM/DD or YYYY-MM-DD format (str)
                - newer_than: Relative date like "7d", "2w", "1m" (str)
                - older_than: Relative date like "7d", "2w", "1m" (str)
            max_results: Maximum number of emails to return
            fetch_full: If True, fetch full message body instead of just snippet

        Returns:
            List of EmailSummary objects

        Example:
            summaries = summarizer.search_by_filter({
                "from": "boss@company.com",
                "is_unread": True,
                "newer_than": "7d"
            }, max_results=5)
        """
        # Build Gmail query from filter dictionary
        query_parts = []

        if 'from' in filter_dict and filter_dict['from']:
            query_parts.append(f"from:{filter_dict['from']}")

        if 'to' in filter_dict and filter_dict['to']:
            query_parts.append(f"to:{filter_dict['to']}")

        if 'subject' in filter_dict and filter_dict['subject']:
            subject = filter_dict['subject']
            # Quote if contains spaces
            if ' ' in subject:
                query_parts.append(f'subject:"{subject}"')
            else:
                query_parts.append(f"subject:{subject}")

        if filter_dict.get('is_unread'):
            query_parts.append("is:unread")

        if filter_dict.get('is_important'):
            query_parts.append("is:important")

        if filter_dict.get('is_starred'):
            query_parts.append("is:starred")

        if filter_dict.get('has_attachment'):
            query_parts.append("has:attachment")

        if 'after' in filter_dict and filter_dict['after']:
            query_parts.append(f"after:{filter_dict['after']}")

        if 'before' in filter_dict and filter_dict['before']:
            query_parts.append(f"before:{filter_dict['before']}")

        if 'newer_than' in filter_dict and filter_dict['newer_than']:
            query_parts.append(f"newer_than:{filter_dict['newer_than']}")

        if 'older_than' in filter_dict and filter_dict['older_than']:
            query_parts.append(f"older_than:{filter_dict['older_than']}")

        # Combine query parts
        query = ' '.join(query_parts)

        if not query:
            print("Error: Empty filter - at least one filter criterion is required")
            return []

        # Use search_by_query with the constructed query
        print(f"Filter converted to query: {query}")
        return self.search_by_query(query, max_results, fetch_full=fetch_full)

    def _get_email_details(self, message_id: str, fetch_full: bool = False) -> Optional[EmailSummary]:
        """
        Get details for a specific email message.

        Args:
            message_id: Gmail message ID
            fetch_full: If True, fetch full message body

        Returns:
            EmailSummary object or None if fetch fails
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            subject = ''
            sender = ''
            date = ''

            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')

                if name == 'subject':
                    subject = value
                elif name == 'from':
                    sender = value
                elif name == 'date':
                    date = value

            snippet = message.get('snippet', '')
            body = ''

            # Extract full body if requested
            if fetch_full:
                payload = message.get('payload', {})
                body = self._extract_body_content(payload)

            return EmailSummary(
                subject=subject or 'No Subject',
                sender=sender or 'Unknown',
                date=date or 'Unknown',
                snippet=snippet,
                message_id=message_id,
                body=body
            )

        except Exception as e:
            print(f"Error fetching email {message_id}: {e}")
            return None

    def _extract_body_content(self, payload: Dict[str, Any]) -> str:
        """
        Extract body content from email payload.

        Args:
            payload: Gmail API message payload

        Returns:
            Extracted body content as string
        """
        body_content = ""

        # Handle different message structures
        if 'parts' in payload:
            # Multi-part message
            for part in payload['parts']:
                body_content += self._extract_part_content(part)
        else:
            # Single part message
            body_content = self._extract_part_content(payload)

        return body_content.strip()

    def _extract_part_content(self, part: Dict[str, Any]) -> str:
        """
        Extract content from a message part.

        Args:
            part: Gmail API message part

        Returns:
            Extracted content as string
        """
        mime_type = part.get('mimeType', '')

        # Handle nested parts (multipart/alternative, etc.)
        if 'parts' in part:
            content = ""
            for subpart in part['parts']:
                content += self._extract_part_content(subpart)
            return content

        # Extract body data
        body = part.get('body', {})
        data = body.get('data', '')

        if not data:
            return ""

        # Decode base64url encoded content
        try:
            decoded_bytes = base64.urlsafe_b64decode(data + '==')  # Add padding if needed

            # Try to decode as UTF-8, fallback to latin-1 if that fails
            try:
                content = decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = decoded_bytes.decode('latin-1', errors='ignore')
                except UnicodeDecodeError:
                    # Last resort: decode with error replacement
                    content = decoded_bytes.decode('utf-8', errors='replace')

            return content

        except Exception:
            return ""


def main():
    """Main entry point for the standalone script."""
    parser = argparse.ArgumentParser(
        description="Gmail Email Summarizer - Search and summarize emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by query
  %(prog)s --query "from:boss@company.com is:unread"

  # Search by filter
  %(prog)s --filter '{"from": "boss@company.com", "is_unread": true}'

  # Search with max results
  %(prog)s --query "is:important" --max-results 20

  # Show full message body
  %(prog)s --query "is:unread" --full

  # Export to JSON
  %(prog)s --query "is:unread" --output results.json

  # Export with full body
  %(prog)s --query "is:unread" --full --output results.json
        """
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Gmail search query (e.g., "from:example@gmail.com is:unread")'
    )

    parser.add_argument(
        '--filter', '-f',
        type=str,
        help='Filter as JSON string (e.g., \'{"from": "example@gmail.com", "is_unread": true}\')'
    )

    parser.add_argument(
        '--max-results', '-m',
        type=int,
        default=10,
        help='Maximum number of emails to return (default: 10)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path for JSON results (optional)'
    )

    parser.add_argument(
        '--credentials',
        type=str,
        default='credentials.json',
        help='Path to credentials file (default: credentials.json)'
    )

    parser.add_argument(
        '--token',
        type=str,
        default='token.json',
        help='Path to token file (default: token.json)'
    )

    parser.add_argument(
        '--full',
        action='store_true',
        help='Fetch and display full message body instead of just snippet'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.query and not args.filter:
        parser.error("Either --query or --filter must be specified")

    if args.query and args.filter:
        parser.error("Cannot specify both --query and --filter")

    # Initialize summarizer
    print("=" * 60)
    print("Gmail Email Summarizer")
    print("=" * 60)

    summarizer = EmailSummarizer(
        credentials_file=args.credentials,
        token_file=args.token
    )

    # Authenticate
    if not summarizer.authenticate():
        print("\nAuthentication failed. Exiting.")
        return 1

    print()

    # Search emails
    summaries = []

    if args.query:
        summaries = summarizer.search_by_query(args.query, args.max_results, fetch_full=args.full)
    elif args.filter:
        try:
            filter_dict = json.loads(args.filter)
            summaries = summarizer.search_by_filter(filter_dict, args.max_results, fetch_full=args.full)
        except json.JSONDecodeError as e:
            print(f"Error parsing filter JSON: {e}")
            return 1

    # Display results
    print()
    print("=" * 60)
    print(f"Results: {len(summaries)} email(s)")
    print("=" * 60)

    if summaries:
        for i, email in enumerate(summaries, 1):
            print(f"\n[{i}] From: {email.sender}")
            print(f"    Subject: {email.subject}")
            print(f"    Date: {email.date}")

            if args.full and email.body:
                print(f"    Body:")
                print("    " + "-" * 56)
                # Indent body content
                for line in email.body.split('\n'):
                    print(f"    {line}")
                print("    " + "-" * 56)
            else:
                print(f"    Snippet: {email.snippet[:100]}{'...' if len(email.snippet) > 100 else ''}")

    # Export to JSON if requested
    if args.output and summaries:
        try:
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'query': args.query if args.query else json.loads(args.filter),
                'count': len(summaries),
                'emails': [
                    {
                        'subject': email.subject,
                        'sender': email.sender,
                        'date': email.date,
                        'snippet': email.snippet,
                        'message_id': email.message_id,
                        'body': email.body if args.full else ''
                    }
                    for email in summaries
                ]
            }

            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Results exported to: {args.output}")

        except Exception as e:
            print(f"\nError exporting results: {e}")
            return 1

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
