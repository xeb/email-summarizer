"""Example search configurations and Gmail search operator documentation.

This module provides pre-defined example search configurations for common use cases
and comprehensive documentation for Gmail search operators with helpful suggestions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from config.search_configs import SearchConfig


class GmailSearchHelp:
    """Comprehensive help and documentation for Gmail search operators."""
    
    # Gmail search operators with descriptions and examples
    OPERATORS = {
        'from:': {
            'description': 'Search for emails from specific senders',
            'examples': [
                'from:john@example.com',
                'from:@company.com',
                'from:(john@example.com OR jane@example.com)'
            ],
            'tips': [
                'Use domain filtering with @domain.com to find all emails from a company',
                'Combine multiple senders with OR operator in parentheses',
                'Use quotes for exact email addresses with special characters'
            ]
        },
        'to:': {
            'description': 'Search for emails sent to specific recipients',
            'examples': [
                'to:me',
                'to:team@company.com',
                'to:(support@company.com OR sales@company.com)'
            ],
            'tips': [
                'Use "to:me" to find emails sent directly to you',
                'Combine with other operators to find emails sent to specific teams',
                'Use OR operator to search multiple recipients'
            ]
        },
        'subject:': {
            'description': 'Search for emails with specific subject text',
            'examples': [
                'subject:"project update"',
                'subject:meeting',
                'subject:(urgent OR important)'
            ],
            'tips': [
                'Use quotes for exact phrase matching',
                'Combine multiple keywords with OR operator',
                'Subject search is case-insensitive'
            ]
        },
        'has:': {
            'description': 'Search for emails with specific attributes',
            'examples': [
                'has:attachment',
                'has:yellow-star',
                'has:userlabels'
            ],
            'valid_values': [
                'attachment', 'nouserlabels', 'userlabels', 'yellow-star',
                'blue-info', 'red-bang', 'orange-guillemet', 'red-star',
                'purple-star', 'green-star', 'yellow-bang'
            ],
            'tips': [
                'Use has:attachment to find emails with file attachments',
                'Star colors help organize and find important emails',
                'has:userlabels finds emails with custom labels'
            ]
        },
        'is:': {
            'description': 'Search for emails with specific status',
            'examples': [
                'is:unread',
                'is:important',
                'is:starred'
            ],
            'valid_values': [
                'important', 'starred', 'unread', 'read', 'chat', 'muted',
                'snoozed', 'spam', 'trash'
            ],
            'tips': [
                'is:unread finds all unread emails',
                'is:important finds emails marked as important by Gmail',
                'Combine multiple status filters with AND/OR operators'
            ]
        },
        'in:': {
            'description': 'Search within specific folders or labels',
            'examples': [
                'in:inbox',
                'in:sent',
                'in:trash'
            ],
            'valid_values': [
                'inbox', 'trash', 'spam', 'unread', 'starred', 'sent',
                'drafts', 'important', 'chats', 'all', 'anywhere'
            ],
            'tips': [
                'in:anywhere searches all folders including trash and spam',
                'in:sent finds emails you have sent',
                'Use in:unread as alternative to is:unread'
            ]
        },
        'after:': {
            'description': 'Search for emails after a specific date',
            'examples': [
                'after:2024-01-01',
                'after:2024/01/15'
            ],
            'date_formats': [
                'YYYY-MM-DD (e.g., 2024-01-01)',
                'YYYY/MM/DD (e.g., 2024/01/15)',
                'Relative dates: yesterday, today'
            ],
            'tips': [
                'Use YYYY-MM-DD format for specific dates',
                'Combine with before: for date ranges',
                'Use relative dates like "yesterday" for recent searches'
            ]
        },
        'before:': {
            'description': 'Search for emails before a specific date',
            'examples': [
                'before:2024-12-31',
                'before:2024/06/01'
            ],
            'date_formats': [
                'YYYY-MM-DD (e.g., 2024-12-31)',
                'YYYY/MM/DD (e.g., 2024/06/01)',
                'Relative dates: yesterday, today'
            ],
            'tips': [
                'Combine with after: to create date ranges',
                'Use before:today to exclude today\'s emails',
                'Useful for archiving old emails'
            ]
        },
        'newer_than:': {
            'description': 'Search for emails newer than a relative time period',
            'examples': [
                'newer_than:7d',
                'newer_than:1m',
                'newer_than:2y'
            ],
            'time_units': [
                'd = days (e.g., 7d for 7 days)',
                'm = months (e.g., 1m for 1 month)',
                'y = years (e.g., 2y for 2 years)'
            ],
            'tips': [
                'More flexible than after: for relative dates',
                'Use for finding recent emails without specific dates',
                'Combine with other operators for targeted searches'
            ]
        },
        'older_than:': {
            'description': 'Search for emails older than a relative time period',
            'examples': [
                'older_than:30d',
                'older_than:6m',
                'older_than:1y'
            ],
            'time_units': [
                'd = days (e.g., 30d for 30 days)',
                'm = months (e.g., 6m for 6 months)',
                'y = years (e.g., 1y for 1 year)'
            ],
            'tips': [
                'Useful for finding old emails to archive or delete',
                'Combine with is:read to find old read emails',
                'Use for cleanup and organization tasks'
            ]
        },
        'larger:': {
            'description': 'Search for emails larger than specified size',
            'examples': [
                'larger:10M',
                'larger:1G',
                'larger:500K'
            ],
            'size_units': [
                'K = kilobytes (e.g., 500K)',
                'M = megabytes (e.g., 10M)',
                'G = gigabytes (e.g., 1G)'
            ],
            'tips': [
                'Useful for finding emails with large attachments',
                'Combine with has:attachment for attachment-specific searches',
                'Use for storage cleanup and management'
            ]
        },
        'smaller:': {
            'description': 'Search for emails smaller than specified size',
            'examples': [
                'smaller:1M',
                'smaller:100K',
                'smaller:10M'
            ],
            'size_units': [
                'K = kilobytes (e.g., 100K)',
                'M = megabytes (e.g., 1M)',
                'G = gigabytes (e.g., 10M)'
            ],
            'tips': [
                'Find text-only emails without attachments',
                'Useful for finding simple notification emails',
                'Combine with other operators for specific searches'
            ]
        },
        'filename:': {
            'description': 'Search for emails with attachments containing specific filenames',
            'examples': [
                'filename:pdf',
                'filename:report.docx',
                'filename:"project plan"'
            ],
            'tips': [
                'Search by file extension to find specific file types',
                'Use quotes for filenames with spaces',
                'Combine with from: to find files from specific senders'
            ]
        },
        'label:': {
            'description': 'Search for emails with specific labels',
            'examples': [
                'label:work',
                'label:important',
                'label:"project-alpha"'
            ],
            'tips': [
                'Use custom labels you\'ve created in Gmail',
                'Combine with other operators for targeted searches',
                'Use quotes for labels with spaces or special characters'
            ]
        },
        'cc:': {
            'description': 'Search for emails where specific recipients were CC\'d',
            'examples': [
                'cc:manager@company.com',
                'cc:team@company.com'
            ],
            'tips': [
                'Find emails where someone was copied',
                'Useful for tracking team communications',
                'Combine with from: to find specific sender patterns'
            ]
        },
        'bcc:': {
            'description': 'Search for emails where specific recipients were BCC\'d',
            'examples': [
                'bcc:me',
                'bcc:admin@company.com'
            ],
            'tips': [
                'Less commonly used as BCC information is often hidden',
                'Useful for finding emails where you were secretly copied',
                'May not work for all email configurations'
            ]
        },
        'size:': {
            'description': 'Search for emails of a specific size',
            'examples': [
                'size:1M',
                'size:500K'
            ],
            'size_units': [
                'K = kilobytes (e.g., 500K)',
                'M = megabytes (e.g., 1M)',
                'G = gigabytes (e.g., 1G)'
            ],
            'tips': [
                'Use for finding emails of exact sizes',
                'More commonly used with larger: or smaller: operators',
                'Useful for storage management'
            ]
        },
        'category:': {
            'description': 'Search for emails in specific Gmail categories',
            'examples': [
                'category:primary',
                'category:social',
                'category:promotions'
            ],
            'valid_values': [
                'primary', 'social', 'promotions', 'updates', 'forums'
            ],
            'tips': [
                'Gmail automatically categorizes emails',
                'Useful for filtering by email type',
                'Categories may vary based on Gmail settings'
            ]
        },
        'deliveredto:': {
            'description': 'Search for emails delivered to specific addresses',
            'examples': [
                'deliveredto:me@company.com',
                'deliveredto:alias@company.com'
            ],
            'tips': [
                'Useful for finding emails sent to specific aliases',
                'Helps track email routing and delivery',
                'Advanced operator for email administration'
            ]
        },
        'circle:': {
            'description': 'Search for emails from Google+ circles (deprecated)',
            'examples': [
                'circle:friends',
                'circle:family'
            ],
            'tips': [
                'This operator is largely deprecated',
                'Was used with Google+ social features',
                'May not work in current Gmail versions'
            ]
        },
        'rfc822msgid:': {
            'description': 'Search for emails by RFC 822 Message-ID',
            'examples': [
                'rfc822msgid:12345@example.com'
            ],
            'tips': [
                'Advanced operator for email administrators',
                'Used for tracking specific email messages',
                'Requires knowledge of email headers'
            ]
        }
    }
    
    # Common search patterns and combinations
    SEARCH_PATTERNS = {
        'recent_important': {
            'query': 'is:important is:unread newer_than:7d',
            'description': 'Important unread emails from the last 7 days',
            'use_case': 'Daily email triage and priority management'
        },
        'work_attachments': {
            'query': 'from:@company.com has:attachment newer_than:30d',
            'description': 'Work emails with attachments from the last month',
            'use_case': 'Finding recent work documents and files'
        },
        'large_emails': {
            'query': 'larger:10M has:attachment',
            'description': 'Emails with large attachments (>10MB)',
            'use_case': 'Storage management and cleanup'
        },
        'meeting_invites': {
            'query': 'subject:(meeting OR call OR invite) is:unread',
            'description': 'Unread meeting invitations and calls',
            'use_case': 'Calendar management and scheduling'
        },
        'urgent_today': {
            'query': 'subject:urgent newer_than:1d',
            'description': 'Urgent emails from today',
            'use_case': 'Emergency and high-priority email handling'
        },
        'newsletter_cleanup': {
            'query': '(subject:newsletter OR subject:unsubscribe) older_than:30d is:read',
            'description': 'Old read newsletters for cleanup',
            'use_case': 'Email organization and unsubscribing'
        }
    }
    
    @classmethod
    def get_operator_help(cls, operator: str = None) -> str:
        """Get help text for Gmail search operators.
        
        Args:
            operator: Specific operator to get help for, or None for all operators
            
        Returns:
            Formatted help text
        """
        if operator:
            if operator in cls.OPERATORS:
                op_info = cls.OPERATORS[operator]
                help_text = f"\n{operator}\n{'=' * len(operator)}\n"
                help_text += f"Description: {op_info['description']}\n\n"
                
                help_text += "Examples:\n"
                for example in op_info['examples']:
                    help_text += f"  {example}\n"
                
                if 'valid_values' in op_info:
                    help_text += f"\nValid values: {', '.join(op_info['valid_values'])}\n"
                
                if 'date_formats' in op_info:
                    help_text += "\nDate formats:\n"
                    for fmt in op_info['date_formats']:
                        help_text += f"  {fmt}\n"
                
                if 'time_units' in op_info:
                    help_text += "\nTime units:\n"
                    for unit in op_info['time_units']:
                        help_text += f"  {unit}\n"
                
                if 'size_units' in op_info:
                    help_text += "\nSize units:\n"
                    for unit in op_info['size_units']:
                        help_text += f"  {unit}\n"
                
                help_text += "\nTips:\n"
                for tip in op_info['tips']:
                    help_text += f"  • {tip}\n"
                
                return help_text
            else:
                return f"Unknown operator: {operator}\nUse --help-search to see all available operators."
        else:
            # Return help for all operators
            help_text = "\nGmail Search Operators Reference\n"
            help_text += "=" * 35 + "\n\n"
            
            for op, info in cls.OPERATORS.items():
                help_text += f"{op:<15} {info['description']}\n"
            
            help_text += "\nFor detailed help on a specific operator, use: --help-search <operator>\n"
            help_text += "For example: --help-search from:\n\n"
            
            help_text += "Common Search Patterns:\n"
            help_text += "-" * 23 + "\n"
            for pattern_name, pattern_info in cls.SEARCH_PATTERNS.items():
                help_text += f"\n{pattern_name}:\n"
                help_text += f"  Query: {pattern_info['query']}\n"
                help_text += f"  Description: {pattern_info['description']}\n"
                help_text += f"  Use case: {pattern_info['use_case']}\n"
            
            return help_text
    
    @classmethod
    def get_search_suggestions(cls, query: str) -> List[str]:
        """Get suggestions for improving a search query.
        
        Args:
            query: Gmail search query to analyze
            
        Returns:
            List of suggestions for improving the query
        """
        suggestions = []
        query_lower = query.lower()
        
        # Suggest combining operators for better results
        if 'from:' in query_lower and 'is:unread' not in query_lower:
            suggestions.append("Consider adding 'is:unread' to focus on unread emails")
        
        if 'has:attachment' in query_lower and 'larger:' not in query_lower:
            suggestions.append("Consider adding 'larger:1M' to find emails with substantial attachments")
        
        if 'subject:' in query_lower and not any(op in query_lower for op in ['from:', 'after:', 'before:']):
            suggestions.append("Consider adding sender or date filters to narrow results")
        
        # Suggest date filters for better performance
        if not any(date_op in query_lower for date_op in ['after:', 'before:', 'newer_than:', 'older_than:']):
            suggestions.append("Consider adding date filters (after:, newer_than:) for better performance")
        
        # Suggest specific patterns based on query content
        if 'meeting' in query_lower:
            suggestions.append("Try: subject:(meeting OR call OR invite) for comprehensive meeting search")
        
        if 'urgent' in query_lower or 'important' in query_lower:
            suggestions.append("Try: (subject:urgent OR is:important) for comprehensive urgent email search")
        
        if 'work' in query_lower or '@company' in query_lower:
            suggestions.append("Consider combining with has:attachment for work documents")
        
        return suggestions


class ExampleConfigurations:
    """Pre-defined example search configurations for common use cases."""
    
    @classmethod
    def get_example_configs(cls) -> List[SearchConfig]:
        """Get a list of example search configurations.
        
        Returns:
            List of SearchConfig instances with common use cases
        """
        now = datetime.now()
        
        examples = [
            SearchConfig(
                name="work-urgent",
                query="from:@company.com subject:urgent is:unread",
                description="Urgent unread emails from work domain",
                created_at=now
            ),
            SearchConfig(
                name="recent-attachments",
                query="has:attachment newer_than:7d",
                description="Emails with attachments from the last 7 days",
                created_at=now
            ),
            SearchConfig(
                name="large-files",
                query="larger:10M has:attachment",
                description="Emails with large attachments (>10MB) for storage cleanup",
                created_at=now
            ),
            SearchConfig(
                name="meeting-invites",
                query="subject:(meeting OR call OR invite OR calendar) is:unread",
                description="Unread meeting invitations and calendar events",
                created_at=now
            ),
            SearchConfig(
                name="today-important",
                query="is:important newer_than:1d",
                description="Important emails from today",
                created_at=now
            ),
            SearchConfig(
                name="weekly-digest",
                query="(subject:digest OR subject:summary OR subject:weekly) newer_than:7d",
                description="Weekly digests and summary emails",
                created_at=now
            ),
            SearchConfig(
                name="support-tickets",
                query="(from:support OR from:noreply OR subject:ticket) is:unread",
                description="Unread support tickets and automated notifications",
                created_at=now
            ),
            SearchConfig(
                name="personal-unread",
                query="is:unread -from:@company.com -subject:newsletter -subject:notification",
                description="Personal unread emails excluding work and newsletters",
                created_at=now
            ),
            SearchConfig(
                name="old-newsletters",
                query="(subject:newsletter OR subject:unsubscribe) older_than:30d is:read",
                description="Old read newsletters for cleanup and unsubscribing",
                created_at=now
            ),
            SearchConfig(
                name="project-alpha",
                query='(subject:"project alpha" OR subject:"alpha project") has:attachment',
                description="Project Alpha related emails with attachments",
                created_at=now
            ),
            SearchConfig(
                name="expense-reports",
                query="(subject:expense OR subject:receipt OR filename:pdf) from:@company.com",
                description="Expense reports and receipts from work",
                created_at=now
            ),
            SearchConfig(
                name="social-media",
                query="(from:@facebook.com OR from:@twitter.com OR from:@linkedin.com) newer_than:3d",
                description="Recent social media notifications",
                created_at=now
            )
        ]
        
        return examples
    
    @classmethod
    def get_config_by_category(cls) -> Dict[str, List[SearchConfig]]:
        """Get example configurations organized by category.
        
        Returns:
            Dictionary with categories as keys and lists of SearchConfig as values
        """
        configs = cls.get_example_configs()
        
        categories = {
            "Work & Business": [
                config for config in configs 
                if any(keyword in config.name for keyword in ["work", "project", "expense", "support"])
            ],
            "Time-based": [
                config for config in configs 
                if any(keyword in config.name for keyword in ["recent", "today", "weekly", "old"])
            ],
            "File Management": [
                config for config in configs 
                if any(keyword in config.name for keyword in ["attachments", "large", "files"])
            ],
            "Communication": [
                config for config in configs 
                if any(keyword in config.name for keyword in ["meeting", "invite", "digest"])
            ],
            "Personal": [
                config for config in configs 
                if any(keyword in config.name for keyword in ["personal", "social", "newsletter"])
            ]
        }
        
        return categories
    
    @classmethod
    def get_config_suggestions_for_query(cls, query: str) -> List[SearchConfig]:
        """Get example configurations that might be relevant to a given query.
        
        Args:
            query: Gmail search query to find relevant examples for
            
        Returns:
            List of relevant SearchConfig examples
        """
        query_lower = query.lower()
        relevant_configs = []
        
        for config in cls.get_example_configs():
            config_keywords = (config.name + " " + config.description + " " + config.query).lower()
            
            # Check for keyword matches
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in config_keywords)
            
            if matches > 0:
                relevant_configs.append((config, matches))
        
        # Sort by relevance (number of matches) and return top 5
        relevant_configs.sort(key=lambda x: x[1], reverse=True)
        return [config for config, _ in relevant_configs[:5]]


def validate_example_configurations() -> Tuple[bool, List[str]]:
    """Validate all example configurations to ensure they have valid queries.
    
    Returns:
        Tuple of (all_valid, list_of_errors)
    """
    from config.search_configs import QueryValidator
    
    validator = QueryValidator()
    errors = []
    
    for config in ExampleConfigurations.get_example_configs():
        is_valid, error_msg = validator.validate_query(config.query)
        if not is_valid:
            errors.append(f"Config '{config.name}': {error_msg}")
    
    return len(errors) == 0, errors


def create_example_config_file(file_path: str = "example_search_configs.json") -> bool:
    """Create a JSON file with example configurations for reference.
    
    Args:
        file_path: Path where to create the example file
        
    Returns:
        True if file was created successfully
    """
    try:
        import json
        
        examples = ExampleConfigurations.get_example_configs()
        categories = ExampleConfigurations.get_config_by_category()
        
        example_data = {
            "version": "1.0",
            "description": "Example Gmail search configurations for common use cases",
            "usage": "Use --save-config to add any of these examples to your personal configurations",
            "categories": {},
            "all_examples": {}
        }
        
        # Add categorized examples
        for category, configs in categories.items():
            example_data["categories"][category] = {
                config.name: {
                    "query": config.query,
                    "description": config.description,
                    "usage_example": f"--search-config {config.name}"
                }
                for config in configs
            }
        
        # Add all examples
        for config in examples:
            example_data["all_examples"][config.name] = config.to_dict()
        
        with open(file_path, 'w') as f:
            json.dump(example_data, f, indent=2, sort_keys=True)
        
        return True
        
    except Exception as e:
        print(f"Error creating example config file: {e}")
        return False