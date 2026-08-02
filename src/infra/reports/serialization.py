from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

_DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@")


def serialize_cell(value: Any) -> str:
    if value is None:
        serialized = ""
    elif isinstance(value, (dict, list, tuple)):
        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(value, (datetime, date)):
        serialized = value.isoformat()
    else:
        serialized = str(value)

    if serialized.startswith(_DANGEROUS_FORMULA_PREFIXES):
        return f"'{serialized}"
    return serialized
