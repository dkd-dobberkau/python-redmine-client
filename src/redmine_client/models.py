"""
Pydantic-Modelle für Redmine API Ressourcen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Type, TypeVar

from pydantic import BaseModel, Field

RedmineApiModelT = TypeVar("RedmineApiModelT", bound="RedmineApiModel")

class RedmineApiModel(BaseModel, ABC):
    """
    Abstract class provides a extended Interface for all Redmine result BaseModels
    """
    @classmethod
    @abstractmethod
    def from_api_response(cls: Type[RedmineApiModelT], data: dict) -> RedmineApiModelT:
        """
        Parse the result via Pydantic with optional mappings
        """
        ...

class RedmineUser(RedmineApiModel):
    """Redmine Benutzer."""

    id: int
    login: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    mail: str | None = None
    created_on: str | None = None
    last_login_on: str | None = None

    @property
    def full_name(self) -> str:
        """Vollständiger Name."""
        return f"{self.firstname or ''} {self.lastname or ''}".strip()

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineUser:
        """
        Validate and parse the API result to a RedmineUser instance
        """
        return RedmineUser.model_validate(data)    

class RedmineCustomField(BaseModel):
    """Redmine Custom Field Wert."""

    id: int
    name: str | None = None
    value: str | list[str] | None = None

    model_config = {"extra": "ignore"}


class RedmineCustomFieldDefinition(BaseModel):
    """Redmine Custom Field Definition."""

    id: int
    name: str
    customized_type: str | None = None  # issue, project, user, etc.
    field_format: str | None = None  # string, list, date, etc.
    possible_values: list[dict[str, Any]] | None = None
    is_required: bool = False
    is_filter: bool = False
    searchable: bool = False
    multiple: bool = False
    default_value: str | None = None

    model_config = {"extra": "ignore"}


class RedmineProject(RedmineApiModel):
    """Redmine Projekt."""

    id: int
    name: str
    identifier: str | None = None
    description: str | None = None
    status: int | None = None
    is_public: bool | None = None
    created_on: str | None = None
    updated_on: str | None = None
    custom_fields: list[RedmineCustomField] | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def get_custom_field(self, name: str) -> str | list[str] | None:
        """Gibt den Wert eines Custom Fields zurück."""
        if self.custom_fields is not None:
            for cf in self.custom_fields:
                if cf.name == name:
                    return cf.value
        return None

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineProject:
        """
        Validate and parse the API result to a RedmineProject instance
        """
        return RedmineProject.model_validate(data)   

class RedmineTimeEntry(RedmineApiModel):
    """Redmine Zeiteintrag."""

    id: int
    project_id: int | None = None
    project_name: str | None = None
    issue_id: int | None = None
    user_id: int | None = None
    user_name: str | None = None
    activity_id: int | None = None
    activity_name: str | None = None
    hours: float
    comments: str = ""
    spent_on: date
    created_on: str | None = None
    updated_on: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineTimeEntry:
        """Erstellt RedmineTimeEntry aus API-Response."""
        project = data.get("project", {})
        user = data.get("user", {})
        activity = data.get("activity", {})
        issue = data.get("issue", {})

        return cls(
            id=data.get("id", 0),
            project_id=project.get("id"),
            project_name=project.get("name"),
            issue_id=issue.get("id"),
            user_id=user.get("id"),
            user_name=user.get("name"),
            activity_id=activity.get("id"),
            activity_name=activity.get("name"),
            hours=data.get("hours", 0.0),
            comments=data.get("comments", ""),
            spent_on=date.fromisoformat(data.get("spent_on", "1970-01-01")),
            created_on=data.get("created_on"),
            updated_on=data.get("updated_on"),
        )


class RedmineJournalDetail(BaseModel):
    """Einzelne Änderung innerhalb eines Journal-Eintrags."""

    property: str  # "attr", "cf", "attachment", "relation"
    name: str  # Feldname (z.B. "status_id", "assigned_to_id")
    old_value: str | None = None
    new_value: str | None = None

    model_config = {"extra": "ignore"}


class RedmineJournal(RedmineApiModel):
    """Journal-Eintrag (Kommentar/Änderung) eines Issues."""

    id: int
    user_id: int | None = None
    user_name: str | None = None
    notes: str | None = None
    created_on: str | None = None
    private_notes: bool = False
    details: list[RedmineJournalDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineJournal:
        """Erstellt RedmineJournal aus API-Response."""
        user = data.get("user", {})
        details = [
            RedmineJournalDetail(**d) for d in data.get("details", [])
        ]
        return cls(
            id=data.get("id", 0),
            user_id=user.get("id"),
            user_name=user.get("name"),
            notes=data.get("notes"),
            created_on=data.get("created_on"),
            private_notes=data.get("private_notes", False),
            details=details,
        )


class RedmineAttachment(RedmineApiModel):
    """Redmine Dateianhang."""

    id: int
    filename: str = ""
    filesize: int = 0
    content_type: str | None = None
    description: str | None = None
    content_url: str | None = None
    author_id: int | None = None
    author_name: str | None = None
    created_on: str | None = None

    model_config = {"extra": "ignore"}

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineAttachment:
        """Erstellt RedmineAttachment aus API-Response."""
        author = data.get("author", {})
        return cls(
            id=data.get("id", 0),
            filename=data.get("filename", ""),
            filesize=data.get("filesize", 0),
            content_type=data.get("content_type"),
            description=data.get("description"),
            content_url=data.get("content_url"),
            author_id=author.get("id"),
            author_name=author.get("name"),
            created_on=data.get("created_on"),
        )


class RedmineRelation(BaseModel):
    """Redmine Issue-Relation."""

    id: int
    issue_id: int = 0
    issue_to_id: int = 0
    relation_type: str = ""
    delay: int | None = None

    model_config = {"extra": "ignore"}


class RedmineChangeset(RedmineApiModel):
    """Redmine Changeset (VCS-Commit)."""

    revision: str = ""
    user_id: int | None = None
    user_name: str | None = None
    comments: str | None = None
    committed_on: str | None = None

    model_config = {"extra": "ignore"}

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineChangeset:
        """Erstellt RedmineChangeset aus API-Response."""
        user = data.get("user", {})
        return cls(
            revision=data.get("revision", ""),
            user_id=user.get("id"),
            user_name=user.get("name"),
            comments=data.get("comments"),
            committed_on=data.get("committed_on"),
        )


class RedmineAllowedStatus(BaseModel):
    """Erlaubter Status-Übergang für ein Issue."""

    id: int
    name: str = ""
    is_closed: bool = False

    model_config = {"extra": "ignore"}


class RedmineIssue(RedmineApiModel):
    """Redmine Issue/Ticket."""

    id: int
    project_id: int | None = None
    project_name: str | None = None
    tracker_id: int | None = None
    tracker_name: str | None = None
    status_id: int | None = None
    status_name: str | None = None
    priority_id: int | None = None
    priority_name: str | None = None
    author_id: int | None = None
    author_name: str | None = None
    assigned_to_id: int | None = None
    assigned_to_name: str | None = None
    subject: str = ""
    description: str | None = None
    done_ratio: int = 0
    estimated_hours: float | None = None
    spent_hours: float | None = None
    created_on: str | None = None
    updated_on: str | None = None
    custom_fields: list[RedmineCustomField] | None = None
    journals: list[RedmineJournal] | None = None
    attachments: list[RedmineAttachment] | None = None
    relations: list[RedmineRelation] | None = None
    watchers: list[RedmineUser] | None = None
    changesets: list[RedmineChangeset] | None = None
    allowed_statuses: list[RedmineAllowedStatus] | None = None
    children: list[RedmineIssue] | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineIssue:
        """Erstellt RedmineIssue aus API-Response."""
        project = data.get("project", {})
        tracker = data.get("tracker", {})
        status = data.get("status", {})
        priority = data.get("priority", {})
        author = data.get("author", {})
        assigned_to = data.get("assigned_to", {})

        # Custom Fields parsen
        custom_fields = None
        if "custom_fields" in data:
            custom_fields = [
                RedmineCustomField(**cf) for cf in data["custom_fields"]
            ]

        # Journals parsen
        journals = None
        if "journals" in data:
            journals = [
                RedmineJournal.from_api_response(j) for j in data["journals"]
            ]

        # Attachments parsen
        attachments = None
        if "attachments" in data:
            attachments = [
                RedmineAttachment.from_api_response(a)
                for a in data["attachments"]
            ]

        # Relations parsen
        relations = None
        if "relations" in data:
            relations = [RedmineRelation(**r) for r in data["relations"]]

        # Watchers parsen
        watchers = None
        if "watchers" in data:
            watchers = [RedmineUser(**w) for w in data["watchers"]]

        # Changesets parsen
        changesets = None
        if "changesets" in data:
            changesets = [
                RedmineChangeset.from_api_response(c)
                for c in data["changesets"]
            ]

        # Allowed Statuses parsen
        allowed_statuses = None
        if "allowed_statuses" in data:
            allowed_statuses = [
                RedmineAllowedStatus(**s) for s in data["allowed_statuses"]
            ]

        # Children parsen (rekursiv)
        children = None
        if "children" in data:
            children = [
                RedmineIssue.from_api_response(c) for c in data["children"]
            ]

        return cls(
            id=data.get("id", 0),
            project_id=project.get("id"),
            project_name=project.get("name"),
            tracker_id=tracker.get("id"),
            tracker_name=tracker.get("name"),
            status_id=status.get("id"),
            status_name=status.get("name"),
            priority_id=priority.get("id"),
            priority_name=priority.get("name"),
            author_id=author.get("id"),
            author_name=author.get("name"),
            assigned_to_id=assigned_to.get("id"),
            assigned_to_name=assigned_to.get("name"),
            subject=data.get("subject", ""),
            description=data.get("description"),
            done_ratio=data.get("done_ratio", 0),
            estimated_hours=data.get("estimated_hours"),
            spent_hours=data.get("spent_hours"),
            created_on=data.get("created_on"),
            updated_on=data.get("updated_on"),
            custom_fields=custom_fields,
            journals=journals,
            attachments=attachments,
            relations=relations,
            watchers=watchers,
            changesets=changesets,
            allowed_statuses=allowed_statuses,
            children=children,
        )

    def get_custom_field(self, name: str) -> str | list[str] | None:
        """Gibt den Wert eines Custom Fields zurück."""
        if self.custom_fields is not None:
            for cf in self.custom_fields:
                if cf.name == name:
                    return cf.value
        return None

    def get_custom_field_by_id(self, field_id: int) -> str | list[str] | None:
        """Gibt den Wert eines Custom Fields anhand der ID zurück."""
        if self.custom_fields is not None:
            for cf in self.custom_fields:
                if cf.id == field_id:
                    return cf.value
        return None


class RedmineWikiPage(RedmineApiModel):
    """Redmine Wiki-Seite."""

    title: str = ""
    text: str | None = None
    version: int | None = None
    author_id: int | None = None
    author_name: str | None = None
    comments: str | None = None
    created_on: str | None = None
    updated_on: str | None = None
    parent_title: str | None = None
    attachments: list[RedmineAttachment] | None = None

    model_config = {"extra": "ignore"}

    @classmethod
    def from_api_response(cls, data: dict) -> RedmineWikiPage:
        """Erstellt RedmineWikiPage aus API-Response."""
        author = data.get("author", {})
        parent = data.get("parent", {})

        attachments = None
        if "attachments" in data:
            attachments = [
                RedmineAttachment.from_api_response(a)
                for a in data["attachments"]
            ]

        return cls(
            title=data.get("title", ""),
            text=data.get("text"),
            version=data.get("version"),
            author_id=author.get("id"),
            author_name=author.get("name"),
            comments=data.get("comments"),
            created_on=data.get("created_on"),
            updated_on=data.get("updated_on"),
            parent_title=parent.get("title"),
            attachments=attachments,
        )


# Self-Referenz für children auflösen
RedmineIssue.model_rebuild()
