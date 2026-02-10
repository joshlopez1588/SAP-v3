from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.audit_service import record_audit_event, verify_audit_hash_chain


@pytest.mark.asyncio
async def test_audit_chain_verifies() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        actor_id = uuid.uuid4()
        await record_audit_event(
            session,
            actor_id=actor_id,
            actor_type="USER",
            action="create",
            entity_type="framework",
            entity_id=uuid.uuid4(),
            before_state=None,
            after_state={"name": "test"},
            request_id="req-1",
        )
        await record_audit_event(
            session,
            actor_id=actor_id,
            actor_type="USER",
            action="update",
            entity_type="framework",
            entity_id=uuid.uuid4(),
            before_state={"name": "test"},
            after_state={"name": "test2"},
            request_id="req-2",
        )
        await session.commit()

    async with session_maker() as session:
        result = await verify_audit_hash_chain(session)
        assert result.valid is True
        assert result.checked_entries == 2
