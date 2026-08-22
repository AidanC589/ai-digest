"""Markdown parsing and HTML fragment generation."""

import re
import html as html_mod


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _escape_html(text):
    """Escape text for safe use in HTML body content and quoted attributes."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )


def safe_url(url):
    """Allow only http(s) links; anything else (javascript:, data:, ...) becomes '#'.

    Idempotent: callers pass either a raw URL (render_section_body) or one that
    inline() has already escaped, so unescape first and escape exactly once —
    otherwise "?a=1&b=2" would become "?a=1&amp;amp;b=2" and resolve wrongly.
    Validating the *unescaped* value also blocks entity-obfuscated schemes.
    """
    u = html_mod.unescape(url.strip())
    return _escape_html(u) if re.match(r"https?://", u, re.I) else "#"


def inline(text):
    """Apply inline markdown: bold, code, links.

    Model output is untrusted — it derives from arbitrary RSS/Reddit/HN content —
    so everything is escaped FIRST and markdown is applied to the escaped text.
    Never emit an unescaped substring of `text`.
    """
    text = _escape_html(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{safe_url(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    return text


def parse_sections(md_text):
    """Split markdown into [(title, body_text)] for each ## section."""
    sections = []
    current_title = None
    current_lines = []
    for line in md_text.split("\n"):
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines)))
    return sections


def extract_tldr(md_text):
    match = re.search(r"## TL;DR\n(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def render_section_body(title, body_text):
    """Render bullet entries for a section into HTML fragments."""
    is_tool = "Tool Updates" in title
    parts = []

    for line in body_text.strip().split("\n"):
        s = line.strip()
        if not s:
            continue

        if s.startswith("- ") or s.startswith("* "):
            content = s[2:]
        else:
            parts.append(f'<p class="empty">{inline(s)}</p>')
            continue

        m = re.match(r'\[(.+?)\]\(([^)]+)\)\s*[—–-]+\s*(.*)', content, re.DOTALL)
        if m:
            link_text, url, desc = m.group(1), m.group(2), m.group(3).strip()
            # Strip leading [Tag] prefixes e.g. "[AINews] Title" → "Title"
            link_text = re.sub(r'^\[[^\]]+\]\s*', '', link_text)
            if is_tool:
                ver_m = re.search(r'(v[\d]+[\d.]*)', link_text)
                tag_html = (
                    f'<span class="tool-tag">{ver_m.group(1)}</span>'
                    if ver_m else ""
                )
                parts.append(
                    f'<div class="tool-entry">'
                    f'<div class="tool-name">'
                    f'<a href="{safe_url(url)}" target="_blank" rel="noopener">{_escape_html(link_text)}</a>'
                    f'{tag_html}</div>'
                    f'<div class="tool-desc">{inline(desc)}</div>'
                    f'</div>'
                )
            else:
                parts.append(
                    f'<div class="entry">'
                    f'<div class="entry-source">'
                    f'<a href="{safe_url(url)}" target="_blank" rel="noopener">{_escape_html(link_text)}</a>'
                    f'</div>'
                    f'<div class="entry-body">{inline(desc)}</div>'
                    f'</div>'
                )
        else:
            cls = "tool-desc" if is_tool else "entry-body"
            # GitHub Trending rows lead with an [AI]/[Other] tag before the repo
            # link, so they never match the pattern above. Render the tag as a chip
            # instead of leaving the brackets as literal text. Mirrors the same
            # handling in email_render.render_section_body.
            tag_html = ""
            tag_m = re.match(r'^\[(AI|Other)\]\s*', content)
            if tag_m:
                variant = " other" if tag_m.group(1) == "Other" else ""
                tag_html = f'<span class="tool-tag repo-tag{variant}">{tag_m.group(1)}</span>'
                content = content[tag_m.end():]
            parts.append(
                f'<div class="entry"><div class="{cls}">{tag_html}{inline(content)}</div></div>'
            )

    return "\n".join(parts)


def to_html(md_text):
    """Generic markdown → HTML for simple content (legacy/fallback)."""
    lines = md_text.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        s = line.rstrip()
        if s.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            heading = s[3:]
            html_lines.append(f'<h2 id="{slugify(heading)}">{inline(heading)}</h2>')
        elif s.startswith("### "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("- ") or s.startswith("* "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"  <li>{inline(s[2:])}</li>")
        elif s == "":
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("")
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<p>{inline(s)}</p>")

    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
