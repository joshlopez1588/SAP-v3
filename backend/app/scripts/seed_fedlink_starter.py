from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import Application, DocumentTemplate, Framework, User


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        admin_result = await session.execute(select(User).where(User.role == "admin", User.is_active.is_(True)))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            print("No admin user found. Run create_initial_admin first.")
            return

        framework_result = await session.execute(
            select(Framework).where(Framework.name == "Fedlink User Access Review - Standard", Framework.is_active.is_(True))
        )
        framework = framework_result.scalar_one_or_none()
        if not framework:
            framework = Framework(
                name="Fedlink User Access Review - Standard",
                description="Starter framework for Fedlink access reviews",
                review_type="user_access",
                version_major=1,
                version_minor=0,
                version_patch=0,
                status="published",
                is_immutable=True,
                settings={"inactive_threshold_days": 90, "high_limit_threshold": 1000000},
                checks=[
                    {
                        "id": "terminated_with_fedlink_access",
                        "name": "Terminated Employee with Active Fedlink Access",
                        "default_severity": "critical",
                        "enabled": True,
                        "condition": {
                            "type": "cross_reference",
                            "mode": "present_in_primary_absent_in_secondary",
                            "match_field": "email",
                        },
                        "filter": {"field": "status", "operator": "equals", "value": "active"},
                        "output_fields": ["identifier", "display_name", "email", "status", "last_activity"],
                        "explainability_template": "Found ${record_count} active accounts missing from HR active records.",
                    },
                    {
                        "id": "inactive_accounts",
                        "name": "Inactive Fedlink Accounts",
                        "default_severity": "medium",
                        "enabled": True,
                        "condition": {
                            "type": "compound",
                            "operator": "AND",
                            "conditions": [
                                {"field": "status", "operator": "equals", "value": "active"},
                                {
                                    "field": "last_activity",
                                    "operator": "older_than_days",
                                    "value": "${settings.inactive_threshold_days}",
                                },
                            ],
                        },
                        "output_fields": ["identifier", "display_name", "email", "last_activity"],
                    },
                    {
                        "id": "admin_access_review",
                        "name": "Administrative Access Review",
                        "default_severity": "info",
                        "enabled": True,
                        "condition": {
                            "type": "role_match",
                            "field": "roles",
                            "mode": "any",
                            "patterns": ["ADMIN*", "*SECURI*", "*ADMIN*"],
                        },
                        "output_fields": ["identifier", "display_name", "roles", "status"],
                    },
                ],
                regulatory_mappings=[{"framework": "FFIEC", "category": "Access Management"}],
                created_by=admin.id,
            )
            session.add(framework)

        app_result = await session.execute(
            select(Application).where(Application.name == "Fedlink Anywhere", Application.is_active.is_(True))
        )
        app = app_result.scalar_one_or_none()
        if not app:
            app = Application(
                name="Fedlink Anywhere",
                description="Federal Reserve wire transfer and ACH settlement system",
                review_type="user_access",
                owner="Operations Department",
                criticality="critical",
                data_classification="confidential",
                context="High sensitivity wire transfer system.",
                review_frequency="quarterly",
                reminder_days=[30, 14, 7],
                created_by=admin.id,
            )
            session.add(app)
            await session.flush()

            template = DocumentTemplate(
                application_id=app.id,
                name="Fedlink Anywhere Users Export",
                format="csv",
                detection={
                    "method": "column_presence",
                    "required_columns": ["userid", "username", "status", "lastlogin", "limit", "authgroup"],
                },
                mapping={
                    "identifier": {"source": "userid", "transform": "lowercase"},
                    "display_name": {"source": "username"},
                    "email": {"source": "email", "transform": "lowercase"},
                    "status": {
                        "source": "status",
                        "transform": "value_map",
                        "value_map": {"A": "active", "D": "disabled"},
                    },
                    "last_activity": {"source": "lastlogin", "transform": "parse_date"},
                    "roles": {"source": "authgroup", "transform": "to_array"},
                    "account_type": {"default": "human"},
                    "extended_attributes.limit": {"source": "limit", "transform": "parse_number"},
                    "extended_attributes.usrlevel": {"source": "usrlevel", "transform": "parse_number"},
                },
                validation=[
                    {"field": "identifier", "rule": "required"},
                    {"field": "identifier", "rule": "unique"},
                ],
                confidence_threshold=0.95,
                created_by=admin.id,
            )
            session.add(template)

        await session.commit()
        print("Fedlink starter framework/application/template seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
