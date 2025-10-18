---
name: upcoming-school-events
description: Tool for searching Gmail to find school-related emails about upcoming events, assignments, and important dates. Fetches and displays email content from schools without AI summarization.
license: MIT
---

# Upcoming School Events Email Finder

This skill helps you search your Gmail for school-related emails about upcoming events, assignments, field trips, parent-teacher conferences, and other important school communications.

**IMPORTANT**: Before searching, you MUST ask the user for their school's name or domain to ensure accurate results.

## Prerequisites

### First Time Setup - Authentication

Authenticate with Gmail (only needed once):

```bash
uv run email_summarizer_auth.py
```

For headless/SSH environments:

```bash
uv run email_summarizer_auth.py --headless
```

## Workflow: How to Help Users Find Upcoming School Events

### Step 1: Ask for School Information

**CRITICAL**: Always ask the user for their school's name or email domain BEFORE searching.

Example questions:
- "What is your school's name?"
- "What email domain does your school use? (e.g., @springfield-schools.org)"
- "What's the name of your child's school?"

### Step 2: Search for School Emails

Once you know the school name/domain, search for relevant emails.

#### Option A: Search by School Domain (Best Practice)

If the school uses a specific domain (e.g., `@springfield-schools.org`):

```bash
# Recent unread emails from school
uv run email_summarizer.py --filter '{"from": "@school-domain.org", "is_unread": true, "newer_than": "7d"}'

# All important emails from school this month
uv run email_summarizer.py --filter '{"from": "@school-domain.org", "is_important": true, "newer_than": "30d"}'
```

#### Option B: Search by School Name in Subject

If you have the school name:

```bash
# Search for school name in subject
uv run email_summarizer.py --query "subject:'Lincoln Elementary' newer_than:14d"
```

### Step 3: Filter for Event-Related Keywords

Search for specific event types:

```bash
# Field trips
uv run email_summarizer.py --query "from:@school.org subject:field trip newer_than:30d"

# Parent-teacher conferences
uv run email_summarizer.py --query "from:@school.org subject:conference newer_than:14d"

# Assignments and homework
uv run email_summarizer.py --query "from:@school.org subject:assignment OR subject:homework is:unread"

# School events
uv run email_summarizer.py --query "from:@school.org subject:event OR subject:assembly newer_than:7d"
```

### Step 4: Present Results to User

Show the user a summary of what you found. Example format:

```
I found 5 school-related emails from Lincoln Elementary:

1. Field Trip Permission Slip - Due Friday
2. Parent-Teacher Conferences - Next Week
3. School Assembly - Thursday 2pm
4. Homework Assignment - Math Chapter 5
5. Book Fair - October 15-20
```

## Best Practices

### 1. **Always Ask for School Name First**

Never search without knowing the school name or domain. This ensures accurate, relevant results.

### 2. **Use Time Filters**

Focus on recent/upcoming events:
- `newer_than:7d` - Last week (current events)
- `newer_than:14d` - Last 2 weeks (near-term planning)
- `newer_than:30d` - Last month (monthly overview)

### 3. **Search for Short Emails**

Schools often send concise announcements. Use filters to find brief, actionable emails:

```bash
# Smaller emails are often quick announcements
uv run email_summarizer.py --query "from:@school.org smaller:50K newer_than:7d"
```

### 4. **Prioritize Important/Unread**

Focus on what needs attention:

```bash
# Unread important emails
uv run email_summarizer.py --filter '{"from": "@school.org", "is_important": true, "is_unread": true}'
```

### 5. **Check for Attachments**

Permission slips, forms, and documents often have attachments:

```bash
# Emails with attachments from school
uv run email_summarizer.py --filter '{"from": "@school.org", "has_attachment": true, "newer_than": "14d"}'
```

### 6. **Use Full Message Body for Details**

When you need complete information (dates, times, requirements):

```bash
# Get full details
uv run email_summarizer.py --query "from:@school.org subject:conference" --full
```

### 7. **Limit Results for Quick Overview**

Start with fewer results to avoid overwhelming the user:

```bash
# Just the 5 most recent
uv run email_summarizer.py --query "from:@school.org is:unread" --max-results 5
```

## Common School Email Searches

### Weekly Event Summary

Get this week's school emails:

```bash
uv run email_summarizer.py --filter '{"from": "@SCHOOL-DOMAIN.org", "newer_than": "7d"}' --max-results 10
```

### Monthly Comprehensive Review (Full Emails)

Get ALL full emails from a school for the past 28 days - useful for comprehensive monthly reviews:

```bash
# Example: Get all full emails from CVCS for the last 28 days
uv run email_summarizer.py --query "from:@cvcs.org smaller:5000K newer_than:28d" --full --max-results 100
```

This example:
- Searches CVCS school domain (`from:@cvcs.org`)
- Filters emails under 5MB (`smaller:5000K`) to exclude very large emails
- Gets last 28 days of emails (`newer_than:28d` = 4 weeks)
- Fetches complete message bodies (`--full`)
- Retrieves up to 100 emails (`--max-results 100`)

Perfect for getting a comprehensive view of all school communications for the month.

### Permission Slips and Forms

Find emails with attachments that might be forms:

```bash
uv run email_summarizer.py --query "from:@SCHOOL-DOMAIN.org subject:permission OR subject:form has:attachment newer_than:30d"
```

### Important Deadlines

Search for deadline-related keywords:

```bash
uv run email_summarizer.py --query "from:@SCHOOL-DOMAIN.org subject:due OR subject:deadline is:important newer_than:14d"
```

### Calendar Events

Find scheduled events and activities:

```bash
uv run email_summarizer.py --query "from:@SCHOOL-DOMAIN.org subject:calendar OR subject:schedule OR subject:event newer_than:14d"
```

### Teacher Communications

If you know the teacher's email:

```bash
uv run email_summarizer.py --filter '{"from": "teacher@school.org", "newer_than": "7d"}'
```

### Emergency or Urgent Notifications

Find urgent communications:

```bash
uv run email_summarizer.py --query "from:@SCHOOL-DOMAIN.org subject:urgent OR subject:important OR subject:emergency newer_than:7d"
```

## Example User Interaction

**User**: "Can you help me find upcoming school events?"

**Assistant**: "I'd be happy to help! What is your child's school name or what email domain does the school use? (For example: @lincoln-elementary.org)"

**User**: "Lincoln Elementary School, they use @lincoln-k12.org"

**Assistant**: "Great! Let me search for recent emails from Lincoln Elementary..."

```bash
uv run email_summarizer.py --filter '{"from": "@lincoln-k12.org", "newer_than": "14d"}' --max-results 10
```

**Assistant**: "I found 8 emails from Lincoln Elementary in the last 2 weeks:

1. **Field Trip to Science Museum** - Permission slip due Friday
2. **Parent-Teacher Conferences** - Sign up by October 20
3. **Book Fair** - October 15-20, library hours
4. **Halloween Parade** - October 31 at 2pm
5. **Early Dismissal** - Professional development day, October 18
...

Would you like me to show the full details for any of these?"

## Common Keywords for School Searches

Include these in subject/query searches:

**Events & Activities**:
- `field trip`, `assembly`, `performance`, `concert`, `play`
- `sports`, `game`, `practice`, `meet`
- `fair`, `festival`, `celebration`, `party`

**Academic**:
- `homework`, `assignment`, `project`, `test`, `quiz`
- `grades`, `report card`, `progress report`
- `class`, `schedule`, `curriculum`

**Administrative**:
- `permission`, `form`, `registration`, `enrollment`
- `conference`, `meeting`, `parent`, `teacher`
- `lunch`, `menu`, `cafeteria`
- `bus`, `transportation`, `pickup`, `dismissal`

**Urgent/Important**:
- `urgent`, `important`, `reminder`, `deadline`
- `due`, `required`, `mandatory`
- `emergency`, `closure`, `delay`, `cancellation`

## Advanced Filtering

### Combine Multiple Criteria

```bash
# Important unread emails with attachments from school
uv run email_summarizer.py --filter '{
  "from": "@school.org",
  "is_important": true,
  "is_unread": true,
  "has_attachment": true,
  "newer_than": "7d"
}'
```

### Date Range Search

```bash
# Emails from specific date range
uv run email_summarizer.py --filter '{
  "from": "@school.org",
  "after": "2024-10-01",
  "before": "2024-10-31"
}'
```

### Export for Record Keeping

```bash
# Export school communications to JSON
uv run email_summarizer.py --filter '{"from": "@school.org", "newer_than": "30d"}' --output school_emails.json
```

## Filter Options Reference

When using `--filter` (JSON format):

- **from**: Email address or domain (e.g., `"@school.org"`, `"principal@school.org"`)
- **to**: Your email address
- **subject**: Keywords in subject line
- **is_unread**: `true` for unread only
- **is_important**: `true` for important only
- **is_starred**: `true` for starred only
- **has_attachment**: `true` for emails with attachments
- **after**: Date (YYYY-MM-DD format)
- **before**: Date (YYYY-MM-DD format)
- **newer_than**: Relative date (`"7d"`, `"2w"`, `"1m"`)
- **older_than**: Relative date (`"7d"`, `"2w"`, `"1m"`)

## Gmail Query Operators

When using `--query` (Gmail syntax):

- `from:@domain.org` - From specific domain
- `from:email@school.org` - From specific sender
- `subject:"field trip"` - Exact phrase in subject
- `subject:homework` - Word in subject
- `is:unread` - Unread messages
- `is:important` - Important messages
- `is:starred` - Starred messages
- `has:attachment` - Has attachments
- `newer_than:7d` - Last 7 days (also: w, m, y)
- `after:2024/10/01` - After specific date
- `before:2024/10/31` - Before specific date
- `smaller:100K` - Smaller than 100KB (useful for finding brief announcements)
- `larger:1M` - Larger than 1MB

Combine with spaces (AND) or `OR`:
```bash
uv run email_summarizer.py --query "from:@school.org (subject:homework OR subject:assignment) newer_than:7d"
```

## Command-Line Reference

```
uv run email_summarizer.py [OPTIONS]

Required (one of):
  --query, -q QUERY         Gmail search query
  --filter, -f FILTER       Filter as JSON string

Optional:
  --max-results, -m NUM     Limit results (default: 10)
  --full                    Show full message body (not just snippet)
  --output, -o FILE         Export to JSON file
  --credentials FILE        Custom credentials file
  --token FILE              Custom token file
```

## Troubleshooting

### No Results Found

1. **Verify school domain**: Ask user to confirm the exact domain
2. **Expand time range**: Try `newer_than:30d` instead of `7d`
3. **Remove filters**: Start broad, then narrow down
4. **Check spelling**: Verify school name spelling

### Too Many Results

1. **Add time filter**: Use `newer_than:7d` for recent emails
2. **Limit results**: Use `--max-results 5`
3. **Add keywords**: Include subject filters
4. **Filter by importance**: Add `is:important`

### Authentication Issues

Re-authenticate if needed:

```bash
uv run email_summarizer_auth.py --force
```

## Tips for Maximum Efficiency

1. **Start with school domain** - Most accurate filter
2. **Use time windows** - Focus on upcoming/recent events
3. **Combine filters** - Multiple criteria = better results
4. **Check unread first** - What needs immediate attention
5. **Export monthly** - Keep records with `--output`
6. **Use --full sparingly** - Only when you need complete details
7. **Search for short emails** - `smaller:50K` finds brief announcements
8. **Look for attachments** - Forms and permission slips usually attached

## Notes

- Does NOT perform AI summarization - returns raw email content
- Respects Gmail API quotas (see Google Cloud Console for limits)
- Token stored securely (chmod 600) in `token.json`
- Never commit credentials or tokens to version control
