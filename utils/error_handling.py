"""
Comprehensive error handling utilities for Gmail Email Summarizer.

This module provides retry logic, error classification, and standardized
error handling patterns for network operations, API calls, and file operations.
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Type, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for different handling strategies."""
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    API_RATE_LIMIT = "api_rate_limit"
    API_QUOTA = "api_quota"
    FILE_SYSTEM = "file_system"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0


class RetryableError(Exception):
    """Base class for errors that should trigger retry logic."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 retry_after: Optional[float] = None):
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after


class NonRetryableError(Exception):
    """Base class for errors that should not trigger retry logic."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN):
        super().__init__(message)
        self.category = category


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
        
    Returns:
        float: Delay in seconds
    """
    # Exponential backoff
    delay = config.base_delay * (config.exponential_base ** attempt) * config.backoff_factor
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RetryableError,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (NonRetryableError,)
):
    """
    Decorator for implementing retry logic with exponential backoff.
    
    Args:
        config: Retry configuration (uses default if None)
        retryable_exceptions: Tuple of exception types that should trigger retry
        non_retryable_exceptions: Tuple of exception types that should not retry
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except non_retryable_exceptions as e:
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate delay
                    if hasattr(e, 'retry_after') and e.retry_after:
                        delay = e.retry_after
                        logger.warning(f"{func.__name__} rate limited, waiting {delay}s as requested")
                    else:
                        delay = calculate_delay(attempt, config)
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    # Unexpected exception - log and re-raise
                    logger.error(f"{func.__name__} failed with unexpected error: {e}")
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"{func.__name__} failed after {config.max_attempts} attempts")
        
        return wrapper
    return decorator


def classify_error(exception: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category for appropriate handling.
    
    Args:
        exception: Exception to classify
        
    Returns:
        ErrorCategory: Classified error category
    """
    exception_str = str(exception).lower()
    exception_type = type(exception).__name__.lower()
    
    # Authentication errors
    auth_indicators = [
        'authentication', 'unauthorized', 'invalid_grant', 'token', 'credentials',
        'oauth', 'permission', 'access_denied', 'forbidden', '401', '403'
    ]
    if any(indicator in exception_str or indicator in exception_type for indicator in auth_indicators):
        return ErrorCategory.AUTHENTICATION
    
    # Rate limiting errors
    rate_limit_indicators = [
        'rate limit', 'too many requests', 'quota exceeded', 'throttled',
        '429', 'rate_limit_exceeded', 'usage_limit'
    ]
    if any(indicator in exception_str for indicator in rate_limit_indicators):
        return ErrorCategory.API_RATE_LIMIT
    
    # API quota errors
    quota_indicators = [
        'quota', 'billing', 'usage limit', 'daily limit', 'monthly limit',
        'insufficient quota', 'quota_exceeded'
    ]
    if any(indicator in exception_str for indicator in quota_indicators):
        return ErrorCategory.API_QUOTA
    
    # Network errors
    network_indicators = [
        'connection', 'network', 'timeout', 'unreachable', 'dns', 'socket',
        'ssl', 'certificate', 'handshake', 'connection reset', 'connection refused'
    ]
    if any(indicator in exception_str or indicator in exception_type for indicator in network_indicators):
        return ErrorCategory.NETWORK
    
    # File system errors
    filesystem_indicators = [
        'file not found', 'permission denied', 'disk', 'space', 'directory',
        'path', 'no such file', 'access denied', 'read-only', 'filesystem'
    ]
    if any(indicator in exception_str or indicator in exception_type for indicator in filesystem_indicators):
        return ErrorCategory.FILE_SYSTEM
    
    # Validation errors
    validation_indicators = [
        'validation', 'invalid', 'malformed', 'parse', 'format', 'schema',
        'required', 'missing', 'empty', 'null'
    ]
    if any(indicator in exception_str or indicator in exception_type for indicator in validation_indicators):
        return ErrorCategory.VALIDATION
    
    return ErrorCategory.UNKNOWN


def create_user_friendly_message(exception: Exception, context: str = "") -> str:
    """
    Create a user-friendly error message based on the exception and context.
    
    Args:
        exception: The exception that occurred
        context: Additional context about what was being done
        
    Returns:
        str: User-friendly error message
    """
    category = classify_error(exception)
    base_context = f" while {context}" if context else ""
    
    if category == ErrorCategory.AUTHENTICATION:
        return (
            f"Authentication failed{base_context}. "
            "Please check your credentials and ensure you have proper access permissions. "
            "You may need to re-authenticate or update your API keys."
        )
    
    elif category == ErrorCategory.NETWORK:
        return (
            f"Network connection failed{base_context}. "
            "Please check your internet connection and try again. "
            "If the problem persists, the service may be temporarily unavailable."
        )
    
    elif category == ErrorCategory.API_RATE_LIMIT:
        return (
            f"API rate limit exceeded{base_context}. "
            "Please wait a few minutes before trying again. "
            "Consider reducing the number of requests or upgrading your API plan."
        )
    
    elif category == ErrorCategory.API_QUOTA:
        return (
            f"API quota exceeded{base_context}. "
            "You have reached your usage limit for this service. "
            "Please check your billing settings or wait until your quota resets."
        )
    
    elif category == ErrorCategory.FILE_SYSTEM:
        return (
            f"File system error{base_context}. "
            "Please check file permissions, available disk space, and that the path exists. "
            "Ensure the application has write access to the output directory."
        )
    
    elif category == ErrorCategory.VALIDATION:
        return (
            f"Data validation failed{base_context}. "
            "Please check your input data and configuration settings. "
            "Ensure all required fields are provided and in the correct format."
        )
    
    else:
        return (
            f"An unexpected error occurred{base_context}: {str(exception)}. "
            "Please check the logs for more details and try again."
        )


def handle_gmail_api_error(exception: Exception) -> Union[RetryableError, NonRetryableError]:
    """
    Handle Gmail API specific errors and convert to appropriate error types.
    
    Args:
        exception: Gmail API exception
        
    Returns:
        Union[RetryableError, NonRetryableError]: Appropriate error type
    """
    error_str = str(exception).lower()
    
    # Check for specific Gmail API error codes
    if hasattr(exception, 'resp') and hasattr(exception.resp, 'status'):
        status_code = exception.resp.status
        
        if status_code == 401:
            return NonRetryableError(
                "Gmail authentication failed. Please re-authenticate.",
                ErrorCategory.AUTHENTICATION
            )
        elif status_code == 403:
            if 'quota' in error_str or 'limit' in error_str:
                return NonRetryableError(
                    "Gmail API quota exceeded. Please check your API usage.",
                    ErrorCategory.API_QUOTA
                )
            else:
                return NonRetryableError(
                    "Gmail API access forbidden. Check your permissions.",
                    ErrorCategory.AUTHENTICATION
                )
        elif status_code == 429:
            # Extract retry-after header if available
            retry_after = None
            if hasattr(exception.resp, 'headers'):
                retry_after = exception.resp.headers.get('Retry-After')
                if retry_after:
                    try:
                        retry_after = float(retry_after)
                    except ValueError:
                        retry_after = None
            
            return RetryableError(
                "Gmail API rate limit exceeded.",
                ErrorCategory.API_RATE_LIMIT,
                retry_after
            )
        elif status_code >= 500:
            return RetryableError(
                f"Gmail API server error (HTTP {status_code}). Service may be temporarily unavailable.",
                ErrorCategory.NETWORK
            )
        elif status_code == 404:
            return NonRetryableError(
                "Requested Gmail resource not found.",
                ErrorCategory.VALIDATION
            )
    
    # Network-related errors are generally retryable
    if any(indicator in error_str for indicator in ['connection', 'timeout', 'network', 'dns']):
        return RetryableError(
            f"Gmail API network error: {str(exception)}",
            ErrorCategory.NETWORK
        )
    
    # Default to non-retryable for unknown Gmail API errors
    return NonRetryableError(
        f"Gmail API error: {str(exception)}",
        ErrorCategory.UNKNOWN
    )


def handle_ai_api_error(exception: Exception, provider: str) -> Union[RetryableError, NonRetryableError]:
    """
    Handle AI service API errors and convert to appropriate error types.
    
    Args:
        exception: AI API exception
        provider: AI provider name ("openai" or "claude")
        
    Returns:
        Union[RetryableError, NonRetryableError]: Appropriate error type
    """
    error_str = str(exception).lower()
    
    # OpenAI specific error handling
    if provider == "openai":
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            
            if status_code == 401:
                return NonRetryableError(
                    "OpenAI API authentication failed. Please check your API key.",
                    ErrorCategory.AUTHENTICATION
                )
            elif status_code == 429:
                return RetryableError(
                    "OpenAI API rate limit exceeded.",
                    ErrorCategory.API_RATE_LIMIT,
                    retry_after=60  # Default 1 minute wait
                )
            elif status_code == 402:
                return NonRetryableError(
                    "OpenAI API quota exceeded. Please check your billing.",
                    ErrorCategory.API_QUOTA
                )
            elif status_code >= 500:
                return RetryableError(
                    f"OpenAI API server error (HTTP {status_code}).",
                    ErrorCategory.NETWORK
                )
    
    # Claude/Anthropic specific error handling
    elif provider == "claude":
        if 'authentication' in error_str or 'api key' in error_str:
            return NonRetryableError(
                "Claude API authentication failed. Please check your API key.",
                ErrorCategory.AUTHENTICATION
            )
        elif 'rate limit' in error_str or '429' in error_str:
            return RetryableError(
                "Claude API rate limit exceeded.",
                ErrorCategory.API_RATE_LIMIT,
                retry_after=60
            )
        elif 'quota' in error_str or 'billing' in error_str:
            return NonRetryableError(
                "Claude API quota exceeded. Please check your billing.",
                ErrorCategory.API_QUOTA
            )
    
    # Network-related errors are generally retryable
    if any(indicator in error_str for indicator in ['connection', 'timeout', 'network', 'dns']):
        return RetryableError(
            f"{provider.title()} API network error: {str(exception)}",
            ErrorCategory.NETWORK
        )
    
    # Default to retryable for unknown AI API errors (with limited retries)
    return RetryableError(
        f"{provider.title()} API error: {str(exception)}",
        ErrorCategory.UNKNOWN
    )


def handle_file_system_error(exception: Exception, operation: str, file_path: str) -> NonRetryableError:
    """
    Handle file system errors and convert to appropriate error types.
    
    Args:
        exception: File system exception
        operation: Description of the operation being performed
        file_path: Path to the file involved
        
    Returns:
        NonRetryableError: File system errors are generally not retryable
    """
    error_str = str(exception).lower()
    
    if 'permission denied' in error_str or 'access denied' in error_str:
        return NonRetryableError(
            f"Permission denied {operation} '{file_path}'. "
            "Please check file permissions and ensure the application has appropriate access.",
            ErrorCategory.FILE_SYSTEM
        )
    elif 'no such file' in error_str or 'file not found' in error_str:
        return NonRetryableError(
            f"File not found {operation} '{file_path}'. "
            "Please ensure the file exists and the path is correct.",
            ErrorCategory.FILE_SYSTEM
        )
    elif 'disk' in error_str or 'space' in error_str:
        return NonRetryableError(
            f"Insufficient disk space {operation} '{file_path}'. "
            "Please free up disk space and try again.",
            ErrorCategory.FILE_SYSTEM
        )
    elif 'read-only' in error_str:
        return NonRetryableError(
            f"Cannot write to read-only location '{file_path}'. "
            "Please choose a writable location or change file permissions.",
            ErrorCategory.FILE_SYSTEM
        )
    else:
        return NonRetryableError(
            f"File system error {operation} '{file_path}': {str(exception)}",
            ErrorCategory.FILE_SYSTEM
        )