import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import _set_pragmas, get_session as _get_session
from app.main import app
from app.models import Base, Metadata, Resource
from fastapi.testclient import TestClient

from sqlalchemy import create_engine


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _set_pragmas)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session = Session(db_engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_data(db_session):
    resource = Resource(
        sha256="a" * 64,
        year=2026,
        month=4,
        base_path="wallpaper/2026/04/" + "a" * 64,
        ext="jpg",
        mime_type="image/jpeg",
        width=3840,
        height=2160,
        bytes=5000000,
        is_deleted=0,
    )
    db_session.add(resource)

    meta = Metadata(
        mkt="zh-CN",
        date="2026-04-18",
        sha256="a" * 64,
        hsh="test_hsh_1",
        title="Test Wallpaper",
        copyright="Test Copyright",
        is_deleted=0,
    )
    db_session.add(meta)
    db_session.commit()

    return {"resource": resource, "metadata": meta}


@pytest.fixture
def api_client(db_engine):
    from app.services import filter_service

    _session_factory = sessionmaker(bind=db_engine)

    def _override_get_session():
        session = _session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[_get_session] = _override_get_session
    filter_service._cache.clear()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
