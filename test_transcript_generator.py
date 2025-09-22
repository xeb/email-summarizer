"""
Unit tests for the TranscriptGenerator class.

Tests cover AI prompt generation, fallback transcript creation, YAML loading,
and error handling scenarios.
"""

import unittest
import tempfile
import os
import yaml
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from summarization.transcript_generator import TranscriptGenerator
from config.settings import Config
from utils.error_handling import RetryableError, NonRetryableError, ErrorCategory


class TestTranscriptGenerator(unittest.TestCase):
    """Test cases for TranscriptGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config with proper string values
        self.config = Mock(spec=Config)
        self.config.ai_provider = "openai"
        self.config.openai_api_key = "test-key"
        self.config.openai_model = "gpt-3.5-turbo"
        self.config.claude_model = "claude-3-sonnet-20240229"
        self.config.max_tokens = 1000
        self.config.temperature = 0.7
        self.config.transcript_max_tokens = 1000
        self.config.transcript_temperature = 0.7
        
        # Create mock summarizer
        self.mock_summarizer = Mock()
        
        # Create transcript generator
        self.generator = TranscriptGenerator(self.config, self.mock_summarizer)
        
        # Sample email summaries for testing
        self.sample_summaries = [
            {
                'subject': 'Friday Newsletter & Home Connection Letter',
                'sender': 'Madison Yarter <email@renweb.com>',
                'date': '2025-09-19T21:17:17+00:00',
                'summary': 'The email provides updates and reminders for parents regarding reading logs, PE clothes, parent helper sign-ups, and upcoming focus on vocabulary words.',
                'key_points': [
                    'Reminder to tear out reading logs from the packet for tracking books read and quiz readiness.',
                    'Wear PE clothes to school on Monday.',
                    'Few open spots for parent helpers, updated forms available for sign-ups.'
                ],
                'action_items': [
                    'Tear out reading logs and keep them in the student\'s boomerang folder.',
                    'Ensure students wear PE clothes to school on Monday.',
                    'Sign up for parent helper spots if interested.'
                ],
                'priority': 'Medium'
            },
            {
                'subject': 'BTSN Slideshow',
                'sender': 'Madison Yarter <email@renweb.com>',
                'date': '2025-09-19T02:53:42+00:00',
                'summary': 'Mrs. Yarter thanks parents for attending Back to School Night and shares a slideshow about second grade.',
                'key_points': [
                    'Mrs. Yarter expresses gratitude for parents attending Back to School Night.',
                    'She shares a slideshow about second grade with parents for reference.'
                ],
                'action_items': [
                    'Review the attached slideshow for information about second grade.',
                    'Keep an eye out for the newsletter from Mrs. Yarter in your email tomorrow.'
                ],
                'priority': 'Medium'
            }
        ]
    
    def test_init_with_summarizer(self):
        """Test initialization with provided summarizer."""
        generator = TranscriptGenerator(self.config, self.mock_summarizer)
        self.assertEqual(generator.summarizer, self.mock_summarizer)
        self.assertEqual(generator.config, self.config)
    
    @patch('summarization.summarizer.EmailSummarizer')
    def test_init_without_summarizer(self, mock_email_summarizer_class):
        """Test initialization without provided summarizer."""
        mock_summarizer_instance = Mock()
        mock_email_summarizer_class.return_value = mock_summarizer_instance
        
        generator = TranscriptGenerator(self.config)
        
        mock_email_summarizer_class.assert_called_once_with(self.config)
        self.assertEqual(generator.summarizer, mock_summarizer_instance)
    
    def test_create_transcript_prompt(self):
        """Test AI prompt creation for transcript generation."""
        date = "2025-09-19"
        prompt = self.generator._create_transcript_prompt(self.sample_summaries, date)
        
        # Verify prompt contains expected elements
        self.assertIn("conversational transcript", prompt)
        self.assertIn("AI host", prompt)
        self.assertIn(date, prompt)
        self.assertIn("Friday Newsletter", prompt)
        self.assertIn("BTSN Slideshow", prompt)
        self.assertIn("Madison Yarter", prompt)
        
        # Verify guidelines are included
        self.assertIn("natural, conversational language", prompt)
        self.assertIn("smooth transitions", prompt)
        self.assertIn("professional but friendly tone", prompt)
    
    def test_format_transcript_content(self):
        """Test transcript content formatting and cleaning."""
        raw_content = "**Good morning!** Here's your *email briefing* for today. `Important` stuff here."
        
        formatted = self.generator._format_transcript_content(raw_content)
        
        # Verify markdown formatting is removed
        self.assertNotIn("**", formatted)
        self.assertNotIn("*", formatted)
        self.assertNotIn("`", formatted)
        self.assertIn("Good morning!", formatted)
        self.assertIn("email briefing", formatted)
        self.assertIn("Important", formatted)
    
    def test_create_fallback_transcript(self):
        """Test fallback transcript generation."""
        date = "2025-09-19"
        transcript = self.generator._create_fallback_transcript(self.sample_summaries, date)
        
        # Verify transcript structure
        self.assertIn("Good morning!", transcript)
        self.assertIn("September 19, 2025", transcript)
        self.assertIn("2 important emails", transcript)
        self.assertIn("Friday Newsletter", transcript)
        self.assertIn("BTSN Slideshow", transcript)
        self.assertIn("Madison Yarter", transcript)
        self.assertIn("action items", transcript)
        # Check for actual closing phrase used in implementation
        self.assertIn("Stay productive!", transcript)
    
    def test_create_empty_day_transcript(self):
        """Test transcript generation for empty email days."""
        date = "2025-09-19"
        transcript = self.generator._create_empty_day_transcript(date)
        
        # Verify empty day transcript content
        self.assertIn("Good morning!", transcript)
        self.assertIn("September 19, 2025", transcript)
        self.assertIn("no important emails", transcript)
        # The actual closing varies by day of week, so check for a general closing
        self.assertTrue(
            "Have a wonderful day!" in transcript or 
            "Have a fantastic Friday!" in transcript or
            "Have a great day!" in transcript or
            "Have a productive Monday!" in transcript or
            "Have a wonderful weekend!" in transcript
        )
    
    def test_load_email_summaries_success(self):
        """Test successful loading of email summaries from YAML file."""
        # Create temporary YAML file
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 2,
            'emails': self.sample_summaries
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        try:
            summaries = self.generator._load_email_summaries(temp_file)
            
            self.assertEqual(len(summaries), 2)
            self.assertEqual(summaries[0]['subject'], 'Friday Newsletter & Home Connection Letter')
            self.assertEqual(summaries[1]['subject'], 'BTSN Slideshow')
        finally:
            os.unlink(temp_file)
    
    def test_load_email_summaries_file_not_found(self):
        """Test loading from non-existent YAML file."""
        with self.assertRaises(NonRetryableError) as context:
            self.generator._load_email_summaries("nonexistent.yaml")
        
        self.assertIn("YAML file not found", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.VALIDATION)
    
    def test_load_email_summaries_empty_file(self):
        """Test loading from YAML file with no emails."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 0
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        try:
            summaries = self.generator._load_email_summaries(temp_file)
            self.assertEqual(summaries, [])
        finally:
            os.unlink(temp_file)
    
    def test_generate_ai_transcript_success(self):
        """Test successful AI transcript generation."""
        date = "2025-09-19"
        mock_ai_response = "Good morning! Here's your email briefing for September 19, 2025. Today I processed 2 important emails for you..."
        
        # Mock the AI service call method
        with patch.object(self.generator, '_call_ai_service_for_transcript', return_value=mock_ai_response):
            transcript = self.generator._generate_ai_transcript(self.sample_summaries, date)
            
            self.assertIn("Good morning!", transcript)
            self.assertIn("September 19, 2025", transcript)
    

    
    def test_generate_ai_transcript_empty_response(self):
        """Test AI transcript generation with empty AI response."""
        with patch.object(self.generator, '_call_ai_service_for_transcript', return_value=""):
            with self.assertRaises(NonRetryableError) as context:
                self.generator._generate_ai_transcript(self.sample_summaries, "2025-09-19")
            
            self.assertIn("empty transcript response", str(context.exception))
    
    def test_generate_ai_transcript_no_summarizer(self):
        """Test AI transcript generation when no summarizer is available."""
        # Create a generator with no summarizer
        generator = TranscriptGenerator(self.config, None)
        
        with self.assertRaises(NonRetryableError) as context:
            generator._generate_ai_transcript(self.sample_summaries, "2025-09-19")
        
        self.assertIn("AI summarizer not available", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.VALIDATION)
    
    def test_generate_ai_transcript_retryable_error(self):
        """Test AI transcript generation with retryable error."""
        with patch.object(self.generator, '_call_ai_service_for_transcript') as mock_call:
            mock_call.side_effect = RetryableError("Rate limit exceeded", ErrorCategory.API_RATE_LIMIT)
            
            with self.assertRaises(RetryableError) as context:
                self.generator._generate_ai_transcript(self.sample_summaries, "2025-09-19")
            
            self.assertIn("Rate limit exceeded", str(context.exception))
    
    def test_generate_ai_transcript_nonretryable_error(self):
        """Test AI transcript generation with non-retryable error."""
        with patch.object(self.generator, '_call_ai_service_for_transcript') as mock_call:
            mock_call.side_effect = NonRetryableError("Invalid API key", ErrorCategory.AUTHENTICATION)
            
            with self.assertRaises(NonRetryableError) as context:
                self.generator._generate_ai_transcript(self.sample_summaries, "2025-09-19")
            
            self.assertIn("Invalid API key", str(context.exception))
    
    def test_generate_ai_transcript_unexpected_error(self):
        """Test AI transcript generation with unexpected error."""
        with patch.object(self.generator, '_call_ai_service_for_transcript') as mock_call:
            mock_call.side_effect = ValueError("Unexpected error")
            
            with self.assertRaises(NonRetryableError) as context:
                self.generator._generate_ai_transcript(self.sample_summaries, "2025-09-19")
            
            self.assertIn("Unexpected error in AI transcript generation", str(context.exception))
    
    def test_call_ai_service_for_transcript_openai(self):
        """Test AI service call routing for OpenAI."""
        self.config.ai_provider = "openai"
        
        with patch.object(self.generator, '_call_openai_for_transcript', return_value="test response") as mock_openai:
            result = self.generator._call_ai_service_for_transcript("test prompt")
            
            mock_openai.assert_called_once_with("test prompt")
            self.assertEqual(result, "test response")
    
    def test_call_ai_service_for_transcript_claude(self):
        """Test AI service call routing for Claude."""
        self.config.ai_provider = "claude"
        
        with patch.object(self.generator, '_call_claude_for_transcript', return_value="test response") as mock_claude:
            result = self.generator._call_ai_service_for_transcript("test prompt")
            
            mock_claude.assert_called_once_with("test prompt")
            self.assertEqual(result, "test response")
    
    def test_call_ai_service_for_transcript_unsupported_provider(self):
        """Test AI service call with unsupported provider."""
        self.config.ai_provider = "unsupported"
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_ai_service_for_transcript("test prompt")
        
        self.assertIn("Unsupported AI provider", str(context.exception))
    
    def test_call_openai_for_transcript_success(self):
        """Test successful OpenAI API call for transcript."""
        # Set up config for transcript generation
        self.config.transcript_max_tokens = 1000
        self.config.transcript_temperature = 0.7
        
        # Mock OpenAI client and response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated transcript content"
        
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        self.mock_summarizer.openai_client = mock_openai_client
        
        result = self.generator._call_openai_for_transcript("test prompt")
        
        self.assertEqual(result, "Generated transcript content")
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        self.assertEqual(call_args[1]['model'], self.config.openai_model)
        self.assertEqual(call_args[1]['max_tokens'], self.config.transcript_max_tokens)
        self.assertEqual(call_args[1]['temperature'], self.config.transcript_temperature)
    
    def test_call_openai_for_transcript_no_client(self):
        """Test OpenAI API call when client is not available."""
        self.mock_summarizer.openai_client = None
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_openai_for_transcript("test prompt")
        
        self.assertIn("OpenAI client not available", str(context.exception))
    
    def test_call_openai_for_transcript_empty_response(self):
        """Test OpenAI API call with empty response."""
        mock_response = Mock()
        mock_response.choices = []
        
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        self.mock_summarizer.openai_client = mock_openai_client
        
        with self.assertRaises(RetryableError) as context:
            self.generator._call_openai_for_transcript("test prompt")
        
        self.assertIn("OpenAI API error", str(context.exception))
    
    def test_call_openai_for_transcript_rate_limit_error(self):
        """Test OpenAI API call with rate limit error."""
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.side_effect = Exception("rate limit exceeded")
        
        self.mock_summarizer.openai_client = mock_openai_client
        
        with self.assertRaises(RetryableError) as context:
            self.generator._call_openai_for_transcript("test prompt")
        
        self.assertIn("OpenAI API rate limit exceeded", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.API_RATE_LIMIT)
    
    def test_call_openai_for_transcript_quota_error(self):
        """Test OpenAI API call with quota error."""
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.side_effect = Exception("quota exceeded")
        
        self.mock_summarizer.openai_client = mock_openai_client
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_openai_for_transcript("test prompt")
        
        self.assertIn("OpenAI API quota/billing issue", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION)
    
    def test_call_openai_for_transcript_invalid_key_error(self):
        """Test OpenAI API call with invalid key error."""
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.side_effect = Exception("invalid api key")
        
        self.mock_summarizer.openai_client = mock_openai_client
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_openai_for_transcript("test prompt")
        
        self.assertIn("OpenAI API key invalid", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION)
    
    def test_call_claude_for_transcript_success(self):
        """Test successful Claude API call for transcript."""
        # Set up config for transcript generation
        self.config.claude_model = "claude-3-sonnet-20240229"
        self.config.transcript_max_tokens = 1000
        self.config.transcript_temperature = 0.7
        
        # Mock Claude client and response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Generated transcript content"
        
        mock_claude_client = Mock()
        mock_claude_client.messages.create.return_value = mock_response
        
        self.mock_summarizer.claude_client = mock_claude_client
        
        result = self.generator._call_claude_for_transcript("test prompt")
        
        self.assertEqual(result, "Generated transcript content")
        mock_claude_client.messages.create.assert_called_once()
        
        # Verify call parameters
        call_args = mock_claude_client.messages.create.call_args
        self.assertEqual(call_args[1]['model'], self.config.claude_model)
        self.assertEqual(call_args[1]['max_tokens'], self.config.transcript_max_tokens)
        self.assertEqual(call_args[1]['temperature'], self.config.transcript_temperature)
    
    def test_call_claude_for_transcript_no_client(self):
        """Test Claude API call when client is not available."""
        self.mock_summarizer.claude_client = None
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_claude_for_transcript("test prompt")
        
        self.assertIn("Claude client not available", str(context.exception))
    
    def test_call_claude_for_transcript_empty_response(self):
        """Test Claude API call with empty response."""
        mock_response = Mock()
        mock_response.content = []
        
        mock_claude_client = Mock()
        mock_claude_client.messages.create.return_value = mock_response
        
        self.mock_summarizer.claude_client = mock_claude_client
        
        with self.assertRaises(RetryableError) as context:
            self.generator._call_claude_for_transcript("test prompt")
        
        self.assertIn("Claude API error", str(context.exception))
    
    def test_call_claude_for_transcript_rate_limit_error(self):
        """Test Claude API call with rate limit error."""
        mock_claude_client = Mock()
        mock_claude_client.messages.create.side_effect = Exception("rate_limit exceeded")
        
        self.mock_summarizer.claude_client = mock_claude_client
        
        with self.assertRaises(RetryableError) as context:
            self.generator._call_claude_for_transcript("test prompt")
        
        self.assertIn("Claude API rate limit exceeded", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.API_RATE_LIMIT)
    
    def test_call_claude_for_transcript_credit_error(self):
        """Test Claude API call with credit error."""
        mock_claude_client = Mock()
        mock_claude_client.messages.create.side_effect = Exception("insufficient credits")
        
        self.mock_summarizer.claude_client = mock_claude_client
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator._call_claude_for_transcript("test prompt")
        
        self.assertIn("Claude API credit/billing issue", str(context.exception))
        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION)
    
    def test_load_email_summaries_invalid_yaml(self):
        """Test loading from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name
        
        try:
            with self.assertRaises(NonRetryableError) as context:
                self.generator._load_email_summaries(temp_file)
            
            self.assertIn("Failed to parse YAML file", str(context.exception))
            self.assertEqual(context.exception.category, ErrorCategory.VALIDATION)
        finally:
            os.unlink(temp_file)
    
    def test_create_fallback_transcript_empty_summaries(self):
        """Test fallback transcript creation with empty summaries."""
        date = "2025-09-19"
        transcript = self.generator._create_fallback_transcript([], date)
        
        # Should delegate to empty day transcript
        self.assertIn("no important emails", transcript)
        self.assertIn("September 19, 2025", transcript)
    
    def test_create_fallback_transcript_single_email(self):
        """Test fallback transcript creation with single email."""
        single_email = [self.sample_summaries[0]]
        date = "2025-09-19"
        
        transcript = self.generator._create_fallback_transcript(single_email, date)
        
        self.assertIn("Good morning!", transcript)
        # Check for actual singular form used in implementation
        self.assertIn("one important email", transcript)
        self.assertIn("Friday Newsletter", transcript)
        self.assertIn("Madison Yarter", transcript)
    
    def test_create_fallback_transcript_action_items_limit(self):
        """Test fallback transcript limits action items to top 5."""
        # Create email with many action items
        email_with_many_actions = {
            'subject': 'Test Email',
            'sender': 'Test Sender',
            'summary': 'Test summary',
            'action_items': [f'Action item {i}' for i in range(10)]  # 10 action items
        }
        
        transcript = self.generator._create_fallback_transcript([email_with_many_actions], "2025-09-19")
        
        # Should only include first 5 action items
        action_item_count = transcript.count('Action item')
        self.assertEqual(action_item_count, 5)
    
    def test_format_transcript_content_whitespace_normalization(self):
        """Test transcript content whitespace normalization."""
        raw_content = "Good   morning!    Here's    your briefing.   Today   is great."
        
        formatted = self.generator._format_transcript_content(raw_content)
        
        # Verify excessive whitespace is normalized
        self.assertNotIn("   ", formatted)
        self.assertIn("Good morning!", formatted)
        self.assertIn("Here's your briefing.", formatted)
    
    def test_format_transcript_content_sentence_spacing(self):
        """Test transcript content sentence spacing."""
        raw_content = "First sentence.Second sentence!Third sentence?Fourth sentence."
        
        formatted = self.generator._format_transcript_content(raw_content)
        
        # Verify proper spacing after sentence endings
        self.assertIn("sentence. Second", formatted)
        self.assertIn("sentence! Third", formatted)
        self.assertIn("sentence? Fourth", formatted)
    
    def test_generate_transcript_with_ai_success(self):
        """Test complete transcript generation with AI success."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 2,
            'emails': self.sample_summaries
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        mock_ai_response = "Good morning! Here's your email briefing..."
        
        with patch.object(self.generator, '_call_ai_service_for_transcript', return_value=mock_ai_response):
            try:
                transcript = self.generator.generate_transcript(temp_file, "2025-09-19")
                
                self.assertIn("Good morning!", transcript)
            finally:
                os.unlink(temp_file)
    
    def test_generate_transcript_ai_failure_fallback(self):
        """Test transcript generation with AI failure and fallback."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 2,
            'emails': self.sample_summaries
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        # Mock AI service to raise an error
        with patch.object(self.generator, '_call_ai_service_for_transcript') as mock_call:
            mock_call.side_effect = RetryableError(
                "API rate limit exceeded", ErrorCategory.API_RATE_LIMIT
            )
            
            try:
                transcript = self.generator.generate_transcript(temp_file, "2025-09-19")
                
                # Should fall back to template-based transcript
                self.assertIn("Good morning!", transcript)
                self.assertIn("September 19, 2025", transcript)
                self.assertIn("2 important emails", transcript)
            finally:
                os.unlink(temp_file)
    
    def test_generate_transcript_empty_summaries(self):
        """Test transcript generation with no email summaries."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 0,
            'emails': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        try:
            transcript = self.generator.generate_transcript(temp_file, "2025-09-19")
            
            # Should generate empty day transcript
            self.assertIn("no important emails", transcript)
            self.assertIn("September 19, 2025", transcript)
        finally:
            os.unlink(temp_file)
    
    def test_generate_transcript_file_read_error(self):
        """Test transcript generation with file read error."""
        # Create a file and then remove it to simulate read error
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=True) as f:
            temp_file = f.name
        
        with self.assertRaises(NonRetryableError) as context:
            self.generator.generate_transcript(temp_file, "2025-09-19")
        
        self.assertIn("YAML file not found", str(context.exception))
    
    def test_generate_transcript_unexpected_error(self):
        """Test transcript generation with unexpected error during processing."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 1,
            'emails': self.sample_summaries[:1]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        # Mock _create_fallback_transcript to raise an unexpected error
        with patch.object(self.generator, '_create_fallback_transcript') as mock_fallback:
            mock_fallback.side_effect = ValueError("Unexpected processing error")
            
            try:
                with self.assertRaises(NonRetryableError) as context:
                    self.generator.generate_transcript(temp_file, "2025-09-19")
                
                self.assertIn("Transcript generation failed", str(context.exception))
            finally:
                os.unlink(temp_file)
    
    def test_create_transcript_prompt_edge_cases(self):
        """Test transcript prompt creation with edge cases."""
        # Test with emails missing various fields
        incomplete_summaries = [
            {
                'subject': 'Complete Email',
                'sender': 'Complete Sender <email@example.com>',
                'summary': 'Complete summary',
                'key_points': ['Point 1', 'Point 2'],
                'action_items': ['Action 1'],
                'priority': 'High'
            },
            {
                # Missing most fields
                'subject': 'Incomplete Email'
            },
            {
                'sender': 'Only Sender',
                'summary': 'Only summary',
                'key_points': [],
                'action_items': [],
                'priority': 'Low'
            }
        ]
        
        date = "2025-09-19"
        prompt = self.generator._create_transcript_prompt(incomplete_summaries, date)
        
        # Verify prompt handles missing fields gracefully
        self.assertIn("Complete Email", prompt)
        self.assertIn("Incomplete Email", prompt)
        self.assertIn("Only Sender", prompt)
        self.assertIn("No subject", prompt)  # Default for missing subject
        self.assertIn("Unknown sender", prompt)  # Default for missing sender
        self.assertIn("No summary available", prompt)  # Default for missing summary
    
    def test_create_empty_day_transcript_invalid_date(self):
        """Test empty day transcript creation with invalid date format."""
        invalid_date = "invalid-date-format"
        transcript = self.generator._create_empty_day_transcript(invalid_date)
        
        # Should use the raw date string when parsing fails
        self.assertIn(invalid_date, transcript)
        self.assertIn("no important emails", transcript)
    
    def test_create_fallback_transcript_invalid_date(self):
        """Test fallback transcript creation with invalid date format."""
        invalid_date = "invalid-date-format"
        transcript = self.generator._create_fallback_transcript(self.sample_summaries, invalid_date)
        
        # Should use the raw date string when parsing fails
        self.assertIn(invalid_date, transcript)
        self.assertIn("Good morning!", transcript)
    
    def test_create_fallback_transcript_sender_name_extraction(self):
        """Test sender name extraction in fallback transcript."""
        email_with_complex_sender = [{
            'subject': 'Test Subject',
            'sender': 'John Doe <john.doe@example.com>',
            'summary': 'Test summary'
        }]
        
        transcript = self.generator._create_fallback_transcript(email_with_complex_sender, "2025-09-19")
        
        # Should extract just the name part
        self.assertIn("John Doe", transcript)
        self.assertNotIn("<john.doe@example.com>", transcript)
    

    
    def test_generate_transcript_no_summarizer_fallback(self):
        """Test transcript generation when no summarizer is available falls back to template."""
        yaml_data = {
            'date': '2025-09-19',
            'processed_at': '2025-09-19T17:27:49.658114',
            'email_count': 1,
            'emails': self.sample_summaries[:1]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_file = f.name
        
        # Create generator without summarizer
        generator = TranscriptGenerator(self.config, None)
        
        try:
            transcript = generator.generate_transcript(temp_file, "2025-09-19")
            
            # Should use template-based transcript
            self.assertIn("Good morning!", transcript)
            self.assertIn("Friday Newsletter", transcript)
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()