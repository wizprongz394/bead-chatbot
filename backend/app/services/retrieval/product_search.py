"""Deterministic product search over products.json."""
import json
import re
from functools import lru_cache
from pathlib import Path

from app.config import DATA_DIR

_NUM_RE = re.compile(r"(-?\d+(?:\.\d+)?)")


def _parse_inches(s):
    """'0.330 in' -> 0.330 ; None -> None"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    m = _NUM_RE.search(str(s))
    return float(m.group(1)) if m else None


@lru_cache(maxsize=1)
def _load_products():
    path = DATA_DIR / "products.json"
    if not path.exists():
        raise FileNotFoundError("products.json missing. Run the ingestion pipeline first.")
    products = json.loads(path.read_text(encoding="utf-8"))
    for p in products:
        p["_length_num"] = _parse_inches(p.get("length_in"))
        p["_square_num"] = _parse_inches(p.get("square_in"))
        p["_diameter_num"] = _parse_inches(p.get("diameter_in"))
    return products


def _ci_match(value, target):
    """Case-insensitive substring match."""
    if target is None:
        return True
    if value is None:
        return False
    return str(target).lower() in str(value).lower()


def _range_match(value, lo, hi):
    """value must be within [lo, hi]. None bounds ignored. Missing value fails."""
    if lo is None and hi is None:
        return True
    if value is None:
        return False
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


def _to_float(c):
    if c is None:
        return None
    v = c["value"] if isinstance(c, dict) else c
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def search_products(problem, limit=10):
    """
    problem: ProblemState.
    Returns list of matching products (public fields only), ordered by
    match-score (descending) then item_number (ascending).
    """
    products = _load_products()
    scored = []

    def cv(name):
        c = getattr(problem, name, None)
        return c.value if c is not None else None

    item_number = cv("item_number")
    material = cv("material")
    pin_type = cv("pin_type")
    end_type = cv("end_type")

    length_lo = _to_float(getattr(problem, "length_in_min", None))
    length_hi = _to_float(getattr(problem, "length_in_max", None))
    square_lo = _to_float(getattr(problem, "square_in_min", None))
    square_hi = _to_float(getattr(problem, "square_in_max", None))
    dia_lo = _to_float(getattr(problem, "diameter_in_min", None))
    dia_hi = _to_float(getattr(problem, "diameter_in_max", None))

    for p in products:
        if item_number and p.get("item_number", "").lower() != str(item_number).lower():
            continue
        if material and not _ci_match(p.get("material"), material):
            continue
        if pin_type and not _ci_match(p.get("pin_type"), pin_type):
            continue
        if end_type and not _ci_match(p.get("end_type"), end_type):
            continue
        if not _range_match(p.get("_length_num"), length_lo, length_hi):
            continue
        if not _range_match(p.get("_square_num"), square_lo, square_hi):
            continue
        if not _range_match(p.get("_diameter_num"), dia_lo, dia_hi):
            continue

        # Score is computed locally and never stored on the returned dict
        score = sum([
            1 if item_number else 0,
            1 if material else 0,
            1 if pin_type else 0,
            1 if end_type else 0,
            1 if (length_lo is not None or length_hi is not None) else 0,
            1 if (square_lo is not None or square_hi is not None) else 0,
            1 if (dia_lo is not None or dia_hi is not None) else 0,
        ])

        # Strip internal fields from response
        p_clean = {k: v for k, v in p.items() if not k.startswith("_")}
        scored.append((score, p_clean))

    scored.sort(key=lambda sp: (-sp[0], sp[1].get("item_number", "")))
    return [p for _, p in scored[:limit]]


def total_count():
    return len(_load_products())
