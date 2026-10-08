\# Design Decisions



Short, honest notes on why the code is the way it is.



\## Why FastAPI (not Django + DRF)



This is a focused file-processing API: three endpoints, one domain,

no admin panel, no auth, no template rendering. FastAPI gives me

Pydantic v2 validation, automatic OpenAPI docs, and a much smaller

surface area. Django would add ORM + migrations + admin machinery

that this assignment does not need.



\## Why GeoPandas / Shapely / PyProj



\- \*\*GeoPandas\*\* is the pragmatic way to read mixed geospatial formats

&#x20; and keeps the CRS attached to the geometry.

\- \*\*Shapely\*\* handles geometry math (area, length, `make\_valid`).

\- \*\*PyProj\*\* is the industry-standard CRS library and underlies

&#x20; GeoPandas' `to\_crs()` and `estimate\_utm\_crs()`.



\## Why UTM auto-selection (and not Web Mercator)



Latitude / longitude degrees are not metres. Area and length must be

computed in a projected CRS with metre units.



\- \*\*UTM\*\* is conformal, has low distortion within a zone, and gives

&#x20; metres directly. `gdf.estimate\_utm\_crs()` picks the zone from the

&#x20; centroid of the data automatically.

\- \*\*EPSG:3857 (Web Mercator)\*\* is meant for tiled web maps. It

&#x20; massively distorts area away from the equator. I explicitly exclude

&#x20; it from the "use as-is" path even if a file arrives in it.



For datasets spanning more than one UTM zone (very large countries)

a geodesic calculation or a global equal-area projection would be

more correct. That is out of scope here and noted in the README.



\## Why synchronous route handlers (`def`, not `async def`)



GeoPandas / Shapely / PyProj are CPU-bound. `async def` would block the

event loop during processing. Plain `def` tells FastAPI to run the

handler in its threadpool, which is the right tool for CPU work.



\## Why a repository layer



`FileRepository` is a thin wrapper over SQLAlchemy. It keeps the

service layer free of session / query details and makes the storage

easy to swap. It is deliberately small — no abstract interfaces, no

generic base classes.



\## Why JSON columns for features



Features (geometry + properties + measurement) are written once and

read as a whole. Storing them as JSON keeps the schema simple. The

trade-off is that individual features cannot be queried efficiently;

PostGIS with a geometry column would be the production path.



\## Why SQLite locally, PostgreSQL in Docker



SQLite keeps local dev zero-setup. `docker-compose.yml` uses

PostgreSQL to show the code works with a real RDBMS. `DATABASE\_URL`

selects between them.



\## Why not PostGIS yet



PostGIS is only worth it when you need spatial indexing or

server-side spatial queries. This service computes measurements in

Python and stores them as JSON. Adding PostGIS now would be

over-engineering for a three-endpoint assignment.



\## Error-code taxonomy



\- \*\*400\*\* — the upload is wrong (bad extension, bad magic bytes,

&#x20; unsafe ZIP). Client-side fix.

\- \*\*413\*\* — the file is too large. Client-side fix.

\- \*\*422\*\* — the file was accepted but cannot be processed

&#x20; (e.g. missing CRS). May need a different file.

\- \*\*404\*\* — the requested `file\_id` does not exist.

\- \*\*409\*\* — a measurement request was made for a file whose status is

&#x20; not `COMPLETED`.

\- \*\*500\*\* — unexpected server error. Details are logged, never

&#x20; returned.



\## Security choices



\- Extension is checked \*\*and\*\* magic bytes are checked. A file named

&#x20; `.zip` that isn't a ZIP is rejected before GDAL sees it.

\- Upload is streamed to disk with a hard byte limit so a huge upload

&#x20; cannot fill memory.

\- ZIP extraction enforces entry count, uncompressed size, compression

&#x20; ratio, path containment, and rejects symlinks — the four classic

&#x20; ZIP attack classes.

\- KML files with `<!ENTITY` are rejected because real KML never needs

&#x20; them, and they enable XXE / billion-laughs attacks.

\- Error responses are shaped by the app, not by FastAPI's default

&#x20; handler, so nothing internal leaks.



\## Scalability path



If file sizes and traffic grow:



1\. Move processing to a background worker (Celery / RQ / Arq).

&#x20;  `POST /api/files/` returns immediately with `status=PROCESSING`.

2\. Store uploaded files in object storage (S3 / GCS) instead of the

&#x20;  local temp dir.

3\. Replace the JSON feature column with a PostGIS geometry column

&#x20;  for spatial queries.

4\. Add Alembic migrations instead of `create\_all` on startup.

5\. Put Uvicorn behind Nginx / Traefik and run multiple workers.

