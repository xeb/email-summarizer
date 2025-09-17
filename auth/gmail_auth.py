"""
Gmail OAuth2 authentication module.

This module handles OAuth2 authentication with the Gmail API, including
credential file handling, token storage, and Gmail service object creation.
"""

import os
import pickle
import json
import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from utils.error_handling import (
    retry_with_backoff, RetryConfig, RetryableError, NonRetryableError,
    ErrorCategory, handle_gmail_api_error, handle_file_system_error,
    create_user_friendly_message
)


# Gmail API scope for reading emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailAuthError(NonRetryableError):
    """Custom exception for Gmail authentication errors."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.AUTHENTICATION):
        super().__init__(message, category)


def authenticate(credentials_file: str = "credentials.json", 
                token_file: str = "token.json") -> Credentials:
    """
    Authenticate with Gmail using OAuth2 flow with comprehensive error handling.
    
    Args:
        credentials_file: Path to the OAuth2 credentials JSON file
        token_file: Path to store/retrieve the authentication token
        
    Returns:
        Authenticated credentials object
        
    Raises:
        GmailAuthError: If authentication fails
    """
    logger = logging.getLogger(__name__)
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        try:
            logger.debug(f"Loading existing token from {token_file}")
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
            logger.debug("Token loaded successfully")
        except (pickle.PickleError, EOFError, OSError) as e:
            logger.warning(f"Token file corrupted or unreadable: {e}")
            try:
                os.remove(token_file)
                logger.info("Corrupted token file removed")
            except OSError as remove_error:
                logger.warning(f"Could not remove corrupted token file: {remove_error}")
            creds = None
        except Exception as e:
            error = handle_file_system_error(e, "reading token file", token_file)
            logger.error(create_user_friendly_message(error, "loading authentication token"))
            raise GmailAuthError(str(error))
    
    # If there are no valid credentials available, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                # Try to classify the error
                if 'invalid_grant' in str(e).lower():
                    raise GmailAuthError(
                        "Authentication token has been revoked or is invalid. "
                        "Please delete the token.json file and re-authenticate.",
                        ErrorCategory.AUTHENTICATION
                    )
                elif 'network' in str(e).lower() or 'connection' in str(e).lower():
                    raise GmailAuthError(
                        "Network error while refreshing authentication. "
                        "Please check your internet connection and try again.",
                        ErrorCategory.NETWORK
                    )
                else:
                    raise GmailAuthError(f"Failed to refresh authentication token: {str(e)}")
        else:
            logger.info("No valid credentials found, starting OAuth2 flow")
            
            # Validate credentials file exists and is readable
            if not validate_credentials_file(credentials_file):
                raise GmailAuthError(
                    f"Credentials file '{credentials_file}' not found or invalid. "
                    "Please download the OAuth2 credentials JSON file from Google Cloud Console "
                    "and place it in the project root directory.",
                    ErrorCategory.VALIDATION
                )
            
            try:
                logger.info("Starting OAuth2 authentication flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("OAuth2 authentication completed successfully")
            except Exception as e:
                logger.error(f"OAuth2 flow failed: {e}")
                if 'redirect_uri_mismatch' in str(e).lower():
                    raise GmailAuthError(
                        "OAuth2 redirect URI mismatch. Please ensure your credentials file "
                        "is configured for a desktop application, not a web application.",
                        ErrorCategory.VALIDATION
                    )
                elif 'access_denied' in str(e).lower():
                    raise GmailAuthError(
                        "OAuth2 access denied. Please grant the necessary permissions "
                        "when prompted during authentication.",
                        ErrorCategory.AUTHENTICATION
                    )
                else:
                    raise GmailAuthError(f"OAuth2 authentication failed: {str(e)}")
        
        # Save the credentials for the next run
        try:
            logger.debug(f"Saving credentials to {token_file}")
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            # Set restrictive permissions on token file
            os.chmod(token_file, 0o600)
            logger.info("Authentication credentials saved successfully")
        except OSError as e:
            error = handle_file_system_error(e, "saving token file", token_file)
            logger.error(create_user_friendly_message(error, "saving authentication token"))
            raise GmailAuthError(str(error))
        except Exception as e:
            raise GmailAuthError(f"Failed to save authentication token: {str(e)}")
    
    return creds


@retry_with_backoff(
    config=RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0),
    retryable_exceptions=(RetryableError,),
    non_retryable_exceptions=(NonRetryableError, GmailAuthError)
)
def get_gmail_service(credentials_file: str = "credentials.json",
                     token_file: str = "token.json") -> Resource:
    """
    Create and return a Gmail API service object with retry logic.
    
    Args:
        credentials_file: Path to the OAuth2 credentials JSON file
        token_file: Path to store/retrieve the authentication token
        
    Returns:
        Gmail API service object
        
    Raises:
        GmailAuthError: If authentication or service creation fails
        RetryableError: If a retryable error occurs (handled by retry decorator)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Authenticating with Gmail API")
        creds = authenticate(credentials_file, token_file)
        
        logger.debug("Building Gmail API service")
        service = build('gmail', 'v1', credentials=creds)
        
        # Test the connection by making a simple API call
        logger.debug("Testing Gmail API connection")
        try:
            profile = service.users().getProfile(userId='me').execute()
            logger.info(f"Gmail API connection successful for {profile.get('emailAddress', 'unknown')}")
        except HttpError as e:
            # Convert Gmail API error to appropriate error type
            converted_error = handle_gmail_api_error(e)
            logger.error(f"Gmail API connection test failed: {converted_error}")
            raise converted_error
        
        return service
        
    except (GmailAuthError, RetryableError, NonRetryableError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating Gmail service: {e}")
        raise GmailAuthError(f"Failed to create Gmail service: {str(e)}")


def validate_credentials_file(credentials_file: str = "credentials.json") -> bool:
    """
    Validate that the credentials file exists and contains valid OAuth2 configuration.
    
    Args:
        credentials_file: Path to the OAuth2 credentials JSON file
        
    Returns:
        True if credentials file is valid, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(credentials_file):
        logger.error(f"Credentials file does not exist: {credentials_file}")
        return False
    
    try:
        with open(credentials_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Basic validation - check for required OAuth2 fields
        if 'installed' in data:
            client_config = data['installed']
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            
            for field in required_fields:
                if field not in client_config:
                    logger.error(f"Missing required field '{field}' in credentials file")
                    return False
            
            logger.debug("Credentials file validation successful (installed app)")
            return True
            
        elif 'web' in data:
            logger.warning("Web application credentials detected. Desktop application credentials recommended.")
            client_config = data['web']
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            
            for field in required_fields:
                if field not in client_config:
                    logger.error(f"Missing required field '{field}' in credentials file")
                    return False
            
            logger.debug("Credentials file validation successful (web app)")
            return True
        else:
            logger.error("Invalid credentials file format. Must contain 'installed' or 'web' configuration.")
            return False
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in credentials file: {e}")
        return False
    except OSError as e:
        logger.error(f"Cannot read credentials file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating credentials file: {e}")
        return False


def validate_credentials(credentials_file: str = "credentials.json") -> bool:
    """
    Legacy function name for backward compatibility.
    
    Args:
        credentials_file: Path to the OAuth2 credentials JSON file
        
    Returns:
        True if credentials file is valid, False otherwise
    """
    return validate_credentials_file(credentials_file)