from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class AreaMeasurement(BaseModel):
    type: Literal["area"] = "area"
    value: float
    unit: Literal["m²"] = "m²"
    value_km2: float


class LengthMeasurement(BaseModel):
    type: Literal["length"] = "length"
    value: float
    unit: Literal["m"] = "m"
    value_km: float


class FeatureOut(BaseModel):
    feature_id: int
    geometry_type: str | None
    geometry: dict[str, Any] | None
    crs: str
    properties: dict[str, Any]
    measurement: AreaMeasurement | LengthMeasurement | None
    status: str
    message: str | None = None


class FileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    feature_count: int
    crs: str | None
    status: Literal["PROCESSING", "COMPLETED", "FAILED"]
    error_code: str | None = None
    error_message: str | None = None


class FileMeasurements(BaseModel):
    file_id: str
    filename: str
    original_crs: str | None
    measurement_crs: str | None
    features: list[FeatureOut]
