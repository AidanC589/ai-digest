"""RSS feed fetching and article text extraction."""

import re
import logging
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import yaml
import feedparser
import trafilatura

from src.config import (
    SOURCES_FILE, MAX_FEED_ITEMS, MAX_WORDS_PER_ARTICLE,
    MIN_SUMMARY_WORDS, MAX_ARTICLE_AGE_DAYS,
    FEED_MAX_RETRIES, FEED_RETRY_BASE_DELAY, FEED_RETRY_MAX_DELAY,
)
from src.net import safe_fetch_bytes, BlockedURL

log = logging.getLogger(__name__)
logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

SKIP_FULL_FETCH_DOMAINS = {"reddit.com", "www.reddit.com", "github.com", "arxiv.org"}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _retry_after(parsed):
    """Seconds from a Retry-After header, if the server sent one we can use."""
    raw = getattr(parsed, "headers", {}).get("retry-after")
    if not raw:
        return None
    try:
        return min(max(float(raw), 0.0), FEED_RETRY_MAX_DELAY)
    except ValueError:
        return None  # HTTP-date form — fall back to our own backoff


def _parse_feed_with_retry(url, headers, name):
    """feedparser.parse with exponential backoff on rate limits and transient 5xx.

    feedparser reports HTTP errors via .status instead of raising, so retryable
    responses are detected by status code rather than by exception.
    """
    delay = FEED_RETRY_BASE_DELAY
    last_exc = None

    for attempt in range(1, FEED_MAX_RETRIES + 1):
        parsed = None
        try:
            parsed = feedparser.parse(url, request_headers=headers)
        except Exception as e:
            last_exc = e

        if parsed is not None:
            status = getattr(parsed, "status", None)
            # Content is content — a 429 that still carried entries is a success.
            if status not in RETRYABLE_STATUSES or parsed.entries:
                return parsed
            delay = _retry_after(parsed) or delay

        if attempt == FEED_MAX_RETRIES:
            break

        reason = last_exc if parsed is None else f"HTTP {getattr(parsed, 'status', None)}"
        log.warning(f"  {name}: {reason} — retrying in {delay:.0f}s [{attempt}/{FEED_MAX_RETRIES}]")
        time.sleep(delay)
        delay = min(delay * 2, FEED_RETRY_MAX_DELAY)

    if parsed is None:
        raise last_exc
    log.warning(f"  {name}: gave up after {FEED_MAX_RETRIES} attempts (HTTP {getattr(parsed, 'status', None)})")
    return parsed


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
    """Fetch and extract clean body text from a URL using trafilatura.

    The download goes through src.net rather than trafilatura.fetch_url: the URL
    comes from a feed entry, so it is only as trustworthy as whoever submitted it,
    and whatever comes back gets published. trafilatura.extract takes the raw
    bytes and does its own charset detection.
    """
    try:
        downloaded = safe_fetch_bytes(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except BlockedURL as e:
        log.warning(f"Blocked article fetch: {e}")
        return None
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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"}
    try:
        parsed = _parse_feed_with_retry(url, headers, name)
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
