import logging
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError, ProcessingFailedError
from app.models.file import FileStatus, UploadedFile
from app.repositories.file_repository import FileRepository
from app.services.geospatial_service import load_kml, load_shapefile_zip, process_dataset
from app.utils.file_validation import save_upload_with_limit, validate_content, validate_extension

logger = logging.getLogger(__name__)


def _safe_filename(raw: str | None) -> str:
    return Path((raw or "").replace("\\", "/")).name[:255]


def process_upload(upload: UploadFile, repo: FileRepository, settings: Settings) -> UploadedFile:
    ext = validate_extension(upload.filename)
    filename = _safe_filename(upload.filename)

    with tempfile.TemporaryDirectory(prefix="geo_upload_") as tmp:
        work_dir = Path(tmp)
        saved = work_dir / f"upload{ext}"

        save_upload_with_limit(upload.file, saved, settings.max_upload_size_mb)
        validate_content(saved, ext)

        record = repo.create(filename)
        try:
            if ext == ".kml":
                gdf = load_kml(saved)
            else:
                gdf = load_shapefile_zip(saved, work_dir / "shapefile", settings)

            result = process_dataset(gdf)

        except AppError as exc:
            repo.mark_failed(record, exc.code, exc.message)
            exc.details["file_id"] = record.id
            logger.warning("upload_failed id=%s name=%r code=%s", record.id, filename, exc.code)
            raise

        except Exception as exc:
            logger.exception("Unexpected error while processing id=%s", record.id)
            repo.mark_failed(record, "PROCESSING_ERROR", "Unexpected error while processing the file.")
            raise ProcessingFailedError(
                "PROCESSING_ERROR",
                "Unexpected error while processing the file.",
                {"file_id": record.id},
            ) from exc

        repo.mark_completed(
            record,
            crs=result.crs,
            measurement_crs=result.measurement_crs,
            features=result.features,
        )
        logger.info(
            "upload_completed id=%s name=%r features=%d measurement_crs=%s",
            record.id, filename, record.feature_count, result.measurement_crs,
        )
        return record


def get_file_or_404(repo: FileRepository, file_id: str) -> UploadedFile:
    record = repo.get(file_id)
    if record is None:
        raise NotFoundError(file_id)
    return record


def get_completed_file(repo: FileRepository, file_id: str) -> UploadedFile:
    record = get_file_or_404(repo, file_id)
    if record.status != FileStatus.COMPLETED.value:
        raise AppError(
            "FILE_NOT_READY",
            "Measurements are only available for files with status COMPLETED.",
            409,
            {"file_id": file_id, "status": record.status},
        )
    return record
