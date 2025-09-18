#!/usr/bin/env python3
"""
Unit tests for example configurations and Gmail search help functionality.

Tests the example configurations, search help system, and validation features
to ensure they provide accurate and helpful information to users.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

from config.example_configs import (
    GmailSearchHelp, ExampleConfigurations, 
    validate_example_configurations, create_example_config_file
)
from config.search_configs import SearchConfig, QueryValidator


class TestGmailSearchHelp(unittest.TestCase):
    """Test cases for Gmail search help functionality."""
    
    def test_get_operator_help_all(self):
        """Test getting help for all operators."""
        help_text = GmailSearchHelp.get_operator_help()
        
        self.assertIn("Gmail Search Operators Reference", help_text)
        self.assertIn("from:", help_text)
        self.assertIn("to:", help_text)
        self.assertIn("subject:", help_text)
        self.assertIn("Common Search Patterns:", help_text)
    
    def test_get_operator_help_specific(self):
        """Test getting help for a specific operator."""
        help_text = GmailSearchHelp.get_operator_help("from:")
        
        self.assertIn("from:", help_text)
        self.assertIn("Description:", help_text)
        self.assertIn("Examples:", help_text)
        self.assertIn("Tips:", help_text)
        self.assertIn("from:john@example.com", help_text)
    
    def test_get_operator_help_unknown(self):
        """Test getting help for an unknown operator."""
        help_text = GmailSearchHelp.get_operator_help("unknown:")
        
        self.assertIn("Unknown operator: unknown:", help_text)
        self.assertIn("--help-search", help_text)
    
    def test_get_search_suggestions(self):
        """Test getting search suggestions for queries."""
        # Test query with from: but no unread filter
        suggestions = GmailSearchHelp.get_search_suggestions("from:john@example.com")
        self.assertTrue(any("is:unread" in s for s in suggestions))
        
        # Test query with has:attachment but no size filter
        suggestions = GmailSearchHelp.get_search_suggestions("has:attachment")
        self.assertTrue(any("larger:" in s for s in suggestions))
        
        # Test query without date filters
        suggestions = GmailSearchHelp.get_search_suggestions("subject:meeting")
        self.assertTrue(any("date filter" in s for s in suggestions))
    
    def test_operators_have_required_fields(self):
        """Test that all operators have required fields."""
        for operator, info in GmailSearchHelp.OPERATORS.items():
            self.assertIn('description', info)
            self.assertIn('examples', info)
            self.assertIn('tips', info)
            self.assertIsInstance(info['examples'], list)
            self.assertIsInstance(info['tips'], list)
            self.assertTrue(len(info['examples']) > 0)
            self.assertTrue(len(info['tips']) > 0)
    
    def test_search_patterns_structure(self):
        """Test that search patterns have proper structure."""
        for pattern_name, pattern_info in GmailSearchHelp.SEARCH_PATTERNS.items():
            self.assertIn('query', pattern_info)
            self.assertIn('description', pattern_info)
            self.assertIn('use_case', pattern_info)
            self.assertIsInstance(pattern_info['query'], str)
            self.assertTrue(len(pattern_info['query']) > 0)


class TestExampleConfigurations(unittest.TestCase):
    """Test cases for example configurations functionality."""
    
    def test_get_example_configs(self):
        """Test getting example configurations."""
        configs = ExampleConfigurations.get_example_configs()
        
        self.assertIsInstance(configs, list)
        self.assertTrue(len(configs) > 0)
        
        # Check that all configs are SearchConfig instances
        for config in configs:
            self.assertIsInstance(config, SearchConfig)
            self.assertIsInstance(config.name, str)
            self.assertIsInstance(config.query, str)
            self.assertIsInstance(config.description, str)
            self.assertIsInstance(config.created_at, datetime)
            self.assertTrue(len(config.name) > 0)
            self.assertTrue(len(config.query) > 0)
            self.assertTrue(len(config.description) > 0)
    
    def test_get_config_by_category(self):
        """Test getting configurations organized by category."""
        categories = ExampleConfigurations.get_config_by_category()
        
        self.assertIsInstance(categories, dict)
        self.assertTrue(len(categories) > 0)
        
        # Check that categories contain SearchConfig instances
        for category, configs in categories.items():
            self.assertIsInstance(category, str)
            self.assertIsInstance(configs, list)
            for config in configs:
                self.assertIsInstance(config, SearchConfig)
    
    def test_get_config_suggestions_for_query(self):
        """Test getting relevant configurations for a query."""
        # Test with work-related query
        suggestions = ExampleConfigurations.get_config_suggestions_for_query("from:@company.com")
        self.assertIsInstance(suggestions, list)
        
        # Test with attachment-related query
        suggestions = ExampleConfigurations.get_config_suggestions_for_query("has:attachment")
        self.assertIsInstance(suggestions, list)
        
        # Test with meeting-related query
        suggestions = ExampleConfigurations.get_config_suggestions_for_query("subject:meeting")
        self.assertIsInstance(suggestions, list)
        
        # Should return at most 5 suggestions
        for suggestion_list in [suggestions]:
            self.assertLessEqual(len(suggestion_list), 5)
    
    def test_unique_config_names(self):
        """Test that all example configuration names are unique."""
        configs = ExampleConfigurations.get_example_configs()
        names = [config.name for config in configs]
        
        self.assertEqual(len(names), len(set(names)), "Configuration names must be unique")
    
    def test_config_queries_not_empty(self):
        """Test that all configuration queries are non-empty."""
        configs = ExampleConfigurations.get_example_configs()
        
        for config in configs:
            self.assertTrue(config.query.strip(), f"Config '{config.name}' has empty query")
    
    def test_config_descriptions_not_empty(self):
        """Test that all configuration descriptions are non-empty."""
        configs = ExampleConfigurations.get_example_configs()
        
        for config in configs:
            self.assertTrue(config.description.strip(), f"Config '{config.name}' has empty description")


class TestExampleConfigValidation(unittest.TestCase):
    """Test cases for example configuration validation."""
    
    def test_validate_example_configurations(self):
        """Test that all example configurations have valid queries."""
        is_valid, errors = validate_example_configurations()
        
        if not is_valid:
            self.fail(f"Example configurations have invalid queries:\n" + "\n".join(errors))
        
        self.assertTrue(is_valid, "All example configurations should have valid queries")
        self.assertEqual(len(errors), 0, "No validation errors should exist")
    
    def test_individual_config_validation(self):
        """Test validation of individual example configurations."""
        validator = QueryValidator()
        configs = ExampleConfigurations.get_example_configs()
        
        for config in configs:
            is_valid, error_msg = validator.validate_query(config.query)
            self.assertTrue(
                is_valid, 
                f"Config '{config.name}' has invalid query '{config.query}': {error_msg}"
            )
    
    def test_config_queries_use_supported_operators(self):
        """Test that example configurations only use supported Gmail operators."""
        validator = QueryValidator()
        configs = ExampleConfigurations.get_example_configs()
        
        for config in configs:
            operators = validator._extract_operators(config.query)
            for operator, value in operators:
                self.assertIn(
                    operator, 
                    validator.SUPPORTED_OPERATORS,
                    f"Config '{config.name}' uses unsupported operator '{operator}'"
                )


class TestCreateExampleConfigFile(unittest.TestCase):
    """Test cases for creating example configuration files."""
    
    def test_create_example_config_file(self):
        """Test creating an example configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create the example file
            success = create_example_config_file(temp_path)
            self.assertTrue(success, "Should successfully create example config file")
            
            # Verify file exists and has valid JSON
            self.assertTrue(os.path.exists(temp_path), "Example config file should exist")
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # Verify structure
            self.assertIn('version', data)
            self.assertIn('description', data)
            self.assertIn('usage', data)
            self.assertIn('categories', data)
            self.assertIn('all_examples', data)
            
            # Verify categories contain configurations
            self.assertIsInstance(data['categories'], dict)
            self.assertTrue(len(data['categories']) > 0)
            
            # Verify all_examples contains configurations
            self.assertIsInstance(data['all_examples'], dict)
            self.assertTrue(len(data['all_examples']) > 0)
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_create_example_config_file_invalid_path(self):
        """Test creating example config file with invalid path."""
        invalid_path = "/invalid/path/that/does/not/exist/example.json"
        
        success = create_example_config_file(invalid_path)
        self.assertFalse(success, "Should fail to create file at invalid path")


class TestSearchHelpIntegration(unittest.TestCase):
    """Integration tests for search help functionality."""
    
    def test_help_covers_all_validator_operators(self):
        """Test that help system covers all operators supported by validator."""
        validator = QueryValidator()
        help_operators = set(GmailSearchHelp.OPERATORS.keys())
        validator_operators = set(validator.SUPPORTED_OPERATORS)
        
        # Help should cover all validator operators
        missing_operators = validator_operators - help_operators
        self.assertEqual(
            len(missing_operators), 0,
            f"Help system missing operators: {missing_operators}"
        )
    
    def test_help_examples_are_valid(self):
        """Test that all examples in help system are valid queries."""
        validator = QueryValidator()
        
        for operator, info in GmailSearchHelp.OPERATORS.items():
            for example in info['examples']:
                is_valid, error_msg = validator.validate_query(example)
                self.assertTrue(
                    is_valid,
                    f"Help example '{example}' for operator '{operator}' is invalid: {error_msg}"
                )
    
    def test_search_patterns_are_valid(self):
        """Test that all search patterns in help system are valid queries."""
        validator = QueryValidator()
        
        for pattern_name, pattern_info in GmailSearchHelp.SEARCH_PATTERNS.items():
            query = pattern_info['query']
            is_valid, error_msg = validator.validate_query(query)
            self.assertTrue(
                is_valid,
                f"Search pattern '{pattern_name}' has invalid query '{query}': {error_msg}"
            )


class TestMainIntegration(unittest.TestCase):
    """Integration tests for main.py help functionality."""
    
    @patch('main.GmailSearchHelp')
    def test_handle_search_help_all(self, mock_help):
        """Test handle_search_help with 'all' parameter."""
        from main import handle_search_help
        
        mock_help.get_operator_help.return_value = "Mock help text"
        
        result = handle_search_help('all')
        
        self.assertEqual(result, 0)
        mock_help.get_operator_help.assert_called_once_with()
    
    @patch('main.GmailSearchHelp')
    def test_handle_search_help_specific(self, mock_help):
        """Test handle_search_help with specific operator."""
        from main import handle_search_help
        
        mock_help.get_operator_help.return_value = "Mock help text for from:"
        
        result = handle_search_help('from')
        
        self.assertEqual(result, 0)
        mock_help.get_operator_help.assert_called_once_with('from:')
    
    @patch('main.ExampleConfigurations')
    def test_show_example_configs(self, mock_examples):
        """Test show_example_configs function."""
        from main import show_example_configs
        
        mock_config = MagicMock()
        mock_config.name = "test-config"
        mock_config.query = "test query"
        mock_config.description = "test description"
        
        mock_examples.get_config_by_category.return_value = {
            "Test Category": [mock_config]
        }
        
        result = show_example_configs()
        
        self.assertEqual(result, 0)
        mock_examples.get_config_by_category.assert_called_once()
    
    @patch('config.search_configs.QueryValidator')
    @patch('main.GmailSearchHelp')
    @patch('main.ExampleConfigurations')
    def test_validate_search_query_valid(self, mock_examples, mock_help, mock_validator_class):
        """Test validate_search_query with valid query."""
        from main import validate_search_query
        
        mock_validator = MagicMock()
        mock_validator.validate_query.return_value = (True, "")
        mock_validator_class.return_value = mock_validator
        
        mock_help.get_search_suggestions.return_value = ["suggestion 1"]
        mock_examples.get_config_suggestions_for_query.return_value = []
        
        result = validate_search_query("is:unread")
        
        self.assertEqual(result, 0)
        mock_validator.validate_query.assert_called_once_with("is:unread")
    
    @patch('config.search_configs.QueryValidator')
    def test_validate_search_query_invalid(self, mock_validator_class):
        """Test validate_search_query with invalid query."""
        from main import validate_search_query
        
        mock_validator = MagicMock()
        mock_validator.validate_query.return_value = (False, "Invalid operator")
        mock_validator.suggest_corrections.return_value = ["correction 1"]
        mock_validator_class.return_value = mock_validator
        
        result = validate_search_query("invalid:query")
        
        self.assertEqual(result, 1)
        mock_validator.validate_query.assert_called_once_with("invalid:query")
        mock_validator.suggest_corrections.assert_called_once_with("invalid:query")


if __name__ == '__main__':
    unittest.main()