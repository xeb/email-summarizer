"""
AI-powered transcript generation module.

This module provides functionality to generate conversational transcript summaries
from existing email summaries, creating script-like content suitable for AI voice synthesis.
"""

import logging
import re
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from config.settings import Config
from utils.error_handling import (
    RetryableError, NonRetryableError, ErrorCategory
)


class TranscriptGenerator:
    """Handles AI-powered transcript generation from email summaries."""
    
    def __init__(self, config: Config, summarizer=...):
        """
        Initialize the transcript generator with configuration.
        
        Args:
            config: Configuration object containing AI service settings
            summarizer: EmailSummarizer instance for AI service calls (optional)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # If summarizer is explicitly provided (including None), use it
        if summarizer is not ...:
            self.summarizer = summarizer
        else:
            # Try to initialize EmailSummarizer if not provided
            try:
                from summarization.summarizer import EmailSummarizer
                self.summarizer = EmailSummarizer(config)
                self.logger.debug("EmailSummarizer initialized for transcript generation")
            except Exception as e:
                self.logger.warning(f"Failed to initialize EmailSummarizer: {e}")
                self.summarizer = None
    
    def generate_transcript(self, yaml_file_path: str, date: str) -> str:
        """
        Generate a conversational transcript from email summaries in a YAML file.
        
        Args:
            yaml_file_path: Path to the YAML file containing email summaries
            date: Date string for the transcript (YYYY-MM-DD format)
            
        Returns:
            str: Generated transcript content
            
        Raises:
            NonRetryableError: If YAML file cannot be read or parsed, or transcript generation fails completely
        """
        try:
            self.logger.info(f"Generating transcript for date: {date}")
            
            # Validate date format early
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError as e:
                raise NonRetryableError(
                    f"Invalid date format '{date}'. Expected YYYY-MM-DD format",
                    ErrorCategory.VALIDATION
                ) from e
            
            # Load email summaries from YAML file
            summaries = self._load_email_summaries(yaml_file_path)
            
            if not summaries:
                self.logger.info("No email summaries found, generating empty day transcript")
                empty_transcript = self._create_empty_day_transcript(date)
                self.logger.info("Successfully generated empty day transcript")
                return empty_transcript
            
            self.logger.info(f"Loaded {len(summaries)} email summaries for transcript generation")
            
            # Generate AI-powered transcript with fallback
            if self.summarizer:
                try:
                    transcript = self._generate_ai_transcript(summaries, date)
                    self.logger.info("AI transcript generation successful")
                    return transcript
                except (RetryableError, NonRetryableError) as e:
                    self.logger.warning(f"AI transcript generation failed: {e}")
                    self.logger.info("Falling back to template-based transcript generation")
                    fallback_transcript = self._create_fallback_transcript(summaries, date)
                    self.logger.info("Successfully generated fallback transcript")
                    return fallback_transcript
            else:
                self.logger.info("No AI service available, using template-based transcript generation")
                fallback_transcript = self._create_fallback_transcript(summaries, date)
                self.logger.info("Successfully generated template-based transcript")
                return fallback_transcript
                
        except (RetryableError, NonRetryableError):
            # Re-raise known error types
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during transcript generation: {e}")
            raise NonRetryableError(
                f"Transcript generation failed due to unexpected error: {e}",
                ErrorCategory.VALIDATION
            )
    
    def _load_email_summaries(self, yaml_file_path: str) -> List[Dict[str, Any]]:
        """
        Load email summaries from a YAML file.
        
        Args:
            yaml_file_path: Path to the YAML file
            
        Returns:
            List of email summary dictionaries
            
        Raises:
            NonRetryableError: If file cannot be read or parsed
        """
        try:
            yaml_path = Path(yaml_file_path)
            if not yaml_path.exists():
                raise NonRetryableError(
                    f"YAML file not found: {yaml_file_path}",
                    ErrorCategory.VALIDATION
                )
            
            with open(yaml_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            if not data or 'emails' not in data:
                self.logger.warning(f"No emails found in YAML file: {yaml_file_path}")
                return []
            
            emails = data['emails']
            self.logger.debug(f"Loaded {len(emails)} email summaries from {yaml_file_path}")
            return emails
            
        except yaml.YAMLError as e:
            raise NonRetryableError(
                f"Failed to parse YAML file {yaml_file_path}: {e}",
                ErrorCategory.VALIDATION
            )
        except Exception as e:
            raise NonRetryableError(
                f"Failed to read YAML file {yaml_file_path}: {e}",
                ErrorCategory.VALIDATION
            )
    
    def _generate_ai_transcript(self, summaries: List[Dict[str, Any]], date: str) -> str:
        """
        Generate a conversational transcript using AI services.
        
        Args:
            summaries: List of email summary dictionaries
            date: Date string for the transcript
            
        Returns:
            str: AI-generated transcript content
            
        Raises:
            RetryableError: If AI service call fails with retryable error
            NonRetryableError: If AI service call fails with non-retryable error
        """
        if not self.summarizer:
            raise NonRetryableError(
                "AI summarizer not available for transcript generation",
                ErrorCategory.VALIDATION
            )
        
        # Create AI prompt for transcript generation
        prompt = self._create_transcript_prompt(summaries, date)
        
        try:
            # Make direct AI service call with transcript-specific configuration
            ai_response = self._call_ai_service_for_transcript(prompt)
            
            if not ai_response or not ai_response.strip():
                raise NonRetryableError(
                    "AI service returned empty transcript response",
                    ErrorCategory.API_RATE_LIMIT
                )
            
            # Format and clean the AI response
            formatted_transcript = self._format_transcript_content(ai_response)
            
            return formatted_transcript
            
        except Exception as e:
            # Re-raise known error types, convert others
            if isinstance(e, (RetryableError, NonRetryableError)):
                raise
            else:
                raise NonRetryableError(
                    f"Unexpected error in AI transcript generation: {e}",
                    ErrorCategory.VALIDATION
                )
    
    def _create_transcript_prompt(self, summaries: List[Dict[str, Any]], date: str) -> str:
        """
        Create an AI prompt for conversational transcript generation.
        
        Args:
            summaries: List of email summary dictionaries
            date: Date string for the transcript
            
        Returns:
            str: Formatted prompt for AI service
        """
        # Format email summaries for the prompt
        email_sections = []
        for i, email in enumerate(summaries, 1):
            section = f"""
Email {i}:
Subject: {email.get('subject', 'No subject')}
From: {email.get('sender', 'Unknown sender')}
Summary: {email.get('summary', 'No summary available')}
Key Points: {', '.join(email.get('key_points', []))}
Action Items: {', '.join(email.get('action_items', []))}
Priority: {email.get('priority', 'Medium')}
"""
            email_sections.append(section.strip())
        
        email_content = '\n\n'.join(email_sections)
        
        prompt = f"""Create a conversational transcript for an AI host to read aloud as a daily email briefing for {date}.

Email Summaries:
{email_content}

Guidelines:
- Use natural, conversational language suitable for audio presentation
- Create smooth transitions between different emails using phrases like "Let me tell you about...", "Moving on to...", "Next up..."
- Group related emails logically when possible
- Maintain a professional but friendly tone throughout
- Include a brief opening greeting and closing
- Consolidate action items at the end in a clear summary
- Keep the total length appropriate for a 2-3 minute audio briefing
- Use present tense and direct address ("you have", "you need to")
- Make it sound natural when read aloud, avoiding awkward phrasing

Format as a complete script that flows naturally when read by an AI voice assistant. Start with a greeting and end with a closing statement."""

        return prompt
    
    def _format_transcript_content(self, ai_response: str) -> str:
        """
        Format and clean AI-generated transcript content.
        
        Args:
            ai_response: Raw AI response text
            
        Returns:
            str: Formatted transcript content
        """
        # Clean up the response
        transcript = ai_response.strip()
        
        # Remove any markdown formatting that might interfere with speech
        transcript = re.sub(r'\*\*(.*?)\*\*', r'\1', transcript)  # Remove bold
        transcript = re.sub(r'\*(.*?)\*', r'\1', transcript)      # Remove italic
        transcript = re.sub(r'`(.*?)`', r'\1', transcript)        # Remove code formatting
        
        # Ensure proper spacing and punctuation for speech
        transcript = re.sub(r'\s+', ' ', transcript)              # Normalize whitespace
        transcript = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', transcript)  # Ensure space after sentences
        
        # Add pauses for better speech flow (optional - can be used by TTS systems)
        transcript = transcript.replace('. ', '. ')  # Ensure consistent sentence spacing
        
        return transcript
    
    def _create_fallback_transcript(self, summaries: List[Dict[str, Any]], date: str) -> str:
        """
        Create a template-based fallback transcript when AI generation fails.
        
        Args:
            summaries: List of email summary dictionaries
            date: Date string for the transcript
            
        Returns:
            str: Template-based transcript content
        """
        try:
            if not summaries:
                self.logger.debug("No summaries provided, creating empty day transcript")
                return self._create_empty_day_transcript(date)
            
            # Format date for speech
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%B %d, %Y')
            except ValueError:
                self.logger.warning(f"Invalid date format for transcript: {date}, using as-is")
                formatted_date = date
            
            # Build transcript sections with enhanced templates
            transcript_parts = []
            
            # Opening with variety based on email count
            email_count = len(summaries)
            if email_count == 1:
                transcript_parts.append(f"Good morning! Here's your email briefing for {formatted_date}.")
                transcript_parts.append("I found one important email that needs your attention today.")
            elif email_count <= 3:
                transcript_parts.append(f"Good morning! Here's your email briefing for {formatted_date}.")
                transcript_parts.append(f"I processed {email_count} important emails for you today.")
            else:
                transcript_parts.append(f"Good morning! Here's your email briefing for {formatted_date}.")
                transcript_parts.append(f"It's been a busy day with {email_count} important emails to review.")
            
            # Email sections with better transitions
            if email_count == 1:
                transcript_parts.append("Here's what you need to know:")
            else:
                transcript_parts.append("Let me walk you through the key highlights:")
            
            # Process emails with enhanced formatting
            high_priority_emails = []
            medium_priority_emails = []
            low_priority_emails = []
            
            for email in summaries:
                priority = email.get('priority', 'Medium').lower()
                if priority in ['high', 'urgent', 'important']:
                    high_priority_emails.append(email)
                elif priority in ['low', 'minor']:
                    low_priority_emails.append(email)
                else:
                    medium_priority_emails.append(email)
            
            # Process high priority emails first
            email_counter = 1
            for email_list, priority_label in [
                (high_priority_emails, "urgent"),
                (medium_priority_emails, ""),
                (low_priority_emails, "")
            ]:
                for email in email_list:
                    subject = email.get('subject', 'No subject')
                    sender = email.get('sender', 'Unknown sender')
                    summary = email.get('summary', 'No summary available')
                    
                    # Extract sender name (remove email address if present)
                    sender_name = re.sub(r'\s*<.*?>', '', sender).strip()
                    if not sender_name:
                        sender_name = "Unknown sender"
                    
                    # Create varied introductions
                    if email_counter == 1:
                        intro = "First up,"
                    elif email_counter == email_count:
                        intro = "Finally,"
                    elif priority_label == "urgent":
                        intro = "Importantly,"
                    else:
                        intro = "Next,"
                    
                    # Clean up summary text for speech
                    clean_summary = summary.replace('\n', ' ').strip()
                    if not clean_summary.endswith('.'):
                        clean_summary += '.'
                    
                    email_section = f"{intro} you have an email from {sender_name} about {subject}. {clean_summary}"
                    transcript_parts.append(email_section)
                    email_counter += 1
            
            # Action items summary with better organization
            all_action_items = []
            for email in summaries:
                action_items = email.get('action_items', [])
                if isinstance(action_items, list):
                    all_action_items.extend(action_items)
            
            if all_action_items:
                if len(all_action_items) == 1:
                    transcript_parts.append("Before you go, there's one action item that needs your attention:")
                    transcript_parts.append(f"{all_action_items[0]}")
                else:
                    transcript_parts.append("To wrap up, here are the main action items for your attention:")
                    # Limit to top 5 action items and clean them up
                    for item in all_action_items[:5]:
                        clean_item = str(item).strip()
                        if clean_item and not clean_item.startswith('-'):
                            transcript_parts.append(f"- {clean_item}")
            
            # Closing with variety
            if email_count == 1:
                transcript_parts.append("That's your single important email for today. Have a great day!")
            elif all_action_items:
                transcript_parts.append("That concludes your email briefing. Stay productive!")
            else:
                transcript_parts.append("That's all for today's email briefing. Have a wonderful day!")
            
            # Join with proper spacing for speech
            result = ' '.join(transcript_parts)
            
            # Final cleanup for speech synthesis
            result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
            result = result.replace('..', '.')    # Fix double periods
            
            self.logger.debug(f"Generated fallback transcript with {len(transcript_parts)} sections")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating fallback transcript: {e}")
            # Return a minimal safe transcript
            return self._create_minimal_fallback_transcript(date, len(summaries) if summaries else 0)
    
    def _create_empty_day_transcript(self, date: str) -> str:
        """
        Create a transcript for days with no important emails.
        
        Args:
            date: Date string for the transcript
            
        Returns:
            str: Transcript content for empty email day
        """
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
            day_of_week = date_obj.strftime('%A')
        except ValueError:
            self.logger.warning(f"Invalid date format for empty day transcript: {date}")
            formatted_date = date
            day_of_week = ""
        
        # Vary the message based on day of week
        if day_of_week.lower() == 'monday':
            message = (f"Good morning! Here's your email briefing for {formatted_date}. "
                      f"What a great way to start the week - there were no important emails that required your attention today. "
                      f"This gives you a clear slate to focus on your weekly priorities. "
                      f"I'll continue monitoring your inbox throughout the day. "
                      f"Have a productive Monday!")
        elif day_of_week.lower() == 'friday':
            message = (f"Good morning! Here's your email briefing for {formatted_date}. "
                      f"Perfect timing for a Friday - there were no important emails that needed your attention today. "
                      f"This gives you more time to wrap up the week and prepare for the weekend. "
                      f"I'll keep watching your inbox in case anything urgent comes in. "
                      f"Have a fantastic Friday!")
        elif day_of_week.lower() in ['saturday', 'sunday']:
            message = (f"Good morning! Here's your email briefing for {formatted_date}. "
                      f"Enjoy your weekend - there were no important emails that required your attention today. "
                      f"This is the perfect time to relax and recharge. "
                      f"I'll continue monitoring your inbox and will alert you if anything urgent arrives. "
                      f"Have a wonderful weekend!")
        else:
            message = (f"Good morning! Here's your email briefing for {formatted_date}. "
                      f"Great news - there were no important emails that required your attention today. "
                      f"This gives you more time to focus on your other priorities and projects. "
                      f"I'll continue monitoring your inbox and will let you know when something important comes in. "
                      f"Have a wonderful day!")
        
        self.logger.debug(f"Generated empty day transcript for {formatted_date}")
        return message
    
    def _create_minimal_fallback_transcript(self, date: str, email_count: int) -> str:
        """
        Create a minimal safe transcript when all other generation methods fail.
        
        Args:
            date: Date string for the transcript
            email_count: Number of emails processed
            
        Returns:
            str: Minimal safe transcript content
        """
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
        except ValueError:
            formatted_date = date
        
        if email_count == 0:
            message = f"Good morning! Your email briefing for {formatted_date} shows no important emails today. Have a great day!"
        elif email_count == 1:
            message = f"Good morning! Your email briefing for {formatted_date} shows one important email to review. Please check your email for details. Have a great day!"
        else:
            message = f"Good morning! Your email briefing for {formatted_date} shows {email_count} important emails to review. Please check your email for details. Have a great day!"
        
        self.logger.info(f"Generated minimal fallback transcript for {email_count} emails")
        return message
    
    def _call_ai_service_for_transcript(self, prompt: str) -> str:
        """
        Call AI service specifically for transcript generation with appropriate configuration.
        
        Args:
            prompt: The transcript generation prompt
            
        Returns:
            str: AI-generated transcript content
            
        Raises:
            RetryableError: If AI service call fails with retryable error
            NonRetryableError: If AI service call fails with non-retryable error
        """
        if self.config.ai_provider == "openai":
            return self._call_openai_for_transcript(prompt)
        elif self.config.ai_provider == "claude":
            return self._call_claude_for_transcript(prompt)
        else:
            raise NonRetryableError(
                f"Unsupported AI provider: {self.config.ai_provider}",
                ErrorCategory.VALIDATION
            )
    
    def _call_openai_for_transcript(self, prompt: str) -> str:
        """
        Call OpenAI API specifically for transcript generation.
        
        Args:
            prompt: The transcript generation prompt
            
        Returns:
            str: OpenAI API response
            
        Raises:
            RetryableError: If a retryable API error occurs
            NonRetryableError: If a non-retryable API error occurs
        """
        if not self.summarizer or not hasattr(self.summarizer, 'openai_client') or not self.summarizer.openai_client:
            raise NonRetryableError(
                "OpenAI client not available for transcript generation",
                ErrorCategory.VALIDATION
            )
        
        try:
            self.logger.debug("Making OpenAI API request for transcript generation")
            response = self.summarizer.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that creates conversational transcripts for voice presentation. Generate natural, flowing scripts suitable for audio briefings."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.transcript_max_tokens,
                temperature=self.config.transcript_temperature
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise NonRetryableError(
                    "OpenAI API returned empty response for transcript",
                    ErrorCategory.API_RATE_LIMIT
                )
            
            result = response.choices[0].message.content.strip()
            self.logger.debug("OpenAI API request for transcript successful")
            return result
            
        except Exception as e:
            # Convert OpenAI exceptions to our error types
            if "rate limit" in str(e).lower():
                raise RetryableError(
                    f"OpenAI API rate limit exceeded: {e}",
                    ErrorCategory.API_RATE_LIMIT
                )
            elif "quota" in str(e).lower() or "billing" in str(e).lower():
                raise NonRetryableError(
                    f"OpenAI API quota/billing issue: {e}",
                    ErrorCategory.AUTHENTICATION
                )
            elif "invalid" in str(e).lower() and "key" in str(e).lower():
                raise NonRetryableError(
                    f"OpenAI API key invalid: {e}",
                    ErrorCategory.AUTHENTICATION
                )
            else:
                raise RetryableError(
                    f"OpenAI API error: {e}",
                    ErrorCategory.NETWORK
                )
    
    def _call_claude_for_transcript(self, prompt: str) -> str:
        """
        Call Claude API specifically for transcript generation.
        
        Args:
            prompt: The transcript generation prompt
            
        Returns:
            str: Claude API response
            
        Raises:
            RetryableError: If a retryable API error occurs
            NonRetryableError: If a non-retryable API error occurs
        """
        if not self.summarizer or not hasattr(self.summarizer, 'claude_client') or not self.summarizer.claude_client:
            raise NonRetryableError(
                "Claude client not available for transcript generation",
                ErrorCategory.VALIDATION
            )
        
        try:
            self.logger.debug("Making Claude API request for transcript generation")
            response = self.summarizer.claude_client.messages.create(
                model=self.config.claude_model,
                max_tokens=self.config.transcript_max_tokens,
                temperature=self.config.transcript_temperature,
                system="You are an AI assistant that creates conversational transcripts for voice presentation. Generate natural, flowing scripts suitable for audio briefings.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if not response.content or not response.content[0].text:
                raise NonRetryableError(
                    "Claude API returned empty response for transcript",
                    ErrorCategory.API_RATE_LIMIT
                )
            
            result = response.content[0].text.strip()
            self.logger.debug("Claude API request for transcript successful")
            return result
            
        except Exception as e:
            # Convert Claude exceptions to our error types
            if "rate_limit" in str(e).lower():
                raise RetryableError(
                    f"Claude API rate limit exceeded: {e}",
                    ErrorCategory.API_RATE_LIMIT
                )
            elif "credit" in str(e).lower() or "billing" in str(e).lower():
                raise NonRetryableError(
                    f"Claude API credit/billing issue: {e}",
                    ErrorCategory.AUTHENTICATION
                )
            elif "invalid" in str(e).lower() and "key" in str(e).lower():
                raise NonRetryableError(
                    f"Claude API key invalid: {e}",
                    ErrorCategory.AUTHENTICATION
                )
            else:
                raise RetryableError(
                    f"Claude API error: {e}",
                    ErrorCategory.NETWORK
                )