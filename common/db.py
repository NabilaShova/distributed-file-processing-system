"""Database engine helpers shared by the coordinator and workers."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str) -> Engine:
    """Open a database engine. The URL is not written to logs."""
    connect_args = {}
    if database_url.startswith("mysql"):
        connect_args["connect_timeout"] = 3
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_db_engine(database_url), expire_on_commit=False)


def check_connection(database_url: str) -> bool:
    """Return True when the database accepts a simple query."""
    engine = create_db_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()
