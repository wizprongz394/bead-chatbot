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
