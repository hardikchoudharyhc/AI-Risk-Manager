import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .models import Transaction
from .normalize import normalize_record, detect_merchant_schema

import uuid
from datetime import datetime, timezone

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class ValidationStats:
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class IngestionResult:
    ingestion_id: str
    source_type: str
    source_id: str
    merchant_id: str
    format_detected: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    errors: list[str]
    valid_transactions: list[Any] = field(default_factory=list)
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingestion_id": self.ingestion_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "merchant_id": self.merchant_id,
            "format_detected": self.format_detected,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "duplicate_records": self.duplicate_records,
            "errors": self.errors,
            "received_at": self.received_at,
        }


def parse_raw_input(raw_input: bytes | str | list | dict) -> tuple[list[dict[str, Any]], str | None, str]:
    """
    Unified format detection, UTF-8 BOM handling, parsing, and key/value sanitization for CSV/JSON input.
    Returns: (records, parse_error, format_detected)
    """
    if isinstance(raw_input, (dict, list)):
        if isinstance(raw_input, dict):
            records = [raw_input]
        else:
            records = [r for r in raw_input if isinstance(r, dict)]
        return records, None, "json"

    if isinstance(raw_input, bytes):
        if raw_input.startswith(b"\xef\xbb\xbf"):
            raw_input = raw_input[3:]
        try:
            content_str = raw_input.decode("utf-8")
        except UnicodeDecodeError:
            return [], "Encoding Error: File/input must be UTF-8 encoded text.", "unknown"
    else:
        content_str = str(raw_input)

    content_str = content_str.lstrip("\ufeff").strip()
    if not content_str:
        return [], "Uploaded/provided content is empty.", "unknown"

    if content_str.startswith("[") or content_str.startswith("{"):
        try:
            parsed = json.loads(content_str)
            if isinstance(parsed, dict):
                records = [parsed]
            elif isinstance(parsed, list):
                records = [r for r in parsed if isinstance(r, dict)]
            else:
                return [], "JSON content must be a JSON object or array of objects.", "json"
            return records, None, "json"
        except json.JSONDecodeError as e:
            return [], f"Malformed JSON syntax: {e}", "json"
    else:
        try:
            reader = csv.DictReader(io.StringIO(content_str))
            records = []
            for row in reader:
                if not row or not any(row.values()):
                    continue
                clean_row = {}
                for k, v in row.items():
                    if k is not None:
                        clean_k = str(k).strip('\ufeff"\' \t\r\n')
                        clean_v = str(v).strip(' \t\r\n') if isinstance(v, str) else v
                        clean_row[clean_k] = clean_v
                if clean_row:
                    records.append(clean_row)
            if not records:
                return [], "No valid CSV records found.", "csv"
            return records, None, "csv"
        except Exception as e:
            return [], f"Malformed CSV structure: {e}", "csv"


def process_records(
    records: list[dict[str, Any]],
    mapping: dict[str, str],
    model: type[ModelT],
) -> tuple[list[ModelT], ValidationStats]:
    stats = ValidationStats(total_records=len(records))
    valid: list[ModelT] = []
    seen_ids: set[str] = set()
    id_field = next(iter(model.model_fields))
    for index, record in enumerate(records):
        try:
            canonical = normalize_record(record, mapping)
            identifier = str(canonical.get(id_field, ""))
            if identifier in seen_ids:
                stats.duplicate_records += 1
                raise ValueError(f"duplicate {id_field}: {identifier}")
            parsed = model.model_validate(canonical)
            seen_ids.add(identifier)
            valid.append(parsed)
            stats.valid_records += 1
        except (ValueError, TypeError, ValidationError) as error:
            stats.invalid_records += 1
            stats.errors.append(f"record {index}: {error}")
    return valid, stats


def ingest_records(
    raw_input: bytes | str | list | dict,
    source_type: str = "csv",
    source_id: str = "uploaded_file",
    merchant_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    model: type[ModelT] = Transaction,
) -> tuple[list[ModelT], IngestionResult]:
    """
    ONE UNIFIED INGESTION PIPELINE:
    Consumes raw records from ANY data source (CSV, JSON, Manual paste, Razorpay Adapter, Shopify Adapter).
    Performs: Format Parsing -> Schema Mapping -> Canonical Normalization -> Validation & Security -> Deduplication.
    Returns: (valid_canonical_transactions, IngestionResult)
    """
    ingest_id = f"ing_{uuid.uuid4().hex[:8]}"
    rec_time = datetime.now(timezone.utc).isoformat()

    records, parse_err, format_detected = parse_raw_input(raw_input)
    if parse_err:
        res = IngestionResult(
            ingestion_id=ingest_id,
            source_type=source_type,
            source_id=source_id,
            merchant_id=merchant_id or "unknown",
            format_detected=format_detected,
            total_records=0,
            valid_records=0,
            invalid_records=1,
            duplicate_records=0,
            errors=[parse_err],
            valid_transactions=[],
            received_at=rec_time,
        )
        return [], res

    detected_merchant_id, mapping = detect_merchant_schema(records)
    final_merchant_id = merchant_id or detected_merchant_id

    valid_records, stats = process_records(records, mapping, model)

    res = IngestionResult(
        ingestion_id=ingest_id,
        source_type=source_type,
        source_id=source_id,
        merchant_id=final_merchant_id,
        format_detected=format_detected,
        total_records=stats.total_records,
        valid_records=stats.valid_records,
        invalid_records=stats.invalid_records,
        duplicate_records=stats.duplicate_records,
        errors=stats.errors,
        valid_transactions=valid_records,
        received_at=rec_time,
    )
    return valid_records, res


def ingest_raw_data(
    raw_input: bytes | str | list | dict,
    model: type[ModelT] = Transaction,
) -> tuple[list[ModelT], ValidationStats, str, str]:
    """
    Unified Ingestion Adapter Entry Point (Backward Compatible Alias).
    """
    valid_txns, res = ingest_records(raw_input=raw_input, model=model)
    stats = ValidationStats(
        total_records=res.total_records,
        valid_records=res.valid_records,
        invalid_records=res.invalid_records,
        duplicate_records=res.duplicate_records,
        errors=res.errors,
    )
    return valid_txns, stats, res.merchant_id, res.format_detected