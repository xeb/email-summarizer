# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gmail Email Summarizer is a Python command-line tool that automatically connects to Gmail, fetches important unread emails, and generates AI-powered summaries stored in YAML files. The application supports both OpenAI and Claude AI providers with extensive search customization and headless authentication for server environments.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Testing Commands
```bash
# Test basic functionality
python test_basic_functionality.py

# Test specific components
python -m pytest test_search_configs.py -v
python -m pytest test_backward_compatibility.py -v
python -m pytest test_transcript_generator.py -v

# Test AI connection only
python main.py --test-ai

# Test with minimal processing for debugging
python main.py --max-emails 1 --verbose --output-dir ./debug_output
```

### Running the Application
```bash
# Basic usage
python main.py

# Headless authentication for SSH/servers
python main.py --headless

# Test with custom search
python main.py --search-query "from:@company.com is:unread" --max-emails 5
```

## Architecture Overview

### Core Module Structure
- **`main.py`**: Entry point with comprehensive CLI argument parsing and workflow orchestration
- **`config/`**: Configuration management with environment variable loading and validation
- **`auth/`**: Gmail OAuth2 authentication with headless support for SSH environments
- **`gmail_email/`**: Email fetching and content processing using Gmail API
- **`summarization/`**: AI-powered summarization with OpenAI/Claude integration
- **`storage/`**: YAML file writing and transcript generation
- **`utils/`**: Error handling with retry logic and user-friendly messages

### Key Architectural Patterns

#### Configuration System
The `Config` dataclass in `config/settings.py` centralizes all configuration with environment variable support. AI provider selection is dynamic between OpenAI and Claude based on available API keys.

#### Authentication Flow
`auth/gmail_auth.py` implements dual authentication modes:
- Browser-based OAuth2 for local development
- Headless authentication with manual URL entry for SSH/server environments
- Sets `OAUTHLIB_INSECURE_TRANSPORT=1` to allow localhost HTTP redirects

#### Error Handling Architecture
Comprehensive error handling system in `utils/error_handling.py`:
- Custom exception hierarchy with `RetryableError` and `NonRetryableError`
- Retry decorator with exponential backoff
- Error categorization for user-friendly messages

#### Search Configuration System
Advanced Gmail search customization with:
- Saved search configurations in JSON format
- Query validation against Gmail search operators
- Interactive search help and examples

### Data Flow
1. **Configuration Loading**: Environment variables → `Config` dataclass
2. **Authentication**: OAuth2 credentials → Gmail API service object
3. **Email Fetching**: Gmail API → filtered email list based on search criteria
4. **Content Processing**: Raw email data → cleaned `EmailData` objects
5. **AI Summarization**: Processed emails → structured `EmailSummary` objects
6. **Storage**: Summaries → daily YAML files + optional transcripts

### Important Implementation Details

#### Headless Authentication
The authentication system detects interactive vs non-interactive terminals and adjusts the OAuth2 flow accordingly. For SSH environments, it provides manual URL entry with proper redirect_uri handling.

#### AI Provider Abstraction
The `EmailSummarizer` class abstracts OpenAI and Claude APIs with identical interfaces, allowing runtime provider switching via configuration.

#### Search Query Validation
Built-in Gmail search operator validation with helpful suggestions for common typos and invalid syntax.

#### Transcript Generation
Optional transcript generation creates formatted summaries for voice consumption, integrated with the main workflow.

## Configuration Files

### Required Files
- `credentials.json`: Gmail OAuth2 credentials from Google Cloud Console
- `.env`: API keys and configuration overrides

### Generated Files
- `token.json`: Stored Gmail authentication tokens
- `search_configs.json`: Saved search configurations
- `email_summaries/YYYY-MM-DD.yaml`: Daily summary files
- `transcripts/YYYY-MM-DD.txt`: Optional transcript files

## Testing Strategy

The project includes extensive test coverage:
- `test_basic_functionality.py`: Core component integration testing
- `test_search_configs.py`: Search configuration management
- `test_backward_compatibility.py`: Compatibility with existing installations
- Component-specific tests for transcript generation, CLI arguments, and error handling

When modifying core functionality, run the basic functionality test first, then relevant component tests.