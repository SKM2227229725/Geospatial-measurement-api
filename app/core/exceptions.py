from typing import Any


class AppError(Exception):
    """Base for errors we deliberately surface to the client."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class InvalidFileError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(code, message, 400, details)


class FileTooLargeError(AppError):
    def __init__(self, max_mb: int):
        super().__init__("FILE_TOO_LARGE", f"File exceeds the {max_mb} MB limit.", 413)


class ProcessingFailedError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(code, message, 422, details)


class NotFoundError(AppError):
    def __init__(self, file_id: str):
        super().__init__("FILE_NOT_FOUND", "File not found.", 404, {"file_id": file_id})
