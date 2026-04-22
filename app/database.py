import sqlite3
from pathlib import Path
from typing import Generator

from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

_api_engine = None


def _set_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=3000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_engine():
    global _api_engine
    if _api_engine is None:
        db_path = Path(settings.DB_PATH).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        def _connect_ro():
            conn = sqlite3.connect(
                f"file:{db_path}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            return conn

        _api_engine = create_engine(
            "sqlite://",
            creator=_connect_ro,
            pool_pre_ping=True,
        )
        event.listen(_api_engine, "connect", _set_pragmas)
    return _api_engine


def get_crawler_engine():
    db_path = Path(settings.DB_PATH).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    uri = f"sqlite:///{db_path}"
    engine = create_engine(
        uri,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    event.listen(engine, "connect", _set_pragmas)
    return engine


def get_session() -> Generator[Session, None, None]:
    engine = get_engine()
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _ensure_metadata_columns(engine) -> None:
    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(metadata)")
        }
        if "copyrightlink" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE metadata ADD COLUMN copyrightlink TEXT"
                )
            )


def init_db():
    engine = get_crawler_engine()
    Base.metadata.create_all(engine)
    _ensure_metadata_columns(engine)
    engine.dispose()
