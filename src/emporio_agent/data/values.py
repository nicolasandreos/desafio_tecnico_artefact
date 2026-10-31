"""Convert recorded numeric cells without replacing a missing value."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation


def recorded_number(value: object) -> int | float | None:
    """Return a recorded number, or None when the cell is empty."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return int(value)
        return value
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if number == number.to_integral_value():
        return int(number)
    return float(number)
