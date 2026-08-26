import html
from typing import Any

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
MAX_RECORD_COUNT = 1000  # Max 1000 records per upload batch
ALLOWED_EXTENSIONS = {".csv", ".json", ".txt"}


def validate_file_upload(raw_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Validate file size, extension, non-emptiness, and UTF-8 encoding safely."""
    if not raw_bytes or len(raw_bytes.strip()) == 0:
        return False, "Uploaded file is empty."

    if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
        return False, f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Invalid file format. Only CSV, JSON, and TXT uploads are allowed."

    try:
        raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False, "Invalid file encoding. File must be valid UTF-8 text."

    return True, ""


def parse_and_validate_input(content_str: str, file_type: str) -> tuple[list[dict[str, Any]], str | None]:
    """Safely parse CSV/JSON text content and enforce batch size limits."""
    from .pipeline import parse_raw_input
    records, parse_err, _ = parse_raw_input(content_str)
    if parse_err:
        return [], parse_err
    if len(records) > MAX_RECORD_COUNT:
        return [], f"Record count ({len(records)}) exceeds maximum allowed batch limit of {MAX_RECORD_COUNT} records."
    return records, None


def sanitize_display_text(val: Any) -> str:
    """Sanitize arbitrary user-provided input strings to prevent HTML/Script injection in UI displays."""
    if val is None:
        return ""
    text = str(val)
    return html.escape(text)
