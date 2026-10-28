"""PostgreSQL-only regression test for concurrent first subscription creation.

This test deliberately uses a unique temporary schema and accepts only a local
PostgreSQL host. It must never point at a developer's or production database.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.salon import Salon
from app.models.subscription import Subscription
from app.services.subscription import _get_subscription


def test_concurrent_first_subscription_creation_is_serialized_by_postgres():
    database_url = os.environ.get("TEST_POSTGRESQL_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_POSTGRESQL_URL is not configured; PostgreSQL lock test is CI-only")

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        pytest.skip("TEST_POSTGRESQL_URL must be a PostgreSQL connection URL")
    # The test creates and drops a uniquely named schema. Fail closed on remote
    # hosts so it cannot accidentally mutate a production database.
    if (parsed.hostname or "").lower() not in {"db", "localhost", "127.0.0.1", "::1"}:
        pytest.skip("PostgreSQL concurrency test only runs against a local CI database")

    schema = f"test_sub_lock_{uuid.uuid4().hex[:16]}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    schema_engine = None

    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        schema_engine = create_engine(
            database_url,
            pool_size=4,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema}"},
        )
        Base.metadata.create_all(bind=schema_engine)

        with Session(schema_engine) as session:
            salon = Salon(name="Concurrent First Use Test Salon", email=f"{schema}@example.invalid")
            session.add(salon)
            session.commit()
            salon_id = salon.id

        start = threading.Barrier(2)

        def create_or_read_subscription() -> str:
            with Session(schema_engine, autoflush=False, autocommit=False) as session:
                start.wait(timeout=10)
                subscription = _get_subscription(session, salon_id, lock=True)
                subscription_id = str(subscription.id)
                # Releasing the parent-row lock at commit lets the competing
                # request re-read the now-existing child subscription.
                session.commit()
                return subscription_id

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(create_or_read_subscription)
            second = executor.submit(create_or_read_subscription)
            subscription_ids = {first.result(timeout=30), second.result(timeout=30)}

        assert len(subscription_ids) == 1, "Concurrent first use created different subscription IDs"
        with Session(schema_engine) as session:
            rows = session.execute(
                select(Subscription.id).where(Subscription.salon_id == salon_id)
            ).scalars().all()
            assert len(rows) == 1, "A salon must have exactly one subscription row"
    finally:
        if schema_engine is not None:
            schema_engine.dispose()
        try:
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        finally:
            admin_engine.dispose()
