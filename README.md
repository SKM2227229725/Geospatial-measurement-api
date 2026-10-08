# Geospatial Measurement API

A small backend service that accepts a geospatial file (KML or a zipped
Shapefile), reads its features, and returns area / length measurements.

Built with FastAPI, GeoPandas, Shapely and PyProj.

---

## Features

- Upload .kml or .zip (Shapefile) via POST /api/files/
- Per-feature output: ID, geometry type, GeoJSON geometry, CRS, properties
- Measurements
  - Polygon / MultiPolygon: area (m2 and km2)
  - LineString / MultiLineString: length (m and km)
  - Point / MultiPoint: no measurement (null)
  - GeometryCollection and unknown types: handled gracefully, never crashes
- CRS handling
  - Geographic CRS (e.g. EPSG:4326) is auto-projected to the best-fit UTM zone
  - Metre-based projected CRS is used as-is (Web Mercator is deliberately replaced)
  - Missing CRS is rejected with a clear 422 error
- Security
  - Extension + magic-byte validation
  - Size limits on upload and on ZIP expansion
  - ZIP-bomb and path-traversal protection
  - XML entity blocking for KML
- Consistent error envelope on every failure path

---

## Tech Stack

- FastAPI + Uvicorn
- Pydantic v2 for validation, pydantic-settings for config
- SQLAlchemy 2.x with SQLite (local) or PostgreSQL (Docker)
- GeoPandas, Shapely, PyProj, pyogrio, Fiona for geospatial work
- Pytest + FastAPI TestClient for tests

---

## Architecture

    Client
      |
      v
    FastAPI router       (app/api/routes/files.py)
      |
      v
    File service         (app/services/file_service.py)
      |
      +-- validation     (app/utils/file_validation.py)
      +-- ZIP safety     (app/utils/zip_security.py)
      |
      v
    Geospatial service   (app/services/geospatial_service.py)
      |
      +-- CRS selection  (app/services/crs_service.py)
      +-- measurement    (app/services/measurement_service.py)
      |
      v
    Repository           (app/repositories/file_repository.py)
      |
      v
    SQLAlchemy / DB
      |
      v
    JSON response

---

## Setup (Windows, Python 3.11)

    py -3.11 -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements-dev.txt
    Copy-Item .env.example .env
    pytest
    uvicorn app.main:app --reload

Swagger UI: http://127.0.0.1:8000/docs

### Docker

    docker compose up --build

API on http://localhost:8000.

---

## API

### 1. Upload a file

    curl -X POST http://127.0.0.1:8000/api/files/ -F "file=@survey.kml"

Response (201):

    {
      "id": "b0a1c4d7-7f9b-4c4a-a2b0-8a0f8f1d4c8a",
      "filename": "survey.kml",
      "feature_count": 3,
      "crs": "EPSG:4326",
      "status": "COMPLETED",
      "error_code": null,
      "error_message": null
    }

### 2. Get file status

    curl http://127.0.0.1:8000/api/files/<id>/

### 3. Get measurements

    curl http://127.0.0.1:8000/api/files/<id>/measurements/

Response:

    {
      "file_id": "b0a1c4d7-7f9b-4c4a-a2b0-8a0f8f1d4c8a",
      "filename": "survey.kml",
      "original_crs": "EPSG:4326",
      "measurement_crs": "EPSG:32643",
      "features": [
        {
          "feature_id": 0,
          "geometry_type": "Polygon",
          "geometry": { "type": "Polygon", "coordinates": [] },
          "crs": "EPSG:4326",
          "properties": { "name": "Field A" },
          "measurement": {
            "type": "area",
            "value": 10234.55,
            "unit": "m2",
            "value_km2": 0.01023455
          },
          "status": "OK",
          "message": null
        }
      ]
    }

### Error format (all failures)

    {
      "error": {
        "code": "INVALID_FILE_TYPE",
        "message": "Unsupported file type.",
        "details": {}
      }
    }

HTTP status codes:

    400  Invalid upload (extension, magic bytes, unsafe ZIP)
    404  File not found
    409  Measurements for a file that is not COMPLETED
    413  File exceeds the size limit
    422  File accepted but cannot be processed (e.g. missing CRS)
    500  Unexpected server error

---

## CRS strategy

Area and length cannot be computed directly on latitude / longitude degrees.
The service therefore:

1. Reads the CRS from the file (.prj for Shapefiles; KML is always EPSG:4326).
2. If the CRS is missing, the upload is rejected with MISSING_CRS.
3. If the CRS is already projected in metres (and not Web Mercator), it is used directly.
4. Otherwise, the best-fit UTM zone for the dataset centroid is chosen via
   gdf.estimate_utm_crs().

Web Mercator (EPSG:3857) is explicitly not used for area because it
distorts area away from the equator.

---

## Security

- Only .kml and .zip are accepted (extension + magic bytes).
- Uploads are streamed to disk and rejected the moment they exceed the limit.
- ZIP extraction enforces:
  - maximum number of entries
  - maximum total uncompressed size
  - maximum compression ratio (ZIP bomb guard)
  - no absolute paths, no .. traversal, no symlinks
- KML files with XML entity declarations are rejected (XML entity attack guard).
- Error responses never leak stack traces or filesystem paths.

---

## Testing

    pytest
    pytest -v
    pytest tests/test_crs.py

Coverage includes happy-path KML and Shapefile uploads, measurement
correctness against a pyproj geodesic calculation, invalid uploads,
ZIP attacks, CRS selection, and missing-CRS handling.

---

## Trade-offs and limitations

- Features are stored as JSON in a single DB column (simple; not queryable).
  PostGIS with a proper geometry column would be the production choice.
- KML files with very large extents are measured with a single UTM zone,
  which is only accurate for regional-scale data.
- Routes are synchronous (def), so FastAPI runs them in a threadpool.
  For very large files a background worker (Celery / RQ) would be the next step.
- The SQLite database is created on startup via create_all; production
  deployments should use Alembic migrations.

---

## Future improvements

- Background processing queue for large uploads
- PostGIS + Alembic
- S3-style object storage for uploaded files
- Authentication + rate limiting
- Geodesic measurement fallback for datasets spanning more than one UTM zone

<!-- commit: update author link -->
