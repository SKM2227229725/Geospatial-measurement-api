import zipfile
from pathlib import Path
from typing import BinaryIO

from app.core.config import MB
from app.core.exceptions import FileTooLargeError, InvalidFileError

ALLOWED_EXTENSIONS = {".kml", ".zip"}
ZIP_MAGIC = b"PK\x03\x04"
CHUNK = 1024 * 1024
SNIFF_BYTES = 4096


def validate_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileError(
            "INVALID_FILE_TYPE",
            "Unsupported file type. Upload a .kml or a .zip containing a Shapefile.",
        )
    return ext


def save_upload_with_limit(stream: BinaryIO, destination: Path, max_mb: int) -> None:
    """Stream to disk and abort the moment we cross the limit."""
    limit = max_mb * MB
    written = 0

    with destination.open("wb") as out:
        while chunk := stream.read(CHUNK):
            written += len(chunk)
            if written > limit:
                raise FileTooLargeError(max_mb)
            out.write(chunk)

    if written == 0:
        raise InvalidFileError("EMPTY_FILE", "The uploaded file is empty.")


def validate_content(path: Path, ext: str) -> None:
    """Trust bytes, not the filename."""
    with path.open("rb") as f:
        head = f.read(SNIFF_BYTES)

    if ext == ".zip":
        if not head.startswith(ZIP_MAGIC) or not zipfile.is_zipfile(path):
            raise InvalidFileError("INVALID_FILE_CONTENT", "Not a valid ZIP archive.")
        return

    text = head.decode("utf-8", errors="ignore").lower()
    if "<kml" not in text:
        raise InvalidFileError("INVALID_FILE_CONTENT", "File does not look like KML.")
    if "<!entity" in text:
        raise InvalidFileError("INVALID_FILE_CONTENT", "KML with XML entities is not allowed.")
