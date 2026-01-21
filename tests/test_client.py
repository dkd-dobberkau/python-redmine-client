"""Tests für den synchronen RedmineClient."""

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
