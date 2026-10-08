import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import app
from app.models import file as _models  # noqa: F401


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def small_limits():
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_size_mb=1)
    yield
    app.dependency_overrides.pop(get_settings, None)
