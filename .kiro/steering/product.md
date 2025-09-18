# Gmail Email Summarizer

A Python command-line tool that automatically connects to Gmail, identifies important unread emails, and generates AI-powered daily summaries stored in structured YAML files.

## Core Features

- **Gmail Integration**: OAuth2 authentication with read-only access to Gmail
- **Smart Email Filtering**: Focuses on emails marked as both important and unread
- **Custom Search Configurations**: Save and manage custom Gmail search queries with full Gmail search operator support
- **AI-Powered Summarization**: Uses OpenAI GPT or Claude to generate structured summaries with key points and action items
- **Structured Storage**: Saves summaries in daily YAML files with metadata
- **CLI Interface**: Full command-line interface with comprehensive workflow orchestration

## Target Use Cases

- Daily email digest automation for busy professionals
- Important email monitoring and summarization
- Custom email filtering and processing workflows
- Automated email content extraction and analysis

## Architecture Philosophy

- **Modular Design**: Clean separation of concerns across auth, fetching, processing, summarization, and storage
- **Error Handling**: Comprehensive error handling with user-friendly messages and graceful degradation
- **Backward Compatibility**: Graceful migration support for configuration changes
- **Security First**: Secure credential management and minimal required permissions