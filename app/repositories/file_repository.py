import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.file import FileStatus, UploadedFile


class FileRepository:
    """Thin wrapper so services never touch SQLAlchemy directly."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, filename: str) -> UploadedFile:
        record = UploadedFile(
            id=str(uuid.uuid4()),
            filename=filename,
            status=FileStatus.PROCESSING.value,
            features=[],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, file_id: str) -> UploadedFile | None:
        return self.db.get(UploadedFile, file_id)

    def mark_completed(
        self,
        record: UploadedFile,
        *,
        crs: str,
        measurement_crs: str,
        features: list[dict[str, Any]],
    ) -> UploadedFile:
        record.status = FileStatus.COMPLETED.value
        record.crs = crs
        record.measurement_crs = measurement_crs
        record.features = features
        record.feature_count = len(features)
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_failed(self, record: UploadedFile, code: str, message: str) -> UploadedFile:
        record.status = FileStatus.FAILED.value
        record.error_code = code
        record.error_message = message[:500]
        self.db.commit()
        self.db.refresh(record)
        return record
