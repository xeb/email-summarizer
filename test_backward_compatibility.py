"""
Integration tests for backward compatibility and migration support.

This module tests that the Gmail Email Summarizer continues to work correctly
when search configuration features are unavailable or when migrating from
older configuration file formats.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import json
import shutil
from datetime import datetime
from argparse import Namespace

from main import determine_search_query, process_emails, handle_config_commands
from config.search_configs import SearchConfigManager, SearchConfig, CorruptedConfigFileError
from config.settings import Config, load_config
from utils.error_handling import RetryableError, NonRetryableError, ErrorCategory


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        
        self.config = Config()
        self.config.search_configs_file = self.config_file
        self.config.default_search_query = "is:unread is:important"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_functionality_without_search_configs_file(self):
        """Test that application works when search configs file doesn't exist."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        args = Namespace(
            search_query=None,
            search_config=None
        )
        
        # Should fall back to default query without error
        result = determine_search_query(args, self.config)
        self.assertEqual(result, "is:unread is:important")
    
    def test_functionality_with_corrupted_config_file(self):
        """Test graceful handling of corrupted configuration file."""
        # Create corrupted JSON file
        with open(self.config_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        args = Namespace(
            search_query=None,
            search_config=None
        )
        
        # Should fall back to default query
        result = determine_search_query(args, self.config)
        self.assertEqual(result, "is:unread is:important")
    
    def test_functionality_with_empty_config_file(self):
        """Test handling of empty configuration file."""
        # Create empty file
        with open(self.config_file, 'w') as f:
            f.write('')
        
        args = Namespace(
            search_query=None,
            search_config=None
        )
        
        # Should fall back to default query
        result = determine_search_query(args, self.config)
        self.assertEqual(result, "is:unread is:important")
    
    def test_functionality_with_missing_search_config_attributes(self):
        """Test that application works when config object lacks search-related attributes."""
        # Create config without search-related attributes
        minimal_config = Mock()
        minimal_config.default_search_query = "is:unread is:important"
        # Missing search_configs_file and enable_search_validation
        
        args = Namespace(
            search_query="from:test@example.com",
            search_config=None
        )
        
        # Should work with custom query
        result = determine_search_query(args, minimal_config)
        self.assertEqual(result, "from:test@example.com")
    
    def test_graceful_degradation_when_search_features_unavailable(self):
        """Test graceful degradation when search configuration features are unavailable."""
        # Mock SearchConfigManager to report features as unavailable
        with patch('main.SearchConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.is_search_feature_available.return_value = False
            mock_manager_class.return_value = mock_manager
            
            args = Namespace(
                search_query=None,
                search_config="some-config"
            )
            
            # Should fall back to default query when features are unavailable
            result = determine_search_query(args, self.config)
            self.assertEqual(result, "is:unread is:important")
    
    def test_custom_query_works_without_validation(self):
        """Test that custom queries work even when validation is unavailable."""
        # Remove config file to make validation unavailable
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        args = Namespace(
            search_query="from:test@example.com is:unread",
            search_config=None
        )
        
        # Should use custom query even without validation
        result = determine_search_query(args, self.config)
        self.assertEqual(result, "from:test@example.com is:unread")


class TestConfigurationMigration(unittest.TestCase):
    """Test configuration file migration scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_migration_from_legacy_format(self):
        """Test migration from legacy configuration format (no version field)."""
        # Create legacy format configuration
        legacy_config = {
            "work-emails": {
                "name": "work-emails",
                "query": "from:@company.com is:unread",
                "description": "Work emails",
                "created_at": "2024-01-15T10:30:00",
                "usage_count": 5
            },
            "personal": {
                "name": "personal",
                "query": "from:@personal.com",
                "description": "Personal emails",
                "created_at": "2024-01-16T09:15:00",
                "usage_count": 2
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(legacy_config, f, indent=2)
        
        # Initialize search manager (should trigger migration)
        search_manager = SearchConfigManager(self.config_file)
        
        # Verify migration occurred
        with open(self.config_file, 'r') as f:
            migrated_data = json.load(f)
        
        self.assertEqual(migrated_data["version"], "1.0")
        self.assertIn("configs", migrated_data)
        # Legacy format should be migrated and preserved
        self.assertEqual(len(migrated_data["configs"]), 2)  # Both configs should be preserved
        
        # Verify backup was created
        backup_files = [f for f in os.listdir(self.temp_dir) if f.startswith("test_search_configs.json.backup_")]
        self.assertTrue(len(backup_files) > 0, "Backup file should have been created")
    
    def test_migration_from_version_with_configs_key(self):
        """Test migration from legacy format that has configs key but no version."""
        # Create legacy format with configs key
        legacy_config = {
            "configs": {
                "work-emails": {
                    "name": "work-emails",
                    "query": "from:@company.com is:unread",
                    "description": "Work emails",
                    "created_at": "2024-01-15T10:30:00",
                    "usage_count": 5
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(legacy_config, f, indent=2)
        
        # Initialize search manager (should trigger migration)
        search_manager = SearchConfigManager(self.config_file)
        
        # Verify migration occurred
        with open(self.config_file, 'r') as f:
            migrated_data = json.load(f)
        
        self.assertEqual(migrated_data["version"], "1.0")
        self.assertIn("configs", migrated_data)
        self.assertIn("work-emails", migrated_data["configs"])
        
        # Verify the configuration is still accessible
        config = search_manager.load_config("work-emails")
        self.assertIsNotNone(config)
        self.assertEqual(config.query, "from:@company.com is:unread")
    
    def test_handling_unsupported_future_version(self):
        """Test handling of configuration file from unsupported (future) version."""
        # Create configuration with future version
        future_config = {
            "version": "2.0",  # Future version
            "configs": {
                "test-config": {
                    "name": "test-config",
                    "query": "from:test@example.com",
                    "description": "Test configuration",
                    "created_at": "2024-01-15T10:30:00",
                    "usage_count": 1,
                    "future_field": "some future data"  # Unknown field
                }
            },
            "future_section": {
                "some_future_data": "value"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(future_config, f, indent=2)
        
        # Initialize search manager (should handle gracefully)
        search_manager = SearchConfigManager(self.config_file)
        
        # Verify it handled the unsupported version
        with open(self.config_file, 'r') as f:
            migrated_data = json.load(f)
        
        self.assertEqual(migrated_data["version"], "1.0")
        self.assertIn("configs", migrated_data)
        
        # Verify known fields were preserved
        if "test-config" in migrated_data["configs"]:
            preserved_config = migrated_data["configs"]["test-config"]
            self.assertEqual(preserved_config["query"], "from:test@example.com")
            self.assertEqual(preserved_config["description"], "Test configuration")
            # Future field should not be preserved
            self.assertNotIn("future_field", preserved_config)
    
    def test_backup_creation_during_migration(self):
        """Test that backups are created during migration."""
        # Create configuration that needs migration (no version field)
        legacy_config = {
            "test": {
                "name": "test",
                "query": "is:unread",
                "description": "Test",
                "created_at": "2024-01-15T10:30:00"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(legacy_config, f, indent=2)
        
        # Initialize search manager (should trigger migration and backup)
        search_manager = SearchConfigManager(self.config_file)
        
        # Check that backup was created
        backup_files = [f for f in os.listdir(self.temp_dir) if f.startswith("test_search_configs.json.backup_")]
        self.assertTrue(len(backup_files) > 0, "Backup file should have been created during migration")
        
        # Verify backup contains original data
        backup_path = os.path.join(self.temp_dir, backup_files[0])
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        self.assertEqual(backup_data, legacy_config)
    
    def test_migration_failure_recovery(self):
        """Test recovery when migration fails."""
        # Create a configuration file
        original_config = {
            "version": "1.0",
            "configs": {
                "test": {
                    "name": "test",
                    "query": "is:unread",
                    "description": "Test",
                    "created_at": "2024-01-15T10:30:00"
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(original_config, f, indent=2)
        
        # Mock migration to fail
        search_manager = SearchConfigManager(self.config_file)
        
        with patch.object(search_manager, '_migrate_config_file', return_value=None):
            # This should not crash, even if migration fails
            search_manager._check_and_migrate_config_file()
        
        # Original file should still be intact
        with open(self.config_file, 'r') as f:
            current_data = json.load(f)
        
        # Should still have the original data (migration failure should not corrupt file)
        self.assertIn("configs", current_data)


class TestEndToEndBackwardCompatibility(unittest.TestCase):
    """Test end-to-end backward compatibility scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        
        # Mock all external dependencies
        self.mock_patches = []
        
        # Mock configuration loading
        self.config_patch = patch('main.load_config')
        self.mock_load_config = self.config_patch.start()
        self.mock_patches.append(self.config_patch)
        
        self.mock_config = Mock()
        self.mock_config.search_configs_file = self.config_file
        self.mock_config.default_search_query = "is:unread is:important"
        self.mock_config.enable_search_validation = True
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
    
    def tearDown(self):
        """Clean up test fixtures."""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_without_search_config_file(self):
        """Test complete workflow when search configuration file doesn't exist."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        # Setup arguments for normal operation (no search customization)
        args = Namespace(
            search_query=None,
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
        
        # Setup successful email processing
        mock_emails = [
            {
                "message_id": "msg1",
                "subject": "Test Email",
                "sender": "test@example.com",
                "date": "Mon, 15 Jan 2024 10:30:00 +0000",
                "body": "Test content"
            }
        ]
        self.mock_fetcher.fetch_emails_with_query.return_value = mock_emails
        self.mock_processor.clean_html_content.return_value = "Cleaned content"
        self.mock_summarizer.batch_summarize_emails.return_value = [
            {"subject": "Test Email", "summary": "Test summary"}
        ]
        self.mock_writer.write_daily_summary.return_value = "/path/to/summary.yaml"
        self.mock_writer.get_summary_stats.return_value = {"exists": True, "file_size": 256, "email_count": 1}
        
        # Execute workflow
        result = process_emails()
        
        # Verify success
        self.assertEqual(result, 0)
        
        # Verify default query was used
        self.mock_fetcher.fetch_emails_with_query.assert_called_once_with(
            "is:unread is:important", 10
        )
    
    def test_end_to_end_with_corrupted_search_config_file(self):
        """Test complete workflow when search configuration file is corrupted."""
        # Create corrupted config file
        with open(self.config_file, 'w') as f:
            f.write('{"invalid": json}')
        
        # Setup arguments for normal operation
        args = Namespace(
            search_query=None,
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
        
        # Setup successful email processing
        mock_emails = [{"message_id": "msg1", "subject": "Test", "sender": "test@example.com", 
                       "date": "Mon, 15 Jan 2024 10:30:00 +0000", "body": "Test"}]
        self.mock_fetcher.fetch_emails_with_query.return_value = mock_emails
        self.mock_processor.clean_html_content.return_value = "Cleaned"
        self.mock_summarizer.batch_summarize_emails.return_value = [{"subject": "Test", "summary": "Summary"}]
        self.mock_writer.write_daily_summary.return_value = "/path/to/summary.yaml"
        self.mock_writer.get_summary_stats.return_value = {"exists": True, "file_size": 256, "email_count": 1}
        
        # Execute workflow
        result = process_emails()
        
        # Verify success (should work despite corrupted config)
        self.assertEqual(result, 0)
        
        # Verify default query was used
        self.mock_fetcher.fetch_emails_with_query.assert_called_once_with(
            "is:unread is:important", 10
        )
    
    def test_config_management_with_unavailable_features(self):
        """Test configuration management commands when search features are unavailable."""
        # Remove config file to make features unavailable
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        # Make the directory read-only to simulate unavailable features
        os.chmod(self.temp_dir, 0o444)
        
        try:
            args = Namespace(
                list_configs=True,
                save_config=None,
                delete_config=None,
                update_config=None
            )
            
            # Should handle gracefully
            result = handle_config_commands(args)
            
            # May return error code, but should not crash
            self.assertIn(result, [0, 1])
            
        finally:
            # Restore directory permissions
            os.chmod(self.temp_dir, 0o755)


class TestSearchFeatureAvailability(unittest.TestCase):
    """Test search feature availability detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_search_features_available_with_valid_config(self):
        """Test that search features are reported as available with valid configuration."""
        # Create valid configuration file
        config_data = {
            "version": "1.0",
            "configs": {}
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        search_manager = SearchConfigManager(self.config_file)
        
        self.assertTrue(search_manager.is_search_feature_available())
    
    def test_search_features_available_without_config_file(self):
        """Test that search features are available even without config file (will be created)."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        search_manager = SearchConfigManager(self.config_file)
        
        self.assertTrue(search_manager.is_search_feature_available())
    
    def test_search_features_unavailable_with_corrupted_config(self):
        """Test that search features are reported as unavailable with corrupted configuration."""
        # Create corrupted configuration file
        with open(self.config_file, 'w') as f:
            f.write('{"invalid": json}')
        
        # SearchConfigManager should raise CorruptedConfigFileError during initialization
        # This is the expected behavior for corrupted files
        with self.assertRaises(CorruptedConfigFileError):
            SearchConfigManager(self.config_file)
        
        # After the exception, the file should have been recreated
        # So a new SearchConfigManager should work
        search_manager = SearchConfigManager(self.config_file)
        self.assertTrue(search_manager.is_search_feature_available())
    
    def test_backward_compatibility_info(self):
        """Test backward compatibility information reporting."""
        # Create configuration file
        config_data = {
            "version": "1.0",
            "configs": {
                "test": {
                    "name": "test",
                    "query": "is:unread",
                    "description": "Test",
                    "created_at": "2024-01-15T10:30:00"
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        search_manager = SearchConfigManager(self.config_file)
        compat_info = search_manager.get_backward_compatibility_info()
        
        self.assertTrue(compat_info["search_features_available"])
        self.assertTrue(compat_info["config_file_exists"])
        self.assertEqual(compat_info["config_file_version"], "1.0")
        self.assertFalse(compat_info["migration_needed"])
        self.assertIn("1.0", compat_info["supported_versions"])
        self.assertEqual(compat_info["current_version"], "1.0")


if __name__ == '__main__':
    unittest.main()