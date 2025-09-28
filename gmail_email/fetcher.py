"""
Gmail email fetching module.

This module handles retrieving emails from Gmail using the Gmail API,
specifically filtering for important unread emails and extracting their content.
"""

import logging
import base64
import re
from typing import List, Dict, Optional, Any, Tuple
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from auth.gmail_auth import get_gmail_service, GmailAuthError
from utils.error_handling import (
    retry_with_backoff, RetryConfig, RetryableError, NonRetryableError,
    ErrorCategory, handle_gmail_api_error, create_user_friendly_message
)


class EmailFetchError(NonRetryableError):
    """Custom exception for email fetching errors."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN):
        super().__init__(message, category)


class QueryValidationError(NonRetryableError):
    """Custom exception for Gmail query validation errors."""
    def __init__(self, message: str, suggestions: List[str] = None):
        super().__init__(message, ErrorCategory.VALIDATION)
        self.suggestions = suggestions or []


class EmailFetcher:
    """Handles fetching emails from Gmail API."""
    
    # Supported Gmail search operators for validation
    SUPPORTED_OPERATORS = [
        'from:', 'to:', 'subject:', 'has:', 'is:', 'in:',
        'after:', 'before:', 'older_than:', 'newer_than:',
        'size:', 'larger:', 'smaller:', 'filename:', 'label:',
        'category:', 'deliveredto:', 'cc:', 'bcc:', 'rfc822msgid:'
    ]
    
    # Common Gmail search values for validation
    VALID_IS_VALUES = ['unread', 'read', 'important', 'starred', 'snoozed', 'sent', 'draft', 'chat']
    VALID_HAS_VALUES = ['attachment', 'nouserlabels', 'userlabels', 'yellow-star', 'blue-info', 'red-bang', 'orange-guillemet', 'red-star', 'purple-star', 'green-star']
    VALID_IN_VALUES = ['inbox', 'trash', 'spam', 'unread', 'starred', 'sent', 'draft', 'important', 'chats', 'all', 'anywhere']
    
    def __init__(self, gmail_service: Resource):
        """
        Initialize the EmailFetcher with a Gmail service object.
        
        Args:
            gmail_service: Authenticated Gmail API service object
        """
        self.service = gmail_service
        self.logger = logging.getLogger(__name__)
    
    def validate_gmail_query(self, query: str) -> Tuple[bool, str]:
        """
        Validate Gmail search query syntax and provide helpful error messages.
        
        This method implements requirement 5.1: validate query syntax and display
        helpful error messages for invalid queries.
        
        Args:
            query: Gmail search query string to validate
            
        Returns:
            Tuple of (is_valid, error_message_or_empty_string)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        query = query.strip()
        suggestions = []
        
        # Check for basic syntax issues
        if query.count('"') % 2 != 0:
            return False, "Unmatched quotes in query. Make sure all quoted phrases are properly closed."
        
        # Split query into tokens for analysis
        tokens = re.findall(r'[^\s"]+|"[^"]*"', query)
        
        for token in tokens:
            # Skip quoted phrases and simple words
            if token.startswith('"') and token.endswith('"'):
                continue
            if ':' not in token:
                continue
                
            # Check operator syntax
            if ':' in token:
                operator, value = token.split(':', 1)
                operator_with_colon = operator + ':'
                
                # Check if operator is supported
                if operator_with_colon not in self.SUPPORTED_OPERATORS:
                    # Find similar operators for suggestions
                    similar_ops = [op for op in self.SUPPORTED_OPERATORS if op.startswith(operator[:2])]
                    suggestion_text = f" Did you mean: {', '.join(similar_ops)}?" if similar_ops else ""
                    return False, f"Unsupported search operator '{operator_with_colon}'.{suggestion_text}"
                
                # Validate specific operator values
                if operator == 'is' and value not in self.VALID_IS_VALUES:
                    return False, f"Invalid value '{value}' for 'is:' operator. Valid values: {', '.join(self.VALID_IS_VALUES)}"
                
                if operator == 'has' and value not in self.VALID_HAS_VALUES:
                    return False, f"Invalid value '{value}' for 'has:' operator. Valid values: {', '.join(self.VALID_HAS_VALUES)}"
                
                if operator == 'in' and value not in self.VALID_IN_VALUES:
                    return False, f"Invalid value '{value}' for 'in:' operator. Valid values: {', '.join(self.VALID_IN_VALUES)}"
                
                # Validate date formats for date operators
                if operator in ['after', 'before']:
                    if not self._validate_date_format(value):
                        return False, f"Invalid date format '{value}' for '{operator}:' operator. Use YYYY/MM/DD or YYYY-MM-DD format."
                
                # Validate relative date formats
                if operator in ['newer_than', 'older_than']:
                    if not self._validate_relative_date_format(value):
                        return False, f"Invalid relative date format '{value}' for '{operator}:' operator. Use format like '7d', '2w', '1m', '1y'."
                
                # Validate size formats
                if operator in ['larger', 'smaller', 'size']:
                    if not self._validate_size_format(value):
                        return False, f"Invalid size format '{value}' for '{operator}:' operator. Use format like '10M', '5K', '1G'."
        
        return True, ""
    
    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format for Gmail date operators."""
        # Gmail accepts YYYY/MM/DD and YYYY-MM-DD formats
        # More strict validation to prevent invalid dates like 2024-13-01
        date_patterns = [
            r'^\d{4}[/-](0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])$',  # YYYY/MM/DD or YYYY-MM-DD with valid months/days
            r'^\d{4}[/-](0?[1-9]|1[0-2])$',                            # YYYY/MM or YYYY-MM with valid months
            r'^\d{4}$'                                                  # YYYY
        ]
        return any(re.match(pattern, date_str) for pattern in date_patterns)
    
    def _validate_relative_date_format(self, date_str: str) -> bool:
        """Validate relative date format for Gmail relative date operators."""
        # Gmail accepts formats like 7d, 2w, 1m, 1y
        return bool(re.match(r'^\d+[dwmy]$', date_str))
    
    def _validate_size_format(self, size_str: str) -> bool:
        """Validate size format for Gmail size operators."""
        # Gmail accepts formats like 10M, 5K, 1G
        return bool(re.match(r'^\d+[KMG]?$', size_str, re.IGNORECASE))

    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError, EmailFetchError, QueryValidationError)
    )
    def fetch_emails_with_query(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail using a custom search query with comprehensive error handling.
        
        This method implements requirements 1.1, 1.3, 3.2, and 5.1: accept custom Gmail
        search queries, validate them, and fetch matching emails.
        
        Args:
            query: Gmail search query string (e.g., "from:sender@domain.com is:unread")
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with full content
            
        Raises:
            QueryValidationError: If the query syntax is invalid
            EmailFetchError: If fetching emails fails
            RetryableError: If a retryable error occurs (handled by retry decorator)
        """
        try:
            self.logger.info(f"Fetching emails with custom query: {query}")
            
            # Validate query syntax before making API calls (requirement 5.1)
            is_valid, error_message = self.validate_gmail_query(query)
            if not is_valid:
                raise QueryValidationError(f"Invalid Gmail search query: {error_message}")
            
            # Get list of message IDs with pagination handling
            message_ids = self._get_message_ids(query, max_results)
            
            if not message_ids:
                self.logger.info(f"No emails found for query: {query}")
                return []
            
            self.logger.info(f"Found {len(message_ids)} emails matching query: {query}")
            
            # Fetch full content for each email
            emails = []
            failed_count = 0
            
            for i, message_id in enumerate(message_ids):
                try:
                    self.logger.debug(f"Fetching email {i+1}/{len(message_ids)}: {message_id}")
                    email_content = self.get_email_content(message_id)
                    if email_content:
                        emails.append(email_content)
                except (RetryableError, NonRetryableError) as e:
                    failed_count += 1
                    self.logger.warning(f"Failed to fetch email {message_id}: {e}")
                    # Continue with other emails rather than failing completely
                    continue
                except Exception as e:
                    failed_count += 1
                    self.logger.warning(f"Unexpected error fetching email {message_id}: {e}")
                    continue
            
            if failed_count > 0:
                self.logger.warning(f"Failed to fetch {failed_count} out of {len(message_ids)} emails")
            
            self.logger.info(f"Successfully fetched {len(emails)} emails with custom query")
            return emails
            
        except QueryValidationError:
            # Re-raise validation errors
            raise
        except HttpError as e:
            # Convert Gmail API error to appropriate error type
            converted_error = handle_gmail_api_error(e)
            self.logger.error(f"Gmail API error while fetching emails with query '{query}': {converted_error}")
            raise converted_error
        except (RetryableError, NonRetryableError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error while fetching emails with query '{query}': {e}"
            self.logger.error(error_msg)
            raise EmailFetchError(error_msg, ErrorCategory.UNKNOWN)

    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError, EmailFetchError)
    )
    def fetch_important_unread_emails(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch important unread emails from Gmail with comprehensive error handling.
        
        This method maintains backward compatibility while using the new custom query
        functionality internally. It implements requirement 2.1: filter for messages 
        that are both unread AND marked as important.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with full content
            
        Raises:
            EmailFetchError: If fetching emails fails
            RetryableError: If a retryable error occurs (handled by retry decorator)
        """
        # Use the new fetch_emails_with_query method for consistency
        # Gmail API query for important unread emails (requirement 2.1)
        # query = "is:unread is:important"
        query = "is:important is:unread"
        
        self.logger.info("Fetching important unread emails using default query...")
        return self.fetch_emails_with_query(query, max_results)
    
    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=1.0, max_delay=20.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError,)
    )
    def _get_message_ids(self, query: str, max_results: int) -> List[str]:
        """
        Get message IDs using Gmail API with pagination support and retry logic.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of message IDs to retrieve
            
        Returns:
            List of message IDs
            
        Raises:
            RetryableError: If a retryable Gmail API error occurs
            NonRetryableError: If a non-retryable Gmail API error occurs
        """
        message_ids = []
        next_page_token = None
        
        try:
            while len(message_ids) < max_results:
                # Calculate how many results to request in this batch
                batch_size = min(500, max_results - len(message_ids))  # Gmail API max is 500
                
                # Make API call with pagination
                request_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': batch_size
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                self.logger.debug(f"Requesting {batch_size} message IDs (total so far: {len(message_ids)})")
                result = self.service.users().messages().list(**request_params).execute()
                
                # Extract message IDs from this batch
                messages = result.get('messages', [])
                batch_ids = [msg['id'] for msg in messages]
                message_ids.extend(batch_ids)
                
                self.logger.debug(f"Retrieved {len(batch_ids)} message IDs in this batch")
                
                # Check if there are more pages
                next_page_token = result.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Return only the requested number of results
            return message_ids[:max_results]
            
        except HttpError as e:
            # Convert Gmail API error to appropriate error type
            converted_error = handle_gmail_api_error(e)
            self.logger.error(f"Gmail API error getting message IDs: {converted_error}")
            raise converted_error
        except Exception as e:
            self.logger.error(f"Unexpected error getting message IDs: {e}")
            raise RetryableError(f"Unexpected error getting message IDs: {e}", ErrorCategory.UNKNOWN)
    
    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=0.5, max_delay=15.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError,)
    )
    def get_email_content(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full email content for a specific message ID with retry logic.
        
        This method implements requirements 2.2 and 2.3: retrieve full content
        including subject, sender, and body.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing email data or None if fetch fails
            
        Raises:
            RetryableError: If a retryable Gmail API error occurs
            NonRetryableError: If a non-retryable Gmail API error occurs
        """
        try:
            self.logger.debug(f"Fetching content for message ID: {message_id}")
            
            # Get full message content
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract email metadata and content
            email_data = self._extract_email_data(message)
            email_data['message_id'] = message_id
            
            self.logger.debug(f"Successfully extracted email data for {message_id}")
            return email_data
            
        except HttpError as e:
            if e.resp.status == 404:
                self.logger.warning(f"Message {message_id} not found (may have been deleted)")
                return None
            else:
                # Convert Gmail API error to appropriate error type
                converted_error = handle_gmail_api_error(e)
                self.logger.error(f"Gmail API error retrieving message {message_id}: {converted_error}")
                raise converted_error
        except Exception as e:
            error_msg = f"Unexpected error retrieving message {message_id}: {e}"
            self.logger.error(error_msg)
            raise RetryableError(error_msg, ErrorCategory.UNKNOWN)
    
    def _extract_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from Gmail API message response.
        
        Args:
            message: Gmail API message object
            
        Returns:
            Dictionary with extracted email data
        """
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract headers
        email_data = {
            'subject': '',
            'sender': '',
            'date': '',
            'body': '',
            'snippet': message.get('snippet', ''),
            'thread_id': message.get('threadId', ''),
            'label_ids': message.get('labelIds', [])
        }
        
        # Parse headers
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name == 'subject':
                email_data['subject'] = value
            elif name == 'from':
                email_data['sender'] = value
            elif name == 'date':
                email_data['date'] = value
        
        # Extract body content
        email_data['body'] = self._extract_body_content(payload)
        
        return email_data
    
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
                    self.logger.warning(f"Used error replacement for message part decoding")
            
            return content
            
        except Exception as e:
            self.logger.warning(f"Failed to decode message part: {e}")
            return ""


def create_email_fetcher(credentials_file: str = "credentials.json",
                        token_file: str = "token.json",
                        headless: bool = False) -> EmailFetcher:
    """
    Create and return an EmailFetcher instance with authenticated Gmail service.

    Args:
        credentials_file: Path to OAuth2 credentials file
        token_file: Path to token storage file
        headless: If True, use device code flow for headless environments

    Returns:
        EmailFetcher instance

    Raises:
        EmailFetchError: If authentication or service creation fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Creating email fetcher with Gmail service")
        gmail_service = get_gmail_service(credentials_file, token_file, headless)
        fetcher = EmailFetcher(gmail_service)
        logger.info("Email fetcher created successfully")
        return fetcher
    except GmailAuthError as e:
        error_msg = f"Gmail authentication failed: {e}"
        logger.error(error_msg)
        raise EmailFetchError(error_msg, ErrorCategory.AUTHENTICATION)
    except (RetryableError, NonRetryableError) as e:
        error_msg = f"Failed to create Gmail service: {e}"
        logger.error(error_msg)
        raise EmailFetchError(error_msg, e.category)
    except Exception as e:
        error_msg = f"Unexpected error creating email fetcher: {e}"
        logger.error(error_msg)
        raise EmailFetchError(error_msg, ErrorCategory.UNKNOWN)