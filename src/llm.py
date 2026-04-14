"""Token estimation, message building, and Anthropic API call."""

import logging
from datetime import date

import tiktoken
import anthropic

from src.config import (
    MODEL, SYSTEM_PROMPT, TOKEN_BUDGET,
    MAX_WORDS_PER_ARTICLE, INPUT_COST_PER_MTOK, OUTPUT_COST_PER_MTOK,
)
from src.feeds import truncate_to_words

log = logging.getLogger(__name__)


def estimate_tokens(text, encoding="cl100k_base"):
    """Estimate token count using tiktoken (cl100k_base ≈ Claude tokeniser)."""
    try:
        enc = tiktoken.get_encoding(encoding)
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4  # rough fallback


def build_user_message(articles, word_cap=None):
    """Build the XML-structured user message (data first, instruction last)."""
    cap = word_cap or MAX_WORDS_PER_ARTICLE
    lines = ["<articles>"]
    for i, a in enumerate(articles, 1):
        atype = a.get("type")
        # changelog and trending entries are short/structured — don't truncate
        text = a["text"] if atype in ("changelog", "trending") else truncate_to_words(a["text"], cap)
        lines.append(f'  <article index="{i}">')
        lines.append(f"    <title>{a['title']}</title>")
        lines.append(f"    <source>{a['source']}</source>")
        lines.append(f"    <url>{a['url']}</url>")
        if atype in ("changelog", "trending"):
            lines.append(f"    <type>{atype}</type>")
        lines.append(f"    <content>{text}</content>")
        lines.append("  </article>")
    lines.append("</articles>")
    lines.append("")
    lines.append(
        f"Today is {date.today().strftime('%A, %d %B %Y')}. "
        "Write today's digest based on the articles above."
    )
    return "\n".join(lines)


def trim_to_budget(articles):
    """Trim article content until estimated input tokens fit within TOKEN_BUDGET."""
    message = build_user_message(articles)
    tokens  = estimate_tokens(SYSTEM_PROMPT + message)

    if tokens <= TOKEN_BUDGET:
        return message, tokens

    # Pass 1: halve per-article word cap
    log.warning(f"Token estimate {tokens:,} exceeds budget {TOKEN_BUDGET:,} — reducing article length")
    message = build_user_message(articles, word_cap=MAX_WORDS_PER_ARTICLE // 2)
    tokens  = estimate_tokens(SYSTEM_PROMPT + message)

    if tokens <= TOKEN_BUDGET:
        return message, tokens

    # Pass 2: drop non-changelog articles from the end
    log.warning("Still over budget — dropping articles")
    trimmed = list(articles)
    while trimmed and tokens > TOKEN_BUDGET:
        for i in range(len(trimmed) - 1, -1, -1):
            if trimmed[i].get("type") not in ("changelog", "trending"):
                trimmed.pop(i)
                break
        else:
            break
        message = build_user_message(trimmed, word_cap=MAX_WORDS_PER_ARTICLE // 2)
        tokens  = estimate_tokens(SYSTEM_PROMPT + message)

    log.warning(f"Trimmed to {len(trimmed)} articles")
    return message, tokens


def call_anthropic(articles):
    """Trim to budget, call Claude, log token usage and cost."""
    client = anthropic.Anthropic()

    user_message, input_tokens = trim_to_budget(articles)
    log.info(f"Estimated input tokens: {input_tokens:,}")
    log.info(f"Estimated input cost:   ${(input_tokens / 1_000_000) * INPUT_COST_PER_MTOK:.4f}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    in_tok  = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    cost    = (in_tok / 1_000_000) * INPUT_COST_PER_MTOK + (out_tok / 1_000_000) * OUTPUT_COST_PER_MTOK

    log.info(f"Actual tokens — input: {in_tok:,}, output: {out_tok:,}")
    log.info(f"Estimated run cost:     ${cost:.4f}")

    return response.content[0].text, cost
