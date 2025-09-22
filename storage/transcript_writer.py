"""
Transcript Writer Module

Handles transcript file creation, storage, and management with date-based naming
conventions and comprehensive error handling.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from utils.error_handling import (
    NonRetryableError, ErrorCategory, handle_file_system_error,
    create_user_friendly_message
)


class TranscriptWriter:
    """
    Manages transcript file creation and storage with proper directory management
    and file utilities.
    """
    
    def __init__(self, output_directory: str = "transcripts"):
        """
        Initialize TranscriptWriter with specified output directory.
        
        Args:
            output_directory: Directory to store transcript files (default: "transcripts")
        """
        self.output_directory = output_directory
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """
        Create the transcript output directory if it doesn't exist.
        
        Raises:
            NonRetryableError: If directory creation fails due to permissions or other issues
        """
        try:
            Path(self.output_directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured transcript directory exists: {self.output_directory}")
        except OSError as e:
            error = handle_file_system_error(e, "creating directory", self.output_directory)
            self.logger.error(f"Failed to create transcript directory: {create_user_friendly_message(error)}")
            raise error
    
    def write_transcript(self, content: str, date: str) -> str:
        """
        Write transcript content to a file with date-based naming convention.
        
        Args:
            content: The transcript content to write
            date: Date string in YYYY-MM-DD format
            
        Returns:
            str: Full path to the created transcript file
            
        Raises:
            NonRetryableError: If date format is invalid or file writing fails
        """
        # Validate content
        if not content or not content.strip():
            raise NonRetryableError(
                "Transcript content cannot be empty or whitespace-only",
                ErrorCategory.VALIDATION
            )
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            raise NonRetryableError(
                f"Invalid date format '{date}'. Expected YYYY-MM-DD format",
                ErrorCategory.VALIDATION
            ) from e
        
        transcript_path = self.get_transcript_path(date)
        
        try:
            # Ensure directory exists before writing
            self._ensure_directory_exists()
            
            # Write transcript with proper file permissions (readable by owner only)
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Set restrictive file permissions (600 - owner read/write only)
            try:
                os.chmod(transcript_path, 0o600)
            except OSError as chmod_error:
                # Log warning but don't fail - file was written successfully
                self.logger.warning(f"Could not set file permissions for {transcript_path}: {chmod_error}")
            
            self.logger.info(f"Successfully wrote transcript to: {transcript_path}")
            return transcript_path
            
        except OSError as e:
            error = handle_file_system_error(e, "writing transcript file", transcript_path)
            self.logger.error(f"Failed to write transcript: {create_user_friendly_message(error)}")
            raise error
    
    def get_transcript_path(self, date: str) -> str:
        """
        Generate the full file path for a transcript based on date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            str: Full path to the transcript file
        """
        filename = f"{date}.txt"
        return os.path.join(self.output_directory, filename)
    
    def transcript_exists(self, date: str) -> bool:
        """
        Check if a transcript file already exists for the given date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            bool: True if transcript file exists, False otherwise
        """
        transcript_path = self.get_transcript_path(date)
        exists = os.path.isfile(transcript_path)
        
        if exists:
            self.logger.debug(f"Transcript file exists: {transcript_path}")
        else:
            self.logger.debug(f"Transcript file does not exist: {transcript_path}")
            
        return exists
    
    def get_transcript_content(self, date: str) -> Optional[str]:
        """
        Read and return the content of an existing transcript file.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            str: Content of the transcript file, or None if file doesn't exist
            
        Raises:
            NonRetryableError: If file reading fails due to permissions or other issues
        """
        transcript_path = self.get_transcript_path(date)
        
        if not self.transcript_exists(date):
            self.logger.debug(f"Transcript file does not exist: {transcript_path}")
            return None
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.logger.debug(f"Successfully read transcript from: {transcript_path}")
            return content
            
        except OSError as e:
            error = handle_file_system_error(e, "reading transcript file", transcript_path)
            self.logger.error(f"Failed to read transcript: {create_user_friendly_message(error)}")
            raise error
    
    def delete_transcript(self, date: str) -> bool:
        """
        Delete a transcript file for the given date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            bool: True if file was deleted, False if file didn't exist
            
        Raises:
            NonRetryableError: If file deletion fails due to permissions or other issues
        """
        transcript_path = self.get_transcript_path(date)
        
        if not self.transcript_exists(date):
            self.logger.debug(f"Transcript file does not exist, nothing to delete: {transcript_path}")
            return False
        
        try:
            os.remove(transcript_path)
            self.logger.info(f"Successfully deleted transcript: {transcript_path}")
            return True
            
        except OSError as e:
            error = handle_file_system_error(e, "deleting transcript file", transcript_path)
            self.logger.error(f"Failed to delete transcript: {create_user_friendly_message(error)}")
            raise error
    
    def list_transcripts(self) -> list[str]:
        """
        List all transcript files in the output directory.
        
        Returns:
            list[str]: List of dates (YYYY-MM-DD format) for which transcripts exist
            
        Raises:
            NonRetryableError: If directory listing fails due to permissions or other issues
        """
        if not os.path.exists(self.output_directory):
            self.logger.debug(f"Transcript directory does not exist: {self.output_directory}")
            return []
        
        transcripts = []
        try:
            for filename in os.listdir(self.output_directory):
                if filename.endswith('.txt') and len(filename) == 14:  # YYYY-MM-DD.txt
                    date_part = filename[:-4]  # Remove .txt extension
                    try:
                        # Validate date format
                        datetime.strptime(date_part, "%Y-%m-%d")
                        transcripts.append(date_part)
                    except ValueError:
                        # Skip files that don't match expected date format
                        self.logger.debug(f"Skipping file with invalid date format: {filename}")
                        continue
            
            transcripts.sort()  # Sort chronologically
            self.logger.debug(f"Found {len(transcripts)} transcript files")
            return transcripts
            
        except OSError as e:
            error = handle_file_system_error(e, "listing transcript files in directory", self.output_directory)
            self.logger.error(f"Failed to list transcripts: {create_user_friendly_message(error)}")
            raise error
    
    def get_transcript_size(self, date: str) -> Optional[int]:
        """
        Get the size of a transcript file in bytes.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            int: File size in bytes, or None if file doesn't exist
            
        Raises:
            NonRetryableError: If file stat operation fails
        """
        transcript_path = self.get_transcript_path(date)
        
        if not self.transcript_exists(date):
            self.logger.debug(f"Transcript file does not exist: {transcript_path}")
            return None
        
        try:
            size = os.path.getsize(transcript_path)
            self.logger.debug(f"Transcript file size: {size} bytes for {transcript_path}")
            return size
            
        except OSError as e:
            error = handle_file_system_error(e, "getting size of transcript file", transcript_path)
            self.logger.error(f"Failed to get transcript size: {create_user_friendly_message(error)}")
            raise error