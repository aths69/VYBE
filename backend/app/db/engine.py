"""SQLite engine, under the configurable data directory (Section 31).

No migration tooling (Alembic etc.) - tables are created via
Base.metadata.create_all(), plus a small additive-column check so a new
nullable field added to an existing model (e.g. Phase 5 adding
useful_output_count to sessions) doesn't require deleting a real database
that already has sessions in it. This only ever ADDS columns - it can't
rename, retype, or drop one; a real migration tool is a drop-in upgrade if
the schema ever needs that.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

DB_PATH = settings.data_dir / "vybe.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_tables() -> None:
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    _add_missing_columns(Base)


def _add_missing_columns(base) -> None:
    inspector = inspect(engine)
    for table in base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            col_type = column.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
                )
