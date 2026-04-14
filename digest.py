#!/usr/bin/env python3
"""AI Digest — entry point."""

import os
import sys
import logging

from src.config import SEEN_URLS_RETENTION_DAYS
from src.feeds import load_sources, fetch_feed
from src.trending import fetch_github_trending
from src.llm import call_anthropic
from src.render import render_html
from src.output import (
    write_markdown, write_html, send_email,
    check_links, load_seen_urls, save_seen_urls,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    from datetime import date
    today_str  = date.today().isoformat()
    seen_urls  = load_seen_urls()

    # Fetch
    sources      = load_sources()
    all_articles = []
    for feed_cfg in sources:
        all_articles.extend(fetch_feed(feed_cfg))

    if not all_articles:
        log.error("No articles fetched — nothing to summarise")
        sys.exit(1)

    # Deduplicate
    fresh   = [a for a in all_articles if a["url"] not in seen_urls]
    skipped = len(all_articles) - len(fresh)
    if skipped:
        log.info(f"Deduped {skipped} URL(s) already seen in the last {SEEN_URLS_RETENTION_DAYS} days")
    all_articles = fresh

    if not all_articles:
        log.error("All articles already seen — nothing new to summarise")
        sys.exit(1)

    # Append trending repos after dedup — same repo can trend on multiple days
    all_articles.extend(fetch_github_trending())

    log.info(f"Total articles collected: {len(all_articles)}")

    # Summarise
    log.info("Calling Anthropic API…")
    digest_md, run_cost = call_anthropic(all_articles)

    # Validate
    log.info("Checking links in digest…")
    check_links(digest_md)

    # Publish
    write_markdown(today_str, digest_md)
    write_html(today_str, digest_md, cost=run_cost)
    send_email(today_str, render_html(digest_md, today_str, cost=run_cost))

    # Persist seen URLs
    save_seen_urls(seen_urls, [a["url"] for a in all_articles if a.get("type") != "trending"])
    log.info(f"Saved {len(all_articles)} URLs to seen list")

    log.info("Done.")


if __name__ == "__main__":
    main()
