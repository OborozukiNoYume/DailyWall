import sqlite3
import threading
import time

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app import database
from app.config import settings


def test_api_engine_uses_nullpool_for_readonly_sqlite(tmp_path, monkeypatch):
    db_file = tmp_path / "readonly.db"
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()

    original_engine = database._api_engine
    database._api_engine = None
    monkeypatch.setattr(settings, "DB_PATH", str(db_file))

    try:
        engine = database.get_engine()
        assert isinstance(engine.pool, NullPool)

        session_factory = sessionmaker(bind=engine)
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(8)

        def worker(index: int) -> None:
            session = session_factory()
            try:
                barrier.wait()
                for _ in range(10):
                    session.execute(text("SELECT 1")).scalar()
                    time.sleep(0.005)
            except Exception as exc:  # pragma: no cover - assertion carries detail
                with lock:
                    errors.append((index, repr(exc)))
            finally:
                session.close()

        threads = [
            threading.Thread(target=worker, args=(index,))
            for index in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
    finally:
        if database._api_engine is not None:
            database._api_engine.dispose()
        database._api_engine = original_engine
