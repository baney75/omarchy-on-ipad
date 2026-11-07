#!/usr/bin/env python3
"""Check repository-relative Markdown links and required image signatures."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts or "_site" in path.parts:
            continue
        for raw in LINK_RE.findall(path.read_text(encoding="utf-8")):
            target = raw.strip().split(maxsplit=1)[0].strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                failures.append(f"{path.relative_to(ROOT)}: link escapes repository: {raw}")
                continue
            if not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)}: missing target: {raw}")

    pngs = [ROOT / "docs/assets/dashboard.png", ROOT / "site/assets/social-card.png"]
    for path in pngs:
        if not path.is_file() or not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            failures.append(f"{path.relative_to(ROOT)}: missing or invalid PNG signature")
    for path in sorted((ROOT / "site/assets").glob("*.svg")):
        body = path.read_text(encoding="utf-8")
        if "<svg" not in body or "</svg>" not in body:
            failures.append(f"{path.relative_to(ROOT)}: invalid SVG shell")

    if failures:
        print("local links and images: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("local links and images: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
