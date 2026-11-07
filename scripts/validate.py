#!/usr/bin/env python3
"""Strict, dependency-free validation for public progress and contribution data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATES = {"blocked", "active", "prepared", "verified_offline", "verified_physical", "complete"}
ID_RE = re.compile(r"^[a-z0-9-]+$")
MODEL_RE = re.compile(r"^iPad\d+,\d+$")
BOARD_RE = re.compile(r"^[A-Z]\d{3,4}AP$")
BUILD_RE = re.compile(r"^\d{2}[A-Z][0-9A-Za-z]+$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")


class ValidationError(ValueError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path}: root must be an object")
    return value


def exact_keys(value: dict, required: set[str], optional: set[str], where: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        fail(f"{where}: missing keys {sorted(missing)}")
    if extra:
        fail(f"{where}: unexpected keys {sorted(extra)}")


def text(value: object, where: str, minimum: int = 1, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        fail(f"{where}: expected string length {minimum}..{maximum}")
    return value


def timestamp(value: object, where: str) -> str:
    raw = text(value, where)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        fail(f"{where}: expected ISO-8601 timestamp")
    if not raw.endswith("Z"):
        fail(f"{where}: timestamp must be UTC and end in Z")
    return raw


def date_string(value: object, where: str) -> str:
    raw = text(value, where)
    try:
        date.fromisoformat(raw)
    except ValueError:
        fail(f"{where}: expected YYYY-MM-DD")
    return raw


def identifier(value: object, where: str) -> str:
    raw = text(value, where, 1, 80)
    if not ID_RE.fullmatch(raw):
        fail(f"{where}: expected lowercase dash-separated id")
    return raw


def nonnegative_int(value: object, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        fail(f"{where}: expected non-negative integer")
    return value


def state(value: object, where: str) -> str:
    raw = text(value, where)
    if raw not in STATES:
        fail(f"{where}: invalid state {raw!r}")
    return raw


def validate_progress(path: Path = ROOT / "data/progress.json") -> dict:
    data = load_json(path)
    exact_keys(data, {"project", "goal", "milestones", "workstreams", "updates", "coverage", "counts"}, {"$schema", "hypotheses", "requests"}, str(path))

    project = data["project"]
    exact_keys(project, {"name", "tagline", "unofficial", "updated_at"}, set(), "project")
    text(project["name"], "project.name")
    text(project["tagline"], "project.tagline")
    if project["unofficial"] is not True:
        fail("project.unofficial: must remain true")
    timestamp(project["updated_at"], "project.updated_at")

    goal = data["goal"]
    exact_keys(goal, {"summary", "current_truth", "reference_target", "reference_build"}, set(), "goal")
    for key in goal:
        text(goal[key], f"goal.{key}")
    if "not" not in goal["current_truth"].lower():
        fail("goal.current_truth: must state the unmet condition explicitly")

    milestones = data["milestones"]
    if not isinstance(milestones, list) or not milestones:
        fail("milestones: expected non-empty array")
    milestone_ids: set[str] = set()
    for index, item in enumerate(milestones):
        where = f"milestones[{index}]"
        exact_keys(item, {"id", "name", "state", "passed", "total", "summary", "evidence_at"}, set(), where)
        item_id = identifier(item["id"], f"{where}.id")
        if item_id in milestone_ids:
            fail(f"{where}.id: duplicate {item_id}")
        milestone_ids.add(item_id)
        text(item["name"], f"{where}.name")
        item_state = state(item["state"], f"{where}.state")
        passed = nonnegative_int(item["passed"], f"{where}.passed")
        total = nonnegative_int(item["total"], f"{where}.total")
        if total < 1 or passed > total:
            fail(f"{where}: require 0 <= passed <= total and total >= 1")
        if item_state == "complete" and passed != total:
            fail(f"{where}: complete requires every check passed")
        text(item["summary"], f"{where}.summary")
        timestamp(item["evidence_at"], f"{where}.evidence_at")

    workstreams = data["workstreams"]
    if not isinstance(workstreams, list) or not workstreams:
        fail("workstreams: expected non-empty array")
    workstream_ids: set[str] = set()
    for index, item in enumerate(workstreams):
        where = f"workstreams[{index}]"
        exact_keys(item, {"id", "name", "state", "needs", "skills"}, set(), where)
        item_id = identifier(item["id"], f"{where}.id")
        if item_id in workstream_ids:
            fail(f"{where}.id: duplicate {item_id}")
        workstream_ids.add(item_id)
        text(item["name"], f"{where}.name")
        state(item["state"], f"{where}.state")
        text(item["needs"], f"{where}.needs")
        if not isinstance(item["skills"], list) or not item["skills"]:
            fail(f"{where}.skills: expected non-empty array")
        for skill in item["skills"]:
            text(skill, f"{where}.skills[]", 1, 80)

    updates = data["updates"]
    if not isinstance(updates, list):
        fail("updates: expected array")
    for index, item in enumerate(updates):
        where = f"updates[{index}]"
        exact_keys(item, {"date", "title", "state", "summary"}, set(), where)
        date_string(item["date"], f"{where}.date")
        text(item["title"], f"{where}.title")
        state(item["state"], f"{where}.state")
        text(item["summary"], f"{where}.summary")

    for index, item in enumerate(data.get("hypotheses", [])):
        where = f"hypotheses[{index}]"
        exact_keys(item, {"text", "source"}, set(), where)
        text(item["text"], f"{where}.text")
        text(item["source"], f"{where}.source")

    request_ids: set[str] = set()
    for index, item in enumerate(data.get("requests", [])):
        where = f"requests[{index}]"
        exact_keys(item, {"id", "title", "detail", "safety", "workstream"}, set(), where)
        item_id = identifier(item["id"], f"{where}.id")
        if item_id in request_ids:
            fail(f"{where}.id: duplicate {item_id}")
        request_ids.add(item_id)
        for key in ("title", "detail", "safety"):
            text(item[key], f"{where}.{key}")
        if identifier(item["workstream"], f"{where}.workstream") not in workstream_ids:
            fail(f"{where}.workstream: unknown workstream")

    coverage = data["coverage"]
    if not isinstance(coverage, list):
        fail("coverage: expected array")
    for index, item in enumerate(coverage):
        where = f"coverage[{index}]"
        exact_keys(item, {"family", "models", "builds", "contributors", "level"}, set(), where)
        text(item["family"], f"{where}.family")
        if not isinstance(item["models"], list) or not item["models"]:
            fail(f"{where}.models: expected non-empty array")
        for model in item["models"]:
            if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
                fail(f"{where}.models: invalid model {model!r}")
        if not isinstance(item["builds"], list) or not item["builds"]:
            fail(f"{where}.builds: expected non-empty array")
        for build in item["builds"]:
            if not isinstance(build, str) or not BUILD_RE.fullmatch(build):
                fail(f"{where}.builds: invalid build {build!r}")
        if nonnegative_int(item["contributors"], f"{where}.contributors") < 1:
            fail(f"{where}.contributors: expected at least one")
        if item["level"] not in {"reported", "reference", "verified_offline", "verified_physical"}:
            fail(f"{where}.level: invalid level")

    counts = data["counts"]
    exact_keys(counts, {"physical_linux_boots", "untethered_cold_boots", "installed_systems", "contributor_devices"}, set(), "counts")
    for key, value in counts.items():
        nonnegative_int(value, f"counts.{key}")
    if counts["contributor_devices"] < sum(row["contributors"] for row in coverage):
        fail("counts.contributor_devices: cannot be lower than coverage contributor total")
    return data


def validate_contribution(path: Path, workstream_ids: set[str]) -> dict:
    data = load_json(path)
    exact_keys(data, {"id", "status", "contributor", "agent", "device", "workstream", "claim", "evidence", "safety", "recorded_at"}, {"$schema"}, str(path))
    contribution_id = identifier(data["id"], f"{path}.id")
    if contribution_id != path.stem:
        fail(f"{path}: filename must equal id")
    if data["status"] not in {"submitted", "verified_offline", "verified_physical", "rejected"}:
        fail(f"{path}.status: invalid status")
    if not isinstance(data["contributor"], str) or not HANDLE_RE.fullmatch(data["contributor"]):
        fail(f"{path}.contributor: expected GitHub handle")
    text(data["agent"], f"{path}.agent", 1, 120)
    device = data["device"]
    exact_keys(device, {"model", "board", "os_build"}, set(), f"{path}.device")
    if not MODEL_RE.fullmatch(text(device["model"], f"{path}.device.model")):
        fail(f"{path}.device.model: invalid")
    if not BOARD_RE.fullmatch(text(device["board"], f"{path}.device.board")):
        fail(f"{path}.device.board: invalid")
    if not BUILD_RE.fullmatch(text(device["os_build"], f"{path}.device.os_build")):
        fail(f"{path}.device.os_build: invalid")
    if identifier(data["workstream"], f"{path}.workstream") not in workstream_ids:
        fail(f"{path}.workstream: unknown workstream")
    text(data["claim"], f"{path}.claim", 20, 1000)
    evidence = data["evidence"]
    if not isinstance(evidence, list) or not evidence:
        fail(f"{path}.evidence: expected non-empty array")
    for index, item in enumerate(evidence):
        where = f"{path}.evidence[{index}]"
        exact_keys(item, {"kind", "path", "sha256"}, set(), where)
        if item["kind"] not in {"command-output", "source-citation", "screenshot", "test-report"}:
            fail(f"{where}.kind: invalid")
        evidence_path = Path(text(item["path"], f"{where}.path"))
        if evidence_path.is_absolute() or ".." in evidence_path.parts or evidence_path.parts[0] not in {"contributions", "docs"}:
            fail(f"{where}.path: must be a repository-relative contribution or docs path")
        if not SHA_RE.fullmatch(text(item["sha256"], f"{where}.sha256")):
            fail(f"{where}.sha256: invalid")
    safety = data["safety"]
    exact_keys(safety, {"read_only", "malformed_input", "storage_write", "reboot_or_recovery"}, set(), f"{path}.safety")
    if safety != {"read_only": True, "malformed_input": False, "storage_write": False, "reboot_or_recovery": False}:
        fail(f"{path}.safety: public contribution records must use the read-only lane")
    timestamp(data["recorded_at"], f"{path}.recorded_at")
    return data


def validate_all(root: Path = ROOT) -> None:
    progress = validate_progress(root / "data/progress.json")
    workstream_ids = {item["id"] for item in progress["workstreams"]}
    for path in sorted((root / "data/contributions").glob("*.json")):
        validate_contribution(path, workstream_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        validate_all(args.root.resolve())
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print("progress and contribution data: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
