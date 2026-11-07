#!/usr/bin/env python3
"""Build the dependency-free GitHub Pages dashboard from verified repository data."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from validate import ROOT, validate_progress

STATE_LABELS = {
    "blocked": "Blocked",
    "active": "Active",
    "prepared": "Prepared",
    "verified_offline": "Verified offline",
    "verified_physical": "Verified physical",
    "complete": "Complete",
}
TOKEN_RE = re.compile(r"\{\{\{?[A-Z0-9_]+\}?\}\}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fill(template: str, context: dict[str, object]) -> str:
    def raw(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"missing raw template value {key}")
        return str(context[key])

    def escaped(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"missing template value {key}")
        return html.escape(str(context[key]), quote=True)

    rendered = re.sub(r"\{\{\{([A-Z0-9_]+)\}\}\}", raw, template)
    rendered = re.sub(r"\{\{([A-Z0-9_]+)\}\}", escaped, rendered)
    survivor = TOKEN_RE.search(rendered)
    if survivor:
        raise ValueError(f"unfilled placeholder {survivor.group(0)}")
    return rendered


def format_timestamp(raw: str) -> str:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return value.strftime("%-d %b %Y, %H:%M UTC")


def format_date(raw: str) -> str:
    return date.fromisoformat(raw).strftime("%-d %b %Y")


def git_commit(root: Path) -> str:
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha and re.fullmatch(r"[a-f0-9]{40}", env_sha):
        return env_sha
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if re.fullmatch(r"[a-f0-9]{40}", value) else "local"


def build(root: Path, output: Path, repo_url: str, site_url: str) -> None:
    data = validate_progress(root / "data/progress.json")
    template_root = root / "site/templates"
    partial_root = template_root / "partials"

    def partial(name: str, context: dict[str, object]) -> str:
        return fill(read(partial_root / f"{name}.html"), context)

    def badge(item_state: str) -> str:
        return partial("state-badge", {"STATE": item_state, "STATE_LABEL": STATE_LABELS[item_state]})

    milestone_items: list[str] = []
    for item in data["milestones"]:
        pips = "".join(partial("pip", {"PIP_STATE": "pass" if index < item["passed"] else "open"}) for index in range(item["total"]))
        milestone_items.append(partial("milestone", {
            "ID": item["id"], "NAME": item["name"], "STATE": item["state"], "STATE_BADGE": badge(item["state"]),
            "SUMMARY": item["summary"], "PASSED": item["passed"], "TOTAL": item["total"], "CHECK_PIPS": pips,
            "EVIDENCE_AT": item["evidence_at"], "EVIDENCE_AT_LABEL": format_timestamp(item["evidence_at"]),
        }))

    verified = [partial("ledger-item", {"TEXT": item["summary"], "SOURCE": f"{STATE_LABELS[item['state']]} · {format_date(item['date'])}"}) for item in data["updates"] if item["state"].startswith("verified_") or item["state"] == "complete"]
    hypotheses = [partial("ledger-item", {"TEXT": item["text"], "SOURCE": item["source"]}) for item in data.get("hypotheses", [])]
    blocked = [partial("ledger-item", {"TEXT": item["summary"], "SOURCE": f"Milestone · {item['name']}"}) for item in data["milestones"] if item["state"] == "blocked"]
    blocked += [partial("ledger-item", {"TEXT": item["needs"], "SOURCE": f"Workstream · {item['name']}"}) for item in data["workstreams"] if item["state"] == "blocked"]

    workstreams = [partial("workstream", {"ID": item["id"], "NAME": item["name"], "STATE_BADGE": badge(item["state"]), "NEEDS": item["needs"], "SKILLS": " · ".join(item["skills"])}) for item in data["workstreams"]]
    updates = [partial("update", {"DATE": item["date"], "DATE_LABEL": format_date(item["date"]), "STATE_BADGE": badge(item["state"]), "TITLE": item["title"], "SUMMARY": item["summary"]}) for item in sorted(data["updates"], key=lambda value: value["date"], reverse=True)]
    coverage = [partial("coverage-row", {"FAMILY": item["family"], "MODELS": ", ".join(item["models"]), "BUILDS": ", ".join(item["builds"]), "CONTRIBUTORS": item["contributors"], "LEVEL": item["level"].replace("_", " ").title()}) for item in data["coverage"]]
    workstream_names = {item["id"]: item["name"] for item in data["workstreams"]}
    requests = [partial("request", {"ID": item["id"], "TITLE": item["title"], "DETAIL": item["detail"], "SAFETY": item["safety"], "WORKSTREAM_ID": item["workstream"], "WORKSTREAM_NAME": workstream_names[item["workstream"]]}) for item in data.get("requests", [])]

    def items_or_empty(items: list[str], sentence: str, row: bool = False) -> str:
        return "\n".join(items) if items else partial("empty-row" if row else "empty", {"TEXT": sentence})

    generated = datetime.now(timezone.utc).replace(microsecond=0)
    generated_raw = generated.isoformat().replace("+00:00", "Z")
    commit = git_commit(root)
    commit_short = commit[:7] if commit != "local" else "local"
    commit_url = f"{repo_url}/commit/{commit}" if commit != "local" else repo_url
    checks_passed = sum(item["passed"] for item in data["milestones"])
    checks_total = sum(item["total"] for item in data["milestones"])
    counts = data["counts"]
    context = {
        "PROJECT_NAME": data["project"]["name"], "PROJECT_TAGLINE": data["project"]["tagline"],
        "GOAL_SUMMARY": data["goal"]["summary"], "CURRENT_TRUTH": data["goal"]["current_truth"],
        "REFERENCE_TARGET": data["goal"]["reference_target"], "REFERENCE_BUILD": data["goal"]["reference_build"],
        "CHECKS_PASSED": checks_passed, "CHECKS_TOTAL": checks_total,
        "MILESTONES_COMPLETE": sum(1 for item in data["milestones"] if item["state"] == "complete"),
        "MILESTONES_TOTAL": len(data["milestones"]),
        "COUNT_PHYSICAL_LINUX_BOOTS": counts["physical_linux_boots"],
        "COUNT_UNTETHERED_COLD_BOOTS": counts["untethered_cold_boots"],
        "COUNT_INSTALLED_SYSTEMS": counts["installed_systems"], "COUNT_CONTRIBUTOR_DEVICES": counts["contributor_devices"],
        "UPDATED_AT": data["project"]["updated_at"], "UPDATED_AT_LABEL": format_timestamp(data["project"]["updated_at"]),
        "GENERATED_AT": generated_raw, "GENERATED_AT_LABEL": format_timestamp(generated_raw),
        "COMMIT_SHORT": commit_short, "COMMIT_URL": commit_url, "REPO_URL": repo_url,
        "SITE_URL": site_url, "SOCIAL_IMAGE_URL": f"{site_url.rstrip('/')}/assets/social-card.png",
        "LIVE_WORK_URL": f"{repo_url}/issues", "CONTRIBUTE_URL": f"{repo_url}/blob/main/CONTRIBUTING.md",
        "SECURITY_URL": f"{repo_url}/security/policy", "MILESTONE_ITEMS": "\n".join(milestone_items),
        "LEDGER_VERIFIED_ITEMS": items_or_empty(verified, "No verified updates recorded yet."),
        "LEDGER_HYPOTHESIS_ITEMS": items_or_empty(hypotheses, "No hypotheses recorded yet."),
        "LEDGER_BLOCKED_ITEMS": items_or_empty(blocked, "No blocked work recorded."),
        "WORKSTREAM_ITEMS": items_or_empty(workstreams, "No workstreams recorded."),
        "UPDATE_ITEMS": items_or_empty(updates, "No updates recorded yet."),
        "COVERAGE_ROWS": items_or_empty(coverage, "No device coverage recorded yet.", row=True),
        "REQUEST_ITEMS": items_or_empty(requests, "No contribution requests are open."),
    }

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / "index.html").write_text(fill(read(template_root / "index.html"), context), encoding="utf-8")
    shutil.copytree(root / "site/assets", output / "assets")
    shutil.copytree(root / "schemas", output / "schemas")
    (output / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    (output / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{html.escape(site_url)}</loc><lastmod>{data["project"]["updated_at"][:10]}</lastmod></url></urlset>\n', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--repo-url", default="https://github.com/baney75/omarchy-on-ipad")
    parser.add_argument("--site-url", default="https://baney75.github.io/omarchy-on-ipad/")
    args = parser.parse_args()
    build(args.root.resolve(), args.output.resolve(), args.repo_url.rstrip("/"), args.site_url)
    print(f"site build: PASS ({args.output.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
