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
Gmail Authentication Script for Email Summarizer

This script handles OAuth2 authentication for Gmail API access.
It can be run with: uv run scripts/email_summarizer_auth.py

After successful authentication, it saves the token to token.json
which can then be used by email_summarizer.py.
"""

import os
import sys
import pickle
import argparse

# Third-party imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
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


def authenticate(credentials_file: str = "credentials.json",
                token_file: str = "token.json",
                headless: bool = False,
                force_reauth: bool = False) -> bool:
    """
    Authenticate with Gmail using OAuth2 flow.

    Args:
        credentials_file: Path to the OAuth2 credentials JSON file
        token_file: Path to store/retrieve the authentication token
        headless: If True, use manual URL entry for headless environments
        force_reauth: If True, force re-authentication even if token exists

    Returns:
        bool: True if authentication successful, False otherwise
    """
    creds = None

    # Resolve file paths
    credentials_file = find_file(credentials_file)
    token_file = find_file(token_file)

    # Load existing token if available and not forcing reauth
    if os.path.exists(token_file) and not force_reauth:
        try:
            print(f"Loading existing token from {token_file}...")
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
            print("✓ Token loaded successfully")
        except Exception as e:
            print(f"Warning: Token file corrupted or unreadable: {e}")
            creds = None

    # Check if credentials are valid
    if creds and creds.valid and not force_reauth:
        print("✓ Existing credentials are valid")
        print("\nTesting connection...")
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            print(f"✓ Successfully authenticated as: {profile.get('emailAddress', 'unknown')}")
            return True
        except Exception as e:
            print(f"Error testing connection: {e}")
            creds = None

    # Refresh expired credentials
    if creds and creds.expired and creds.refresh_token and not force_reauth:
        print("Refreshing expired credentials...")
        try:
            creds.refresh(Request())
            print("✓ Credentials refreshed successfully")
        except Exception as e:
            print(f"Error refreshing credentials: {e}")
            print("Will attempt full re-authentication...")
            creds = None

    # Full authentication if no valid credentials
    if not creds:
        if not os.path.exists(credentials_file):
            print(f"Error: Credentials file not found: {credentials_file}")
            print("\nTo obtain credentials:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a project or select an existing one")
            print("3. Enable the Gmail API")
            print("4. Create OAuth2 credentials (Desktop application)")
            print("5. Download the credentials JSON file")
            print(f"6. Save it as '{credentials_file}' in the current directory")
            return False

        print("\nStarting OAuth2 authentication flow...")
        print("=" * 60)

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES
            )

            if headless:
                print("Using headless authentication mode")
                print("=" * 60)

                # Check if we're in an interactive terminal
                is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

                if is_interactive:
                    print("\nManual authorization required:")
                    print("-" * 60)

                    # Find an available port
                    import socket
                    sock = socket.socket()
                    sock.bind(('', 0))
                    port = sock.getsockname()[1]
                    sock.close()

                    # Set the redirect URI
                    redirect_uri = f'http://localhost:{port}/'
                    flow.redirect_uri = redirect_uri

                    # Get the authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')

                    print("\n1. Open this URL in your browser:")
                    print(f"\n   {auth_url}\n")
                    print("2. Complete the authorization")
                    print("3. Copy the ENTIRE redirect URL from your browser")
                    print(f"   (should start with 'http://localhost:{port}/')")
                    print("-" * 60)

                    # Prompt for the authorization response
                    try:
                        auth_response = input("\nPaste the redirect URL here: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n\nAuthentication cancelled by user")
                        return False

                    if not auth_response:
                        print("Error: No URL provided")
                        return False

                    try:
                        # Process the authorization response
                        flow.fetch_token(authorization_response=auth_response)
                        creds = flow.credentials
                        print("\n✓ Authorization successful!")
                    except Exception as auth_error:
                        print(f"\nError processing authorization: {auth_error}")
                        print("Please ensure you copied the complete URL")
                        return False
                else:
                    print("Non-interactive environment detected")
                    print("Will attempt local server method...")
                    creds = flow.run_local_server(
                        port=0,
                        open_browser=False,
                        authorization_prompt_message=(
                            '\nPlease visit this URL to authorize:\n{url}\n\n'
                            'Waiting for authorization...\n'
                        )
                    )
            else:
                print("Using browser-based authentication")
                print("=" * 60)
                print("\nYour browser will open automatically.")
                print("Please complete the authorization process.")
                print("-" * 60)

                creds = flow.run_local_server(port=0)

            print("\n✓ OAuth2 authentication completed successfully")

        except Exception as e:
            print(f"\nAuthentication failed: {e}")
            if 'could not locate runnable browser' in str(e).lower():
                print("\nNo browser available. Try using --headless flag:")
                print("  uv run scripts/email_summarizer_auth.py --headless")
            return False

    # Save the credentials
    try:
        print(f"\nSaving credentials to {token_file}...")
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

        # Set restrictive permissions
        os.chmod(token_file, 0o600)

        print("✓ Credentials saved successfully")
        print(f"✓ Token file: {token_file}")

        # Test the connection
        print("\nTesting Gmail API connection...")
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()

        print("=" * 60)
        print("AUTHENTICATION SUCCESS")
        print("=" * 60)
        print(f"Email: {profile.get('emailAddress', 'unknown')}")
        print(f"Total messages: {profile.get('messagesTotal', 0)}")
        print(f"Total threads: {profile.get('threadsTotal', 0)}")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nError saving credentials: {e}")
        return False


def main():
    """Main entry point for the authentication script."""
    parser = argparse.ArgumentParser(
        description="Gmail Authentication for Email Summarizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic authentication
  %(prog)s

  # Headless authentication (for SSH/servers)
  %(prog)s --headless

  # Force re-authentication
  %(prog)s --force

  # Custom credentials file
  %(prog)s --credentials my-credentials.json
        """
    )

    parser.add_argument(
        '--credentials',
        type=str,
        default='credentials.json',
        help='Path to OAuth2 credentials file (default: credentials.json)'
    )

    parser.add_argument(
        '--token',
        type=str,
        default='token.json',
        help='Path to save authentication token (default: token.json)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Use headless authentication for SSH/server environments'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-authentication even if valid token exists'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Gmail Email Summarizer - Authentication")
    print("=" * 60)
    print()

    if args.force:
        print("Force re-authentication requested")
        if os.path.exists(args.token):
            print(f"Removing existing token: {args.token}")
            try:
                os.remove(args.token)
            except Exception as e:
                print(f"Warning: Could not remove token file: {e}")
        print()

    # Authenticate
    success = authenticate(
        credentials_file=args.credentials,
        token_file=args.token,
        headless=args.headless,
        force_reauth=args.force
    )

    if success:
        print("\nYou can now use email_summarizer.py:")
        print("  uv run scripts/email_summarizer.py --query \"is:unread\"")
        print()
        return 0
    else:
        print("\nAuthentication failed. Please try again.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
