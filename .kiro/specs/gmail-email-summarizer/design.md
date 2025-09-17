# Design Document

## Overview

The Gmail Email Summarizer is a Python command-line application that automates the process of retrieving, processing, and summarizing important unread emails from a Gmail account. The system uses the Gmail API for secure access, implements content extraction and summarization capabilities, and stores results in structured YAML files organized by date.

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
gmail-email-summarizer/
├── main.py                 # Entry point and CLI interface
├── auth/
│   ├── __init__.py
│   └── gmail_auth.py      # OAuth2 authentication handling
├── email/
│   ├── __init__.py
│   ├── fetcher.py         # Gmail API email retrieval
│   └── processor.py       # Email content extraction and processing
├── summarization/
│   ├── __init__.py
│   └── summarizer.py      # Email content summarization
├── storage/
│   ├── __init__.py
│   └── yaml_writer.py     # YAML file management
├── config/
│   ├── __init__.py
│   └── settings.py        # Configuration management
└── requirements.txt       # Python dependencies
```

## Components and Interfaces

### 1. Authentication Module (`auth/gmail_auth.py`)

**Purpose:** Handles OAuth2 authentication with Gmail API

**Key Methods:**
- `authenticate()` → `google.auth.credentials.Credentials`
- `get_gmail_service()` → `googleapiclient.discovery.Resource`

**Dependencies:**
- Google API Client Library
- OAuth2 credentials file (credentials.json)
- Token storage (token.json)

### 2. Email Fetcher (`email/fetcher.py`)

**Purpose:** Retrieves emails using Gmail API with specific filters

**Key Methods:**
- `fetch_important_unread_emails()` → `List[Dict]`
- `get_email_content(message_id: str)` → `Dict`

**Gmail API Query:** `is:unread is:important`

### 3. Email Processor (`email/processor.py`)

**Purpose:** Extracts and cleans email content from various formats

**Key Methods:**
- `extract_email_data(raw_email: Dict)` → `EmailData`
- `clean_html_content(html: str)` → `str`
- `extract_plain_text(email_parts: List)` → `str`

**EmailData Structure:**
```python
@dataclass
class EmailData:
    subject: str
    sender: str
    date: datetime
    body: str
    message_id: str
```

### 4. Summarizer (`summarization/summarizer.py`)

**Purpose:** Generates concise summaries of email content using AI models (OpenAI or Claude)

**Key Methods:**
- `summarize_email(email_data: EmailData)` → `EmailSummary`
- `call_openai_api(content: str, prompt: str)` → `str`
- `call_claude_api(content: str, prompt: str)` → `str`
- `parse_ai_response(response: str)` → `Dict[str, List[str]]`

**AI Summarization Approach:**
- **Provider Selection:** Configurable choice between OpenAI (GPT-4/3.5) or Claude (Anthropic)
- **Structured Prompts:** Use specific prompts to extract summaries, key points, and action items
- **Response Parsing:** Parse AI responses into structured data (summary, key_points, action_items)
- **Fallback Handling:** Graceful degradation if AI service is unavailable
- **Rate Limiting:** Implement proper rate limiting and retry logic for API calls

**EmailSummary Structure:**
```python
@dataclass
class EmailSummary:
    subject: str
    sender: str
    date: str
    key_points: List[str]
    action_items: List[str]
    summary: str
```

### 5. YAML Writer (`storage/yaml_writer.py`)

**Purpose:** Manages daily summary file creation and updates

**Key Methods:**
- `write_daily_summary(summaries: List[EmailSummary], date: str)`
- `append_to_existing_summary(summaries: List[EmailSummary], date: str)`
- `create_empty_summary_file(date: str)`

**YAML Structure:**
```yaml
date: "2024-01-15"
processed_at: "2024-01-15T10:30:00Z"
email_count: 3
emails:
  - subject: "Project Update Required"
    sender: "manager@company.com"
    date: "2024-01-15T09:15:00Z"
    summary: "Brief summary of email content"
    key_points:
      - "Point 1"
      - "Point 2"
    action_items:
      - "Action required by Friday"
```

### 6. Main Application (`main.py`)

**Purpose:** Orchestrates the entire workflow and provides CLI interface

**Key Functions:**
- `main()` - Entry point
- `process_emails()` - Main workflow orchestration
- `handle_errors()` - Error handling and logging

## Data Models

### Configuration Settings
```python
@dataclass
class Config:
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    output_directory: str = "email_summaries"
    max_emails_per_run: int = 50
    
    # AI Summarization Settings
    ai_provider: str = "openai"  # "openai" or "claude"
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    claude_api_key: str = ""
    claude_model: str = "claude-3-haiku-20240307"
    max_tokens: int = 500
    temperature: float = 0.3
```

### Email Processing Pipeline
1. **Authentication** → Gmail Service Object
2. **Email Fetching** → Raw Email Data
3. **Content Extraction** → Structured Email Data
4. **Summarization** → Email Summaries
5. **Storage** → YAML File

## Error Handling

### Authentication Errors
- **Invalid Credentials:** Clear error message with setup instructions
- **Token Expiry:** Automatic token refresh or re-authentication prompt
- **API Quota Exceeded:** Graceful degradation with retry logic

### Email Processing Errors
- **Malformed Emails:** Skip problematic emails, log warnings
- **Network Issues:** Retry with exponential backoff
- **Content Extraction Failures:** Use fallback extraction methods

### AI Service Errors
- **API Key Issues:** Clear error messages about missing or invalid API keys
- **Rate Limiting:** Implement exponential backoff and respect rate limits
- **Service Unavailable:** Fallback to basic text extraction when AI services fail
- **Token Limits:** Handle content that exceeds model token limits by truncating intelligently
- **Parsing Errors:** Robust parsing of AI responses with fallback to partial data

### File System Errors
- **Permission Issues:** Clear error messages about file access
- **Disk Space:** Check available space before writing
- **Invalid YAML:** Validate structure before writing

## Testing Strategy

Since this is a proof of concept, testing will be limited to manual verification:
- Manual testing with real Gmail account
- Verification of YAML output format
- Basic error scenario testing

### Dependencies
```
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.5.0
PyYAML>=6.0
beautifulsoup4>=4.9.0  # For HTML content extraction
python-dateutil>=2.8.0
openai>=1.0.0  # For OpenAI API integration
anthropic>=0.7.0  # For Claude API integration
requests>=2.28.0  # For HTTP requests
```

### AI Summarization Implementation Details

**AI-Powered Approach:**
The summarization leverages advanced language models for high-quality summaries:

1. **Provider Configuration:** Support for both OpenAI and Claude APIs with configurable models
2. **Structured Prompting:** Use carefully crafted prompts to extract:
   - Concise summary (2-3 sentences)
   - Key points (bullet list)
   - Action items with deadlines
   - Priority level assessment
3. **Response Processing:** Parse structured AI responses into EmailSummary objects
4. **Error Handling:** Fallback to basic text extraction if AI service fails
5. **Cost Management:** Token counting and rate limiting to manage API costs

**Example AI Prompt:**
```
Analyze this email and provide a structured summary:

Subject: {subject}
From: {sender}
Content: {body}

Please respond with:
SUMMARY: [2-3 sentence summary]
KEY_POINTS: [bullet list of main points]
ACTION_ITEMS: [specific actions needed with deadlines if mentioned]
PRIORITY: [High/Medium/Low based on urgency indicators]
```

## Security Considerations

- **Credential Storage:** OAuth2 tokens stored securely with appropriate file permissions
- **API Scopes:** Minimal required scopes (gmail.readonly)
- **Data Handling:** No sensitive email content logged or cached
- **File Permissions:** Summary files created with restricted access (600)
- **API Key Security:** AI service API keys stored in environment variables or secure config
- **Data Privacy:** Email content sent to AI services - ensure compliance with privacy policies
- **Network Security:** Use HTTPS for all API communications
- **Logging:** Avoid logging sensitive content or API keys