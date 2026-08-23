from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .normalize import normalize_record

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class ValidationStats:
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    errors: list[str] = field(default_factory=list)


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