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

    pass


class RedmineNotFoundError(RedmineError):
    """Ressource nicht gefunden (404)."""

    pass


class RedmineValidationError(RedmineError):
    """Validierungsfehler (422)."""

    pass
