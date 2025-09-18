#!/usr/bin/env python3
"""
Unit tests for configuration management command functions in Gmail Email Summarizer.

Tests the individual command handler functions: list_search_configs, save_search_config,
delete_search_config, and update_search_config.
"""

import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from io import StringIO
import sys

# Import the functions to test
from main import (
    list_search_configs, save_search_config, delete_search_config, 
    update_search_config, _handle_update_config
)
from config.search_configs import SearchConfig, SearchConfigManager


class TestListSearchConfigs(unittest.TestCase):
    """Test cases for list_search_configs function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
        
        # Create sample configurations
        self.sample_configs = [
            SearchConfig(
                name="work-emails",
                query="from:@company.com is:unread",
                description="Unread emails from company",
                created_at=datetime(2024, 1, 15, 10, 30),
                last_used=datetime(2024, 1, 16, 9, 15),
                usage_count=5
            ),
            SearchConfig(
                name="urgent-today",
                query="is:important newer_than:1d",
                description="Important emails from today",
                created_at=datetime(2024, 1, 15, 11, 0),
                last_used=None,
                usage_count=0
            )
        ]
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_list_configs_with_configurations(self, mock_stdout):
        """Test listing configurations when configurations exist."""
        # Setup mock
        self.mock_search_manager.list_configs.return_value = self.sample_configs
        self.mock_search_manager.get_config_stats.return_value = {
            "total_usage": 5,
            "most_used": {"name": "work-emails", "usage_count": 5}
        }
        
        # Call function
        result = list_search_configs(self.mock_search_manager)
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Found 2 saved search configuration(s)", output)
        self.assertIn("work-emails", output)
        self.assertIn("from:@company.com is:unread", output)
        self.assertIn("Unread emails from company", output)
        self.assertIn("2024-01-15 10:30:00", output)
        self.assertIn("2024-01-16 09:15:00", output)
        self.assertIn("Usage count: 5", output)
        self.assertIn("urgent-today", output)
        self.assertIn("Last used: Never", output)
        self.assertIn("Total usage across all configs: 5", output)
        self.assertIn("Most used: work-emails (5 times)", output)
        
        # Verify manager calls
        self.mock_search_manager.list_configs.assert_called_once()
        self.mock_search_manager.get_config_stats.assert_called_once()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_list_configs_empty(self, mock_stdout):
        """Test listing configurations when no configurations exist."""
        # Setup mock
        self.mock_search_manager.list_configs.return_value = []
        
        # Call function
        result = list_search_configs(self.mock_search_manager)
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("No saved search configurations found", output)
        self.assertIn("Use --save-config to create your first configuration", output)
        
        # Verify manager calls
        self.mock_search_manager.list_configs.assert_called_once()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_list_configs_exception_handling(self, mock_stdout):
        """Test error handling when listing configurations fails."""
        # Setup mock to raise exception
        self.mock_search_manager.list_configs.side_effect = Exception("Test error")
        
        # Call function
        result = list_search_configs(self.mock_search_manager)
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify manager calls
        self.mock_search_manager.list_configs.assert_called_once()


class TestSaveSearchConfig(unittest.TestCase):
    """Test cases for save_search_config function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
        self.mock_search_manager.validator = MagicMock()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_success(self, mock_stdout):
        """Test successful configuration save."""
        # Setup mocks
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.save_config.return_value = True
        
        # Call function
        result = save_search_config(
            self.mock_search_manager, 
            "test-config", 
            "from:test@example.com", 
            "Test configuration"
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("✓ Successfully saved search configuration 'test-config'", output)
        self.assertIn("Query: from:test@example.com", output)
        self.assertIn("Description: Test configuration", output)
        
        # Verify manager calls
        self.mock_search_manager.validate_query.assert_called_once_with("from:test@example.com")
        self.mock_search_manager.save_config.assert_called_once()
        
        # Verify the SearchConfig object passed to save_config
        call_args = self.mock_search_manager.save_config.call_args[0][0]
        self.assertEqual(call_args.name, "test-config")
        self.assertEqual(call_args.query, "from:test@example.com")
        self.assertEqual(call_args.description, "Test configuration")
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_empty_name(self, mock_stdout):
        """Test save configuration with empty name."""
        result = save_search_config(self.mock_search_manager, "", "query", "description")
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration name cannot be empty", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_empty_query(self, mock_stdout):
        """Test save configuration with empty query."""
        result = save_search_config(self.mock_search_manager, "name", "", "description")
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Search query cannot be empty", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_empty_description(self, mock_stdout):
        """Test save configuration with empty description."""
        result = save_search_config(self.mock_search_manager, "name", "query", "")
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Description cannot be empty", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_invalid_query(self, mock_stdout):
        """Test save configuration with invalid query."""
        # Setup mock
        self.mock_search_manager.validate_query.return_value = (False, "Invalid operator")
        self.mock_search_manager.validator.suggest_corrections.return_value = ["Use from: instead of form:"]
        
        # Call function
        result = save_search_config(
            self.mock_search_manager, 
            "test-config", 
            "form:test@example.com", 
            "Test configuration"
        )
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Invalid search query - Invalid operator", output)
        self.assertIn("Suggestions:", output)
        self.assertIn("Use from: instead of form:", output)
        
        # Verify manager calls
        self.mock_search_manager.validate_query.assert_called_once_with("form:test@example.com")
        self.mock_search_manager.validator.suggest_corrections.assert_called_once_with("form:test@example.com")
        self.mock_search_manager.save_config.assert_not_called()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_already_exists(self, mock_stdout):
        """Test save configuration when name already exists."""
        # Setup mocks
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.save_config.side_effect = ValueError("Configuration 'test-config' already exists")
        
        # Call function
        result = save_search_config(
            self.mock_search_manager, 
            "test-config", 
            "from:test@example.com", 
            "Test configuration"
        )
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration 'test-config' already exists", output)
        self.assertIn("Use --delete-config to remove it first", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_save_config_whitespace_handling(self, mock_stdout):
        """Test that whitespace is properly stripped from inputs."""
        # Setup mocks
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.save_config.return_value = True
        
        # Call function with whitespace
        result = save_search_config(
            self.mock_search_manager, 
            "  test-config  ", 
            "  from:test@example.com  ", 
            "  Test configuration  "
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify the SearchConfig object passed to save_config has stripped values
        call_args = self.mock_search_manager.save_config.call_args[0][0]
        self.assertEqual(call_args.name, "test-config")
        self.assertEqual(call_args.query, "from:test@example.com")
        self.assertEqual(call_args.description, "Test configuration")


class TestDeleteSearchConfig(unittest.TestCase):
    """Test cases for delete_search_config function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
        self.sample_config = SearchConfig(
            name="test-config",
            query="from:test@example.com",
            description="Test configuration",
            created_at=datetime(2024, 1, 15, 10, 30),
            usage_count=3
        )
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_delete_config_success(self, mock_stdout):
        """Test successful configuration deletion."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.sample_config
        self.mock_search_manager.delete_config.return_value = True
        
        # Call function
        result = delete_search_config(self.mock_search_manager, "test-config")
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Configuration to delete:", output)
        self.assertIn("Name: test-config", output)
        self.assertIn("Query: from:test@example.com", output)
        self.assertIn("Description: Test configuration", output)
        self.assertIn("Usage count: 3", output)
        self.assertIn("✓ Successfully deleted configuration 'test-config'", output)
        
        # Verify manager calls
        self.mock_search_manager.load_config.assert_called_once_with("test-config")
        self.mock_search_manager.delete_config.assert_called_once_with("test-config")
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_delete_config_empty_name(self, mock_stdout):
        """Test delete configuration with empty name."""
        result = delete_search_config(self.mock_search_manager, "")
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration name cannot be empty", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_delete_config_not_found(self, mock_stdout):
        """Test delete configuration when configuration doesn't exist."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = None
        self.mock_search_manager.list_configs.return_value = [
            SearchConfig("other-config", "query", "desc", datetime.now())
        ]
        
        # Call function
        result = delete_search_config(self.mock_search_manager, "nonexistent")
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration 'nonexistent' not found", output)
        self.assertIn("Available configurations:", output)
        self.assertIn("other-config", output)
        
        # Verify manager calls
        self.mock_search_manager.load_config.assert_called_once_with("nonexistent")
        self.mock_search_manager.list_configs.assert_called_once()
        self.mock_search_manager.delete_config.assert_not_called()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_delete_config_not_found_no_configs(self, mock_stdout):
        """Test delete configuration when no configurations exist."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = None
        self.mock_search_manager.list_configs.return_value = []
        
        # Call function
        result = delete_search_config(self.mock_search_manager, "nonexistent")
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration 'nonexistent' not found", output)
        self.assertIn("No saved configurations found", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_delete_config_deletion_fails(self, mock_stdout):
        """Test delete configuration when deletion operation fails."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.sample_config
        self.mock_search_manager.delete_config.return_value = False
        
        # Call function
        result = delete_search_config(self.mock_search_manager, "test-config")
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Failed to delete configuration 'test-config'", output)


class TestUpdateSearchConfig(unittest.TestCase):
    """Test cases for update_search_config function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
        self.mock_search_manager.validator = MagicMock()
        self.existing_config = SearchConfig(
            name="test-config",
            query="from:old@example.com",
            description="Old description",
            created_at=datetime(2024, 1, 15, 10, 30),
            last_used=datetime(2024, 1, 16, 9, 15),
            usage_count=5
        )
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_query_only(self, mock_stdout):
        """Test updating only the query."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.existing_config
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.update_config.return_value = True
        
        # Call function
        result = update_search_config(
            self.mock_search_manager, 
            "test-config", 
            query="from:new@example.com"
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Updating configuration 'test-config'", output)
        self.assertIn("Current query: from:old@example.com", output)
        self.assertIn("New query: from:new@example.com", output)
        self.assertIn("Current description: Old description", output)
        self.assertIn("New description: Old description", output)
        self.assertIn("✓ Successfully updated configuration 'test-config'", output)
        
        # Verify manager calls
        self.mock_search_manager.load_config.assert_called_once_with("test-config")
        self.mock_search_manager.validate_query.assert_called_once_with("from:new@example.com")
        self.mock_search_manager.update_config.assert_called_once()
        
        # Verify the updated config preserves original metadata
        call_args = self.mock_search_manager.update_config.call_args[0][1]
        self.assertEqual(call_args.name, "test-config")
        self.assertEqual(call_args.query, "from:new@example.com")
        self.assertEqual(call_args.description, "Old description")
        self.assertEqual(call_args.created_at, self.existing_config.created_at)
        self.assertEqual(call_args.last_used, self.existing_config.last_used)
        self.assertEqual(call_args.usage_count, self.existing_config.usage_count)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_description_only(self, mock_stdout):
        """Test updating only the description."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.existing_config
        self.mock_search_manager.update_config.return_value = True
        
        # Call function
        result = update_search_config(
            self.mock_search_manager, 
            "test-config", 
            description="New description"
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify the updated config
        call_args = self.mock_search_manager.update_config.call_args[0][1]
        self.assertEqual(call_args.query, "from:old@example.com")  # Unchanged
        self.assertEqual(call_args.description, "New description")  # Changed
        
        # Verify query validation was not called since query wasn't changed
        self.mock_search_manager.validate_query.assert_not_called()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_both_fields(self, mock_stdout):
        """Test updating both query and description."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.existing_config
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.update_config.return_value = True
        
        # Call function
        result = update_search_config(
            self.mock_search_manager, 
            "test-config", 
            query="from:new@example.com",
            description="New description"
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify the updated config
        call_args = self.mock_search_manager.update_config.call_args[0][1]
        self.assertEqual(call_args.query, "from:new@example.com")
        self.assertEqual(call_args.description, "New description")
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_empty_name(self, mock_stdout):
        """Test update configuration with empty name."""
        result = update_search_config(self.mock_search_manager, "", query="new query")
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration name cannot be empty", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_not_found(self, mock_stdout):
        """Test update configuration when configuration doesn't exist."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = None
        self.mock_search_manager.list_configs.return_value = [
            SearchConfig("other-config", "query", "desc", datetime.now())
        ]
        
        # Call function
        result = update_search_config(
            self.mock_search_manager, 
            "nonexistent", 
            query="new query"
        )
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Configuration 'nonexistent' not found", output)
        self.assertIn("Available configurations:", output)
        self.assertIn("other-config", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_invalid_query(self, mock_stdout):
        """Test update configuration with invalid query."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.existing_config
        self.mock_search_manager.validate_query.return_value = (False, "Invalid operator")
        self.mock_search_manager.validator.suggest_corrections.return_value = ["Use from: instead"]
        
        # Call function
        result = update_search_config(
            self.mock_search_manager, 
            "test-config", 
            query="invalid:query"
        )
        
        # Verify result
        self.assertEqual(result, 1)
        
        # Verify output
        output = mock_stdout.getvalue()
        self.assertIn("Error: Invalid search query - Invalid operator", output)
        self.assertIn("Suggestions:", output)
        self.assertIn("Use from: instead", output)
        
        # Verify update was not called
        self.mock_search_manager.update_config.assert_not_called()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_update_config_whitespace_handling(self, mock_stdout):
        """Test that whitespace is properly handled in updates."""
        # Setup mocks
        self.mock_search_manager.load_config.return_value = self.existing_config
        self.mock_search_manager.validate_query.return_value = (True, "")
        self.mock_search_manager.update_config.return_value = True
        
        # Call function with whitespace
        result = update_search_config(
            self.mock_search_manager, 
            "  test-config  ", 
            query="  from:new@example.com  ",
            description="  New description  "
        )
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify the updated config has stripped values
        call_args = self.mock_search_manager.update_config.call_args[0][1]
        self.assertEqual(call_args.query, "from:new@example.com")
        self.assertEqual(call_args.description, "New description")


class TestHandleUpdateConfig(unittest.TestCase):
    """Test cases for _handle_update_config function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_update_config_insufficient_args(self, mock_stdout):
        """Test handling update config with insufficient arguments."""
        result = _handle_update_config(self.mock_search_manager, ["name-only"])
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: --update-config requires at least a name and one field to update", output)
        self.assertIn("Usage: --update-config NAME query=", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_update_config_invalid_format(self, mock_stdout):
        """Test handling update config with invalid field format."""
        result = _handle_update_config(self.mock_search_manager, ["name", "invalid-format"])
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Invalid update argument 'invalid-format'", output)
        self.assertIn("Expected format: field=value", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_update_config_unknown_field(self, mock_stdout):
        """Test handling update config with unknown field."""
        result = _handle_update_config(self.mock_search_manager, ["name", "unknown=value"])
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: Unknown field 'unknown'", output)
        self.assertIn("Supported fields: query, description", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_update_config_no_fields(self, mock_stdout):
        """Test handling update config with no valid fields."""
        # This shouldn't happen in practice, but test the edge case
        result = _handle_update_config(self.mock_search_manager, ["name"])
        
        self.assertEqual(result, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Error: --update-config requires at least a name and one field to update", output)
    
    @patch('main.update_search_config')
    def test_handle_update_config_success(self, mock_update_func):
        """Test successful handling of update config."""
        mock_update_func.return_value = 0
        
        result = _handle_update_config(
            self.mock_search_manager, 
            ["test-config", "query=new query", "description=new desc"]
        )
        
        self.assertEqual(result, 0)
        mock_update_func.assert_called_once_with(
            self.mock_search_manager, 
            "test-config", 
            "new query", 
            "new desc"
        )
    
    @patch('main.update_search_config')
    def test_handle_update_config_quoted_values(self, mock_update_func):
        """Test handling of quoted values in update config."""
        mock_update_func.return_value = 0
        
        result = _handle_update_config(
            self.mock_search_manager, 
            ["test-config", 'query="quoted query"', "description='single quoted'"]
        )
        
        self.assertEqual(result, 0)
        mock_update_func.assert_called_once_with(
            self.mock_search_manager, 
            "test-config", 
            "quoted query", 
            "single quoted"
        )


if __name__ == '__main__':
    unittest.main()