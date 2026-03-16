from typing import Any

class ReinsightError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details


class AuthError(ReinsightError):
    pass


class ValidationError(ReinsightError):
    pass


class RateLimitError(ReinsightError):
    pass


class ServerError(ReinsightError):
    pass


class NetworkError(ReinsightError):
    pass