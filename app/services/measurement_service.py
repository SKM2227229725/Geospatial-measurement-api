"""Area / length of a single geometry. Input MUST already be in a metre CRS."""
from dataclasses import dataclass

import shapely
from shapely.geometry.base import BaseGeometry

AREA_TYPES = {"Polygon", "MultiPolygon"}
LENGTH_TYPES = {"LineString", "MultiLineString"}
POINT_TYPES = {"Point", "MultiPoint"}


@dataclass
class MeasurementResult:
    measurement: dict | None
    status: str
    message: str | None = None


def measure_geometry(geometry: BaseGeometry | None) -> MeasurementResult:
    if geometry is None or geometry.is_empty:
        return MeasurementResult(None, "EMPTY_GEOMETRY", "Feature has no geometry.")

    geom_type = geometry.geom_type

    if geom_type in POINT_TYPES:
        return MeasurementResult(None, "OK", "Points have no area or length.")

    if geom_type not in AREA_TYPES | LENGTH_TYPES:
        return MeasurementResult(
            None, "UNSUPPORTED_GEOMETRY", f"Measuring {geom_type} is not supported."
        )

    status, message = "OK", None
    if not geometry.is_valid:
        repaired = _try_repair(geometry)
        if repaired is None:
            return MeasurementResult(
                None, "INVALID_GEOMETRY", "Geometry is invalid and could not be repaired."
            )
        geometry = repaired
        status, message = "REPAIRED", "Invalid geometry was repaired before measuring."

    if geom_type in AREA_TYPES:
        area = geometry.area
        measurement = {
            "type": "area",
            "value": round(area, 2),
            "unit": "m\u00b2",
            "value_km2": round(area / 1_000_000, 8),
        }
    else:
        length = geometry.length
        measurement = {
            "type": "length",
            "value": round(length, 2),
            "unit": "m",
            "value_km": round(length / 1000, 5),
        }

    return MeasurementResult(measurement, status, message)


def _try_repair(geometry: BaseGeometry) -> BaseGeometry | None:
    wanted = "Polygon" if geometry.geom_type in AREA_TYPES else "LineString"
    fixed = shapely.make_valid(geometry)
    parts = shapely.get_parts(shapely.get_parts(fixed))
    kept = [p for p in parts if p.geom_type == wanted and not p.is_empty]
    if not kept:
        return None
    return shapely.union_all(kept)
