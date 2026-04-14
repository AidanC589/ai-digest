#!/usr/bin/env python3
"""Health check for all configured RSS sources."""

import sys
import yaml
import feedparser
from datetime import datetime, timezone, timedelta
from src.config import SOURCES_FILE, MAX_ARTICLE_AGE_DAYS

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"}
RECENT_DAYS = 7  # warn if newest article is older than this


def check_sources():
    with open(SOURCES_FILE) as f:
        sources = yaml.safe_load(f)["feeds"]

    results = []
    for src in sources:
        name = src["name"]
        url  = src["url"]
        result = {"name": name, "url": url}

        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            status = getattr(feed, "status", None)
            result["status"] = status
            result["entries"] = len(feed.entries)
            result["bozo"] = feed.bozo

            if feed.bozo and not feed.entries:
                result["error"] = str(feed.bozo_exception)
            elif feed.entries:
                # Find newest entry date
                newest = None
                for e in feed.entries:
                    pub = e.get("published_parsed") or e.get("updated_parsed")
                    if pub:
                        dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        if newest is None or dt > newest:
                            newest = dt
                result["newest"] = newest
            else:
                result["error"] = "No entries returned"

        except Exception as e:
            result["status"] = None
            result["entries"] = 0
            result["error"] = str(e)

        results.append(result)

    # ── Report ─────────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    cutoff_recent = now - timedelta(days=RECENT_DAYS)
    cutoff_age    = now - timedelta(days=MAX_ARTICLE_AGE_DAYS)

    ok = []
    warnings = []
    failures = []

    for r in results:
        if r.get("error") or r.get("entries", 0) == 0:
            failures.append(r)
        elif r.get("newest") and r["newest"] < cutoff_recent:
            warnings.append(r)
        else:
            ok.append(r)

    print(f"\n{'='*60}")
    print(f"  Source health check — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    if ok:
        print(f"OK ({len(ok)})")
        for r in ok:
            age = f"newest {(now - r['newest']).days}d ago" if r.get("newest") else "no dates"
            print(f"  {r['entries']:>3} entries  {age:<20}  {r['name']}")

    if warnings:
        print(f"\nWARN ({len(warnings)}) — no articles in last {RECENT_DAYS} days")
        for r in warnings:
            age = f"newest {(now - r['newest']).days}d ago" if r.get("newest") else "no dates"
            print(f"  {r['entries']:>3} entries  {age:<20}  {r['name']}")
            print(f"    {r['url']}")

    if failures:
        print(f"\nFAIL ({len(failures)})")
        for r in failures:
            status = r.get("status", "N/A")
            print(f"  status={status}  {r['name']}")
            print(f"    {r['url']}")
            if r.get("error"):
                print(f"    {r['error'][:120]}")

    print()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    check_sources()
