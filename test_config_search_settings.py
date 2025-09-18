"""Unit tests for search-related configuration settings.

This module tests the extended Config dataclass with search configuration
settings, including validation and environment variable loading.
"""

import os
import pytest
import tempfile
from unittest.mock import patch
from config.settings import Config, load_config


class TestConfigSearchSettings:
    """Test cases for search-related configuration settings."""
    
    def test_default_search_settings(self):
        """Test that default search settings are properly initialized."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Config()
            
            assert config.search_configs_file == "search_configs.json"
            assert config.default_search_query == "is:unread is:important"
            assert config.enable_search_validation is True
            assert config.max_search_results == 100
    
    def test_search_settings_from_environment(self):
        """Test loading search settings from environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "SEARCH_CONFIGS_FILE": "custom_search.json",
            "DEFAULT_SEARCH_QUERY": "from:test@example.com is:unread",
            "ENABLE_SEARCH_VALIDATION": "false",
            "MAX_SEARCH_RESULTS": "50"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            assert config.search_configs_file == "custom_search.json"
            assert config.default_search_query == "from:test@example.com is:unread"
            assert config.enable_search_validation is False
            assert config.max_search_results == 50
    
    def test_boolean_environment_variable_parsing(self):
        """Test parsing of boolean environment variables for search validation."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),  # Empty string should be False
        ]
        
        for env_value, expected in test_cases:
            env_vars = {
                "OPENAI_API_KEY": "test-key",
                "ENABLE_SEARCH_VALIDATION": env_value
            }
            
            with patch.dict(os.environ, env_vars, clear=True):
                config = Config()
                assert config.enable_search_validation == expected, f"Failed for env value: '{env_value}'"
    
    def test_invalid_numeric_search_settings(self):
        """Test validation of invalid numeric search settings."""
        # Test invalid max_search_results
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "MAX_SEARCH_RESULTS": "0"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="max_search_results must be greater than 0"):
                Config()
        
        # Test negative max_search_results
        env_vars["MAX_SEARCH_RESULTS"] = "-10"
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="max_search_results must be greater than 0"):
                Config()
    
    def test_empty_search_configs_file_validation(self):
        """Test validation of empty search_configs_file."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "SEARCH_CONFIGS_FILE": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="search_configs_file cannot be empty"):
                Config()
    
    def test_empty_default_search_query_validation(self):
        """Test validation of empty default_search_query."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "DEFAULT_SEARCH_QUERY": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="default_search_query cannot be empty"):
                Config()
    
    def test_invalid_environment_variable_types(self):
        """Test handling of invalid environment variable types."""
        # Test invalid numeric value for MAX_SEARCH_RESULTS
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "MAX_SEARCH_RESULTS": "not-a-number"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Should use default value and log warning
            config = Config()
            assert config.max_search_results == 100  # Default value
    
    def test_search_settings_with_load_config_function(self):
        """Test that load_config function properly loads search settings."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "SEARCH_CONFIGS_FILE": "test_search.json",
            "DEFAULT_SEARCH_QUERY": "is:starred",
            "MAX_SEARCH_RESULTS": "75"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            
            assert config.search_configs_file == "test_search.json"
            assert config.default_search_query == "is:starred"
            assert config.max_search_results == 75
            assert config.enable_search_validation is True  # Default
    
    def test_search_settings_validation_with_all_providers(self):
        """Test search settings validation works with both AI providers."""
        # Test with OpenAI provider
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "AI_PROVIDER": "openai",
            "DEFAULT_SEARCH_QUERY": "from:work@company.com"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.default_search_query == "from:work@company.com"
        
        # Test with Claude provider
        env_vars = {
            "CLAUDE_API_KEY": "test-key",
            "AI_PROVIDER": "claude",
            "DEFAULT_SEARCH_QUERY": "has:attachment"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.default_search_query == "has:attachment"
    
    def test_search_settings_backward_compatibility(self):
        """Test that existing functionality still works with new search settings."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "AI_PROVIDER": "openai",
            "MAX_EMAILS_PER_RUN": "10",
            "OUTPUT_DIRECTORY": "test_output"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            # Existing settings should still work
            assert config.ai_provider == "openai"
            assert config.max_emails_per_run == 10
            assert config.output_directory == "test_output"
            
            # New search settings should have defaults
            assert config.search_configs_file == "search_configs.json"
            assert config.default_search_query == "is:unread is:important"
            assert config.enable_search_validation is True
            assert config.max_search_results == 100
    
    def test_config_methods_with_search_settings(self):
        """Test that existing Config methods still work with search settings."""
        env_vars = {
            "OPENAI_API_KEY": "test-openai-key",
            "AI_PROVIDER": "openai"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            # Test existing methods
            assert config.get_api_key() == "test-openai-key"
            assert config.get_model_name() == "gpt-3.5-turbo"
            
            # Search settings should be available
            assert hasattr(config, 'search_configs_file')
            assert hasattr(config, 'default_search_query')
            assert hasattr(config, 'enable_search_validation')
            assert hasattr(config, 'max_search_results')


if __name__ == "__main__":
    pytest.main([__file__])