from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.repositories.file_repository import FileRepository
from app.schemas.error import ErrorResponse
from app.schemas.file import FileMeasurements, FileSummary
from app.services import file_service

router = APIRouter(prefix="/api/files", tags=["files"])


def get_repository(db: Session = Depends(get_db)) -> FileRepository:
    return FileRepository(db)


@router.post(
    "/",
    response_model=FileSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a KML or zipped Shapefile",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid upload"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "File cannot be processed"},
    },
)
def upload_file(
    file: UploadFile = File(...),
    repo: FileRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    return file_service.process_upload(file, repo, settings)


@router.get(
    "/{file_id}/",
    response_model=FileSummary,
    summary="Get processing status of a file",
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_file(file_id: str, repo: FileRepository = Depends(get_repository)):
    return file_service.get_file_or_404(repo, file_id)


@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurements,
    summary="Get features with area/length measurements",
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
        409: {"model": ErrorResponse, "description": "File is not COMPLETED yet"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_measurements(file_id: str, repo: FileRepository = Depends(get_repository)):
    record = file_service.get_completed_file(repo, file_id)
    return FileMeasurements(
        file_id=record.id,
        filename=record.filename,
        original_crs=record.crs,
        measurement_crs=record.measurement_crs,
        features=record.features,
    )