# Technology Stack

## Core Technologies

- **Python 3.7+**: Main programming language
- **Gmail API**: Google API client for email access
- **OAuth2**: Authentication via google-auth-oauthlib
- **AI Services**: OpenAI GPT models or Anthropic Claude
- **YAML**: Structured data storage format
- **JSON**: Configuration file format

## Key Dependencies

```
google-api-python-client>=2.0.0    # Gmail API integration
google-auth-httplib2>=0.1.0        # HTTP transport for Google Auth
google-auth-oauthlib>=0.5.0        # OAuth2 flow handling
PyYAML>=6.0                        # YAML file processing
beautifulsoup4>=4.9.0              # HTML email content parsing
python-dateutil>=2.8.0             # Date parsing utilities
openai>=1.0.0                      # OpenAI API client
anthropic>=0.7.0                   # Claude API client
requests>=2.28.0                   # HTTP requests
python-dotenv>=0.19.0              # Environment variable loading
```

## Development Environment

### Setup Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Verify installation
python main.py --test-ai
```

### Testing Commands

```bash
# Run basic functionality tests
python test_basic_functionality.py

# Run specific test suites
python test_config_management_commands.py
python test_search_configs.py
python test_email_fetcher_custom_queries.py

# Test with minimal processing
python main.py --max-emails 1 --verbose
```

### Common Development Commands

```bash
# Run with verbose logging
python main.py --verbose

# Test AI connection
python main.py --test-ai

# List search configurations
python main.py --list-configs

# Validate search query
python main.py --validate-query "from:test@example.com"

# Process limited emails for testing
python main.py --max-emails 5 --verbose
```

## Configuration Management

- **Environment Variables**: Loaded via python-dotenv from `.env` file
- **Credentials**: OAuth2 credentials in `credentials.json` (not committed)
- **Tokens**: Stored in `token.json` (auto-generated, not committed)
- **Search Configs**: Managed in `search_configs.json`

## Security Considerations

- All sensitive files (credentials.json, token.json, .env) are gitignored
- OAuth2 tokens are automatically refreshed
- Read-only Gmail API access
- API keys stored in environment variables only