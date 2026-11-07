#!/usr/bin/env python3
"""Strict, dependency-free validation for public progress and contribution data."""

from __future__ import annotations

import argparse
import hashlib
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
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
CONTRIBUTION_STATUSES = {"submitted", "verified_offline", "verified_physical", "rejected"}
REVIEWED_STATUSES = CONTRIBUTION_STATUSES - {"submitted"}
EVIDENCE_KINDS = {"command-output", "source-citation", "screenshot", "test-report", "research-task"}
EVIDENCE_SUFFIXES = {".txt", ".json", ".md", ".csv", ".log", ".png"}
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
READ_ONLY_SAFETY = {"read_only": True, "malformed_input": False, "storage_write": False, "reboot_or_recovery": False}
INSTALL_STATES = {"unavailable", "available"}


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


def maintainers(root: Path = ROOT) -> set[str]:
    """Handles named in CODEOWNERS. Only they may record a review."""
    path = root / ".github/CODEOWNERS"
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {handle.lower() for handle in re.findall(r"@([A-Za-z0-9-]{1,39})\b", body)}


def evidence_file(root: Path, raw_path: str, contributor: str, where: str) -> Path:
    """Resolve one evidence path, refusing anything outside the public evidence folders."""
    if "\\" in raw_path or raw_path.startswith("/") or raw_path != raw_path.strip():
        fail(f"{where}: must be a plain repository-relative path")
    relative = Path(raw_path)
    parts = relative.parts
    if not parts or any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        fail(f"{where}: dot segments and hidden files are not accepted")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", raw_path):
        fail(f"{where}: unexpected characters in path")
    if parts[0] == "contributions":
        if len(parts) < 3 or parts[1].lower() != contributor.lower():
            fail(f"{where}: contribution evidence must live under contributions/<contributor>/")
    elif parts[0] != "docs" or len(parts) < 2:
        fail(f"{where}: must be under contributions/<contributor>/ or docs/")
    if relative.suffix.lower() not in EVIDENCE_SUFFIXES:
        fail(f"{where}: evidence type must be one of {sorted(EVIDENCE_SUFFIXES)}")
    root = root.resolve()
    candidate = root / relative
    walk = root
    for part in parts:
        walk = walk / part
        if walk.is_symlink():
            fail(f"{where}: symbolic links are not accepted")
    try:
        candidate.resolve().relative_to(root)
    except ValueError:
        fail(f"{where}: escapes the repository")
    if not candidate.is_file():
        fail(f"{where}: evidence file does not exist")
    if candidate.stat().st_size > MAX_EVIDENCE_BYTES:
        fail(f"{where}: evidence file exceeds {MAX_EVIDENCE_BYTES} bytes")
    return candidate


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_review(review: object, data: dict, where: str, allowed_reviewers: set[str]) -> None:
    if not isinstance(review, dict):
        fail(f"{where}: expected object")
    exact_keys(review, {"reviewer", "reviewed_at", "pull_request", "summary"}, set(), where)
    reviewer = review["reviewer"]
    if not isinstance(reviewer, str) or not HANDLE_RE.fullmatch(reviewer):
        fail(f"{where}.reviewer: expected GitHub handle")
    if reviewer.lower() not in allowed_reviewers:
        fail(f"{where}.reviewer: must be a maintainer named in .github/CODEOWNERS")
    if reviewer.lower() == data["contributor"].lower():
        fail(f"{where}.reviewer: a contributor cannot review their own record")
    reviewed_at = timestamp(review["reviewed_at"], f"{where}.reviewed_at")
    if parse_time(reviewed_at) < parse_time(data["recorded_at"]):
        fail(f"{where}.reviewed_at: review cannot predate the record")
    pull = review["pull_request"]
    if isinstance(pull, bool) or not isinstance(pull, int) or pull < 1:
        fail(f"{where}.pull_request: expected positive pull-request number")
    text(review["summary"], f"{where}.summary", 20, 600)


def parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def validate_contribution(path: Path, workstream_ids: set[str], root: Path = ROOT, allowed_reviewers: set[str] | None = None, submission: bool = False, progress: dict | None = None) -> dict:
    """Validate one record. submission=True applies the stricter contributor lane: unreviewed only."""
    if allowed_reviewers is None:
        allowed_reviewers = maintainers(root)
    data = load_json(path)
    exact_keys(data, {"id", "status", "contributor", "agent", "device", "workstream", "claim", "evidence", "safety", "recorded_at"}, {"$schema", "review"}, str(path))
    contribution_id = identifier(data["id"], f"{path}.id")
    if len(contribution_id) < 3:
        fail(f"{path}.id: expected at least 3 characters")
    if contribution_id != path.stem:
        fail(f"{path}: filename must equal id")
    if data["status"] not in CONTRIBUTION_STATUSES:
        fail(f"{path}.status: invalid status")
    if not isinstance(data["contributor"], str) or not HANDLE_RE.fullmatch(data["contributor"]):
        fail(f"{path}.contributor: expected GitHub handle")
    text(data["agent"], f"{path}.agent", 1, 120)
    device = data["device"]
    if not isinstance(device, dict):
        fail(f"{path}.device: expected object")
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
    timestamp(data["recorded_at"], f"{path}.recorded_at")
    evidence = data["evidence"]
    if not isinstance(evidence, list) or not evidence:
        fail(f"{path}.evidence: expected non-empty array")
    seen_paths: set[str] = set()
    for index, item in enumerate(evidence):
        where = f"{path}.evidence[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"kind", "path", "sha256"}, set(), where)
        if item["kind"] not in EVIDENCE_KINDS:
            fail(f"{where}.kind: invalid")
        raw_path = text(item["path"], f"{where}.path", 1, 240)
        if raw_path in seen_paths:
            fail(f"{where}.path: duplicate evidence path")
        seen_paths.add(raw_path)
        if not SHA_RE.fullmatch(text(item["sha256"], f"{where}.sha256")):
            fail(f"{where}.sha256: invalid")
        resolved = evidence_file(root, raw_path, data["contributor"], f"{where}.path")
        if sha256_file(resolved) != item["sha256"]:
            fail(f"{where}.sha256: does not match the evidence file")
        if item["kind"] == "research-task":
            if resolved.suffix != ".json":
                fail(f"{where}: a research-task evidence file is JSON")
            import research  # local import: research.py builds on this module
            research.validate_task(resolved, progress or validate_progress(root / "data/progress.json"), ready=True, final=True, root=root)
    safety = data["safety"]
    if not isinstance(safety, dict):
        fail(f"{path}.safety: expected object")
    exact_keys(safety, set(READ_ONLY_SAFETY), set(), f"{path}.safety")
    if safety != READ_ONLY_SAFETY or any(type(safety[key]) is not bool for key in safety):
        fail(f"{path}.safety: public contribution records must use the read-only lane")
    free_text = [data["agent"], data["claim"]] + ([data["review"]["summary"]] if isinstance(data.get("review"), dict) and isinstance(data["review"].get("summary"), str) else [])
    if any("{{" in value or "}}" in value for value in free_text):
        fail(f"{path}: template braces are not accepted in free text")
    has_review = "review" in data
    if data["status"] == "submitted":
        if has_review:
            fail(f"{path}.review: an unreviewed record must not carry a review; maintainers add it")
    else:
        if submission:
            fail(f"{path}.status: contributors submit with status 'submitted'; only a maintainer review sets {data['status']!r}")
        if not has_review:
            fail(f"{path}.review: status {data['status']!r} requires a maintainer review")
        validate_review(data["review"], data, f"{path}.review", allowed_reviewers)
    return data


def validate_contributions(root: Path, workstream_ids: set[str], progress: dict | None = None) -> list[dict]:
    allowed = maintainers(root)
    records = []
    seen: set[str] = set()
    for path in sorted((root / "data/contributions").glob("*.json")):
        record = validate_contribution(path, workstream_ids, root, allowed, progress=progress)
        if record["id"] in seen:
            fail(f"{path}: duplicate id")
        seen.add(record["id"])
        records.append(record)
    return records


def https_url(value: object, where: str, prefix: str) -> str:
    raw = text(value, where, 10, 500)
    if not raw.startswith(prefix) or any(ch in raw for ch in " \"'<>`"):
        fail(f"{where}: must be an https URL under {prefix}")
    return raw


RELEASE_URL_PREFIX = "https://github.com/baney75/omarchy-on-ipad/releases/"


def validate_installation(path: Path, progress: dict, records: list[dict]) -> dict:
    """The installation record stays unavailable until reviewed physical evidence supports a release."""
    data = load_json(path)
    exact_keys(data, {"schema_version", "state", "summary", "requirements", "releases", "updated_at"}, {"$schema"}, str(path))
    if data["schema_version"] != 1:
        fail("installation.schema_version: expected 1")
    if data["state"] not in INSTALL_STATES:
        fail("installation.state: invalid")
    text(data["summary"], "installation.summary", 20, 600)
    timestamp(data["updated_at"], "installation.updated_at")
    requirements = data["requirements"]
    if not isinstance(requirements, list) or not requirements:
        fail("installation.requirements: expected non-empty array")
    required_ids = {"model-build-compatibility", "artifact-hashes", "provenance", "recovery-verified", "rollback-verified", "human-review", "security-review"}
    seen: set[str] = set()
    for index, item in enumerate(requirements):
        where = f"installation.requirements[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"id", "title", "detail"}, set(), where)
        seen.add(identifier(item["id"], f"{where}.id"))
        text(item["title"], f"{where}.title", 3, 120)
        text(item["detail"], f"{where}.detail", 20, 600)
    if not required_ids <= seen:
        fail(f"installation.requirements: missing {sorted(required_ids - seen)}")
    releases = data["releases"]
    if not isinstance(releases, list):
        fail("installation.releases: expected array")
    if data["state"] == "unavailable":
        if releases:
            fail("installation.releases: must be empty while installation is unavailable")
        if "not" not in data["summary"].lower():
            fail("installation.summary: must state that installation is not available")
        return data
    if not releases:
        fail("installation.state: 'available' requires at least one release")
    counts = progress["counts"]
    milestones = {item["id"]: item for item in progress["milestones"]}
    if counts["installed_systems"] < 1 or counts["untethered_cold_boots"] < 1:
        fail("installation.state: progress records no installed system and untethered cold boot")
    if any(item["state"] != "complete" for item in progress["milestones"]):
        fail("installation.state: every milestone must be complete before a release is offered")
    if "untethered" not in milestones:
        fail("installation.state: progress lacks the untethered milestone")
    physical = {item["id"]: item for item in records if item["status"] == "verified_physical"}
    for index, release in enumerate(releases):
        validate_release(release, f"installation.releases[{index}]", physical)
    return data


def validate_release(release: object, where: str, physical: dict[str, dict]) -> None:
    if not isinstance(release, dict):
        fail(f"{where}: expected object")
    exact_keys(release, {"id", "version", "published_at", "release_url", "compatibility", "artifacts", "provenance", "verification", "review"}, set(), where)
    identifier(release["id"], f"{where}.id")
    text(release["version"], f"{where}.version", 1, 40)
    timestamp(release["published_at"], f"{where}.published_at")
    https_url(release["release_url"], f"{where}.release_url", RELEASE_URL_PREFIX)
    compatibility = release["compatibility"]
    if not isinstance(compatibility, list) or not compatibility:
        fail(f"{where}.compatibility: expected non-empty array of exact model/board/build entries")
    targets: set[tuple[str, str, str]] = set()
    for c_index, entry in enumerate(compatibility):
        c_where = f"{where}.compatibility[{c_index}]"
        if not isinstance(entry, dict):
            fail(f"{c_where}: expected object")
        exact_keys(entry, {"model", "board", "os_build"}, set(), c_where)
        if not MODEL_RE.fullmatch(text(entry["model"], f"{c_where}.model")):
            fail(f"{c_where}.model: invalid")
        if not BOARD_RE.fullmatch(text(entry["board"], f"{c_where}.board")):
            fail(f"{c_where}.board: invalid")
        if not BUILD_RE.fullmatch(text(entry["os_build"], f"{c_where}.os_build")):
            fail(f"{c_where}.os_build: invalid")
        targets.add((entry["model"], entry["board"], entry["os_build"]))
    artifacts = release["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        fail(f"{where}.artifacts: expected non-empty array")
    for a_index, artifact in enumerate(artifacts):
        a_where = f"{where}.artifacts[{a_index}]"
        if not isinstance(artifact, dict):
            fail(f"{a_where}: expected object")
        exact_keys(artifact, {"name", "url", "sha256", "size_bytes"}, set(), a_where)
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", text(artifact["name"], f"{a_where}.name")):
            fail(f"{a_where}.name: invalid")
        https_url(artifact["url"], f"{a_where}.url", RELEASE_URL_PREFIX + "download/")
        if not SHA_RE.fullmatch(text(artifact["sha256"], f"{a_where}.sha256")):
            fail(f"{a_where}.sha256: invalid")
        if nonnegative_int(artifact["size_bytes"], f"{a_where}.size_bytes") < 1:
            fail(f"{a_where}.size_bytes: expected positive size")
    provenance = release["provenance"]
    if not isinstance(provenance, dict):
        fail(f"{where}.provenance: expected object")
    exact_keys(provenance, {"source_commit", "build_recipe", "attestation_url"}, set(), f"{where}.provenance")
    if not COMMIT_RE.fullmatch(text(provenance["source_commit"], f"{where}.provenance.source_commit")):
        fail(f"{where}.provenance.source_commit: expected 40-character commit")
    recipe = text(provenance["build_recipe"], f"{where}.provenance.build_recipe", 3, 200)
    if recipe.startswith("/") or ".." in Path(recipe).parts:
        fail(f"{where}.provenance.build_recipe: must be repository-relative")
    https_url(provenance["attestation_url"], f"{where}.provenance.attestation_url", "https://github.com/baney75/omarchy-on-ipad/")
    verification = release["verification"]
    if not isinstance(verification, dict):
        fail(f"{where}.verification: expected object")
    exact_keys(verification, {"install_evidence", "recovery_evidence", "rollback_evidence", "cold_boots"}, set(), f"{where}.verification")
    if nonnegative_int(verification["cold_boots"], f"{where}.verification.cold_boots") < 3:
        fail(f"{where}.verification.cold_boots: at least three untethered cold boots are required")
    for key in ("install_evidence", "recovery_evidence", "rollback_evidence"):
        covered: set[tuple[str, str, str]] = set()
        ids = verification[key]
        if not isinstance(ids, list) or not ids:
            fail(f"{where}.verification.{key}: expected reviewed contribution ids")
        for record_id in ids:
            record = physical.get(record_id) if isinstance(record_id, str) else None
            if record is None:
                fail(f"{where}.verification.{key}: {record_id!r} is not a reviewed verified_physical record")
            target = tuple(record["device"][field] for field in ("model", "board", "os_build"))
            if target not in targets:
                fail(f"{where}.verification.{key}: {record_id} device is outside the release compatibility list")
            covered.add(target)
        if targets - covered:
            fail(f"{where}.verification.{key}: missing physical evidence for compatible targets {sorted(targets - covered)}")
    review = release["review"]
    if not isinstance(review, dict):
        fail(f"{where}.review: expected object")
    exact_keys(review, {"human_reviewer", "security_reviewer", "pull_request", "reviewed_at"}, set(), f"{where}.review")
    human = review["human_reviewer"]
    security = review["security_reviewer"]
    for key, value in (("human_reviewer", human), ("security_reviewer", security)):
        if not isinstance(value, str) or not HANDLE_RE.fullmatch(value):
            fail(f"{where}.review.{key}: expected GitHub handle")
    if human.lower() == security.lower():
        fail(f"{where}.review: human and security review must be done by different people")
    pull = review["pull_request"]
    if isinstance(pull, bool) or not isinstance(pull, int) or pull < 1:
        fail(f"{where}.review.pull_request: expected positive pull-request number")
    timestamp(review["reviewed_at"], f"{where}.review.reviewed_at")


def validate_all(root: Path = ROOT) -> dict:
    progress = validate_progress(root / "data/progress.json")
    workstream_ids = {item["id"] for item in progress["workstreams"]}
    records = validate_contributions(root, workstream_ids, progress)
    installation = validate_installation(root / "data/installation.json", progress, records)
    return {"progress": progress, "contributions": records, "installation": installation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        validate_all(args.root.resolve())
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print("progress, contribution, and installation data: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
