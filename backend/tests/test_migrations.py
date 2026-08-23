from io import StringIO
from pathlib import Path

from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.config import get_settings


def test_initial_migration_generates_postgresql_sql() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    output = StringIO()
    config = Config(backend_root / "alembic.ini", output_buffer=output)

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue()
    assert "CREATE TYPE risk_level" in sql
    assert "CREATE TABLE sites" in sql
    assert "CREATE TABLE inspections" in sql
    assert "CREATE TABLE anomalies" in sql
    assert "CREATE TABLE processing_jobs" in sql
    assert "CREATE TABLE agent_conversations" in sql
    assert "CREATE TABLE agent_messages" in sql
    assert "CREATE TABLE report_chunks" in sql
    assert "CREATE UNIQUE INDEX uq_sites_name_lower" in sql


def test_initial_migration_upgrades_and_downgrades_clean_database(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = (tmp_path / "migration.db").as_posix()
    monkeypatch.setenv("AERIALOPS_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(backend_root / "alembic.ini")

    try:
        command.upgrade(config, "head")
        engine = create_engine(f"sqlite+pysqlite:///{database_path}")
        try:
            assert set(inspect(engine).get_table_names()) == {
                "alembic_version",
                "agent_conversations",
                "agent_messages",
                "anomalies",
                "inspection_images",
                "inspection_reports",
                "inspections",
                "processing_jobs",
                "risk_assessments",
                "report_chunks",
                "sites",
            }
        finally:
            engine.dispose()

        command.downgrade(config, "base")
        engine = create_engine(f"sqlite+pysqlite:///{database_path}")
        try:
            assert inspect(engine).get_table_names() == ["alembic_version"]
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()
