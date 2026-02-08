# Redmine Client

[![PyPI version](https://badge.fury.io/py/redmine-client.svg)](https://pypi.org/project/redmine-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Python client for the Redmine REST API with synchronous and asynchronous support.

## Features

- Synchronous and asynchronous client
- Full type hints with Pydantic models
- Issues with journals, attachments, relations, watchers, changesets, children
- Wiki API (CRUD)
- Attachment upload and download
- Custom fields support
- Automatic pagination
- Context manager support

## Installation

```bash
pip install redmine-client
```

Or with uv:

```bash
uv add redmine-client
```

## Quick Start

### Synchronous

```python
from redmine_client import RedmineClient

with RedmineClient("https://redmine.example.com", "your-api-key") as client:
    issues = client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")
```

### Asynchronous

```python
from redmine_client import AsyncRedmineClient

async with AsyncRedmineClient("https://redmine.example.com", "your-api-key") as client:
    issues = await client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")
```

## API Reference

### Issues

```python
# Get issues with filters
issues = client.get_issues(
    project_id="myproject",
    assigned_to_id="me",
    status_id="open",            # "open", "closed", "*", or ID
    tracker_id=1,
    updated_on=">=2025-01-01",
    created_on=">=2025-01-01",
)

# Get single issue with related data
issue = client.get_issue(123, include=[
    "journals",           # Comments and change history
    "attachments",        # File attachments
    "relations",          # Related issues
    "watchers",           # Watching users
    "changesets",         # VCS commits
    "children",           # Sub-issues
    "allowed_statuses",   # Available status transitions
])

# Access included data
for journal in issue.journals or []:
    print(f"{journal.user_name}: {journal.notes}")

for attachment in issue.attachments or []:
    print(f"{attachment.filename} ({attachment.filesize} bytes)")

for child in issue.children or []:
    print(f"  Sub-issue #{child.id}: {child.subject}")

# Create issue
new_issue = client.create_issue(
    project_id="myproject",
    subject="New feature",
    description="Description...",
    tracker_id=2,
    custom_fields=[{"id": 42, "value": "Sprint value"}],
)

# Update issue
client.update_issue(
    issue_id=123,
    subject="Updated subject",
    status_id=2,
    notes="Add a comment",
    custom_fields=[{"id": 42, "value": "New value"}],
)

# Add comment
client.add_issue_note(123, "My comment")
```

### Wiki

```python
# List wiki pages
pages = client.get_wiki_pages("myproject")

for page in pages:
    print(page.title)

# Get wiki page content
page = client.get_wiki_page("myproject", "Start", include_attachments=True)
print(page.text)
print(f"Author: {page.author_name}, Version: {page.version}")

# Create or update wiki page
client.create_or_update_wiki_page(
    "myproject", "NewPage",
    text="h1. Page Title\n\nContent here.",
    comments="Initial version",
)

# Delete wiki page
client.delete_wiki_page("myproject", "OldPage")
```

### Attachments

```python
# Upload a file and get a token
token = client.upload_file("/path/to/document.pdf")

# Or upload bytes directly
token = client.upload_file(b"file content", filename="data.csv")

# Attach to issue via create or update
client.create_issue(
    project_id="myproject",
    subject="Issue with attachment",
    uploads=[{
        "token": token,
        "filename": "document.pdf",
        "content_type": "application/pdf",
    }],
)

# Get attachment metadata
attachment = client.get_attachment(42)
print(f"{attachment.filename} - {attachment.filesize} bytes")

# Download attachment
data = client.download_attachment(42)
with open("downloaded.pdf", "wb") as f:
    f.write(data)

# Delete attachment
client.delete_attachment(42)
```

### Custom Fields

```python
# Get all custom fields (requires admin rights)
fields = client.get_custom_fields()

# Get issue custom fields only
issue_fields = client.get_issue_custom_fields()

# Find custom field by name
sprint_field = client.find_custom_field_by_name("Sprint")

# Read custom field value from issue
issue = client.get_issue(123)
sprint = issue.get_custom_field("Sprint")
sprint_by_id = issue.get_custom_field_by_id(42)
```

### Projects

```python
projects = client.get_projects(include_closed=False)
project = client.get_project("myproject")
```

### Users

```python
current_user = client.get_current_user()
users = client.get_users(status=1)  # 1 = active
user = client.get_user(42)
```

### Time Entries

```python
from datetime import date

entries = client.get_time_entries(
    user_id=1,
    from_date=date(2025, 1, 1),
    to_date=date(2025, 12, 31),
)
entry = client.get_time_entry(42)
```

### Enumerations

```python
trackers = client.get_trackers()
statuses = client.get_issue_statuses()
priorities = client.get_issue_priorities()
activities = client.get_time_entry_activities()
```

## Models

All responses are returned as Pydantic models:

| Model | Description |
|-------|-------------|
| `RedmineIssue` | Issue/Ticket with optional journals, attachments, relations, watchers, changesets, children |
| `RedmineProject` | Project |
| `RedmineUser` | User |
| `RedmineTimeEntry` | Time entry |
| `RedmineJournal` | Comment/change history entry |
| `RedmineJournalDetail` | Single field change within a journal |
| `RedmineAttachment` | File attachment |
| `RedmineRelation` | Issue relation |
| `RedmineChangeset` | VCS commit |
| `RedmineAllowedStatus` | Allowed status transition |
| `RedmineWikiPage` | Wiki page |
| `RedmineCustomField` | Custom field value |
| `RedmineCustomFieldDefinition` | Custom field definition |

## Error Handling

```python
from redmine_client import (
    RedmineError,
    RedmineAuthenticationError,
    RedmineNotFoundError,
    RedmineValidationError,
)

try:
    issue = client.get_issue(99999)
except RedmineNotFoundError:
    print("Issue not found")
except RedmineAuthenticationError:
    print("Invalid API key")
except RedmineValidationError as e:
    print(f"Validation error: {e.response}")
except RedmineError as e:
    print(f"Redmine error: {e}")
```

## Development

```bash
git clone https://github.com/dkd-dobberkau/python-redmine-client.git
cd python-redmine-client
uv sync --all-extras
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

## License

MIT
