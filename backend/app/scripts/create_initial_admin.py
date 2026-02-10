from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import get_password_hash, validate_password_policy
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import Invite, User


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    email = input("Admin email: ").strip().lower()
    name = input("Full name: ").strip()
    password = input("Password: ").strip()

    validate_password_policy(password)

    async with AsyncSessionLocal() as session:
        existing_result = await session.execute(select(User).where(User.email == email))
        existing = existing_result.scalar_one_or_none()
        if existing:
            print("Admin already exists for this email.")
            return

        user = User(
            email=email,
            name=name,
            role="admin",
            password_hash=get_password_hash(password),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        for role in ["analyst", "reviewer", "auditor"]:
            invite = Invite(
                code=f"INV-{secrets.token_hex(3).upper()}",
                role=role,
                created_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=30),
                is_active=True,
            )
            session.add(invite)

        await session.commit()
        print("Initial admin created and starter invite codes generated.")


if __name__ == "__main__":
    asyncio.run(main())
