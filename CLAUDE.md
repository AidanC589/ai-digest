# CLAUDE.md

## What This Project Does

AI Digest is an automated daily news aggregation pipeline that fetches RSS feeds, extracts article text, sends everything to Claude in one API call, and publishes the resulting digest as HTML to Cloudflare Pages and email.

Live site: https://ai-digest-elw.pages.dev

## Commands

```bash
# Run the full digest (requires ANTHROPIC_API_KEY)
python digest.py

# Render a local preview without calling Claude (opens docs/index.html)
python preview.py

# Same, but render the email template instead of the web page
python preview.py --email
```

There are no automated tests. Use `python preview.py` (add `--email` for the email template) to verify HTML rendering changes without an API call.

## Architecture

Data flows through four stages:

1. **Fetch** (`src/feeds.py`) — Parse `sources.yml`, fetch RSS for each source, skip articles older than 14 days, extract full text via Trafilatura if summary < 100 words, truncate to 600 words/article.

2. **Deduplicate** (`src/output.py`) — Filter URLs already in `seen_urls.json` (14-day rolling window). Abort if nothing new.

3. **Summarize** (`src/llm.py`) — Build an XML message from all articles, estimate tokens with tiktoken against a 60,000-token budget (trim if over), then make a single Claude API call. The system prompt in `src/config.py` specifies six required sections and editorial rules.

4. **Publish** (`src/output.py`, `src/render.py`, `src/email_render.py`) — Validate links (HEAD requests), write Markdown to `digests/YYYY-MM-DD.md`, render to `docs/index.html`, update `docs/archive.html`, send email if `GMAIL_APP_PASSWORD` is set.

The web page (`src/render.py` + `src/styles.py`) and the email (`src/email_render.py`) are separate templates. Mail clients strip CSS custom properties, `<style>` blocks, flex/grid, and external font links, so the email is a table layout with inline styles only. Markdown parsing is shared via `src/md.py` — keep it there rather than duplicating it.

Outbound fetches of URLs the pipeline does not control — article links from feeds, and the model's own links during validation — go through `src/net.py`, which rejects loopback/private addresses and re-checks every redirect hop. Use `safe_urlopen`/`safe_fetch_bytes` rather than `urlopen` or `trafilatura.fetch_url` for anything feed- or model-supplied.

**Key design constraint:** Everything goes to Claude in a single API call — no streaming, no chunking — to preserve coherence and leverage prompt caching.

## Configuration

- **`sources.yml`** — Feed sources. Sources with `type: changelog` bypass editorial filtering and are always included.
- **`seen_urls.json`** — Persisted URL dedup state (git-tracked, committed by GitHub Actions).

## Git

The 03:00 UTC Action commits to `main` daily, so the remote is usually ahead. Run
`git pull` before pushing. This clone sets `pull.rebase` and `rebase.autoStash`, so that
rebases and restores uncommitted work rather than making a merge commit.

That config lives in `.git/config`, which is not tracked — a fresh clone needs it again:

```bash
git config pull.rebase true && git config rebase.autoStash true
```

The bot only writes generated output (`digests/`, `docs/*.html`, `seen_urls.json`,
`trending_history.json`), so a rebase has nothing to conflict with as long as those
stay machine-written. Don't hand-edit them.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `GMAIL_USER` | No | Gmail address to send/receive the digest |
| `GMAIL_APP_PASSWORD` | No | Email delivery via SMTP |
| `CF_API_TOKEN` | Deployment only | Cloudflare Pages deploy |
| `CF_ACCOUNT_ID` | Deployment only | Cloudflare Pages deploy |
