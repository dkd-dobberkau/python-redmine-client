"""
Pydantic-Modelle für Redmine API Ressourcen.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class RedmineUser(BaseModel):
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


class RedmineProject(BaseModel):
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
        if not self.custom_fields:
            return None
        for cf in self.custom_fields:
            if cf.name == name:
                return cf.value
        return None


class RedmineTimeEntry(BaseModel):
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
    def from_api_response(cls, data: dict) -> "RedmineTimeEntry":
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


class RedmineIssue(BaseModel):
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

    @classmethod
    def from_api_response(cls, data: dict) -> "RedmineIssue":
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
        )

    def get_custom_field(self, name: str) -> str | list[str] | None:
        """Gibt den Wert eines Custom Fields zurück."""
        if not self.custom_fields:
            return None
        for cf in self.custom_fields:
            if cf.name == name:
                return cf.value
        return None

    def get_custom_field_by_id(self, field_id: int) -> str | list[str] | None:
        """Gibt den Wert eines Custom Fields anhand der ID zurück."""
        if not self.custom_fields:
            return None
        for cf in self.custom_fields:
            if cf.id == field_id:
                return cf.value
        return None
