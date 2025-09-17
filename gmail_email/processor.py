"""
Email content processing module for extracting and cleaning email data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
import re
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime


@dataclass
class EmailData:
    """Structured representation of email data."""
    subject: str
    sender: str
    date: datetime
    body: str
    message_id: str


class EmailProcessor:
    """Handles email content extraction and processing."""
    
    def extract_email_data(self, raw_email: Dict[str, Any]) -> EmailData:
        """
        Extract structured email data from Gmail API response.
        
        Args:
            raw_email: Raw email data from Gmail API
            
        Returns:
            EmailData: Structured email data
        """
        headers = self._extract_headers(raw_email)
        
        # Extract basic email metadata
        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', 'Unknown Sender')
        date_str = headers.get('Date', '')
        message_id = raw_email.get('id', '')
        
        # Parse date
        date = self._parse_email_date(date_str)
        
        # Extract email body content
        body = self._extract_body_content(raw_email)
        
        return EmailData(
            subject=subject,
            sender=sender,
            date=date,
            body=body,
            message_id=message_id
        )
    
    def _extract_headers(self, raw_email: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from raw email data."""
        headers = {}
        payload = raw_email.get('payload', {})
        header_list = payload.get('headers', [])
        
        for header in header_list:
            name = header.get('name', '')
            value = header.get('value', '')
            headers[name] = value
            
        return headers
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime object."""
        if not date_str:
            return datetime.now()
            
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            # Fallback to current time if parsing fails
            return datetime.now()
    
    def _extract_body_content(self, raw_email: Dict[str, Any]) -> str:
        """
        Extract body content from email, handling both plain text and HTML.
        
        Args:
            raw_email: Raw email data from Gmail API
            
        Returns:
            str: Cleaned email body content
        """
        payload = raw_email.get('payload', {})
        
        # Handle multipart emails
        if 'parts' in payload:
            return self._extract_from_parts(payload['parts'])
        
        # Handle single part emails
        return self._extract_single_part(payload)
    
    def _extract_from_parts(self, parts: List[Dict[str, Any]]) -> str:
        """Extract content from multipart email."""
        plain_text = ""
        html_content = ""
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                plain_text = self._decode_part_data(part)
            elif mime_type == 'text/html':
                html_content = self._decode_part_data(part)
            elif 'parts' in part:
                # Recursively handle nested parts
                nested_content = self._extract_from_parts(part['parts'])
                if nested_content:
                    return nested_content
        
        # Prefer plain text, fall back to cleaned HTML
        if plain_text:
            return self._clean_plain_text(plain_text)
        elif html_content:
            return self.clean_html_content(html_content)
        
        return "No readable content found"
    
    def _extract_single_part(self, payload: Dict[str, Any]) -> str:
        """Extract content from single part email."""
        mime_type = payload.get('mimeType', '')
        content = self._decode_part_data(payload)
        
        if mime_type == 'text/plain':
            return self._clean_plain_text(content)
        elif mime_type == 'text/html':
            return self.clean_html_content(content)
        
        return content if content else "No readable content found"
    
    def _decode_part_data(self, part: Dict[str, Any]) -> str:
        """Decode base64 encoded email part data."""
        body = part.get('body', {})
        data = body.get('data', '')
        
        if not data:
            return ""
        
        try:
            # Gmail API returns base64url encoded data
            decoded_bytes = base64.urlsafe_b64decode(data + '==')
            return decoded_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    def clean_html_content(self, html: str) -> str:
        """
        Clean HTML content and extract readable text.
        
        Args:
            html: Raw HTML content
            
        Returns:
            str: Cleaned plain text
        """
        if not html:
            return ""
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            return self._clean_plain_text(text)
            
        except Exception:
            # If HTML parsing fails, return original content
            return self._clean_plain_text(html)
    
    def _clean_plain_text(self, text: str) -> str:
        """
        Clean and normalize plain text content.
        
        Args:
            text: Raw text content
            
        Returns:
            str: Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Remove common email artifacts
        text = self._remove_email_artifacts(text)
        
        return text
    
    def _remove_email_artifacts(self, text: str) -> str:
        """Remove common email artifacts and signatures."""
        # Remove common email signatures patterns
        patterns = [
            r'--\s*\n.*$',  # Standard email signature delimiter
            r'Sent from my \w+.*$',  # Mobile signatures
            r'Get Outlook for \w+.*$',  # Outlook mobile signatures
            r'This email was sent from.*$',  # Auto-generated footers
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        return text.strip()
    
    def extract_plain_text(self, email_parts: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from email parts.
        
        Args:
            email_parts: List of email parts from Gmail API
            
        Returns:
            str: Extracted plain text content
        """
        for part in email_parts:
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                content = self._decode_part_data(part)
                return self._clean_plain_text(content)
            elif 'parts' in part:
                # Recursively search nested parts
                nested_text = self.extract_plain_text(part['parts'])
                if nested_text:
                    return nested_text
        
        return ""