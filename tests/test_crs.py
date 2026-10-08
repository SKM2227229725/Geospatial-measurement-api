import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from app.core.exceptions import ProcessingFailedError
from app.services.crs_service import select_measurement_crs
from tests.helpers import build_shapefile_zip, post_file, sample_polygon


def _gdf(crs, geometry=None):
    return gpd.GeoDataFrame(geometry=[geometry or Point(75.9, 31.5)], crs=crs)


def test_geographic_crs_gets_utm_zone():
    assert select_measurement_crs(_gdf("EPSG:4326")).to_epsg() == 32643


def test_southern_hemisphere_gets_south_utm_zone():
    assert select_measurement_crs(_gdf("EPSG:4326", Point(151.2, -33.9))).to_epsg() == 32756


def test_metre_based_projected_crs_is_kept():
    assert select_measurement_crs(_gdf("EPSG:32643")).to_epsg() == 32643


def test_web_mercator_is_replaced_by_utm():
    gdf = _gdf("EPSG:4326").to_crs("EPSG:3857")
    assert select_measurement_crs(gdf).to_epsg() == 32643


def test_missing_crs_raises():
    gdf = gpd.GeoDataFrame(geometry=[Point(1, 1)])
    with pytest.raises(ProcessingFailedError) as error:
        select_measurement_crs(gdf)
    assert error.value.code == "MISSING_CRS"


def test_shapefile_without_prj_is_rejected_and_marked_failed(client, tmp_path):
    gdf = gpd.GeoDataFrame({"name": ["a"]}, geometry=[sample_polygon()], crs="EPSG:4326")
    response = post_file(client, "no_prj.zip", build_shapefile_zip(tmp_path, gdf, include_prj=False))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "MISSING_CRS"

    file_id = error["details"]["file_id"]
    detail = client.get(f"/api/files/{file_id}/").json()
    assert detail["status"] == "FAILED"
    assert detail["error_code"] == "MISSING_CRS"
    assert client.get(f"/api/files/{file_id}/measurements/").status_code == 409


def test_already_projected_shapefile_is_measured_directly(client, tmp_path):
    square = Polygon([
        (500000, 3500000), (500100, 3500000), (500100, 3500100), (500000, 3500100),
    ])
    gdf = gpd.GeoDataFrame({"name": ["plot"]}, geometry=[square], crs="EPSG:32643")
    response = post_file(client, "projected.zip", build_shapefile_zip(tmp_path, gdf))
    assert response.status_code == 201, response.text
    file_id = response.json()["id"]

    body = client.get(f"/api/files/{file_id}/measurements/").json()
    assert body["measurement_crs"] == body["original_crs"]
    assert body["features"][0]["measurement"]["value"] == 10000.0
