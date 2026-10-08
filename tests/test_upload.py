import geopandas as gpd
from pyproj import Geod
from shapely.geometry import LineString, Polygon

from tests.helpers import (
    LINE_COORDS,
    build_sample_kml,
    build_shapefile_zip,
    post_file,
    sample_polygon,
)

GEOD = Geod(ellps="WGS84")


def _upload_kml(client):
    response = post_file(client, "survey.kml", build_sample_kml())
    assert response.status_code == 201, response.text
    return response.json()


def test_valid_kml_upload(client):
    body = _upload_kml(client)
    assert body["filename"] == "survey.kml"
    assert body["feature_count"] == 3
    assert body["crs"] == "EPSG:4326"
    assert body["status"] == "COMPLETED"


def test_valid_shapefile_zip_upload(client, tmp_path):
    polygons = gpd.GeoDataFrame(
        {"name": ["north", "south"]},
        geometry=[sample_polygon(), Polygon([(75.91, 31.5), (75.911, 31.5), (75.911, 31.501)])],
        crs="EPSG:4326",
    )
    response = post_file(client, "any_name.zip", build_shapefile_zip(tmp_path, polygons))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["feature_count"] == 2
    assert body["crs"] == "EPSG:4326"

    features = client.get(f"/api/files/{body['id']}/measurements/").json()["features"]
    assert [f["properties"]["name"] for f in features] == ["north", "south"]


def test_file_detail_endpoint(client):
    created = _upload_kml(client)
    response = client.get(f"/api/files/{created['id']}/")
    assert response.status_code == 200
    assert response.json() == created


def test_measurements_endpoint_values(client):
    file_id = _upload_kml(client)["id"]
    body = client.get(f"/api/files/{file_id}/measurements/").json()

    assert body["original_crs"] == "EPSG:4326"
    assert body["measurement_crs"] == "EPSG:32643"

    by_type = {f["geometry_type"]: f for f in body["features"]}

    expected_area = abs(GEOD.geometry_area_perimeter(sample_polygon())[0])
    area = by_type["Polygon"]["measurement"]
    assert area["type"] == "area" and area["unit"] == "m\u00b2"
    assert abs(area["value"] - expected_area) / expected_area < 0.005
    assert abs(area["value_km2"] - area["value"] / 1e6) < 1e-6

    expected_length = GEOD.geometry_length(LineString(LINE_COORDS))
    length = by_type["LineString"]["measurement"]
    assert length["type"] == "length" and length["unit"] == "m"
    assert abs(length["value"] - expected_length) / expected_length < 0.005
    assert abs(length["value_km"] - length["value"] / 1000) < 1e-4

    assert by_type["Point"]["measurement"] is None
    assert by_type["Point"]["geometry"]["type"] == "Point"
    assert "Field A" in by_type["Polygon"]["properties"].values()


def test_file_not_found(client):
    for url in ("/api/files/nope/", "/api/files/nope/measurements/"):
        response = client.get(url)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FILE_NOT_FOUND"
