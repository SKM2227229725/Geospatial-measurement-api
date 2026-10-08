import json
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from app.core.config import Settings
from app.core.exceptions import ProcessingFailedError
from app.services.crs_service import crs_label, select_measurement_crs
from app.services.measurement_service import measure_geometry
from app.utils.zip_security import extract_zip_safely

logger = logging.getLogger(__name__)

KML_DEFAULT_CRS = "EPSG:4326"
REQUIRED_SIDECARS = (".shx", ".dbf")


@dataclass
class ProcessedDataset:
    crs: str
    measurement_crs: str
    features: list[dict[str, Any]]


def _read_all_layers(path: Path) -> gpd.GeoDataFrame:
    """KML folders become separate layers, so read them all."""
    try:
        layer_names = [row[0] for row in pyogrio.list_layers(path)]
        frames = [pyogrio.read_dataframe(path, layer=name) for name in layer_names]
        frames = [f for f in frames if not f.empty]
    except Exception as exc:
        logger.exception("Failed to read geospatial file")
        raise ProcessingFailedError(
            "UNREADABLE_FILE", "The file could not be read as geospatial data."
        ) from exc

    if not frames:
        raise ProcessingFailedError("EMPTY_DATASET", "The file contains no features.")

    combined = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=frames[0].crs)


def load_kml(path: Path) -> gpd.GeoDataFrame:
    gdf = _read_all_layers(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(KML_DEFAULT_CRS)
    return gdf


def _find_shapefile(folder: Path) -> Path:
    candidates = [
        p for p in folder.rglob("*")
        if p.suffix.lower() == ".shp" and "__MACOSX" not in p.parts
    ]
    if not candidates:
        raise ProcessingFailedError("NO_SHAPEFILE", "The ZIP does not contain a .shp file.")
    if len(candidates) > 1:
        raise ProcessingFailedError(
            "MULTIPLE_SHAPEFILES", "The ZIP contains more than one Shapefile."
        )
    return candidates[0]


def _check_sidecars(shp_path: Path) -> None:
    present = {p.suffix.lower() for p in shp_path.parent.iterdir() if p.stem == shp_path.stem}
    missing = [ext for ext in REQUIRED_SIDECARS if ext not in present]
    if missing:
        raise ProcessingFailedError(
            "INCOMPLETE_SHAPEFILE",
            f"Shapefile is missing required files: {', '.join(missing)}.",
        )


def load_shapefile_zip(zip_path: Path, work_dir: Path, settings: Settings) -> gpd.GeoDataFrame:
    extract_zip_safely(
        zip_path,
        work_dir,
        max_files=settings.max_zip_files,
        max_uncompressed_bytes=settings.max_uncompressed_bytes,
        max_ratio=settings.max_compression_ratio,
    )
    shp_path = _find_shapefile(work_dir)
    _check_sidecars(shp_path)
    return _read_all_layers(shp_path)


def _json_safe(value: Any) -> Any:
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def process_dataset(gdf: gpd.GeoDataFrame) -> ProcessedDataset:
    if gdf.geometry.isna().all() or gdf.geometry.is_empty.all():
        raise ProcessingFailedError("EMPTY_DATASET", "The file has no usable geometries.")

    measurement_crs = select_measurement_crs(gdf)
    projected = gdf.to_crs(measurement_crs)
    if not np.isfinite(projected.total_bounds).all():
        raise ProcessingFailedError(
            "INVALID_COORDINATES",
            "Coordinates fall outside the valid range of the file's CRS.",
        )

    original_crs = crs_label(gdf.crs)
    attributes = gdf.drop(columns=gdf.geometry.name).to_dict("records")

    features: list[dict[str, Any]] = []
    for index, (orig_geom, proj_geom) in enumerate(zip(gdf.geometry, projected.geometry)):
        result = measure_geometry(proj_geom)
        features.append(
            {
                "feature_id": index,
                "geometry_type": orig_geom.geom_type if orig_geom is not None else None,
                "geometry": (
                    json.loads(shapely.to_geojson(orig_geom))
                    if orig_geom is not None
                    else None
                ),
                "crs": original_crs,
                "properties": {k: _json_safe(v) for k, v in attributes[index].items()},
                "measurement": result.measurement,
                "status": result.status,
                "message": result.message,
            }
        )

    return ProcessedDataset(
        crs=original_crs,
        measurement_crs=crs_label(measurement_crs),
        features=features,
    )
