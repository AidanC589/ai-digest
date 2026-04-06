"""CSS constants for the digest and archive pages."""

DIGEST_CSS = """\
    :root {
      --ink: #0f0e0d;
      --paper: #f5f1eb;
      --warm-mid: #e8e0d4;
      --rule: #c8bfb0;
      --accent: #c0392b;
      --accent-dim: #e8d5d3;
      --muted: #7a7268;
      --tag-bg: #0f0e0d;
      --tag-fg: #f5f1eb;
      --link: #1a4a6b;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: var(--paper);
      color: var(--ink);
      font-family: 'DM Sans', sans-serif;
      font-weight: 300;
      line-height: 1.65;
      font-size: 15px;
      min-height: 100vh;
    }

    /* ── MASTHEAD ── */
    .masthead {
      border-bottom: 3px solid var(--ink);
      padding: 2rem 0 1rem;
      text-align: center;
      position: relative;
      overflow: hidden;
    }

    .masthead::before {
      content: '';
      display: block;
      height: 4px;
      background: repeating-linear-gradient(90deg, var(--ink) 0, var(--ink) 8px, transparent 8px, transparent 16px);
      margin-bottom: 1.5rem;
    }

    .masthead-kicker {
      font-family: 'DM Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 0.5rem;
    }

    .masthead-title {
      font-family: 'DM Serif Display', serif;
      font-size: clamp(2.8rem, 8vw, 5rem);
      line-height: 1;
      letter-spacing: -0.02em;
      color: var(--ink);
      margin-bottom: 0.5rem;
    }

    .masthead-date {
      font-family: 'DM Mono', monospace;
      font-size: 0.7rem;
      letter-spacing: 0.15em;
      color: var(--muted);
      text-transform: uppercase;
    }

    /* ── NAV BAR ── */
    .nav-bar {
      border-bottom: 1px solid var(--rule);
      padding: 0.6rem 0;
      overflow-x: auto;
      white-space: nowrap;
      text-align: center;
      background: var(--warm-mid);
    }

    .nav-bar a {
      font-family: 'DM Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      text-decoration: none;
      padding: 0 1rem;
      border-right: 1px solid var(--rule);
      transition: color 0.15s;
    }
    .nav-bar a:last-child { border-right: none; }
    .nav-bar a:hover { color: var(--ink); }

    /* ── LAYOUT ── */
    .wrapper {
      max-width: 760px;
      margin: 0 auto;
      padding: 0 1.5rem;
    }

    /* ── TL;DR ── */
    .tldr-block {
      margin: 2.5rem 0;
      border: 1px solid var(--ink);
      position: relative;
    }

    .tldr-label {
      position: absolute;
      top: -0.75rem;
      left: 1.2rem;
      background: var(--ink);
      color: var(--paper);
      font-family: 'DM Mono', monospace;
      font-size: 0.6rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      padding: 0.15rem 0.6rem;
    }

    .tldr-block p {
      padding: 1.5rem 1.4rem 1.3rem;
      font-size: 0.93rem;
      font-style: italic;
      color: var(--ink);
      font-family: 'DM Serif Display', serif;
      line-height: 1.6;
      font-weight: 400;
    }

    .tldr-block p strong {
      font-style: normal;
      font-weight: 400;
      border-bottom: 2px solid var(--accent);
    }

    /* ── SECTION ── */
    .section {
      margin-bottom: 2.5rem;
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.2rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--ink);
    }

    .section-number {
      font-family: 'DM Mono', monospace;
      font-size: 0.6rem;
      color: var(--muted);
      flex-shrink: 0;
      padding-top: 2px;
    }

    .section-title {
      font-family: 'DM Serif Display', serif;
      font-size: 1.25rem;
      font-weight: 400;
      color: var(--ink);
      letter-spacing: -0.01em;
    }

    /* ── ENTRY ── */
    .entry {
      padding: 1rem 0;
      border-bottom: 1px solid var(--rule);
      display: grid;
      grid-template-columns: 1fr;
      gap: 0.35rem;
    }

    .entry:last-child { border-bottom: none; }

    .entry-source {
      font-family: 'DM Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .entry-source a {
      color: var(--link);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.15s;
    }
    .entry-source a:hover { border-color: var(--link); }

    .entry-body {
      font-size: 0.9rem;
      line-height: 1.68;
      color: #1e1c1a;
    }

    .entry-body strong {
      font-weight: 500;
      color: var(--ink);
    }

    /* ── TOOL UPDATE ENTRIES ── */
    .tool-entry {
      padding: 0.85rem 0;
      border-bottom: 1px solid var(--rule);
    }
    .tool-entry:last-child { border-bottom: none; }

    .tool-name {
      font-family: 'DM Mono', monospace;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--ink);
      margin-bottom: 0.3rem;
    }

    .tool-name a {
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.15s;
    }
    .tool-name a:hover { border-color: var(--ink); }

    .tool-tag {
      display: inline-block;
      font-family: 'DM Mono', monospace;
      font-size: 0.55rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      background: var(--tag-bg);
      color: var(--tag-fg);
      padding: 0.1rem 0.4rem;
      margin-left: 0.5rem;
      vertical-align: middle;
      position: relative;
      top: -1px;
    }

    .tool-tag.alpha { background: #6b4f1a; }
    .tool-tag.minor { background: #2a5a3a; }

    .tool-desc {
      font-size: 0.88rem;
      line-height: 1.65;
      color: #1e1c1a;
    }

    /* ── TRY THIS ── */
    .try-block {
      background: var(--ink);
      color: var(--paper);
      padding: 1.8rem 1.6rem;
      margin-bottom: 2.5rem;
      position: relative;
    }

    .try-block::before {
      content: '→ TRY THIS';
      display: block;
      font-family: 'DM Mono', monospace;
      font-size: 0.6rem;
      letter-spacing: 0.2em;
      color: var(--accent);
      margin-bottom: 0.8rem;
    }

    .try-block p {
      font-size: 0.9rem;
      line-height: 1.72;
      color: #e8e4de;
    }

    .try-block code {
      font-family: 'DM Mono', monospace;
      font-size: 0.8rem;
      background: rgba(255,255,255,0.08);
      padding: 0.1rem 0.35rem;
      color: #f0c07a;
    }

    /* ── FOOTER ── */
    footer {
      border-top: 3px solid var(--ink);
      padding: 1.2rem 0;
      margin-top: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .footer-left {
      font-family: 'DM Mono', monospace;
      font-size: 0.62rem;
      letter-spacing: 0.1em;
      color: var(--muted);
      text-transform: uppercase;
    }

    .footer-right {
      font-family: 'DM Mono', monospace;
      font-size: 0.62rem;
      color: var(--muted);
    }

    .footer-archive {
      color: var(--link);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.15s;
    }
    .footer-archive:hover { border-color: var(--link); }

    .cost-pill {
      display: inline-block;
      font-family: 'DM Mono', monospace;
      font-size: 0.58rem;
      background: var(--warm-mid);
      border: 1px solid var(--rule);
      padding: 0.1rem 0.5rem;
      color: var(--muted);
      margin-left: 0.5rem;
    }

    /* ── EMPTY STATE ── */
    .empty {
      font-family: 'DM Mono', monospace;
      font-size: 0.75rem;
      color: var(--muted);
      padding: 1rem 0;
      font-style: italic;
    }

    .section + .section { border-top: none; }

    @media (max-width: 480px) {
      .masthead-title { font-size: 2.4rem; }
      footer { flex-direction: column; align-items: flex-start; }
    }"""

ARCHIVE_CSS = """\
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --ink: #0f0e0d; --paper: #f5f1eb; --warm-mid: #e8e0d4; --rule: #c8bfb0;
      --muted: #7a7268; --link: #1a4a6b;
    }
    body {
      font-family: 'DM Sans', sans-serif;
      font-weight: 300;
      font-size: 15px;
      line-height: 1.65;
      color: var(--ink);
      background: var(--paper);
      margin: 0;
    }
    .masthead {
      border-bottom: 3px solid var(--ink);
      padding: 1.5rem 0 1rem;
      text-align: center;
    }
    .masthead::before {
      content: '';
      display: block;
      height: 4px;
      background: repeating-linear-gradient(90deg, var(--ink) 0, var(--ink) 8px, transparent 8px, transparent 16px);
      margin-bottom: 1.5rem;
    }
    .masthead-title {
      font-family: 'DM Serif Display', serif;
      font-size: 2.5rem;
      line-height: 1;
      letter-spacing: -0.02em;
      color: var(--ink);
      margin-bottom: 0.4rem;
    }
    .masthead-sub {
      font-family: 'DM Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .wrapper { max-width: 760px; margin: 0 auto; padding: 0 1.5rem; }
    .back-row {
      padding: 1rem 0;
      border-bottom: 1px solid var(--rule);
      margin-bottom: 2rem;
    }
    .back-link {
      font-family: 'DM Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--link);
      text-decoration: none;
    }
    .back-link:hover { text-decoration: underline; }
    .year-group { margin-bottom: 2rem; }
    .year-label {
      font-family: 'DM Serif Display', serif;
      font-size: 1.1rem;
      color: var(--ink);
      margin: 0 0 0.75rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--ink);
    }
    ul { list-style: none; padding: 0; margin: 0; }
    li {
      border-bottom: 1px solid var(--rule);
      padding: 0.65rem 0;
      font-family: 'DM Mono', monospace;
      font-size: 0.75rem;
    }
    li:last-child { border-bottom: none; }
    a { color: var(--link); text-decoration: none; }
    a:hover { text-decoration: underline; }
    #entries { display: none; }"""

GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300'
    '&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300'
    '&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">'
)
