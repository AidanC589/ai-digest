# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

AI Digest is an automated daily news aggregation pipeline that fetches RSS feeds, extracts article text, sends everything to Claude in one API call, and publishes the resulting digest as HTML to Cloudflare Pages and email.

Live site: https://ai-digest-elw.pages.dev

## Commands

```bash
# Run the full digest (requires ANTHROPIC_API_KEY)
python digest.py

# Render a local preview without calling Claude (opens docs/index.html)
python preview.py

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies (Wrangler for deployment)
npm install
```

There are no automated tests. Use `python preview.py` to verify HTML rendering changes without an API call.

## Architecture

Data flows through four stages:

1. **Fetch** (`src/feeds.py`) — Parse `sources.yml`, fetch RSS for each source, skip articles older than 14 days, extract full text via Trafilatura if summary < 100 words, truncate to 600 words/article.

2. **Deduplicate** (`src/output.py`) — Filter URLs already in `seen_urls.json` (14-day rolling window). Abort if nothing new.

3. **Summarize** (`src/llm.py`) — Build an XML message from all articles, estimate tokens with tiktoken against a 35,000-token budget (trim if over), then make a single Claude API call. The system prompt in `src/config.py` specifies five required sections and editorial rules.

4. **Publish** (`src/output.py`, `src/render.py`) — Validate links (HEAD requests), write Markdown to `digests/YYYY-MM-DD.md`, render to `docs/index.html`, update `docs/archive.html`, send email if `GMAIL_APP_PASSWORD` is set.

**Key design constraint:** Everything goes to Claude in a single API call — no streaming, no chunking — to preserve coherence and leverage prompt caching.

## Configuration

- **`sources.yml`** — Feed sources. Sources with `type: changelog` bypass editorial filtering and are always included.
- **`src/config.py`** — All numeric constants (`TOKEN_BUDGET`, `MAX_WORDS_PER_ARTICLE`, `MAX_FEED_ITEMS`, `MAX_ARTICLE_AGE_DAYS`, etc.), the Claude model name, and the full system prompt.
- **`seen_urls.json`** — Persisted URL dedup state (git-tracked, committed by GitHub Actions).

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `GMAIL_USER` | No | Gmail address to send/receive the digest |
| `GMAIL_APP_PASSWORD` | No | Email delivery via SMTP |
| `CF_API_TOKEN` | Deployment only | Cloudflare Pages deploy |
| `CF_ACCOUNT_ID` | Deployment only | Cloudflare Pages deploy |

## Automation

`.github/workflows/digest.yml` runs at 03:00 UTC daily. It commits changes to `digests/`, `docs/`, and `seen_urls.json`, then deploys `docs/` to Cloudflare Pages via Wrangler. Trigger manually with `gh workflow run digest.yml`.
