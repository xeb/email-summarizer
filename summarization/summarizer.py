"""
AI-powered email summarization module.

This module provides functionality to summarize email content using AI services
like OpenAI and Claude, with structured output parsing and fallback handling.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import AI service clients
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Install with: pip install openai")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not available. Install with: pip install anthropic")

from gmail_email.processor import EmailData
from config.settings import Config
from utils.error_handling import (
    retry_with_backoff, RetryConfig, RetryableError, NonRetryableError,
    ErrorCategory, handle_ai_api_error, create_user_friendly_message
)


@dataclass
class EmailSummary:
    """Structured representation of an email summary."""
    subject: str
    sender: str
    date: str
    key_points: List[str]
    action_items: List[str]
    summary: str
    priority: str = "Medium"


class EmailSummarizer:
    """Handles AI-powered email summarization with multiple provider support."""
    
    def __init__(self, config: Config):
        """
        Initialize the email summarizer with configuration.
        
        Args:
            config: Configuration object containing AI service settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI clients based on configuration
        self._init_ai_clients()
    
    def _init_ai_clients(self):
        """Initialize AI service clients based on configuration with error handling."""
        self.openai_client = None
        self.claude_client = None
        
        if self.config.ai_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise NonRetryableError(
                    "OpenAI library not available. Install with: pip install openai",
                    ErrorCategory.VALIDATION
                )
            
            if not self.config.openai_api_key:
                raise NonRetryableError(
                    "OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
                    ErrorCategory.AUTHENTICATION
                )
            
            try:
                self.openai_client = openai.OpenAI(api_key=self.config.openai_api_key)
                self.logger.info("OpenAI client initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize OpenAI client: {e}"
                self.logger.error(error_msg)
                raise NonRetryableError(error_msg, ErrorCategory.AUTHENTICATION)
        
        elif self.config.ai_provider == "claude":
            if not ANTHROPIC_AVAILABLE:
                raise NonRetryableError(
                    "Anthropic library not available. Install with: pip install anthropic",
                    ErrorCategory.VALIDATION
                )
            
            if not self.config.claude_api_key:
                raise NonRetryableError(
                    "Claude API key not configured. Set CLAUDE_API_KEY environment variable.",
                    ErrorCategory.AUTHENTICATION
                )
            
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.config.claude_api_key)
                self.logger.info("Claude client initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize Claude client: {e}"
                self.logger.error(error_msg)
                raise NonRetryableError(error_msg, ErrorCategory.AUTHENTICATION)
        else:
            raise NonRetryableError(
                f"Unsupported AI provider: {self.config.ai_provider}. Must be 'openai' or 'claude'.",
                ErrorCategory.VALIDATION
            )
    
    def summarize_email(self, email_data: EmailData) -> EmailSummary:
        """
        Generate a structured summary of an email using AI with comprehensive error handling.
        
        Args:
            email_data: Structured email data to summarize
            
        Returns:
            EmailSummary: Structured summary with key points and action items
        """
        try:
            self.logger.debug(f"Summarizing email: {email_data.subject}")
            
            # Prepare content for AI processing
            content = self._prepare_email_content(email_data)
            
            # Generate AI summary with retry logic
            ai_response = self._call_ai_service(content)
            
            # Parse AI response into structured format
            parsed_response = self._parse_ai_response(ai_response)
            
            # Create EmailSummary object
            summary = EmailSummary(
                subject=email_data.subject,
                sender=email_data.sender,
                date=email_data.date.isoformat(),
                summary=parsed_response.get("summary", "Unable to generate summary"),
                key_points=parsed_response.get("key_points", []),
                action_items=parsed_response.get("action_items", []),
                priority=parsed_response.get("priority", "Medium")
            )
            
            self.logger.debug(f"Successfully summarized email: {email_data.subject}")
            return summary
            
        except (RetryableError, NonRetryableError) as e:
            self.logger.warning(f"AI summarization failed for email {email_data.message_id}: {e}")
            self.logger.info("Falling back to basic summary generation")
            return self._create_fallback_summary(email_data)
        except Exception as e:
            self.logger.error(f"Unexpected error summarizing email {email_data.message_id}: {e}")
            return self._create_fallback_summary(email_data)
    
    def _prepare_email_content(self, email_data: EmailData) -> str:
        """
        Prepare email content for AI processing by truncating if necessary.
        
        Args:
            email_data: Email data to prepare
            
        Returns:
            str: Prepared content string
        """
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        max_content_length = (self.config.max_tokens - 200) * 4  # Reserve tokens for prompt and response
        
        content = f"Subject: {email_data.subject}\nFrom: {email_data.sender}\nContent: {email_data.body}"
        
        if len(content) > max_content_length:
            # Truncate content intelligently
            truncated_body = email_data.body[:max_content_length - len(f"Subject: {email_data.subject}\nFrom: {email_data.sender}\nContent: ")]
            content = f"Subject: {email_data.subject}\nFrom: {email_data.sender}\nContent: {truncated_body}..."
            self.logger.warning(f"Email content truncated for AI processing: {email_data.message_id}")
        
        return content
    
    def _call_ai_service(self, content: str) -> str:
        """
        Call the configured AI service to generate a summary.
        
        Args:
            content: Email content to summarize
            
        Returns:
            str: AI-generated response
        """
        if self.config.ai_provider == "openai":
            return self._call_openai_api(content)
        elif self.config.ai_provider == "claude":
            return self._call_claude_api(content)
        else:
            raise ValueError(f"Unsupported AI provider: {self.config.ai_provider}")
    
    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=2.0, max_delay=120.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError,)
    )
    def _call_openai_api(self, content: str) -> str:
        """
        Call OpenAI API to generate email summary with retry logic and error handling.
        
        Args:
            content: Email content to summarize
            
        Returns:
            str: OpenAI API response
            
        Raises:
            RetryableError: If a retryable API error occurs
            NonRetryableError: If a non-retryable API error occurs
        """
        if not self.openai_client:
            raise NonRetryableError(
                "OpenAI client not initialized",
                ErrorCategory.VALIDATION
            )
        
        prompt = self._create_summarization_prompt(content)
        
        try:
            self.logger.debug("Making OpenAI API request")
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert email assistant that creates concise, structured summaries of emails."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise NonRetryableError(
                    "OpenAI API returned empty response",
                    ErrorCategory.API_RATE_LIMIT
                )
            
            result = response.choices[0].message.content.strip()
            self.logger.debug("OpenAI API request successful")
            return result
            
        except Exception as e:
            # Convert to appropriate error type
            converted_error = handle_ai_api_error(e, "openai")
            self.logger.error(f"OpenAI API call failed: {converted_error}")
            raise converted_error
    
    @retry_with_backoff(
        config=RetryConfig(max_attempts=3, base_delay=2.0, max_delay=120.0),
        retryable_exceptions=(RetryableError,),
        non_retryable_exceptions=(NonRetryableError,)
    )
    def _call_claude_api(self, content: str) -> str:
        """
        Call Claude API to generate email summary with retry logic and error handling.
        
        Args:
            content: Email content to summarize
            
        Returns:
            str: Claude API response
            
        Raises:
            RetryableError: If a retryable API error occurs
            NonRetryableError: If a non-retryable API error occurs
        """
        if not self.claude_client:
            raise NonRetryableError(
                "Claude client not initialized",
                ErrorCategory.VALIDATION
            )
        
        prompt = self._create_summarization_prompt(content)
        
        try:
            self.logger.debug("Making Claude API request")
            response = self.claude_client.messages.create(
                model=self.config.claude_model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if not response.content or not response.content[0].text:
                raise NonRetryableError(
                    "Claude API returned empty response",
                    ErrorCategory.API_RATE_LIMIT
                )
            
            result = response.content[0].text.strip()
            self.logger.debug("Claude API request successful")
            return result
            
        except Exception as e:
            # Convert to appropriate error type
            converted_error = handle_ai_api_error(e, "claude")
            self.logger.error(f"Claude API call failed: {converted_error}")
            raise converted_error
    
    def _create_summarization_prompt(self, content: str) -> str:
        """
        Create a structured prompt for AI summarization.
        
        Args:
            content: Email content to include in prompt
            
        Returns:
            str: Formatted prompt for AI service
        """
        return f"""Analyze this email and provide a structured summary in the following format:

{content}

Please respond with the following structure:

SUMMARY: [Provide a concise 2-3 sentence summary of the email's main purpose and content]

KEY_POINTS:
- [List the main points, decisions, or information from the email]
- [Each point should be clear and actionable]
- [Include important details like dates, names, amounts, etc.]

ACTION_ITEMS:
- [List specific actions that need to be taken]
- [Include deadlines if mentioned]
- [Be specific about who needs to do what]

PRIORITY: [Assess as High, Medium, or Low based on urgency indicators, deadlines, or sender importance]

Guidelines:
- Keep the summary concise but informative
- Focus on actionable information
- Preserve important details like dates, names, and numbers
- If no action items are present, write "None identified"
- Base priority on urgency words, deadlines, sender authority, and content importance
"""
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parse structured AI response into components.
        
        Args:
            response: Raw AI response text
            
        Returns:
            Dict containing parsed summary components
        """
        parsed = {
            "summary": "",
            "key_points": [],
            "action_items": [],
            "priority": "Medium"
        }
        
        try:
            # Extract summary
            summary_match = re.search(r'SUMMARY:\s*(.*?)(?=\n\n|\nKEY_POINTS:|$)', response, re.DOTALL)
            if summary_match:
                parsed["summary"] = summary_match.group(1).strip()
            
            # Extract key points
            key_points_match = re.search(r'KEY_POINTS:\s*(.*?)(?=\n\n|\nACTION_ITEMS:|$)', response, re.DOTALL)
            if key_points_match:
                key_points_text = key_points_match.group(1).strip()
                parsed["key_points"] = self._extract_bullet_points(key_points_text)
            
            # Extract action items
            action_items_match = re.search(r'ACTION_ITEMS:\s*(.*?)(?=\n\n|\nPRIORITY:|$)', response, re.DOTALL)
            if action_items_match:
                action_items_text = action_items_match.group(1).strip()
                parsed["action_items"] = self._extract_bullet_points(action_items_text)
            
            # Extract priority
            priority_match = re.search(r'PRIORITY:\s*(High|Medium|Low)', response, re.IGNORECASE)
            if priority_match:
                parsed["priority"] = priority_match.group(1).capitalize()
            
        except Exception as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            # Return partial parsing results
        
        return parsed
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """
        Extract bullet points from text.
        
        Args:
            text: Text containing bullet points
            
        Returns:
            List of bullet point strings
        """
        if not text or text.lower().strip() in ["none", "none identified", "n/a"]:
            return []
        
        # Split by lines and extract bullet points
        lines = text.split('\n')
        bullet_points = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                # Remove bullet character and clean up
                point = re.sub(r'^[-•*]\s*', '', line).strip()
                if point:
                    bullet_points.append(point)
        
        return bullet_points
    
    def _create_fallback_summary(self, email_data: EmailData) -> EmailSummary:
        """
        Create a basic fallback summary when AI processing fails.
        
        Args:
            email_data: Original email data
            
        Returns:
            EmailSummary: Basic summary without AI processing
        """
        # Create a simple summary based on subject and basic content analysis
        summary = f"Email from {email_data.sender} regarding: {email_data.subject}"
        
        # Extract basic key points from content
        key_points = []
        if email_data.body:
            # Simple heuristic: first few sentences as key points
            sentences = email_data.body.split('.')[:3]
            key_points = [s.strip() for s in sentences if s.strip()]
        
        # Look for basic action indicators
        action_items = []
        action_keywords = ['please', 'need', 'required', 'deadline', 'by', 'asap', 'urgent']
        if any(keyword in email_data.body.lower() for keyword in action_keywords):
            action_items.append("Review email content for specific actions needed")
        
        return EmailSummary(
            subject=email_data.subject,
            sender=email_data.sender,
            date=email_data.date.isoformat(),
            summary=summary,
            key_points=key_points,
            action_items=action_items,
            priority="Medium"
        )
    
    def batch_summarize_emails(self, emails: List[EmailData]) -> List[EmailSummary]:
        """
        Summarize multiple emails with comprehensive rate limiting and error handling.
        
        Args:
            emails: List of email data to summarize
            
        Returns:
            List of email summaries
        """
        summaries = []
        failed_count = 0
        
        for i, email in enumerate(emails):
            try:
                self.logger.info(f"Summarizing email {i+1}/{len(emails)}: {email.subject}")
                summary = self.summarize_email(email)
                summaries.append(summary)
                
                # Adaptive rate limiting based on provider
                if i < len(emails) - 1:  # Don't delay after the last email
                    if self.config.ai_provider == "openai":
                        # OpenAI has higher rate limits
                        time.sleep(0.5)  # 500ms delay
                    elif self.config.ai_provider == "claude":
                        # Claude has stricter rate limits
                        time.sleep(1.0)  # 1s delay
                    
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Failed to summarize email {email.message_id}: {e}")
                
                # Add fallback summary for failed emails
                fallback_summary = self._create_fallback_summary(email)
                summaries.append(fallback_summary)
                
                # If too many failures, add extra delay to avoid cascading failures
                if failed_count > len(emails) * 0.3:  # More than 30% failure rate
                    self.logger.warning("High failure rate detected, adding extra delay")
                    time.sleep(2.0)
        
        if failed_count > 0:
            self.logger.warning(f"Failed to generate AI summaries for {failed_count} out of {len(emails)} emails")
            self.logger.info("Fallback summaries were generated for failed emails")
        
        return summaries
    
    def test_ai_connection(self) -> bool:
        """
        Test the AI service connection with a simple request and comprehensive error handling.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        test_content = "Subject: Test\nFrom: test@example.com\nContent: This is a test email."
        
        try:
            self.logger.info(f"Testing {self.config.ai_provider.upper()} API connection...")
            response = self._call_ai_service(test_content)
            
            if response and len(response.strip()) > 0:
                self.logger.info("AI service connection test successful")
                return True
            else:
                self.logger.error("AI service returned empty response during test")
                return False
                
        except NonRetryableError as e:
            self.logger.error(f"AI service connection test failed (non-retryable): {e}")
            if e.category == ErrorCategory.AUTHENTICATION:
                self.logger.error("Please check your API key configuration")
            elif e.category == ErrorCategory.VALIDATION:
                self.logger.error("Please check your AI service configuration")
            return False
        except RetryableError as e:
            self.logger.error(f"AI service connection test failed (retryable): {e}")
            if e.category == ErrorCategory.API_RATE_LIMIT:
                self.logger.error("Rate limit exceeded during test - this may resolve itself")
            elif e.category == ErrorCategory.NETWORK:
                self.logger.error("Network connectivity issue - check your internet connection")
            return False
        except Exception as e:
            self.logger.error(f"AI service connection test failed with unexpected error: {e}")
            return False