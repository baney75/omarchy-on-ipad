#!/usr/bin/env python3
"""Reject private-machine traces and dangerous artifact types from the public tree."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "_site", "__pycache__"}
MAX_FILE = 2 * 1024 * 1024
DENIED_SUFFIXES = {".7z", ".a", ".app", ".bin", ".dmg", ".dylib", ".elf", ".exe", ".gz", ".img", ".ipa", ".ipsw", ".iso", ".jar", ".kext", ".ko", ".o", ".pkg", ".rar", ".tar", ".xz", ".zip", ".zst"}
DENIED_MAGIC = (b"\x7fELF", b"MZ", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"PK\x03\x04")
PRIVATE_PATTERNS = {
    "absolute user path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "Apple device UDID": re.compile(r"\b[0-9A-F]{8}-[0-9A-F]{16}\b", re.I),
    "CoreDevice UUID": re.compile(r"\b[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}\b", re.I),
    "private host label": re.compile(r"\b(?:chapel|parish|vestry|rectory|abbey|gatehouse)1\b", re.I),
    "private key marker": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{22,})\b"),
    "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b"),
}

# Contribution evidence has stricter rules than documentation or test source.
EVIDENCE_PRIVATE_PATTERNS = {
    "email address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "IPv4 address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ECID-like value": re.compile(r"(?i)\becid\b\s*[:=]?\s*(?:0x)?[0-9a-f]{8,}"),
    "serial-number field": re.compile(r"(?i)\bserial(?:[ _-]?number)?\b\s*[:=]\s*\S+"),
}


def tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True, check=True)
    return [root / value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def main() -> int:
    failures: list[str] = []
    for path in tracked_paths(ROOT):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts) or not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_FILE:
            failures.append(f"{relative}: exceeds {MAX_FILE} bytes")
            continue
        if path.suffix.lower() in DENIED_SUFFIXES:
            failures.append(f"{relative}: denied artifact extension")
        raw = path.read_bytes()
        if raw.startswith(DENIED_MAGIC):
            failures.append(f"{relative}: executable/archive file signature is not accepted")
        if b"\0" in raw[:8192] and path.suffix.lower() not in {".png"}:
            failures.append(f"{relative}: unexpected binary content")
            continue
        if path.suffix.lower() == ".png":
            continue
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"{relative}: non-UTF-8 content")
            continue
        for label, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(body):
                failures.append(f"{relative}: contains {label}")
    if failures:
        print("public surface: FAIL", file=sys.stderr)
        for failure in sorted(set(failures)):
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("public surface: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
