"""
Redmine API Exceptions.
"""


class RedmineError(Exception):
    """Basis-Exception für Redmine-Fehler."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RedmineAuthenticationError(RedmineError):
    """Authentifizierungsfehler (401)."""
    def __init__(
        self,
        message: str,
        response: dict | None = None,
    ):
        super().__init__(message, 401, response)


class RedmineNotFoundError(RedmineError):
    """Ressource nicht gefunden (404)."""
    def __init__(
        self,
        message: str,
        response: dict | None = None,
    ):
        super().__init__(message, 404, response)


class RedmineValidationError(RedmineError):
    """Validierungsfehler (422)."""
    def __init__(
        self,
        message: str,
        response: dict | None = None,
    ):
        super().__init__(message, 422, response)
