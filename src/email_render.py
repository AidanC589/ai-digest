"""Email rendering: table layout, inline styles only, no web fonts.

Kept separate from src/render.py because mail clients strip most of what the
website relies on — CSS custom properties, <style> blocks, flex/grid, and
external font links. Markdown parsing is shared via src/md.py; only the HTML
fragment builders are email-specific.
"""

import re
from datetime import datetime

from src.md import inline, parse_sections, extract_tldr, safe_url, _escape_html

SITE_URL = "https://ai-digest-elw.pages.dev"

# Palette mirrored from the :root block in src/styles.py, as literal hex.
INK    = "#0f0e0d"
PAPER  = "#f5f1eb"
WARM   = "#e8e0d4"
RULE   = "#c8bfb0"
ACCENT = "#c0392b"
MUTED  = "#7a7268"
LINK   = "#1a4a6b"
BODY   = "#1e1c1a"

SERIF = "Georgia,'Times New Roman',serif"
SANS  = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO  = "Consolas,Monaco,'Courier New',monospace"

_TAG = (
    f"display:inline-block;font-family:{SANS};font-size:10px;letter-spacing:0.1em;"
    f"text-transform:uppercase;background:{INK};color:{PAPER};padding:2px 6px;"
)


def _style_tags(html, dark=False):
    """Add inline styles to the tags md.inline() emits — classes are useless in email."""
    if dark:
        link   = "color:#f0c07a;text-decoration:underline;"
        strong = "font-weight:600;color:#ffffff;"
        code   = f"font-family:{MONO};font-size:14px;background:#2a2724;padding:1px 4px;color:#f0c07a;"
    else:
        link   = f"color:{LINK};text-decoration:underline;"
        strong = f"font-weight:600;color:{INK};"
        code   = f"font-family:{MONO};font-size:14px;background:{WARM};padding:1px 4px;color:{BODY};"

    html = html.replace("<a ", f'<a style="{link}" ')
    html = html.replace("<strong>", f'<strong style="{strong}">')
    html = html.replace("<code>", f'<code style="{code}">')
    return html


def _inline(text, dark=False):
    return _style_tags(inline(text), dark=dark)


def _entry_html(title_html, desc_html):
    return (
        f'<div style="font-family:{SANS};font-size:16px;line-height:1.45;'
        f'font-weight:600;margin:0 0 8px;">{title_html}</div>'
        f'<div style="font-family:{SANS};font-size:15px;line-height:1.6;'
        f'color:{BODY};">{desc_html}</div>'
    )


def _section_body(title, body_text):
    """Email variant of md.render_section_body — same parsing, table-safe HTML."""
    is_tool = "Tool Updates" in title
    entries = []

    for line in body_text.strip().split("\n"):
        s = line.strip()
        if not s:
            continue

        if s.startswith("- ") or s.startswith("* "):
            content = s[2:]
        else:
            entries.append(
                f'<div style="font-family:{SANS};font-size:14px;font-style:italic;'
                f'color:{MUTED};">{_inline(s)}</div>'
            )
            continue

        m = re.match(r'\[(.+?)\]\(([^)]+)\)\s*[—–-]+\s*(.*)', content, re.DOTALL)
        if m:
            link_text, url, desc = m.group(1), m.group(2), m.group(3).strip()
            link_text = re.sub(r'^\[[^\]]+\]\s*', '', link_text)
            tag_html = ""
            if is_tool:
                ver_m = re.search(r'(v[\d]+[\d.]*)', link_text)
                if ver_m:
                    tag_html = f'<span style="{_TAG}margin-left:8px;">{ver_m.group(1)}</span>'
            anchor = (
                f'<a href="{safe_url(url)}" target="_blank" rel="noopener" '
                f'style="color:{LINK};text-decoration:underline;">{_escape_html(link_text)}</a>'
            )
            entries.append(_entry_html(anchor + tag_html, _inline(desc)))
        else:
            # Lines the pattern above does not match — e.g. GitHub Trending rows,
            # which lead with an [AI]/[Other] tag before the repo link.
            tag_m = re.match(r'^\[(AI|Other)\]\s*', content)
            prefix = ""
            if tag_m:
                bg = INK if tag_m.group(1) == "AI" else MUTED
                prefix = (
                    f'<span style="{_TAG}background:{bg};margin-right:8px;">'
                    f'{tag_m.group(1)}</span>'
                )
                content = content[tag_m.end():]
            entries.append(
                f'<div style="font-family:{SANS};font-size:15px;line-height:1.6;'
                f'color:{BODY};">{prefix}{_inline(content)}</div>'
            )

    parts = []
    for i, entry in enumerate(entries):
        border = "" if i == len(entries) - 1 else f"border-bottom:1px solid {RULE};"
        parts.append(f'<div style="padding:20px 2px;{border}">{entry}</div>')
    return "\n".join(parts)


def _section(number, title, body_text):
    return (
        f'<div style="margin:0 0 34px;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="border-bottom:2px solid {INK};margin:0 0 6px;">'
        f'<tr>'
        f'<td width="34" valign="top" style="font-family:{SANS};font-size:11px;'
        f'letter-spacing:0.1em;color:{MUTED};padding:0 0 10px;">{number:02d}</td>'
        f'<td style="font-family:{SERIF};font-size:21px;color:{INK};padding:0 0 10px;">{_escape_html(title)}</td>'
        f'</tr></table>'
        f'{_section_body(title, body_text)}'
        f'</div>'
    )


def render_email(md_content, today_str):
    """Render a digest markdown string into a mail-client-safe HTML email."""
    tldr_text = extract_tldr(md_content)

    body_md = re.sub(r"^# .+\n", "", md_content)
    body_md = re.sub(r"## TL;DR\n.*?(?=\n## |\Z)", "", body_md, flags=re.DOTALL).strip()

    parts = []
    number = 0
    for title, body in parse_sections(body_md):
        number += 1
        parts.append(_section(number, title, body))
    sections_html = "\n".join(parts)

    formatted_date = datetime.strptime(today_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
    preheader = re.split(r"(?<=\.)\s", tldr_text.strip())[0] if tldr_text else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>AI Digest — {today_str}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};color:{INK};">
  <div style="display:none;max-height:0;max-width:0;opacity:0;overflow:hidden;font-size:1px;line-height:1px;color:{PAPER};">{_escape_html(preheader)}</div>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="{PAPER}" style="background:{PAPER};">
    <tr>
      <td align="center" style="padding:28px 20px 48px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="width:100%;max-width:600px;">
          <tr>
            <td align="center" style="border-bottom:3px solid {INK};padding:14px 0 20px;">
              <div style="font-family:{SERIF};font-size:44px;line-height:1.05;color:{INK};">AI Digest</div>
              <div style="font-family:{SANS};font-size:11px;letter-spacing:0.15em;text-transform:uppercase;color:{MUTED};padding-top:8px;">{formatted_date}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 0 0;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border:1px solid {INK};margin:0 0 34px;">
                <tr>
                  <td style="padding:22px 24px;">
                    <div style="font-family:{SANS};font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:{MUTED};margin:0 0 8px;">TL;DR</div>
                    <div style="font-family:{SERIF};font-size:17px;line-height:1.6;font-style:italic;color:{INK};">{_inline(tldr_text)}</div>
                  </td>
                </tr>
              </table>
              {sections_html}
            </td>
          </tr>
          <tr>
            <td style="border-top:3px solid {INK};padding:20px 0 0;font-family:{SANS};font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:{MUTED};">
              AI Digest &middot; Daily Briefing
              <span style="float:right;text-transform:none;letter-spacing:0;">
                <a href="{SITE_URL}/{today_str}.html" style="color:{LINK};text-decoration:underline;">Read on the web</a>
                &nbsp;&middot;&nbsp;
                <a href="{SITE_URL}/archive.html" style="color:{LINK};text-decoration:underline;">Archive</a>
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
