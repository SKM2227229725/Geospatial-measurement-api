import geopandas as gpd
from pyproj import CRS

from app.core.exceptions import ProcessingFailedError

WEB_MERCATOR = 3857
METRE_UNITS = {"metre", "meter"}


def crs_label(crs: CRS) -> str:
    epsg = crs.to_epsg()
    return f"EPSG:{epsg}" if epsg else crs.name


def _metre_based(crs: CRS) -> bool:
    return all(axis.unit_name in METRE_UNITS for axis in crs.axis_info)


def select_measurement_crs(gdf: gpd.GeoDataFrame) -> CRS:
    """Pick a CRS where area / length are meaningful, in metres."""
    crs = gdf.crs
    if crs is None:
        raise ProcessingFailedError(
            "MISSING_CRS",
            "File has no CRS (.prj missing or empty). A CRS is required for reliable measurements.",
        )

    if crs.is_projected and _metre_based(crs) and crs.to_epsg() != WEB_MERCATOR:
        return crs

    if crs.is_geographic or crs.is_projected:
        return gdf.estimate_utm_crs()

    raise ProcessingFailedError("UNSUPPORTED_CRS", "This CRS is not supported.")
