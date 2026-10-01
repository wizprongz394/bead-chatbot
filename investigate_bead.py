"""
Bead Electronics feasibility investigation — v4.
Handles both gzip AND zip archives for the catalog sitemap.
Also iterates RSS more thoroughly and fetches 5 blog posts.
"""

import gzip
import io
import json
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "BeadResearchBot/0.1 (+internal research; respects robots.txt)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 30.0
OUTPUT = Path("DATA_FEASIBILITY.md")

client = httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)


def safe_get(url):
    try:
        return client.get(url)
    except Exception as e:
        print(f"[ERR] {url} -> {e}")
        return None


def decompress_any(resp):
    """
    Handle three cases:
      1. Raw gzip (magic: 1f 8b)
      2. ZIP archive (magic: 50 4b 03 04)
      3. Plain text (no magic)
    Returns decoded string or an error marker string.
    """
    if resp is None:
        return None

    content = resp.content

    # Case 1: gzip
    if content[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(content).decode("utf-8", errors="replace")
        except Exception as e:
            return f"[gzip_error: {e}]"

    # Case 2: ZIP
    if content[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names = zf.namelist()
                if not names:
                    return "[zip_error: empty archive]"
                # Take the first .xml file, or the first file if none end in .xml
                xml_names = [n for n in names if n.lower().endswith(".xml")]
                target = xml_names[0] if xml_names else names[0]
                return zf.read(target).decode("utf-8", errors="replace")
        except Exception as e:
            return f"[zip_error: {e}]"

    # Case 3: plain
    return resp.text


def strip_ns_full(xml_text):
    """Strip namespace declarations AND prefixes."""
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", xml_text)
    xml_text = re.sub(r"<(/?)(\w+):(\w+)", r"<\1\3", xml_text)
    xml_text = re.sub(r'\s(\w+):(\w+)=', r" \2=", xml_text)
    # Strip BOM if present
    if xml_text.startswith("\ufeff"):
        xml_text = xml_text[1:]
    return xml_text


def fetch_sitemap(url):
    """Fetch a sitemap URL, decompress gzip/zip, parse as XML, return all <loc> URLs."""
    r = safe_get(url)
    if not r or r.status_code != 200:
        return {"status": r.status_code if r else "error", "urls": [], "raw_preview": None}

    text = decompress_any(r)
    if text is None or text.startswith("[gzip_error") or text.startswith("[zip_error"):
        return {
            "status": "decompress_failed",
            "urls": [],
            "raw_preview": str(text)[:300],
        }

    raw_preview = text[:400]

    try:
        cleaned = strip_ns_full(text)
        root = ET.fromstring(cleaned)
    except Exception as e:
        return {
            "status": "parse_error",
            "error": str(e),
            "urls": [],
            "raw_preview": raw_preview,
        }

    urls = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "loc" and el.text:
            urls.append(el.text.strip())

    return {"status": 200, "urls": urls, "raw_preview": raw_preview}


def parse_rss(url):
    r = safe_get(url)
    if not r or r.status_code != 200:
        return {"status": r.status_code if r else "error", "items": []}

    try:
        cleaned = strip_ns_full(r.text)
        root = ET.fromstring(cleaned)
    except Exception as e:
        return {"status": "parse_error", "error": str(e), "items": []}

    items = []
    for item in root.iter("item"):
        link_el = item.find("link")
        title_el = item.find("title")
        pub_el = item.find("pubDate")
        if link_el is not None and link_el.text:
            items.append({
                "url": link_el.text.strip(),
                "title": title_el.text.strip() if title_el is not None and title_el.text else None,
                "pub_date": pub_el.text.strip() if pub_el is not None and pub_el.text else None,
            })

    return {"status": 200, "count": len(items), "items": items}


def inspect_page(url):
    """Deep inspection — works for both product and blog pages."""
    r = safe_get(url)
    if not r:
        return {"url": url, "status": "error"}

    soup = BeautifulSoup(r.text, "lxml")

    ld_json = []
    for block in soup.find_all("script", type="application/ld+json"):
        try:
            ld_json.append(json.loads(block.string or "{}"))
        except Exception:
            pass

    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if cells and any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)

    dl_pairs = []
    for dl in soup.find_all("dl"):
        dts = [dt.get_text(" ", strip=True) for dt in dl.find_all("dt")]
        dds = [dd.get_text(" ", strip=True) for dd in dl.find_all("dd")]
        if dts and dds:
            dl_pairs.extend(list(zip(dts, dds)))

    spec_pairs = []
    for el in soup.select("[class*=spec], [class*=attribute], [class*=property]"):
        text = el.get_text(" ", strip=True)
        if ":" in text and len(text) < 200:
            spec_pairs.append(text)
    spec_pairs = spec_pairs[:30]

    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)

    return {
        "url": url,
        "status": r.status_code,
        "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        "text_length": len(text),
        "text_preview": text[:1500],
        "ld_json_count": len(ld_json),
        "ld_json_sample": ld_json[:1],
        "tables_count": len(tables),
        "tables_sample": tables[:2],
        "dl_pairs_count": len(dl_pairs),
        "dl_pairs_sample": dl_pairs[:15],
        "spec_pairs_sample": spec_pairs,
    }


def main():
    findings = {"date": datetime.now(timezone.utc).isoformat()}

    print("[1] Catalog sitemap INDEX")
    idx = fetch_sitemap("https://catalog.beadelectronics.com/sitemapindex.google.xml")
    print(f"    status={idx['status']}  urls={len(idx['urls'])}")
    for u in idx["urls"]:
        print(f"      -> {u}")
    findings["catalog_index"] = idx

    print()
    print("[2] Fetching child sitemap (with zip/gzip auto-detect)")
    findings["catalog_children"] = []
    all_product_urls = []
    for child_url in idx["urls"][:5]:
        print(f"    -> {child_url}")
        result = fetch_sitemap(child_url)
        print(f"       status={result['status']}  urls={len(result['urls'])}")
        if result.get("error"):
            print(f"       error: {result['error']}")
        findings["catalog_children"].append({"url": child_url, **result})
        all_product_urls.extend(result["urls"])
        time.sleep(1)

    findings["all_product_urls_count"] = len(all_product_urls)
    findings["all_product_urls_sample"] = all_product_urls[:30]
    print(f"    TOTAL product URLs: {len(all_product_urls)}")

    # Inspect up to 5 real product pages
    print()
    print("[3] Inspecting up to 5 catalog product pages")
    findings["catalog_products"] = []
    for url in all_product_urls[:5]:
        print(f"    -> {url}")
        result = inspect_page(url)
        print(f"       status={result.get('status')}  "
              f"text={result.get('text_length')}  "
              f"tables={result.get('tables_count')}  "
              f"dl={result.get('dl_pairs_count')}  "
              f"ld_json={result.get('ld_json_count')}")
        findings["catalog_products"].append(result)
        time.sleep(1.5)

    print()
    print("[4] Blog RSS")
    rss = parse_rss("https://www.beadelectronics.com/blog/rss.xml")
    print(f"    status={rss['status']}  items={rss.get('count', 0)}")
    findings["blog_rss"] = rss

    print()
    print("[5] Blog posts — content depth")
    findings["blog_posts"] = []
    for item in rss.get("items", [])[:5]:
        url = item["url"]
        print(f"    -> {url}")
        page = inspect_page(url)
        findings["blog_posts"].append({
            "url": url,
            "title": item.get("title"),
            "text_length": page.get("text_length"),
            "text_preview": page.get("text_preview", "")[:800],
            "ld_json_count": page.get("ld_json_count", 0),
        })
        time.sleep(1)

    write_markdown(findings)
    print(f"\n✅ Wrote {OUTPUT.resolve()}")


def write_markdown(f):
    L = []
    L.append("# DATA FEASIBILITY — Bead Electronics AI Chatbot (v4)")
    L.append("")
    L.append(f"**Generated:** {f['date']}")
    L.append("")

    # 1. Catalog index
    L.append("## 1. Catalog Sitemap Index")
    L.append("")
    idx = f["catalog_index"]
    L.append(f"- Status: `{idx['status']}`")
    L.append(f"- URLs: **{len(idx['urls'])}**")
    for u in idx["urls"]:
        L.append(f"  - `{u}`")
    if idx.get("error"):
        L.append(f"- Error: `{idx['error']}`")
    L.append("")

    # 2. Child sitemaps
    L.append("## 2. Child Sitemaps")
    L.append("")
    for ch in f["catalog_children"]:
        L.append(f"### `{ch['url']}`")
        L.append(f"- Status: `{ch['status']}`")
        L.append(f"- URL count: **{len(ch['urls'])}**")
        if ch.get("error"):
            L.append(f"- Error: `{ch['error']}`")
        L.append("")

    L.append(f"**TOTAL product URLs discovered: {f['all_product_urls_count']}**")
    L.append("")

    L.append("### Sample product URLs (first 30)")
    L.append("")
    for u in f["all_product_urls_sample"]:
        L.append(f"- `{u}`")
    L.append("")

    # 3. Product pages
    L.append("## 3. Catalog Product Page Structure")
    L.append("")
    if not f["catalog_products"]:
        L.append("_No product URLs available to inspect._")
        L.append("")
    for p in f["catalog_products"]:
        L.append(f"### `{p.get('url')}`")
        L.append(f"- Status: `{p.get('status')}`")
        L.append(f"- Title: {p.get('title')}")
        L.append(f"- Text length: {p.get('text_length')}")
        L.append(f"- LD+JSON blocks: {p.get('ld_json_count')}")
        L.append(f"- Tables: {p.get('tables_count')}")
        L.append(f"- DL pairs: {p.get('dl_pairs_count')}")
        L.append("")
        if p.get("tables_sample"):
            L.append("**Table sample:**")
            L.append("```")
            for row in p["tables_sample"][0][:10]:
                L.append(" | ".join(row))
            L.append("```")
            L.append("")
        if p.get("dl_pairs_sample"):
            L.append("**DL pairs sample:**")
            L.append("```")
            for k, v in p["dl_pairs_sample"]:
                L.append(f"{k}: {v}")
            L.append("```")
            L.append("")
        if p.get("spec_pairs_sample"):
            L.append("**Spec-like class matches:**")
            L.append("```")
            for s in p["spec_pairs_sample"][:15]:
                L.append(s)
            L.append("```")
            L.append("")
        if p.get("text_preview"):
            L.append("**Text preview:**")
            L.append("```")
            L.append(p["text_preview"][:800])
            L.append("```")
            L.append("")

    # 4. Blog RSS
    L.append("## 4. Blog RSS Feed")
    L.append("")
    rss = f["blog_rss"]
    L.append(f"- Status: `{rss['status']}`")
    L.append(f"- Items: **{rss.get('count', 0)}**")
    L.append("")
    for item in rss.get("items", []):
        L.append(f"- [{item.get('title')}]({item['url']})")
    L.append("")

    # 5. Blog depth
    L.append("## 5. Blog Post Content Depth")
    L.append("")
    for post in f["blog_posts"]:
        L.append(f"### {post.get('title')}")
        L.append(f"- URL: `{post['url']}`")
        L.append(f"- Text length: **{post.get('text_length')}**")
        L.append(f"- LD+JSON blocks: {post.get('ld_json_count', 0)}")
        L.append("")

    # 6. Verdict
    L.append("## 6. Verdict")
    L.append("")
    L.append("### Content sources (for RAG)")
    L.append(f"- Blog posts available: **{rss.get('count', 0)}**")
    L.append("- Blog post average text length: [see section 5]")
    L.append("")
    L.append("### Catalog")
    L.append(f"- Product URLs in sitemap: **{f['all_product_urls_count']}**")
    L.append("- Product page structure: [see section 3]")
    L.append("- Spec data extractable: [see section 3]")
    L.append("")
    L.append("### MVP decision")
    L.append("- [ ] Full MVP — catalog pages have clean HTML spec data")
    L.append("- [ ] Reduced MVP — no catalog search, RAG + routing only")
    L.append("- [ ] Hybrid MVP — partial catalog data, limited search")
    L.append("")

    OUTPUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()