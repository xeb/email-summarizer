# Design Document

## Overview

The transcript summary generator feature extends the existing Gmail email summarization workflow by adding a post-processing step that combines individual email summaries into a cohesive, script-style narrative. This transcript will be optimized for AI voice synthesis, providing a natural-sounding daily briefing of important emails.

The feature integrates seamlessly into the existing architecture, leveraging the current AI summarization capabilities to create a secondary summary that transforms structured YAML data into conversational prose suitable for audio presentation.

## Architecture

### Integration Points

The transcript generator will integrate with the existing workflow at the following points:

1. **Post-Processing Hook**: After `YAMLWriter.write_daily_summary()` completes successfully
2. **AI Service Reuse**: Leverages the existing `EmailSummarizer` class for transcript generation
3. **Configuration Extension**: Extends the current `Config` class with transcript-specific settings
4. **CLI Integration**: Adds new command-line options to the existing argument parser

### Data Flow

```
Existing Workflow:
Gmail API → Email Processing → AI Summarization → YAML Storage

Extended Workflow:
Gmail API → Email Processing → AI Summarization → YAML Storage → Transcript Generation → Text File Storage
```

### Directory Structure

```
email_summaries/           # Existing YAML files
transcripts/              # New directory for transcript files
├── 2025-09-19.txt       # Daily transcript files
├── 2025-09-20.txt
└── ...
```

## Components and Interfaces

### 1. TranscriptGenerator Class

**Location**: `summarization/transcript_generator.py`

**Responsibilities**:
- Read email summaries from daily YAML files
- Generate conversational transcript using AI services
- Handle transcript formatting and structure
- Manage error handling and fallback scenarios

**Key Methods**:
```python
class TranscriptGenerator:
    def __init__(self, config: Config, summarizer: EmailSummarizer)
    def generate_transcript(self, yaml_file_path: str, date: str) -> str
    def _create_transcript_prompt(self, summaries: List[Dict]) -> str
    def _format_transcript_content(self, ai_response: str) -> str
    def _create_fallback_transcript(self, summaries: List[Dict]) -> str
```

### 2. TranscriptWriter Class

**Location**: `storage/transcript_writer.py`

**Responsibilities**:
- Manage transcript file creation and storage
- Handle file naming conventions and directory structure
- Provide transcript file utilities and metadata

**Key Methods**:
```python
class TranscriptWriter:
    def __init__(self, output_directory: str = "transcripts")
    def write_transcript(self, content: str, date: str) -> str
    def get_transcript_path(self, date: str) -> str
    def transcript_exists(self, date: str) -> bool
```

### 3. Configuration Extensions

**Location**: `config/settings.py`

**New Configuration Options**:
```python
# Transcript generation settings
enable_transcript_generation: bool = True
transcript_output_directory: str = "transcripts"
transcript_max_tokens: int = 1000
transcript_temperature: float = 0.7
```

### 4. CLI Integration

**Location**: `main.py`

**New Command-Line Options**:
- `--no-transcript`: Disable transcript generation
- `--transcript-only`: Generate transcript from existing YAML file
- `--transcript-date`: Specify date for transcript generation

## Data Models

### Transcript Content Structure

The transcript will follow a conversational format optimized for AI voice synthesis:

```
Good morning! Here's your email briefing for [date].

Today I processed [X] important emails for you.

[Opening summary of overall email activity]

Let me walk you through the key highlights:

[Email 1 narrative section]
[Transition phrase]
[Email 2 narrative section]
[Transition phrase]
...

To wrap up, here are the main action items for your attention:
[Consolidated action items]

That concludes your email briefing for today. Have a great day!
```

### AI Prompt Structure

The AI prompt will be designed to create natural, conversational flow:

```python
TRANSCRIPT_PROMPT = """
Create a conversational transcript for an AI host to read aloud as a daily email briefing.

Email Summaries:
{email_summaries}

Guidelines:
- Use natural, conversational language suitable for audio presentation
- Create smooth transitions between different emails
- Group related emails logically
- Maintain a professional but friendly tone
- Include a brief opening and closing
- Consolidate action items at the end
- Keep the total length appropriate for a 2-3 minute audio briefing
- Use phrases like "Let me tell you about..." and "Moving on to..."

Format as a script that flows naturally when read aloud.
"""
```

## Error Handling

### Graceful Degradation

1. **AI Service Failures**: Fall back to template-based transcript generation
2. **File System Errors**: Log errors but don't block main workflow
3. **YAML Parsing Errors**: Skip transcript generation with appropriate logging
4. **Empty Email Days**: Generate appropriate "no emails" transcript

### Error Recovery Strategies

```python
def generate_transcript_with_fallback(self, yaml_file_path: str, date: str) -> str:
    try:
        return self.generate_ai_transcript(yaml_file_path, date)
    except RetryableError as e:
        self.logger.warning(f"AI transcript generation failed, using fallback: {e}")
        return self.generate_template_transcript(yaml_file_path, date)
    except NonRetryableError as e:
        self.logger.error(f"Transcript generation failed: {e}")
        raise
```

### Fallback Template

When AI generation fails, use a structured template:

```python
FALLBACK_TEMPLATE = """
Good morning! Here's your email briefing for {date}.

I processed {email_count} important emails today.

{email_sections}

{action_items_section}

That's all for today's email briefing.
"""
```

## Testing Strategy

### Unit Tests

1. **TranscriptGenerator Tests**:
   - AI prompt generation
   - Response parsing and formatting
   - Fallback scenario handling
   - Error condition testing

2. **TranscriptWriter Tests**:
   - File creation and writing
   - Directory management
   - Path generation utilities
   - Permission handling

3. **Integration Tests**:
   - End-to-end transcript generation
   - CLI option handling
   - Configuration loading
   - Workflow integration

### Test Data

Create test YAML files with various scenarios:
- Single email day
- Multiple emails with different priorities
- Empty email day
- Malformed YAML data

### Mock Strategies

- Mock AI service responses for consistent testing
- Mock file system operations for error scenario testing
- Mock configuration loading for different settings

## Performance Considerations

### AI Service Usage

- Reuse existing `EmailSummarizer` instance to avoid re-initialization
- Implement appropriate rate limiting for transcript generation
- Use shorter, focused prompts to minimize token usage

### File System Optimization

- Check for existing transcript files before generation
- Use atomic file operations to prevent corruption
- Implement proper file locking if needed

### Memory Management

- Process YAML data efficiently without loading entire file into memory unnecessarily
- Clean up temporary data structures after transcript generation

## Security Considerations

### File Permissions

- Set restrictive permissions on transcript files (600)
- Ensure transcript directory has appropriate access controls
- Validate file paths to prevent directory traversal

### Data Handling

- Sanitize email content before including in transcripts
- Avoid logging sensitive email content
- Ensure transcript files are included in .gitignore

### AI Service Security

- Reuse existing secure AI client configurations
- Implement same retry and error handling patterns
- Maintain existing API key security practices