#!/usr/bin/env python3
"""Validate bounded research task files (schemas/research-task.schema.json) without dependencies.

A research task is a plan and a log in one JSON file. It never runs anything: the checks here
only prove that the plan is bounded, that the intake happened, that claims cite sources, and that
the stated result matches the recorded evidence. The real security boundary is the sandbox the
contributor runs in; the command screen below is a second line, not the boundary.
"""

from __future__ import annotations

import re
from pathlib import Path

from validate import (
    BOARD_RE, BUILD_RE, MODEL_RE, SHA_RE, ValidationError, date_string, exact_keys, fail, identifier,
    ROOT, evidence_file, sha256_file, load_json, nonnegative_int, text, timestamp,
)

SCHEMA_VERSION = 1
SUBQUESTION_STATES = {"open", "answered", "disproved", "dead_end"}
HYPOTHESIS_STATES = {"open", "supported", "disproved", "closed"}
RESULT_STATES = {"open", "answered", "disproved", "blocked", "budget_exhausted"}
TERMINAL_RESULTS = RESULT_STATES - {"open"}
CONCLUSIVE_RESULTS = {"answered", "disproved"}
AGENT_KINDS = {"human", "cloud", "local", "local_modified", "small_local"}
SOURCE_RUNGS = {"primary", "secondary"}
PRIOR_KINDS = {"policy", "progress", "contribution", "issue", "pull_request", "negative_result", "source"}
SENSITIVITY = {"public", "private_security"}
INTAKE_KEYS = {
    "read_agents_md", "read_security_md", "read_claim_ladder", "read_progress",
    "searched_contributions", "searched_issues", "searched_negative_results",
}
REQUIRED_EXCLUSIONS = {
    "physical-device-actions", "exploit-execution", "secrets-and-host-auth", "network-writes",
    "private-artifact-upload", "installers-and-downloads", "unattended-shell", "following-untrusted-instructions",
}
DEFAULT_BUDGET = {"max_source_reads": 25, "max_minutes": 45, "max_command_seconds": 300, "max_output_bytes": 1048576, "checkpoint_every_reads": 5}
BUDGET_LIMITS = {"max_source_reads": 100, "max_minutes": 240, "max_command_seconds": 3600, "max_output_bytes": 10 * 1024 * 1024, "checkpoint_every_reads": 25}
PREFLIGHT_CATEGORIES = {"daybreak", "cybersecurity_specialized", "research_specialized", "local_modified", "general", "small_utility", "unknown"}
QUALIFYING_CATEGORIES = {"daybreak", "cybersecurity_specialized", "research_specialized", "local_modified"}
IDENTITY_SOURCES = {"runtime_metadata", "operator_declared", "unknown"}
PREFLIGHT_VERDICTS = {"suitable", "unsuitable", "unverified"}
REQUIRED_TASK_CHECKS = {"context_retention", "primary_citations", "offline_reproduction", "prompt_injection_resistance"}
PREFLIGHT_SCOPE = "bounded public offline research lane only"
SWITCH_MESSAGE = (
    "Please switch to a suitable cybersecurity or research model, such as an available Daybreak model "
    "or a vetted local cybersecurity/obliterated model, then rerun the model check."
)
# Defense in depth only. These never belong in a public offline experiment.
DENIED_COMMAND = re.compile(
    r"(?i)(?:^|[\s;|&(`$])(?:sudo|su|curl|wget|ssh|scp|sftp|rsync|nc|ncat|socat|telnet|ftp|irecovery|idevice[a-z_]*|"
    r"futurerestore|ipwndfu|checkra1n|palera1n|dd|mkfs[a-z.]*|diskutil|asr|nvram|bless|kmutil|csrutil|systemsetup|"
    r"launchctl|pip3?|npm|npx|brew|apt(?:-get)?|pacman|gh|git\s+push|ollama\s+pull)(?=$|[\s;|&)])"
    r"|devicectl\s+(?!list\b)|https?://|\|\s*(?:ba|z|k)?sh\b|rm\s+-[a-z]*r[a-z]*f"
)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _refs(value: object, where: str, known: set[str]) -> list[str]:
    if not isinstance(value, list):
        fail(f"{where}: expected array of source ids")
    for item in value:
        if not isinstance(item, str) or item not in known:
            fail(f"{where}: unknown source id {item!r}")
    return value


def _location(value: object, where: str) -> str:
    raw = text(value, where, 3, 400)
    if raw.startswith("https://"):
        if any(ch in raw for ch in " \"'<>`\\"):
            fail(f"{where}: invalid URL")
        return raw
    path = Path(raw)
    if raw.startswith("/") or "\\" in raw or ".." in path.parts or raw.startswith("~"):
        fail(f"{where}: must be an https URL or a repository-relative path")
    return raw


def command_screen(command: str, where: str) -> None:
    if CONTROL_CHARS.search(command) or "\n" in command:
        fail(f"{where}: commands must be one printable line")
    if DENIED_COMMAND.search(command):
        fail(f"{where}: command uses a network, device, install, privilege, or destructive tool outside the public offline lane")


def validate_task(path: Path, progress: dict, *, ready: bool = False, final: bool = False, root: Path = ROOT) -> dict:
    """ready: intake and plan are complete. final: a terminal result is recorded."""
    data = load_json(path)
    required = {
        "schema_version", "kind", "id", "created_at", "sensitivity", "target", "workstream", "blocker", "question",
        "falsifier", "pass_criteria", "fail_criteria", "expected_evidence", "intake", "prior_work", "priority",
        "subquestions", "hypotheses", "agent", "allowed_tools", "allowed_artifacts", "exclusions", "budget",
        "checkpoints", "sources", "result", "model_preflight",
    }
    exact_keys(data, required, {"$schema"}, str(path))
    if data["schema_version"] != SCHEMA_VERSION or data["kind"] != "research-task":
        fail(f"{path}: expected kind 'research-task' and schema_version {SCHEMA_VERSION}")
    task_id = identifier(data["id"], "task.id")
    if len(task_id) < 3:
        fail("task.id: expected at least 3 characters")
    timestamp(data["created_at"], "task.created_at")
    if data["sensitivity"] not in SENSITIVITY:
        fail("task.sensitivity: expected 'public' or 'private_security'")
    if data["sensitivity"] == "private_security":
        fail("task.sensitivity: vulnerability-sensitive work leaves the public workflow; report it privately through SECURITY.md")

    target = data["target"]
    if not isinstance(target, dict):
        fail("task.target: expected object")
    exact_keys(target, {"model", "board", "os_build", "scope"}, set(), "task.target")
    if not MODEL_RE.fullmatch(text(target["model"], "task.target.model")):
        fail("task.target.model: expected exact model identifier such as iPad13,8")
    if not BOARD_RE.fullmatch(text(target["board"], "task.target.board")):
        fail("task.target.board: expected exact board such as J522AP")
    if not BUILD_RE.fullmatch(text(target["os_build"], "task.target.os_build")):
        fail("task.target.os_build: expected exact build such as 24B119")
    text(target["scope"], "task.target.scope", 20, 400)

    workstreams = {item["id"] for item in progress["workstreams"]}
    milestones = {item["id"]: item for item in progress["milestones"]}
    if identifier(data["workstream"], "task.workstream") not in workstreams:
        fail("task.workstream: unknown workstream")
    blocker = data["blocker"]
    if not isinstance(blocker, dict):
        fail("task.blocker: expected object")
    exact_keys(blocker, {"milestone", "prerequisite"}, set(), "task.blocker")
    if identifier(blocker["milestone"], "task.blocker.milestone") not in milestones:
        fail("task.blocker.milestone: unknown milestone")
    text(blocker["prerequisite"], "task.blocker.prerequisite", 10, 400)

    for key, low, high in (("question", 20, 400), ("falsifier", 20, 400), ("pass_criteria", 10, 400), ("fail_criteria", 10, 400), ("expected_evidence", 10, 400)):
        text(data[key], f"task.{key}", low, high)
    if data["pass_criteria"].strip().lower() == data["fail_criteria"].strip().lower():
        fail("task: pass and fail criteria must differ")

    intake = data["intake"]
    if not isinstance(intake, dict):
        fail("task.intake: expected object")
    exact_keys(intake, INTAKE_KEYS, set(), "task.intake")
    if any(type(value) is not bool for value in intake.values()):
        fail("task.intake: values must be true or false")
    intake_missing = sorted(key for key, value in intake.items() if not value)

    prior = data["prior_work"]
    if not isinstance(prior, list):
        fail("task.prior_work: expected array")
    for index, item in enumerate(prior):
        where = f"task.prior_work[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"kind", "ref", "summary"}, set(), where)
        if item["kind"] not in PRIOR_KINDS:
            fail(f"{where}.kind: invalid")
        _location(item["ref"], f"{where}.ref")
        text(item["summary"], f"{where}.summary", 5, 400)
    if ready and not {"policy", "progress"} <= {item["kind"] for item in prior}:
        fail("task.prior_work: a ready task cites at least the policies and the progress matrix it read")

    priority = data["priority"]
    if not isinstance(priority, dict):
        fail("task.priority: expected object")
    scores = {"blocker_relevance", "reachability", "evidence_strength", "information_gain", "cost"}
    exact_keys(priority, scores | {"rationale"}, set(), "task.priority")
    for key in scores:
        value = nonnegative_int(priority[key], f"task.priority.{key}")
        if value > 3:
            fail(f"task.priority.{key}: expected 0..3")
    text(priority["rationale"], "task.priority.rationale", 20, 600)

    budget = data["budget"]
    if not isinstance(budget, dict):
        fail("task.budget: expected object")
    exact_keys(budget, set(DEFAULT_BUDGET), set(), "task.budget")
    for key, limit in BUDGET_LIMITS.items():
        value = nonnegative_int(budget[key], f"task.budget.{key}")
        if not 1 <= value <= limit:
            fail(f"task.budget.{key}: expected 1..{limit}")

    sources = data["sources"]
    if not isinstance(sources, list):
        fail("task.sources: expected array")
    if len(sources) > budget["max_source_reads"]:
        fail("task.sources: more reads than the budget allows; stop and record budget_exhausted")
    source_ids: set[str] = set()
    for index, item in enumerate(sources):
        where = f"task.sources[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"id", "title", "location", "rung", "revision", "date_read"}, {"sha256"}, where)
        source_id = identifier(item["id"], f"{where}.id")
        if source_id in source_ids:
            fail(f"{where}.id: duplicate")
        source_ids.add(source_id)
        text(item["title"], f"{where}.title", 3, 200)
        location = _location(item["location"], f"{where}.location")
        if item["rung"] not in SOURCE_RUNGS:
            fail(f"{where}.rung: expected primary or secondary")
        text(item["revision"], f"{where}.revision", 1, 120)
        date_string(item["date_read"], f"{where}.date_read")
        if "sha256" in item and not SHA_RE.fullmatch(text(item["sha256"], f"{where}.sha256")):
            fail(f"{where}.sha256: invalid")
        if not location.startswith("https://") and "sha256" not in item:
            fail(f"{where}.sha256: a local artifact needs a pinned hash")

    subquestions = data["subquestions"]
    if not isinstance(subquestions, list) or not 3 <= len(subquestions) <= 7:
        fail("task.subquestions: expected three to seven sub-questions")
    for index, item in enumerate(subquestions):
        where = f"task.subquestions[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"id", "text", "state", "sources"}, set(), where)
        identifier(item["id"], f"{where}.id")
        text(item["text"], f"{where}.text", 10, 400)
        if item["state"] not in SUBQUESTION_STATES:
            fail(f"{where}.state: invalid")
        refs = _refs(item["sources"], f"{where}.sources", source_ids)
        if item["state"] in {"answered", "disproved"} and not refs:
            fail(f"{where}: a closed sub-question cites at least one source")

    hypotheses = data["hypotheses"]
    if not isinstance(hypotheses, list) or not hypotheses:
        fail("task.hypotheses: expected at least one hypothesis")
    def norm(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() if isinstance(value, str) else ""

    closed_texts: dict[str, set[str]] = {}
    for item in hypotheses:
        if isinstance(item, dict) and item.get("state") in {"disproved", "closed"} and isinstance(item.get("sources"), list):
            closed_texts.setdefault(norm(item.get("text")), set()).update(ref for ref in item["sources"] if isinstance(ref, str))
    seen_texts: set[str] = set()
    for index, item in enumerate(hypotheses):
        where = f"task.hypotheses[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"id", "text", "state", "experiment", "sources", "reopened_with"}, set(), where)
        identifier(item["id"], f"{where}.id")
        statement = text(item["text"], f"{where}.text", 10, 400)
        if item["state"] not in HYPOTHESIS_STATES:
            fail(f"{where}.state: invalid")
        refs = _refs(item["sources"], f"{where}.sources", source_ids)
        reopened = _refs(item["reopened_with"], f"{where}.reopened_with", source_ids)
        key = norm(statement)
        if key in seen_texts:
            if key in closed_texts and (not reopened or set(reopened) <= closed_texts[key]):
                fail(f"{where}: repeats a closed hypothesis without new evidence in reopened_with")
            if key not in closed_texts:
                fail(f"{where}: duplicate hypothesis")
        seen_texts.add(key)
        experiment = item["experiment"]
        if experiment is not None:
            if not isinstance(experiment, dict):
                fail(f"{where}.experiment: expected object or null")
            exact_keys(experiment, {"command", "baseline", "control", "runtime_limit_seconds", "output_limit_bytes", "offline"}, set(), f"{where}.experiment")
            command = text(experiment["command"], f"{where}.experiment.command", 2, 400)
            command_screen(command, f"{where}.experiment.command")
            text(experiment["baseline"], f"{where}.experiment.baseline", 10, 400)
            text(experiment["control"], f"{where}.experiment.control", 10, 400)
            if experiment["offline"] is not True:
                fail(f"{where}.experiment.offline: public experiments run offline")
            runtime = nonnegative_int(experiment["runtime_limit_seconds"], f"{where}.experiment.runtime_limit_seconds")
            output = nonnegative_int(experiment["output_limit_bytes"], f"{where}.experiment.output_limit_bytes")
            if not 1 <= runtime <= budget["max_command_seconds"]:
                fail(f"{where}.experiment.runtime_limit_seconds: must be within the task budget")
            if not 1 <= output <= budget["max_output_bytes"]:
                fail(f"{where}.experiment.output_limit_bytes: must be within the task budget")
        if item["state"] in {"supported", "disproved"}:
            if experiment is None or not refs:
                fail(f"{where}: a decided hypothesis needs its controlled experiment and cited evidence")

    if ready or final:
        leftover = sorted(set(_placeholders(data)))
        if leftover:
            fail(f"task: fill every {PLACEHOLDER} field first: {leftover[:5]}")
    validate_agent(data["agent"])
    validate_preflight(data["model_preflight"], data["agent"])
    if ready or final:
        eligible, message = preflight_gate(data)
        if not eligible:
            fail(f"task.model_preflight: {message}")
        if intake_missing:
            fail(f"task.intake: incomplete: {intake_missing}")

    for key in ("allowed_tools", "allowed_artifacts", "exclusions"):
        values = data[key]
        if not isinstance(values, list) or not values:
            fail(f"task.{key}: expected non-empty array")
        for value in values:
            text(value, f"task.{key}[]", 2, 120)
    missing = REQUIRED_EXCLUSIONS - set(data["exclusions"])
    if missing:
        fail(f"task.exclusions: missing required exclusions {sorted(missing)}")

    checkpoints = data["checkpoints"]
    if not isinstance(checkpoints, list):
        fail("task.checkpoints: expected array")
    for index, item in enumerate(checkpoints):
        where = f"task.checkpoints[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"at", "reads_used", "minutes_used", "note"}, set(), where)
        timestamp(item["at"], f"{where}.at")
        if nonnegative_int(item["reads_used"], f"{where}.reads_used") > budget["max_source_reads"]:
            fail(f"{where}.reads_used: exceeds budget")
        if nonnegative_int(item["minutes_used"], f"{where}.minutes_used") > budget["max_minutes"]:
            fail(f"{where}.minutes_used: exceeds budget")
        text(item["note"], f"{where}.note", 3, 400)

    validate_result(data, source_ids, final)
    for item in data["result"]["evidence"]:
        if item["path"].startswith("https://"):
            continue  # Remote hashes are declarations; this offline validator never fetches them.
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            fail("task.result.evidence: task must be inside the repository")
        if len(relative.parts) < 3 or relative.parts[0] != "contributions":
            fail("task.result.evidence: local evidence requires a task under contributions/<handle>/")
        artifact = evidence_file(root, item["path"], relative.parts[1], "task.result.evidence")
        if sha256_file(artifact) != item["sha256"]:
            fail("task.result.evidence.sha256: does not match the evidence file")
    return data


PLACEHOLDER = "REPLACE:"


def _placeholders(value: object, where: str = "task"):
    if isinstance(value, str):
        if PLACEHOLDER in value:
            yield where
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _placeholders(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _placeholders(child, f"{where}[{index}]")


def validate_agent(agent: object) -> None:
    if not isinstance(agent, dict):
        fail("task.agent: expected object")
    exact_keys(agent, {"kind", "provider", "model_id", "reasoning", "used_on", "representative_checks"},
               {"upstream_model", "revision", "quantization", "license", "provenance", "limitations"}, "task.agent")
    kind = agent["kind"]
    if kind not in AGENT_KINDS:
        fail(f"task.agent.kind: expected one of {sorted(AGENT_KINDS)}")
    text(agent["provider"], "task.agent.provider", 1, 120)
    text(agent["model_id"], "task.agent.model_id", 1, 160)
    text(agent["reasoning"], "task.agent.reasoning", 1, 120)
    date_string(agent["used_on"], "task.agent.used_on")
    checks = agent["representative_checks"]
    if not isinstance(checks, list):
        fail("task.agent.representative_checks: expected array")
    for value in checks:
        text(value, "task.agent.representative_checks[]", 3, 200)
    if kind in {"local", "local_modified"}:
        for key in ("upstream_model", "revision", "quantization", "license", "provenance", "limitations"):
            if key not in agent:
                fail(f"task.agent.{key}: required for local models")
            text(agent[key], f"task.agent.{key}", 1, 400)
        if len(checks) < 4:
            fail("task.agent.representative_checks: a local model needs context, citation, offline reproduction, and prompt-injection checks recorded")
    if kind == "local_modified" and "refusal" not in agent["limitations"].lower():
        fail("task.agent.limitations: state that removing refusals is not evidence of accuracy or trust")


def validate_preflight(preflight: object, agent: dict) -> None:
    """Structure only. preflight_gate decides eligibility."""
    if not isinstance(preflight, dict):
        fail("task.model_preflight: expected object")
    exact_keys(preflight, {"identity_source", "identity_evidence", "category", "model_card", "task_checks", "verdict", "assessed_at", "limitations", "scope"}, set(), "task.model_preflight")
    if preflight["identity_source"] not in IDENTITY_SOURCES:
        fail(f"task.model_preflight.identity_source: expected one of {sorted(IDENTITY_SOURCES)}")
    text(preflight["identity_evidence"], "task.model_preflight.identity_evidence", 3, 400)
    if preflight["category"] not in PREFLIGHT_CATEGORIES:
        fail(f"task.model_preflight.category: expected one of {sorted(PREFLIGHT_CATEGORIES)}")
    card = preflight["model_card"]
    if card is not None:
        if not isinstance(card, dict):
            fail("task.model_preflight.model_card: expected object or null")
        exact_keys(card, {"location", "revision", "date_read"}, set(), "task.model_preflight.model_card")
        _location(card["location"], "task.model_preflight.model_card.location")
        text(card["revision"], "task.model_preflight.model_card.revision", 1, 120)
        date_string(card["date_read"], "task.model_preflight.model_card.date_read")
    checks = preflight["task_checks"]
    if not isinstance(checks, list):
        fail("task.model_preflight.task_checks: expected array")
    for index, item in enumerate(checks):
        where = f"task.model_preflight.task_checks[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"check", "outcome", "evidence"}, set(), where)
        if item["check"] not in REQUIRED_TASK_CHECKS:
            fail(f"{where}.check: expected one of {sorted(REQUIRED_TASK_CHECKS)}")
        if item["outcome"] not in {"pass", "fail", "not_run"}:
            fail(f"{where}.outcome: expected pass, fail, or not_run")
        text(item["evidence"], f"{where}.evidence", 3, 400)
    if preflight["verdict"] not in PREFLIGHT_VERDICTS:
        fail("task.model_preflight.verdict: expected suitable, unsuitable, or unverified")
    if preflight["assessed_at"] is not None:
        timestamp(preflight["assessed_at"], "task.model_preflight.assessed_at")
    text(preflight["limitations"], "task.model_preflight.limitations", 3, 600)
    if preflight["scope"] != PREFLIGHT_SCOPE:
        fail(f"task.model_preflight.scope: must be exactly {PREFLIGHT_SCOPE!r}; a model check never authorizes more")


def preflight_gate(task: dict) -> tuple[bool, str]:
    """Return (eligible, message). Unknown, unverified, and unsuitable all block. Nothing here authorizes
    device actions, exploit execution, installation, or publication; it only opens the bounded public lane."""
    preflight = task["model_preflight"]
    agent = task["agent"]
    identity = f"{agent['provider']} / {agent['model_id']}" if preflight["identity_source"] != "unknown" else "unknown"
    def blocked(reason: str) -> tuple[bool, str]:
        return False, f"BLOCKED. Current model: {identity}. Reason: {reason}. {SWITCH_MESSAGE}"
    if agent["kind"] == "human":
        if preflight["verdict"] == "suitable" and preflight["identity_source"] == "operator_declared":
            return True, f"ELIGIBLE for the {PREFLIGHT_SCOPE}: human researcher, declared by the operator."
        return blocked("a human researcher records verdict 'suitable' with identity_source 'operator_declared'")
    if preflight["identity_source"] == "unknown" or agent["model_id"].strip().lower() in {"", "unknown"}:
        return blocked("model identity is unknown; read it from runtime metadata, not from the model's own guess")
    if preflight["verdict"] == "unsuitable":
        return blocked("the preflight verdict is unsuitable")
    if preflight["verdict"] != "suitable":
        return blocked("the preflight verdict is unverified")
    if preflight["category"] not in QUALIFYING_CATEGORIES:
        if preflight["category"] == "small_utility":
            return blocked("small utility models may format and validate records but may not run substantive research")
        return blocked(f"category {preflight['category']!r} does not qualify for security or boot-chain research")
    if preflight["model_card"] is None:
        return blocked("no model card or provenance source is cited")
    check_names = [item["check"] for item in preflight["task_checks"]]
    if len(check_names) != len(set(check_names)):
        return blocked("each representative task check must have exactly one outcome; conflicting or duplicate outcomes are not accepted")
    passed = {item["check"] for item in preflight["task_checks"] if item["outcome"] == "pass"}
    missing = REQUIRED_TASK_CHECKS - passed
    if missing:
        return blocked(f"representative task checks not passed: {sorted(missing)}")
    if preflight["category"] == "local_modified" and agent["kind"] != "local_modified":
        return blocked("an obliterated or otherwise modified local model must record agent.kind 'local_modified' with full provenance")
    if preflight["category"] == "local_modified" and "refusal" not in preflight["limitations"].lower():
        return blocked("limitations must state that removing refusals is not evidence of accuracy, trust, or permission")
    origin = "runtime metadata" if preflight["identity_source"] == "runtime_metadata" else "operator declaration (declared, not runtime-verified)"
    return True, f"ELIGIBLE for the {PREFLIGHT_SCOPE}. Current model: {identity}, identity from {origin}. This grants no device, exploit, install, merge, or publication authority."


def validate_result(data: dict, source_ids: set[str], final: bool) -> None:
    result = data["result"]
    if not isinstance(result, dict):
        fail("task.result: expected object")
    exact_keys(result, {"state", "claim", "evidence", "limits", "contradictions", "failed_avenues", "next_check"}, set(), "task.result")
    state = result["state"]
    if not isinstance(result["claim"], str) or len(result["claim"]) > 600:
        fail("task.result.claim: expected string up to 600 characters")
    if not isinstance(result["limits"], str) or not isinstance(result["next_check"], str):
        fail("task.result: limits and next_check are strings")
    if state not in RESULT_STATES:
        fail("task.result.state: invalid")
    if final and state not in TERMINAL_RESULTS:
        fail("task.result.state: a finished task records answered, disproved, blocked, or budget_exhausted")
    evidence = result["evidence"]
    if not isinstance(evidence, list):
        fail("task.result.evidence: expected array")
    for index, item in enumerate(evidence):
        where = f"task.result.evidence[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: expected object")
        exact_keys(item, {"path", "sha256"}, set(), where)
        _location(item["path"], f"{where}.path")
        if not SHA_RE.fullmatch(text(item["sha256"], f"{where}.sha256")):
            fail(f"{where}.sha256: invalid")
    for key in ("contradictions", "failed_avenues"):
        if not isinstance(result[key], list):
            fail(f"task.result.{key}: expected array")
        for value in result[key]:
            text(value, f"task.result.{key}[]", 3, 400)
    if state == "open":
        return
    text(result["limits"], "task.result.limits", 10, 600)
    text(result["next_check"], "task.result.next_check", 10, 400)
    if state in CONCLUSIVE_RESULTS:
        text(result["claim"], "task.result.claim", 20, 600)
        if not source_ids or not evidence:
            fail("task.result: a conclusive result needs cited sources and hashed evidence")
        if any(item["state"] == "open" for item in data["subquestions"]):
            fail("task.result: answered or disproved requires every sub-question closed; otherwise record blocked or budget_exhausted")


def is_complete(task: dict) -> bool:
    """Budget exhaustion and blocked results are recorded outcomes, never completion."""
    return task["result"]["state"] in CONCLUSIVE_RESULTS


__all__ = ["validate_task", "preflight_gate", "SWITCH_MESSAGE", "PREFLIGHT_SCOPE", "is_complete", "DEFAULT_BUDGET", "REQUIRED_EXCLUSIONS", "INTAKE_KEYS", "ValidationError", "command_screen"]
