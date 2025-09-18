# Design Document

## Overview

The Gmail Search Customization feature extends the existing Gmail Email Summarizer by adding flexible search query capabilities. Users can define custom Gmail search configurations, save them for reuse, and apply them via command-line arguments. This design maintains backward compatibility with the existing default behavior while providing powerful customization options.

## Architecture

The feature integrates with the existing modular architecture by extending the configuration system and email fetcher:

```
gmail-email-summarizer/
├── main.py                     # Updated CLI with search arguments
├── config/
│   ├── settings.py            # Extended with search configuration
│   └── search_configs.py      # NEW: Search configuration management
├── gmail_email/
│   └── fetcher.py             # Updated to accept custom queries
└── search_configs.json        # NEW: Stored search configurations
```

## Components and Interfaces

### 1. Search Configuration Manager (`config/search_configs.py`)

**Purpose:** Manages custom search configurations with CRUD operations

**Key Classes:**
```python
@dataclass
class SearchConfig:
    name: str
    query: str
    description: str
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0

class SearchConfigManager:
    def __init__(self, config_file: str = "search_configs.json")
    def save_config(self, config: SearchConfig) -> bool
    def load_config(self, name: str) -> Optional[SearchConfig]
    def list_configs(self) -> List[SearchConfig]
    def delete_config(self, name: str) -> bool
    def update_config(self, name: str, config: SearchConfig) -> bool
    def validate_query(self, query: str) -> Tuple[bool, str]
```

**Configuration File Structure:**
```json
{
  "version": "1.0",
  "configs": {
    "work-emails": {
      "name": "work-emails",
      "query": "from:@company.com is:unread after:2024-01-01",
      "description": "Unread emails from company domain since start of year",
      "created_at": "2024-01-15T10:30:00Z",
      "last_used": "2024-01-16T09:15:00Z",
      "usage_count": 5
    },
    "urgent-today": {
      "name": "urgent-today",
      "query": "is:important is:unread newer_than:1d",
      "description": "Important unread emails from today",
      "created_at": "2024-01-15T11:00:00Z",
      "last_used": null,
      "usage_count": 0
    }
  }
}
```

### 2. Extended Configuration (`config/settings.py`)

**Purpose:** Integrate search configuration into main application config

**New Configuration Fields:**
```python
@dataclass
class Config:
    # ... existing fields ...
    
    # Search Configuration Settings
    search_configs_file: str = "search_configs.json"
    default_search_query: str = "is:unread is:important"
    enable_search_validation: bool = True
    max_search_results: int = 100
```

### 3. Updated Email Fetcher (`gmail_email/fetcher.py`)

**Purpose:** Accept and use custom search queries

**Modified Methods:**
```python
class EmailFetcher:
    def fetch_emails_with_query(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]
    def fetch_important_unread_emails(self, max_results: int = 50) -> List[Dict[str, Any]]  # Wrapper for backward compatibility
    def validate_gmail_query(self, query: str) -> Tuple[bool, str]
```

### 4. Enhanced CLI Interface (`main.py`)

**Purpose:** Provide command-line access to search customization

**New Command-Line Arguments:**
```python
parser.add_argument(
    '--search-config', '-sc',
    type=str,
    help='Use a saved search configuration by name'
)

parser.add_argument(
    '--search-query', '-sq',
    type=str,
    help='Use a custom Gmail search query directly'
)

parser.add_argument(
    '--list-configs',
    action='store_true',
    help='List all saved search configurations and exit'
)

parser.add_argument(
    '--save-config',
    nargs=3,
    metavar=('NAME', 'QUERY', 'DESCRIPTION'),
    help='Save a new search configuration'
)

parser.add_argument(
    '--delete-config',
    type=str,
    metavar='NAME',
    help='Delete a saved search configuration'
)
```

## Data Models

### Search Configuration Data Structure
```python
@dataclass
class SearchConfig:
    name: str                    # Unique identifier for the configuration
    query: str                   # Gmail search query string
    description: str             # Human-readable description
    created_at: datetime         # When the configuration was created
    last_used: Optional[datetime] = None  # Last time this config was used
    usage_count: int = 0         # Number of times this config has been used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchConfig':
        """Create instance from dictionary."""
```

### Gmail Search Query Validation
```python
class QueryValidator:
    SUPPORTED_OPERATORS = [
        'from:', 'to:', 'subject:', 'has:', 'is:', 'in:',
        'after:', 'before:', 'older_than:', 'newer_than:',
        'size:', 'larger:', 'smaller:', 'filename:'
    ]
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate Gmail search query syntax."""
        
    def suggest_corrections(self, query: str) -> List[str]:
        """Suggest corrections for invalid queries."""
```

## Integration Points

### 1. Main Application Workflow
```python
def process_emails() -> int:
    # ... existing setup ...
    
    # Determine search query to use
    search_query = determine_search_query(args, config)
    
    # Fetch emails with custom or default query
    raw_emails = email_fetcher.fetch_emails_with_query(search_query, config.max_emails_per_run)
    
    # ... rest of existing workflow ...

def determine_search_query(args, config) -> str:
    """Determine which search query to use based on arguments and config."""
    if args.search_query:
        return args.search_query
    elif args.search_config:
        search_manager = SearchConfigManager(config.search_configs_file)
        saved_config = search_manager.load_config(args.search_config)
        if saved_config:
            search_manager.update_usage_stats(args.search_config)
            return saved_config.query
        else:
            raise ValueError(f"Search configuration '{args.search_config}' not found")
    else:
        return config.default_search_query
```

### 2. Configuration Management Commands
```python
def handle_config_commands(args) -> int:
    """Handle search configuration management commands."""
    search_manager = SearchConfigManager()
    
    if args.list_configs:
        return list_search_configs(search_manager)
    elif args.save_config:
        return save_search_config(search_manager, *args.save_config)
    elif args.delete_config:
        return delete_search_config(search_manager, args.delete_config)
    
    return 0
```

## Gmail Search Query Support

### Supported Gmail Operators
The system will support all standard Gmail search operators:

**Basic Operators:**
- `from:sender@domain.com` - Emails from specific sender
- `to:recipient@domain.com` - Emails to specific recipient
- `subject:"exact phrase"` - Emails with specific subject
- `has:attachment` - Emails with attachments
- `is:unread` - Unread emails
- `is:important` - Important emails
- `is:starred` - Starred emails

**Date Operators:**
- `after:2024-01-01` - Emails after specific date
- `before:2024-12-31` - Emails before specific date
- `newer_than:7d` - Emails newer than 7 days
- `older_than:1m` - Emails older than 1 month

**Size Operators:**
- `larger:10M` - Emails larger than 10MB
- `smaller:1M` - Emails smaller than 1MB

**Advanced Operators:**
- `filename:pdf` - Emails with PDF attachments
- `in:inbox` - Emails in inbox
- `label:work` - Emails with specific label

### Query Examples
```python
EXAMPLE_QUERIES = {
    "work-urgent": "from:@company.com is:important is:unread",
    "recent-attachments": "has:attachment newer_than:3d",
    "large-emails": "larger:5M after:2024-01-01",
    "specific-sender": "from:manager@company.com subject:project",
    "date-range": "after:2024-01-01 before:2024-01-31 is:unread"
}
```

## Error Handling

### Configuration Errors
- **Invalid Configuration Name:** Clear error message with available options
- **Duplicate Configuration Names:** Prevent overwrites without confirmation
- **Corrupted Configuration File:** Backup and recovery mechanisms
- **Permission Issues:** Clear error messages about file access

### Query Validation Errors
- **Invalid Gmail Operators:** Suggest correct syntax
- **Malformed Date Formats:** Provide format examples
- **Unsupported Operators:** List supported operators
- **Empty Query Results:** Log information and create empty summary

### Runtime Errors
- **Configuration Not Found:** List available configurations
- **Gmail API Query Errors:** Validate queries before API calls
- **Network Issues:** Retry logic for configuration file access

## Testing Strategy

### Unit Tests
- Search configuration CRUD operations
- Query validation logic
- Command-line argument parsing
- Configuration file serialization/deserialization

### Integration Tests
- End-to-end workflow with custom queries
- Configuration management commands
- Gmail API integration with custom queries
- Error handling scenarios

### Manual Testing Scenarios
1. Create and use custom search configurations
2. Test various Gmail search operators
3. Verify backward compatibility with existing functionality
4. Test error scenarios and recovery

## Security Considerations

### Configuration File Security
- **File Permissions:** Restrict access to configuration files (600)
- **Input Validation:** Sanitize all user inputs for configuration names and queries
- **Path Traversal Prevention:** Validate configuration file paths

### Gmail Query Security
- **Query Sanitization:** Prevent injection of malicious operators
- **Rate Limiting:** Respect Gmail API rate limits with custom queries
- **Scope Validation:** Ensure queries don't exceed granted OAuth scopes

### Data Privacy
- **Configuration Storage:** Store only search queries, not email content
- **Logging:** Avoid logging sensitive search criteria
- **Audit Trail:** Optional logging of configuration usage for debugging

## Performance Considerations

### Configuration Management
- **Lazy Loading:** Load configurations only when needed
- **Caching:** Cache frequently used configurations in memory
- **File I/O Optimization:** Minimize configuration file reads/writes

### Gmail API Efficiency
- **Query Optimization:** Validate queries before API calls
- **Result Limiting:** Enforce reasonable limits on search results
- **Batch Processing:** Process multiple configurations efficiently

## Backward Compatibility

### Existing Functionality
- **Default Behavior:** Maintain existing default search query
- **API Compatibility:** Preserve existing method signatures
- **Configuration Format:** Extend existing config without breaking changes

### Migration Strategy
- **Graceful Degradation:** Function without search configurations
- **Optional Dependencies:** Make search customization features optional
- **Version Compatibility:** Support configuration file format versioning

## Future Enhancements

### Advanced Features
- **Query Templates:** Parameterized queries with variable substitution
- **Scheduled Searches:** Time-based execution of different configurations
- **Search Analytics:** Usage statistics and query performance metrics
- **Import/Export:** Share configurations between installations

### UI Improvements
- **Interactive Configuration:** Guided configuration creation
- **Query Builder:** Visual query construction interface
- **Preview Mode:** Test queries without processing emails
- **Configuration Validation:** Real-time query syntax checking