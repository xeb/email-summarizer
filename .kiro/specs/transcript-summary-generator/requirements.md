# Requirements Document

## Introduction

This feature adds a transcript-style summary generation step to the existing Gmail email summarization workflow. After all individual emails have been processed and summarized into the daily YAML file, the system will generate an additional summary file that combines all email summaries into a cohesive, script-like overview designed for an AI host to read aloud.

## Requirements

### Requirement 1

**User Story:** As a user, I want the system to automatically generate a transcript-style summary after processing all emails, so that I can have an AI host read a cohesive overview of my daily email activity.

#### Acceptance Criteria

1. WHEN all emails have been summarized and stored in the daily YAML file THEN the system SHALL generate a transcript-style summary file
2. WHEN the transcript generation process starts THEN the system SHALL read all email summaries from the current day's YAML file
3. WHEN creating the transcript THEN the system SHALL combine individual email summaries into a flowing, narrative format suitable for audio presentation
4. WHEN the transcript is complete THEN the system SHALL save it as a separate file with a clear naming convention

### Requirement 2

**User Story:** As a user, I want the transcript summary to be stored in a predictable location and format, so that I can easily integrate it with AI voice systems.

#### Acceptance Criteria

1. WHEN the transcript is generated THEN the system SHALL save it in a dedicated directory structure
2. WHEN naming the transcript file THEN the system SHALL use a date-based naming convention consistent with existing YAML files
3. WHEN storing the transcript THEN the system SHALL use a text format optimized for speech synthesis
4. IF the transcript file already exists for the current date THEN the system SHALL overwrite it with the new content

### Requirement 3

**User Story:** As a user, I want the transcript to have a natural, conversational flow, so that it sounds professional when read by an AI host.

#### Acceptance Criteria

1. WHEN generating the transcript THEN the system SHALL create smooth transitions between different email summaries
2. WHEN structuring the content THEN the system SHALL organize emails by importance or logical grouping
3. WHEN writing the transcript THEN the system SHALL use conversational language appropriate for audio presentation
4. WHEN including email details THEN the system SHALL focus on key points and action items while maintaining readability
5. WHEN no emails are available THEN the system SHALL generate an appropriate "no important emails today" message

### Requirement 4

**User Story:** As a user, I want the transcript generation to be integrated into the existing workflow, so that it happens automatically without additional manual steps.

#### Acceptance Criteria

1. WHEN the daily email summarization process completes successfully THEN the system SHALL automatically trigger transcript generation
2. WHEN transcript generation fails THEN the system SHALL log the error but NOT prevent the main summarization workflow from completing
3. WHEN running with verbose logging THEN the system SHALL provide clear status updates about transcript generation progress
4. WHEN the transcript generation step is skipped due to errors THEN the system SHALL continue normal operation and inform the user

### Requirement 5

**User Story:** As a user, I want to be able to control transcript generation through CLI options, so that I can enable or disable this feature as needed.

#### Acceptance Criteria

1. WHEN running the main command THEN the system SHALL generate transcripts by default
2. WHEN a user provides a disable transcript flag THEN the system SHALL skip transcript generation
3. WHEN testing or debugging THEN the system SHALL support transcript generation for existing YAML files
4. WHEN using the help command THEN the system SHALL display information about transcript-related options