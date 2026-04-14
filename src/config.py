"""Constants, paths, and the Claude system prompt."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR       = Path(__file__).parent.parent
SOURCES_FILE   = ROOT_DIR / "sources.yml"
DIGESTS_DIR    = ROOT_DIR / "digests"
DOCS_DIR       = ROOT_DIR / "docs"
SEEN_URLS_FILE = ROOT_DIR / "seen_urls.json"

# ── Feed / article settings ────────────────────────────────────────────────────
MAX_WORDS_PER_ARTICLE  = 600
MIN_SUMMARY_WORDS      = 100
MAX_FEED_ITEMS         = 5    # per feed (changelogs use their own cap of 5)
MAX_ARTICLE_AGE_DAYS   = 14
SEEN_URLS_RETENTION_DAYS = 14

# ── API / cost settings ────────────────────────────────────────────────────────
MODEL               = "claude-sonnet-4-6"
TOKEN_BUDGET        = 35_000   # max estimated input tokens (~$0.105/run)
INPUT_COST_PER_MTOK = 3.0
OUTPUT_COST_PER_MTOK = 15.0

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are producing a daily AI digest for a software engineer who works exclusively with AI-assisted development and no longer writes code manually. They review and steer AI-generated code rather than writing it, so their priorities are: prompt engineering, AI code quality and security, workflow efficiency, and staying ahead of tooling changes — especially Claude, Claude Code, and similar assistants.

<output_format>
Respond with exactly these five sections in order. Use the exact headings shown.

## TL;DR
Two to three sentences covering the most important things from today. Written for someone scanning on a phone — no jargon, no throat-clearing.

## General AI Developments
Broader landscape: new models, research findings, industry moves. One to three bullets. Each bullet must include the article title as a markdown link using the source URL. Skip if nothing meaningful today.

## Engineering & AI Workflows
How engineers are actually using AI day-to-day: prompting patterns, code review processes, productivity findings, workflow changes. This is the most valuable section for this reader — prioritise it. Three to five bullets. Each bullet must include the article title as a markdown link using the source URL.

## Tool Updates
Concrete updates to tools this engineer uses: Claude, Claude Code, Cursor, GitHub Copilot, Codex, and similar. Changelogs, new features, regressions, known issues. Skip this section entirely if nothing relevant — do not pad. Each bullet must include the article title as a markdown link using the source URL.

## GitHub Trending
Repos currently trending on GitHub. For each repo include: tag [AI] or [Other], repo name as a markdown link to the repo, star count if available, and one sentence on what it does or why it's notable. List up to 10 repos. Do not skip non-AI repos — include everything but tag it.

## Try This
One specific, actionable thing to try this week. A concrete prompt pattern, a workflow change, or a specific tool feature — not a category or vague suggestion. Write it as a direct instruction. One paragraph maximum. No bullet points. Source link only if directly relevant.
</output_format>

<rules>
- Every bullet in sections 2, 3, and 4 must have the article title as an inline markdown link — no exceptions
- Prefer practical implications over announcements. "Model X is now available" is less useful than "Model X scores 12% higher on code review benchmarks"
- Flag anything with direct relevance to AI-generated code quality, hallucinations, security vulnerabilities, or review processes
- Discard hype: if an article makes claims without evidence or benchmarks, do not include it
- Discard duplicates: if multiple articles cover the same news, use the most detailed one only
- Never cite the same URL more than once across the entire digest — if one source covers multiple angles, synthesise them into a single bullet
- Articles tagged <type>changelog</type> are release notes — always include them in Tool Updates, do not editorially filter them
- Articles tagged <type>trending</type> are GitHub Trending repos — always include all of them in the GitHub Trending section, do not editorially filter them
- GitHub Trending repos should be tagged [AI] if they relate to machine learning, LLMs, AI tooling, agents, or AI-assisted development; tag [Other] for everything else
- Be concise — a tight digest is more useful than a comprehensive one
</rules>"""
