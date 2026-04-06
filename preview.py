#!/usr/bin/env python3
"""
Generate a local preview without touching any tracked files.

Uses today's digest from digests/ if it exists, otherwise renders sample content.
Does NOT call the Anthropic API, write to docs/, or send email.

Usage:
    python preview.py
    # then open the printed file:// URL in your browser
"""

import sys
import tempfile
import webbrowser
from datetime import date
from pathlib import Path

from src.render import render_html
from src.config import DIGESTS_DIR

SAMPLE_DIGEST = """\
## TL;DR
Claude Code v2.1.87 ships a fix for co-work dispatch message delivery. OpenAI's Codex CLI hits 0.118.0-alpha with improved context handling. Practitioners are converging on structured review checklists as the most reliable way to catch AI-generated logic errors.

## General AI Developments
- [Anthropic publishes alignment progress report showing 34% reduction in sycophantic responses](https://www.anthropic.com/news/alignment-progress) — key finding: models trained with constitutional AI are more likely to flag their own errors when prompted to review output.
- [Meta open-sources Llama 3.2 with extended context window](https://ai.meta.com/blog/llama-3-2) — 128k context now available in the open-source tier; early benchmarks show competitive performance on code summarisation tasks.

## Engineering & AI Workflows
- [Teams using structured AI code review checklists report 40% fewer logic errors reaching production](https://www.swyx.io/ai-review-checklists) — the most effective pattern: a dedicated review prompt that asks Claude to identify assumptions the original prompt made, not just check the output.
- [Simon Willison on prompt injection risks in agentic pipelines](https://simonwillison.net/2026/Mar/28/prompt-injection/) — documents three real-world cases where AI-generated code silently introduced injection vectors; recommends treating all LLM output as untrusted input at system boundaries.
- [r/LocalLLaMA: practical comparison of Claude Code vs Codex for long refactors](https://www.reddit.com/r/LocalLLaMA/comments/example/) — community consensus: Claude Code handles multi-file context better; Codex faster for single-function tasks.

## Tool Updates
- [Claude Code v2.1.87](https://github.com/anthropics/claude-code/releases/tag/v2.1.87) — Fixed messages in co-work dispatch not being delivered. Minor stability improvements to the MCP server connection handling.
- [Codex CLI 0.118.0-alpha.3](https://github.com/openai/codex/releases/tag/0.118.0-alpha.3) — Adds `--context-file` flag to pass additional context without including it in the conversation history. Fixes token counting bug on Windows.

## Try This
When reviewing AI-generated code, add a second prompt pass specifically focused on assumptions: "List every assumption this code makes about its inputs, the environment, and the behaviour of dependencies. For each assumption, tell me whether it is validated anywhere." This surfaces edge cases that a general review prompt misses, particularly around error handling and boundary conditions.
"""


def main():
    today_str = date.today().isoformat()

    # Use today's real digest if available, otherwise use sample
    digest_path = DIGESTS_DIR / f"{today_str}.md"
    if digest_path.exists():
        raw = digest_path.read_text(encoding="utf-8")
        # Strip the "# AI Digest — YYYY-MM-DD\n\n" header added by write_markdown
        md_content = "\n".join(raw.split("\n")[2:]).strip()
        print(f"Using today's digest: {digest_path}")
    else:
        md_content = SAMPLE_DIGEST.strip()
        print("No digest found for today — using sample content")

    html = render_html(md_content, today_str)

    # Write to a temp file — never touches docs/ or any tracked file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        tmp_path = Path(f.name)

    url = f"file:///{str(tmp_path).replace(chr(92), '/')}"
    print(f"\nPreview ready. Open in your browser:")
    print(f"  {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    main()
