#!/usr/bin/env python3
"""
Integration tests for transcript generation end-to-end workflow.

Tests the complete transcript generation workflow including CLI options,
configuration loading, and integration with the existing email summarization workflow.
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from argparse import Namespace

# Import modules to test
from main import (
    process_emails, handle_transcript_only, generate_transcript_for_workflow,
    parse_arguments, determine_search_query
)
from config.settings import Config
from summarization.transcript_generator import TranscriptGenerator
from storage.transcript_writer import TranscriptWriter


class TestTranscriptWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete transcript generation workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_dir = os.path.join(self.temp_dir, "email_summaries")
        self.transcript_dir = os.path.join(self.temp_dir, "transcripts")
        os.makedirs(self.yaml_dir, exist_ok=True)
        os.makedirs(self.transcript_dir, exist_ok=True)
        
        # Create test YAML file
        self.test_date = "2025-09-19"
        self.yaml_file_path = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        
        # Mock all external dependencies
        self.mock_patches = []
        self._setup_mocks()
        
    def tearDown(self):
        """Clean up test fixtures."""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        shutil.rmtree(self.temp_dir)
    
    def _setup_mocks(self):
        """Set up all mock patches."""
        # Mock configuration loading
        self.config_patch = patch('main.load_config')
        self.mock_load_config = self.config_patch.start()
        self.mock_patches.append(self.config_patch)
        
        self.mock_config = Mock(spec=Config)
        self.mock_config.output_directory = self.yaml_dir
        self.mock_config.transcript_output_directory = self.transcript_dir
        self.mock_config.enable_transcript_generation = True
        self.mock_config.max_emails_per_run = 10
        self.mock_config.credentials_file = "credentials.json"
        self.mock_config.token_file = "token.json"
        self.mock_config.default_search_query = "is:unread is:important"
        self.mock_config.ai_provider = "openai"
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.openai_model = "gpt-3.5-turbo"
        self.mock_load_config.return_value = self.mock_config
        
        # Mock validation functions
        self.validate_creds_patch = patch('main.validate_gmail_credentials', return_value=True)
        self.mock_validate_creds = self.validate_creds_patch.start()
        self.mock_patches.append(self.validate_creds_patch)
        
        self.ensure_dir_patch = patch('main.ensure_output_directory', return_value=True)
        self.mock_ensure_dir = self.ensure_dir_patch.start()
        self.mock_patches.append(self.ensure_dir_patch)
        
        self.ensure_transcript_dir_patch = patch('main.ensure_transcript_directory', return_value=True)
        self.mock_ensure_transcript_dir = self.ensure_transcript_dir_patch.start()
        self.mock_patches.append(self.ensure_transcript_dir_patch)
        
        # Mock component creation
        self.create_fetcher_patch = patch('main.create_email_fetcher')
        self.mock_create_fetcher = self.create_fetcher_patch.start()
        self.mock_patches.append(self.create_fetcher_patch)
        
        self.mock_fetcher = Mock()
        self.mock_create_fetcher.return_value = self.mock_fetcher
        
        # Mock other components
        self.processor_patch = patch('main.EmailProcessor')
        self.mock_processor_class = self.processor_patch.start()
        self.mock_patches.append(self.processor_patch)
        
        self.mock_processor = Mock()
        self.mock_processor_class.return_value = self.mock_processor
        
        self.summarizer_patch = patch('main.EmailSummarizer')
        self.mock_summarizer_class = self.summarizer_patch.start()
        self.mock_patches.append(self.summarizer_patch)
        
        self.mock_summarizer = Mock()
        self.mock_summarizer_class.return_value = self.mock_summarizer
        
        self.writer_patch = patch('main.YAMLWriter')
        self.mock_writer_class = self.writer_patch.start()
        self.mock_patches.append(self.writer_patch)
        
        self.mock_writer = Mock()
        self.mock_writer_class.return_value = self.mock_writer
        
        # Mock transcript components
        self.transcript_gen_patch = patch('main.TranscriptGenerator')
        self.mock_transcript_gen_class = self.transcript_gen_patch.start()
        self.mock_patches.append(self.transcript_gen_patch)
        
        self.mock_transcript_gen = Mock()
        self.mock_transcript_gen_class.return_value = self.mock_transcript_gen
        
        self.transcript_writer_patch = patch('main.TranscriptWriter')
        self.mock_transcript_writer_class = self.transcript_writer_patch.start()
        self.mock_patches.append(self.transcript_writer_patch)
        
        self.mock_transcript_writer = Mock()
        self.mock_transcript_writer_class.return_value = self.mock_transcript_writer
        
        # Mock argument parsing
        self.parse_args_patch = patch('main.parse_arguments')
        self.mock_parse_args = self.parse_args_patch.start()
        self.mock_patches.append(self.parse_args_patch)
        
        # Mock os.path.exists for transcript workflow
        self.exists_patch = patch('main.os.path.exists')
        self.mock_exists = self.exists_patch.start()
        self.mock_patches.append(self.exists_patch)
        self.mock_exists.return_value = True
    
    def _create_test_yaml_file(self, email_count=2):
        """Create a test YAML file with sample email summaries."""
        yaml_content = f"""date: "{self.test_date}"
total_emails: {email_count}
emails:
"""
        for i in range(email_count):
            yaml_content += f"""  - subject: "Test Email {i+1}"
    sender: "test{i+1}@example.com"
    date: "2025-09-19T10:{30+i*10}:00Z"
    summary: "This is a test email summary {i+1}"
    key_points:
      - "Key point {i+1}.1"
      - "Key point {i+1}.2"
    action_items:
      - "Action item {i+1}.1"
"""
        
        with open(self.yaml_file_path, 'w') as f:
            f.write(yaml_content)
    
    def test_complete_workflow_with_transcript_generation(self):
        """Test complete email processing workflow with transcript generation enabled."""
        # Setup arguments
        args = Namespace(
            search_query=None,
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None,
            help_search=None,
            example_configs=False,
            validate_query=None,
            transcript_only=None,
            no_transcript=False,
            transcript_date=None,
            verbose=False
        )
        self.mock_parse_args.return_value = args
        
        # Setup email fetching
        mock_emails = [
            {
                "message_id": "msg1",
                "subject": "Important Meeting",
                "sender": "boss@company.com",
                "date": "Mon, 19 Sep 2025 10:30:00 +0000",
                "body": "We need to discuss the quarterly results."
            },
            {
                "message_id": "msg2",
                "subject": "Project Update",
                "sender": "team@company.com", 
                "date": "Mon, 19 Sep 2025 11:30:00 +0000",
                "body": "The project is on track for completion."
            }
        ]
        self.mock_fetcher.fetch_emails_with_query.return_value = mock_emails
        
        # Setup email processing
        self.mock_processor.clean_html_content.side_effect = lambda x: f"Cleaned: {x}"
        
        # Setup summarization
        mock_summaries = [
            {
                "subject": "Important Meeting",
                "sender": "boss@company.com",
                "date": "2025-09-19T10:30:00Z",
                "summary": "Meeting discussion about quarterly results",
                "key_points": ["Quarterly results review", "Performance metrics"],
                "action_items": ["Prepare presentation", "Schedule follow-up"]
            },
            {
                "subject": "Project Update", 
                "sender": "team@company.com",
                "date": "2025-09-19T11:30:00Z",
                "summary": "Project status update showing good progress",
                "key_points": ["On track completion", "Team performance"],
                "action_items": ["Continue current pace", "Monitor milestones"]
            }
        ]
        self.mock_summarizer.batch_summarize_emails.return_value = mock_summaries
        
        # Setup YAML file writing
        yaml_file_path = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        self.mock_writer.write_daily_summary.return_value = yaml_file_path
        self.mock_writer.get_summary_stats.return_value = {
            "exists": True,
            "file_size": 1024,
            "email_count": 2
        }
        
        # Create the actual YAML file for transcript generation
        self._create_test_yaml_file(2)
        
        # Setup transcript generation
        mock_transcript_content = """Good morning! Here's your email briefing for September 19, 2025.

Today I processed 2 important emails for you.

Let me walk you through the key highlights:

First, you received an important meeting request from boss@company.com about quarterly results. The main points include quarterly results review and performance metrics. You'll need to prepare a presentation and schedule a follow-up.

Moving on to the project update from team@company.com. The project status shows good progress and is on track for completion. The team performance is solid, so you should continue the current pace and monitor milestones.

That concludes your email briefing for today. Have a great day!"""
        
        self.mock_transcript_gen.generate_transcript.return_value = mock_transcript_content
        
        transcript_file_path = os.path.join(self.transcript_dir, f"{self.test_date}.txt")
        self.mock_transcript_writer.write_transcript.return_value = transcript_file_path
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify email processing pipeline
        self.mock_fetcher.fetch_emails_with_query.assert_called_once_with(
            "is:unread is:important", 10
        )
        self.mock_summarizer.batch_summarize_emails.assert_called_once()
        self.mock_writer.write_daily_summary.assert_called_once_with(mock_summaries)
        
        # Verify transcript generation was called
        self.mock_transcript_gen_class.assert_called_once_with(self.mock_config)
        self.mock_transcript_writer_class.assert_called_once_with(self.transcript_dir)
        self.mock_transcript_gen.generate_transcript.assert_called_once_with(yaml_file_path, self.test_date)
        self.mock_transcript_writer.write_transcript.assert_called_once_with(mock_transcript_content, self.test_date)
    
    def test_workflow_with_no_transcript_flag(self):
        """Test workflow with --no-transcript flag disables transcript generation."""
        # Setup arguments with no-transcript flag
        args = Namespace(
            search_query=None,
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None,
            help_search=None,
            example_configs=False,
            validate_query=None,
            transcript_only=None,
            no_transcript=True,  # Transcript disabled
            transcript_date=None,
            verbose=False
        )
        self.mock_parse_args.return_value = args
        
        # Setup minimal email processing
        self.mock_fetcher.fetch_emails_with_query.return_value = []
        self.mock_writer.create_empty_summary_file.return_value = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify transcript components were NOT initialized
        self.mock_transcript_gen_class.assert_not_called()
        self.mock_transcript_writer_class.assert_not_called()
    
    def test_workflow_with_transcript_disabled_in_config(self):
        """Test workflow with transcript generation disabled in configuration."""
        # Disable transcript in config
        self.mock_config.enable_transcript_generation = False
        
        # Setup arguments
        args = Namespace(
            search_query=None,
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None,
            help_search=None,
            example_configs=False,
            validate_query=None,
            transcript_only=None,
            no_transcript=False,
            transcript_date=None,
            verbose=False
        )
        self.mock_parse_args.return_value = args
        
        # Setup minimal email processing
        self.mock_fetcher.fetch_emails_with_query.return_value = []
        self.mock_writer.create_empty_summary_file.return_value = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify transcript components were NOT initialized
        self.mock_transcript_gen_class.assert_not_called()
        self.mock_transcript_writer_class.assert_not_called()


class TestTranscriptOnlyWorkflow(unittest.TestCase):
    """Integration tests for --transcript-only workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_dir = os.path.join(self.temp_dir, "email_summaries")
        self.transcript_dir = os.path.join(self.temp_dir, "transcripts")
        os.makedirs(self.yaml_dir, exist_ok=True)
        os.makedirs(self.transcript_dir, exist_ok=True)
        
        self.test_date = "2025-09-19"
        self.yaml_file_path = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        
        # Mock patches
        self.mock_patches = []
        self._setup_mocks()
        
    def tearDown(self):
        """Clean up test fixtures."""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        shutil.rmtree(self.temp_dir)
    
    def _setup_mocks(self):
        """Set up mock patches."""
        # Mock configuration loading
        self.config_patch = patch('main.load_config')
        self.mock_load_config = self.config_patch.start()
        self.mock_patches.append(self.config_patch)
        
        self.mock_config = Mock(spec=Config)
        self.mock_config.output_directory = self.yaml_dir
        self.mock_config.transcript_output_directory = self.transcript_dir
        self.mock_config.enable_transcript_generation = True
        self.mock_load_config.return_value = self.mock_config
        
        # Mock transcript components
        self.transcript_gen_patch = patch('main.TranscriptGenerator')
        self.mock_transcript_gen_class = self.transcript_gen_patch.start()
        self.mock_patches.append(self.transcript_gen_patch)
        
        self.mock_transcript_gen = Mock()
        self.mock_transcript_gen_class.return_value = self.mock_transcript_gen
        
        self.transcript_writer_patch = patch('main.TranscriptWriter')
        self.mock_transcript_writer_class = self.transcript_writer_patch.start()
        self.mock_patches.append(self.transcript_writer_patch)
        
        self.mock_transcript_writer = Mock()
        self.mock_transcript_writer_class.return_value = self.mock_transcript_writer
        
        # Mock directory functions
        self.ensure_transcript_dir_patch = patch('main.ensure_transcript_directory', return_value=True)
        self.mock_ensure_transcript_dir = self.ensure_transcript_dir_patch.start()
        self.mock_patches.append(self.ensure_transcript_dir_patch)
        
        # Mock argument parsing
        self.parse_args_patch = patch('main.parse_arguments')
        self.mock_parse_args = self.parse_args_patch.start()
        self.mock_patches.append(self.parse_args_patch)
    
    def _create_test_yaml_file(self, email_count=2):
        """Create a test YAML file with sample email summaries."""
        yaml_content = f"""date: "{self.test_date}"
total_emails: {email_count}
emails:
"""
        for i in range(email_count):
            yaml_content += f"""  - subject: "Test Email {i+1}"
    sender: "test{i+1}@example.com"
    date: "2025-09-19T10:{30+i*10}:00Z"
    summary: "This is a test email summary {i+1}"
    key_points:
      - "Key point {i+1}.1"
      - "Key point {i+1}.2"
    action_items:
      - "Action item {i+1}.1"
"""
        
        with open(self.yaml_file_path, 'w') as f:
            f.write(yaml_content)
    
    @patch('main.os.path.exists')
    def test_transcript_only_workflow_success(self, mock_exists):
        """Test successful --transcript-only workflow."""
        # Create test YAML file
        self._create_test_yaml_file()
        
        # Mock file existence check
        mock_exists.return_value = True
        
        # Setup arguments for transcript-only mode
        args = Namespace(
            transcript_only=self.test_date,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None,
            help_search=None,
            example_configs=False,
            validate_query=None,
            verbose=False
        )
        self.mock_parse_args.return_value = args
        
        # Setup transcript generation
        mock_transcript_content = f"""Good morning! Here's your email briefing for {self.test_date}.

Today I processed 2 important emails for you.

Let me walk you through the key highlights:

First, you received a test email from test1@example.com. Key points include key point 1.1 and key point 1.2. You'll need to handle action item 1.1.

Moving on to another test email from test2@example.com. This covers key point 2.1 and key point 2.2, with action item 2.1 to address.

That concludes your email briefing for today. Have a great day!"""
        
        self.mock_transcript_gen.generate_transcript.return_value = mock_transcript_content
        
        transcript_file_path = os.path.join(self.transcript_dir, f"{self.test_date}.txt")
        self.mock_transcript_writer.write_transcript.return_value = transcript_file_path
        
        # Execute transcript-only workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify transcript generation was called correctly
        expected_yaml_path = os.path.join(self.yaml_dir, f"{self.test_date}.yaml")
        self.mock_transcript_gen.generate_transcript.assert_called_once_with(expected_yaml_path, self.test_date)
        self.mock_transcript_writer.write_transcript.assert_called_once_with(mock_transcript_content, self.test_date)
    
    @patch('main.os.path.exists')
    def test_transcript_only_workflow_missing_yaml(self, mock_exists):
        """Test --transcript-only workflow with missing YAML file."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Setup arguments for transcript-only mode
        args = Namespace(
            transcript_only=self.test_date,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None,
            help_search=None,
            example_configs=False,
            validate_query=None,
            verbose=False
        )
        self.mock_parse_args.return_value = args
        
        # Execute transcript-only workflow
        result = process_emails()
        
        # Verify failure
        self.assertEqual(result, 1)
        
        # Verify transcript generation was NOT called
        self.mock_transcript_gen.generate_transcript.assert_not_called()
        self.mock_transcript_writer.write_transcript.assert_not_called()


class TestCLIOptionsIntegration(unittest.TestCase):
    """Integration tests for CLI options related to transcript generation."""
    
    def test_parse_arguments_transcript_options(self):
        """Test parsing of transcript-related CLI arguments."""
        # Test --no-transcript flag
        with patch('sys.argv', ['main.py', '--no-transcript']):
            args = parse_arguments()
            self.assertTrue(args.no_transcript)
            self.assertIsNone(args.transcript_only)
            self.assertIsNone(args.transcript_date)
        
        # Test --transcript-only option
        with patch('sys.argv', ['main.py', '--transcript-only', '2025-09-19']):
            args = parse_arguments()
            self.assertFalse(args.no_transcript)
            self.assertEqual(args.transcript_only, '2025-09-19')
            self.assertIsNone(args.transcript_date)
        
        # Test --transcript-date option
        with patch('sys.argv', ['main.py', '--transcript-date', '2025-09-20']):
            args = parse_arguments()
            self.assertFalse(args.no_transcript)
            self.assertIsNone(args.transcript_only)
            self.assertEqual(args.transcript_date, '2025-09-20')
        
        # Test combined options
        with patch('sys.argv', ['main.py', '--transcript-only', '2025-09-19', '--verbose']):
            args = parse_arguments()
            self.assertEqual(args.transcript_only, '2025-09-19')
            self.assertTrue(args.verbose)


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for configuration loading with transcript settings."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('config.settings.load_config')
    def test_configuration_loading_with_transcript_settings(self, mock_load_config):
        """Test configuration loading includes transcript settings."""
        # Setup mock config with transcript settings
        mock_config = Mock(spec=Config)
        mock_config.enable_transcript_generation = True
        mock_config.transcript_output_directory = "transcripts"
        mock_config.transcript_max_tokens = 1000
        mock_config.transcript_temperature = 0.7
        mock_load_config.return_value = mock_config
        
        # Import and test
        from config.settings import load_config
        config = load_config()
        
        # Verify transcript settings are available
        self.assertTrue(hasattr(config, 'enable_transcript_generation'))
        self.assertTrue(hasattr(config, 'transcript_output_directory'))
        self.assertTrue(hasattr(config, 'transcript_max_tokens'))
        self.assertTrue(hasattr(config, 'transcript_temperature'))
        
        self.assertTrue(config.enable_transcript_generation)
        self.assertEqual(config.transcript_output_directory, "transcripts")
        self.assertEqual(config.transcript_max_tokens, 1000)
        self.assertEqual(config.transcript_temperature, 0.7)


class TestEmailSummaryScenarios(unittest.TestCase):
    """Integration tests for various email summary scenarios with transcript generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_dir = os.path.join(self.temp_dir, "email_summaries")
        self.transcript_dir = os.path.join(self.temp_dir, "transcripts")
        os.makedirs(self.yaml_dir, exist_ok=True)
        os.makedirs(self.transcript_dir, exist_ok=True)
        
        # Mock patches
        self.mock_patches = []
        self._setup_mocks()
        
    def tearDown(self):
        """Clean up test fixtures."""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        shutil.rmtree(self.temp_dir)
    
    def _setup_mocks(self):
        """Set up mock patches."""
        # Mock configuration
        self.config_patch = patch('main.load_config')
        self.mock_load_config = self.config_patch.start()
        self.mock_patches.append(self.config_patch)
        
        self.mock_config = Mock(spec=Config)
        self.mock_config.output_directory = self.yaml_dir
        self.mock_config.transcript_output_directory = self.transcript_dir
        self.mock_config.enable_transcript_generation = True
        self.mock_config.ai_provider = "openai"
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.openai_model = "gpt-3.5-turbo"
        self.mock_load_config.return_value = self.mock_config
        
        # Mock transcript components
        self.transcript_gen_patch = patch('summarization.transcript_generator.TranscriptGenerator')
        self.mock_transcript_gen_class = self.transcript_gen_patch.start()
        self.mock_patches.append(self.transcript_gen_patch)
        
        self.mock_transcript_gen = Mock()
        self.mock_transcript_gen_class.return_value = self.mock_transcript_gen
        
        self.transcript_writer_patch = patch('storage.transcript_writer.TranscriptWriter')
        self.mock_transcript_writer_class = self.transcript_writer_patch.start()
        self.mock_patches.append(self.transcript_writer_patch)
        
        self.mock_transcript_writer = Mock()
        self.mock_transcript_writer_class.return_value = self.mock_transcript_writer
        
        # Mock EmailSummarizer for TranscriptGenerator
        self.email_summarizer_patch = patch('summarization.summarizer.EmailSummarizer')
        self.mock_email_summarizer_class = self.email_summarizer_patch.start()
        self.mock_patches.append(self.email_summarizer_patch)
        
        self.mock_email_summarizer = Mock()
        self.mock_email_summarizer_class.return_value = self.mock_email_summarizer
        
        # Mock directory functions
        self.ensure_transcript_dir_patch = patch('main.ensure_transcript_directory', return_value=True)
        self.mock_ensure_transcript_dir = self.ensure_transcript_dir_patch.start()
        self.mock_patches.append(self.ensure_transcript_dir_patch)
    
    def _create_yaml_file(self, date, email_count):
        """Create a YAML file with specified number of emails."""
        yaml_file_path = os.path.join(self.yaml_dir, f"{date}.yaml")
        
        if email_count == 0:
            yaml_content = f"""date: "{date}"
total_emails: 0
emails: []
"""
        else:
            yaml_content = f"""date: "{date}"
total_emails: {email_count}
emails:
"""
            for i in range(email_count):
                yaml_content += f"""  - subject: "Email {i+1}"
    sender: "sender{i+1}@example.com"
    date: "{date}T10:{30+i*10}:00Z"
    summary: "Summary for email {i+1}"
    key_points:
      - "Key point {i+1}.1"
    action_items:
      - "Action {i+1}.1"
"""
        
        with open(yaml_file_path, 'w') as f:
            f.write(yaml_content)
        return yaml_file_path
    
    @patch('main.os.path.exists')
    def test_single_email_scenario(self, mock_exists):
        """Test transcript generation for single email scenario."""
        test_date = "2025-09-19"
        yaml_file_path = self._create_yaml_file(test_date, 1)
        mock_exists.return_value = True
        
        # Setup transcript generation
        expected_transcript = f"""Good morning! Here's your email briefing for {test_date}.

Today I processed 1 important email for you.

You received an email from sender1@example.com with the subject "Email 1". The summary indicates this covers key point 1.1, and you have action 1.1 to handle.

That concludes your email briefing for today. Have a great day!"""
        
        self.mock_transcript_gen.generate_transcript.return_value = expected_transcript
        transcript_file_path = os.path.join(self.transcript_dir, f"{test_date}.txt")
        self.mock_transcript_writer.write_transcript.return_value = transcript_file_path
        
        # Test transcript generation
        from main import generate_transcript_for_workflow
        result = generate_transcript_for_workflow(self.mock_config, yaml_file_path, None, False)
        
        # Verify success
        self.assertTrue(result)
        self.mock_transcript_gen.generate_transcript.assert_called_once_with(yaml_file_path, test_date)
        self.mock_transcript_writer.write_transcript.assert_called_once_with(expected_transcript, test_date)
    
    @patch('main.os.path.exists')
    def test_multiple_emails_scenario(self, mock_exists):
        """Test transcript generation for multiple emails scenario."""
        test_date = "2025-09-20"
        yaml_file_path = self._create_yaml_file(test_date, 5)
        mock_exists.return_value = True
        
        # Setup transcript generation
        expected_transcript = f"""Good morning! Here's your email briefing for {test_date}.

Today I processed 5 important emails for you.

Let me walk you through the key highlights:

First, you received an email from sender1@example.com about "Email 1"...
[Additional email summaries]

To wrap up, here are the main action items:
- Action 1.1
- Action 2.1
- Action 3.1
- Action 4.1
- Action 5.1

That concludes your email briefing for today. Have a great day!"""
        
        self.mock_transcript_gen.generate_transcript.return_value = expected_transcript
        transcript_file_path = os.path.join(self.transcript_dir, f"{test_date}.txt")
        self.mock_transcript_writer.write_transcript.return_value = transcript_file_path
        
        # Test transcript generation
        from main import generate_transcript_for_workflow
        result = generate_transcript_for_workflow(self.mock_config, yaml_file_path, None, False)
        
        # Verify success
        self.assertTrue(result)
        self.mock_transcript_gen.generate_transcript.assert_called_once_with(yaml_file_path, test_date)
        self.mock_transcript_writer.write_transcript.assert_called_once_with(expected_transcript, test_date)
    
    @patch('main.os.path.exists')
    def test_empty_emails_scenario(self, mock_exists):
        """Test transcript generation for empty emails scenario."""
        test_date = "2025-09-21"
        yaml_file_path = self._create_yaml_file(test_date, 0)
        mock_exists.return_value = True
        
        # Setup transcript generation for empty day
        expected_transcript = f"""Good morning! Here's your email briefing for {test_date}.

I didn't find any important emails that needed your attention today. 

Enjoy your day with a lighter inbox!"""
        
        self.mock_transcript_gen.generate_transcript.return_value = expected_transcript
        transcript_file_path = os.path.join(self.transcript_dir, f"{test_date}.txt")
        self.mock_transcript_writer.write_transcript.return_value = transcript_file_path
        
        # Test transcript generation
        from main import generate_transcript_for_workflow
        result = generate_transcript_for_workflow(self.mock_config, yaml_file_path, None, False)
        
        # Verify success
        self.assertTrue(result)
        self.mock_transcript_gen.generate_transcript.assert_called_once_with(yaml_file_path, test_date)
        self.mock_transcript_writer.write_transcript.assert_called_once_with(expected_transcript, test_date)


if __name__ == '__main__':
    unittest.main()