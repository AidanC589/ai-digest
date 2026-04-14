"""Scrape GitHub Trending page and return structured article dicts."""

import logging
import re
import urllib.request
from html.parser import HTMLParser

log = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_REPOS = 15


class _TrendingParser(HTMLParser):
    """State-machine HTML parser that extracts repo cards from github.com/trending."""

    def __init__(self):
        super().__init__()
        self.repos = []
        self._in_article = False
        self._depth = 0          # nesting depth inside the article element
        self._article_depth = 0  # depth at which article started
        self._buf = ""           # text buffer for current leaf element
        self._tag_stack = []
        # per-repo state
        self._repo = {}
        self._capture = None     # which field we're currently capturing

    # ── helpers ────────────────────────────────────────────────────────────────

    def _start_repo(self):
        self._in_article = True
        self._article_depth = self._depth
        self._repo = {}
        self._capture = None

    def _end_repo(self):
        r = self._repo
        if r.get("name") and r.get("url"):
            self.repos.append(r)
        self._in_article = False
        self._repo = {}
        self._capture = None

    # ── parser callbacks ───────────────────────────────────────────────────────

    def handle_starttag(self, tag, attrs):
        self._depth += 1
        attrs = dict(attrs)
        classes = attrs.get("class", "")

        if tag == "article" and "Box-row" in classes:
            self._start_repo()
            return

        if not self._in_article:
            return

        # Repo name link: <h2 class="h3 …"><a href="/owner/repo">
        if tag == "h2" and "h3" in classes:
            self._capture = None  # wait for the <a> inside
        if tag == "a" and self._capture is None and "name" not in self._repo:
            href = attrs.get("href", "")
            # href is "/owner/repo" (two segments)
            if href.count("/") == 2:
                self._repo["url"] = f"https://github.com{href}"
                self._repo["name"] = href.lstrip("/")
                self._buf = ""
                self._capture = None  # we use href, not text

        # Description: <p class="col-9 …">
        if tag == "p" and "col-9" in classes:
            self._buf = ""
            self._capture = "description"

        # Language: <span itemprop="programmingLanguage">
        if tag == "span" and attrs.get("itemprop") == "programmingLanguage":
            self._buf = ""
            self._capture = "language"

        # Stars today: last <span class="d-inline-block float-sm-right">
        if tag == "span" and "float-sm-right" in classes:
            self._buf = ""
            self._capture = "stars_today"

        # Total stars link: href="/owner/repo/stargazers"
        if tag == "a":
            href = attrs.get("href", "")
            if href.endswith("/stargazers"):
                self._buf = ""
                self._capture = "stars_total"

    def handle_endtag(self, tag):
        self._depth -= 1

        if self._in_article and self._depth < self._article_depth:
            self._end_repo()
            return

        if not self._in_article:
            return

        if self._capture and tag in ("p", "span", "a"):
            value = re.sub(r"\s+", " ", self._buf).strip()
            if value:
                self._repo[self._capture] = value
            self._capture = None
            self._buf = ""

    def handle_data(self, data):
        if self._in_article and self._capture is not None:
            self._buf += data


def _parse_star_count(text):
    """Normalise '1,234' or '1.2k' style star counts to an int."""
    text = text.lower().replace(",", "").strip()
    if text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def fetch_github_trending() -> list[dict]:
    """Scrape github.com/trending and return a list of article dicts."""
    try:
        req = urllib.request.Request(TRENDING_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"Failed to fetch GitHub Trending: {e}")
        return []

    parser = _TrendingParser()
    try:
        parser.feed(html)
    except Exception as e:
        log.warning(f"Failed to parse GitHub Trending HTML: {e}")
        return []

    repos = parser.repos[:MAX_REPOS]
    if not repos:
        log.warning("GitHub Trending: no repos parsed from page")
        return []

    articles = []
    for r in repos:
        stars_total = _parse_star_count(r.get("stars_total", "0"))
        stars_today_raw = r.get("stars_today", "")
        # strip trailing " stars today" / " star today"
        stars_today = re.sub(r"\s*stars?\s*today", "", stars_today_raw, flags=re.I).strip()

        parts = []
        if r.get("language"):
            parts.append(r["language"])
        if stars_total:
            star_str = f"{stars_total:,}★"
            if stars_today:
                star_str += f" (+{stars_today} today)"
            parts.append(star_str)

        prefix = " · ".join(parts)
        desc = r.get("description", "").strip()
        text = f"{prefix} — {desc}" if prefix and desc else (prefix or desc or "No description.")

        articles.append({
            "title":  r["name"],
            "url":    r["url"],
            "text":   text,
            "source": "GitHub Trending",
            "type":   "trending",
        })

    log.info(f"  → {len(articles)} articles from GitHub Trending")
    return articles
