"""Star-velocity tracking for the GitHub Trending section.

The model writes only the description for each repo; every number in the rendered
line is produced here from the scrape plus `trending_history.json`, so the format
is fixed and the figures are never transcribed by hand.
"""

import json
import logging
import re
from datetime import date, timedelta

from src.config import (
    TRENDING_HISTORY_FILE,
    TRENDING_HISTORY_RETENTION_DAYS,
    VELOCITY_MIN_OBSERVATIONS,
    VELOCITY_MIN_DAYS,
    VELOCITY_MIN_RATIO,
)

log = logging.getLogger(__name__)


# ── Persisted history ──────────────────────────────────────────────────────────
# Schema: {repo: {date_str: [stars_total, stars_today_or_null]}}

def load_history():
    """Load the star history, dropping entries older than the retention window."""
    if not TRENDING_HISTORY_FILE.exists():
        return {}
    try:
        data = json.loads(TRENDING_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"Could not read {TRENDING_HISTORY_FILE.name} ({e}) — starting empty")
        return {}

    cutoff = (date.today() - timedelta(days=TRENDING_HISTORY_RETENTION_DAYS)).isoformat()
    pruned = {}
    for repo, observations in data.items():
        kept = {d: v for d, v in observations.items() if d >= cutoff}
        if kept:
            pruned[repo] = kept
    return pruned


def save_history(history, trending_articles):
    """Record today's star counts and persist."""
    today = date.today().isoformat()
    for a in trending_articles:
        repo = a.get("repo")
        if not repo:
            continue
        history.setdefault(repo, {})[today] = [
            a.get("stars_total") or 0,
            a.get("stars_today"),
        ]
    TRENDING_HISTORY_FILE.write_text(
        json.dumps(history, indent=2, sort_keys=True), encoding="utf-8"
    )
    log.info(f"Recorded star counts for {len(trending_articles)} trending repo(s)")


# ── Metrics ────────────────────────────────────────────────────────────────────

def annotate(repo, stars_total, stars_today, history):
    """Build the stats prefix, e.g. '★4,436 · +298/day · ▲8.8x · day 5'.

    The acceleration baseline is total star growth over *elapsed calendar days*,
    not over days the repo happened to trend — the comparison we want is against
    the repo's true all-days average, so gaps in the observations are wanted here.
    """
    parts = []
    if stars_total:
        parts.append(f"★{stars_total:,}")
    if stars_today:
        parts.append(f"+{stars_today:,}/day")

    observations = history.get(repo) or {}
    if not observations:
        return " · ".join(parts)

    dates = sorted(observations)
    seen_count = len(dates) + 1  # today is not in history yet

    first_stars = observations[dates[0]][0]
    elapsed = (date.today() - date.fromisoformat(dates[0])).days

    if (
        stars_today
        and stars_total
        and first_stars
        and seen_count >= VELOCITY_MIN_OBSERVATIONS
        and elapsed >= VELOCITY_MIN_DAYS
    ):
        baseline = (stars_total - first_stars) / elapsed
        if baseline > 0:
            ratio = stars_today / baseline
            if ratio >= VELOCITY_MIN_RATIO:
                parts.append(f"▲{ratio:.1f}x")

    parts.append(f"day {seen_count}")
    return " · ".join(parts)


# ── Rewriting the digest section ───────────────────────────────────────────────

_SECTION_RE = re.compile(r"(^## GitHub Trending[^\n]*\n)(.*?)(?=^## |\Z)", re.M | re.S)

_BULLET_RE = re.compile(
    r"^[-*]\s+"
    r"(?:(?P<tag>\[(?:AI|Other)\])\s*)?"
    r"\*{0,2}\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)]+)\)\*{0,2}"
    r"(?P<rest>.*)$"
)

_REPO_FROM_URL = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)")

# Stats the model may still emit out of habit, stripped before the description.
_LEADING_STATS = re.compile(
    r"^(?:\s|·|\|"
    r"|★\s*[\d,]+|[\d,]+\s*★"
    r"|\(\+[^)]*\)|\+[\d,]+\s*(?:/day|today)?"
    r"|▲\s*[\d.]+x|day\s+\d+"
    r"|[—–-])+",
    re.I,
)


def _repo_key(url):
    m = _REPO_FROM_URL.match(url.strip())
    return m.group(1).lower() if m else None


def _description(rest):
    """Pull the prose out of whatever the model put after the repo link."""
    text = _LEADING_STATS.sub("", rest).strip()
    return text or None


def rewrite_trending_section(digest_md, trending_articles, history):
    """Replace the model's trending bullets with deterministically rendered ones.

    Never fatal: any failure leaves the digest exactly as the model wrote it.
    """
    try:
        return _rewrite(digest_md, trending_articles, history)
    except Exception as e:
        log.warning(f"Could not annotate GitHub Trending ({e}) — leaving section as written")
        return digest_md


def _rewrite(digest_md, trending_articles, history):
    match = _SECTION_RE.search(digest_md)
    if not match:
        log.info("No GitHub Trending section in digest — nothing to annotate")
        return digest_md

    parsed = {}     # repo_key -> (tag, description, raw_line)
    unmatched = []  # lines with no usable repo link — passed through untouched
    for line in match.group(2).split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        m = _BULLET_RE.match(stripped)
        key = _repo_key(m.group("url")) if m else None
        if key:
            parsed[key] = (m.group("tag") or "", _description(m.group("rest")), stripped)
        else:
            unmatched.append(stripped)

    lines = []
    for a in trending_articles:
        repo = a.get("repo")
        key = repo.lower() if repo else None
        if not key or key not in parsed:
            continue
        tag, desc, _ = parsed.pop(key)
        desc = desc or a.get("description") or "No description."
        stats = annotate(repo, a.get("stars_total") or 0, a.get("stars_today"), history)
        prefix = f"{tag} " if tag else ""
        stats = f" {stats}" if stats else ""
        lines.append(f"- {prefix}**[{repo}]({a['url']})**{stats} — {desc}")

    if not lines:
        log.warning("No trending bullets matched today's scrape — leaving section as written")
        return digest_md

    # Bullets the model wrote for repos not in today's scrape keep their own line.
    leftovers = [raw for _, _, raw in parsed.values()]
    if leftovers:
        log.info(f"{len(leftovers)} trending bullet(s) not in today's scrape — passed through")

    log.info(f"Annotated {len(lines)} trending repo(s)")
    body = "\n".join(lines + leftovers + unmatched)
    return digest_md[: match.start(2)] + body + "\n\n" + digest_md[match.end(2):]
