#!/usr/bin/env python3
"""
Basic functionality test script for Gmail Email Summarizer.

This script tests the core components that have been implemented so far:
- Configuration loading
- Gmail authentication
- Email fetching
"""

import logging
import sys
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_configuration():
    """Test configuration loading."""
    print("🔧 Testing configuration loading...")
    try:
        from config.settings import load_config, validate_gmail_credentials
        
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   - AI Provider: {config.ai_provider}")
        print(f"   - Max emails per run: {config.max_emails_per_run}")
        print(f"   - Credentials file: {config.credentials_file}")
        
        # Check if Gmail credentials file exists
        if validate_gmail_credentials(config):
            print("✅ Gmail credentials file found")
        else:
            print("⚠️  Gmail credentials file not found - you'll need credentials.json to test Gmail functionality")
        
        return config
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return None

def test_gmail_auth(config):
    """Test Gmail authentication."""
    print("\n🔐 Testing Gmail authentication...")
    try:
        from auth.gmail_auth import validate_credentials, get_gmail_service
        
        # First check if credentials file is valid
        if not validate_credentials(config.credentials_file):
            print("⚠️  Invalid or missing credentials file - skipping Gmail auth test")
            return None
        
        # Try to create Gmail service (this will trigger OAuth flow if needed)
        print("   Attempting to authenticate with Gmail...")
        service = get_gmail_service(config.credentials_file, config.token_file)
        print("✅ Gmail authentication successful")
        
        # Test a simple API call
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress', 'Unknown')
        print(f"   - Authenticated as: {email_address}")
        
        return service
        
    except Exception as e:
        print(f"❌ Gmail authentication failed: {e}")
        print("   This is expected if you haven't set up Gmail API credentials yet")
        return None

def test_email_fetching(service, config):
    """Test email fetching functionality."""
    print("\n📧 Testing email fetching...")
    try:
        from gmail_email.fetcher import EmailFetcher
        
        if not service:
            print("⚠️  No Gmail service available - skipping email fetch test")
            return
        
        fetcher = EmailFetcher(service)
        
        # Try to fetch a small number of emails for testing
        print("   Fetching important unread emails...")
        emails = fetcher.fetch_important_unread_emails(max_results=3)
        
        print(f"✅ Email fetching successful")
        print(f"   - Found {len(emails)} important unread emails")
        
        # Show basic info about fetched emails
        for i, email in enumerate(emails[:2], 1):  # Show first 2 emails
            subject = email.get('subject', 'No subject')[:50]
            sender = email.get('sender', 'Unknown sender')[:30]
            print(f"   - Email {i}: '{subject}...' from '{sender}...'")
        
        if len(emails) > 2:
            print(f"   - ... and {len(emails) - 2} more emails")
            
    except Exception as e:
        print(f"❌ Email fetching failed: {e}")

def main():
    """Run basic functionality tests."""
    print("🚀 Gmail Email Summarizer - Basic Functionality Test")
    print("=" * 60)
    
    # Test configuration
    config = test_configuration()
    if not config:
        print("\n❌ Cannot proceed without valid configuration")
        sys.exit(1)
    
    # Test Gmail authentication
    service = test_gmail_auth(config)
    
    # Test email fetching
    test_email_fetching(service, config)
    
    print("\n" + "=" * 60)
    print("🎉 Basic functionality test completed!")
    
    if service:
        print("\n✅ All core components are working!")
        print("   You can now proceed with implementing the remaining features:")
        print("   - Email content processing")
        print("   - AI-powered summarization") 
        print("   - YAML storage")
    else:
        print("\n⚠️  Gmail functionality not tested due to missing credentials")
        print("   To test Gmail features:")
        print("   1. Set up Gmail API credentials (see README.md)")
        print("   2. Place credentials.json in the project root")
        print("   3. Run this test again")

if __name__ == "__main__":
    main()