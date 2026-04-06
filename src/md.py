"""Markdown parsing and HTML fragment generation."""

import re


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def inline(text):
    """Apply inline markdown: bold, code, links."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
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
                    f'<a href="{url}" target="_blank" rel="noopener">{link_text}</a>'
                    f'{tag_html}</div>'
                    f'<div class="tool-desc">{inline(desc)}</div>'
                    f'</div>'
                )
            else:
                parts.append(
                    f'<div class="entry">'
                    f'<div class="entry-source">'
                    f'<a href="{url}" target="_blank" rel="noopener">{link_text}</a>'
                    f'</div>'
                    f'<div class="entry-body">{inline(desc)}</div>'
                    f'</div>'
                )
        else:
            cls = "tool-desc" if is_tool else "entry-body"
            parts.append(
                f'<div class="entry"><div class="{cls}">{inline(content)}</div></div>'
            )

    return "\n".join(parts)


def render_try_block(body_text):
    """Render the Try This section as a dark callout block."""
    parts = [
        f"<p>{inline(line.strip())}</p>"
        for line in body_text.strip().split("\n")
        if line.strip()
    ]
    return '<div class="try-block" id="try-this">\n' + "\n".join(parts) + "\n</div>"


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
