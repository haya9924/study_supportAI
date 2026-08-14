"""SQLAlchemy エンジン / セッション。"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import settings


class Base(DeclarativeBase):
    pass


settings.ensure_dirs()

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401  (モデル登録のため import)

    Base.metadata.create_all(bind=engine)
    _run_light_migrations()


# 既存 DB に後付けカラムを追加する軽量マイグレーション (SQLite)。
# create_all は既存テーブルを変更しないため、追加カラムはここで補う。
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "review_logs": {
        "prev_fsrs_state": "TEXT",
        "prev_due": "DATETIME",
        "prev_reps": "INTEGER DEFAULT 0",
        "prev_is_new": "BOOLEAN DEFAULT 0",
    },
    "materials": {
        "year": "VARCHAR DEFAULT ''",
        "exam_type": "VARCHAR DEFAULT ''",
    },
}


def _run_light_migrations() -> None:
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            for name, ddl in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"
                    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
