# Email processing module for fetching and processing Gmail messages

from .processor import EmailProcessor, EmailData
from .fetcher import EmailFetcher

__all__ = ['EmailProcessor', 'EmailData', 'EmailFetcher']