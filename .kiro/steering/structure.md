# Project Structure

## Directory Organization

```
gmail-email-summarizer/
├── main.py                 # CLI entry point and workflow orchestration
├── auth/                   # Gmail OAuth2 authentication
│   └── gmail_auth.py
├── config/                 # Configuration management
│   ├── settings.py         # Environment and config loading
│   ├── search_configs.py   # Search configuration management
│   └── example_configs.py  # Example search configurations
├── gmail_email/            # Email fetching and processing
│   ├── fetcher.py          # Gmail API integration
│   └── processor.py        # Email content processing
├── summarization/          # AI-powered summarization
│   └── summarizer.py       # OpenAI/Claude integration
├── storage/                # Data persistence
│   └── yaml_writer.py      # YAML file management
├── utils/                  # Shared utilities
│   └── error_handling.py   # Error handling and retry logic
├── email_summaries/        # Output directory (generated)
├── test_*.py              # Test files (multiple)
└── requirements.txt       # Dependencies
```

## Module Responsibilities

### Core Modules

- **main.py**: CLI argument parsing, workflow orchestration, command routing
- **auth/gmail_auth.py**: OAuth2 flow, token management, Gmail service creation
- **config/settings.py**: Environment variable loading, configuration validation
- **gmail_email/fetcher.py**: Gmail API calls, email retrieval, query validation
- **gmail_email/processor.py**: Email content extraction, HTML cleaning, data normalization
- **summarization/summarizer.py**: AI service integration, structured summary generation
- **storage/yaml_writer.py**: Daily YAML file creation and management

### Configuration Modules

- **config/search_configs.py**: Search configuration CRUD operations, query validation
- **config/example_configs.py**: Pre-defined search configurations and help text

### Utility Modules

- **utils/error_handling.py**: Centralized error handling, retry logic, user-friendly messages

## Data Flow Architecture

1. **CLI Layer** (main.py) → Argument parsing and command routing
2. **Configuration Layer** (config/) → Settings loading and validation
3. **Authentication Layer** (auth/) → Gmail OAuth2 authentication
4. **Data Retrieval Layer** (gmail_email/) → Email fetching and processing
5. **AI Processing Layer** (summarization/) → Content summarization
6. **Storage Layer** (storage/) → YAML file persistence

## File Naming Conventions

- **Module files**: lowercase with underscores (e.g., `gmail_auth.py`)
- **Test files**: prefix with `test_` (e.g., `test_basic_functionality.py`)
- **Configuration files**: descriptive names (e.g., `search_configs.json`)
- **Output files**: date-based YAML (e.g., `2025-09-17.yaml`)

## Import Patterns

- **Relative imports**: Used within packages (e.g., `from .processor import EmailData`)
- **Absolute imports**: Used for cross-package imports (e.g., `from config.settings import Config`)
- **Conditional imports**: Used for optional dependencies (AI libraries)

## Error Handling Architecture

- **Custom exceptions**: Module-specific error classes inheriting from base error types
- **Retry logic**: Centralized in `utils/error_handling.py` with exponential backoff
- **User-friendly messages**: Error translation for CLI users
- **Graceful degradation**: Fallback behavior when features are unavailable

## Testing Structure

- **Unit tests**: Individual function/class testing
- **Integration tests**: Cross-module workflow testing
- **Functionality tests**: End-to-end feature validation
- **Mock usage**: External API calls mocked for reliable testing