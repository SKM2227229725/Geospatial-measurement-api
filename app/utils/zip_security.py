import zipfile
from pathlib import Path

from app.core.exceptions import InvalidFileError

CHUNK = 1024 * 1024
SYMLINK_MASK = 0o170000
SYMLINK_TYPE = 0o120000


def _unsafe(message: str) -> InvalidFileError:
    return InvalidFileError("UNSAFE_ZIP", message)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return (info.external_attr >> 16) & SYMLINK_MASK == SYMLINK_TYPE


def extract_zip_safely(
    zip_path: Path,
    destination: Path,
    *,
    max_files: int,
    max_uncompressed_bytes: int,
    max_ratio: int,
) -> None:
    """Extract a ZIP but refuse anything that looks hostile."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    try:
        with zipfile.ZipFile(zip_path) as zf:
            entries = [i for i in zf.infolist() if not i.is_dir()]

            if len(entries) > max_files:
                raise _unsafe(f"ZIP contains more than {max_files} entries.")

            declared = sum(i.file_size for i in entries)
            if declared > max_uncompressed_bytes:
                raise _unsafe("ZIP is too large when uncompressed.")

            ratio = declared / max(zip_path.stat().st_size, 1)
            if ratio > max_ratio:
                raise _unsafe("ZIP compression ratio is suspiciously high.")

            extracted = 0
            for info in entries:
                if _is_symlink(info):
                    raise _unsafe("ZIP contains symlinks.")

                target = (root / info.filename).resolve()
                if not target.is_relative_to(root):
                    raise _unsafe("ZIP contains paths outside the extraction folder.")

                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as out:
                    while chunk := src.read(CHUNK):
                        extracted += len(chunk)
                        if extracted > max_uncompressed_bytes:
                            raise _unsafe("ZIP is too large when uncompressed.")
                        out.write(chunk)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise InvalidFileError("INVALID_ZIP", "ZIP archive is corrupt or encrypted.") from exc
