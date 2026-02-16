"""Tests für den synchronen RedmineClient."""

import warnings

import pytest
from pytest_httpx import HTTPXMock

from redmine_client import (
    RedmineAuthenticationError,
    RedmineClient,
    RedmineNotFoundError,
    RedmineValidationError,
)


@pytest.fixture
def client():
    """Erstellt einen Test-Client."""
    return RedmineClient("https://redmine.example.com", "test-api-key")


class TestRedmineClient:
    """Tests für grundlegende Client-Funktionalität."""

    def test_client_initialization(self, client: RedmineClient):
        """Client wird korrekt initialisiert."""
        assert client.base_url == "https://redmine.example.com"
        assert client.api_key == "test-api-key"
        assert client.timeout == 30.0

    def test_client_strips_trailing_slash(self):
        """Trailing Slash wird entfernt."""
        client = RedmineClient("https://redmine.example.com/", "key")
        assert client.base_url == "https://redmine.example.com"

    def test_context_manager(self):
        """Context Manager funktioniert."""
        with RedmineClient("https://redmine.example.com", "key") as client:
            assert client is not None


class TestAuthentication:
    """Tests für Authentifizierung."""

    def test_auth_error_on_401(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """401 wirft RedmineAuthenticationError."""
        httpx_mock.add_response(status_code=401)

        with pytest.raises(RedmineAuthenticationError):
            client.get_current_user()


class TestNotFound:
    """Tests für 404-Fehler."""

    def test_not_found_on_404(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """404 wirft RedmineNotFoundError."""
        httpx_mock.add_response(status_code=404)

        with pytest.raises(RedmineNotFoundError):
            client.get_issue(99999)


class TestValidation:
    """Tests für Validierungsfehler."""

    def test_validation_error_on_422(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """422 wirft RedmineValidationError."""
        httpx_mock.add_response(
            status_code=422,
            json={"errors": ["Subject can't be blank"]},
        )

        with pytest.raises(RedmineValidationError) as exc_info:
            client.create_issue("project", "")

        assert "Subject can't be blank" in str(exc_info.value)


class TestUsers:
    """Tests für User-Operationen."""

    def test_get_current_user(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Aktueller User wird abgerufen."""
        httpx_mock.add_response(
            json={
                "user": {
                    "id": 1,
                    "login": "testuser",
                    "firstname": "Test",
                    "lastname": "User",
                    "mail": "test@example.com",
                }
            }
        )

        user = client.get_current_user()

        assert user["id"] == 1
        assert user["login"] == "testuser"

    def test_get_user(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Einzelner User wird abgerufen."""
        httpx_mock.add_response(
            json={
                "user": {
                    "id": 42,
                    "login": "johndoe",
                    "firstname": "John",
                    "lastname": "Doe",
                }
            }
        )

        user = client.get_user(42)

        assert user.id == 42
        assert user.login == "johndoe"
        assert user.full_name == "John Doe"


class TestProjects:
    """Tests für Projekt-Operationen."""

    def test_get_projects(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Projekte werden abgerufen."""
        httpx_mock.add_response(
            json={
                "projects": [
                    {"id": 1, "name": "Project A", "identifier": "project-a"},
                    {"id": 2, "name": "Project B", "identifier": "project-b"},
                ],
                "total_count": 2,
            }
        )

        projects = client.get_projects()

        assert len(projects) == 2
        assert projects[0].name == "Project A"
        assert projects[1].identifier == "project-b"


class TestIssues:
    """Tests für Issue-Operationen."""

    def test_get_issues(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Issues werden abgerufen."""
        httpx_mock.add_response(
            json={
                "issues": [
                    {
                        "id": 123,
                        "subject": "Test Issue",
                        "project": {"id": 1, "name": "Project A"},
                        "tracker": {"id": 1, "name": "Bug"},
                        "status": {"id": 1, "name": "New"},
                        "priority": {"id": 2, "name": "Normal"},
                        "author": {"id": 1, "name": "Test User"},
                    }
                ],
                "total_count": 1,
            }
        )

        issues = client.get_issues(assigned_to_id="me", status_id="open")

        assert len(issues) == 1
        assert issues[0].id == 123
        assert issues[0].subject == "Test Issue"
        assert issues[0].tracker_name == "Bug"

    def test_get_issue_with_custom_fields(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue mit Custom Fields wird abgerufen."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 456,
                    "subject": "Issue mit Sprint",
                    "project": {"id": 1, "name": "Project A"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "status": {"id": 1, "name": "New"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "Test User"},
                    "custom_fields": [
                        {"id": 42, "name": "Sprint", "value": "2026-KW03-KW04"},
                        {"id": 43, "name": "Team", "value": "Backend"},
                    ],
                }
            }
        )

        issue = client.get_issue(456)

        assert issue.id == 456
        assert issue.get_custom_field("Sprint") == "2026-KW03-KW04"
        assert issue.get_custom_field("Team") == "Backend"
        assert issue.get_custom_field_by_id(42) == "2026-KW03-KW04"
        assert issue.get_custom_field("Nonexistent") is None

    def test_create_issue(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Issue wird erstellt."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 789,
                    "subject": "Neues Issue",
                    "project": {"id": 1, "name": "Project A"},
                    "tracker": {"id": 2, "name": "Feature"},
                    "status": {"id": 1, "name": "New"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "Test User"},
                }
            }
        )

        issue = client.create_issue(
            project_id="project-a",
            subject="Neues Issue",
            tracker_id=2,
        )

        assert issue.id == 789
        assert issue.subject == "Neues Issue"

    def test_update_issue_with_custom_fields(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue wird mit Custom Fields aktualisiert."""
        httpx_mock.add_response(status_code=204)

        # Sollte keinen Fehler werfen
        client.update_issue(
            issue_id=123,
            subject="Aktualisierter Betreff",
            custom_fields=[{"id": 42, "value": "2026-KW05-KW06"}],
        )

        # Request wurde gesendet
        request = httpx_mock.get_request()
        assert request is not None
        assert b'"custom_fields"' in request.content

    def test_get_issue_with_journals(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue mit Journals wird korrekt geparst."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 100,
                    "subject": "Issue mit Historie",
                    "project": {"id": 1, "name": "Project A"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "status": {"id": 2, "name": "In Progress"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "Test User"},
                    "journals": [
                        {
                            "id": 1,
                            "user": {"id": 1, "name": "Test User"},
                            "notes": "Erster Kommentar",
                            "created_on": "2026-01-15T10:00:00Z",
                            "private_notes": False,
                            "details": [],
                        },
                        {
                            "id": 2,
                            "user": {"id": 2, "name": "Admin"},
                            "notes": "",
                            "created_on": "2026-01-16T14:30:00Z",
                            "private_notes": False,
                            "details": [
                                {
                                    "property": "attr",
                                    "name": "status_id",
                                    "old_value": "1",
                                    "new_value": "2",
                                },
                                {
                                    "property": "attr",
                                    "name": "assigned_to_id",
                                    "old_value": None,
                                    "new_value": "3",
                                },
                            ],
                        },
                    ],
                }
            }
        )

        issue = client.get_issue(100, include_journals=True)

        assert issue.id == 100
        assert issue.journals is not None
        assert len(issue.journals) == 2

        # Erster Journal-Eintrag: Kommentar
        j1 = issue.journals[0]
        assert j1.id == 1
        assert j1.user_name == "Test User"
        assert j1.notes == "Erster Kommentar"
        assert j1.created_on == "2026-01-15T10:00:00Z"
        assert len(j1.details) == 0

        # Zweiter Journal-Eintrag: Statusänderung
        j2 = issue.journals[1]
        assert j2.id == 2
        assert j2.user_name == "Admin"
        assert len(j2.details) == 2
        assert j2.details[0].property == "attr"
        assert j2.details[0].name == "status_id"
        assert j2.details[0].old_value == "1"
        assert j2.details[0].new_value == "2"
        assert j2.details[1].name == "assigned_to_id"
        assert j2.details[1].old_value is None
        assert j2.details[1].new_value == "3"

    def test_get_issue_without_journals(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue ohne Journals hat journals=None."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 101,
                    "subject": "Issue ohne Journals",
                    "project": {"id": 1, "name": "Project A"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "status": {"id": 1, "name": "New"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "Test User"},
                }
            }
        )

        issue = client.get_issue(101)

        assert issue.journals is None

    def test_get_issue_include_journals_sends_param(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """include_journals sendet den richtigen Query-Parameter."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 102,
                    "subject": "Test",
                    "project": {"id": 1, "name": "P"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "status": {"id": 1, "name": "New"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "User"},
                    "journals": [],
                }
            }
        )

        client.get_issue(102, include_journals=True)

        request = httpx_mock.get_request()
        assert request is not None
        assert "include=journals" in str(request.url)

    def test_add_issue_note(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Kommentar wird zu Issue hinzugefügt."""
        httpx_mock.add_response(status_code=204)

        client.add_issue_note(123, "Mein Kommentar")

        request = httpx_mock.get_request()
        assert request is not None
        assert b'"notes"' in request.content
        assert b"Mein Kommentar" in request.content


class TestCustomFields:
    """Tests für Custom Field Operationen."""

    def test_get_custom_fields(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Custom Fields werden abgerufen."""
        httpx_mock.add_response(
            json={
                "custom_fields": [
                    {
                        "id": 42,
                        "name": "Sprint",
                        "customized_type": "issue",
                        "field_format": "string",
                    },
                    {
                        "id": 43,
                        "name": "Department",
                        "customized_type": "user",
                        "field_format": "list",
                    },
                ]
            }
        )

        fields = client.get_custom_fields()

        assert len(fields) == 2
        assert fields[0].name == "Sprint"
        assert fields[0].customized_type == "issue"

    def test_get_issue_custom_fields(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Nur Issue Custom Fields werden gefiltert."""
        httpx_mock.add_response(
            json={
                "custom_fields": [
                    {"id": 42, "name": "Sprint", "customized_type": "issue"},
                    {"id": 43, "name": "Department", "customized_type": "user"},
                    {"id": 44, "name": "Estimate", "customized_type": "issue"},
                ]
            }
        )

        fields = client.get_issue_custom_fields()

        assert len(fields) == 2
        assert all(f.customized_type == "issue" for f in fields)

    def test_find_custom_field_by_name(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Custom Field wird nach Namen gefunden."""
        httpx_mock.add_response(
            json={
                "custom_fields": [
                    {"id": 42, "name": "Sprint", "customized_type": "issue"},
                    {"id": 43, "name": "Team", "customized_type": "issue"},
                ]
            }
        )

        field = client.find_custom_field_by_name("Sprint")

        assert field is not None
        assert field.id == 42
        assert field.name == "Sprint"

    def test_find_custom_field_not_found(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """None wird zurückgegeben wenn Custom Field nicht existiert."""
        httpx_mock.add_response(json={"custom_fields": []})

        field = client.find_custom_field_by_name("Nonexistent")

        assert field is None


class TestPagination:
    """Tests für Paginierung."""

    def test_pagination_multiple_pages(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Mehrere Seiten werden automatisch abgerufen."""
        # Erste Seite
        httpx_mock.add_response(
            json={
                "issues": [{"id": i, "subject": f"Issue {i}"} for i in range(1, 101)],
                "total_count": 150,
            }
        )
        # Zweite Seite
        httpx_mock.add_response(
            json={
                "issues": [
                    {"id": i, "subject": f"Issue {i}"} for i in range(101, 151)
                ],
                "total_count": 150,
            }
        )

        issues = client.get_issues()

        assert len(issues) == 150
        assert issues[0].id == 1
        assert issues[149].id == 150


class TestIncludeParameters:
    """Tests für erweiterte Include-Parameter."""

    def _issue_response(self, **extra):
        """Hilfsmethode für Issue-Response mit optionalen Include-Daten."""
        base = {
            "id": 200,
            "subject": "Include Test",
            "project": {"id": 1, "name": "P"},
            "tracker": {"id": 1, "name": "Bug"},
            "status": {"id": 1, "name": "New"},
            "priority": {"id": 2, "name": "Normal"},
            "author": {"id": 1, "name": "User"},
        }
        base.update(extra)
        return {"issue": base}

    def test_include_list_sends_correct_param(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Include-Liste sendet korrekten Query-Parameter."""
        httpx_mock.add_response(json=self._issue_response())

        client.get_issue(200, include=["journals", "attachments", "relations"])

        request = httpx_mock.get_request()
        assert request is not None
        url_str = str(request.url)
        assert "include=" in url_str
        assert "journals" in url_str
        assert "attachments" in url_str
        assert "relations" in url_str

    def test_include_journals_deprecated_warning(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """include_journals erzeugt DeprecationWarning."""
        httpx_mock.add_response(json=self._issue_response(journals=[]))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.get_issue(200, include_journals=True)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_include_journals_merges_with_include(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """include_journals wird mit include-Liste gemergt ohne Duplikate."""
        httpx_mock.add_response(json=self._issue_response(journals=[]))

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            client.get_issue(
                200,
                include=["journals", "attachments"],
                include_journals=True,
            )

        request = httpx_mock.get_request()
        url_str = str(request.url)
        # journals sollte nur einmal vorkommen
        assert url_str.count("journals") == 1
        assert "attachments" in url_str

    def test_attachments_parsed(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Attachments werden korrekt geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                attachments=[
                    {
                        "id": 10,
                        "filename": "doc.pdf",
                        "filesize": 12345,
                        "content_type": "application/pdf",
                        "description": "Ein Dokument",
                        "content_url": "https://redmine.example.com/attachments/download/10/doc.pdf",
                        "author": {"id": 1, "name": "Test User"},
                        "created_on": "2026-01-20T10:00:00Z",
                    }
                ]
            )
        )

        issue = client.get_issue(200, include=["attachments"])

        assert issue.attachments is not None
        assert len(issue.attachments) == 1
        att = issue.attachments[0]
        assert att.id == 10
        assert att.filename == "doc.pdf"
        assert att.filesize == 12345
        assert att.content_type == "application/pdf"
        assert att.author_name == "Test User"

    def test_relations_parsed(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Relations werden korrekt geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                relations=[
                    {
                        "id": 5,
                        "issue_id": 200,
                        "issue_to_id": 201,
                        "relation_type": "relates",
                    }
                ]
            )
        )

        issue = client.get_issue(200, include=["relations"])

        assert issue.relations is not None
        assert len(issue.relations) == 1
        rel = issue.relations[0]
        assert rel.id == 5
        assert rel.issue_to_id == 201
        assert rel.relation_type == "relates"

    def test_watchers_parsed(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Watchers werden als RedmineUser geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                watchers=[
                    {"id": 1, "login": "user1", "firstname": "Max", "lastname": "Muster"},
                    {"id": 2, "login": "user2", "firstname": "Erika", "lastname": "Muster"},
                ]
            )
        )

        issue = client.get_issue(200, include=["watchers"])

        assert issue.watchers is not None
        assert len(issue.watchers) == 2
        assert issue.watchers[0].full_name == "Max Muster"

    def test_changesets_parsed(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Changesets werden korrekt geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                changesets=[
                    {
                        "revision": "abc123",
                        "user": {"id": 1, "name": "Dev"},
                        "comments": "Fix bug #200",
                        "committed_on": "2026-01-18T09:00:00Z",
                    }
                ]
            )
        )

        issue = client.get_issue(200, include=["changesets"])

        assert issue.changesets is not None
        assert len(issue.changesets) == 1
        cs = issue.changesets[0]
        assert cs.revision == "abc123"
        assert cs.user_name == "Dev"
        assert cs.comments == "Fix bug #200"

    def test_allowed_statuses_parsed(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """AllowedStatuses werden korrekt geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                allowed_statuses=[
                    {"id": 1, "name": "New", "is_closed": False},
                    {"id": 5, "name": "Closed", "is_closed": True},
                ]
            )
        )

        issue = client.get_issue(200, include=["allowed_statuses"])

        assert issue.allowed_statuses is not None
        assert len(issue.allowed_statuses) == 2
        assert issue.allowed_statuses[0].name == "New"
        assert issue.allowed_statuses[1].is_closed is True

    def test_children_parsed_recursively(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Children werden rekursiv als RedmineIssue geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                children=[
                    {
                        "id": 201,
                        "subject": "Child Issue",
                        "project": {"id": 1, "name": "P"},
                        "tracker": {"id": 1, "name": "Bug"},
                        "status": {"id": 1, "name": "New"},
                        "priority": {"id": 2, "name": "Normal"},
                        "author": {"id": 1, "name": "User"},
                    }
                ]
            )
        )

        issue = client.get_issue(200, include=["children"])

        assert issue.children is not None
        assert len(issue.children) == 1
        assert issue.children[0].id == 201
        assert issue.children[0].subject == "Child Issue"


class TestWiki:
    """Tests für Wiki-Operationen."""

    def test_get_wiki_pages(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Wiki-Seitenübersicht wird abgerufen."""
        httpx_mock.add_response(
            json={
                "wiki_pages": [
                    {"title": "Start", "version": 3, "created_on": "2026-01-01T10:00:00Z"},
                    {"title": "FAQ", "version": 1, "created_on": "2026-01-05T12:00:00Z"},
                ]
            }
        )

        pages = client.get_wiki_pages("my-project")

        assert len(pages) == 2
        assert pages[0].title == "Start"
        assert pages[1].title == "FAQ"

    def test_get_wiki_page(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Einzelne Wiki-Seite wird abgerufen."""
        httpx_mock.add_response(
            json={
                "wiki_page": {
                    "title": "Start",
                    "text": "h1. Willkommen\n\nInhalt der Startseite.",
                    "version": 5,
                    "author": {"id": 1, "name": "Admin"},
                    "comments": "Aktualisiert",
                    "created_on": "2026-01-01T10:00:00Z",
                    "updated_on": "2026-01-20T14:00:00Z",
                }
            }
        )

        page = client.get_wiki_page("my-project", "Start")

        assert page.title == "Start"
        assert page.text is not None
        assert "Willkommen" in page.text
        assert page.version == 5
        assert page.author_name == "Admin"

    def test_get_wiki_page_with_attachments(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seite mit Attachments wird korrekt geparst."""
        httpx_mock.add_response(
            json={
                "wiki_page": {
                    "title": "Docs",
                    "text": "Dokumentation",
                    "version": 1,
                    "author": {"id": 1, "name": "Admin"},
                    "attachments": [
                        {
                            "id": 50,
                            "filename": "diagram.png",
                            "filesize": 54321,
                            "content_type": "image/png",
                            "author": {"id": 1, "name": "Admin"},
                            "created_on": "2026-01-20T10:00:00Z",
                        }
                    ],
                }
            }
        )

        page = client.get_wiki_page("my-project", "Docs", include_attachments=True)

        assert page.attachments is not None
        assert len(page.attachments) == 1
        assert page.attachments[0].filename == "diagram.png"

        request = httpx_mock.get_request()
        assert "include=attachments" in str(request.url)

    def test_get_wiki_page_with_parent(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seite mit Parent wird korrekt geparst."""
        httpx_mock.add_response(
            json={
                "wiki_page": {
                    "title": "SubPage",
                    "text": "Unterseite",
                    "version": 1,
                    "author": {"id": 1, "name": "Admin"},
                    "parent": {"title": "Start"},
                }
            }
        )

        page = client.get_wiki_page("my-project", "SubPage")

        assert page.parent_title == "Start"

    def test_create_or_update_wiki_page(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seite wird erstellt/aktualisiert."""
        httpx_mock.add_response(status_code=204)

        client.create_or_update_wiki_page(
            "my-project", "NewPage", "Neuer Inhalt", comments="Erstellt"
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert b'"text"' in request.content
        assert b"Neuer Inhalt" in request.content
        assert b'"comments"' in request.content

    def test_delete_wiki_page(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Wiki-Seite wird gelöscht."""
        httpx_mock.add_response(status_code=204)

        client.delete_wiki_page("my-project", "OldPage")

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "DELETE"
        assert "/wiki/OldPage.json" in str(request.url)


class TestAttachments:
    """Tests für Attachment-Operationen."""

    def test_upload_file_bytes(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Datei-Upload mit Bytes gibt Token zurück."""
        httpx_mock.add_response(
            json={"upload": {"token": "abc-123-upload-token"}}
        )

        token = client.upload_file(b"file content here", filename="test.txt")

        assert token == "abc-123-upload-token"
        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["Content-Type"] == "application/octet-stream"
        assert request.content == b"file content here"

    def test_upload_file_from_path(
        self, client: RedmineClient, httpx_mock: HTTPXMock, tmp_path
    ):
        """Datei-Upload von Dateipfad."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"PDF content")

        httpx_mock.add_response(
            json={"upload": {"token": "pdf-upload-token"}}
        )

        token = client.upload_file(test_file)

        assert token == "pdf-upload-token"
        request = httpx_mock.get_request()
        assert request.content == b"PDF content"
        assert "filename=document.pdf" in str(request.url)

    def test_get_attachment(self, client: RedmineClient, httpx_mock: HTTPXMock):
        """Attachment-Metadaten werden abgerufen."""
        httpx_mock.add_response(
            json={
                "attachment": {
                    "id": 42,
                    "filename": "report.pdf",
                    "filesize": 98765,
                    "content_type": "application/pdf",
                    "content_url": "https://redmine.example.com/attachments/download/42/report.pdf",
                    "author": {"id": 1, "name": "Test User"},
                    "created_on": "2026-01-20T10:00:00Z",
                }
            }
        )

        att = client.get_attachment(42)

        assert att.id == 42
        assert att.filename == "report.pdf"
        assert att.filesize == 98765
        assert att.content_url is not None

    def test_download_attachment(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Attachment wird heruntergeladen."""
        # Erste Anfrage: Metadaten
        httpx_mock.add_response(
            json={
                "attachment": {
                    "id": 42,
                    "filename": "report.pdf",
                    "filesize": 11,
                    "content_url": "https://redmine.example.com/attachments/download/42/report.pdf",
                    "author": {"id": 1, "name": "User"},
                }
            }
        )
        # Zweite Anfrage: Download
        httpx_mock.add_response(content=b"PDF binary data")

        data = client.download_attachment(42)

        assert data == b"PDF binary data"

    def test_delete_attachment(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Attachment wird gelöscht."""
        httpx_mock.add_response(status_code=204)

        client.delete_attachment(42)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "DELETE"
        assert "/attachments/42.json" in str(request.url)

    def test_create_issue_with_uploads(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue mit Uploads wird erstellt."""
        httpx_mock.add_response(
            json={
                "issue": {
                    "id": 999,
                    "subject": "Issue mit Anhang",
                    "project": {"id": 1, "name": "P"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "status": {"id": 1, "name": "New"},
                    "priority": {"id": 2, "name": "Normal"},
                    "author": {"id": 1, "name": "User"},
                }
            }
        )

        issue = client.create_issue(
            project_id="my-project",
            subject="Issue mit Anhang",
            uploads=[
                {
                    "token": "abc-123",
                    "filename": "test.txt",
                    "content_type": "text/plain",
                }
            ],
        )

        assert issue.id == 999
        request = httpx_mock.get_request()
        assert b'"uploads"' in request.content
        assert b'"token"' in request.content

    def test_update_issue_with_uploads(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue wird mit Uploads aktualisiert."""
        httpx_mock.add_response(status_code=204)

        client.update_issue(
            issue_id=123,
            uploads=[
                {
                    "token": "def-456",
                    "filename": "attachment.pdf",
                    "content_type": "application/pdf",
                }
            ],
        )

        request = httpx_mock.get_request()
        assert b'"uploads"' in request.content


class TestImpersonate:
    """Tests für User-Impersonation."""

    def test_impersonate_sets_header(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Impersonierter Client sendet X-Redmine-Switch-User Header."""
        httpx_mock.add_response(
            json={"user": {"id": 1, "login": "testuser"}}
        )

        with client.impersonate("john.doe") as user_client:
            user_client.get_current_user()

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["X-Redmine-Switch-User"] == "john.doe"

    def test_impersonate_does_not_affect_original_client(
        self, client: RedmineClient, httpx_mock: HTTPXMock
    ):
        """Original-Client hat keinen X-Redmine-Switch-User Header."""
        httpx_mock.add_response(
            json={"user": {"id": 1, "login": "testuser"}}
        )
        httpx_mock.add_response(
            json={"user": {"id": 2, "login": "john.doe"}}
        )

        with client.impersonate("john.doe") as user_client:
            user_client.get_current_user()

        client.get_current_user()

        requests = httpx_mock.get_requests()
        assert requests[0].headers["X-Redmine-Switch-User"] == "john.doe"
        assert "X-Redmine-Switch-User" not in requests[1].headers
