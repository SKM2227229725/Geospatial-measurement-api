import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import files
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.models import file as _file_models  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(get_settings().debug)
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Geospatial Measurement API",
    description="Upload a KML or zipped Shapefile and get area / length measurements.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(files.router)


def _error_response(status_code: int, code: str, message: str, details: dict | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError):
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return _error_response(422, "VALIDATION_ERROR", "Request validation failed.", {"errors": errors})


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return _error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception):
    logger.error("Unhandled error", exc_info=exc)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")
