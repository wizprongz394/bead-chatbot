"""Extractors: product tables from viewitems pages, article text from blog/category."""

import re as _re
from bs4 import BeautifulSoup

PRODUCT_HEADER_MAP = {
    "item #": "item_number",
    "item number": "item_number",
    "mat'l type": "material",
    "material type": "material",
    "material": "material",
    "type": "pin_type",
    "end type": "end_type",
    "feature type": "feature_type",
    "length \"l\"": "length_in",
    "length (l)": "length_in",
    "square \"a\"": "square_in",
    "diameter \"d\"": "diameter_in",
}


def _normalize_header(raw):
    return PRODUCT_HEADER_MAP.get(raw.strip().lower())


def _clean_cell(text):
    return text.replace("N/A", "").strip()


def extract_product_table(soup):
    best_table = None
    best_rows = 0
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
        header_norm = [h.strip().lower() for h in header_cells]
        if "item #" in header_norm or "item number" in header_norm:
            if len(rows) > best_rows:
                best_table = table
                best_rows = len(rows)
    if best_table is None:
        return []
    rows = best_table.find_all("tr")
    header_cells = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
    columns = [_normalize_header(h) for h in header_cells]
    products = []
    for row in rows[1:]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if not cells or not any(cells):
            continue
        item = {}
        for col_name, cell in zip(columns, cells):
            if col_name is None:
                continue
            item[col_name] = _clean_cell(cell)
        if item.get("item_number"):
            products.append(item)
    return products


def extract_article_text(soup):
    """Clean narrative text. Aggressively strips chrome and non-content."""
    for tag in soup(["script", "style", "nav", "footer", "header", "form",
                     "noscript", "iframe", "svg", "picture"]):
        tag.decompose()
    for tag in soup.find_all("img"):
        tag.decompose()
    for el in soup.find_all(attrs={"style": _re.compile(r"display\s*:\s*none", _re.I)}):
        el.decompose()
    for el in soup.find_all(attrs={"hidden": True}):
        el.decompose()
    for cls in ["breadcrumb", "breadcrumbs", "sidebar", "menu", "navigation",
                "cookie", "banner", "popup", "modal", "share", "social"]:
        for el in soup.select("." + cls + ", [class*=" + cls + "]"):
            el.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("x")]
    return "\n".join(lines)
