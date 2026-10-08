import io
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

# ~95 m x 111 m square near 75.9E, 31.5N  ->  UTM zone 43N (EPSG:32643)
POLYGON_COORDS = [
    (75.900, 31.500),
    (75.901, 31.500),
    (75.901, 31.501),
    (75.900, 31.501),
    (75.900, 31.500),
]
LINE_COORDS = [(75.900, 31.500), (75.902, 31.502)]
POINT_COORD = (75.9005, 31.5005)

KML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark><name>Field A</name>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{polygon}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
    <Placemark><name>Road B</name>
      <LineString><coordinates>{line}</coordinates></LineString>
    </Placemark>
    <Placemark><name>Well C</name>
      <Point><coordinates>{point}</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""


def _coords(points) -> str:
    return " ".join(f"{x},{y},0" for x, y in points)


def build_sample_kml() -> bytes:
    return KML_TEMPLATE.format(
        polygon=_coords(POLYGON_COORDS),
        line=_coords(LINE_COORDS),
        point=_coords([POINT_COORD]),
    ).encode()


def sample_polygon() -> Polygon:
    return Polygon(POLYGON_COORDS)


def build_shapefile_zip(workdir: Path, gdf: gpd.GeoDataFrame, include_prj: bool = True) -> bytes:
    folder = workdir / "shp_source"
    folder.mkdir()
    gdf.to_file(folder / "parcels.shp")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in folder.iterdir():
            if path.suffix == ".prj" and not include_prj:
                continue
            archive.write(path, arcname=path.name)
    return buffer.getvalue()


def build_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def post_file(client, filename: str, content: bytes):
    return client.post(
        "/api/files/",
        files={"file": (filename, content, "application/octet-stream")},
    )
