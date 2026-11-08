#!/usr/bin/env python3
"""Enforce pinned actions and least-privilege workflow invariants without YAML dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USES_RE = re.compile(r"^\s*uses:\s*([^\s#]+)")
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[a-f0-9]{40}$")  # a reusable workflow path has several segments


def main() -> int:
    failures: list[str] = []
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        body = path.read_text(encoding="utf-8")
        if "pull_request_target:" in body:
            failures.append(f"{path.name}: pull_request_target is forbidden")
        if re.search(r"permissions:\s*(?:write-all|read-all)", body):
            failures.append(f"{path.name}: broad permission alias is forbidden")
        if "github/codeql-action/" in body and not re.search(r"(?m)^  actions:\s*read\s*$", body):
            failures.append(f"{path.name}: CodeQL requires actions: read to inspect its workflow run")
        for line_number, line in enumerate(body.splitlines(), 1):
            match = USES_RE.match(line)
            if not match:
                continue
            value = match.group(1)
            if value.startswith("./"):
                continue
            if not PIN_RE.fullmatch(value):
                failures.append(f"{path.name}:{line_number}: action is not pinned to a 40-character commit: {value}")
    if failures:
        print("workflow policy: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("workflow policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
