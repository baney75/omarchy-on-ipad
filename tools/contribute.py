#!/usr/bin/env python3
"""Prepare, check, and plan the submission of a public contribution without touching the network.

Subcommands:
  lanes              list contribution lanes, their policies, and their checks
  new                scaffold data/contributions/<id>.json with hashed evidence
  check              validate a record in the contributor lane and scan it for private data
  pr-body            print a pull-request description for a checked record
  submit-plan        print the git and gh commands to open the pull request yourself
  research new       scaffold a bounded research task file
  research check     validate a research task (--ready before work, --final before submission)
  research preflight evaluate the model suitability preflight; exit 2 when blocked
  research prompt    print the starter prompt filled from a task file

This tool never runs git, gh, a model, or any experiment, never reads credentials, and never merges.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import contract  # noqa: E402
import research  # noqa: E402
import validate  # noqa: E402
from public_surface import PRIVATE_PATTERNS, EVIDENCE_PRIVATE_PATTERNS  # noqa: E402

UPSTREAM = "baney75/omarchy-on-ipad"
EXTRA_PATTERNS = EVIDENCE_PRIVATE_PATTERNS
TEXT_SUFFIXES = {".txt", ".json", ".md", ".csv", ".log"}
PROMPT_START = "<!-- prompt:start -->"
PROMPT_END = "<!-- prompt:end -->"


class CliError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def progress(root: Path) -> dict:
    return validate.validate_progress(root / "data/progress.json")


def safe_new_file(root: Path, relative: str, allowed_prefix: tuple[str, ...]) -> Path:
    """A new file inside the repository, under an allowed prefix, with no symlinks and no overwrite."""
    if relative.startswith("/") or "\\" in relative or any(part in {"", ".", ".."} or part.startswith(".") for part in Path(relative).parts):
        raise CliError(f"unsafe output path: {relative}")
    if Path(relative).parts[: len(allowed_prefix)] != allowed_prefix:
        raise CliError(f"output must be under {'/'.join(allowed_prefix)}/")
    root = root.resolve()
    walk = root
    for part in Path(relative).parts:
        walk = walk / part
        if walk.is_symlink():
            raise CliError(f"refusing symbolic link in output path: {relative}")
    target = root / relative
    try:
        target.resolve().relative_to(root)
    except ValueError as exc:
        raise CliError(f"output escapes the repository: {relative}") from exc
    if target.exists():
        raise CliError(f"refusing to overwrite existing file: {relative}")
    return target


def record_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path)
    if path.is_symlink():
        raise CliError("refusing a symbolic-link record")
    resolved = path.resolve()
    folder = (root / "data/contributions").resolve()
    if resolved.parent != folder or resolved.suffix != ".json":
        raise CliError("record must be data/contributions/<id>.json")
    if not resolved.is_file():
        raise CliError(f"record not found: {raw}")
    return resolved


def privacy_scan(root: Path, record: dict, record_file: Path) -> list[str]:
    findings = []
    files = [record_file] + [root / item["path"] for item in record["evidence"]]
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in {**PRIVATE_PATTERNS, **EXTRA_PATTERNS}.items():
            if pattern.search(body):
                findings.append(f"{path.relative_to(root)}: contains {label}")
    return findings


def cmd_lanes(args) -> int:
    if args.json:
        print(contract.dumps(contract.LANES), end="")
        return 0
    for lane in contract.LANES:
        print(f"{lane['id']}: {lane['title']}")
        print(f"  model: {lane['model_requirement']}")
        print(f"  read: {', '.join(lane['policies'])}")
        for step in lane["start"]:
            print(f"  start: {step}")
        for command in lane["validation"]:
            print(f"  check: {command}")
    return 0


def cmd_new(args) -> int:
    root = args.root
    data = progress(root)
    evidence = []
    for spec in args.evidence:
        if ":" not in spec:
            raise CliError(f"evidence must be kind:path, got {spec!r}")
        kind, raw_path = spec.split(":", 1)
        if kind not in validate.EVIDENCE_KINDS:
            raise CliError(f"evidence kind must be one of {sorted(validate.EVIDENCE_KINDS)}")
        resolved = validate.evidence_file(root, raw_path, args.contributor, f"evidence {raw_path}")
        evidence.append({"kind": kind, "path": raw_path, "sha256": validate.sha256_file(resolved)})
    if not evidence:
        raise CliError("at least one --evidence kind:path is required")
    record = {
        "$schema": "../../schemas/contribution.schema.json",
        "id": args.id,
        "status": "submitted",
        "contributor": args.contributor,
        "agent": args.agent,
        "device": {"model": args.model, "board": args.board, "os_build": args.os_build},
        "workstream": args.workstream,
        "claim": args.claim,
        "evidence": evidence,
        "safety": dict(validate.READ_ONLY_SAFETY),
        "recorded_at": now(),
    }
    if not re.fullmatch(r"[a-z0-9-]{3,80}", args.id):
        raise CliError("id must be 3 to 80 lowercase letters, digits, or dashes")
    target = safe_new_file(root, f"data/contributions/{args.id}.json", ("data", "contributions"))
    body = json.dumps(record, indent=2) + "\n"
    target.write_text(body, encoding="utf-8")
    try:
        validate.validate_contribution(target, {item["id"] for item in data["workstreams"]}, root, submission=True, progress=data)
    except validate.ValidationError:
        target.unlink()
        raise
    print(f"wrote {target.relative_to(root)}; next: python3 tools/contribute.py check {target.relative_to(root)}")
    return 0


def checked_record(root: Path, raw: str) -> tuple[Path, dict]:
    path = record_path(root, raw)
    data = progress(root)
    record = validate.validate_contribution(path, {item["id"] for item in data["workstreams"]}, root, submission=True, progress=data)
    findings = privacy_scan(root, record, path)
    if findings:
        raise CliError("private data found; remove it before submitting:\n- " + "\n- ".join(findings))
    return path, record


def cmd_check(args) -> int:
    path, record = checked_record(args.root, args.record)
    print(f"{path.relative_to(args.root)}: PASS (contributor lane, status submitted, {len(record['evidence'])} evidence file(s) hash-matched, privacy scan clean)")
    print("next: make check && make build, then python3 tools/contribute.py submit-plan " + str(path.relative_to(args.root)))
    return 0


def pr_body(record: dict) -> str:
    device = record["device"]
    evidence = "\n".join(f"- `{item['path']}` ({item['kind']}) sha256 `{item['sha256']}`" for item in record["evidence"])
    return f"""## What changed

Adds contribution record `{record['id']}` in the `{record['workstream']}` workstream.

{record['claim']}

## Evidence and scope

- Device: `{device['model']}` / `{device['board']}` / `{device['os_build']}`
- Status on submission: `submitted` (a maintainer review sets any reviewed state)

{evidence}

## Agent disclosure

{record['agent']}

## Checked by tools/contribute.py check

- Schema, filename, read-only safety flags, and evidence hashes match.
- Privacy scan found no identifiers, credentials, local paths, or private host labels.

## Safety

- [ ] No private identifier, credential, local path, private hostname, signing material, or copyrighted firmware is included.
- [ ] No malformed physical input, storage write, reboot/recovery action, persistence mechanism, or exploit payload is introduced through the public lane.
- [ ] The claim uses the lowest state its evidence proves.
- [ ] Upstream sources and licenses are credited.
- [ ] `make check` passes.
- [ ] `make build` passes.

A human maintainer reviews this pull request. Nothing here merges automatically.
"""


def cmd_pr_body(args) -> int:
    _, record = checked_record(args.root, args.record)
    print(pr_body(record), end="")
    return 0


def cmd_submit_plan(args) -> int:
    path, record = checked_record(args.root, args.record)
    rel = str(path.relative_to(args.root))
    branch = f"contrib/{record['id']}"
    files = [rel] + [item["path"] for item in record["evidence"]]
    for item in record["evidence"]:
        if item["kind"] == "research-task":
            task = validate.load_json(args.root / item["path"])
            files.extend(row["path"] for row in task["result"]["evidence"] if not row["path"].startswith("https://"))
    files = list(dict.fromkeys(files))
    body = f'"${{TMPDIR:-/tmp}}/omarchy-pr-{record["id"]}.md"'
    q = shlex.quote
    lines = [
        "# Run these yourself in a clone of your own fork. This tool ran none of them.",
        "# gh uses the login you already have; this project never asks for a token or password.",
        "make check && make build",
        f"git switch -c {q(branch)}",
        "git add -- " + " ".join(q(item) for item in files),
        f"git commit -m {q('Add contribution record ' + record['id'])}",
        f"python3 tools/contribute.py pr-body {q(rel)} > {body}",
        f"git push --set-upstream origin {q(branch)}",
        f"gh pr create --repo {UPSTREAM} --base main --head {q(record['contributor'] + ':' + branch)} --title {q('Contribution: ' + record['id'])} --body-file {body}",
        "# A maintainer reviews the pull request. Do not merge it yourself.",
    ]
    print("\n".join(lines))
    return 0


def scaffold_task(args, data: dict) -> dict:
    r = research.PLACEHOLDER
    agent = {"kind": args.agent_kind, "provider": args.provider, "model_id": args.model_id,
             "reasoning": args.reasoning, "used_on": now()[:10], "representative_checks": []}
    if args.agent_kind in {"local", "local_modified"}:
        agent.update({key: f"{r} {key}" for key in ("upstream_model", "revision", "quantization", "license", "provenance")})
        agent["limitations"] = f"{r} task limitations; removing refusals is not evidence of accuracy or trust"
        agent["representative_checks"] = [f"{r} {name} evidence" for name in sorted(research.REQUIRED_TASK_CHECKS)]
    return {
        "$schema": "../../../schemas/research-task.schema.json",
        "schema_version": research.SCHEMA_VERSION,
        "kind": "research-task",
        "id": args.id,
        "created_at": now(),
        "sensitivity": "public",
        "model_preflight": {
            "identity_source": "unknown",
            "identity_evidence": f"{r} where the provider and model id came from (runtime metadata, or the operator's declaration). Never the model's own guess.",
            "category": "unknown",
            "model_card": None,
            "task_checks": [{"check": name, "outcome": "not_run", "evidence": f"{r} how this check was run and what it showed"} for name in sorted(research.REQUIRED_TASK_CHECKS)],
            "verdict": "unverified",
            "assessed_at": None,
            "limitations": f"{r} known limits of this model for this task",
            "scope": research.PREFLIGHT_SCOPE,
        },
        "target": {"model": args.model, "board": args.board, "os_build": args.os_build, "scope": args.scope},
        "workstream": args.workstream,
        "blocker": {"milestone": args.milestone, "prerequisite": next(item["summary"] for item in data["milestones"] if item["id"] == args.milestone)},
        "question": args.question,
        "falsifier": args.falsifier,
        "pass_criteria": f"{r} the observable result that answers yes",
        "fail_criteria": f"{r} the observable result that answers no",
        "expected_evidence": f"{r} the evidence that would change a decision",
        "intake": {key: False for key in sorted(research.INTAKE_KEYS)},
        "prior_work": [
            {"kind": "policy", "ref": "AGENTS.md", "summary": f"{r} what applies to this task"},
            {"kind": "progress", "ref": "data/progress.json", "summary": f"{r} current milestone and blocker"},
        ],
        "priority": {"blocker_relevance": 0, "reachability": 0, "evidence_strength": 0, "information_gain": 0, "cost": 3, "rationale": f"{r} why this question, now, over the alternatives"},
        "subquestions": [{"id": f"q{index}", "text": f"{r} sub-question {index}", "state": "open", "sources": []} for index in (1, 2, 3)],
        "hypotheses": [{"id": "h1", "text": f"{r} one testable hypothesis", "state": "open", "experiment": None, "sources": [], "reopened_with": []}],
        "agent": agent,
        "allowed_tools": ["read repository files", "read cited public sources", "offline local analysis within the budget"],
        "allowed_artifacts": ["public source code and documentation at pinned revisions", "sanitized repository records"],
        "exclusions": sorted(research.REQUIRED_EXCLUSIONS),
        "budget": dict(research.DEFAULT_BUDGET),
        "checkpoints": [],
        "sources": [],
        "result": {"state": "open", "claim": "", "evidence": [], "limits": "", "contradictions": [], "failed_avenues": [], "next_check": ""},
    }


def cmd_research_new(args) -> int:
    root = args.root
    data = progress(root)
    if args.milestone not in {item["id"] for item in data["milestones"]}:
        raise CliError("unknown milestone; see data/progress.json")
    if not re.fullmatch(r"[a-z0-9-]{3,80}", args.id) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", args.contributor):
        raise CliError("id must be 3 to 80 lowercase letters, digits, or dashes, and contributor a GitHub handle")
    relative = args.output or f"contributions/{args.contributor}/research/{args.id}.json"
    target = safe_new_file(root, relative, ("contributions", args.contributor))
    task = scaffold_task(args, data)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    try:
        research.validate_task(target, data, root=root)
    except validate.ValidationError:
        target.unlink()
        raise
    print(f"wrote {relative}")
    print("first step: run the model suitability preflight, then fill every REPLACE: field before research.")
    print(f"next: python3 tools/contribute.py research preflight {relative}")
    return 0


def task_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_symlink() or not path.is_file() or path.suffix != ".json":
        raise CliError(f"research task must be an existing .json file: {raw}")
    return path


def cmd_research_check(args) -> int:
    task = research.validate_task(task_path(args.task), progress(args.root), ready=args.ready or args.final, final=args.final, root=args.root)
    eligible, message = research.preflight_gate(task)
    mode = "final" if args.final else "ready" if args.ready else "structure"
    print(f"{args.task}: PASS ({mode})")
    print(f"preflight: {message}")
    if args.final:
        print("complete" if research.is_complete(task) else f"recorded outcome {task['result']['state']!r}: not a completion")
    return 0


def cmd_research_preflight(args) -> int:
    task = research.validate_task(task_path(args.task), progress(args.root), root=args.root)
    eligible, message = research.preflight_gate(task)
    print(message)
    return 0 if eligible else 2


def prompt_template(root: Path) -> str:
    body = (root / "docs/RESEARCH-PROMPT.md").read_text(encoding="utf-8")
    try:
        start = body.index(PROMPT_START) + len(PROMPT_START)
        end = body.index(PROMPT_END, start)
    except ValueError as exc:
        raise CliError("docs/RESEARCH-PROMPT.md lacks its prompt markers") from exc
    block = body[start:end].strip()
    return re.sub(r"^```text\n|\n```$", "", block)


def cmd_research_prompt(args) -> int:
    task = research.validate_task(task_path(args.task), progress(args.root), root=args.root)
    target = task["target"]
    budget = task["budget"]
    values = {
        "TASK_FILE": args.task, "TASK_ID": task["id"], "MODEL": target["model"], "BOARD": target["board"],
        "OS_BUILD": target["os_build"], "SCOPE": target["scope"], "QUESTION": task["question"],
        "FALSIFIER": task["falsifier"], "MILESTONE": task["blocker"]["milestone"],
        "MAX_READS": str(budget["max_source_reads"]), "MAX_MINUTES": str(budget["max_minutes"]),
        "MAX_COMMAND_SECONDS": str(budget["max_command_seconds"]), "MAX_OUTPUT_BYTES": str(budget["max_output_bytes"]),
        "CHECKPOINT_READS": str(budget["checkpoint_every_reads"]), "SWITCH_MESSAGE": research.SWITCH_MESSAGE,
    }
    text = re.sub(r"\[\[([A-Z_]+)\]\]", lambda m: values.get(m.group(1), m.group(0)), prompt_template(args.root))
    print(text)
    return 0


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    sub = top.add_subparsers(dest="command", required=True)

    lanes = sub.add_parser("lanes", help="list contribution lanes")
    lanes.add_argument("--json", action="store_true")
    lanes.set_defaults(func=cmd_lanes)

    new = sub.add_parser("new", help="scaffold a contribution record")
    for name in ("id", "contributor", "workstream", "model", "board", "os-build", "agent", "claim"):
        new.add_argument(f"--{name}", required=True)
    new.add_argument("--evidence", action="append", default=[], help="kind:path, repeatable")
    new.set_defaults(func=cmd_new)

    for name, func, text in (("check", cmd_check, "validate a record"), ("pr-body", cmd_pr_body, "print a PR description"), ("submit-plan", cmd_submit_plan, "print submission commands")):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("record")
        cmd.set_defaults(func=func)

    res = sub.add_parser("research", help="bounded research tasks").add_subparsers(dest="research_command", required=True)
    rnew = res.add_parser("new", help="scaffold a research task")
    for name in ("id", "contributor", "workstream", "milestone", "model", "board", "os-build", "scope", "question", "falsifier"):
        rnew.add_argument(f"--{name}", required=True)
    rnew.add_argument("--agent-kind", choices=sorted(research.AGENT_KINDS), default="cloud")
    rnew.add_argument("--provider", default="unknown")
    rnew.add_argument("--model-id", default="unknown")
    rnew.add_argument("--reasoning", default="unknown")
    rnew.add_argument("--output")
    rnew.set_defaults(func=cmd_research_new)
    rcheck = res.add_parser("check", help="validate a research task")
    rcheck.add_argument("task")
    rcheck.add_argument("--ready", action="store_true", help="intake, preflight, and plan are complete")
    rcheck.add_argument("--final", action="store_true", help="a terminal result is recorded")
    rcheck.set_defaults(func=cmd_research_check)
    for name, func in (("preflight", cmd_research_preflight), ("prompt", cmd_research_prompt)):
        cmd = res.add_parser(name)
        cmd.add_argument("task")
        cmd.set_defaults(func=func)
    return top


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    args.root = args.root.resolve()
    try:
        return args.func(args)
    except (CliError, validate.ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
