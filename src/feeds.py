"""RSS feed fetching and article text extraction."""

import re
import base64
import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import yaml
import feedparser
import trafilatura

from src.config import (
    SOURCES_FILE, MAX_FEED_ITEMS, MAX_WORDS_PER_ARTICLE,
    MIN_SUMMARY_WORDS, MAX_ARTICLE_AGE_DAYS,
)

log = logging.getLogger(__name__)
logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

SKIP_FULL_FETCH_DOMAINS = {"reddit.com", "www.reddit.com", "github.com", "arxiv.org"}
REDDIT_DOMAINS = {"reddit.com", "www.reddit.com"}


def _reddit_auth_header():
    """Return Authorization header for Reddit basic auth, or None if creds not set."""
    user = os.environ.get("REDDIT_USERNAME")
    pwd  = os.environ.get("REDDIT_PASSWORD")
    if user and pwd:
        token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
    return {}


def load_sources():
    with open(SOURCES_FILE) as f:
        return yaml.safe_load(f)["feeds"]


def word_count(text):
    return len(text.split())


def truncate_to_words(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " […]"


def fetch_article_text(url):
    """Fetch and extract clean body text from a URL using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None


def fetch_feed(feed_cfg):
    """Fetch a single RSS feed and return a list of article dicts."""
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    is_changelog = feed_cfg.get("type") == "changelog"
    item_cap = 5 if is_changelog else MAX_FEED_ITEMS

    log.info(f"Fetching feed: {name}{' [changelog]' if is_changelog else ''}")
    feed_domain = urlparse(url).netloc
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"}
    if feed_domain in REDDIT_DOMAINS:
        headers.update(_reddit_auth_header())
    try:
        parsed = feedparser.parse(url, request_headers=headers)
        if parsed.bozo and not parsed.entries:
            log.warning(f"Feed parse error for {name}: {parsed.bozo_exception}")
            return []
        if parsed.bozo:
            log.warning(f"Feed {name} has minor parse issues but {len(parsed.entries)} entries — continuing")
    except Exception as e:
        log.warning(f"Failed to fetch feed {name}: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    articles = []

    for entry in parsed.entries[:item_cap * 3]:
        title = entry.get("title", "Untitled").strip()
        link  = entry.get("link", "")

        # Age filter
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub:
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                log.info(f"  Skipping old article ({pub_dt.date()}): '{title}'")
                continue

        # Extract summary from feed
        summary = ""
        if hasattr(entry, "summary"):
            summary = re.sub(r"<[^>]+>", " ", entry.summary)
            summary = re.sub(r"\s+", " ", summary).strip()

        # Full-text fetch if summary too short (skip changelogs and blocked domains)
        domain = urlparse(link).netloc if link else ""
        if (not is_changelog
                and word_count(summary) < MIN_SUMMARY_WORDS
                and link
                and domain not in SKIP_FULL_FETCH_DOMAINS):
            log.info(f"  Short summary for '{title}', fetching full text…")
            full_text = fetch_article_text(link)
            if full_text and word_count(full_text) > word_count(summary):
                summary = full_text

        if not summary:
            log.info(f"  No content for '{title}', skipping")
            continue

        summary = truncate_to_words(summary, MAX_WORDS_PER_ARTICLE)
        articles.append({
            "title":  title,
            "url":    link,
            "text":   summary,
            "source": name,
            "type":   "changelog" if is_changelog else "article",
        })

        if len(articles) >= item_cap:
            break

    log.info(f"  → {len(articles)} articles from {name}")
    return articles
