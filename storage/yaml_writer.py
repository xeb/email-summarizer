"""
YAML storage module for email summaries.

This module handles the creation and management of daily YAML files containing
email summaries, with support for appending to existing files and handling
empty summary scenarios.
"""

import os
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from summarization.summarizer import EmailSummary
from utils.error_handling import (
    NonRetryableError, ErrorCategory, handle_file_system_error,
    create_user_friendly_message
)


class YAMLWriter:
    """Manages daily summary file creation and updates in YAML format."""
    
    def __init__(self, output_directory: str = "email_summaries"):
        """
        Initialize the YAML writer with output directory.
        
        Args:
            output_directory: Directory where YAML files will be stored
        """
        self.output_directory = Path(output_directory)
        self.logger = logging.getLogger(__name__)
        
        # Create output directory if it doesn't exist
        self._ensure_output_directory()
    
    def _ensure_output_directory(self):
        """Create the output directory if it doesn't exist with comprehensive error handling."""
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory ensured: {self.output_directory}")
            
            # Test write permissions
            test_file = self.output_directory / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.logger.debug("Write permissions verified for output directory")
            except Exception as perm_error:
                error = handle_file_system_error(
                    perm_error, 
                    "testing write permissions in", 
                    str(self.output_directory)
                )
                self.logger.error(create_user_friendly_message(error, "verifying output directory permissions"))
                raise error
                
        except OSError as e:
            error = handle_file_system_error(e, "creating output directory", str(self.output_directory))
            self.logger.error(create_user_friendly_message(error, "creating output directory"))
            raise error
        except Exception as e:
            self.logger.error(f"Unexpected error creating output directory {self.output_directory}: {e}")
            raise NonRetryableError(
                f"Failed to create output directory: {e}",
                ErrorCategory.FILE_SYSTEM
            )
    
    def write_daily_summary(self, summaries: List[EmailSummary], date: Optional[str] = None) -> str:
        """
        Write email summaries to a daily YAML file with comprehensive error handling.
        
        Args:
            summaries: List of email summaries to write
            date: Date string in YYYY-MM-DD format (defaults to today)
            
        Returns:
            str: Path to the created/updated YAML file
            
        Raises:
            NonRetryableError: If file system operations fail
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            raise NonRetryableError(
                f"Invalid date format '{date}'. Expected YYYY-MM-DD format.",
                ErrorCategory.VALIDATION
            )
        
        file_path = self.output_directory / f"{date}.yaml"
        
        try:
            # Ensure output directory exists and is writable
            self._ensure_output_directory()
            
            if file_path.exists():
                self.logger.info(f"Appending to existing daily summary file: {file_path}")
                return self.append_to_existing_summary(summaries, date)
            else:
                self.logger.info(f"Creating new daily summary file: {file_path}")
                return self._create_new_summary_file(summaries, date)
                
        except NonRetryableError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            error = handle_file_system_error(e, "writing daily summary", str(file_path))
            self.logger.error(create_user_friendly_message(error, f"writing daily summary for {date}"))
            raise error
    
    def append_to_existing_summary(self, summaries: List[EmailSummary], date: str) -> str:
        """
        Append new summaries to an existing daily YAML file.
        
        Args:
            summaries: List of email summaries to append
            date: Date string in YYYY-MM-DD format
            
        Returns:
            str: Path to the updated YAML file
        """
        file_path = self.output_directory / f"{date}.yaml"
        
        try:
            # Load existing data
            existing_data = self._load_existing_yaml(file_path)
            
            # Convert new summaries to dict format
            new_emails = [self._summary_to_dict(summary) for summary in summaries]
            
            # Append new emails to existing list
            existing_data["emails"].extend(new_emails)
            
            # Update metadata
            existing_data["email_count"] = len(existing_data["emails"])
            existing_data["last_updated"] = datetime.now().isoformat()
            
            # Write updated data back to file
            self._write_yaml_file(file_path, existing_data)
            
            self.logger.info(f"Appended {len(summaries)} summaries to {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to append to existing summary file {file_path}: {e}")
            raise
    
    def create_empty_summary_file(self, date: Optional[str] = None) -> str:
        """
        Create an empty summary file when no emails are found.
        
        Args:
            date: Date string in YYYY-MM-DD format (defaults to today)
            
        Returns:
            str: Path to the created YAML file
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        file_path = self.output_directory / f"{date}.yaml"
        
        try:
            # Check if file already exists
            if file_path.exists():
                existing_data = self._load_existing_yaml(file_path)
                if existing_data["email_count"] > 0:
                    self.logger.info(f"Daily summary file already exists with emails: {file_path}")
                    return str(file_path)
                else:
                    self.logger.info(f"Updating existing empty summary file: {file_path}")
            
            # Create empty summary structure
            empty_data = {
                "date": date,
                "processed_at": datetime.now().isoformat(),
                "email_count": 0,
                "status": "No important unread emails found",
                "emails": []
            }
            
            self._write_yaml_file(file_path, empty_data)
            
            self.logger.info(f"Created empty summary file: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create empty summary file for {date}: {e}")
            raise
    
    def _create_new_summary_file(self, summaries: List[EmailSummary], date: str) -> str:
        """
        Create a new daily summary YAML file.
        
        Args:
            summaries: List of email summaries
            date: Date string in YYYY-MM-DD format
            
        Returns:
            str: Path to the created YAML file
        """
        file_path = self.output_directory / f"{date}.yaml"
        
        # Convert summaries to dict format
        emails_data = [self._summary_to_dict(summary) for summary in summaries]
        
        # Create summary structure
        summary_data = {
            "date": date,
            "processed_at": datetime.now().isoformat(),
            "email_count": len(summaries),
            "emails": emails_data
        }
        
        self._write_yaml_file(file_path, summary_data)
        
        self.logger.info(f"Created new summary file with {len(summaries)} emails: {file_path}")
        return str(file_path)
    
    def _load_existing_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Load existing YAML file data with comprehensive error handling.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dict containing the loaded YAML data
            
        Raises:
            NonRetryableError: If file cannot be loaded or is invalid
        """
        try:
            self.logger.debug(f"Loading existing YAML file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            # Handle empty file
            if data is None:
                self.logger.warning(f"YAML file is empty: {file_path}")
                data = {}
                
            # Ensure required structure exists
            if not isinstance(data, dict):
                raise NonRetryableError(
                    f"Invalid YAML structure in {file_path}: root must be a dictionary",
                    ErrorCategory.VALIDATION
                )
            
            if "emails" not in data:
                data["emails"] = []
                self.logger.debug("Added missing 'emails' field to YAML data")
            
            if "email_count" not in data:
                data["email_count"] = len(data["emails"])
                self.logger.debug("Added missing 'email_count' field to YAML data")
            
            # Validate emails structure
            if not isinstance(data["emails"], list):
                raise NonRetryableError(
                    f"Invalid YAML structure in {file_path}: 'emails' must be a list",
                    ErrorCategory.VALIDATION
                )
            
            self.logger.debug(f"Successfully loaded YAML file with {data['email_count']} emails")
            return data
            
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML format in {file_path}: {e}"
            self.logger.error(error_msg)
            raise NonRetryableError(error_msg, ErrorCategory.VALIDATION)
        except OSError as e:
            error = handle_file_system_error(e, "reading YAML file", str(file_path))
            self.logger.error(create_user_friendly_message(error, "loading existing YAML file"))
            raise error
        except NonRetryableError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error loading YAML file {file_path}: {e}"
            self.logger.error(error_msg)
            raise NonRetryableError(error_msg, ErrorCategory.UNKNOWN)
    
    def _write_yaml_file(self, file_path: Path, data: Dict[str, Any]):
        """
        Write data to YAML file with proper formatting and comprehensive error handling.
        
        Args:
            file_path: Path where to write the YAML file
            data: Data to write to the file
            
        Raises:
            NonRetryableError: If file cannot be written
        """
        try:
            self.logger.debug(f"Writing YAML file: {file_path}")
            
            # Validate data structure before writing
            if not isinstance(data, dict):
                raise NonRetryableError(
                    "Invalid data structure: must be a dictionary",
                    ErrorCategory.VALIDATION
                )
            
            # Create a backup if file exists
            backup_path = None
            if file_path.exists():
                backup_path = file_path.with_suffix('.yaml.backup')
                try:
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    self.logger.debug(f"Created backup: {backup_path}")
                except Exception as backup_error:
                    self.logger.warning(f"Could not create backup: {backup_error}")
            
            # Write the YAML file
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(
                    data,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    width=120
                )
            
            # Set appropriate file permissions (readable by owner only)
            try:
                os.chmod(file_path, 0o600)
                self.logger.debug("Set restrictive file permissions (600)")
            except OSError as perm_error:
                self.logger.warning(f"Could not set file permissions: {perm_error}")
            
            # Remove backup if write was successful
            if backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                    self.logger.debug("Removed backup file after successful write")
                except Exception as cleanup_error:
                    self.logger.warning(f"Could not remove backup file: {cleanup_error}")
            
            self.logger.debug(f"Successfully wrote YAML file: {file_path}")
            
        except yaml.YAMLError as e:
            error_msg = f"YAML serialization error for {file_path}: {e}"
            self.logger.error(error_msg)
            raise NonRetryableError(error_msg, ErrorCategory.VALIDATION)
        except OSError as e:
            error = handle_file_system_error(e, "writing YAML file", str(file_path))
            self.logger.error(create_user_friendly_message(error, "writing YAML file"))
            raise error
        except Exception as e:
            error_msg = f"Unexpected error writing YAML file {file_path}: {e}"
            self.logger.error(error_msg)
            raise NonRetryableError(error_msg, ErrorCategory.UNKNOWN)
    
    def _summary_to_dict(self, summary: EmailSummary) -> Dict[str, Any]:
        """
        Convert EmailSummary object to dictionary format for YAML serialization.
        
        Args:
            summary: EmailSummary object to convert
            
        Returns:
            Dict representation of the email summary
        """
        return {
            "subject": summary.subject,
            "sender": summary.sender,
            "date": summary.date,
            "summary": summary.summary,
            "key_points": summary.key_points,
            "action_items": summary.action_items,
            "priority": summary.priority
        }
    
    def get_daily_summary_path(self, date: Optional[str] = None) -> str:
        """
        Get the file path for a daily summary file.
        
        Args:
            date: Date string in YYYY-MM-DD format (defaults to today)
            
        Returns:
            str: Path to the daily summary file
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return str(self.output_directory / f"{date}.yaml")
    
    def file_exists(self, date: Optional[str] = None) -> bool:
        """
        Check if a daily summary file exists for the given date.
        
        Args:
            date: Date string in YYYY-MM-DD format (defaults to today)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        file_path = Path(self.get_daily_summary_path(date))
        return file_path.exists()
    
    def get_summary_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about a daily summary file.
        
        Args:
            date: Date string in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Dict containing file statistics
        """
        file_path = Path(self.get_daily_summary_path(date))
        
        if not file_path.exists():
            return {
                "exists": False,
                "email_count": 0,
                "file_size": 0,
                "last_modified": None
            }
        
        try:
            data = self._load_existing_yaml(file_path)
            stat = file_path.stat()
            
            return {
                "exists": True,
                "email_count": data.get("email_count", 0),
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "processed_at": data.get("processed_at"),
                "status": data.get("status", "Contains email summaries")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get summary stats for {date}: {e}")
            return {
                "exists": True,
                "email_count": 0,
                "file_size": 0,
                "last_modified": None,
                "error": str(e)
            }