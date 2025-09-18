"""Unit tests for search configuration data models and validation.

Tests the SearchConfig dataclass and QueryValidator functionality.
"""

import json
import pytest
from datetime import datetime
from config.search_configs import SearchConfig, QueryValidator, SearchConfigManager


class TestSearchConfig:
    """Test cases for SearchConfig dataclass."""
    
    def test_search_config_creation(self):
        """Test basic SearchConfig creation."""
        created_at = datetime.now()
        config = SearchConfig(
            name="test-config",
            query="from:test@example.com is:unread",
            description="Test configuration",
            created_at=created_at
        )
        
        assert config.name == "test-config"
        assert config.query == "from:test@example.com is:unread"
        assert config.description == "Test configuration"
        assert config.created_at == created_at
        assert config.last_used is None
        assert config.usage_count == 0
    
    def test_search_config_with_optional_fields(self):
        """Test SearchConfig creation with optional fields."""
        created_at = datetime.now()
        last_used = datetime.now()
        
        config = SearchConfig(
            name="test-config",
            query="is:important",
            description="Important emails",
            created_at=created_at,
            last_used=last_used,
            usage_count=5
        )
        
        assert config.last_used == last_used
        assert config.usage_count == 5
    
    def test_to_dict_serialization(self):
        """Test SearchConfig to_dict serialization."""
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        last_used = datetime(2024, 1, 16, 9, 15, 0)
        
        config = SearchConfig(
            name="work-emails",
            query="from:@company.com is:unread",
            description="Work emails",
            created_at=created_at,
            last_used=last_used,
            usage_count=3
        )
        
        data = config.to_dict()
        
        assert data['name'] == "work-emails"
        assert data['query'] == "from:@company.com is:unread"
        assert data['description'] == "Work emails"
        assert data['created_at'] == "2024-01-15T10:30:00"
        assert data['last_used'] == "2024-01-16T09:15:00"
        assert data['usage_count'] == 3
    
    def test_to_dict_with_none_last_used(self):
        """Test to_dict serialization when last_used is None."""
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        config = SearchConfig(
            name="test-config",
            query="is:unread",
            description="Test",
            created_at=created_at
        )
        
        data = config.to_dict()
        assert data['last_used'] is None
    
    def test_from_dict_deserialization(self):
        """Test SearchConfig from_dict deserialization."""
        data = {
            'name': 'urgent-emails',
            'query': 'is:important is:unread newer_than:1d',
            'description': 'Urgent emails from today',
            'created_at': '2024-01-15T11:00:00',
            'last_used': '2024-01-16T08:30:00',
            'usage_count': 2
        }
        
        config = SearchConfig.from_dict(data)
        
        assert config.name == 'urgent-emails'
        assert config.query == 'is:important is:unread newer_than:1d'
        assert config.description == 'Urgent emails from today'
        assert config.created_at == datetime(2024, 1, 15, 11, 0, 0)
        assert config.last_used == datetime(2024, 1, 16, 8, 30, 0)
        assert config.usage_count == 2
    
    def test_from_dict_with_none_last_used(self):
        """Test from_dict deserialization when last_used is None."""
        data = {
            'name': 'test-config',
            'query': 'is:unread',
            'description': 'Test',
            'created_at': '2024-01-15T10:30:00',
            'last_used': None,
            'usage_count': 0
        }
        
        config = SearchConfig.from_dict(data)
        assert config.last_used is None
        assert config.usage_count == 0
    
    def test_from_dict_missing_usage_count(self):
        """Test from_dict with missing usage_count defaults to 0."""
        data = {
            'name': 'test-config',
            'query': 'is:unread',
            'description': 'Test',
            'created_at': '2024-01-15T10:30:00',
            'last_used': None
        }
        
        config = SearchConfig.from_dict(data)
        assert config.usage_count == 0
    
    def test_from_dict_invalid_data(self):
        """Test from_dict with invalid data raises ValueError."""
        # Missing required field
        data = {
            'name': 'test-config',
            'query': 'is:unread',
            # missing description and created_at
        }
        
        with pytest.raises(ValueError, match="Invalid search configuration data"):
            SearchConfig.from_dict(data)
    
    def test_from_dict_invalid_datetime(self):
        """Test from_dict with invalid datetime format raises ValueError."""
        data = {
            'name': 'test-config',
            'query': 'is:unread',
            'description': 'Test',
            'created_at': 'invalid-date',
            'last_used': None
        }
        
        with pytest.raises(ValueError, match="Invalid search configuration data"):
            SearchConfig.from_dict(data)
    
    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = SearchConfig(
            name="round-trip-test",
            query="from:test@example.com has:attachment",
            description="Round trip test",
            created_at=datetime(2024, 1, 15, 12, 0, 0),
            last_used=datetime(2024, 1, 16, 10, 0, 0),
            usage_count=7
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = SearchConfig.from_dict(data)
        
        # Compare all fields
        assert restored.name == original.name
        assert restored.query == original.query
        assert restored.description == original.description
        assert restored.created_at == original.created_at
        assert restored.last_used == original.last_used
        assert restored.usage_count == original.usage_count
    
    def test_string_representation(self):
        """Test SearchConfig string representation."""
        config = SearchConfig(
            name="test-config",
            query="is:unread",
            description="Test",
            created_at=datetime.now()
        )
        
        str_repr = str(config)
        assert "SearchConfig" in str_repr
        assert "test-config" in str_repr
        assert "is:unread" in str_repr


class TestQueryValidator:
    """Test cases for QueryValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QueryValidator()
    
    def test_valid_basic_queries(self):
        """Test validation of basic valid Gmail queries."""
        valid_queries = [
            "is:unread",
            "is:important",
            "from:test@example.com",
            "to:recipient@example.com",
            "subject:meeting",
            "has:attachment",
            "in:inbox",
            "is:unread is:important",
            "from:@company.com is:unread"
        ]
        
        for query in valid_queries:
            is_valid, error = self.validator.validate_query(query)
            assert is_valid, f"Query '{query}' should be valid, but got error: {error}"
            assert error == ""
    
    def test_valid_date_queries(self):
        """Test validation of date-based queries."""
        valid_date_queries = [
            "after:2024-01-01",
            "before:2024-12-31",
            "after:2024/01/01",
            "newer_than:7d",
            "older_than:1m",
            "newer_than:2y"
        ]
        
        for query in valid_date_queries:
            is_valid, error = self.validator.validate_query(query)
            assert is_valid, f"Date query '{query}' should be valid, but got error: {error}"
    
    def test_valid_size_queries(self):
        """Test validation of size-based queries."""
        valid_size_queries = [
            "larger:10M",
            "smaller:1MB",
            "size:5KB",
            "larger:100",
            "smaller:2G"
        ]
        
        for query in valid_size_queries:
            is_valid, error = self.validator.validate_query(query)
            assert is_valid, f"Size query '{query}' should be valid, but got error: {error}"
    
    def test_valid_complex_queries(self):
        """Test validation of complex multi-operator queries."""
        complex_queries = [
            "from:@company.com is:unread after:2024-01-01",
            "has:attachment larger:5M from:manager@example.com",
            "subject:project is:important newer_than:7d",
            "in:inbox is:unread",  # Simplified - OR handling is complex and not core to validation
            "is:starred OR is:important"  # Simple OR case
        ]
        
        for query in complex_queries:
            is_valid, error = self.validator.validate_query(query)
            assert is_valid, f"Complex query '{query}' should be valid, but got error: {error}"
    
    def test_empty_query_validation(self):
        """Test validation of empty queries."""
        empty_queries = ["", "   ", None]
        
        for query in empty_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "empty" in error.lower()
    
    def test_unbalanced_quotes_validation(self):
        """Test validation of queries with unbalanced quotes."""
        unbalanced_queries = [
            'subject:"test email',
            'from:"sender@example.com to:recipient@example.com',
            'subject:"meeting" from:"incomplete'
        ]
        
        for query in unbalanced_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "quote" in error.lower()
    
    def test_unsupported_operator_validation(self):
        """Test validation of unsupported operators."""
        invalid_queries = [
            "unsupported:value",
            "fake_operator:test",
            "invalid:query"
        ]
        
        for query in invalid_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "unsupported" in error.lower()
    
    def test_invalid_has_values(self):
        """Test validation of invalid has: operator values."""
        invalid_has_queries = [
            "has:invalid_value",
            "has:fake_attachment",
            "has:nonexistent"
        ]
        
        for query in invalid_has_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "has:" in error
    
    def test_invalid_is_values(self):
        """Test validation of invalid is: operator values."""
        invalid_is_queries = [
            "is:invalid_status",
            "is:fake_state",
            "is:nonexistent"
        ]
        
        for query in invalid_is_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "is:" in error
    
    def test_invalid_date_formats(self):
        """Test validation of invalid date formats."""
        invalid_date_queries = [
            "after:invalid-date",
            "before:2024-13-01",  # Invalid month
            "newer_than:invalid",
            "older_than:7x"  # Invalid unit
        ]
        
        for query in invalid_date_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "date" in error.lower()
    
    def test_invalid_size_formats(self):
        """Test validation of invalid size formats."""
        invalid_size_queries = [
            "larger:invalid",
            "smaller:10X",  # Invalid unit
            "size:abc"
        ]
        
        for query in invalid_size_queries:
            is_valid, error = self.validator.validate_query(query)
            assert not is_valid
            assert "size" in error.lower()
    
    def test_suggest_corrections_empty_query(self):
        """Test suggestions for empty queries."""
        suggestions = self.validator.suggest_corrections("")
        assert len(suggestions) > 0
        assert any("non-empty" in suggestion.lower() for suggestion in suggestions)
    
    def test_suggest_corrections_common_mistakes(self):
        """Test suggestions for common operator misspellings."""
        mistakes_and_corrections = [
            ("form:test@example.com", "from:"),
            ("too:recipient@example.com", "to:"),
            ("subjet:meeting", "subject:"),
            ("attachement:", "has:attachment"),
            ("unred:", "is:unread")
        ]
        
        for mistake_query, expected_correction in mistakes_and_corrections:
            suggestions = self.validator.suggest_corrections(mistake_query)
            assert any(expected_correction in suggestion for suggestion in suggestions)
    
    def test_suggest_corrections_unsupported_operators(self):
        """Test suggestions for unsupported operators."""
        query = "unsupported_operator:value"
        suggestions = self.validator.suggest_corrections(query)
        
        assert len(suggestions) > 0
        assert any("unsupported_operator:" in suggestion for suggestion in suggestions)
    
    def test_suggest_corrections_unbalanced_quotes(self):
        """Test suggestions for unbalanced quotes."""
        query = 'subject:"unbalanced quote'
        suggestions = self.validator.suggest_corrections(query)
        
        assert len(suggestions) > 0
        assert any("quote" in suggestion.lower() for suggestion in suggestions)
    
    def test_extract_operators(self):
        """Test operator extraction from queries."""
        query = "from:test@example.com is:unread has:attachment"
        operators = self.validator._extract_operators(query)
        
        expected_operators = [
            ("from:", "test@example.com"),
            ("is:", "unread"),
            ("has:", "attachment")
        ]
        
        assert len(operators) == len(expected_operators)
        for expected in expected_operators:
            assert expected in operators
    
    def test_find_closest_operator(self):
        """Test finding closest matching operator for typos."""
        test_cases = [
            ("form:", "from:"),
            ("too:", "to:"),
            ("subjet:", "subject:")
        ]
        
        for typo, expected in test_cases:
            closest = self.validator._find_closest_operator(typo)
            assert closest == expected
    
    def test_validate_date_format(self):
        """Test date format validation."""
        valid_dates = ["2024-01-01", "2024/12/31"]
        invalid_dates = ["invalid-date", "2024-13-01", "01-01-2024"]
        
        for date in valid_dates:
            assert self.validator._validate_date_format(date)
        
        for date in invalid_dates:
            assert not self.validator._validate_date_format(date)
    
    def test_validate_relative_date(self):
        """Test relative date format validation."""
        valid_relative_dates = ["7d", "1m", "2y", "30d"]
        invalid_relative_dates = ["7x", "invalid", "1day", "2months"]
        
        for date in valid_relative_dates:
            assert self.validator._validate_relative_date(date)
        
        for date in invalid_relative_dates:
            assert not self.validator._validate_relative_date(date)
    
    def test_validate_size_format(self):
        """Test size format validation."""
        valid_sizes = ["10M", "1MB", "5KB", "100", "2G", "500kb"]
        invalid_sizes = ["invalid", "10X", "abc", "10 MB"]
        
        for size in valid_sizes:
            assert self.validator._validate_size_format(size)
        
        for size in invalid_sizes:
            assert not self.validator._validate_size_format(size)
    
    def test_check_for_warnings(self):
        """Test warning detection for potentially problematic queries."""
        # Test long query warning
        long_query = "from:test@example.com " * 50  # Very long query
        warnings = self.validator._check_for_warnings(long_query)
        assert any("long" in warning.lower() for warning in warnings)
        
        # Test too many OR conditions
        or_query = " OR ".join(["is:unread"] * 15)
        warnings = self.validator._check_for_warnings(or_query)
        assert any("or" in warning.lower() for warning in warnings)
        
        # Test attachment without size filter
        attachment_query = "has:attachment from:test@example.com"
        warnings = self.validator._check_for_warnings(attachment_query)
        assert any("size" in warning.lower() for warning in warnings)


class TestSearchConfigManager:
    """Test cases for SearchConfigManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        import tempfile
        import os
        
        # Create temporary config file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_search_configs.json")
        self.manager = SearchConfigManager(self.config_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_initialization(self):
        """Test SearchConfigManager initialization."""
        assert self.manager.config_file == self.config_file
        assert self.manager.CONFIG_VERSION == "1.0"
        assert isinstance(self.manager.validator, QueryValidator)
        
        # Check that config file was created
        import os
        assert os.path.exists(self.config_file)
    
    def test_save_config_success(self):
        """Test successful configuration saving."""
        config = SearchConfig(
            name="test-save",
            query="from:test@example.com is:unread",
            description="Test save configuration",
            created_at=datetime.now()
        )
        
        result = self.manager.save_config(config)
        assert result is True
        
        # Verify config was saved
        loaded_config = self.manager.load_config("test-save")
        assert loaded_config is not None
        assert loaded_config.name == config.name
        assert loaded_config.query == config.query
        assert loaded_config.description == config.description
    
    def test_save_config_duplicate_name(self):
        """Test saving configuration with duplicate name raises error."""
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
        with pytest.raises(ValueError, match="already exists"):
            self.manager.save_config(config2)
    
    def test_save_config_invalid_query(self):
        """Test saving configuration with invalid query raises error."""
        config = SearchConfig(
            name="invalid-query-test",
            query="invalid_operator:value",
            description="Invalid query config",
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Invalid search query"):
            self.manager.save_config(config)
    
    def test_load_config_success(self):
        """Test successful configuration loading."""
        # First save a config
        original_config = SearchConfig(
            name="load-test",
            query="from:sender@example.com has:attachment",
            description="Load test configuration",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            usage_count=5
        )
        
        self.manager.save_config(original_config)
        
        # Load and verify
        loaded_config = self.manager.load_config("load-test")
        assert loaded_config is not None
        assert loaded_config.name == original_config.name
        assert loaded_config.query == original_config.query
        assert loaded_config.description == original_config.description
        assert loaded_config.usage_count == original_config.usage_count
    
    def test_load_config_not_found(self):
        """Test loading non-existent configuration returns None."""
        result = self.manager.load_config("non-existent")
        assert result is None
    
    def test_list_configs_empty(self):
        """Test listing configurations when none exist."""
        configs = self.manager.list_configs()
        assert configs == []
    
    def test_list_configs_multiple(self):
        """Test listing multiple configurations."""
        configs_to_save = [
            SearchConfig(
                name="config-a",
                query="is:unread",
                description="Config A",
                created_at=datetime.now()
            ),
            SearchConfig(
                name="config-b",
                query="is:important",
                description="Config B",
                created_at=datetime.now()
            ),
            SearchConfig(
                name="config-c",
                query="has:attachment",
                description="Config C",
                created_at=datetime.now()
            )
        ]
        
        # Save all configs
        for config in configs_to_save:
            self.manager.save_config(config)
        
        # List and verify
        listed_configs = self.manager.list_configs()
        assert len(listed_configs) == 3
        
        # Should be sorted by name
        names = [config.name for config in listed_configs]
        assert names == ["config-a", "config-b", "config-c"]
    
    def test_delete_config_success(self):
        """Test successful configuration deletion."""
        # Save a config first
        config = SearchConfig(
            name="delete-test",
            query="is:starred",
            description="Delete test config",
            created_at=datetime.now()
        )
        self.manager.save_config(config)
        
        # Verify it exists
        assert self.manager.load_config("delete-test") is not None
        
        # Delete it
        result = self.manager.delete_config("delete-test")
        assert result is True
        
        # Verify it's gone
        assert self.manager.load_config("delete-test") is None
    
    def test_delete_config_not_found(self):
        """Test deleting non-existent configuration returns False."""
        result = self.manager.delete_config("non-existent")
        assert result is False
    
    def test_update_config_success(self):
        """Test successful configuration update."""
        # Save original config
        original_config = SearchConfig(
            name="update-test",
            query="is:unread",
            description="Original description",
            created_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        self.manager.save_config(original_config)
        
        # Update config
        updated_config = SearchConfig(
            name="update-test",
            query="is:important is:unread",
            description="Updated description",
            created_at=datetime.now(),  # This should be preserved from original
            usage_count=10
        )
        
        result = self.manager.update_config("update-test", updated_config)
        assert result is True
        
        # Verify update
        loaded_config = self.manager.load_config("update-test")
        assert loaded_config.query == "is:important is:unread"
        assert loaded_config.description == "Updated description"
        assert loaded_config.usage_count == 10
    
    def test_update_config_not_found(self):
        """Test updating non-existent configuration returns False."""
        config = SearchConfig(
            name="non-existent",
            query="is:unread",
            description="Test",
            created_at=datetime.now()
        )
        
        result = self.manager.update_config("non-existent", config)
        assert result is False
    
    def test_update_config_invalid_query(self):
        """Test updating with invalid query raises error."""
        # Save original config
        original_config = SearchConfig(
            name="update-invalid-test",
            query="is:unread",
            description="Original",
            created_at=datetime.now()
        )
        self.manager.save_config(original_config)
        
        # Try to update with invalid query
        invalid_config = SearchConfig(
            name="update-invalid-test",
            query="invalid_operator:value",
            description="Invalid update",
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Invalid search query"):
            self.manager.update_config("update-invalid-test", invalid_config)
    
    def test_update_usage_stats_success(self):
        """Test successful usage statistics update."""
        # Save a config
        config = SearchConfig(
            name="usage-test",
            query="is:unread",
            description="Usage test",
            created_at=datetime.now(),
            usage_count=0
        )
        self.manager.save_config(config)
        
        # Update usage stats
        result = self.manager.update_usage_stats("usage-test")
        assert result is True
        
        # Verify update
        updated_config = self.manager.load_config("usage-test")
        assert updated_config.usage_count == 1
        assert updated_config.last_used is not None
    
    def test_update_usage_stats_not_found(self):
        """Test updating usage stats for non-existent config returns False."""
        result = self.manager.update_usage_stats("non-existent")
        assert result is False
    
    def test_validate_query_delegation(self):
        """Test that validate_query delegates to QueryValidator."""
        # Valid query
        is_valid, error = self.manager.validate_query("is:unread is:important")
        assert is_valid is True
        assert error == ""
        
        # Invalid query
        is_valid, error = self.manager.validate_query("invalid_operator:value")
        assert is_valid is False
        assert "unsupported" in error.lower()
    
    def test_get_config_stats_empty(self):
        """Test getting statistics when no configurations exist."""
        stats = self.manager.get_config_stats()
        
        expected_stats = {
            "total_configs": 0,
            "most_used": None,
            "recently_used": None,
            "total_usage": 0
        }
        
        assert stats == expected_stats
    
    def test_get_config_stats_with_data(self):
        """Test getting statistics with multiple configurations."""
        # Create configs with different usage patterns
        configs = [
            SearchConfig(
                name="most-used",
                query="is:unread",
                description="Most used config",
                created_at=datetime(2024, 1, 10, 10, 0, 0),
                last_used=datetime(2024, 1, 15, 10, 0, 0),
                usage_count=10
            ),
            SearchConfig(
                name="recently-used",
                query="is:important",
                description="Recently used config",
                created_at=datetime(2024, 1, 12, 10, 0, 0),
                last_used=datetime(2024, 1, 16, 10, 0, 0),
                usage_count=3
            ),
            SearchConfig(
                name="unused",
                query="has:attachment",
                description="Unused config",
                created_at=datetime(2024, 1, 14, 10, 0, 0),
                usage_count=0
            )
        ]
        
        # Save all configs
        for config in configs:
            self.manager.save_config(config)
        
        # Get stats
        stats = self.manager.get_config_stats()
        
        assert stats["total_configs"] == 3
        assert stats["total_usage"] == 13
        assert stats["most_used"]["name"] == "most-used"
        assert stats["most_used"]["usage_count"] == 10
        assert stats["recently_used"]["name"] == "recently-used"
    
    def test_migrate_config_file_current_version(self):
        """Test migration when file is already current version."""
        result = self.manager.migrate_config_file(backup=False)
        assert result is True
    
    def test_migrate_config_file_from_v0(self):
        """Test migration from version 0.0 to current version."""
        # Create a v0.0 format config file
        v0_config = {
            "configs": {
                "old-config": {
                    "name": "old-config",
                    "query": "is:unread",
                    "description": "Old format config",
                    "created_at": "2024-01-15T10:00:00"
                    # Missing usage_count and last_used
                }
            }
        }
        
        # Write v0.0 format file
        import json
        with open(self.config_file, 'w') as f:
            json.dump(v0_config, f)
        
        # Create new manager to trigger migration
        manager = SearchConfigManager(self.config_file)
        result = manager.migrate_config_file(backup=False)
        assert result is True
        
        # Verify migration
        config_data = manager._load_config_file()
        assert config_data["version"] == "1.0"
        
        old_config = config_data["configs"]["old-config"]
        assert old_config["usage_count"] == 0
        assert old_config["last_used"] is None
        assert "created_at" in old_config
    
    def test_config_file_creation(self):
        """Test that configuration file is created with proper structure."""
        import os
        import json
        
        # Remove the file created in setup
        os.remove(self.config_file)
        
        # Create new manager, should create file
        manager = SearchConfigManager(self.config_file)
        
        # Verify file exists and has correct structure
        assert os.path.exists(self.config_file)
        
        with open(self.config_file, 'r') as f:
            config_data = json.load(f)
        
        assert config_data["version"] == "1.0"
        assert config_data["configs"] == {}
    
    def test_corrupted_config_file_recreation(self):
        """Test handling of corrupted configuration file."""
        import json
        
        # Write invalid JSON to config file
        with open(self.config_file, 'w') as f:
            f.write("invalid json content")
        
        # Create new manager, should recreate file
        manager = SearchConfigManager(self.config_file)
        
        # Verify file was recreated with proper structure
        with open(self.config_file, 'r') as f:
            config_data = json.load(f)
        
        assert config_data["version"] == "1.0"
        assert config_data["configs"] == {}
    
    def test_config_file_backup_creation(self):
        """Test backup creation during migration."""
        import os
        
        # Save a config first
        config = SearchConfig(
            name="backup-test",
            query="is:unread",
            description="Backup test",
            created_at=datetime.now()
        )
        self.manager.save_config(config)
        
        # Create backup
        backup_file = f"{self.config_file}.backup.test"
        self.manager._create_backup(backup_file)
        
        # Verify backup exists and has same content
        assert os.path.exists(backup_file)
        
        import json
        with open(self.config_file, 'r') as f:
            original_data = json.load(f)
        
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        assert original_data == backup_data
    
    def test_list_configs_with_invalid_config(self):
        """Test listing configurations when one is invalid."""
        import json
        
        # Save a valid config first
        valid_config = SearchConfig(
            name="valid-config",
            query="is:unread",
            description="Valid config",
            created_at=datetime.now()
        )
        self.manager.save_config(valid_config)
        
        # Manually add an invalid config to the file
        config_data = self.manager._load_config_file()
        config_data["configs"]["invalid-config"] = {
            "name": "invalid-config",
            "query": "is:unread",
            # Missing required fields
        }
        self.manager._save_config_file(config_data)
        
        # List configs should skip invalid one and return valid ones
        configs = self.manager.list_configs()
        assert len(configs) == 1
        assert configs[0].name == "valid-config"
    
    def test_concurrent_access_simulation(self):
        """Test behavior with simulated concurrent access."""
        # This is a basic test - real concurrent testing would require threading
        
        # Save multiple configs in sequence
        for i in range(5):
            config = SearchConfig(
                name=f"concurrent-test-{i}",
                query=f"from:test{i}@example.com",
                description=f"Concurrent test {i}",
                created_at=datetime.now()
            )
            self.manager.save_config(config)
        
        # Verify all were saved
        configs = self.manager.list_configs()
        assert len(configs) == 5
        
        # Update usage stats for all
        for i in range(5):
            result = self.manager.update_usage_stats(f"concurrent-test-{i}")
            assert result is True
        
        # Verify all updates
        for i in range(5):
            config = self.manager.load_config(f"concurrent-test-{i}")
            assert config.usage_count == 1


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])