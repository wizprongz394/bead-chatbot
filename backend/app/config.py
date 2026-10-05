from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

APP_ROOT = Path(__file__).parent
DATA_DIR = APP_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

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
