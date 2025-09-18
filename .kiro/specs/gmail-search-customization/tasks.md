# Implementation Plan

- [x] 1. Create search configuration data models and validation
  - Implement SearchConfig dataclass with serialization methods
  - Create QueryValidator class with Gmail operator validation
  - Add unit tests for data models and validation logic
  - _Requirements: 1.1, 1.2, 5.1, 5.2_

- [x] 2. Implement search configuration manager
  - Create SearchConfigManager class with CRUD operations
  - Implement JSON file-based configuration storage
  - Add configuration file versioning and migration support
  - Create unit tests for configuration management operations
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Extend main configuration system
  - Update Config dataclass with search-related settings
  - Add search configuration file path and default query settings
  - Implement configuration validation for search settings
  - Create unit tests for extended configuration system
  - _Requirements: 2.1, 3.1_

- [x] 4. Update email fetcher for custom queries
  - Modify EmailFetcher to accept custom Gmail search queries
  - Add fetch_emails_with_query method with query parameter
  - Maintain backward compatibility with existing fetch_important_unread_emails method
  - Implement Gmail query validation before API calls
  - Create unit tests for custom query functionality
  - _Requirements: 1.1, 1.3, 3.2, 5.1_

- [x] 5. Implement command-line interface extensions
  - Add new CLI arguments for search configuration management
  - Implement --search-config and --search-query argument handling
  - Add --list-configs, --save-config, and --delete-config commands
  - Create argument validation and error handling
  - Write unit tests for CLI argument parsing
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3_

- [x] 6. Create configuration management command handlers
  - Implement list_search_configs function to display saved configurations
  - Create save_search_config function for adding new configurations
  - Implement delete_search_config function with confirmation prompts
  - Add update_search_config function for modifying existing configurations
  - Create unit tests for all configuration management commands
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7. Integrate search customization into main workflow
  - Update main process_emails function to handle custom search queries
  - Implement determine_search_query function for query selection logic
  - Add search configuration usage statistics tracking
  - Integrate error handling for invalid configurations and queries
  - Create integration tests for end-to-end workflow with custom searches
  - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [x] 8. Add comprehensive error handling and validation
  - Implement error handling for corrupted configuration files
  - Add validation for Gmail search query syntax
  - Create user-friendly error messages for invalid configurations
  - Implement fallback behavior when configurations are not found
  - Add logging for search configuration usage and errors
  - Create unit tests for error scenarios
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 9. Create example configurations and documentation
  - Create sample search configurations for common use cases
  - Add inline help text for Gmail search operators
  - Implement configuration validation with helpful suggestions
  - Create example queries for different scenarios (work emails, date ranges, etc.)
  - Add unit tests for example configurations
  - _Requirements: 1.1, 1.4, 5.4_

- [x] 10. Add backward compatibility and migration support
  - Ensure existing functionality works without search configurations
  - Implement graceful degradation when search features are unavailable
  - Add configuration file format versioning
  - Create migration logic for future configuration format changes
  - Write integration tests to verify backward compatibility
  - _Requirements: 3.1, 3.2_