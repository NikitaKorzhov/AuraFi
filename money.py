from __future__ import annotations


def to_kopecks(amount: float | int) -> int:
    """Converts a hryvnia amount (float|int) into kopecks (int) for storage/calculation."""
    return round(amount * 100)


def to_display(kopecks: int) -> float | int:
    """Converts kopecks (int) back into a hryvnia amount (int if whole, float otherwise)."""
    value = kopecks / 100
    whole = int(value)
    return whole if value == whole else round(value, 2)
