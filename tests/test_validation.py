from tests.helpers import build_zip, post_file


def test_invalid_extension(client):
    response = post_file(client, "notes.txt", b"hello")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_empty_upload(client):
    response = post_file(client, "empty.kml", b"")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_oversized_upload(client, small_limits):
    content = b"<kml>" + b"x" * (1024 * 1024 + 1)
    response = post_file(client, "big.kml", content)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_kml_extension_with_wrong_content(client):
    response = post_file(client, "fake.kml", b"just some text, not xml")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_CONTENT"


def test_invalid_zip(client):
    response = post_file(client, "broken.zip", b"this is not a zip file")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_CONTENT"


def test_zip_without_shapefile(client):
    response = post_file(client, "docs.zip", build_zip({"readme.txt": b"hello"}))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_SHAPEFILE"


def test_zip_missing_required_sidecar(client):
    response = post_file(client, "partial.zip", build_zip({"a.shp": b"x", "a.prj": b"x"}))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INCOMPLETE_SHAPEFILE"


def test_zip_path_traversal(client):
    response = post_file(client, "evil.zip", build_zip({"../../evil.shp": b"x"}))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSAFE_ZIP"


def test_zip_bomb(client):
    response = post_file(client, "bomb.zip", build_zip({"big.shp": b"\0" * 3 * 1024 * 1024}))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSAFE_ZIP"


def test_error_envelope_is_consistent(client):
    responses = [
        post_file(client, "notes.txt", b"hello"),
        client.post("/api/files/"),
        client.get("/api/files/missing/"),
        client.get("/this/route/does/not/exist"),
    ]
    for response in responses:
        assert response.status_code >= 400
        error = response.json()["error"]
        assert set(error) == {"code", "message", "details"}
        assert "Traceback" not in response.text
