#!/usr/bin/env python3
"""
Gmail Email Summarizer

A command-line tool that connects to Gmail, fetches important unread emails,
generates AI-powered summaries, and stores them in daily YAML files.
"""

import sys
import logging
import argparse
from datetime import datetime
from typing import List, Optional

# Import application modules
from config.settings import load_config, validate_gmail_credentials, ensure_output_directory
from auth.gmail_auth import GmailAuthError
from gmail_email.fetcher import create_email_fetcher, EmailFetchError
from gmail_email.processor import EmailProcessor, EmailData
from summarization.summarizer import EmailSummarizer
from storage.yaml_writer import YAMLWriter
from utils.error_handling import (
    RetryableError, NonRetryableError, ErrorCategory,
    create_user_friendly_message, classify_error
)


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Gmail Email Summarizer - Fetch and summarize important unread emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run with default settings
  %(prog)s --max-emails 10    # Process up to 10 emails
  %(prog)s --verbose          # Enable verbose logging
  %(prog)s --test-ai          # Test AI service connection only
        """
    )
    
    parser.add_argument(
        '--max-emails',
        type=int,
        help='Maximum number of emails to process (overrides config)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--test-ai',
        action='store_true',
        help='Test AI service connection and exit'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for YAML files (overrides config)'
    )
    
    return parser.parse_args()


def test_ai_connection(config) -> bool:
    """Test AI service connection."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Testing {config.ai_provider.upper()} connection...")
        summarizer = EmailSummarizer(config)
        
        if summarizer.test_ai_connection():
            logger.info("✓ AI service connection successful")
            return True
        else:
            logger.error("✗ AI service connection failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ AI service test failed: {e}")
        return False


def process_emails() -> int:
    """
    Main email processing workflow.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()
        
        # Override config with command-line arguments if provided
        if args.max_emails:
            config.max_emails_per_run = args.max_emails
        if args.output_dir:
            config.output_directory = args.output_dir
        
        # Test AI connection if requested
        if args.test_ai:
            return 0 if test_ai_connection(config) else 1
        
        # Validate Gmail credentials
        if not validate_gmail_credentials(config):
            logger.error("Gmail credentials validation failed")
            logger.error("Please ensure credentials.json file exists in the project root")
            return 1
        
        # Ensure output directory exists
        if not ensure_output_directory(config):
            logger.error("Failed to create output directory")
            return 1
        
        # Initialize components with comprehensive error handling
        try:
            logger.info("Initializing email fetcher...")
            email_fetcher = create_email_fetcher(config.credentials_file, config.token_file)
        except (GmailAuthError, EmailFetchError, RetryableError, NonRetryableError) as e:
            logger.error(create_user_friendly_message(e, "initializing Gmail connection"))
            return 1
        
        try:
            logger.info("Initializing email processor...")
            email_processor = EmailProcessor()
        except Exception as e:
            logger.error(f"Failed to initialize email processor: {e}")
            return 1
        
        try:
            logger.info("Initializing email summarizer...")
            email_summarizer = EmailSummarizer(config)
        except (RetryableError, NonRetryableError) as e:
            logger.error(create_user_friendly_message(e, "initializing AI summarization service"))
            return 1
        
        try:
            logger.info("Initializing YAML writer...")
            yaml_writer = YAMLWriter(config.output_directory)
        except NonRetryableError as e:
            logger.error(create_user_friendly_message(e, "initializing file storage"))
            return 1
        
        # Fetch important unread emails with error handling
        try:
            logger.info(f"Fetching up to {config.max_emails_per_run} important unread emails...")
            raw_emails = email_fetcher.fetch_important_unread_emails(config.max_emails_per_run)
            
            if not raw_emails:
                logger.info("No important unread emails found")
                # Create empty summary file
                try:
                    file_path = yaml_writer.create_empty_summary_file()
                    logger.info(f"Created empty summary file: {file_path}")
                    return 0
                except NonRetryableError as e:
                    logger.error(create_user_friendly_message(e, "creating empty summary file"))
                    return 1
            
            logger.info(f"Found {len(raw_emails)} important unread emails")
            
        except (EmailFetchError, RetryableError, NonRetryableError) as e:
            logger.error(create_user_friendly_message(e, "fetching emails from Gmail"))
            return 1
        
        # Process emails to extract structured data
        logger.info("Processing email content...")
        processed_emails: List[EmailData] = []
        
        for i, raw_email in enumerate(raw_emails):
            try:
                # The fetcher already extracted the data, we just need to convert it to EmailData
                from datetime import datetime
                from email.utils import parsedate_to_datetime
                
                # Parse the date
                date_str = raw_email.get('date', '')
                try:
                    if date_str:
                        email_date = parsedate_to_datetime(date_str)
                    else:
                        email_date = datetime.now()
                except (ValueError, TypeError):
                    email_date = datetime.now()
                
                # Clean the body content using the processor
                body_content = raw_email.get('body', '')
                if body_content:
                    # Use the processor's HTML cleaning capabilities
                    cleaned_body = email_processor.clean_html_content(body_content)
                    if not cleaned_body or cleaned_body.strip() == "":
                        cleaned_body = email_processor._clean_plain_text(body_content)
                else:
                    cleaned_body = "No readable content found"
                
                # Create EmailData object with the already-extracted data
                email_data = EmailData(
                    subject=raw_email.get('subject', 'No Subject'),
                    sender=raw_email.get('sender', 'Unknown Sender'),
                    date=email_date,
                    body=cleaned_body,
                    message_id=raw_email.get('message_id', '')
                )
                
                processed_emails.append(email_data)
                logger.debug(f"Processed email {i+1}: {email_data.subject}")
            except Exception as e:
                logger.warning(f"Failed to process email {i+1}: {e}")
                continue
        
        if not processed_emails:
            logger.warning("No emails could be processed successfully")
            file_path = yaml_writer.create_empty_summary_file()
            logger.info(f"Created empty summary file: {file_path}")
            return 0
        
        logger.info(f"Successfully processed {len(processed_emails)} emails")
        
        # Generate AI summaries with error handling
        try:
            logger.info("Generating AI-powered summaries...")
            email_summaries = email_summarizer.batch_summarize_emails(processed_emails)
            
            if not email_summaries:
                logger.error("Failed to generate any email summaries")
                return 1
            
            logger.info(f"Generated {len(email_summaries)} email summaries")
            
        except Exception as e:
            logger.error(f"Unexpected error during AI summarization: {e}")
            logger.info("Attempting to create fallback summaries...")
            
            # Create basic fallback summaries
            email_summaries = []
            for email_data in processed_emails:
                try:
                    fallback_summary = email_summarizer._create_fallback_summary(email_data)
                    email_summaries.append(fallback_summary)
                except Exception as fallback_error:
                    logger.error(f"Failed to create fallback summary: {fallback_error}")
            
            if not email_summaries:
                logger.error("Failed to generate any summaries, including fallbacks")
                return 1
        
        # Store summaries in YAML file with error handling
        try:
            logger.info("Storing summaries in YAML file...")
            file_path = yaml_writer.write_daily_summary(email_summaries)
        except NonRetryableError as e:
            logger.error(create_user_friendly_message(e, "storing email summaries"))
            return 1
        
        # Display summary of actions taken
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Emails processed: {len(processed_emails)}")
        logger.info(f"Summaries generated: {len(email_summaries)}")
        logger.info(f"Output file: {file_path}")
        
        # Display summary statistics
        stats = yaml_writer.get_summary_stats()
        if stats.get("exists"):
            logger.info(f"File size: {stats.get('file_size', 0)} bytes")
            logger.info(f"Total emails in file: {stats.get('email_count', 0)}")
        
        logger.info("Gmail Email Summarizer completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
    except (GmailAuthError, EmailFetchError) as e:
        # These are already handled above, but catch any that slip through
        logger.error(create_user_friendly_message(e, "processing emails"))
        return 1
    except (RetryableError, NonRetryableError) as e:
        logger.error(create_user_friendly_message(e, "processing emails"))
        if e.category == ErrorCategory.AUTHENTICATION:
            logger.error("Please check your API keys and credentials")
        elif e.category == ErrorCategory.NETWORK:
            logger.error("Please check your internet connection and try again")
        elif e.category == ErrorCategory.FILE_SYSTEM:
            logger.error("Please check file permissions and available disk space")
        return 1
    except Exception as e:
        error_category = classify_error(e)
        logger.error(create_user_friendly_message(e, "processing emails"))
        logger.debug("Full error details:", exc_info=True)
        
        # Provide specific guidance based on error category
        if error_category == ErrorCategory.AUTHENTICATION:
            logger.error("This appears to be an authentication issue. Please check your credentials.")
        elif error_category == ErrorCategory.NETWORK:
            logger.error("This appears to be a network issue. Please check your connection.")
        elif error_category == ErrorCategory.FILE_SYSTEM:
            logger.error("This appears to be a file system issue. Please check permissions and disk space.")
        
        return 1


def handle_errors(func):
    """Decorator for comprehensive error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            logging.getLogger(__name__).info("Process interrupted by user")
            return 1
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.debug("Full error details:", exc_info=True)
            return 1
    return wrapper


@handle_errors
def main():
    """Main entry point for the Gmail Email Summarizer."""
    # Parse arguments first to get verbose flag
    args = parse_arguments()
    
    # Setup logging with verbosity level
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("Gmail Email Summarizer starting...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run main processing workflow
    exit_code = process_emails()
    
    if exit_code == 0:
        logger.info("Process completed successfully")
    else:
        logger.error("Process completed with errors")
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())