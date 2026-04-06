"""File writing, email delivery, link checking, and seen-URL deduplication."""

import os
import re
import json
import logging
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from src.config import DIGESTS_DIR, DOCS_DIR, SEEN_URLS_FILE, SEEN_URLS_RETENTION_DAYS
from src.render import render_html, update_archive

log = logging.getLogger(__name__)


# ── File output ────────────────────────────────────────────────────────────────

def write_markdown(today_str, content):
    DIGESTS_DIR.mkdir(exist_ok=True)
    path = DIGESTS_DIR / f"{today_str}.md"
    path.write_text(f"# AI Digest — {today_str}\n\n{content}", encoding="utf-8")
    log.info(f"Wrote {path}")


def write_html(today_str, md_content, cost=None):
    DOCS_DIR.mkdir(exist_ok=True)
    html = render_html(md_content, today_str, cost=cost)
    index_path = DOCS_DIR / "index.html"
    index_path.write_text(html, encoding="utf-8")
    log.info(f"Wrote {index_path}")
    dated_path = DOCS_DIR / f"{today_str}.html"
    dated_path.write_text(html, encoding="utf-8")
    log.info(f"Wrote {dated_path}")
    update_archive(today_str)
    log.info("Updated archive")


# ── Email delivery ─────────────────────────────────────────────────────────────

def send_email(today_str, html_content):
    """Send the digest via Gmail SMTP. Requires GMAIL_USER and GMAIL_APP_PASSWORD env vars."""
    gmail_user   = os.environ.get("GMAIL_USER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password or not gmail_user:
        log.warning("GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping email")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Digest — {today_str}"
    msg["From"]    = gmail_user
    msg["To"]      = gmail_user
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(gmail_user, app_password)
            smtp.sendmail(gmail_user, gmail_user, msg.as_string())
        log.info(f"Email sent to {gmail_user}")
    except Exception as e:
        log.error(f"Failed to send email: {e}")


# ── Link checker ───────────────────────────────────────────────────────────────

def check_links(md_text):
    """HEAD-request every markdown link in the digest and log non-200 responses."""
    urls = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', md_text)
    if not urls:
        return []

    dead = []
    for anchor, url in urls:
        try:
            req = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"})
            with urlopen(req, timeout=8) as resp:
                status = resp.status
        except HTTPError as e:
            status = e.code
        except URLError as e:
            status = str(e.reason)
        except Exception as e:
            status = str(e)

        ok = str(status) in ("200", "301", "302", "403")  # 403 often blocks HEAD but page exists
        if ok:
            log.info(f"  Link OK [{status}]: {url}")
        else:
            log.warning(f"Possible dead link [{status}]: {anchor} → {url}")
            dead.append((status, anchor, url))

    if dead:
        log.warning(f"{len(dead)} potentially dead link(s) found")
    else:
        log.info("All links OK")
    return dead


# ── Seen-URL deduplication ─────────────────────────────────────────────────────

def load_seen_urls():
    """Load {url: date_str} map, dropping entries older than the retention window."""
    if not SEEN_URLS_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_URLS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cutoff = (date.today() - timedelta(days=SEEN_URLS_RETENTION_DAYS)).isoformat()
    return {url: d for url, d in data.items() if d >= cutoff}


def save_seen_urls(seen: dict, new_urls: list):
    """Add today's URLs to the seen map and persist to disk."""
    today = date.today().isoformat()
    seen.update({url: today for url in new_urls})
    SEEN_URLS_FILE.write_text(json.dumps(seen, indent=2), encoding="utf-8")
