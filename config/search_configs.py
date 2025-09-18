"""Search configuration data models and validation for Gmail Email Summarizer.

This module provides data models for storing and managing custom Gmail search
configurations, along with validation for Gmail search query syntax.
"""

import json
import re
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
from utils.error_handling import (
    NonRetryableError, ErrorCategory, create_user_friendly_message,
    handle_file_system_error
)


class SearchConfigError(Exception):
    """Base exception for search configuration errors."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.VALIDATION):
        super().__init__(message)
        self.category = category


class ConfigurationNotFoundError(SearchConfigError):
    """Raised when a requested configuration is not found."""
    def __init__(self, config_name: str, available_configs: List[str] = None):
        self.config_name = config_name
        self.available_configs = available_configs or []
        
        if self.available_configs:
            message = (
                f"Search configuration '{config_name}' not found. "
                f"Available configurations: {', '.join(self.available_configs)}"
            )
        else:
            message = (
                f"Search configuration '{config_name}' not found. "
                "No saved configurations exist. Use --save-config to create one."
            )
        
        super().__init__(message, ErrorCategory.VALIDATION)


class InvalidConfigurationError(SearchConfigError):
    """Raised when configuration data is invalid or corrupted."""
    def __init__(self, message: str, config_name: str = None, suggestions: List[str] = None):
        self.config_name = config_name
        self.suggestions = suggestions or []
        super().__init__(message, ErrorCategory.VALIDATION)


class QueryValidationError(SearchConfigError):
    """Raised when a Gmail search query fails validation."""
    def __init__(self, query: str, error_message: str, suggestions: List[str] = None):
        self.query = query
        self.error_message = error_message
        self.suggestions = suggestions or []
        
        message = f"Invalid Gmail search query '{query}': {error_message}"
        if self.suggestions:
            message += f"\nSuggestions: {'; '.join(self.suggestions)}"
        
        super().__init__(message, ErrorCategory.VALIDATION)


class CorruptedConfigFileError(SearchConfigError):
    """Raised when configuration file is corrupted or unreadable."""
    def __init__(self, file_path: str, original_error: Exception, backup_path: str = None):
        self.file_path = file_path
        self.original_error = original_error
        self.backup_path = backup_path
        
        message = f"Configuration file '{file_path}' is corrupted: {str(original_error)}"
        if backup_path:
            message += f"\nA backup has been created at '{backup_path}'"
        message += "\nThe file will be recreated with default settings."
        
        super().__init__(message, ErrorCategory.FILE_SYSTEM)


@dataclass
class SearchConfig:
    """Data model for a Gmail search configuration.
    
    Attributes:
        name: Unique identifier for the configuration
        query: Gmail search query string
        description: Human-readable description of the search
        created_at: When the configuration was created
        last_used: Last time this configuration was used (optional)
        usage_count: Number of times this configuration has been used
    """
    name: str
    query: str
    description: str
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SearchConfig to dictionary for JSON serialization.
        
        Returns:
            Dict containing all configuration data with datetime objects
            converted to ISO format strings.
        """
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        if self.last_used:
            data['last_used'] = self.last_used.isoformat()
        else:
            data['last_used'] = None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchConfig':
        """Create SearchConfig instance from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            SearchConfig instance
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Parse datetime fields
            created_at = datetime.fromisoformat(data['created_at'])
            last_used = None
            if data.get('last_used'):
                last_used = datetime.fromisoformat(data['last_used'])
            
            return cls(
                name=data['name'],
                query=data['query'],
                description=data['description'],
                created_at=created_at,
                last_used=last_used,
                usage_count=data.get('usage_count', 0)
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid search configuration data: {e}")
    
    def __str__(self) -> str:
        """String representation of the search configuration."""
        return f"SearchConfig(name='{self.name}', query='{self.query}')"


class QueryValidator:
    """Validator for Gmail search query syntax.
    
    Provides validation and suggestions for Gmail search operators and syntax.
    """
    
    # Supported Gmail search operators
    SUPPORTED_OPERATORS = [
        'from:', 'to:', 'cc:', 'bcc:', 'subject:', 'has:', 'is:', 'in:',
        'after:', 'before:', 'older_than:', 'newer_than:', 'size:',
        'larger:', 'smaller:', 'filename:', 'label:', 'category:',
        'deliveredto:', 'circle:', 'rfc822msgid:'
    ]
    
    # Common Gmail search values for validation
    VALID_HAS_VALUES = [
        'attachment', 'nouserlabels', 'userlabels', 'yellow-star',
        'blue-info', 'red-bang', 'orange-guillemet', 'red-star',
        'purple-star', 'green-star', 'yellow-bang'
    ]
    
    VALID_IS_VALUES = [
        'important', 'starred', 'unread', 'read', 'chat', 'muted',
        'snoozed', 'spam', 'trash'
    ]
    
    VALID_IN_VALUES = [
        'inbox', 'trash', 'spam', 'unread', 'starred', 'sent',
        'drafts', 'important', 'chats', 'all', 'anywhere'
    ]
    
    # Date format patterns
    DATE_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        r'\d{1,2}d',           # Nd (days)
        r'\d{1,2}m',           # Nm (months)
        r'\d{1,2}y',           # Ny (years)
    ]
    
    def __init__(self):
        """Initialize the query validator."""
        self.logger = logging.getLogger(__name__)
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate Gmail search query syntax.
        
        Args:
            query: Gmail search query string to validate
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        if not query or not query.strip():
            return False, "Search query cannot be empty"
        
        query = query.strip()
        
        try:
            # Check for basic syntax issues
            if not self._check_quote_balance(query):
                return False, "Unbalanced quotes in search query"
            
            # Validate individual operators
            validation_errors = []
            operators_found = self._extract_operators(query)
            
            for operator, value in operators_found:
                error = self._validate_operator(operator, value)
                if error:
                    validation_errors.append(error)
            
            if validation_errors:
                return False, "; ".join(validation_errors)
            
            # Check for potentially problematic patterns
            warnings = self._check_for_warnings(query)
            if warnings:
                self.logger.warning(f"Query validation warnings: {'; '.join(warnings)}")
            
            return True, ""
            
        except Exception as e:
            self.logger.error(f"Error validating query '{query}': {e}")
            return False, f"Query validation error: {str(e)}"
    
    def suggest_corrections(self, query: str) -> List[str]:
        """Suggest corrections for invalid Gmail search queries.
        
        Args:
            query: Invalid Gmail search query
            
        Returns:
            List of suggested corrections
        """
        suggestions = []
        
        if not query or not query.strip():
            suggestions.append("Provide a non-empty search query")
            return suggestions
        
        # Check for common operator misspellings
        common_mistakes = {
            'form:': 'from:',
            'too:': 'to:',
            'subjet:': 'subject:',
            'subjct:': 'subject:',
            'attachement:': 'has:attachment',
            'unred:': 'is:unread',
            'importnt:': 'is:important'
        }
        
        for mistake, correction in common_mistakes.items():
            if mistake in query.lower():
                suggestions.append(f"Replace '{mistake}' with '{correction}'")
        
        # Check for unsupported operators
        operators_found = self._extract_operators(query)
        for operator, _ in operators_found:
            if operator not in self.SUPPORTED_OPERATORS:
                closest_match = self._find_closest_operator(operator)
                if closest_match:
                    suggestions.append(f"Replace '{operator}' with '{closest_match}'")
                else:
                    suggestions.append(f"Remove unsupported operator '{operator}'")
        
        # Suggest quote fixes for unbalanced quotes
        if not self._check_quote_balance(query):
            suggestions.append("Balance quotes in your search query")
        
        return suggestions
    
    def _check_quote_balance(self, query: str) -> bool:
        """Check if quotes are balanced in the query."""
        return query.count('"') % 2 == 0
    
    def _extract_operators(self, query: str) -> List[Tuple[str, str]]:
        """Extract operators and their values from the query.
        
        Returns:
            List of (operator, value) tuples
        """
        operators = []
        # Pattern to match operator:value pairs, handling quoted values and OR operators
        pattern = r'(\w+:)("(?:[^"\\]|\\.)*"|[^\s]+)(?=\s|$)'
        
        matches = re.finditer(pattern, query)
        for match in matches:
            operator = match.group(1)
            value = match.group(2).strip()
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            operators.append((operator, value))
        
        return operators
    
    def _validate_operator(self, operator: str, value: str) -> Optional[str]:
        """Validate a specific operator and its value.
        
        Returns:
            Error message if invalid, None if valid
        """
        if operator not in self.SUPPORTED_OPERATORS:
            return f"Unsupported operator: {operator}"
        
        # Validate specific operator values
        if operator == 'has:':
            if value not in self.VALID_HAS_VALUES:
                return f"Invalid value for has: operator: {value}"
        
        elif operator == 'is:':
            if value not in self.VALID_IS_VALUES:
                return f"Invalid value for is: operator: {value}"
        
        elif operator == 'in:':
            if value not in self.VALID_IN_VALUES:
                return f"Invalid value for in: operator: {value}"
        
        elif operator in ['after:', 'before:']:
            if not self._validate_date_format(value):
                return f"Invalid date format for {operator} operator: {value}"
        
        elif operator in ['older_than:', 'newer_than:']:
            if not self._validate_relative_date(value):
                return f"Invalid relative date format for {operator} operator: {value}"
        
        elif operator in ['size:', 'larger:', 'smaller:']:
            if not self._validate_size_format(value):
                return f"Invalid size format for {operator} operator: {value}"
        
        return None
    
    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format for after:/before: operators."""
        for pattern in self.DATE_PATTERNS[:2]:  # Only absolute date patterns
            if re.fullmatch(pattern, date_str):
                # Additional validation for YYYY-MM-DD format
                if '-' in date_str:
                    try:
                        year, month, day = map(int, date_str.split('-'))
                        if not (1 <= month <= 12 and 1 <= day <= 31):
                            return False
                        # Additional validation for impossible dates
                        if month == 2 and day > 29:  # February can't have more than 29 days
                            return False
                        if month == 2 and day == 29:  # Check for leap year
                            if not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                                return False
                        if month in [4, 6, 9, 11] and day > 30:  # April, June, September, November have 30 days
                            return False
                    except ValueError:
                        return False
                return True
        return False
    
    def _validate_relative_date(self, date_str: str) -> bool:
        """Validate relative date format for older_than:/newer_than: operators."""
        return bool(re.fullmatch(r'\d+[dmy]', date_str))
    
    def _validate_size_format(self, size_str: str) -> bool:
        """Validate size format for size-related operators."""
        return bool(re.fullmatch(r'\d+[KMGB]*', size_str, re.IGNORECASE))
    
    def _check_for_warnings(self, query: str) -> List[str]:
        """Check for potentially problematic query patterns.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for very long queries
        if len(query) > 500:
            warnings.append("Query is very long and may be slow")
        
        # Check for too many OR conditions
        or_count = query.lower().count(' or ')
        if or_count > 10:
            warnings.append("Too many OR conditions may impact performance")
        
        # Check for potentially inefficient patterns
        if 'has:attachment' in query and 'larger:' not in query:
            warnings.append("Consider adding size filter when searching attachments")
        
        return warnings
    
    def _find_closest_operator(self, operator: str) -> Optional[str]:
        """Find the closest matching supported operator.
        
        Uses simple string similarity to suggest corrections.
        """
        operator_lower = operator.lower()
        best_match = None
        best_score = 0
        
        for supported_op in self.SUPPORTED_OPERATORS:
            # Simple similarity score based on common characters
            score = len(set(operator_lower) & set(supported_op.lower()))
            if score > best_score and score >= len(operator_lower) * 0.6:
                best_score = score
                best_match = supported_op
        
        return best_match


class SearchConfigManager:
    """Manager for Gmail search configurations with CRUD operations.
    
    Provides functionality to create, read, update, and delete search configurations
    with JSON file-based storage and versioning support.
    """
    
    # Configuration file format version
    CONFIG_VERSION = "1.0"
    
    # Supported configuration file versions for backward compatibility
    SUPPORTED_VERSIONS = ["1.0"]
    
    # Migration functions for version upgrades
    MIGRATION_FUNCTIONS = {
        # Future migrations will be added here
        # "1.1": "_migrate_from_1_0_to_1_1",
    }
    
    def __init__(self, config_file: str = "search_configs.json"):
        """Initialize the search configuration manager.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        self.config_file = config_file
        self.validator = QueryValidator()
        self.logger = logging.getLogger(__name__)
        
        # Log initialization
        self.logger.debug(f"Initializing SearchConfigManager with config file: {config_file}")
        
        # Ensure configuration file exists with proper structure
        try:
            self._ensure_config_file()
            self.logger.debug("SearchConfigManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize SearchConfigManager: {e}")
            raise
    
    def save_config(self, config: SearchConfig) -> bool:
        """Save a search configuration to the file.
        
        Args:
            config: SearchConfig instance to save
            
        Returns:
            True if saved successfully
            
        Raises:
            QueryValidationError: If search query is invalid
            InvalidConfigurationError: If configuration name already exists
            CorruptedConfigFileError: If config file is corrupted
            NonRetryableError: If file system errors occur
        """
        try:
            self.logger.debug(f"Attempting to save search configuration: {config.name}")
            
            # Validate the search query
            is_valid, error_msg = self.validator.validate_query(config.query)
            if not is_valid:
                suggestions = self.validator.suggest_corrections(config.query)
                self.logger.warning(f"Invalid query for config '{config.name}': {error_msg}")
                raise QueryValidationError(config.query, error_msg, suggestions)
            
            # Load existing configurations with error handling
            try:
                config_data = self._load_config_file()
            except CorruptedConfigFileError:
                # If file is corrupted, we'll recreate it, so continue
                config_data = {"version": self.CONFIG_VERSION, "configs": {}}
                self.logger.warning("Using default config structure due to corrupted file")
            
            # Check if configuration name already exists
            if config.name in config_data["configs"]:
                self.logger.warning(f"Attempt to save duplicate configuration: {config.name}")
                raise InvalidConfigurationError(
                    f"Configuration '{config.name}' already exists. Use update_config() to modify it.",
                    config.name,
                    ["Use a different name", "Delete the existing configuration first", "Use update_config() instead"]
                )
            
            # Add new configuration
            config_data["configs"][config.name] = config.to_dict()
            
            # Save updated configurations
            self._save_config_file(config_data)
            
            self.logger.info(f"Successfully saved search configuration '{config.name}' with query: {config.query}")
            self.log_configuration_access(config.name, "save", True, f"Query: {config.query}")
            return True
            
        except (QueryValidationError, InvalidConfigurationError, CorruptedConfigFileError) as e:
            # Log the failure and re-raise our custom exceptions
            self.log_configuration_access(config.name, "save", False, str(e))
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving configuration '{config.name}': {e}")
            self.log_configuration_access(config.name, "save", False, f"Unexpected error: {str(e)}")
            # Convert to appropriate error type
            fs_error = handle_file_system_error(e, "saving configuration", self.config_file)
            raise fs_error
    
    def load_config(self, name: str) -> Optional[SearchConfig]:
        """Load a search configuration by name.
        
        Args:
            name: Name of the configuration to load
            
        Returns:
            SearchConfig instance if found, None otherwise
            
        Raises:
            ConfigurationNotFoundError: If configuration is not found (when raise_on_missing=True)
            CorruptedConfigFileError: If config file is corrupted
            InvalidConfigurationError: If configuration data is invalid
        """
        try:
            self.logger.debug(f"Loading search configuration: {name}")
            
            config_data = self._load_config_file()
            
            if name not in config_data["configs"]:
                self.logger.info(f"Configuration '{name}' not found")
                return None
            
            config_dict = config_data["configs"][name]
            
            try:
                config = SearchConfig.from_dict(config_dict)
                self.logger.debug(f"Successfully loaded configuration '{name}'")
                self.log_configuration_access(name, "load", True, f"Query: {config.query}")
                return config
            except ValueError as e:
                self.logger.error(f"Invalid configuration data for '{name}': {e}")
                self.log_configuration_access(name, "load", False, f"Invalid data: {str(e)}")
                raise InvalidConfigurationError(
                    f"Configuration '{name}' contains invalid data: {str(e)}",
                    name,
                    ["Delete and recreate the configuration", "Check the configuration file format"]
                )
            
        except (CorruptedConfigFileError, InvalidConfigurationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error loading configuration '{name}': {e}")
            # For load operations, we generally want to return None rather than raise
            return None
    
    def load_config_or_raise(self, name: str) -> SearchConfig:
        """Load a search configuration by name, raising an error if not found.
        
        Args:
            name: Name of the configuration to load
            
        Returns:
            SearchConfig instance
            
        Raises:
            ConfigurationNotFoundError: If configuration is not found
            CorruptedConfigFileError: If config file is corrupted
            InvalidConfigurationError: If configuration data is invalid
        """
        config = self.load_config(name)
        if config is None:
            # Get available configurations for better error message
            try:
                available_configs = [cfg.name for cfg in self.list_configs()]
            except Exception:
                available_configs = []
            
            raise ConfigurationNotFoundError(name, available_configs)
        
        return config
    
    def list_configs(self) -> List[SearchConfig]:
        """List all saved search configurations.
        
        Returns:
            List of SearchConfig instances
        """
        try:
            config_data = self._load_config_file()
            configs = []
            
            for config_dict in config_data["configs"].values():
                try:
                    config = SearchConfig.from_dict(config_dict)
                    configs.append(config)
                except ValueError as e:
                    self.logger.warning(f"Skipping invalid configuration: {e}")
            
            # Sort by name for consistent ordering
            configs.sort(key=lambda c: c.name)
            return configs
            
        except Exception as e:
            self.logger.error(f"Failed to list configurations: {e}")
            return []
    
    def delete_config(self, name: str) -> bool:
        """Delete a search configuration by name.
        
        Args:
            name: Name of the configuration to delete
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            Exception: If deletion fails due to file system errors
        """
        try:
            config_data = self._load_config_file()
            
            if name not in config_data["configs"]:
                self.logger.warning(f"Configuration '{name}' not found for deletion")
                return False
            
            # Remove configuration
            del config_data["configs"][name]
            
            # Save updated configurations
            self._save_config_file(config_data)
            
            self.logger.info(f"Deleted search configuration: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete configuration '{name}': {e}")
            raise
    
    def update_config(self, name: str, config: SearchConfig) -> bool:
        """Update an existing search configuration.
        
        Args:
            name: Name of the configuration to update
            config: Updated SearchConfig instance
            
        Returns:
            True if updated successfully, False if not found
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate the search query
            is_valid, error_msg = self.validator.validate_query(config.query)
            if not is_valid:
                suggestions = self.validator.suggest_corrections(config.query)
                raise QueryValidationError(config.query, error_msg, suggestions)
            
            config_data = self._load_config_file()
            
            if name not in config_data["configs"]:
                self.logger.warning(f"Configuration '{name}' not found for update")
                return False
            
            # Update configuration (preserve original created_at if not changed)
            old_config_dict = config_data["configs"][name]
            config_dict = config.to_dict()
            
            # Preserve created_at from original if not explicitly changed
            if config_dict["created_at"] == config.created_at.isoformat():
                config_dict["created_at"] = old_config_dict.get("created_at", config_dict["created_at"])
            
            config_data["configs"][name] = config_dict
            
            # Save updated configurations
            self._save_config_file(config_data)
            
            self.logger.info(f"Updated search configuration: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration '{name}': {e}")
            raise
    
    def update_usage_stats(self, name: str) -> bool:
        """Update usage statistics for a configuration.
        
        Args:
            name: Name of the configuration to update
            
        Returns:
            True if updated successfully, False if not found
        """
        try:
            self.logger.debug(f"Updating usage statistics for configuration: {name}")
            
            config_data = self._load_config_file()
            
            if name not in config_data["configs"]:
                self.logger.warning(f"Cannot update usage stats: configuration '{name}' not found")
                return False
            
            # Update usage statistics
            config_dict = config_data["configs"][name]
            old_count = config_dict.get("usage_count", 0)
            config_dict["usage_count"] = old_count + 1
            config_dict["last_used"] = datetime.now().isoformat()
            
            # Save updated configurations
            self._save_config_file(config_data)
            
            self.logger.info(f"Updated usage stats for configuration '{name}': usage count {old_count} -> {old_count + 1}")
            return True
            
        except (CorruptedConfigFileError, NonRetryableError):
            # Don't log these as errors since they're already handled
            self.logger.warning(f"Could not update usage stats for '{name}' due to file issues")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error updating usage stats for '{name}': {e}")
            return False
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate a Gmail search query.
        
        Args:
            query: Gmail search query string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.validator.validate_query(query)
    
    def get_config_stats(self) -> Dict[str, Any]:
        """Get statistics about saved configurations.
        
        Returns:
            Dictionary containing configuration statistics
        """
        try:
            configs = self.list_configs()
            
            if not configs:
                return {
                    "total_configs": 0,
                    "most_used": None,
                    "recently_used": None,
                    "total_usage": 0
                }
            
            # Calculate statistics
            total_usage = sum(config.usage_count for config in configs)
            most_used = max(configs, key=lambda c: c.usage_count)
            
            # Find most recently used (excluding None values)
            used_configs = [c for c in configs if c.last_used is not None]
            recently_used = max(used_configs, key=lambda c: c.last_used) if used_configs else None
            
            return {
                "total_configs": len(configs),
                "most_used": {
                    "name": most_used.name,
                    "usage_count": most_used.usage_count
                } if most_used.usage_count > 0 else None,
                "recently_used": {
                    "name": recently_used.name,
                    "last_used": recently_used.last_used.isoformat()
                } if recently_used else None,
                "total_usage": total_usage
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get configuration stats: {e}")
            return {"error": str(e)}
    
    def migrate_config_file(self, backup: bool = True) -> bool:
        """Migrate configuration file to current version format.
        
        Args:
            backup: Whether to create a backup before migration
            
        Returns:
            True if migration successful or not needed, False otherwise
        """
        try:
            config_data = self._load_config_file()
            current_version = config_data.get("version", "0.0")
            
            if current_version == self.CONFIG_VERSION:
                self.logger.info("Configuration file is already at current version")
                return True
            
            if backup:
                backup_file = f"{self.config_file}.backup.{current_version}"
                self._create_backup(backup_file)
                self.logger.info(f"Created backup at {backup_file}")
            
            # Perform version-specific migrations
            if current_version == "0.0":
                config_data = self._migrate_from_v0_to_v1(config_data)
            
            # Update version
            config_data["version"] = self.CONFIG_VERSION
            
            # Save migrated configuration
            self._save_config_file(config_data)
            
            self.logger.info(f"Migrated configuration file from {current_version} to {self.CONFIG_VERSION}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate configuration file: {e}")
            return False
    
    def _ensure_config_file(self):
        """Ensure configuration file exists with proper structure.
        
        Raises:
            CorruptedConfigFileError: If file exists but is corrupted beyond repair
        """
        try:
            if not os.path.exists(self.config_file):
                self.logger.info(f"Configuration file does not exist, creating: {self.config_file}")
                self._create_default_config_file()
                return
            
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                
            # Check if migration is needed
            current_version = config_data.get("version", "0.0")
            if current_version != self.CONFIG_VERSION:
                self.logger.info(f"Configuration file needs migration from {current_version} to {self.CONFIG_VERSION}")
                
                # Create backup before migration
                backup_path = self._create_backup(self.config_file)
                self.logger.info(f"Created backup at: {backup_path}")
                
                migrated_data = self._migrate_config_file(config_data, current_version)
                if migrated_data:
                    self._save_config_file(migrated_data)
                    self.logger.info(f"Successfully migrated configuration from {current_version} to {self.CONFIG_VERSION}")
                else:
                    self.logger.error("Configuration file migration failed")
                    # Restore from backup if migration failed
                    if backup_path and os.path.exists(backup_path):
                        shutil.copy2(backup_path, self.config_file)
                        self.logger.info("Restored configuration file from backup")
                return
                
            # Validate structure for current version
            if "version" not in config_data or "configs" not in config_data:
                raise ValueError("Invalid configuration file structure")
                
        except FileNotFoundError:
            self.logger.info(f"Creating new configuration file: {self.config_file}")
            self._create_default_config_file()
        except json.JSONDecodeError as e:
            self.logger.error(f"Configuration file contains invalid JSON: {e}")
            self._handle_corrupted_config_file(e)
        except (ValueError, KeyError) as e:
            self.logger.error(f"Configuration file has invalid structure: {e}")
            self._handle_corrupted_config_file(e)
        except Exception as e:
            self.logger.error(f"Unexpected error reading configuration file: {e}")
            fs_error = handle_file_system_error(e, "reading configuration file", self.config_file)
            raise fs_error
    
    def _create_default_config_file(self):
        """Create a new configuration file with default structure."""
        default_config = {
            "version": self.CONFIG_VERSION,
            "configs": {}
        }
        try:
            self._save_config_file(default_config)
            self.logger.info(f"Created default configuration file: {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to create default configuration file: {e}")
            fs_error = handle_file_system_error(e, "creating configuration file", self.config_file)
            raise fs_error
    
    def _handle_corrupted_config_file(self, original_error: Exception):
        """Handle a corrupted configuration file by backing it up and recreating.
        
        Args:
            original_error: The original error that indicated corruption
            
        Raises:
            CorruptedConfigFileError: Always raised to inform caller of the issue
        """
        backup_path = None
        try:
            # Create backup of corrupted file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_file}.corrupted.{timestamp}"
            shutil.copy2(self.config_file, backup_path)
            self.logger.warning(f"Created backup of corrupted file: {backup_path}")
            
            # Create new default file
            self._create_default_config_file()
            
        except Exception as backup_error:
            self.logger.error(f"Failed to backup corrupted file: {backup_error}")
            # Still try to create default file
            try:
                self._create_default_config_file()
            except Exception as create_error:
                self.logger.error(f"Failed to create default config after corruption: {create_error}")
        
        # Always raise the corruption error to inform the caller
        raise CorruptedConfigFileError(self.config_file, original_error, backup_path)
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration data from JSON file.
        
        Returns:
            Dictionary containing configuration data
            
        Raises:
            CorruptedConfigFileError: If file is corrupted or has invalid format
            NonRetryableError: If file system errors occur
        """
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Validate basic structure
            if not isinstance(config_data, dict):
                raise ValueError("Configuration file must contain a JSON object")
            
            if "configs" not in config_data:
                raise ValueError("Configuration file missing 'configs' section")
            
            if not isinstance(config_data["configs"], dict):
                raise ValueError("'configs' section must be a JSON object")
            
            return config_data
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_file}")
            # Create default file and return it
            self._create_default_config_file()
            return {"version": self.CONFIG_VERSION, "configs": {}}
        except json.JSONDecodeError as e:
            self.logger.error(f"Configuration file contains invalid JSON: {e}")
            self._handle_corrupted_config_file(e)
        except (ValueError, KeyError) as e:
            self.logger.error(f"Configuration file has invalid structure: {e}")
            self._handle_corrupted_config_file(e)
        except Exception as e:
            self.logger.error(f"Unexpected error loading configuration file: {e}")
            fs_error = handle_file_system_error(e, "loading configuration file", self.config_file)
            raise fs_error
    
    def _save_config_file(self, config_data: Dict[str, Any]):
        """Save configuration data to JSON file.
        
        Args:
            config_data: Dictionary containing configuration data
            
        Raises:
            Exception: If file cannot be written
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2, sort_keys=True)
        except Exception as e:
            self.logger.error(f"Failed to save configuration file: {e}")
            raise
    
    def _create_backup(self, backup_file: str):
        """Create a backup of the current configuration file.
        
        Args:
            backup_file: Path for the backup file
        """
        import shutil
        shutil.copy2(self.config_file, backup_file)
    
    def _migrate_from_v0_to_v1(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration from version 0.0 to 1.0.
        
        Args:
            config_data: Configuration data in v0.0 format
            
        Returns:
            Configuration data in v1.0 format
        """
        # In v0.0, there might not be a proper structure
        # Ensure all required fields exist
        if "configs" not in config_data:
            config_data["configs"] = {}
        
        # Migrate individual configurations to ensure all required fields
        for name, config_dict in config_data["configs"].items():
            if "usage_count" not in config_dict:
                config_dict["usage_count"] = 0
            if "last_used" not in config_dict:
                config_dict["last_used"] = None
            if "created_at" not in config_dict:
                config_dict["created_at"] = datetime.now().isoformat()
        
        return config_data
    
    def log_usage_summary(self) -> None:
        """Log a summary of search configuration usage patterns."""
        try:
            stats = self.get_config_stats()
            
            if "error" in stats:
                self.logger.warning(f"Could not generate usage summary: {stats['error']}")
                return
            
            total_configs = stats.get("total_configs", 0)
            total_usage = stats.get("total_usage", 0)
            
            self.logger.info(f"Search Configuration Usage Summary:")
            self.logger.info(f"  Total configurations: {total_configs}")
            self.logger.info(f"  Total usage count: {total_usage}")
            
            if total_configs > 0:
                avg_usage = total_usage / total_configs
                self.logger.info(f"  Average usage per config: {avg_usage:.1f}")
                
                most_used = stats.get("most_used")
                if most_used:
                    self.logger.info(f"  Most used config: '{most_used['name']}' ({most_used['usage_count']} times)")
                
                recently_used = stats.get("recently_used")
                if recently_used:
                    self.logger.info(f"  Most recently used: '{recently_used['name']}'")
            else:
                self.logger.info("  No configurations have been created yet")
                
        except Exception as e:
            self.logger.error(f"Failed to generate usage summary: {e}")
    
    def log_configuration_access(self, config_name: str, operation: str, success: bool, details: str = None):
        """Log configuration access for audit purposes.
        
        Args:
            config_name: Name of the configuration being accessed
            operation: Type of operation (load, save, update, delete)
            success: Whether the operation was successful
            details: Additional details about the operation
        """
        level = logging.INFO if success else logging.WARNING
        status = "SUCCESS" if success else "FAILED"
        
        message = f"Config {operation.upper()} {status}: '{config_name}'"
        if details:
            message += f" - {details}"
        
        self.logger.log(level, message)
        
        # Also log to a separate audit logger if configured
        audit_logger = logging.getLogger(f"{__name__}.audit")
        if audit_logger.handlers:  # Only log if audit logger is configured
            audit_logger.info(f"{datetime.now().isoformat()} | {operation.upper()} | {config_name} | {status} | {details or ''}")    

    def _migrate_config_file(self, config_data: Dict[str, Any], current_version: str) -> Optional[Dict[str, Any]]:
        """Migrate configuration file from current version to latest version.
        
        Args:
            config_data: Current configuration data
            current_version: Current version of the configuration file
            
        Returns:
            Migrated configuration data, or None if migration failed
        """
        try:
            # Check if current version is supported
            if current_version not in self.SUPPORTED_VERSIONS and current_version != "0.0":
                self.logger.warning(f"Unsupported configuration version: {current_version}")
                # For unsupported versions, try to preserve what we can
                return self._migrate_unsupported_version(config_data)
            
            # Handle legacy files without version (version 0.0)
            if current_version == "0.0":
                config_data = self._migrate_from_legacy(config_data)
                current_version = "1.0"
            
            # Apply sequential migrations if needed
            migrated_data = config_data.copy()
            
            # Future migrations would be applied here
            # For example, if we had version 1.1:
            # if current_version == "1.0" and self.CONFIG_VERSION >= "1.1":
            #     migrated_data = self._migrate_from_1_0_to_1_1(migrated_data)
            #     current_version = "1.1"
            
            # Update version to current
            migrated_data["version"] = self.CONFIG_VERSION
            
            return migrated_data
            
        except Exception as e:
            self.logger.error(f"Migration failed from {current_version} to {self.CONFIG_VERSION}: {e}")
            return None
    
    def _migrate_from_legacy(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from legacy configuration format (no version field).
        
        Args:
            config_data: Legacy configuration data
            
        Returns:
            Migrated configuration data in version 1.0 format
        """
        self.logger.info("Migrating from legacy configuration format")
        
        migrated_data = {
            "version": "1.0",
            "configs": {}
        }
        
        # If the legacy file has a "configs" key, preserve it
        if "configs" in config_data and isinstance(config_data["configs"], dict):
            migrated_data["configs"] = config_data["configs"]
            self.logger.info(f"Preserved {len(config_data['configs'])} existing configurations")
        
        # Handle other legacy formats if they existed
        # For example, if configurations were stored directly at root level:
        elif isinstance(config_data, dict):
            # Check if this looks like a direct configuration storage
            for key, value in config_data.items():
                if isinstance(value, dict) and "query" in value:
                    migrated_data["configs"][key] = value
                    self.logger.info(f"Migrated legacy configuration: {key}")
        
        return migrated_data
    
    def _migrate_unsupported_version(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle migration from unsupported/future versions.
        
        This method attempts to preserve as much data as possible when encountering
        a configuration file from an unsupported (likely newer) version.
        
        Args:
            config_data: Configuration data from unsupported version
            
        Returns:
            Best-effort migrated configuration data
        """
        self.logger.warning("Attempting to handle unsupported configuration version")
        
        migrated_data = {
            "version": self.CONFIG_VERSION,
            "configs": {}
        }
        
        # Try to preserve configurations if they exist in a recognizable format
        if "configs" in config_data and isinstance(config_data["configs"], dict):
            for name, config in config_data["configs"].items():
                try:
                    # Validate that this looks like a valid configuration
                    if isinstance(config, dict) and "query" in config:
                        # Only preserve fields we understand
                        preserved_config = {
                            "name": config.get("name", name),
                            "query": config["query"],
                            "description": config.get("description", "Migrated configuration"),
                            "created_at": config.get("created_at", datetime.now().isoformat()),
                            "last_used": config.get("last_used"),
                            "usage_count": config.get("usage_count", 0)
                        }
                        migrated_data["configs"][name] = preserved_config
                        self.logger.info(f"Preserved configuration from unsupported version: {name}")
                except Exception as e:
                    self.logger.warning(f"Could not preserve configuration '{name}': {e}")
        
        return migrated_data
    
    def _check_and_migrate_config_file(self):
        """Check if configuration file needs migration and perform it if necessary.
        
        This method is called during initialization to ensure the configuration file
        is in the correct format for the current version.
        """
        try:
            if not os.path.exists(self.config_file):
                return  # Nothing to migrate
            
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            current_version = config_data.get("version", "0.0")
            
            if current_version != self.CONFIG_VERSION:
                self.logger.info(f"Configuration file migration needed: {current_version} -> {self.CONFIG_VERSION}")
                
                # Create backup before migration
                backup_path = self._create_backup(self.config_file)
                self.logger.info(f"Created backup at: {backup_path}")
                
                # Perform migration
                migrated_data = self._migrate_config_file(config_data, current_version)
                
                if migrated_data:
                    self._save_config_file(migrated_data)
                    self.logger.info("Configuration file migration completed successfully")
                else:
                    self.logger.error("Configuration file migration failed")
                    # Restore from backup if migration failed
                    if backup_path and os.path.exists(backup_path):
                        shutil.copy2(backup_path, self.config_file)
                        self.logger.info("Restored configuration file from backup")
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Configuration file contains invalid JSON, will be recreated: {e}")
        except Exception as e:
            self.logger.warning(f"Error during configuration file migration check: {e}")
    
    def _create_backup(self, file_path: str) -> str:
        """Create a backup of the configuration file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    def is_search_feature_available(self) -> bool:
        """Check if search configuration features are available.
        
        This method provides a way to check if search customization features
        are working properly, allowing for graceful degradation.
        
        Returns:
            True if search features are available, False otherwise
        """
        try:
            # Check if configuration file is accessible
            if not os.path.exists(self.config_file):
                return True  # File will be created when needed
            
            # Try to read the configuration file
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Check if it has the expected structure
            if "version" not in config_data or "configs" not in config_data:
                return False
            
            # Check if version is supported
            version = config_data.get("version", "0.0")
            if version not in self.SUPPORTED_VERSIONS and version != "0.0":
                self.logger.warning(f"Configuration file version {version} may not be fully supported")
                return True  # Still try to work with it
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Search configuration features unavailable: {e}")
            return False
    
    def get_backward_compatibility_info(self) -> Dict[str, Any]:
        """Get information about backward compatibility status.
        
        Returns:
            Dictionary containing compatibility information
        """
        try:
            info = {
                "search_features_available": self.is_search_feature_available(),
                "config_file_exists": os.path.exists(self.config_file),
                "config_file_version": None,
                "migration_needed": False,
                "supported_versions": self.SUPPORTED_VERSIONS.copy(),
                "current_version": self.CONFIG_VERSION
            }
            
            if info["config_file_exists"]:
                try:
                    with open(self.config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    info["config_file_version"] = config_data.get("version", "0.0")
                    info["migration_needed"] = info["config_file_version"] != self.CONFIG_VERSION
                    
                except Exception as e:
                    info["config_file_error"] = str(e)
            
            return info
            
        except Exception as e:
            return {
                "search_features_available": False,
                "error": str(e),
                "supported_versions": self.SUPPORTED_VERSIONS.copy(),
                "current_version": self.CONFIG_VERSION
            }