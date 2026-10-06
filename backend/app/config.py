"""Configuration and paths.

The .env file is loaded once at import time. Paths are defined but not
created here — on Vercel the filesystem is read-only, so any mkdir
call at import time crashes the function. Code that needs to write
(only the ingestion pipeline) creates its own directories.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env relative to backend/ (works both locally and in containers)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=False)

APP_ROOT = Path(__file__).parent
DATA_DIR = APP_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

# Best-effort directory creation. On Vercel this will be a no-op.
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Read-only filesystem (production). Directories already exist
    # because they're bundled with the deployment.
    pass

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
