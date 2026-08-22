#!/usr/bin/env python3
"""One-off: seed trending_history.json from the existing digest archive.

The archive predates deterministic rendering, so its star counts appear in four
different formats the model drifted between. This parses all of them once so the
velocity feature ships with history instead of a three-week cold start.

Run from the repo root, check the output, then DELETE this file — nothing in
src/ parses markdown, and the legacy formats should not become maintenance.

    python scripts/bootstrap_velocity.py [--force]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DIGESTS_DIR, TRENDING_HISTORY_FILE  # noqa: E402

# Handles "★29,595", "35,770★", "· 233,593★" and the bolded variant alike.
STARS = re.compile(r"(?:★\s*([\d,]+)|([\d,]+)\s*★)")
REPO = re.compile(r"\(https?://(?:www\.)?github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)\)")


def parse_digest(path):
    """Yield (repo, stars) for each trending row in one digest."""
    in_section = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            in_section = "GitHub Trending" in line
            continue
        if not in_section or "★" not in line:
            continue
        repo_m = REPO.search(line)
        if not repo_m:
            continue
        # Only look for stars after the link, so a URL containing digits can't match.
        star_m = STARS.search(line[repo_m.end():])
        if not star_m:
            continue
        yield repo_m.group(1), int((star_m.group(1) or star_m.group(2)).replace(",", ""))


def main():
    if TRENDING_HISTORY_FILE.exists() and "--force" not in sys.argv:
        sys.exit(f"{TRENDING_HISTORY_FILE.name} already exists — pass --force to overwrite")

    history, rows, skipped_sponsors = {}, 0, 0
    files = sorted(DIGESTS_DIR.glob("*.md"))
    for path in files:
        digest_date = path.stem
        for repo, stars in parse_digest(path):
            # The scraper used to file repos under the owner's Sponsors link. Those
            # keys can never match again now that it's fixed, so don't carry them.
            if repo.lower().startswith("sponsors/"):
                skipped_sponsors += 1
                continue
            # Deltas were rarely recorded; the baseline uses total growth anyway.
            history.setdefault(repo, {})[digest_date] = [stars, None]
            rows += 1

    TRENDING_HISTORY_FILE.write_text(
        json.dumps(history, indent=2, sort_keys=True), encoding="utf-8"
    )

    trackable = sum(1 for obs in history.values() if len(obs) >= 3)
    print(f"Scanned {len(files)} digests")
    print(f"  {rows} rows kept, {skipped_sponsors} sponsors/* rows skipped")
    print(f"  {len(history)} repos, {trackable} with 3+ observations")
    print(f"Wrote {TRENDING_HISTORY_FILE}")


if __name__ == "__main__":
    main()
