from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Extraction,
    ExtractedRecord,
    Finding,
    Framework,
    ReferenceRecord,
    Review,
    ReviewReferenceDataset,
)


def _resolve_field(record: dict[str, Any], field_path: str) -> Any:
    parts = field_path.split(".")
    current: Any = record
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _condition_match(record: dict[str, Any], condition: dict[str, Any], settings: dict[str, Any]) -> bool:
    if condition.get("type") == "compound":
        operator = condition.get("operator", "AND").upper()
        conditions = condition.get("conditions", [])
        if operator == "OR":
            return any(_condition_match(record, c, settings) for c in conditions)
        return all(_condition_match(record, c, settings) for c in conditions)

    field = condition.get("field")
    operator = condition.get("operator")
    raw_value = condition.get("value")
    if isinstance(raw_value, str) and raw_value.startswith("${settings.") and raw_value.endswith("}"):
        key = raw_value.replace("${settings.", "").replace("}", "")
        raw_value = settings.get(key)

    actual = _resolve_field(record, field) if field else None

    if operator == "equals":
        return actual == raw_value
    if operator == "not_equals":
        return actual != raw_value
    if operator == "greater_than_or_equal":
        try:
            return float(actual) >= float(raw_value)
        except (TypeError, ValueError):
            return False
    if operator == "greater_than":
        try:
            return float(actual) > float(raw_value)
        except (TypeError, ValueError):
            return False
    if operator == "older_than_days":
        if not actual:
            return False
        if isinstance(actual, str):
            try:
                actual_dt = datetime.fromisoformat(actual.replace("Z", "+00:00"))
            except ValueError:
                return False
        elif isinstance(actual, datetime):
            actual_dt = actual
        else:
            return False

        delta_days = (datetime.now(UTC) - actual_dt.replace(tzinfo=UTC)).days
        try:
            threshold = int(raw_value)
        except (TypeError, ValueError):
            return False
        return delta_days >= threshold

    if operator == "contains":
        if isinstance(actual, list):
            return raw_value in actual
        return str(raw_value) in str(actual)

    return False


def _eval_json_logic(expr: Any, context: dict[str, Any]) -> bool:
    if not isinstance(expr, dict):
        return bool(expr)

    if ">" in expr:
        left, right = expr[">"]
        return float(_eval_json_logic_value(left, context)) > float(_eval_json_logic_value(right, context))
    if ">=" in expr:
        left, right = expr[">="]
        return float(_eval_json_logic_value(left, context)) >= float(_eval_json_logic_value(right, context))
    if "<" in expr:
        left, right = expr["<"]
        return float(_eval_json_logic_value(left, context)) < float(_eval_json_logic_value(right, context))
    if "<=" in expr:
        left, right = expr["<="]
        return float(_eval_json_logic_value(left, context)) <= float(_eval_json_logic_value(right, context))
    if "==" in expr:
        left, right = expr["=="]
        return _eval_json_logic_value(left, context) == _eval_json_logic_value(right, context)
    return False


def _eval_json_logic_value(node: Any, context: dict[str, Any]) -> Any:
    if isinstance(node, dict) and "var" in node:
        return context.get(node["var"])
    return node


def _resolve_severity(check: dict[str, Any], context: dict[str, Any]) -> str:
    for rule in check.get("severity_rules", []):
        condition = rule.get("condition")
        if condition and _eval_json_logic(condition, context):
            return rule.get("severity", check.get("default_severity", "medium"))
    return check.get("default_severity", "medium")


def _render_explainability(template: str | None, check_name: str, record_count: int) -> str:
    if template:
        return template.replace("${record_count}", str(record_count))
    return f"Check '{check_name}' triggered for {record_count} record(s)."


async def run_review_analysis(db: AsyncSession, review: Review, framework: Framework) -> tuple[int, str]:
    rows_result = await db.execute(
        select(ExtractedRecord)
        .join(Extraction, ExtractedRecord.extraction_id == Extraction.id)
        .where(Extraction.review_id == review.id, Extraction.is_active.is_(True))
        .order_by(ExtractedRecord.record_index.asc())
    )
    records = list(rows_result.scalars().all())

    record_payloads: list[dict[str, Any]] = []
    for rec in records:
        record_payloads.append(
            {
                "id": str(rec.id),
                "identifier": rec.identifier,
                "display_name": rec.display_name,
                "email": rec.email,
                "status": rec.status,
                "last_activity": rec.last_activity,
                "department": rec.department,
                "manager": rec.manager,
                "account_type": rec.account_type,
                "roles": rec.roles or [],
                "extended_attributes": rec.extended_attributes or {},
                "data": rec.data or {},
            }
        )

    ref_dataset_ids_result = await db.execute(
        select(ReviewReferenceDataset.reference_dataset_id).where(ReviewReferenceDataset.review_id == review.id)
    )
    ref_dataset_ids = [row[0] for row in ref_dataset_ids_result.all()]

    reference_records: list[ReferenceRecord] = []
    if ref_dataset_ids:
        rr = await db.execute(select(ReferenceRecord).where(ReferenceRecord.dataset_id.in_(ref_dataset_ids)))
        reference_records = list(rr.scalars().all())

    await db.execute(delete(Finding).where(Finding.review_id == review.id))

    findings_created = 0
    for check in framework.checks:
        if not check.get("enabled", True):
            continue

        check_id = check.get("id", f"check_{findings_created + 1}")
        check_name = check.get("name", check_id)

        affected_records: list[dict[str, Any]] = []
        context_for_severity: dict[str, Any] = {}

        condition = check.get("condition", {})
        condition_type = condition.get("type")

        if condition_type == "role_match":
            field = condition.get("field", "roles")
            patterns = condition.get("patterns", [])
            mode = condition.get("mode", "any")

            for rec in record_payloads:
                roles = _resolve_field(rec, field) or []
                if not isinstance(roles, list):
                    continue
                matches = [any(fnmatch.fnmatch(str(role).upper(), pattern.upper()) for pattern in patterns) for role in roles]
                if (mode == "any" and any(matches)) or (mode != "any" and all(matches)):
                    affected_records.append(rec)

        elif condition_type == "cross_reference":
            mode = condition.get("mode", "present_in_primary_absent_in_secondary")
            match_field = condition.get("match_field")
            match_on = condition.get("match_on")
            filter_def = check.get("filter") or condition.get("primary_dataset", {}).get("filter")

            primary_records = record_payloads
            if isinstance(filter_def, dict):
                primary_records = [r for r in primary_records if _condition_match(r, filter_def, framework.settings or {})]

            secondary_active_index: set[str] = set()
            reference_map: dict[str, ReferenceRecord] = {}
            for ref in reference_records:
                key_candidates = [ref.email, ref.identifier]
                for raw in key_candidates:
                    if not raw:
                        continue
                    key = str(raw).strip().lower()
                    reference_map[key] = ref
                    if not ref.employment_status or ref.employment_status.lower() == "active":
                        secondary_active_index.add(key)

            for rec in primary_records:
                if match_field:
                    candidate = _resolve_field(rec, match_field)
                elif isinstance(match_on, list) and match_on:
                    candidate = _resolve_field(rec, match_on[0].get("primary_field", "email"))
                else:
                    candidate = rec.get("email") or rec.get("identifier")

                key = str(candidate).strip().lower() if candidate else ""
                missing = bool(key) and key not in secondary_active_index
                if mode == "present_in_primary_absent_in_secondary" and missing:
                    matched_reference = reference_map.get(key)
                    if matched_reference and matched_reference.termination_date:
                        context_for_severity["days_since_termination"] = (
                            datetime.now(UTC).date() - matched_reference.termination_date
                        ).days
                    affected_records.append(rec)

        elif condition_type == "compound":
            for rec in record_payloads:
                if _condition_match(rec, condition, framework.settings or {}):
                    affected_records.append(rec)

        else:
            for rec in record_payloads:
                if _condition_match(rec, condition, framework.settings or {}):
                    affected_records.append(rec)

        if not affected_records:
            continue

        finding = Finding(
            review_id=review.id,
            check_id=check_id,
            check_name=check_name,
            severity=_resolve_severity(check, context_for_severity),
            explainability=_render_explainability(check.get("explainability_template"), check_name, len(affected_records)),
            record_count=len(affected_records),
            affected_record_ids=[r["id"] for r in affected_records],
            output_fields=check.get("output_fields", ["identifier", "display_name", "email", "status"]),
        )
        db.add(finding)
        findings_created += 1

    checksum_payload = {
        "review_id": str(review.id),
        "framework_id": str(framework.id),
        "check_count": len(framework.checks),
        "record_count": len(record_payloads),
    }
    checksum = hashlib.sha256(json.dumps(checksum_payload, sort_keys=True).encode("utf-8")).hexdigest()

    review.analysis_checksum = checksum
    review.status = "analyzed"

    return findings_created, checksum
