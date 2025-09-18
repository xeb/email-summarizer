# Requirements Document

## Introduction

This feature extends the existing Gmail Email Summarizer by adding customizable search query functionality. Users can define and store custom Gmail search configurations to target specific emails from certain senders, time periods, or other criteria, while maintaining the default behavior when no custom search is specified.

## Requirements

### Requirement 1

**User Story:** As a user, I want to define custom Gmail search queries, so that I can target specific emails based on sender, date range, subject, or other Gmail search criteria.

#### Acceptance Criteria

1. WHEN I specify a custom search query THEN the system SHALL use Gmail search operators like from:, to:, subject:, after:, before:, has:attachment
2. WHEN I provide multiple search criteria THEN the system SHALL combine them using Gmail's search syntax
3. WHEN I specify a date range THEN the system SHALL support relative dates (e.g., "last 7 days") and absolute dates (e.g., "2024-01-01")
4. WHEN I specify sender criteria THEN the system SHALL support single senders, multiple senders, and domain-based filtering

### Requirement 2

**User Story:** As a user, I want to save and reuse search configurations, so that I don't have to specify complex search queries repeatedly.

#### Acceptance Criteria

1. WHEN I create a search configuration THEN the system SHALL store it with a user-defined name in a configuration file
2. WHEN I save a search configuration THEN the system SHALL include the search query, description, and creation date
3. WHEN I list saved configurations THEN the system SHALL display all available search configurations with their names and descriptions
4. WHEN I reference a saved configuration THEN the system SHALL load and apply the stored search query

### Requirement 3

**User Story:** As a user, I want to use custom search queries via command-line arguments, so that I can easily specify different search criteria for different runs.

#### Acceptance Criteria

1. WHEN I run the tool without search arguments THEN the system SHALL use the default search query (important and unread emails)
2. WHEN I provide a --search-config argument THEN the system SHALL use the named saved configuration
3. WHEN I provide a --search-query argument THEN the system SHALL use the provided Gmail search query directly
4. WHEN I provide both search arguments THEN the system SHALL prioritize --search-query over --search-config
5. WHEN I provide an invalid configuration name THEN the system SHALL display available configurations and exit with an error

### Requirement 4

**User Story:** As a user, I want to manage my saved search configurations, so that I can add, update, delete, and organize my custom searches.

#### Acceptance Criteria

1. WHEN I want to add a new configuration THEN the system SHALL provide a command to create and save a new search configuration
2. WHEN I want to update an existing configuration THEN the system SHALL allow modifying the search query and description
3. WHEN I want to delete a configuration THEN the system SHALL remove it from the configuration file after confirmation
4. WHEN I want to view a configuration THEN the system SHALL display the search query, description, and usage statistics

### Requirement 5

**User Story:** As a user, I want validation and helpful error messages for search configurations, so that I can quickly identify and fix issues with my custom searches.

#### Acceptance Criteria

1. WHEN I provide an invalid Gmail search query THEN the system SHALL validate the query syntax and display helpful error messages
2. WHEN a search query returns no results THEN the system SHALL log this information and create an empty summary file
3. WHEN a search configuration file is corrupted THEN the system SHALL display a clear error message and suggest recovery options
4. WHEN I use unsupported search operators THEN the system SHALL warn about potentially unsupported Gmail search syntax