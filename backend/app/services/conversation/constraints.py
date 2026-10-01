"""Regex-based constraint extraction. No LLM."""
import re


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def extract_item_number(text):
    m = re.search(r"\b([A-Z]\d{3}-\d{3,4}[A-Z]{0,3})\b", text.upper())
    return m.group(1) if m else None


def extract_product_family(text):
    t = text.lower()
    if "end to end" in t or "end-to-end" in t or "tandem" in t:
        return "end_to_end_pin"
    if "hollow" in t:
        return "hollow_pin"
    if "solid wire" in t or "solid-wire" in t or ("solid" in t and "wire" in t):
        return "solid_wire_pin"
    if "pin assembly" in t or "pin assemblies" in t:
        return "pin_assembly"
    return None


def extract_pin_type(text):
    t = text.lower()
    for cand in ["square tandem", "round tandem", "square wire", "round wire", "square", "round", "hollow"]:
        if cand in t:
            return cand.title()
    return None


def extract_application(text):
    t = text.lower()
    for key, val in [("medical","medical"), ("automotive","automotive"), ("car","automotive"), ("vehicle","automotive"),
                     ("aerospace","aerospace"), ("defense","aerospace"), ("industrial","industrial"),
                     ("pcb","pcb"), ("board","pcb"), ("overmold","overmolded"),
                     ("deutsch","deutsch_compatible"), ("connector","connector")]:
        if key in t:
            return val
    return None


def extract_mounting(text):
    t = text.lower()
    if "through-hole" in t or "through hole" in t or "throughhole" in t:
        return "through_hole"
    if "smd" in t or "surface mount" in t or "smt" in t:
        return "smd"
    if "press fit" in t or "press-fit" in t:
        return "press_fit"
    return None


def extract_material(text):
    m = re.search(r"\b([CK]\d{5})\b", text.upper())
    return m.group(1) if m else None


def extract_length_range(text):
    t = text.lower()
    m = re.search(r"(\d+\.\d+)\s*(in|inch|inches|mm)?\s*(length|l\b)", t)
    if m:
        v = _num(m.group(1))
        return (v, v) if v else None
    m = re.search(r"between (\d+\.\d+) and (\d+\.\d+)", t)
    if m:
        return (_num(m.group(1)), _num(m.group(2)))
    m = re.search(r"(under|less than|below) (\d+\.\d+)", t)
    if m:
        return (None, _num(m.group(2)))
    m = re.search(r"(over|more than|greater than|above) (\d+\.\d+)", t)
    if m:
        return (_num(m.group(2)), None)
    return None


def extract_diameter_range(text):
    t = text.lower()
    if "diameter" not in t and "dia" not in t:
        return None
    m = re.search(r"(?:diameter|dia\.?)\s*(?:of|is|:)?\s*(\d+\.\d+)", t)
    if m:
        v = _num(m.group(1))
        return (v, v) if v else None
    return None


def extract_volume(text):
    # Normalize commas so "10,000" becomes "10000"
    t = text.lower().replace(",", "")
    # "10000 pieces" / "5000 pcs" / "200 units"
    m = re.search(r"\b(\d{2,})\s*(pieces|units|pcs|parts|ea|each)\b", t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    # Bare large number (heuristic: >= 100)
    m = re.search(r"\b(\d{3,})\b", t)
    if m:
        try:
            v = int(m.group(1))
            if v >= 100:
                return v
        except ValueError:
            return None
    return None


def extract_into_state(text, state):
    newly_set = {}
    for field_name, extractor in [
        ("item_number", extract_item_number),
        ("product_family", extract_product_family),
        ("pin_type", extract_pin_type),
        ("application", extract_application),
        ("mounting", extract_mounting),
        ("material", extract_material),
        ("volume", extract_volume),
    ]:
        value = extractor(text)
        if value is not None:
            state.set(field_name, value, source="user_stated", confidence="high")
            newly_set[field_name] = value

    lr = extract_length_range(text)
    if lr:
        lo, hi = lr
        if lo is not None:
            state.set("length_in_min", lo, source="user_stated")
            newly_set["length_in_min"] = lo
        if hi is not None:
            state.set("length_in_max", hi, source="user_stated")
            newly_set["length_in_max"] = hi

    dr = extract_diameter_range(text)
    if dr:
        lo, hi = dr
        if lo is not None:
            state.set("diameter_in_min", lo, source="user_stated")
            newly_set["diameter_in_min"] = lo
        if hi is not None:
            state.set("diameter_in_max", hi, source="user_stated")
            newly_set["diameter_in_max"] = hi

    return newly_set
