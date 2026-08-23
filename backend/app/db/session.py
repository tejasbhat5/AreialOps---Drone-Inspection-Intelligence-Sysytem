from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Provide one transaction-capable session per request."""
    with get_session_factory()() as session:
        yield session


def database_is_ready() -> bool:
    """Return whether PostgreSQL accepts a minimal query."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def reset_database_caches() -> None:
    """Clear cached engine/session objects; intended for tests and process reconfiguration."""
    get_session_factory.cache_clear()
    get_engine.cache_clear()
