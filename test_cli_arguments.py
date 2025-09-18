#!/usr/bin/env python3
"""
Unit tests for CLI argument parsing in Gmail Email Summarizer.

Tests the new search configuration management command-line arguments
and their validation logic.
"""

import unittest
import sys
import argparse
from unittest.mock import patch, MagicMock
from datetime import datetime
from io import StringIO

# Import the main module functions
from main import parse_arguments, handle_config_commands, determine_search_query
from config.search_configs import SearchConfigManager, SearchConfig


class TestCLIArgumentParsing(unittest.TestCase):
    """Test cases for command-line argument parsing."""
    
    def test_parse_basic_arguments(self):
        """Test parsing of basic existing arguments."""
        with patch('sys.argv', ['main.py', '--verbose', '--max-emails', '5']):
            args = parse_arguments()
            self.assertTrue(args.verbose)
            self.assertEqual(args.max_emails, 5)
            self.assertIsNone(args.search_config)
            self.assertIsNone(args.search_query)
            self.assertFalse(args.list_configs)
            self.assertIsNone(args.save_config)
            self.assertIsNone(args.delete_config)
    
    def test_parse_search_config_argument(self):
        """Test parsing of --search-config argument."""
        with patch('sys.argv', ['main.py', '--search-config', 'work-emails']):
            args = parse_arguments()
            self.assertEqual(args.search_config, 'work-emails')
            self.assertIsNone(args.search_query)
    
    def test_parse_search_config_short_form(self):
        """Test parsing of -sc short form argument."""
        with patch('sys.argv', ['main.py', '-sc', 'urgent-today']):
            args = parse_arguments()
            self.assertEqual(args.search_config, 'urgent-today')
    
    def test_parse_search_query_argument(self):
        """Test parsing of --search-query argument."""
        query = "from:boss@company.com is:unread"
        with patch('sys.argv', ['main.py', '--search-query', query]):
            args = parse_arguments()
            self.assertEqual(args.search_query, query)
            self.assertIsNone(args.search_config)
    
    def test_parse_search_query_short_form(self):
        """Test parsing of -sq short form argument."""
        query = "is:important newer_than:1d"
        with patch('sys.argv', ['main.py', '-sq', query]):
            args = parse_arguments()
            self.assertEqual(args.search_query, query)
    
    def test_parse_list_configs_argument(self):
        """Test parsing of --list-configs argument."""
        with patch('sys.argv', ['main.py', '--list-configs']):
            args = parse_arguments()
            self.assertTrue(args.list_configs)
    
    def test_parse_save_config_argument(self):
        """Test parsing of --save-config argument with three parameters."""
        with patch('sys.argv', ['main.py', '--save-config', 'test-config', 'is:unread', 'Test description']):
            args = parse_arguments()
            self.assertEqual(args.save_config, ['test-config', 'is:unread', 'Test description'])
    
    def test_parse_delete_config_argument(self):
        """Test parsing of --delete-config argument."""
        with patch('sys.argv', ['main.py', '--delete-config', 'old-config']):
            args = parse_arguments()
            self.assertEqual(args.delete_config, 'old-config')
    
    def test_parse_combined_arguments(self):
        """Test parsing multiple arguments together."""
        with patch('sys.argv', ['main.py', '--verbose', '--search-config', 'work', '--max-emails', '10']):
            args = parse_arguments()
            self.assertTrue(args.verbose)
            self.assertEqual(args.search_config, 'work')
            self.assertEqual(args.max_emails, 10)
    
    def test_parse_both_search_arguments(self):
        """Test parsing both search-config and search-query (should be allowed)."""
        with patch('sys.argv', ['main.py', '--search-config', 'work', '--search-query', 'is:unread']):
            args = parse_arguments()
            self.assertEqual(args.search_config, 'work')
            self.assertEqual(args.search_query, 'is:unread')
    
    def test_save_config_requires_three_arguments(self):
        """Test that --save-config requires exactly three arguments."""
        # This should raise SystemExit due to argparse error
        with patch('sys.argv', ['main.py', '--save-config', 'name', 'query']):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_argument_help_text(self):
        """Test that help text is properly formatted."""
        parser = argparse.ArgumentParser()
        
        # Add the same arguments as in parse_arguments
        parser.add_argument('--search-config', '-sc', type=str, help='Use a saved search configuration by name')
        parser.add_argument('--search-query', '-sq', type=str, help='Use a custom Gmail search query directly')
        parser.add_argument('--list-configs', action='store_true', help='List all saved search configurations and exit')
        parser.add_argument('--save-config', nargs=3, metavar=('NAME', 'QUERY', 'DESCRIPTION'), help='Save a new search configuration with name, query, and description')
        parser.add_argument('--delete-config', type=str, metavar='NAME', help='Delete a saved search configuration by name')
        
        # Test that help can be generated without errors
        help_text = parser.format_help()
        self.assertIn('--search-config', help_text)
        self.assertIn('--search-query', help_text)
        self.assertIn('--list-configs', help_text)
        self.assertIn('--save-config', help_text)
        self.assertIn('--delete-config', help_text)


class TestConfigurationCommands(unittest.TestCase):
    """Test cases for configuration management commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_config.search_configs_file = 'test_search_configs.json'
        
        # Create a mock SearchConfigManager
        self.mock_search_manager = MagicMock(spec=SearchConfigManager)
    
    @patch('main.load_config')
    @patch('main.SearchConfigManager')
    @patch('main.list_search_configs')
    def test_handle_list_configs_command(self, mock_list_func, mock_manager_class, mock_load_config):
        """Test handling of --list-configs command."""
        # Setup mocks
        mock_load_config.return_value = self.mock_config
        mock_manager_class.return_value = self.mock_search_manager
        mock_list_func.return_value = 0
        
        # Create mock args
        args = MagicMock()
        args.list_configs = True
        args.save_config = None
        args.delete_config = None
        
        # Test the function
        result = handle_config_commands(args)
        
        # Verify calls
        mock_load_config.assert_called_once()
        mock_manager_class.assert_called_once_with('test_search_configs.json')
        mock_list_func.assert_called_once_with(self.mock_search_manager)
        self.assertEqual(result, 0)
    
    @patch('main.load_config')
    @patch('main.SearchConfigManager')
    @patch('main.save_search_config')
    def test_handle_save_config_command(self, mock_save_func, mock_manager_class, mock_load_config):
        """Test handling of --save-config command."""
        # Setup mocks
        mock_load_config.return_value = self.mock_config
        mock_manager_class.return_value = self.mock_search_manager
        mock_save_func.return_value = 0
        
        # Create mock args
        args = MagicMock()
        args.list_configs = False
        args.save_config = ['test-name', 'test-query', 'test-description']
        args.delete_config = None
        
        # Test the function
        result = handle_config_commands(args)
        
        # Verify calls
        mock_load_config.assert_called_once()
        mock_manager_class.assert_called_once_with('test_search_configs.json')
        mock_save_func.assert_called_once_with(self.mock_search_manager, 'test-name', 'test-query', 'test-description')
        self.assertEqual(result, 0)
    
    @patch('main.load_config')
    @patch('main.SearchConfigManager')
    @patch('main.delete_search_config')
    def test_handle_delete_config_command(self, mock_delete_func, mock_manager_class, mock_load_config):
        """Test handling of --delete-config command."""
        # Setup mocks
        mock_load_config.return_value = self.mock_config
        mock_manager_class.return_value = self.mock_search_manager
        mock_delete_func.return_value = 0
        
        # Create mock args
        args = MagicMock()
        args.list_configs = False
        args.save_config = None
        args.delete_config = 'config-to-delete'
        
        # Test the function
        result = handle_config_commands(args)
        
        # Verify calls
        mock_load_config.assert_called_once()
        mock_manager_class.assert_called_once_with('test_search_configs.json')
        mock_delete_func.assert_called_once_with(self.mock_search_manager, 'config-to-delete')
        self.assertEqual(result, 0)
    
    @patch('main.load_config')
    def test_handle_config_commands_error_handling(self, mock_load_config):
        """Test error handling in configuration commands."""
        # Setup mock to raise exception
        mock_load_config.side_effect = Exception("Test error")
        
        # Create mock args
        args = MagicMock()
        args.list_configs = True
        args.save_config = None
        args.delete_config = None
        
        # Test the function
        result = handle_config_commands(args)
        
        # Should return error code
        self.assertEqual(result, 1)


class TestSearchQueryDetermination(unittest.TestCase):
    """Test cases for search query determination logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_config.search_configs_file = 'test_search_configs.json'
        self.mock_config.default_search_query = 'is:unread is:important'
    
    def test_determine_query_with_custom_query(self):
        """Test query determination when --search-query is provided."""
        args = MagicMock()
        args.search_query = 'from:test@example.com'
        args.search_config = None
        
        result = determine_search_query(args, self.mock_config)
        self.assertEqual(result, 'from:test@example.com')
    
    def test_determine_query_with_custom_query_strips_whitespace(self):
        """Test that custom query whitespace is stripped."""
        args = MagicMock()
        args.search_query = '  from:test@example.com  '
        args.search_config = None
        
        result = determine_search_query(args, self.mock_config)
        self.assertEqual(result, 'from:test@example.com')
    
    @patch('main.SearchConfigManager')
    def test_determine_query_with_saved_config(self, mock_manager_class):
        """Test query determination when --search-config is provided."""
        # Setup mock search manager
        mock_search_manager = MagicMock()
        mock_manager_class.return_value = mock_search_manager
        
        # Create a mock saved configuration
        saved_config = SearchConfig(
            name='test-config',
            query='is:starred',
            description='Test config',
            created_at=datetime.now()
        )
        mock_search_manager.load_config.return_value = saved_config
        
        args = MagicMock()
        args.search_query = None
        args.search_config = 'test-config'
        
        result = determine_search_query(args, self.mock_config)
        
        # Verify calls
        mock_manager_class.assert_called_once_with('test_search_configs.json')
        mock_search_manager.load_config.assert_called_once_with('test-config')
        mock_search_manager.update_usage_stats.assert_called_once_with('test-config')
        
        self.assertEqual(result, 'is:starred')
    
    @patch('main.SearchConfigManager')
    def test_determine_query_with_nonexistent_config(self, mock_manager_class):
        """Test error handling when saved config doesn't exist."""
        # Setup mock search manager
        mock_search_manager = MagicMock()
        mock_manager_class.return_value = mock_search_manager
        mock_search_manager.load_config.return_value = None
        mock_search_manager.list_configs.return_value = []
        
        args = MagicMock()
        args.search_query = None
        args.search_config = 'nonexistent-config'
        
        with self.assertRaises(ValueError) as context:
            determine_search_query(args, self.mock_config)
        
        self.assertIn('nonexistent-config', str(context.exception))
        self.assertIn('not found', str(context.exception))
    
    @patch('main.SearchConfigManager')
    def test_determine_query_with_nonexistent_config_shows_available(self, mock_manager_class):
        """Test that available configs are shown when requested config doesn't exist."""
        # Setup mock search manager
        mock_search_manager = MagicMock()
        mock_manager_class.return_value = mock_search_manager
        mock_search_manager.load_config.return_value = None
        
        # Mock available configurations
        available_configs = [
            SearchConfig('config1', 'query1', 'desc1', datetime.now()),
            SearchConfig('config2', 'query2', 'desc2', datetime.now())
        ]
        mock_search_manager.list_configs.return_value = available_configs
        
        args = MagicMock()
        args.search_query = None
        args.search_config = 'nonexistent-config'
        
        with self.assertRaises(ValueError) as context:
            determine_search_query(args, self.mock_config)
        
        error_message = str(context.exception)
        self.assertIn('config1', error_message)
        self.assertIn('config2', error_message)
    
    def test_determine_query_with_default(self):
        """Test query determination when no custom options are provided."""
        args = MagicMock()
        args.search_query = None
        args.search_config = None
        
        result = determine_search_query(args, self.mock_config)
        self.assertEqual(result, 'is:unread is:important')
    
    def test_determine_query_priority_search_query_over_config(self):
        """Test that --search-query takes priority over --search-config."""
        args = MagicMock()
        args.search_query = 'custom query'
        args.search_config = 'some-config'
        
        result = determine_search_query(args, self.mock_config)
        self.assertEqual(result, 'custom query')
    
    def test_determine_query_with_missing_default_config_attribute(self):
        """Test fallback when config doesn't have default_search_query attribute."""
        config_without_default = MagicMock()
        config_without_default.search_configs_file = 'test.json'
        # Don't set default_search_query attribute
        del config_without_default.default_search_query
        
        args = MagicMock()
        args.search_query = None
        args.search_config = None
        
        result = determine_search_query(args, config_without_default)
        self.assertEqual(result, 'is:unread is:important')  # Should use hardcoded fallback


class TestArgumentValidation(unittest.TestCase):
    """Test cases for argument validation and error handling."""
    
    def test_empty_search_query_handling(self):
        """Test handling of empty search query strings."""
        args = MagicMock()
        args.search_query = '   '  # Only whitespace
        args.search_config = None
        
        config = MagicMock()
        config.default_search_query = 'is:unread'
        
        # Should strip whitespace and fall back to config
        result = determine_search_query(args, config)
        self.assertEqual(result, 'is:unread')
    
    def test_none_search_query_handling(self):
        """Test handling of None search query."""
        args = MagicMock()
        args.search_query = None
        args.search_config = None
        
        config = MagicMock()
        config.default_search_query = 'is:unread'
        
        result = determine_search_query(args, config)
        self.assertEqual(result, 'is:unread')


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)