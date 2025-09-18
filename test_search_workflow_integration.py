"""
Integration tests for Gmail search customization workflow.

This module tests the end-to-end workflow integration of custom search functionality,
including search query determination, configuration usage tracking, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import json
from datetime import datetime
from argparse import Namespace

from main import determine_search_query, process_emails
from config.search_configs import SearchConfigManager, SearchConfig
from config.settings import Config
from utils.error_handling import RetryableError, NonRetryableError, ErrorCategory


class TestSearchQueryDetermination(unittest.TestCase):
    """Test search query determination logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config.search_configs_file = "test_search_configs.json"
        self.config.default_search_query = "is:unread is:important"
        
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        self.config.search_configs_file = self.config_file
        
        # Initialize search manager with test config
        self.search_manager = SearchConfigManager(self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_determine_search_query_custom_query_priority(self):
        """Test that --search-query takes priority over --search-config."""
        args = Namespace(
            search_query="from:priority@example.com",
            search_config="work-emails"
        )
        
        result = determine_search_query(args, self.config)
        
        self.assertEqual(result, "from:priority@example.com")
    
    def test_determine_search_query_saved_config(self):
        """Test using saved search configuration."""
        # Create a test configuration
        test_config = SearchConfig(
            name="work-emails",
            query="from:@company.com is:unread",
            description="Work emails",
            created_at=datetime.now()
        )
        self.search_manager.save_config(test_config)
        
        args = Namespace(
            search_query=None,
            search_config="work-emails"
        )
        
        result = determine_search_query(args, self.config)
        
        self.assertEqual(result, "from:@company.com is:unread")
        
        # Verify usage stats were updated
        updated_config = self.search_manager.load_config("work-emails")
        self.assertEqual(updated_config.usage_count, 1)
        self.assertIsNotNone(updated_config.last_used)
    
    def test_determine_search_query_default(self):
        """Test using default search query."""
        args = Namespace(
            search_query=None,
            search_config=None
        )
        
        result = determine_search_query(args, self.config)
        
        self.assertEqual(result, "is:unread is:important")
    
    def test_determine_search_query_config_not_found(self):
        """Test error when search configuration is not found."""
        args = Namespace(
            search_query=None,
            search_config="nonexistent-config"
        )
        
        with self.assertRaises(ValueError) as context:
            determine_search_query(args, self.config)
        
        self.assertIn("Search configuration 'nonexistent-config' not found", str(context.exception))
    
    def test_determine_search_query_config_not_found_with_suggestions(self):
        """Test error message includes available configurations when config not found."""
        # Create some test configurations
        configs = [
            SearchConfig("work-emails", "from:@company.com", "Work emails", datetime.now()),
            SearchConfig("personal", "from:@personal.com", "Personal emails", datetime.now())
        ]
        
        for config in configs:
            self.search_manager.save_config(config)
        
        args = Namespace(
            search_query=None,
            search_config="nonexistent-config"
        )
        
        with self.assertRaises(ValueError) as context:
            determine_search_query(args, self.config)
        
        error_message = str(context.exception)
        self.assertIn("Search configuration 'nonexistent-config' not found", error_message)
        # Check that both configurations are mentioned (order may vary)
        self.assertIn("work-emails", error_message)
        self.assertIn("personal", error_message)
        self.assertIn("Available configurations:", error_message)
    
    def test_determine_search_query_empty_query_handling(self):
        """Test handling of empty search query strings."""
        args = Namespace(
            search_query="   ",  # Empty/whitespace query
            search_config=None
        )
        
        result = determine_search_query(args, self.config)
        
        # Should fall back to default when query is empty/whitespace
        self.assertEqual(result, "is:unread is:important")


class TestWorkflowIntegration(unittest.TestCase):
    """Test end-to-end workflow integration with search customization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        
        # Mock all the external dependencies
        self.mock_patches = []
        
        # Mock configuration loading
        self.config_patch = patch('main.load_config')
        self.mock_load_config = self.config_patch.start()
        self.mock_patches.append(self.config_patch)
        
        self.mock_config = Mock()
        self.mock_config.search_configs_file = self.config_file
        self.mock_config.default_search_query = "is:unread is:important"
        self.mock_config.max_emails_per_run = 10
        self.mock_config.output_directory = self.temp_dir
        self.mock_config.credentials_file = "credentials.json"
        self.mock_config.token_file = "token.json"
        self.mock_load_config.return_value = self.mock_config
        
        # Mock validation functions
        self.validate_creds_patch = patch('main.validate_gmail_credentials', return_value=True)
        self.mock_validate_creds = self.validate_creds_patch.start()
        self.mock_patches.append(self.validate_creds_patch)
        
        self.ensure_dir_patch = patch('main.ensure_output_directory', return_value=True)
        self.mock_ensure_dir = self.ensure_dir_patch.start()
        self.mock_patches.append(self.ensure_dir_patch)
        
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
        
        # Mock argument parsing
        self.parse_args_patch = patch('main.parse_arguments')
        self.mock_parse_args = self.parse_args_patch.start()
        self.mock_patches.append(self.parse_args_patch)
        
        # Initialize search manager
        self.search_manager = SearchConfigManager(self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_workflow_with_custom_search_query(self):
        """Test end-to-end workflow with custom search query."""
        # Setup arguments
        args = Namespace(
            search_query="from:test@example.com is:unread",
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Setup email fetching
        mock_emails = [
            {
                "message_id": "msg1",
                "subject": "Test Email 1",
                "sender": "test@example.com",
                "date": "Mon, 15 Jan 2024 10:30:00 +0000",
                "body": "Test email content 1"
            },
            {
                "message_id": "msg2", 
                "subject": "Test Email 2",
                "sender": "test@example.com",
                "date": "Mon, 15 Jan 2024 11:30:00 +0000",
                "body": "Test email content 2"
            }
        ]
        self.mock_fetcher.fetch_emails_with_query.return_value = mock_emails
        
        # Setup email processing
        self.mock_processor.clean_html_content.side_effect = lambda x: f"Cleaned: {x}"
        
        # Setup summarization
        mock_summaries = [
            {"subject": "Test Email 1", "summary": "Summary 1"},
            {"subject": "Test Email 2", "summary": "Summary 2"}
        ]
        self.mock_summarizer.batch_summarize_emails.return_value = mock_summaries
        
        # Setup file writing
        self.mock_writer.write_daily_summary.return_value = "/path/to/summary.yaml"
        self.mock_writer.get_summary_stats.return_value = {
            "exists": True,
            "file_size": 1024,
            "email_count": 2
        }
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify custom query was used
        self.mock_fetcher.fetch_emails_with_query.assert_called_once_with(
            "from:test@example.com is:unread", 10
        )
        
        # Verify processing pipeline
        self.mock_summarizer.batch_summarize_emails.assert_called_once()
        self.mock_writer.write_daily_summary.assert_called_once_with(mock_summaries)
    
    def test_workflow_with_saved_search_config(self):
        """Test end-to-end workflow with saved search configuration."""
        # Create a test configuration
        test_config = SearchConfig(
            name="work-emails",
            query="from:@company.com is:unread after:2024-01-01",
            description="Work emails from this year",
            created_at=datetime.now(),
            usage_count=5
        )
        self.search_manager.save_config(test_config)
        
        # Setup arguments
        args = Namespace(
            search_query=None,
            search_config="work-emails",
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Setup email fetching
        mock_emails = [
            {
                "message_id": "msg1",
                "subject": "Work Email",
                "sender": "colleague@company.com",
                "date": "Mon, 15 Jan 2024 10:30:00 +0000",
                "body": "Work email content"
            }
        ]
        self.mock_fetcher.fetch_emails_with_query.return_value = mock_emails
        
        # Setup other mocks
        self.mock_processor.clean_html_content.return_value = "Cleaned work content"
        self.mock_summarizer.batch_summarize_emails.return_value = [
            {"subject": "Work Email", "summary": "Work summary"}
        ]
        self.mock_writer.write_daily_summary.return_value = "/path/to/summary.yaml"
        self.mock_writer.get_summary_stats.return_value = {"exists": True, "file_size": 512, "email_count": 1}
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify saved config query was used
        self.mock_fetcher.fetch_emails_with_query.assert_called_once_with(
            "from:@company.com is:unread after:2024-01-01", 10
        )
        
        # Verify usage statistics were updated
        updated_config = self.search_manager.load_config("work-emails")
        self.assertEqual(updated_config.usage_count, 6)  # Incremented from 5
        self.assertIsNotNone(updated_config.last_used)
    
    def test_workflow_with_invalid_search_config(self):
        """Test workflow error handling with invalid search configuration."""
        # Setup arguments with non-existent config
        args = Namespace(
            search_query=None,
            search_config="nonexistent-config",
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Execute workflow
        result = process_emails()
        
        # Verify error exit code
        self.assertEqual(result, 1)
        
        # Verify email fetcher was not called
        self.mock_fetcher.fetch_emails_with_query.assert_not_called()
    
    def test_workflow_with_no_matching_emails(self):
        """Test workflow when search query returns no emails."""
        # Setup arguments
        args = Namespace(
            search_query="from:nonexistent@example.com",
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Setup email fetching to return no emails
        self.mock_fetcher.fetch_emails_with_query.return_value = []
        
        # Setup empty file creation
        self.mock_writer.create_empty_summary_file.return_value = "/path/to/empty_summary.yaml"
        
        # Execute workflow
        result = process_emails()
        
        # Verify success (empty result is still success)
        self.assertEqual(result, 0)
        
        # Verify empty file was created
        self.mock_writer.create_empty_summary_file.assert_called_once()
        
        # Verify summarizer was not called
        self.mock_summarizer.batch_summarize_emails.assert_not_called()
    
    def test_workflow_error_handling_fetch_failure(self):
        """Test workflow error handling when email fetching fails."""
        # Setup arguments
        args = Namespace(
            search_query="from:test@example.com",
            search_config=None,
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Setup email fetching to fail
        self.mock_fetcher.fetch_emails_with_query.side_effect = RetryableError(
            "Network timeout", ErrorCategory.NETWORK
        )
        
        # Execute workflow
        result = process_emails()
        
        # Verify error exit code
        self.assertEqual(result, 1)
        
        # Verify subsequent steps were not called
        self.mock_summarizer.batch_summarize_emails.assert_not_called()
        self.mock_writer.write_daily_summary.assert_not_called()
    
    def test_workflow_usage_statistics_tracking(self):
        """Test that usage statistics are properly tracked during workflow."""
        # Create multiple test configurations
        configs = [
            SearchConfig("config1", "from:@example1.com", "Config 1", datetime.now(), usage_count=0),
            SearchConfig("config2", "from:@example2.com", "Config 2", datetime.now(), usage_count=3),
            SearchConfig("config3", "from:@example3.com", "Config 3", datetime.now(), usage_count=1)
        ]
        
        for config in configs:
            self.search_manager.save_config(config)
        
        # Setup arguments to use config2
        args = Namespace(
            search_query=None,
            search_config="config2",
            max_emails=None,
            output_dir=None,
            test_ai=False,
            list_configs=False,
            save_config=None,
            delete_config=None,
            update_config=None
        )
        self.mock_parse_args.return_value = args
        
        # Setup successful workflow
        self.mock_fetcher.fetch_emails_with_query.return_value = [
            {"message_id": "msg1", "subject": "Test", "sender": "test@example2.com", 
             "date": "Mon, 15 Jan 2024 10:30:00 +0000", "body": "Test content"}
        ]
        self.mock_processor.clean_html_content.return_value = "Cleaned content"
        self.mock_summarizer.batch_summarize_emails.return_value = [
            {"subject": "Test", "summary": "Test summary"}
        ]
        self.mock_writer.write_daily_summary.return_value = "/path/to/summary.yaml"
        self.mock_writer.get_summary_stats.return_value = {"exists": True, "file_size": 256, "email_count": 1}
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify usage statistics were updated for config2
        updated_config = self.search_manager.load_config("config2")
        self.assertEqual(updated_config.usage_count, 4)  # Incremented from 3
        self.assertIsNotNone(updated_config.last_used)
        
        # Verify other configs were not affected
        config1 = self.search_manager.load_config("config1")
        config3 = self.search_manager.load_config("config3")
        self.assertEqual(config1.usage_count, 0)
        self.assertEqual(config3.usage_count, 1)


class TestSearchConfigurationErrorHandling(unittest.TestCase):
    """Test error handling for search configuration scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        self.search_manager = SearchConfigManager(self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_corrupted_config_file_handling(self):
        """Test handling of corrupted configuration file."""
        # Create corrupted JSON file
        with open(self.config_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        config = Config()
        config.search_configs_file = self.config_file
        
        args = Namespace(
            search_query=None,
            search_config="any-config"
        )
        
        # Should handle the corrupted file gracefully
        with self.assertRaises(ValueError):
            determine_search_query(args, config)
    
    def test_missing_config_file_handling(self):
        """Test handling when configuration file doesn't exist."""
        # Remove the config file
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        config = Config()
        config.search_configs_file = self.config_file
        
        args = Namespace(
            search_query=None,
            search_config="any-config"
        )
        
        # Should handle missing file by creating it and then reporting config not found
        with self.assertRaises(ValueError) as context:
            determine_search_query(args, config)
        
        self.assertIn("not found", str(context.exception))
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.config_file))


if __name__ == '__main__':
    unittest.main()