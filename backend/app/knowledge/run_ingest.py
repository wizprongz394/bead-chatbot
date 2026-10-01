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
from app.knowledge.store import write_products, write_chunks, build_vector_store

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

    print("\n       writing vector store...")
    build_vector_store(all_chunks, embeddings)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  products:  {len(all_products)}")
    print(f"  chunks:    {len(all_chunks)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
