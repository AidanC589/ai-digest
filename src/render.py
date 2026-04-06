"""Page assembly: render digest markdown to HTML and maintain archive."""

import re
import logging
from datetime import datetime

from src.config import DOCS_DIR
from src.md import inline, slugify, parse_sections, extract_tldr, render_section_body, render_try_block
from src.styles import DIGEST_CSS, ARCHIVE_CSS, GOOGLE_FONTS

log = logging.getLogger(__name__)

KNOWN_SECTIONS = [
    ("General AI Developments",    "general-ai-developments"),
    ("Engineering & AI Workflows", "engineering-ai-workflows"),
    ("Tool Updates",               "tool-updates"),
    ("GitHub Trending",            "github-trending"),
    ("Try This",                   "try-this"),
]

# Keep old name available for any external callers.
markdown_to_html = __import__("src.md", fromlist=["to_html"]).to_html


def render_html(md_content, today_str, cost=None):
    """Render a digest markdown string into a complete HTML page."""
    tldr_text = extract_tldr(md_content)

    body_md = re.sub(r"^# .+\n", "", md_content)
    body_md = re.sub(r"## TL;DR\n.*?(?=\n## |\Z)", "", body_md, flags=re.DOTALL).strip()

    sections = parse_sections(body_md)
    section_titles = {t for t, _ in sections}

    nav_links = "".join(
        f'<a href="#{slug}">{label}</a>'
        for label, slug in KNOWN_SECTIONS
        if label in section_titles
    )

    parts = []
    section_num = 0
    for title, body in sections:
        if "Try This" in title:
            parts.append(render_try_block(body))
        else:
            section_num += 1
            slug = slugify(title)
            content = render_section_body(title, body)
            parts.append(
                f'<section class="section" id="{slug}">\n'
                f'  <div class="section-header">\n'
                f'    <span class="section-number">{section_num:02d}</span>\n'
                f'    <h2 class="section-title">{title}</h2>\n'
                f'  </div>\n'
                f'  {content}\n'
                f'</section>'
            )

    sections_html = "\n".join(parts)
    formatted_date = datetime.strptime(today_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
    cost_html = f'<span class="cost-pill">${cost:.4f}</span>' if cost is not None else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Digest — {today_str}</title>
  {GOOGLE_FONTS}
  <style>
{DIGEST_CSS}
  </style>
</head>
<body>
  <div class="masthead">
    <p class="masthead-kicker">Daily AI Intelligence</p>
    <h1 class="masthead-title">AI Digest</h1>
    <p class="masthead-date">{formatted_date}</p>
  </div>
  <nav class="nav-bar">{nav_links}</nav>
  <div class="wrapper">
    <div class="tldr-block">
      <span class="tldr-label">TL;DR</span>
      <p>{inline(tldr_text)}</p>
    </div>
    {sections_html}
    <footer>
      <div class="footer-left">AI Digest &middot; Daily Briefing</div>
      <div class="footer-right">
        <a class="footer-archive" href="archive.html">Archive</a>{cost_html}
      </div>
    </footer>
  </div>
</body>
</html>"""


def update_archive(today_str):
    """Add today's entry to docs/archive.html, creating it if needed."""
    archive_path = DOCS_DIR / "archive.html"
    entry_display = datetime.strptime(today_str, "%Y-%m-%d").strftime("%A, %d %B")
    entry_year    = today_str[:4]
    entry_line    = (
        f'      <li data-date="{today_str}" data-year="{entry_year}">'
        f'<a href="{today_str}.html">{entry_display}</a></li>\n'
    )

    if archive_path.exists():
        content = archive_path.read_text(encoding="utf-8")
        if today_str in content:
            return
        content = content.replace("</ul>", entry_line + "    </ul>", 1)
        archive_path.write_text(content, encoding="utf-8")
    else:
        archive_path.write_text(
            f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Digest — Archive</title>
  {GOOGLE_FONTS}
  <style>
{ARCHIVE_CSS}
  </style>
</head>
<body>
  <div class="masthead">
    <h1 class="masthead-title">AI Digest</h1>
    <p class="masthead-sub">Archive</p>
  </div>
  <div class="wrapper">
    <div class="back-row">
      <a class="back-link" href="index.html">← Latest digest</a>
    </div>
    <ul id="entries">
{entry_line}    </ul>
    <div id="grouped"></div>
  </div>
  <script>
    const items = Array.from(document.querySelectorAll('#entries li'));
    const grouped = document.getElementById('grouped');
    const byYear = {{}};
    items.forEach(li => {{
      const year = li.dataset.year;
      if (!byYear[year]) byYear[year] = [];
      byYear[year].push(li);
    }});
    Object.keys(byYear).sort((a,b) => b-a).forEach(year => {{
      const div = document.createElement('div');
      div.className = 'year-group';
      const p = document.createElement('p');
      p.className = 'year-label';
      p.textContent = year;
      div.appendChild(p);
      const ul = document.createElement('ul');
      byYear[year].forEach(li => ul.appendChild(li));
      div.appendChild(ul);
      grouped.appendChild(div);
    }});
  </script>
</body>
</html>""",
            encoding="utf-8",
        )
