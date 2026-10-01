# setup_backend.ps1
# Creates the backend file tree for the Bead chatbot ingestion pipeline.

$root = "C:\Projects\Bead-chatbot\backend"
Set-Location $root

# ---------- requirements.txt ----------
@'
httpx==0.28.1
beautifulsoup4==4.15.0
lxml==6.1.3
sentence-transformers==3.0.1
chromadb==0.5.0
pydantic==2.9.0
pyyaml==6.0.1
'@ | Out-File -FilePath requirements.txt -Encoding utf8

# ---------- app\config.py ----------
@'
from pathlib import Path

APP_ROOT = Path(__file__).parent
DATA_DIR = APP_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "BeadChatbotBot/0.1 (+internal; respects robots.txt)"
REQUEST_DELAY_SECONDS = 1.5

CATALOG_SITEMAP_INDEX = "https://catalog.beadelectronics.com/sitemapindex.google.xml"
BLOG_RSS = "https://www.beadelectronics.com/blog/rss.xml"

MAIN_SITE_BASE = "https://www.beadelectronics.com"
MAIN_SITE_CANDIDATE_PATHS = [
    "/products/hollow-contact-pins",
    "/products/solid-wire-contact-pins",
    "/products/contact-pin-assemblies",
    "/applications/connector",
    "/applications/mechanical",
    "/applications/overmolded",
    "/applications/pcb",
    "/markets/automotive",
    "/markets/heavy-equipment",
    "/markets/aerospace-defense",
    "/markets/communication",
    "/markets/industrial",
    "/markets/lighting",
    "/markets/medical",
    "/company/about-us",
    "/company/contact-us",
    "/resources/downloads",
    "/resources/videos",
]
'@ | Out-File -FilePath app\config.py -Encoding utf8

# ---------- app\knowledge\sources.py ----------
@'
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
'@ | Out-File -FilePath app\knowledge\sources.py -Encoding utf8

# ---------- app\knowledge\crawl.py ----------
@'
"""Respectful crawler. Preserves raw HTML, returns parsed soup."""

import hashlib
import time

import httpx
from bs4 import BeautifulSoup

from app.config import USER_AGENT, REQUEST_DELAY_SECONDS, RAW_DIR


def url_to_filename(url: str) -> str:
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe)
    return f"{safe[:80]}__{h}.html"


def fetch_and_save(url: str):
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            if r.status_code != 200:
                print(f"  [skip] {url} -> {r.status_code}")
                return None
            html = r.text
    except Exception as e:
        print(f"  [err] {url} -> {e}")
        return None

    raw_path = RAW_DIR / url_to_filename(url)
    raw_path.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "lxml")
    return html, soup


def crawl_all(urls):
    results = []
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url}")
        fetched = fetch_and_save(url)
        if fetched:
            html, soup = fetched
            results.append((url, html, soup))
        time.sleep(REQUEST_DELAY_SECONDS)
    return results
'@ | Out-File -FilePath app\knowledge\crawl.py -Encoding utf8

# ---------- app\knowledge\extract.py ----------
@'
"""Extractors: product tables from viewitems pages, article text from blog/category."""

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


def _normalize_header(raw: str):
    return PRODUCT_HEADER_MAP.get(raw.strip().lower())


def _clean_cell(text: str) -> str:
    return text.replace("N/A", "").strip()


def extract_product_table(soup: BeautifulSoup):
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


def extract_article_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
        tag.decompose()
    for cls in ["breadcrumb", "breadcrumbs", "sidebar", "menu", "navigation"]:
        for el in soup.select(f".{cls}, [class*={cls}]"):
            el.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)
'@ | Out-File -FilePath app\knowledge\extract.py -Encoding utf8

# ---------- app\knowledge\chunk.py ----------
@'
"""Simple character-window chunker with metadata."""

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source_url: str
    source_title: str
    content_type: str
    chunk_index: int
    total_chunks: int


def chunk_text(
    text: str,
    source_url: str,
    source_title: str,
    content_type: str,
    target_chars: int = 1500,
    overlap_chars: int = 200,
):
    if not text:
        return []
    chunks = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + target_chars, n)
        if end < n:
            nl = text.rfind("\n", start, end)
            if nl > start + target_chars // 2:
                end = nl
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                text=chunk_text,
                source_url=source_url,
                source_title=source_title,
                content_type=content_type,
                chunk_index=idx,
                total_chunks=0,
            ))
            idx += 1
        start = end - overlap_chars if end < n else n

    for c in chunks:
        c.total_chunks = len(chunks)
    return chunks
'@ | Out-File -FilePath app\knowledge\chunk.py -Encoding utf8

# ---------- app\knowledge\embed.py ----------
@'
"""Local embedding model wrapper."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_texts(texts):
    model = get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [v.tolist() for v in vectors]
'@ | Out-File -FilePath app\knowledge\embed.py -Encoding utf8

# ---------- app\knowledge\store.py ----------
@'
"""Write products and chunks to disk + Chroma."""

import json

import chromadb

from app.config import DATA_DIR, CHROMA_DIR


def write_products(products):
    path = DATA_DIR / "products.json"
    path.write_text(json.dumps(products, indent=2), encoding="utf-8")
    return path


def write_chunks(chunks):
    path = DATA_DIR / "content_chunks.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({
                "text": c.text,
                "source_url": c.source_url,
                "source_title": c.source_title,
                "content_type": c.content_type,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
            }) + "\n")
    return path


def build_chroma(chunks, embeddings):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection("bead_content")
    except Exception:
        pass
    collection = client.create_collection("bead_content")

    ids = [f"{c.source_url}#{c.chunk_index}" for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [{
        "source_url": c.source_url,
        "source_title": c.source_title,
        "content_type": c.content_type,
        "chunk_index": c.chunk_index,
    } for c in chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
'@ | Out-File -FilePath app\knowledge\store.py -Encoding utf8

# ---------- app\knowledge\run_ingest.py ----------
@'
"""Entry point for Day 1 Hour 2-5. Run: python -m app.knowledge.run_ingest"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.knowledge.sources import (
    discover_catalog_urls,
    discover_blog_urls,
    discover_main_site_urls,
)
from app.knowledge.crawl import crawl_all
from app.knowledge.extract import extract_product_table, extract_article_text
from app.knowledge.chunk import chunk_text
from app.knowledge.embed import embed_texts
from app.knowledge.store import write_products, write_chunks, build_chroma


def main():
    print("=" * 60)
    print("BEAD INGESTION PIPELINE")
    print("=" * 60)

    print("\n[1/6] Discovering catalog URLs...")
    product_urls, category_urls = discover_catalog_urls()
    print(f"       product pages: {len(product_urls)}")
    print(f"       category pages: {len(category_urls)}")

    print("\n[2/6] Discovering blog URLs...")
    blog_urls = discover_blog_urls()
    print(f"       blog posts: {len(blog_urls)}")

    print("\n[3/6] Probing main-site URLs...")
    main_urls = discover_main_site_urls()
    print(f"       valid main-site pages: {len(main_urls)}")

    print("\n[4/6] Crawling all pages...")
    print("       (product + category)")
    product_pages = crawl_all(product_urls + category_urls)
    print("       (blog + main site)")
    content_pages = crawl_all(blog_urls + main_urls)

    print("\n[5/6] Extracting...")
    all_products = []
    for url, _html, soup in product_pages:
        if "/viewitems/" in url:
            rows = extract_product_table(soup)
            for row in rows:
                row["_source_url"] = url
                all_products.append(row)
            print(f"       {url}: {len(rows)} products")

    print(f"\n       TOTAL PRODUCTS: {len(all_products)}")
    products_path = write_products(all_products)
    print(f"       wrote {products_path}")

    print("\n[6/6] Chunking + embedding content pages...")
    all_chunks = []
    for url, _html, soup in content_pages:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        text = extract_article_text(soup)
        if len(text) < 200:
            continue
        ctype = "blog" if "/blog/" in url else "main_site"
        chunks = chunk_text(text, url, title, ctype)
        all_chunks.extend(chunks)
        print(f"       {url}: {len(chunks)} chunks")

    for url, _html, soup in product_pages:
        if "/category/" in url:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url
            text = extract_article_text(soup)
            if len(text) < 200:
                continue
            chunks = chunk_text(text, url, title, "category")
            all_chunks.extend(chunks)
            print(f"       {url}: {len(chunks)} chunks (category)")

    print(f"\n       TOTAL CHUNKS: {len(all_chunks)}")
    chunks_path = write_chunks(all_chunks)
    print(f"       wrote {chunks_path}")

    print("\n       embedding...")
    embeddings = embed_texts([c.text for c in all_chunks])
    print(f"       embedded {len(embeddings)} chunks")

    print("\n       writing to Chroma...")
    build_chroma(all_chunks, embeddings)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  products:  {len(all_products)}")
    print(f"  chunks:    {len(all_chunks)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
'@ | Out-File -FilePath app\knowledge\run_ingest.py -Encoding utf8

Write-Host ""
Write-Host "✅ All files created." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. cd C:\Projects\Bead-chatbot\backend"
Write-Host "  2. pip install -r requirements.txt"
Write-Host "  3. python -m app.knowledge.run_ingest"