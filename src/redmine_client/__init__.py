"""
Redmine API Client - Python-Bibliothek für die Redmine REST-API.

Unterstützt sowohl synchrone als auch asynchrone Operationen.

Beispiel (synchron):
    from redmine_client import RedmineClient

    with RedmineClient("https://redmine.example.com", "api-key") as client:
        issues = client.get_issues(assigned_to_id="me", status_id="open")

Beispiel (asynchron):
    from redmine_client import AsyncRedmineClient

    async with AsyncRedmineClient("https://redmine.example.com", "api-key") as client:
        issues = await client.get_issues(assigned_to_id="me", status_id="open")
"""

from .async_client import AsyncRedmineClient
from .client import RedmineClient
from .exceptions import (
    RedmineAuthenticationError,
    RedmineError,
    RedmineNotFoundError,
    RedmineValidationError,
)
from .models import (
    RedmineAllowedStatus,
    RedmineAttachment,
    RedmineChangeset,
    RedmineCustomField,
    RedmineCustomFieldDefinition,
    RedmineIssue,
    RedmineJournal,
    RedmineJournalDetail,
    RedmineProject,
    RedmineRelation,
    RedmineTimeEntry,
    RedmineUser,
    RedmineWikiPage,
)

__version__ = "0.1.0"

__all__ = [
    # Clients
    "RedmineClient",
    "AsyncRedmineClient",
    # Exceptions
    "RedmineError",
    "RedmineAuthenticationError",
    "RedmineNotFoundError",
    "RedmineValidationError",
    # Models
    "RedmineUser",
    "RedmineProject",
    "RedmineIssue",
    "RedmineJournal",
    "RedmineJournalDetail",
    "RedmineTimeEntry",
    "RedmineCustomField",
    "RedmineCustomFieldDefinition",
    "RedmineAttachment",
    "RedmineRelation",
    "RedmineChangeset",
    "RedmineAllowedStatus",
    "RedmineWikiPage",
]
