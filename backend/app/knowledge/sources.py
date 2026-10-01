"""URL discovery. Produces product/category/content URL lists."""

import gzip
import io
import re
import xml.etree.ElementTree as ET
import zipfile

import httpx

from app.config import (
    USER_AGENT,
    CATALOG_SITEMAP_INDEX,
    BLOG_RSS,
    MAIN_SITE_BASE,
    MAIN_SITE_CANDIDATE_PATHS,
)


def _client():
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    )


def _decompress(content: bytes) -> str:
    if content[:2] == b"\x1f\x8b":
        return gzip.decompress(content).decode("utf-8", errors="replace")
    if content[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            xml_names = [n for n in names if n.lower().endswith(".xml")]
            target = xml_names[0] if xml_names else names[0]
            return zf.read(target).decode("utf-8", errors="replace")
    return content.decode("utf-8", errors="replace")


def _strip_ns(xml_text: str) -> str:
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", xml_text)
    xml_text = re.sub(r"<(/?)(\w+):(\w+)", r"<\1\3", xml_text)
    xml_text = re.sub(r'\s(\w+):(\w+)=', r" \2=", xml_text)
    if xml_text.startswith("\ufeff"):
        xml_text = xml_text[1:]
    return xml_text


def discover_catalog_urls() -> tuple[list[str], list[str]]:
    with _client() as client:
        r = client.get(CATALOG_SITEMAP_INDEX)
        r.raise_for_status()
        xml_text = _decompress(r.content)
        root = ET.fromstring(_strip_ns(xml_text))
        child_sitemaps = [loc.text.strip() for loc in root.iter("loc") if loc.text]

        all_urls = []
        for child in child_sitemaps:
            r = client.get(child)
            r.raise_for_status()
            xml_text = _decompress(r.content)
            root = ET.fromstring(_strip_ns(xml_text))
            all_urls.extend(loc.text.strip() for loc in root.iter("loc") if loc.text)

    product_urls = [u for u in all_urls if "/viewitems/" in u]
    category_urls = [u for u in all_urls if "/category/" in u]
    return product_urls, category_urls


def discover_blog_urls() -> list[str]:
    with _client() as client:
        r = client.get(BLOG_RSS)
        r.raise_for_status()
        root = ET.fromstring(_strip_ns(r.text))
        urls = []
        for item in root.iter("item"):
            link = item.find("link")
            if link is not None and link.text:
                urls.append(link.text.strip())
        return urls


def discover_main_site_urls() -> list[str]:
    valid = []
    with _client() as client:
        for path in MAIN_SITE_CANDIDATE_PATHS:
            url = MAIN_SITE_BASE + path
            try:
                r = client.get(url)
                if r.status_code == 200 and len(r.text) > 500:
                    valid.append(url)
            except Exception:
                pass
    return valid
