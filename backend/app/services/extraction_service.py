from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil import parser as date_parser


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".xml", ".pdf"}


class ExtractionError(Exception):
    pass


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sanitize_csv_formula(value: Any) -> Any:
    if isinstance(value, str) and value and value[0] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def load_rows_from_bytes(filename: str, content: bytes) -> list[dict[str, Any]]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ExtractionError("FILE_FORMAT_UNSUPPORTED")

    if ext == ".csv":
        text = content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        return [{normalize_key(k): sanitize_csv_formula(v) for k, v in row.items()} for row in reader]

    if ext in {".xlsx", ".xls"}:
        df = pd.read_excel(io.BytesIO(content)).fillna("")
        rows = df.to_dict(orient="records")
        normalized: list[dict[str, Any]] = []
        for row in rows:
            normalized.append({normalize_key(str(k)): sanitize_csv_formula(v) for k, v in row.items()})
        return normalized

    raise ExtractionError("Unsupported parser for file type in this phase")


def _apply_transform(value: Any, config: dict[str, Any]) -> Any:
    transform = config.get("transform")
    if value is None or value == "":
        if "default" in config:
            return config["default"]
        return value

    if transform == "lowercase":
        return str(value).lower()

    if transform == "uppercase":
        return str(value).upper()

    if transform == "value_map":
        value_map = config.get("value_map", {})
        return value_map.get(str(value), config.get("default", value))

    if transform == "to_array":
        if isinstance(value, list):
            return value
        separator = config.get("separator", ";")
        return [item.strip() for item in str(value).split(separator) if item.strip()]

    if transform == "parse_date":
        try:
            parsed = date_parser.parse(str(value))
            return parsed.isoformat()
        except (ValueError, TypeError, OverflowError):
            return None

    if transform == "parse_number":
        cleaned = str(value).replace(",", "").replace("$", "")
        try:
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return None

    return value


def apply_mapping(
    rows: list[dict[str, Any]],
    mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    extracted: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    required_fields = {"identifier", "status"}
    valid_count = 0

    for index, row in enumerate(rows):
        normalized: dict[str, Any] = {
            "identifier": None,
            "display_name": None,
            "email": None,
            "status": None,
            "last_activity": None,
            "department": None,
            "manager": None,
            "account_type": "human",
            "roles": [],
            "extended_attributes": {},
            "data": {},
            "validation_status": "valid",
            "validation_messages": [],
        }

        for target_field, config in mapping.items():
            if not isinstance(config, dict):
                continue

            source = normalize_key(config.get("source", "")) if config.get("source") else None
            value = row.get(source) if source else config.get("default")
            transformed = _apply_transform(value, config)

            if target_field.startswith("extended_attributes."):
                extended_field = target_field.split(".", 1)[1]
                normalized["extended_attributes"][extended_field] = transformed
                continue

            if target_field in normalized:
                normalized[target_field] = transformed
            else:
                normalized["data"][target_field] = transformed

        missing_required = [field for field in required_fields if not normalized.get(field)]
        if missing_required:
            normalized["validation_status"] = "warning"
            normalized["validation_messages"].append(f"Missing required fields: {', '.join(missing_required)}")
            warnings.append(
                {
                    "row": index + 1,
                    "type": "missing_required",
                    "fields": missing_required,
                }
            )
        else:
            valid_count += 1

        extracted.append(normalized)

    if not rows:
        return extracted, [{"type": "empty_file"}], 0.0

    confidence = Decimal(valid_count / len(rows))
    return extracted, warnings, float(round(confidence, 4))


def compute_extraction_checksum(records: list[dict[str, Any]]) -> str:
    payload = str(records).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_iso_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return date_parser.parse(str(value))
    except (ValueError, TypeError):
        return None
