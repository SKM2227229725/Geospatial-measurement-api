from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon

from app.services.measurement_service import measure_geometry


def test_polygon_area():
    result = measure_geometry(Polygon([(0, 0), (100, 0), (100, 50), (0, 50)]))
    assert result.status == "OK"
    assert result.measurement == {
        "type": "area", "value": 5000.0, "unit": "m\u00b2", "value_km2": 0.005,
    }


def test_linestring_length():
    result = measure_geometry(LineString([(0, 0), (300, 400)]))
    assert result.measurement == {
        "type": "length", "value": 500.0, "unit": "m", "value_km": 0.5,
    }


def test_point_has_no_measurement():
    result = measure_geometry(Point(1, 1))
    assert result.measurement is None
    assert result.status == "OK"


def test_multipolygon_area_is_summed():
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    far_square = Polygon([(100, 100), (110, 100), (110, 110), (100, 110)])
    result = measure_geometry(MultiPolygon([square, far_square]))
    assert result.measurement["value"] == 200.0


def test_unsupported_geometry_does_not_crash():
    collection = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    result = measure_geometry(collection)
    assert result.measurement is None
    assert result.status == "UNSUPPORTED_GEOMETRY"


def test_empty_geometry():
    result = measure_geometry(Polygon())
    assert result.measurement is None
    assert result.status == "EMPTY_GEOMETRY"


def test_invalid_bowtie_polygon_is_repaired():
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    assert not bowtie.is_valid
    result = measure_geometry(bowtie)
    assert result.status == "REPAIRED"
    assert result.measurement["value"] == 50.0
