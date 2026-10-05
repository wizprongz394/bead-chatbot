"""Deterministic product search over products.json."""
import json
import re
from functools import lru_cache
from pathlib import Path

from app.config import DATA_DIR

_NUM_RE = re.compile(r"(-?\d+(?:\.\d+)?)")

FAMILY_URL_PATTERNS = {
    "hollow_pin": "hollow-contact-pins",
    "solid_wire_pin": "solid-wire-pins",
    "end_to_end_pin": "end-to-end-pins",
    "pin_assembly": "pin-assemblies",
    "square_end_to_end_pin": "square-end-to-end-pins",
    "round_end_to_end_pin": "round-end-to-end-pins",
    "square_wire_pin": "square-wire-pins",
    "round_wire_pin": "round-wire-pins",
}


def _parse_inches(s):
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
        raise FileNotFoundError("products.json missing.")
    products = json.loads(path.read_text(encoding="utf-8"))
    for p in products:
        p["_length_num"] = _parse_inches(p.get("length_in"))
        p["_square_num"] = _parse_inches(p.get("square_in"))
        p["_diameter_num"] = _parse_inches(p.get("diameter_in"))
    return products


def _ci_match(value, target):
    if target is None:
        return True
    if value is None:
        return False
    return str(target).lower() in str(value).lower()


def _range_match(value, lo, hi):
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


def _family_matches(product_url, family_value):
    if not family_value or not product_url:
        return True
    pattern = FAMILY_URL_PATTERNS.get(str(family_value))
    if not pattern:
        return True
    return pattern in product_url


def search_products(problem, limit=10):
    products = _load_products()
    scored = []

    def cv(name):
        c = getattr(problem, name, None)
        return c.value if c is not None else None

    item_number = cv("item_number")
    material = cv("material")
    pin_type = cv("pin_type")
    end_type = cv("end_type")
    product_family = cv("product_family")

    length_lo = _to_float(getattr(problem, "length_in_min", None))
    length_hi = _to_float(getattr(problem, "length_in_max", None))
    square_lo = _to_float(getattr(problem, "square_in_min", None))
    square_hi = _to_float(getattr(problem, "square_in_max", None))
    dia_lo = _to_float(getattr(problem, "diameter_in_min", None))
    dia_hi = _to_float(getattr(problem, "diameter_in_max", None))

    family_active = bool(product_family)

    for p in products:
        if item_number and p.get("item_number", "").lower() != str(item_number).lower():
            continue
        if material and not _ci_match(p.get("material"), material):
            continue

        # pin_type filter: skip if product has no pin_type AND family filter is active
        if pin_type:
            product_pt = p.get("pin_type")
            if product_pt is not None:
                if not _ci_match(product_pt, pin_type):
                    continue
            elif not family_active:
                continue

        if end_type and not _ci_match(p.get("end_type"), end_type):
            continue
        if not _family_matches(p.get("source_url", ""), product_family):
            continue
        if not _range_match(p.get("_length_num"), length_lo, length_hi):
            continue
        if not _range_match(p.get("_square_num"), square_lo, square_hi):
            continue
        if not _range_match(p.get("_diameter_num"), dia_lo, dia_hi):
            continue

        score = sum([
            1 if item_number else 0,
            1 if material else 0,
            1 if pin_type else 0,
            1 if end_type else 0,
            1 if product_family else 0,
            1 if (length_lo is not None or length_hi is not None) else 0,
            1 if (square_lo is not None or square_hi is not None) else 0,
            1 if (dia_lo is not None or dia_hi is not None) else 0,
        ])

        p_clean = {k: v for k, v in p.items() if not k.startswith("_")}
        scored.append((score, p_clean))

    scored.sort(key=lambda sp: (-sp[0], sp[1].get("item_number", "")))
    return [p for _, p in scored[:limit]]


def total_count():
    return len(_load_products())
