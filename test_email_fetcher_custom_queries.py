"""
Unit tests for EmailFetcher custom query functionality.

This module tests the new custom query features added to the EmailFetcher class,
including query validation and the fetch_emails_with_query method.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
from googleapiclient.errors import HttpError

from gmail_email.fetcher import EmailFetcher, QueryValidationError, EmailFetchError
from utils.error_handling import RetryableError, NonRetryableError, ErrorCategory


class TestEmailFetcherQueryValidation(unittest.TestCase):
    """Test Gmail query validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.fetcher = EmailFetcher(self.mock_service)
    
    def test_validate_gmail_query_valid_queries(self):
        """Test validation of valid Gmail queries."""
        valid_queries = [
            "from:sender@domain.com",
            "to:recipient@domain.com",
            "subject:test",
            "is:unread",
            "is:important",
            "has:attachment",
            "after:2024-01-01",
            "before:2024-12-31",
            "newer_than:7d",
            "older_than:1m",
            "larger:10M",
            "smaller:5K",
            "from:sender@domain.com is:unread",
            "subject:\"test message\" has:attachment",
            "from:@company.com after:2024-01-01 is:important",
            "in:inbox is:unread newer_than:3d"
        ]
        
        for query in valid_queries:
            with self.subTest(query=query):
                is_valid, error_msg = self.fetcher.validate_gmail_query(query)
                self.assertTrue(is_valid, f"Query '{query}' should be valid but got error: {error_msg}")
                self.assertEqual(error_msg, "")
    
    def test_validate_gmail_query_invalid_queries(self):
        """Test validation of invalid Gmail queries."""
        invalid_queries = [
            ("", "Query cannot be empty"),
            ("   ", "Query cannot be empty"),
            ('subject:"unclosed quote', "Unmatched quotes in query"),
            ("invalid_operator:value", "Unsupported search operator 'invalid_operator:'"),
            ("is:invalid_value", "Invalid value 'invalid_value' for 'is:' operator"),
            ("has:invalid_attachment", "Invalid value 'invalid_attachment' for 'has:' operator"),
            ("in:invalid_location", "Invalid value 'invalid_location' for 'in:' operator"),
            ("after:invalid-date", "Invalid date format 'invalid-date' for 'after:' operator"),
            ("newer_than:invalid", "Invalid relative date format 'invalid' for 'newer_than:' operator"),
            ("larger:invalid", "Invalid size format 'invalid' for 'larger:' operator")
        ]
        
        for query, expected_error in invalid_queries:
            with self.subTest(query=query):
                is_valid, error_msg = self.fetcher.validate_gmail_query(query)
                self.assertFalse(is_valid, f"Query '{query}' should be invalid")
                self.assertIn(expected_error, error_msg)
    
    def test_validate_date_format(self):
        """Test date format validation."""
        valid_dates = ["2024-01-01", "2024/01/01", "2024-1-1", "2024/1/1", "2024-01", "2024/01", "2024"]
        invalid_dates = ["24-01-01", "2024-13-01", "2024-01-32", "invalid", "2024/01/01/01"]
        
        for date in valid_dates:
            with self.subTest(date=date):
                self.assertTrue(self.fetcher._validate_date_format(date))
        
        for date in invalid_dates:
            with self.subTest(date=date):
                self.assertFalse(self.fetcher._validate_date_format(date))
    
    def test_validate_relative_date_format(self):
        """Test relative date format validation."""
        valid_dates = ["7d", "2w", "1m", "1y", "30d", "12m"]
        invalid_dates = ["7", "d", "7days", "2weeks", "invalid", "7D"]
        
        for date in valid_dates:
            with self.subTest(date=date):
                self.assertTrue(self.fetcher._validate_relative_date_format(date))
        
        for date in invalid_dates:
            with self.subTest(date=date):
                self.assertFalse(self.fetcher._validate_relative_date_format(date))
    
    def test_validate_size_format(self):
        """Test size format validation."""
        valid_sizes = ["10M", "5K", "1G", "100", "10m", "5k", "1g"]
        invalid_sizes = ["10MB", "5KB", "1GB", "invalid", "10.5M", ""]
        
        for size in valid_sizes:
            with self.subTest(size=size):
                self.assertTrue(self.fetcher._validate_size_format(size))
        
        for size in invalid_sizes:
            with self.subTest(size=size):
                self.assertFalse(self.fetcher._validate_size_format(size))


class TestEmailFetcherCustomQueries(unittest.TestCase):
    """Test custom query functionality in EmailFetcher."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.fetcher = EmailFetcher(self.mock_service)
        
        # Mock the _get_message_ids and get_email_content methods
        self.fetcher._get_message_ids = Mock()
        self.fetcher.get_email_content = Mock()
    
    def test_fetch_emails_with_query_success(self):
        """Test successful email fetching with custom query."""
        # Setup mocks
        query = "from:test@example.com is:unread"
        message_ids = ["msg1", "msg2", "msg3"]
        email_data = [
            {"message_id": "msg1", "subject": "Test 1", "sender": "test@example.com"},
            {"message_id": "msg2", "subject": "Test 2", "sender": "test@example.com"},
            {"message_id": "msg3", "subject": "Test 3", "sender": "test@example.com"}
        ]
        
        self.fetcher._get_message_ids.return_value = message_ids
        self.fetcher.get_email_content.side_effect = email_data
        
        # Execute
        result = self.fetcher.fetch_emails_with_query(query, max_results=10)
        
        # Verify
        self.assertEqual(len(result), 3)
        self.fetcher._get_message_ids.assert_called_once_with(query, 10)
        self.assertEqual(self.fetcher.get_email_content.call_count, 3)
        
        for i, email in enumerate(result):
            self.assertEqual(email["message_id"], f"msg{i+1}")
            self.assertEqual(email["sender"], "test@example.com")
    
    def test_fetch_emails_with_query_invalid_query(self):
        """Test fetch_emails_with_query with invalid query."""
        invalid_query = "invalid_operator:value"
        
        with self.assertRaises(QueryValidationError) as context:
            self.fetcher.fetch_emails_with_query(invalid_query)
        
        self.assertIn("Invalid Gmail search query", str(context.exception))
        self.assertIn("Unsupported search operator", str(context.exception))
    
    def test_fetch_emails_with_query_no_results(self):
        """Test fetch_emails_with_query when no emails match."""
        query = "from:nonexistent@example.com"
        self.fetcher._get_message_ids.return_value = []
        
        result = self.fetcher.fetch_emails_with_query(query)
        
        self.assertEqual(result, [])
        self.fetcher._get_message_ids.assert_called_once_with(query, 50)
        self.fetcher.get_email_content.assert_not_called()
    
    def test_fetch_emails_with_query_partial_failure(self):
        """Test fetch_emails_with_query with some emails failing to fetch."""
        query = "from:test@example.com"
        message_ids = ["msg1", "msg2", "msg3"]
        
        self.fetcher._get_message_ids.return_value = message_ids
        
        # Mock get_email_content to succeed for some, fail for others
        def mock_get_email_content(msg_id):
            if msg_id == "msg2":
                raise RetryableError("Temporary failure", ErrorCategory.NETWORK)
            return {"message_id": msg_id, "subject": f"Test {msg_id}"}
        
        self.fetcher.get_email_content.side_effect = mock_get_email_content
        
        result = self.fetcher.fetch_emails_with_query(query)
        
        # Should return 2 emails (msg1 and msg3), skipping the failed msg2
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["message_id"], "msg1")
        self.assertEqual(result[1]["message_id"], "msg3")
    
    @patch('gmail_email.fetcher.handle_gmail_api_error')
    def test_fetch_emails_with_query_gmail_api_error(self, mock_handle_error):
        """Test fetch_emails_with_query with Gmail API error."""
        query = "from:test@example.com"
        
        # Mock Gmail API error
        http_error = HttpError(
            resp=Mock(status=403),
            content=b'{"error": {"code": 403, "message": "Forbidden"}}'
        )
        
        converted_error = NonRetryableError("API quota exceeded", ErrorCategory.API_QUOTA)
        mock_handle_error.return_value = converted_error
        
        self.fetcher._get_message_ids.side_effect = http_error
        
        with self.assertRaises(NonRetryableError):
            self.fetcher.fetch_emails_with_query(query)
        
        mock_handle_error.assert_called_once_with(http_error)
    
    def test_fetch_important_unread_emails_backward_compatibility(self):
        """Test that fetch_important_unread_emails still works and uses new method."""
        # Mock the fetch_emails_with_query method
        expected_emails = [{"message_id": "msg1", "subject": "Important email"}]
        
        with patch.object(self.fetcher, 'fetch_emails_with_query', return_value=expected_emails) as mock_fetch:
            result = self.fetcher.fetch_important_unread_emails(max_results=25)
            
            # Verify it calls the new method with the correct query
            mock_fetch.assert_called_once_with("is:important from:email@renweb.com", 25)
            self.assertEqual(result, expected_emails)


class TestEmailFetcherIntegration(unittest.TestCase):
    """Integration tests for EmailFetcher custom query functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.fetcher = EmailFetcher(self.mock_service)
    
    def test_complex_query_validation_and_execution(self):
        """Test complex query validation and execution flow."""
        complex_query = 'from:@company.com subject:"project update" has:attachment after:2024-01-01 is:unread'
        
        # Mock the internal methods that are actually called
        message_ids = ['msg1', 'msg2']
        email_data = [
            {"message_id": "msg1", "subject": "Project Update", "sender": "sender@company.com"},
            {"message_id": "msg2", "subject": "Project Update 2", "sender": "sender@company.com"}
        ]
        
        self.fetcher._get_message_ids = Mock(return_value=message_ids)
        self.fetcher.get_email_content = Mock(side_effect=email_data)
        
        # Execute
        result = self.fetcher.fetch_emails_with_query(complex_query, max_results=10)
        
        # Verify query was validated and executed
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # Verify internal methods were called with correct parameters
        self.fetcher._get_message_ids.assert_called_once_with(complex_query, 10)
        self.assertEqual(self.fetcher.get_email_content.call_count, 2)
        
        # Verify the returned data
        for i, email in enumerate(result):
            self.assertEqual(email["message_id"], f"msg{i+1}")
            self.assertIn("Project Update", email["subject"])


if __name__ == '__main__':
    unittest.main()