"""Tests für den asynchronen AsyncRedmineClient."""

import warnings

import pytest
from pytest_httpx import HTTPXMock

from redmine_client import (
    AsyncRedmineClient,
    RedmineAuthenticationError,
    RedmineNotFoundError,
)


@pytest.fixture
def async_client():
    """Erstellt einen Test-Client."""
    return AsyncRedmineClient("https://redmine.example.com", "test-api-key")


class TestAsyncRedmineClient:
    """Tests für grundlegende async Client-Funktionalität."""

    def test_client_initialization(self, async_client: AsyncRedmineClient):
        """Client wird korrekt initialisiert."""
        assert async_client.base_url == "https://redmine.example.com"
        assert async_client.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Async Context Manager funktioniert."""
        async with AsyncRedmineClient(
            "https://redmine.example.com", "key"
        ) as client:
            assert client is not None


class TestAsyncAuthentication:
    """Tests für Authentifizierung."""

    @pytest.mark.asyncio
    async def test_auth_error_on_401(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """401 wirft RedmineAuthenticationError."""
        httpx_mock.add_response(status_code=401)

        with pytest.raises(RedmineAuthenticationError):
            await async_client.get_current_user()


class TestAsyncNotFound:
    """Tests für 404-Fehler."""

    @pytest.mark.asyncio
    async def test_not_found_on_404(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """404 wirft RedmineNotFoundError."""
        httpx_mock.add_response(status_code=404)

        with pytest.raises(RedmineNotFoundError):
            await async_client.get_issue(99999)


class TestAsyncUsers:
    """Tests für async User-Operationen."""

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Aktueller User wird abgerufen."""
        httpx_mock.add_response(
            json={
                "user": {
                    "id": 1,
                    "login": "testuser",
                    "firstname": "Test",
                    "lastname": "User",
                }
            }
        )

        user = await async_client.get_current_user()

        assert user["id"] == 1
        assert user["login"] == "testuser"


class TestAsyncIssues:
    """Tests für async Issue-Operationen."""

    @pytest.mark.asyncio
    async def test_get_issues(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
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

        issues = await async_client.get_issues(assigned_to_id="me")

        assert len(issues) == 1
        assert issues[0].id == 123

    @pytest.mark.asyncio
    async def test_get_issue_with_custom_fields(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
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
                    ],
                }
            }
        )

        issue = await async_client.get_issue(456)

        assert issue.get_custom_field("Sprint") == "2026-KW03-KW04"

    @pytest.mark.asyncio
    async def test_update_issue_with_custom_fields(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Issue wird mit Custom Fields aktualisiert."""
        httpx_mock.add_response(status_code=204)

        await async_client.update_issue(
            issue_id=123,
            custom_fields=[{"id": 42, "value": "2026-KW05-KW06"}],
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert b'"custom_fields"' in request.content

    @pytest.mark.asyncio
    async def test_add_issue_note(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Kommentar wird zu Issue hinzugefügt."""
        httpx_mock.add_response(status_code=204)

        await async_client.add_issue_note(123, "Async Kommentar")

        request = httpx_mock.get_request()
        assert b"Async Kommentar" in request.content


class TestAsyncCustomFields:
    """Tests für async Custom Field Operationen."""

    @pytest.mark.asyncio
    async def test_find_custom_field_by_name(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Custom Field wird nach Namen gefunden."""
        httpx_mock.add_response(
            json={
                "custom_fields": [
                    {"id": 42, "name": "Sprint", "customized_type": "issue"},
                ]
            }
        )

        field = await async_client.find_custom_field_by_name("Sprint")

        assert field is not None
        assert field.id == 42


class TestAsyncPagination:
    """Tests für async Paginierung."""

    @pytest.mark.asyncio
    async def test_pagination_multiple_pages(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Mehrere Seiten werden automatisch abgerufen."""
        httpx_mock.add_response(
            json={
                "issues": [{"id": i, "subject": f"Issue {i}"} for i in range(1, 101)],
                "total_count": 150,
            }
        )
        httpx_mock.add_response(
            json={
                "issues": [
                    {"id": i, "subject": f"Issue {i}"} for i in range(101, 151)
                ],
                "total_count": 150,
            }
        )

        issues = await async_client.get_issues()

        assert len(issues) == 150


class TestAsyncIncludeParameters:
    """Tests für erweiterte Include-Parameter (async)."""

    def _issue_response(self, **extra):
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

    @pytest.mark.asyncio
    async def test_include_list_sends_correct_param(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Include-Liste sendet korrekten Query-Parameter."""
        httpx_mock.add_response(json=self._issue_response())

        await async_client.get_issue(200, include=["journals", "attachments"])

        request = httpx_mock.get_request()
        url_str = str(request.url)
        assert "journals" in url_str
        assert "attachments" in url_str

    @pytest.mark.asyncio
    async def test_include_journals_deprecated(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """include_journals erzeugt DeprecationWarning."""
        httpx_mock.add_response(json=self._issue_response(journals=[]))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await async_client.get_issue(200, include_journals=True)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    @pytest.mark.asyncio
    async def test_attachments_parsed(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
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
                        "author": {"id": 1, "name": "Test User"},
                        "created_on": "2026-01-20T10:00:00Z",
                    }
                ]
            )
        )

        issue = await async_client.get_issue(200, include=["attachments"])

        assert issue.attachments is not None
        assert len(issue.attachments) == 1
        assert issue.attachments[0].filename == "doc.pdf"

    @pytest.mark.asyncio
    async def test_children_parsed(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Children werden rekursiv geparst."""
        httpx_mock.add_response(
            json=self._issue_response(
                children=[
                    {
                        "id": 201,
                        "subject": "Child",
                        "project": {"id": 1, "name": "P"},
                        "tracker": {"id": 1, "name": "Bug"},
                        "status": {"id": 1, "name": "New"},
                        "priority": {"id": 2, "name": "Normal"},
                        "author": {"id": 1, "name": "User"},
                    }
                ]
            )
        )

        issue = await async_client.get_issue(200, include=["children"])

        assert issue.children is not None
        assert issue.children[0].id == 201


class TestAsyncWiki:
    """Tests für async Wiki-Operationen."""

    @pytest.mark.asyncio
    async def test_get_wiki_pages(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seitenübersicht wird abgerufen."""
        httpx_mock.add_response(
            json={
                "wiki_pages": [
                    {"title": "Start", "version": 3},
                    {"title": "FAQ", "version": 1},
                ]
            }
        )

        pages = await async_client.get_wiki_pages("my-project")

        assert len(pages) == 2
        assert pages[0].title == "Start"

    @pytest.mark.asyncio
    async def test_get_wiki_page(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Einzelne Wiki-Seite wird abgerufen."""
        httpx_mock.add_response(
            json={
                "wiki_page": {
                    "title": "Start",
                    "text": "Inhalt",
                    "version": 5,
                    "author": {"id": 1, "name": "Admin"},
                }
            }
        )

        page = await async_client.get_wiki_page("my-project", "Start")

        assert page.title == "Start"
        assert page.text == "Inhalt"
        assert page.author_name == "Admin"

    @pytest.mark.asyncio
    async def test_create_or_update_wiki_page(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seite wird erstellt/aktualisiert."""
        httpx_mock.add_response(status_code=204)

        await async_client.create_or_update_wiki_page(
            "my-project", "NewPage", "Inhalt", comments="Erstellt"
        )

        request = httpx_mock.get_request()
        assert b'"text"' in request.content

    @pytest.mark.asyncio
    async def test_delete_wiki_page(
        self, async_client: AsyncRedmineClient, httpx_mock: HTTPXMock
    ):
        """Wiki-Seite wird gelöscht."""
        httpx_mock.add_response(status_code=204)

        await async_client.delete_wiki_page("my-project", "OldPage")

        request = httpx_mock.get_request()
        assert request.method == "DELETE"
