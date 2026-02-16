"""
Redmine REST API Client (synchron).

Beispiel:
    from redmine_client import RedmineClient

    with RedmineClient("https://redmine.example.com", "api-key") as client:
        projects = client.get_projects()
        issues = client.get_issues(assigned_to_id="me", status_id="open")
"""

import logging
import warnings
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Generator

import httpx

from .exceptions import (
    RedmineAuthenticationError,
    RedmineNotFoundError,
    RedmineValidationError,
)
from .models import (
    RedmineAttachment,
    RedmineCustomFieldDefinition,
    RedmineIssue,
    RedmineProject,
    RedmineTimeEntry,
    RedmineUser,
    RedmineWikiPage,
)

logger = logging.getLogger(__name__)


class RedmineClient:
    """
    Synchroner Python-Client für die Redmine REST-API.

    Args:
        base_url: Basis-URL der Redmine-Instanz
        api_key: Redmine API-Key
        timeout: Request-Timeout in Sekunden (default: 30)

    Beispiel:
        with RedmineClient("https://redmine.example.com", "api-key") as client:
            issues = client.get_issues(assigned_to_id="me")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialisierter HTTP-Client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "X-Redmine-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def close(self) -> None:
        """Schließt den HTTP-Client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "RedmineClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @contextmanager
    def impersonate(self, login: str) -> Generator["RedmineClient", None, None]:
        """
        Context Manager für User-Impersonation via X-Redmine-Switch-User.

        Erzeugt einen neuen Client der alle Anfragen im Namen des
        angegebenen Benutzers ausführt. Erfordert einen Admin-API-Key.

        Args:
            login: Login-Name des Benutzers

        Beispiel:
            with client.impersonate("john.doe") as user_client:
                issues = user_client.get_issues(assigned_to_id="me")
        """
        impersonated = RedmineClient(self.base_url, self.api_key, self.timeout)
        impersonated.client.headers["X-Redmine-Switch-User"] = login
        try:
            yield impersonated
        finally:
            impersonated.close()

    # === HTTP Methods ===

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Führt HTTP-Request aus und behandelt Fehler."""
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        logger.debug(f"{method} {path} params={params} json={json}")

        response = self.client.request(
            method=method,
            url=path,
            params=params,
            json=json,
        )

        if response.status_code == 401:
            raise RedmineAuthenticationError(
                "Authentifizierung fehlgeschlagen", status_code=401
            )

        if response.status_code == 404:
            raise RedmineNotFoundError(
                f"Ressource nicht gefunden: {path}", status_code=404
            )

        if response.status_code == 422:
            error_response = response.json() if response.content else {}
            errors = error_response.get("errors", [])
            raise RedmineValidationError(
                f"Validierungsfehler: {errors}",
                status_code=422,
                response=error_response,
            )

        response.raise_for_status()

        if response.status_code == 204:
            return {}

        return response.json()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET-Request."""
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: dict[str, Any]) -> dict:
        """POST-Request."""
        return self._request("POST", path, json=json)

    def _put(self, path: str, json: dict[str, Any]) -> dict:
        """PUT-Request."""
        return self._request("PUT", path, json=json)

    def _delete(self, path: str) -> dict:
        """DELETE-Request."""
        return self._request("DELETE", path)

    def _upload_file(self, file_data: bytes, filename: str) -> dict[str, Any]:
        """Upload-Request mit octet-stream Content-Type."""
        logger.debug(f"POST /uploads.json filename={filename}")

        response = self.client.post(
            "/uploads.json",
            content=file_data,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Redmine-API-Key": self.api_key,
            },
            params={"filename": filename},
        )

        if response.status_code == 401:
            raise RedmineAuthenticationError(
                "Authentifizierung fehlgeschlagen", status_code=401
            )

        response.raise_for_status()
        return response.json()

    def _download_file(self, url: str) -> bytes:
        """Download einer Datei als Bytes."""
        logger.debug(f"GET {url}")

        response = self.client.get(
            url,
            headers={"X-Redmine-API-Key": self.api_key},
        )

        if response.status_code == 401:
            raise RedmineAuthenticationError(
                "Authentifizierung fehlgeschlagen", status_code=401
            )

        if response.status_code == 404:
            raise RedmineNotFoundError(
                f"Datei nicht gefunden: {url}", status_code=404
            )

        response.raise_for_status()
        return response.content

    def _paginate(
        self,
        path: str,
        key: str,
        params: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Iteriert durch alle Seiten einer paginierten Ressource."""
        params = params or {}
        params["limit"] = limit

        all_records = []
        offset = 0

        while True:
            params["offset"] = offset
            response = self._get(path, params)

            records = response.get(key, [])
            all_records.extend(records)

            total_count = response.get("total_count", len(records))
            if offset + len(records) >= total_count:
                break

            offset += limit

        return all_records

    # === Users ===

    def get_current_user(self) -> dict:
        """Ruft den aktuellen authentifizierten User ab."""
        response = self._get("/users/current.json")
        return response.get("user", {})

    def get_user(self, user_id: int) -> RedmineUser:
        """Ruft einzelnen User ab."""
        response = self._get(f"/users/{user_id}.json")
        return RedmineUser(**response.get("user", {}))

    def get_users(
        self, status: int | None = None, limit: int = 100
    ) -> list[RedmineUser]:
        """
        Ruft Benutzer ab.

        Args:
            status: 0=anonym, 1=aktiv, 2=registriert, 3=gesperrt
            limit: Max. Einträge pro Seite
        """
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status

        records = self._paginate("/users.json", "users", params, limit)
        return [RedmineUser(**r) for r in records]

    # === Projects ===

    def get_projects(
        self, include_closed: bool = False, limit: int = 100
    ) -> list[RedmineProject]:
        """Ruft alle Projekte ab."""
        params: dict[str, Any] = {}
        if not include_closed:
            params["status"] = 1  # Nur aktive Projekte

        records = self._paginate("/projects.json", "projects", params, limit)
        return [RedmineProject(**r) for r in records]

    def get_project(self, project_id: int | str) -> RedmineProject:
        """Ruft einzelnes Projekt ab."""
        response = self._get(f"/projects/{project_id}.json")
        return RedmineProject(**response.get("project", {}))

    # === Time Entries ===

    def get_time_entries(
        self,
        user_id: int | None = None,
        project_id: int | str | None = None,
        issue_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        activity_id: int | None = None,
        limit: int = 100,
    ) -> list[RedmineTimeEntry]:
        """Ruft Zeitbuchungen ab."""
        params: dict[str, Any] = {}
        if user_id:
            params["user_id"] = user_id
        if project_id:
            params["project_id"] = project_id
        if issue_id:
            params["issue_id"] = issue_id
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        if activity_id:
            params["activity_id"] = activity_id

        records = self._paginate("/time_entries.json", "time_entries", params, limit)
        return [RedmineTimeEntry.from_api_response(r) for r in records]

    def get_time_entry(self, time_entry_id: int) -> RedmineTimeEntry:
        """Ruft einzelne Zeitbuchung ab."""
        response = self._get(f"/time_entries/{time_entry_id}.json")
        return RedmineTimeEntry.from_api_response(response.get("time_entry", {}))

    # === Issues ===

    def get_issues(
        self,
        project_id: int | str | None = None,
        assigned_to_id: int | str | None = None,
        status_id: str | int | None = None,
        tracker_id: int | None = None,
        updated_on: str | None = None,
        created_on: str | None = None,
        limit: int = 100,
    ) -> list[RedmineIssue]:
        """
        Ruft Issues ab.

        Args:
            project_id: Filter nach Projekt
            assigned_to_id: Filter nach Zugewiesenem (oder "me")
            status_id: Filter nach Status ("open", "closed", "*", oder ID)
            tracker_id: Filter nach Tracker
            updated_on: Filter nach Update-Datum (z.B. ">=2025-01-01")
            created_on: Filter nach Erstelldatum (z.B. ">=2025-01-01")
            limit: Max. Einträge pro Seite
        """
        params: dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if assigned_to_id:
            params["assigned_to_id"] = assigned_to_id
        if status_id:
            params["status_id"] = status_id
        if tracker_id:
            params["tracker_id"] = tracker_id
        if updated_on:
            params["updated_on"] = updated_on
        if created_on:
            params["created_on"] = created_on

        records = self._paginate("/issues.json", "issues", params, limit)
        return [RedmineIssue.from_api_response(r) for r in records]

    def get_issue(
        self,
        issue_id: int,
        include: list[str] | None = None,
        include_journals: bool = False,
    ) -> RedmineIssue:
        """
        Ruft einzelnes Issue ab.

        Args:
            issue_id: Issue-ID
            include: Liste von Include-Optionen, z.B.
                ["journals", "attachments", "relations", "watchers",
                 "changesets", "allowed_statuses", "children"]
            include_journals: Deprecated. Verwende include=["journals"].
        """
        includes = list(include) if include else []

        if include_journals:
            warnings.warn(
                "include_journals ist deprecated, verwende include=['journals']",
                DeprecationWarning,
                stacklevel=2,
            )
            if "journals" not in includes:
                includes.append("journals")

        params: dict[str, Any] = {}
        if includes:
            params["include"] = ",".join(includes)

        response = self._get(f"/issues/{issue_id}.json", params=params)
        return RedmineIssue.from_api_response(response.get("issue", {}))

    def create_issue(
        self,
        project_id: int | str,
        subject: str,
        description: str = "",
        tracker_id: int | None = None,
        priority_id: int | None = None,
        assigned_to_id: int | None = None,
        parent_issue_id: int | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
        uploads: list[dict[str, Any]] | None = None,
    ) -> RedmineIssue:
        """
        Erstellt ein neues Issue.

        Args:
            project_id: Projekt-ID oder Identifier
            subject: Betreff
            description: Beschreibung
            tracker_id: Tracker-ID
            priority_id: Prioritäts-ID
            assigned_to_id: Zugewiesen an (User-ID)
            parent_issue_id: Parent-Issue für Unteraufgaben
            custom_fields: Custom Fields als Liste von {id, value} Dicts
            uploads: Liste von Upload-Dicts mit {token, filename, content_type}
        """
        issue_data: dict[str, Any] = {
            "project_id": project_id,
            "subject": subject,
            "description": description,
        }
        if tracker_id:
            issue_data["tracker_id"] = tracker_id
        if priority_id:
            issue_data["priority_id"] = priority_id
        if assigned_to_id:
            issue_data["assigned_to_id"] = assigned_to_id
        if parent_issue_id:
            issue_data["parent_issue_id"] = parent_issue_id
        if custom_fields:
            issue_data["custom_fields"] = custom_fields
        if uploads:
            issue_data["uploads"] = uploads

        response = self._post("/issues.json", json={"issue": issue_data})
        return RedmineIssue.from_api_response(response.get("issue", {}))

    def update_issue(
        self,
        issue_id: int,
        subject: str | None = None,
        description: str | None = None,
        status_id: int | None = None,
        priority_id: int | None = None,
        assigned_to_id: int | None = None,
        done_ratio: int | None = None,
        notes: str | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
        uploads: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Aktualisiert ein bestehendes Issue.

        Args:
            issue_id: Issue-ID
            subject: Neuer Betreff
            description: Neue Beschreibung
            status_id: Neuer Status
            priority_id: Neue Priorität
            assigned_to_id: Neue Zuweisung
            done_ratio: Fortschritt in % (0-100)
            notes: Kommentar hinzufügen
            custom_fields: Custom Fields als Liste von {id, value} Dicts
            uploads: Liste von Upload-Dicts mit {token, filename, content_type}
        """
        issue_data: dict[str, Any] = {}

        if subject is not None:
            issue_data["subject"] = subject
        if description is not None:
            issue_data["description"] = description
        if status_id is not None:
            issue_data["status_id"] = status_id
        if priority_id is not None:
            issue_data["priority_id"] = priority_id
        if assigned_to_id is not None:
            issue_data["assigned_to_id"] = assigned_to_id
        if done_ratio is not None:
            issue_data["done_ratio"] = done_ratio
        if notes is not None:
            issue_data["notes"] = notes
        if custom_fields is not None:
            issue_data["custom_fields"] = custom_fields
        if uploads is not None:
            issue_data["uploads"] = uploads

        self._put(f"/issues/{issue_id}.json", json={"issue": issue_data})

    def add_issue_note(self, issue_id: int, notes: str) -> None:
        """Fügt einen Kommentar zu einem Issue hinzu."""
        self.update_issue(issue_id, notes=notes)

    # === Custom Fields ===

    def get_custom_fields(self) -> list[RedmineCustomFieldDefinition]:
        """
        Ruft alle Custom Field Definitionen ab.

        Hinweis: Benötigt Admin-Rechte.
        """
        response = self._get("/custom_fields.json")
        return [
            RedmineCustomFieldDefinition(**cf)
            for cf in response.get("custom_fields", [])
        ]

    def get_issue_custom_fields(self) -> list[RedmineCustomFieldDefinition]:
        """Ruft nur Issue Custom Fields ab."""
        all_fields = self.get_custom_fields()
        return [f for f in all_fields if f.customized_type == "issue"]

    def find_custom_field_by_name(
        self, name: str, customized_type: str = "issue"
    ) -> RedmineCustomFieldDefinition | None:
        """Sucht ein Custom Field anhand des Namens."""
        all_fields = self.get_custom_fields()
        for f in all_fields:
            if f.name == name and f.customized_type == customized_type:
                return f
        return None

    # === Enumerations ===

    def get_trackers(self) -> list[dict]:
        """Ruft verfügbare Tracker ab (Bug, Feature, etc.)."""
        response = self._get("/trackers.json")
        return response.get("trackers", [])

    def get_issue_statuses(self) -> list[dict]:
        """Ruft verfügbare Issue-Status ab."""
        response = self._get("/issue_statuses.json")
        return response.get("issue_statuses", [])

    def get_issue_priorities(self) -> list[dict]:
        """Ruft verfügbare Prioritäten ab."""
        response = self._get("/enumerations/issue_priorities.json")
        return response.get("issue_priorities", [])

    def get_time_entry_activities(self) -> list[dict]:
        """Ruft verfügbare Aktivitätstypen ab."""
        response = self._get("/enumerations/time_entry_activities.json")
        return response.get("time_entry_activities", [])

    # === Wiki ===

    def get_wiki_pages(self, project_id: int | str) -> list[RedmineWikiPage]:
        """
        Ruft die Wiki-Seitenübersicht eines Projekts ab.

        Args:
            project_id: Projekt-ID oder Identifier
        """
        response = self._get(f"/projects/{project_id}/wiki/index.json")
        return [
            RedmineWikiPage.from_api_response(w)
            for w in response.get("wiki_pages", [])
        ]

    def get_wiki_page(
        self,
        project_id: int | str,
        title: str,
        include_attachments: bool = False,
    ) -> RedmineWikiPage:
        """
        Ruft eine Wiki-Seite ab.

        Args:
            project_id: Projekt-ID oder Identifier
            title: Seitentitel
            include_attachments: Inklusive Dateianhänge
        """
        params: dict[str, Any] = {}
        if include_attachments:
            params["include"] = "attachments"

        response = self._get(
            f"/projects/{project_id}/wiki/{title}.json", params=params
        )
        return RedmineWikiPage.from_api_response(response.get("wiki_page", {}))

    def create_or_update_wiki_page(
        self,
        project_id: int | str,
        title: str,
        text: str,
        comments: str | None = None,
    ) -> None:
        """
        Erstellt oder aktualisiert eine Wiki-Seite.

        Args:
            project_id: Projekt-ID oder Identifier
            title: Seitentitel
            text: Wiki-Inhalt (Textile/Markdown)
            comments: Änderungskommentar
        """
        wiki_data: dict[str, Any] = {"text": text}
        if comments is not None:
            wiki_data["comments"] = comments

        self._put(
            f"/projects/{project_id}/wiki/{title}.json",
            json={"wiki_page": wiki_data},
        )

    def delete_wiki_page(self, project_id: int | str, title: str) -> None:
        """
        Löscht eine Wiki-Seite.

        Args:
            project_id: Projekt-ID oder Identifier
            title: Seitentitel
        """
        self._delete(f"/projects/{project_id}/wiki/{title}.json")

    # === Attachments ===

    def upload_file(
        self,
        file_data: Path | str | bytes,
        filename: str | None = None,
    ) -> str:
        """
        Lädt eine Datei hoch und gibt das Upload-Token zurück.

        Args:
            file_data: Dateipfad (Path/str) oder Bytes-Daten
            filename: Dateiname (wird aus Pfad abgeleitet falls nicht angegeben)

        Returns:
            Upload-Token für die Verwendung in create_issue/update_issue
        """
        if isinstance(file_data, (str, Path)):
            path = Path(file_data)
            if filename is None:
                filename = path.name
            file_data = path.read_bytes()

        if filename is None:
            filename = "upload"

        response = self._upload_file(file_data, filename)
        token: str = response.get("upload", {}).get("token", "")
        return token

    def get_attachment(self, attachment_id: int) -> RedmineAttachment:
        """
        Ruft Attachment-Metadaten ab.

        Args:
            attachment_id: Attachment-ID
        """
        response = self._get(f"/attachments/{attachment_id}.json")
        return RedmineAttachment.from_api_response(
            response.get("attachment", {})
        )

    def download_attachment(self, attachment_id: int) -> bytes:
        """
        Lädt ein Attachment herunter.

        Args:
            attachment_id: Attachment-ID

        Returns:
            Dateiinhalt als Bytes
        """
        attachment = self.get_attachment(attachment_id)
        if not attachment.content_url:
            raise RedmineNotFoundError(
                f"Keine Download-URL für Attachment {attachment_id}",
                status_code=404,
            )
        return self._download_file(attachment.content_url)

    def delete_attachment(self, attachment_id: int) -> None:
        """
        Löscht ein Attachment.

        Args:
            attachment_id: Attachment-ID
        """
        self._delete(f"/attachments/{attachment_id}.json")
