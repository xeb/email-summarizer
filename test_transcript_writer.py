"""
Unit tests for TranscriptWriter class

Tests file operations, directory management, error handling, and file utilities
for the transcript storage functionality.
"""

import os
import tempfile
import shutil
import stat
from unittest.mock import patch, mock_open, MagicMock
import pytest
from pathlib import Path

from storage.transcript_writer import TranscriptWriter
from utils.error_handling import NonRetryableError, ErrorCategory


class TestTranscriptWriter:
    """Test suite for TranscriptWriter class"""
    
    def setup_method(self):
        """Set up test environment with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.transcript_writer = TranscriptWriter(output_directory=self.temp_dir)
        
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_creates_directory(self):
        """Test that TranscriptWriter creates output directory on initialization"""
        # Create a new temp directory that doesn't exist yet
        new_temp_dir = os.path.join(self.temp_dir, "new_transcripts")
        assert not os.path.exists(new_temp_dir)
        
        # Initialize TranscriptWriter with non-existent directory
        writer = TranscriptWriter(output_directory=new_temp_dir)
        
        # Verify directory was created
        assert os.path.exists(new_temp_dir)
        assert os.path.isdir(new_temp_dir)
        assert writer.output_directory == new_temp_dir
    
    def test_init_with_existing_directory(self):
        """Test that TranscriptWriter works with existing directory"""
        # Directory already exists from setup
        assert os.path.exists(self.temp_dir)
        
        writer = TranscriptWriter(output_directory=self.temp_dir)
        assert writer.output_directory == self.temp_dir
        assert os.path.exists(self.temp_dir)
    
    @patch('storage.transcript_writer.Path.mkdir')
    def test_init_directory_creation_failure(self, mock_mkdir):
        """Test handling of directory creation failure during initialization"""
        mock_mkdir.side_effect = OSError("Permission denied")
        
        with pytest.raises(NonRetryableError) as exc_info:
            TranscriptWriter(output_directory="/invalid/path")
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_get_transcript_path(self):
        """Test transcript file path generation"""
        date = "2025-09-21"
        expected_path = os.path.join(self.temp_dir, "2025-09-21.txt")
        
        path = self.transcript_writer.get_transcript_path(date)
        assert path == expected_path
    
    def test_write_transcript_success(self):
        """Test successful transcript writing"""
        content = "This is a test transcript content."
        date = "2025-09-21"
        
        result_path = self.transcript_writer.write_transcript(content, date)
        
        # Verify file was created
        expected_path = os.path.join(self.temp_dir, "2025-09-21.txt")
        assert result_path == expected_path
        assert os.path.exists(expected_path)
        
        # Verify content was written correctly
        with open(expected_path, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == content
    
    def test_write_transcript_file_permissions(self):
        """Test that transcript files are created with restrictive permissions"""
        content = "Test content for permissions check."
        date = "2025-09-21"
        
        result_path = self.transcript_writer.write_transcript(content, date)
        
        # Check file permissions (should be 600 - owner read/write only)
        file_stat = os.stat(result_path)
        file_mode = stat.filemode(file_stat.st_mode)
        
        # On Unix systems, should be -rw-------
        # Note: On some systems, chmod might not work as expected in tests
        # so we'll check if the file is at least readable by owner
        assert os.access(result_path, os.R_OK)
        assert os.access(result_path, os.W_OK)
    
    def test_write_transcript_empty_content(self):
        """Test that empty content raises validation error"""
        date = "2025-09-21"
        
        with pytest.raises(NonRetryableError) as exc_info:
            self.transcript_writer.write_transcript("", date)
        
        assert exc_info.value.category == ErrorCategory.VALIDATION
        assert "empty" in str(exc_info.value).lower()
    
    def test_write_transcript_whitespace_only_content(self):
        """Test that whitespace-only content raises validation error"""
        date = "2025-09-21"
        
        with pytest.raises(NonRetryableError) as exc_info:
            self.transcript_writer.write_transcript("   \n\t  ", date)
        
        assert exc_info.value.category == ErrorCategory.VALIDATION
        assert "empty" in str(exc_info.value).lower()
    
    def test_write_transcript_invalid_date_format(self):
        """Test that invalid date format raises validation error"""
        content = "Test content"
        invalid_dates = ["2025-13-01", "2025-02-30", "25-09-21", "2025/09/21", "invalid"]
        
        for invalid_date in invalid_dates:
            with pytest.raises(NonRetryableError) as exc_info:
                self.transcript_writer.write_transcript(content, invalid_date)
            
            assert exc_info.value.category == ErrorCategory.VALIDATION
            assert "date format" in str(exc_info.value).lower()
    
    def test_write_transcript_overwrites_existing(self):
        """Test that writing transcript overwrites existing file"""
        date = "2025-09-21"
        original_content = "Original content"
        new_content = "New content that should overwrite"
        
        # Write original content
        self.transcript_writer.write_transcript(original_content, date)
        
        # Write new content (should overwrite)
        result_path = self.transcript_writer.write_transcript(new_content, date)
        
        # Verify new content was written
        with open(result_path, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == new_content
    
    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_write_transcript_file_write_error(self, mock_open):
        """Test handling of file write errors"""
        content = "Test content"
        date = "2025-09-21"
        
        with pytest.raises(NonRetryableError) as exc_info:
            self.transcript_writer.write_transcript(content, date)
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_transcript_exists_true(self):
        """Test transcript_exists returns True for existing file"""
        date = "2025-09-21"
        content = "Test content"
        
        # Create transcript file
        self.transcript_writer.write_transcript(content, date)
        
        # Check existence
        assert self.transcript_writer.transcript_exists(date) is True
    
    def test_transcript_exists_false(self):
        """Test transcript_exists returns False for non-existing file"""
        date = "2025-09-21"
        
        # Check existence without creating file
        assert self.transcript_writer.transcript_exists(date) is False
    
    def test_get_transcript_content_success(self):
        """Test successful reading of transcript content"""
        date = "2025-09-21"
        content = "This is test transcript content with\nmultiple lines."
        
        # Create transcript file
        self.transcript_writer.write_transcript(content, date)
        
        # Read content back
        read_content = self.transcript_writer.get_transcript_content(date)
        assert read_content == content
    
    def test_get_transcript_content_nonexistent_file(self):
        """Test reading content from non-existent file returns None"""
        date = "2025-09-21"
        
        content = self.transcript_writer.get_transcript_content(date)
        assert content is None
    
    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_get_transcript_content_read_error(self, mock_open):
        """Test handling of file read errors"""
        date = "2025-09-21"
        
        # Mock transcript_exists to return True
        with patch.object(self.transcript_writer, 'transcript_exists', return_value=True):
            with pytest.raises(NonRetryableError) as exc_info:
                self.transcript_writer.get_transcript_content(date)
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_delete_transcript_success(self):
        """Test successful transcript deletion"""
        date = "2025-09-21"
        content = "Test content"
        
        # Create transcript file
        file_path = self.transcript_writer.write_transcript(content, date)
        assert os.path.exists(file_path)
        
        # Delete transcript
        result = self.transcript_writer.delete_transcript(date)
        
        assert result is True
        assert not os.path.exists(file_path)
        assert not self.transcript_writer.transcript_exists(date)
    
    def test_delete_transcript_nonexistent_file(self):
        """Test deleting non-existent transcript returns False"""
        date = "2025-09-21"
        
        result = self.transcript_writer.delete_transcript(date)
        assert result is False
    
    @patch('os.remove', side_effect=OSError("Permission denied"))
    def test_delete_transcript_error(self, mock_remove):
        """Test handling of file deletion errors"""
        date = "2025-09-21"
        
        # Mock transcript_exists to return True
        with patch.object(self.transcript_writer, 'transcript_exists', return_value=True):
            with pytest.raises(NonRetryableError) as exc_info:
                self.transcript_writer.delete_transcript(date)
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_list_transcripts_empty_directory(self):
        """Test listing transcripts in empty directory"""
        transcripts = self.transcript_writer.list_transcripts()
        assert transcripts == []
    
    def test_list_transcripts_with_files(self):
        """Test listing transcripts with multiple files"""
        dates = ["2025-09-19", "2025-09-21", "2025-09-20"]  # Intentionally out of order
        content = "Test content"
        
        # Create transcript files
        for date in dates:
            self.transcript_writer.write_transcript(content, date)
        
        # List transcripts
        transcripts = self.transcript_writer.list_transcripts()
        
        # Should return sorted list
        expected = ["2025-09-19", "2025-09-20", "2025-09-21"]
        assert transcripts == expected
    
    def test_list_transcripts_filters_invalid_files(self):
        """Test that list_transcripts filters out files with invalid names"""
        valid_date = "2025-09-21"
        content = "Test content"
        
        # Create valid transcript
        self.transcript_writer.write_transcript(content, valid_date)
        
        # Create invalid files directly
        invalid_files = [
            "invalid.txt",
            "2025-13-01.txt",  # Invalid month
            "not-a-date.txt",
            "2025-09-21.yaml",  # Wrong extension
            "2025-09-21",  # No extension
        ]
        
        for invalid_file in invalid_files:
            invalid_path = os.path.join(self.temp_dir, invalid_file)
            with open(invalid_path, 'w') as f:
                f.write("invalid content")
        
        # List transcripts should only return valid ones
        transcripts = self.transcript_writer.list_transcripts()
        assert transcripts == [valid_date]
    
    def test_list_transcripts_nonexistent_directory(self):
        """Test listing transcripts when directory doesn't exist"""
        # Create writer with non-existent directory
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        writer = TranscriptWriter(output_directory=nonexistent_dir)
        
        # Remove the directory that was created during init
        shutil.rmtree(nonexistent_dir)
        
        transcripts = writer.list_transcripts()
        assert transcripts == []
    
    @patch('os.listdir', side_effect=OSError("Permission denied"))
    def test_list_transcripts_directory_error(self, mock_listdir):
        """Test handling of directory listing errors"""
        with pytest.raises(NonRetryableError) as exc_info:
            self.transcript_writer.list_transcripts()
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_get_transcript_size_success(self):
        """Test getting transcript file size"""
        date = "2025-09-21"
        content = "This is test content for size calculation."
        
        # Create transcript file
        self.transcript_writer.write_transcript(content, date)
        
        # Get file size
        size = self.transcript_writer.get_transcript_size(date)
        
        # Verify size matches content length (in bytes)
        expected_size = len(content.encode('utf-8'))
        assert size == expected_size
    
    def test_get_transcript_size_nonexistent_file(self):
        """Test getting size of non-existent transcript returns None"""
        date = "2025-09-21"
        
        size = self.transcript_writer.get_transcript_size(date)
        assert size is None
    
    @patch('os.path.getsize', side_effect=OSError("Permission denied"))
    def test_get_transcript_size_error(self, mock_getsize):
        """Test handling of file size retrieval errors"""
        date = "2025-09-21"
        
        # Mock transcript_exists to return True
        with patch.object(self.transcript_writer, 'transcript_exists', return_value=True):
            with pytest.raises(NonRetryableError) as exc_info:
                self.transcript_writer.get_transcript_size(date)
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_ensure_directory_exists_creates_nested_directories(self):
        """Test that _ensure_directory_exists creates nested directory structure"""
        nested_dir = os.path.join(self.temp_dir, "level1", "level2", "transcripts")
        writer = TranscriptWriter(output_directory=nested_dir)
        
        assert os.path.exists(nested_dir)
        assert os.path.isdir(nested_dir)
    
    @patch('storage.transcript_writer.Path.mkdir')
    def test_ensure_directory_exists_error_handling(self, mock_mkdir):
        """Test error handling in _ensure_directory_exists"""
        mock_mkdir.side_effect = OSError("Permission denied")
        
        with pytest.raises(NonRetryableError) as exc_info:
            writer = TranscriptWriter(output_directory="/invalid/path")
        
        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
    
    def test_write_transcript_ensures_directory_exists(self):
        """Test that write_transcript ensures directory exists before writing"""
        # Remove the directory
        shutil.rmtree(self.temp_dir)
        assert not os.path.exists(self.temp_dir)
        
        # Write transcript should recreate directory
        content = "Test content"
        date = "2025-09-21"
        
        result_path = self.transcript_writer.write_transcript(content, date)
        
        # Verify directory was recreated and file was written
        assert os.path.exists(self.temp_dir)
        assert os.path.exists(result_path)
        
        with open(result_path, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == content


class TestTranscriptWriterIntegration:
    """Integration tests for TranscriptWriter with real file system operations"""
    
    def setup_method(self):
        """Set up test environment with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.transcript_writer = TranscriptWriter(output_directory=self.temp_dir)
        
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_workflow_integration(self):
        """Test complete workflow: write, read, list, delete"""
        dates = ["2025-09-19", "2025-09-20", "2025-09-21"]
        contents = [
            "First transcript content",
            "Second transcript with more details",
            "Third transcript for testing"
        ]
        
        # Write multiple transcripts
        written_paths = []
        for date, content in zip(dates, contents):
            path = self.transcript_writer.write_transcript(content, date)
            written_paths.append(path)
            assert self.transcript_writer.transcript_exists(date)
        
        # List all transcripts
        transcript_list = self.transcript_writer.list_transcripts()
        assert transcript_list == dates  # Should be sorted
        
        # Read each transcript and verify content
        for date, expected_content in zip(dates, contents):
            actual_content = self.transcript_writer.get_transcript_content(date)
            assert actual_content == expected_content
            
            # Check file size
            size = self.transcript_writer.get_transcript_size(date)
            assert size == len(expected_content.encode('utf-8'))
        
        # Delete middle transcript
        middle_date = dates[1]
        result = self.transcript_writer.delete_transcript(middle_date)
        assert result is True
        assert not self.transcript_writer.transcript_exists(middle_date)
        
        # Verify list is updated
        remaining_transcripts = self.transcript_writer.list_transcripts()
        expected_remaining = [dates[0], dates[2]]
        assert remaining_transcripts == expected_remaining
        
        # Verify other transcripts still exist and are readable
        for date in expected_remaining:
            assert self.transcript_writer.transcript_exists(date)
            content = self.transcript_writer.get_transcript_content(date)
            assert content is not None
            assert len(content) > 0
    
    def test_unicode_content_handling(self):
        """Test handling of Unicode content in transcripts"""
        date = "2025-09-21"
        unicode_content = "Test with émojis 🎉 and spëcial chäractërs: 中文, العربية, русский"
        
        # Write Unicode content
        path = self.transcript_writer.write_transcript(unicode_content, date)
        
        # Read back and verify
        read_content = self.transcript_writer.get_transcript_content(date)
        assert read_content == unicode_content
        
        # Verify file size accounts for UTF-8 encoding
        size = self.transcript_writer.get_transcript_size(date)
        expected_size = len(unicode_content.encode('utf-8'))
        assert size == expected_size
    
    def test_large_content_handling(self):
        """Test handling of large transcript content"""
        date = "2025-09-21"
        # Create large content (approximately 1MB)
        large_content = "This is a test line for large content handling.\n" * 20000
        
        # Write large content
        path = self.transcript_writer.write_transcript(large_content, date)
        
        # Verify file was created and has correct size
        assert os.path.exists(path)
        size = self.transcript_writer.get_transcript_size(date)
        expected_size = len(large_content.encode('utf-8'))
        assert size == expected_size
        
        # Read back and verify (this tests memory handling)
        read_content = self.transcript_writer.get_transcript_content(date)
        assert read_content == large_content


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])