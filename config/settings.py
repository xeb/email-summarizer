"""Configuration management for Gmail Email Summarizer.

This module handles loading and validation of configuration settings,
including environment variables for API keys and other settings.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
import logging

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


@dataclass
class Config:
    """Configuration settings for the Gmail Email Summarizer application."""
    
    # Gmail API settings
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    
    # Output settings
    output_directory: str = "email_summaries"
    max_emails_per_run: int = 5
    
    # AI Summarization Settings
    ai_provider: str = "openai"  # "openai" or "claude"
    openai_api_key: str = field(default="")
    openai_model: str = "gpt-3.5-turbo"
    claude_api_key: str = field(default="")
    claude_model: str = "claude-3-haiku-20240307"
    max_tokens: int = 500
    temperature: float = 0.3
    
    def __post_init__(self):
        """Load environment variables and validate configuration after initialization."""
        self._load_from_environment()
        self._validate_configuration()
    
    def _load_from_environment(self):
        """Load configuration values from environment variables."""
        # Load API keys from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", self.claude_api_key)
        
        # Load other optional settings from environment
        self.ai_provider = os.getenv("AI_PROVIDER", self.ai_provider).lower()
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)
        self.claude_model = os.getenv("CLAUDE_MODEL", self.claude_model)
        self.output_directory = os.getenv("OUTPUT_DIRECTORY", self.output_directory)
        
        # Load numeric settings with validation
        try:
            self.max_emails_per_run = int(os.getenv("MAX_EMAILS_PER_RUN", str(self.max_emails_per_run)))
            self.max_tokens = int(os.getenv("MAX_TOKENS", str(self.max_tokens)))
            self.temperature = float(os.getenv("TEMPERATURE", str(self.temperature)))
        except ValueError as e:
            logging.warning(f"Invalid numeric environment variable: {e}")
    
    def _validate_configuration(self):
        """Validate configuration settings and raise errors for invalid values."""
        # Validate AI provider
        if self.ai_provider not in ["openai", "claude"]:
            raise ValueError(f"Invalid AI provider: {self.ai_provider}. Must be 'openai' or 'claude'")
        
        # Validate API keys based on provider
        if self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI provider. Set OPENAI_API_KEY environment variable.")
        
        if self.ai_provider == "claude" and not self.claude_api_key:
            raise ValueError("Claude API key is required when using Claude provider. Set CLAUDE_API_KEY environment variable.")
        
        # Validate numeric ranges
        if self.max_emails_per_run <= 0:
            raise ValueError("max_emails_per_run must be greater than 0")
        
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")
        
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        
        # Validate file paths
        if not self.credentials_file:
            raise ValueError("credentials_file cannot be empty")
        
        if not self.token_file:
            raise ValueError("token_file cannot be empty")
        
        if not self.output_directory:
            raise ValueError("output_directory cannot be empty")
    
    def get_api_key(self) -> str:
        """Get the appropriate API key based on the configured provider."""
        if self.ai_provider == "openai":
            return self.openai_api_key
        elif self.ai_provider == "claude":
            return self.claude_api_key
        else:
            raise ValueError(f"Unknown AI provider: {self.ai_provider}")
    
    def get_model_name(self) -> str:
        """Get the appropriate model name based on the configured provider."""
        if self.ai_provider == "openai":
            return self.openai_model
        elif self.ai_provider == "claude":
            return self.claude_model
        else:
            raise ValueError(f"Unknown AI provider: {self.ai_provider}")


def load_config() -> Config:
    """Load and return a validated configuration instance.
    
    Returns:
        Config: A validated configuration instance with settings loaded from
                environment variables and defaults.
    
    Raises:
        ValueError: If configuration validation fails.
    """
    try:
        config = Config()
        logging.info(f"Configuration loaded successfully. AI Provider: {config.ai_provider}")
        return config
    except ValueError as e:
        logging.error(f"Configuration validation failed: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        raise ValueError(f"Failed to load configuration: {e}")


def validate_gmail_credentials(config: Config) -> bool:
    """Validate that Gmail API credentials file exists.
    
    Args:
        config: Configuration instance to validate
        
    Returns:
        bool: True if credentials file exists, False otherwise
    """
    if not os.path.exists(config.credentials_file):
        logging.error(f"Gmail credentials file not found: {config.credentials_file}")
        return False
    
    logging.info(f"Gmail credentials file found: {config.credentials_file}")
    return True


def ensure_output_directory(config: Config) -> bool:
    """Ensure the output directory exists, creating it if necessary.
    
    Args:
        config: Configuration instance containing output directory path
        
    Returns:
        bool: True if directory exists or was created successfully, False otherwise
    """
    try:
        os.makedirs(config.output_directory, exist_ok=True)
        logging.info(f"Output directory ready: {config.output_directory}")
        return True
    except OSError as e:
        logging.error(f"Failed to create output directory {config.output_directory}: {e}")
        return False