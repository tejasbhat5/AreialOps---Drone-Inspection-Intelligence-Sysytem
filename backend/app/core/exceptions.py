from typing import Any


class ApplicationError(Exception):
    """Expected use-case failure that can be shown safely to an API client."""

    status_code = 400
    code = "application_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = details


class NotFoundError(ApplicationError):
    status_code = 404
    code = "resource_not_found"


class ConflictError(ApplicationError):
    status_code = 409
    code = "resource_conflict"


class InvalidStateError(ApplicationError):
    status_code = 409
    code = "invalid_state_transition"


class PayloadTooLargeError(ApplicationError):
    status_code = 413
    code = "payload_too_large"
