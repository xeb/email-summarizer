"""Unit tests for search configuration error handling and validation.

Tests comprehensive error scenarios, validation, and fallback behavior
for the search configuration system.
"""

import json
import os
import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock

from config.search_configs import (
    SearchConfig, SearchConfigManager, QueryValidator,
    SearchConfigError, ConfigurationNotFoundError,
    InvalidConfigurationError, QueryValidationError,
    CorruptedConfigFileError
)
from utils.error_handling import ErrorCategory, NonRetryableError


class TestSearchConfigErrorHandling:
    """Test cases for search configuration error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        self.manager = SearchConfigManager(self.config_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_corrupted_json_file_handling(self):
        """Test handling of corrupted JSON configuration file."""
        # Create a file with invalid JSON
        with open(self.config_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        # Creating a new manager should handle the corruption
        with pytest.raises(CorruptedConfigFileError) as exc_info:
            SearchConfigManager(self.config_file)
        
        error = exc_info.value
        assert self.config_file in str(error)
        assert error.backup_path is not None
        assert os.path.exists(error.backup_path)
        
        # Original file should be replaced with valid default
        assert os.path.exists(self.config_file)
        with open(self.config_file, 'r') as f:
            data = json.load(f)
        assert data["version"] == "1.0"
        assert data["configs"] == {}
    
    def test_missing_configs_section_handling(self):
        """Test handling of config file missing configs section."""
        # Create file with missing configs section
        invalid_data = {"version": "1.0"}
        with open(self.config_file, 'w') as f:
            json.dump(invalid_data, f)
        
        with pytest.raises(CorruptedConfigFileError):
            SearchConfigManager(self.config_file)
    
    def test_invalid_configs_section_type(self):
        """Test handling of config file with invalid configs section type."""
        # Create file with configs as array instead of object
        invalid_data = {"version": "1.0", "configs": []}
        with open(self.config_file, 'w') as f:
            json.dump(invalid_data, f)
        
        with pytest.raises(CorruptedConfigFileError):
            SearchConfigManager(self.config_file)
    
    def test_file_permission_error_handling(self):
        """Test handling of file permission errors."""
        # Create a read-only directory
        readonly_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)  # Read-only
        
        readonly_config_file = os.path.join(readonly_dir, "config.json")
        
        try:
            with pytest.raises(NonRetryableError) as exc_info:
                SearchConfigManager(readonly_config_file)
            
            error = exc_info.value
            assert error.category == ErrorCategory.FILE_SYSTEM
            assert "permission" in str(error).lower()
        finally:
            # Clean up - restore permissions
            os.chmod(readonly_dir, 0o755)
    
    def test_save_config_with_invalid_query(self):
        """Test saving configuration with invalid query raises appropriate error."""
        config = SearchConfig(
            name="invalid-query-test",
            query="invalid_operator:value unsupported:test",
            description="Test config with invalid query",
            created_at=datetime.now()
        )
        
        with pytest.raises(QueryValidationError) as exc_info:
            self.manager.save_config(config)
        
        error = exc_info.value
        assert error.query == config.query
        assert "invalid_operator:" in error.error_message
        assert len(error.suggestions) > 0
        assert error.category == ErrorCategory.VALIDATION
    
    def test_save_config_duplicate_name(self):
        """Test saving configuration with duplicate name raises appropriate error."""
        config1 = SearchConfig(
            name="duplicate-test",
            query="is:unread",
            description="First config",
            created_at=datetime.now()
        )
        
        config2 = SearchConfig(
            name="duplicate-test",
            query="is:important",
            description="Second config",
            created_at=datetime.now()
        )
        
        # Save first config
        self.manager.save_config(config1)
        
        # Attempt to save duplicate should raise error
        with pytest.raises(InvalidConfigurationError) as exc_info:
            self.manager.save_config(config2)
        
        error = exc_info.value
        assert error.config_name == "duplicate-test"
        assert "already exists" in str(error)
        assert len(error.suggestions) > 0
        assert error.category == ErrorCategory.VALIDATION
    
    def test_load_config_not_found_with_raise(self):
        """Test loading non-existent configuration with raise option."""
        # Create some configs for better error message
        config1 = SearchConfig(
            name="existing-config",
            query="is:unread",
            description="Existing config",
            created_at=datetime.now()
        )
        self.manager.save_config(config1)
        
        with pytest.raises(ConfigurationNotFoundError) as exc_info:
            self.manager.load_config_or_raise("non-existent")
        
        error = exc_info.value
        assert error.config_name == "non-existent"
        assert "existing-config" in error.available_configs
        assert "Available configurations" in str(error)
        assert error.category == ErrorCategory.VALIDATION
    
    def test_load_config_not_found_empty_list(self):
        """Test loading non-existent configuration when no configs exist."""
        with pytest.raises(ConfigurationNotFoundError) as exc_info:
            self.manager.load_config_or_raise("non-existent")
        
        error = exc_info.value
        assert error.config_name == "non-existent"
        assert len(error.available_configs) == 0
        assert "No saved configurations exist" in str(error)
    
    def test_load_config_invalid_data(self):
        """Test loading configuration with invalid data."""
        # Manually create config with invalid data
        invalid_config_data = {
            "version": "1.0",
            "configs": {
                "invalid-config": {
                    "name": "invalid-config",
                    "query": "is:unread",
                    # Missing required fields like description, created_at
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(invalid_config_data, f)
        
        # Create new manager to load the invalid data
        manager = SearchConfigManager(self.config_file)
        
        with pytest.raises(InvalidConfigurationError) as exc_info:
            manager.load_config_or_raise("invalid-config")
        
        error = exc_info.value
        assert error.config_name == "invalid-config"
        assert "invalid data" in str(error)
        assert len(error.suggestions) > 0
    
    def test_list_configs_with_corrupted_entries(self):
        """Test listing configurations when some entries are corrupted."""
        # Create mix of valid and invalid configs
        mixed_config_data = {
            "version": "1.0",
            "configs": {
                "valid-config": {
                    "name": "valid-config",
                    "query": "is:unread",
                    "description": "Valid config",
                    "created_at": "2024-01-15T10:00:00",
                    "usage_count": 0
                },
                "invalid-config": {
                    "name": "invalid-config",
                    "query": "is:important",
                    # Missing required fields
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(mixed_config_data, f)
        
        manager = SearchConfigManager(self.config_file)
        configs = manager.list_configs()
        
        # Should only return valid configs, skip invalid ones
        assert len(configs) == 1
        assert configs[0].name == "valid-config"
    
    def test_update_config_not_found(self):
        """Test updating non-existent configuration."""
        config = SearchConfig(
            name="non-existent",
            query="is:unread",
            description="Test",
            created_at=datetime.now()
        )
        
        result = self.manager.update_config("non-existent", config)
        assert result is False
    
    def test_update_config_invalid_query(self):
        """Test updating configuration with invalid query."""
        # Save original config
        original_config = SearchConfig(
            name="update-test",
            query="is:unread",
            description="Original",
            created_at=datetime.now()
        )
        self.manager.save_config(original_config)
        
        # Try to update with invalid query
        invalid_config = SearchConfig(
            name="update-test",
            query="invalid_operator:value",
            description="Invalid update",
            created_at=datetime.now()
        )
        
        with pytest.raises(QueryValidationError):
            self.manager.update_config("update-test", invalid_config)
    
    def test_delete_config_not_found(self):
        """Test deleting non-existent configuration."""
        result = self.manager.delete_config("non-existent")
        assert result is False
    
    def test_update_usage_stats_not_found(self):
        """Test updating usage stats for non-existent configuration."""
        result = self.manager.update_usage_stats("non-existent")
        assert result is False
    
    def test_get_config_stats_with_error(self):
        """Test getting configuration stats when errors occur."""
        # Mock list_configs to raise an exception
        with patch.object(self.manager, 'list_configs', side_effect=Exception("Test error")):
            stats = self.manager.get_config_stats()
            assert "error" in stats
            assert "Test error" in stats["error"]
    
    def test_migrate_config_file_backup_failure(self):
        """Test migration when backup creation fails."""
        # Create invalid config file
        with open(self.config_file, 'w') as f:
            f.write('invalid json')
        
        # Mock shutil.copy2 to fail
        with patch('shutil.copy2', side_effect=OSError("Permission denied")):
            with pytest.raises(CorruptedConfigFileError):
                SearchConfigManager(self.config_file)
        
        # Should still create default config despite backup failure
        assert os.path.exists(self.config_file)
        with open(self.config_file, 'r') as f:
            data = json.load(f)
        assert data["version"] == "1.0"
    
    def test_save_config_file_permission_error(self):
        """Test saving configuration when file write fails."""
        config = SearchConfig(
            name="test-config",
            query="is:unread",
            description="Test config",
            created_at=datetime.now()
        )
        
        # Mock open to raise permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(NonRetryableError) as exc_info:
                self.manager.save_config(config)
            
            error = exc_info.value
            assert error.category == ErrorCategory.FILE_SYSTEM
            assert "permission" in str(error).lower()


class TestQueryValidatorErrorHandling:
    """Test cases for query validator error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QueryValidator()
    
    def test_validate_query_exception_handling(self):
        """Test query validation when internal error occurs."""
        # Mock _extract_operators to raise an exception
        with patch.object(self.validator, '_extract_operators', side_effect=Exception("Internal error")):
            is_valid, error = self.validator.validate_query("is:unread")
            assert not is_valid
            assert "validation error" in error.lower()
    
    def test_suggest_corrections_empty_input(self):
        """Test suggestions for empty or None input."""
        suggestions = self.validator.suggest_corrections("")
        assert len(suggestions) > 0
        assert any("non-empty" in suggestion.lower() for suggestion in suggestions)
        
        suggestions = self.validator.suggest_corrections(None)
        assert len(suggestions) > 0
    
    def test_suggest_corrections_with_multiple_errors(self):
        """Test suggestions for query with multiple errors."""
        query = "form:test@example.com subjet:meeting attachement: unred:"
        suggestions = self.validator.suggest_corrections(query)
        
        # Should suggest corrections for multiple mistakes
        assert len(suggestions) >= 3
        assert any("from:" in suggestion for suggestion in suggestions)
        assert any("subject:" in suggestion for suggestion in suggestions)
        assert any("has:attachment" in suggestion for suggestion in suggestions)
    
    def test_find_closest_operator_no_match(self):
        """Test finding closest operator when no good match exists."""
        # Very different operator should return None
        closest = self.validator._find_closest_operator("xyz123:")
        assert closest is None
    
    def test_validate_date_format_edge_cases(self):
        """Test date format validation with edge cases."""
        # Invalid month/day combinations
        assert not self.validator._validate_date_format("2024-02-30")  # Feb 30th doesn't exist
        assert not self.validator._validate_date_format("2024-13-01")  # Month 13 doesn't exist
        assert not self.validator._validate_date_format("2024-00-01")  # Month 0 doesn't exist
        assert not self.validator._validate_date_format("2024-01-00")  # Day 0 doesn't exist
        
        # Valid edge cases
        assert self.validator._validate_date_format("2024-02-29")  # Leap year
        assert self.validator._validate_date_format("2024-12-31")  # Last day of year
    
    def test_validate_operator_with_quoted_values(self):
        """Test operator validation with quoted values."""
        # Should handle quoted values correctly
        error = self.validator._validate_operator('subject:', '"meeting notes"')
        assert error is None
        
        error = self.validator._validate_operator('from:', '"John Doe <john@example.com>"')
        assert error is None
    
    def test_check_for_warnings_edge_cases(self):
        """Test warning detection for edge cases."""
        # Very short query should not trigger warnings
        warnings = self.validator._check_for_warnings("is:unread")
        assert len(warnings) == 0
        
        # Query with exactly the warning threshold
        or_query = " OR ".join(["is:unread"] * 10)  # Exactly at threshold
        warnings = self.validator._check_for_warnings(or_query)
        assert len(warnings) == 0
        
        # Query just over the threshold
        or_query = " OR ".join(["is:unread"] * 11)  # Just over threshold
        warnings = self.validator._check_for_warnings(or_query)
        assert len(warnings) > 0


class TestSearchConfigManagerFallbackBehavior:
    """Test cases for fallback behavior in search configuration manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_file_creates_default_on_missing(self):
        """Test that loading missing config file creates default."""
        # File doesn't exist initially
        assert not os.path.exists(self.config_file)
        
        manager = SearchConfigManager(self.config_file)
        
        # Should create default file
        assert os.path.exists(self.config_file)
        with open(self.config_file, 'r') as f:
            data = json.load(f)
        assert data["version"] == "1.0"
        assert data["configs"] == {}
    
    def test_list_configs_handles_partial_corruption(self):
        """Test that list_configs handles partially corrupted data gracefully."""
        # Create config with mix of valid and invalid entries
        mixed_data = {
            "version": "1.0",
            "configs": {
                "valid1": {
                    "name": "valid1",
                    "query": "is:unread",
                    "description": "Valid config 1",
                    "created_at": "2024-01-15T10:00:00",
                    "usage_count": 0
                },
                "invalid": {
                    "name": "invalid",
                    "query": "is:important"
                    # Missing required fields
                },
                "valid2": {
                    "name": "valid2",
                    "query": "has:attachment",
                    "description": "Valid config 2",
                    "created_at": "2024-01-16T10:00:00",
                    "usage_count": 5
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(mixed_data, f)
        
        manager = SearchConfigManager(self.config_file)
        configs = manager.list_configs()
        
        # Should return only valid configs
        assert len(configs) == 2
        config_names = [cfg.name for cfg in configs]
        assert "valid1" in config_names
        assert "valid2" in config_names
        assert "invalid" not in config_names
    
    def test_save_config_recovers_from_corruption(self):
        """Test that save_config can recover from corrupted file."""
        # Create corrupted file
        with open(self.config_file, 'w') as f:
            f.write('corrupted json content')
        
        # Manager creation should handle corruption
        with pytest.raises(CorruptedConfigFileError):
            manager = SearchConfigManager(self.config_file)
        
        # File should be recreated as default
        assert os.path.exists(self.config_file)
        
        # Create new manager with clean file
        manager = SearchConfigManager(self.config_file)
        
        # Should be able to save config normally
        config = SearchConfig(
            name="recovery-test",
            query="is:unread",
            description="Recovery test config",
            created_at=datetime.now()
        )
        
        result = manager.save_config(config)
        assert result is True
        
        # Verify config was saved
        loaded_config = manager.load_config("recovery-test")
        assert loaded_config is not None
        assert loaded_config.name == "recovery-test"
    
    def test_graceful_degradation_on_file_system_errors(self):
        """Test graceful degradation when file system operations fail."""
        # Create manager with valid file
        manager = SearchConfigManager(self.config_file)
        
        # Mock file operations to fail
        with patch('builtins.open', side_effect=OSError("Disk full")):
            # load_config should return None instead of crashing
            result = manager.load_config("any-config")
            assert result is None
            
            # list_configs should return empty list instead of crashing
            configs = manager.list_configs()
            assert configs == []
            
            # update_usage_stats should return False instead of crashing
            result = manager.update_usage_stats("any-config")
            assert result is False
    
    def test_migration_with_partial_failure(self):
        """Test migration behavior when some operations fail."""
        # Create v0.0 format file
        v0_data = {
            "configs": {
                "old-config": {
                    "name": "old-config",
                    "query": "is:unread",
                    "description": "Old config"
                    # Missing created_at, usage_count, last_used
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(v0_data, f)
        
        # Mock backup creation to fail
        with patch('shutil.copy2', side_effect=OSError("Permission denied")):
            result = SearchConfigManager(self.config_file).migrate_config_file(backup=True)
            # Should still succeed despite backup failure
            assert result is True
        
        # Verify migration completed
        with open(self.config_file, 'r') as f:
            data = json.load(f)
        assert data["version"] == "1.0"
        assert "old-config" in data["configs"]
        assert data["configs"]["old-config"]["usage_count"] == 0


class TestErrorMessageGeneration:
    """Test cases for user-friendly error message generation."""
    
    def test_configuration_not_found_error_message(self):
        """Test ConfigurationNotFoundError message generation."""
        # With available configs
        error = ConfigurationNotFoundError("missing-config", ["config1", "config2"])
        message = str(error)
        assert "missing-config" in message
        assert "config1, config2" in message
        assert "Available configurations" in message
        
        # Without available configs
        error = ConfigurationNotFoundError("missing-config", [])
        message = str(error)
        assert "missing-config" in message
        assert "No saved configurations exist" in message
        assert "Use --save-config" in message
    
    def test_query_validation_error_message(self):
        """Test QueryValidationError message generation."""
        suggestions = ["Replace 'form:' with 'from:'", "Use 'is:unread' instead"]
        error = QueryValidationError("form:test@example.com", "Invalid operator", suggestions)
        
        message = str(error)
        assert "form:test@example.com" in message
        assert "Invalid operator" in message
        assert "Suggestions:" in message
        assert "Replace 'form:' with 'from:'" in message
    
    def test_corrupted_config_file_error_message(self):
        """Test CorruptedConfigFileError message generation."""
        original_error = json.JSONDecodeError("Invalid JSON", "test", 0)
        backup_path = "/tmp/backup.json"
        
        error = CorruptedConfigFileError("/path/to/config.json", original_error, backup_path)
        message = str(error)
        
        assert "/path/to/config.json" in message
        assert "corrupted" in message
        assert backup_path in message
        assert "backup has been created" in message
        assert "recreated with default settings" in message
    
    def test_invalid_configuration_error_with_suggestions(self):
        """Test InvalidConfigurationError with suggestions."""
        suggestions = ["Delete and recreate", "Check file format"]
        error = InvalidConfigurationError("Config data is invalid", "test-config", suggestions)
        
        message = str(error)
        assert "Config data is invalid" in message
        assert error.config_name == "test-config"
        assert len(error.suggestions) == 2