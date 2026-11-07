"""Tests for the contribution contract, registry, installation gate, research preflight, lanes, and forms."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "scripts", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import build_site  # noqa: E402
import contract  # noqa: E402
import contribute  # noqa: E402
import research  # noqa: E402
import validate  # noqa: E402

REPO = "https://github.com/baney75/omarchy-on-ipad"
SITE = "https://baney75.github.io/omarchy-on-ipad/"
HANDLE = "octo-contributor"
SHA_ZERO = "0" * 64


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Sandbox:
    """A throwaway copy of the repository's source, so tests can add records freely."""

    def __init__(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "_site", "__pycache__"))
        self.progress = json.loads((self.root / "data/progress.json").read_text(encoding="utf-8"))

    def close(self) -> None:
        self._dir.cleanup()

    def evidence(self, name: str = "inventory.json", body: str = '{"devices": []}\n', handle: str = HANDLE) -> tuple[str, str]:
        path = self.root / "contributions" / handle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return f"contributions/{handle}/{name}", sha(path)

    def record(self, record_id: str = "octo-inventory", **changes) -> dict:
        rel, digest = self.evidence()
        record = {
            "id": record_id, "status": "submitted", "contributor": HANDLE, "agent": "human",
            "device": {"model": "iPad13,8", "board": "J522AP", "os_build": "24B119"},
            "workstream": "device-matrix", "claim": "Read-only inventory of one reference-class device.",
            "evidence": [{"kind": "command-output", "path": rel, "sha256": digest}],
            "safety": dict(validate.READ_ONLY_SAFETY), "recorded_at": "2026-11-07T00:00:00Z",
        }
        record.update(changes)
        return record

    def review(self, **changes) -> dict:
        review = {"reviewer": "baney75", "reviewed_at": "2026-11-07T01:00:00Z", "pull_request": 12, "summary": "Evidence matches the claim and stays in the read-only lane."}
        review.update(changes)
        return review

    def write(self, record: dict) -> Path:
        path = self.root / "data/contributions" / f"{record['id']}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def check(self, record: dict, submission: bool = False) -> dict:
        path = self.write(record)
        workstreams = {item["id"] for item in self.progress["workstreams"]}
        return validate.validate_contribution(path, workstreams, self.root, submission=submission)

    def build(self) -> Path:
        output = self.root.parent / "out"
        build_site.build(self.root, output, REPO, SITE)
        return output


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = contribute.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def suitable_task(**changes) -> dict:
    """A fully filled, conclusive research task with an eligible preflight."""
    task = {
        "schema_version": 1, "kind": "research-task", "id": "octo-dcp-question", "created_at": "2026-11-07T00:00:00Z",
        "sensitivity": "public",
        "model_preflight": {
            "identity_source": "runtime_metadata", "identity_evidence": "Provider and model id from the harness session banner.",
            "category": "daybreak", "model_card": {"location": "https://example.org/model-card", "revision": "2026-10", "date_read": "2026-11-07"},
            "task_checks": [{"check": name, "outcome": "pass", "evidence": "Ran the playbook check on a repository task."} for name in sorted(research.REQUIRED_TASK_CHECKS)],
            "verdict": "suitable", "assessed_at": "2026-11-07T00:00:00Z",
            "limitations": "Long sessions may drop early context; checkpoints mitigate.", "scope": research.PREFLIGHT_SCOPE,
        },
        "target": {"model": "iPad13,8", "board": "J522AP", "os_build": "24B119", "scope": "Offline reading of public upstream display driver source only."},
        "workstream": "j522-linux", "blocker": {"milestone": "hardware", "prerequisite": "Board support is mapped but not verified."},
        "question": "Does the pinned upstream display driver list a compatible string for this board?",
        "falsifier": "The compatible string is absent from the pinned revision of the driver source.",
        "pass_criteria": "The compatible string appears at the pinned revision.",
        "fail_criteria": "The compatible string is absent at the pinned revision.",
        "expected_evidence": "A file and line at a pinned upstream commit.",
        "intake": {key: True for key in research.INTAKE_KEYS},
        "prior_work": [{"kind": "policy", "ref": "AGENTS.md", "summary": "Read-only offline lane."}, {"kind": "progress", "ref": "data/progress.json", "summary": "Hardware milestone is prepared."}],
        "priority": {"blocker_relevance": 2, "reachability": 3, "evidence_strength": 3, "information_gain": 2, "cost": 1, "rationale": "Cheap, offline, and it decides whether reuse is plausible."},
        "subquestions": [
            {"id": "q1", "text": "Which upstream file holds the compatible list?", "state": "answered", "sources": ["s1"]},
            {"id": "q2", "text": "Is this board listed at the pinned revision?", "state": "answered", "sources": ["s1"]},
            {"id": "q3", "text": "Does a later revision change the answer?", "state": "dead_end", "sources": []},
        ],
        "hypotheses": [{"id": "h1", "text": "The driver lists this board already.", "state": "disproved",
                        "experiment": {"command": "grep -n compatible driver.c", "baseline": "Known listed board appears in the output.", "control": "A made-up board string does not appear.", "runtime_limit_seconds": 10, "output_limit_bytes": 4096, "offline": True},
                        "sources": ["s1"], "reopened_with": []}],
        "agent": {"kind": "cloud", "provider": "example-provider", "model_id": "example-model", "reasoning": "high", "used_on": "2026-11-07", "representative_checks": []},
        "allowed_tools": ["read repository files"], "allowed_artifacts": ["public source at pinned revisions"],
        "exclusions": sorted(research.REQUIRED_EXCLUSIONS),
        "budget": dict(research.DEFAULT_BUDGET), "checkpoints": [{"at": "2026-11-07T00:10:00Z", "reads_used": 1, "minutes_used": 10, "note": "One source read."}],
        "sources": [{"id": "s1", "title": "Upstream driver source", "location": "https://example.org/driver.c", "rung": "primary", "revision": "abc123", "date_read": "2026-11-07"}],
        "result": {"state": "disproved", "claim": "The pinned driver revision does not list this board's compatible string.", "evidence": [{"path": "https://example.org/driver.c", "sha256": SHA_ZERO}],
                   "limits": "One revision of one file; later revisions were not read.", "contradictions": [], "failed_avenues": ["Searching release notes found nothing."],
                   "next_check": "Read the next tagged revision of the same file."},
    }
    for key, value in changes.items():
        task[key] = value
    return task


class SandboxCase(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Sandbox()

    def tearDown(self) -> None:
        self.box.close()


class ContributionReviewTests(SandboxCase):
    def test_submitted_record_with_hashed_evidence_passes(self):
        self.box.check(self.box.record(), submission=True)

    def test_hash_mismatch_is_rejected(self):
        record = self.box.record()
        record["evidence"][0]["sha256"] = SHA_ZERO
        with self.assertRaisesRegex(validate.ValidationError, "does not match"):
            self.box.check(record)

    def test_unsafe_evidence_paths_are_rejected(self):
        outside = self.box.root.parent / "outside.txt"
        outside.write_text("x", encoding="utf-8")
        link = self.box.root / "contributions" / HANDLE / "link.txt"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(outside)
        other_rel, _ = self.box.evidence(handle="someone-else")
        bad_paths = [
            f"contributions/{HANDLE}/../../data/progress.json", "/etc/hosts", f"contributions\\{HANDLE}\\x.txt",
            f"contributions/{HANDLE}/.hidden.txt", f"contributions/{HANDLE}/link.txt", other_rel,
            f"contributions/{HANDLE}/payload.bin", "data/progress.json", f"contributions/{HANDLE}/missing.txt",
        ]
        for bad in bad_paths:
            with self.subTest(path=bad):
                record = self.box.record()
                record["evidence"][0]["path"] = bad
                with self.assertRaises(validate.ValidationError):
                    self.box.check(record)

    def test_review_rules(self):
        cases = {
            "submitted with review": self.box.record(review=self.box.review()),
            "reviewed without review": self.box.record(status="verified_offline"),
            "reviewer outside CODEOWNERS": self.box.record(status="verified_offline", review=self.box.review(reviewer="random-person")),
            "self review": self.box.record(status="verified_offline", contributor="baney75", review=self.box.review()),
            "review before record": self.box.record(status="verified_offline", review=self.box.review(reviewed_at="2026-11-06T00:00:00Z")),
            "zero pull request": self.box.record(status="verified_offline", review=self.box.review(pull_request=0)),
        }
        for label, record in cases.items():
            if label == "self review":
                record["evidence"] = [dict(record["evidence"][0], path=self.box.evidence(handle="baney75")[0], sha256=self.box.evidence(handle="baney75")[1])]
            with self.subTest(label):
                with self.assertRaises(validate.ValidationError):
                    self.box.check(record)

    def test_contributor_lane_refuses_reviewed_status(self):
        record = self.box.record(status="verified_physical", review=self.box.review())
        self.box.check(record)  # repository lane accepts a maintainer review
        with self.assertRaisesRegex(validate.ValidationError, "contributors submit"):
            self.box.check(record, submission=True)

    def test_unsafe_safety_flags_and_template_braces_are_rejected(self):
        for record in (
            self.box.record(safety=dict(validate.READ_ONLY_SAFETY, storage_write=True)),
            self.box.record(safety=dict(validate.READ_ONLY_SAFETY, read_only=1)),
            self.box.record(claim="Inject {{PROJECT_NAME}} into the page template."),
        ):
            with self.assertRaises(validate.ValidationError):
                self.box.check(record)

    def test_malformed_json_and_types_are_rejected(self):
        path = self.box.root / "data/contributions/broken-record.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(validate.ValidationError):
            validate.validate_all(self.box.root)
        path.write_text(json.dumps(self.box.record("broken-record", evidence="none")), encoding="utf-8")
        with self.assertRaises(validate.ValidationError):
            validate.validate_all(self.box.root)


class RegistryAndSiteTests(SandboxCase):
    def test_only_reviewed_records_are_listed_and_html_is_escaped(self):
        self.box.write(self.box.record("octo-pending"))
        self.box.write(self.box.record("octo-reviewed", status="verified_offline", claim="Escaping check <script>alert(1)</script> & done.", review=self.box.review()))
        output = self.box.build()
        registry = json.loads((output / "api/v1/registry.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["id"] for entry in registry["entries"]], ["octo-reviewed"])
        self.assertEqual(registry["summary"]["awaiting_review"], 1)
        self.assertEqual(registry["summary"]["reviewed"], 1)
        entry = registry["entries"][0]
        self.assertEqual(entry["review"]["pull_request_url"], f"{REPO}/pull/12")
        self.assertTrue(entry["evidence"][0]["url"].startswith(f"{REPO}/blob/main/contributions/"))
        page = (output / "registry/index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; done.", page)
        self.assertNotIn("octo-pending", page)
        self.assertEqual(page.count('class="entry"'), len(registry["entries"]))

    def test_fill_is_single_pass_and_encodes_braces(self):
        self.assertEqual(build_site.fill("{{A}}", {"A": "{{B}}", "B": "x"}), "&#123;&#123;B&#125;&#125;")
        self.assertEqual(build_site.fill("{{{A}}}|{{B}}", {"A": "<b>", "B": "<b>"}), "<b>|&lt;b&gt;")
        with self.assertRaises(KeyError):
            build_site.fill("{{MISSING}}", {})

    def test_json_endpoints_match_data_and_pages(self):
        output = self.box.build()
        index = json.loads((output / "api/v1/index.json").read_text(encoding="utf-8"))
        progress = json.loads((output / "api/v1/progress.json").read_text(encoding="utf-8"))
        data = self.box.progress
        passed = sum(item["passed"] for item in data["milestones"])
        total = sum(item["total"] for item in data["milestones"])
        self.assertEqual((index["truth"]["checks_passed"], index["truth"]["checks_total"]), (passed, total))
        self.assertEqual(progress["derived"]["checks_passed"], passed)
        self.assertEqual(index["truth"]["current_truth"], data["goal"]["current_truth"])
        self.assertEqual(index["contract_version"], 1)
        for name in contract.SCHEMA_FILES:
            self.assertTrue((output / "schemas" / f"{name}.schema.json").is_file(), name)
        for path in contract.POLICY_PATHS.values():
            self.assertTrue((ROOT / path).is_file(), path)
        for key, url in index["endpoints"].items():
            rel = url.removeprefix(SITE)
            target = output / rel / "index.html" if rel.endswith("/") else output / rel
            self.assertTrue(target.is_file(), key)
        for path in output.rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
        for path in output.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".json", ".txt"}:
                self.assertNotIn("{{", path.read_text(encoding="utf-8"), path.name)
        llms = (output / "llms.txt").read_text(encoding="utf-8")
        self.assertIn(data["goal"]["current_truth"], llms)
        self.assertIn("Installation state: unavailable", llms)
        self.assertIn(research.SWITCH_MESSAGE, llms)
        for lane in contract.LANES:
            self.assertIn(lane["id"], llms)
        home = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="llms.txt"', home)
        self.assertIn("bug-report.yml", home)
        for page in ("index.html", "registry/index.html", "install/index.html"):
            body = (output / page).read_text(encoding="utf-8")
            self.assertNotRegex(body, r'(?:src|href)=["\']https?://[^"\']+\.(?:css|js)["\']')
            self.assertIn('<a class="skip-link" href="#main">', body)
            self.assertEqual(body.count("<h1"), 1)


class DeviceViewTests(SandboxCase):
    def test_reference_device_specifics_come_from_public_records(self):
        data = self.box.progress
        view = contract.devices(data)
        reference = [entry for entry in view["devices"] if entry["role"] == "reference"]
        self.assertEqual(len(reference), sum(1 for row in data["coverage"] if row["level"] == "reference"))
        device = reference[0]
        self.assertEqual(device["reference_target"], data["goal"]["reference_target"])
        self.assertEqual(device["reference_build"], data["goal"]["reference_build"])
        row = next(row for row in data["coverage"] if row["level"] == "reference")
        self.assertEqual(device["models"], row["models"])
        self.assertEqual(device["builds"], row["builds"])
        status = device["status"]
        first_open = next(item for item in data["milestones"] if item["state"] != "complete")
        first_blocked = next(item for item in data["milestones"] if item["state"] == "blocked")
        self.assertEqual(status["current_stage"]["id"], first_open["id"])
        self.assertEqual(status["blocker"]["id"], first_blocked["id"])
        self.assertEqual([item["id"] for item in status["verified_offline"]], [item["id"] for item in data["milestones"] if item["state"] == "verified_offline"])
        for key in ("physical_linux_boots", "installed_systems", "untethered_cold_boots"):
            self.assertEqual(status[key], data["counts"][key])

    def test_current_reference_values_and_no_unsupported_attributes(self):
        data = self.box.progress
        view = contract.devices(data)
        rendered = json.dumps(view).lower()
        self.assertIn("ipad13,8", rendered)
        self.assertIn("j522ap", rendered)
        self.assertIn("24b119", rendered)
        allowed = {"family", "models", "builds", "level", "contributors", "role", "reference_target", "reference_build", "status"}
        for entry in view["devices"]:
            self.assertLessEqual(set(entry), allowed)
        for forbidden in ("ram", "memory", "capacity", "storage", "serial", "udid", "ecid", "gigabyte", " gb", " tb"):
            self.assertNotIn(f'"{forbidden}"', rendered)
            self.assertNotRegex(rendered, rf"\b{re.escape(forbidden.strip())}\b" if forbidden.strip() not in {"storage"} else r"\bstorage capacity\b")
        self.assertEqual(view["other_devices"]["state"], "welcome")
        if all(row["level"] == "reference" for row in data["coverage"]):
            self.assertIn("No other device is currently being tested.", view["other_devices"]["summary"])
        output = self.box.build()
        home = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="devices"', home)
        self.assertIn(build_site.escape(data["goal"]["reference_target"]), home)
        self.assertIn("Welcome", home)
        self.assertNotIn("currently tested", home.replace("No other device is currently being tested", ""))


class InstallationGateTests(SandboxCase):
    def installation(self) -> dict:
        return json.loads((self.box.root / "data/installation.json").read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        (self.box.root / "data/installation.json").write_text(json.dumps(data), encoding="utf-8")

    def release(self, evidence_id: str = "octo-install") -> dict:
        return {
            "id": "first", "version": "0.1.0", "published_at": "2027-01-01T00:00:00Z",
            "release_url": f"{REPO}/releases/tag/v0.1.0",
            "compatibility": [{"model": "iPad13,8", "board": "J522AP", "os_build": "24B119"}],
            "artifacts": [{"name": "image.img", "url": f"{REPO}/releases/download/v0.1.0/image.img", "sha256": SHA_ZERO, "size_bytes": 10}],
            "provenance": {"source_commit": "a" * 40, "build_recipe": "platform/packaging/recipe.md", "attestation_url": f"{REPO}/attestations/1"},
            "verification": {"install_evidence": [evidence_id], "recovery_evidence": [evidence_id], "rollback_evidence": [evidence_id], "cold_boots": 3},
            "review": {"human_reviewer": "baney75", "security_reviewer": "second-person", "pull_request": 99, "reviewed_at": "2027-01-01T00:00:00Z"},
        }

    def complete_progress(self) -> None:
        data = copy.deepcopy(self.box.progress)
        for item in data["milestones"]:
            item["state"], item["passed"] = "complete", item["total"]
        data["counts"].update(installed_systems=1, untethered_cold_boots=3, physical_linux_boots=3)
        (self.box.root / "data/progress.json").write_text(json.dumps(data), encoding="utf-8")

    def test_current_installation_is_unavailable_and_page_offers_nothing(self):
        bundle = validate.validate_all(self.box.root)
        self.assertEqual(bundle["installation"]["state"], "unavailable")
        self.assertEqual(bundle["installation"]["releases"], [])
        output = self.box.build()
        api = json.loads((output / "api/v1/installation.json").read_text(encoding="utf-8"))
        self.assertFalse(api["installable"])
        page = (output / "install/index.html").read_text(encoding="utf-8")
        self.assertIn("Installation is not available.", page)
        for forbidden in ("releases/download", "curl ", "wget ", "install.sh", "sudo "):
            self.assertNotIn(forbidden, page)
        for requirement in ("model-build-compatibility", "artifact-hashes", "provenance", "recovery-verified", "rollback-verified", "human-review", "security-review"):
            self.assertIn(f'id="requirement-{requirement}"', page)

    def test_release_while_unavailable_or_without_evidence_is_refused(self):
        data = self.installation()
        data["releases"] = [self.release()]
        self.save(data)
        with self.assertRaisesRegex(validate.ValidationError, "must be empty"):
            validate.validate_all(self.box.root)
        data["state"] = "available"
        self.save(data)
        with self.assertRaisesRegex(validate.ValidationError, "no installed system"):
            validate.validate_all(self.box.root)
        self.complete_progress()
        with self.assertRaisesRegex(validate.ValidationError, "not a reviewed verified_physical"):
            validate.validate_all(self.box.root)

    def test_fully_evidenced_release_passes_only_with_every_requirement(self):
        self.complete_progress()
        self.box.write(self.box.record("octo-install", status="verified_physical", review=self.box.review()))
        data = self.installation()
        data.update(state="available", releases=[self.release()])
        self.save(data)
        bundle = validate.validate_all(self.box.root)
        self.assertTrue(contract.installation(bundle)["installable"])
        broken = {
            "same reviewers": lambda r: r["review"].update(security_reviewer="baney75"),
            "offsite artifact": lambda r: r["artifacts"][0].update(url="https://example.com/image.img"),
            "short commit": lambda r: r["provenance"].update(source_commit="abc"),
            "two cold boots": lambda r: r["verification"].update(cold_boots=2),
            "incompatible evidence": lambda r: r["compatibility"][0].update(os_build="24A100"),
            "wrong board": lambda r: r["compatibility"][0].update(board="J523AP"),
            "uncovered device": lambda r: r["compatibility"].append({"model": "iPad14,1", "board": "J523AP", "os_build": "24B119"}),
            "missing hash": lambda r: r["artifacts"][0].pop("sha256"),
        }
        for label, mutate in broken.items():
            with self.subTest(label):
                release = self.release()
                mutate(release)
                data["releases"] = [release]
                self.save(data)
                with self.assertRaises(validate.ValidationError):
                    validate.validate_all(self.box.root)

    def test_required_requirements_cannot_be_dropped(self):
        data = self.installation()
        data["requirements"] = [item for item in data["requirements"] if item["id"] != "security-review"]
        self.save(data)
        with self.assertRaisesRegex(validate.ValidationError, "security-review"):
            validate.validate_all(self.box.root)


class CliTests(SandboxCase):
    def cli(self, *argv: str) -> tuple[int, str, str]:
        return run_cli("--root", str(self.box.root), *argv)

    def new_record(self, record_id: str = "octo-cli") -> tuple[int, str, str]:
        rel, _ = self.box.evidence()
        return self.cli("new", "--id", record_id, "--contributor", HANDLE, "--workstream", "device-matrix", "--model", "iPad13,8",
                        "--board", "J522AP", "--os-build", "24B119", "--agent", "human", "--claim", "Read-only inventory of one device.",
                        "--evidence", f"command-output:{rel}")

    def test_scaffold_check_and_submit_plan(self):
        code, out, err = self.new_record()
        self.assertEqual(code, 0, err)
        record = self.box.root / "data/contributions/octo-cli.json"
        self.assertTrue(record.is_file())
        code, out, err = self.cli("check", str(record))
        self.assertEqual(code, 0, err)
        self.assertIn("PASS", out)
        code, plan, err = self.cli("submit-plan", str(record))
        self.assertEqual(code, 0, err)
        self.assertIn("gh pr create --repo baney75/omarchy-on-ipad --base main", plan)
        self.assertIn(f"{HANDLE}:contrib/octo-cli", plan)
        for forbidden in ("gh pr merge", "--admin", "GH_TOKEN", "GITHUB_TOKEN", "auth login", "--auto"):
            self.assertNotIn(forbidden, plan)
        code, body, err = self.cli("pr-body", str(record))
        self.assertEqual(code, 0, err)
        self.assertIn("A human maintainer reviews this pull request", body)

    def test_scaffold_refuses_overwrite_and_bad_ids(self):
        self.assertEqual(self.new_record()[0], 0)
        code, _, err = self.new_record()
        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)
        code, _, err = self.new_record("../escape")
        self.assertEqual(code, 1)

    def test_check_refuses_records_outside_the_folder_and_private_data(self):
        stray = self.box.root / "stray.json"
        stray.write_text("{}", encoding="utf-8")
        self.assertEqual(self.cli("check", str(stray))[0], 1)
        rel, digest = self.box.evidence("notes.txt", "contact me at someone@example.com\n")
        record = self.box.record("octo-private", evidence=[{"kind": "command-output", "path": rel, "sha256": digest}])
        path = self.box.write(record)
        code, _, err = self.cli("check", str(path))
        self.assertEqual(code, 1)
        self.assertIn("email address", err)

    def test_lanes_json_matches_contract(self):
        code, out, _ = self.cli("lanes", "--json")
        self.assertEqual(code, 0)
        self.assertEqual([lane["id"] for lane in json.loads(out)], [lane["id"] for lane in contract.LANES])


class ResearchTaskTests(SandboxCase):
    def path(self, task: dict, name: str = "task.json") -> Path:
        path = self.box.root / "contributions" / HANDLE / "research" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task), encoding="utf-8")
        return path

    def check(self, task: dict, **flags) -> dict:
        return research.validate_task(self.path(task), self.box.progress, root=self.box.root, **flags)

    def test_local_result_evidence_must_exist_and_match_hash(self):
        task = suitable_task()
        task["result"]["evidence"] = [{"path": f"contributions/{HANDLE}/missing.txt", "sha256": SHA_ZERO}]
        with self.assertRaises(validate.ValidationError):
            self.check(task, final=True)
        rel, digest = self.box.evidence("result.txt", "Reproducible public result.\n")
        task["result"]["evidence"] = [{"path": rel, "sha256": SHA_ZERO}]
        with self.assertRaisesRegex(validate.ValidationError, "does not match"):
            self.check(task, final=True)
        task["result"]["evidence"][0]["sha256"] = digest
        self.check(task, final=True)
        path = self.path(task)
        record = self.box.record("octo-local-result", evidence=[{"kind": "research-task", "path": str(path.relative_to(self.box.root)), "sha256": sha(path)}])
        record_path = self.box.write(record)
        code, plan, err = run_cli("--root", str(self.box.root), "submit-plan", str(record_path))
        self.assertEqual(code, 0, err)
        self.assertIn(rel, next(line for line in plan.splitlines() if line.startswith("git add")))

    def test_suitable_conclusive_task_passes_final(self):
        task = self.check(suitable_task(), ready=True, final=True)
        self.assertTrue(research.is_complete(task))
        eligible, message = research.preflight_gate(task)
        self.assertTrue(eligible)
        self.assertIn(research.PREFLIGHT_SCOPE, message)
        self.assertIn("grants no device, exploit, install, merge, or publication authority", message)

    def test_preflight_gate_blocks_unknown_unverified_and_unsuitable(self):
        cases = {
            "unknown identity": lambda t: t["model_preflight"].update(identity_source="unknown"),
            "unknown model id": lambda t: t["agent"].update(model_id="unknown"),
            "unverified": lambda t: t["model_preflight"].update(verdict="unverified"),
            "unsuitable": lambda t: t["model_preflight"].update(verdict="unsuitable"),
            "general category": lambda t: t["model_preflight"].update(category="general"),
            "small utility": lambda t: t["model_preflight"].update(category="small_utility"),
            "no model card": lambda t: t["model_preflight"].update(model_card=None),
            "failed check": lambda t: t["model_preflight"]["task_checks"][0].update(outcome="fail"),
            "conflicting check": lambda t: t["model_preflight"]["task_checks"].append(dict(t["model_preflight"]["task_checks"][0], outcome="fail")),
            "duplicate check": lambda t: t["model_preflight"]["task_checks"].append(dict(t["model_preflight"]["task_checks"][0])),
            "obliterated without provenance": lambda t: t["model_preflight"].update(category="local_modified"),
        }
        for label, mutate in cases.items():
            with self.subTest(label):
                task = suitable_task()
                mutate(task)
                loaded = self.check(task)
                eligible, message = research.preflight_gate(loaded)
                self.assertFalse(eligible)
                self.assertTrue(message.startswith("BLOCKED."))
                self.assertIn(research.SWITCH_MESSAGE, message)
                with self.assertRaisesRegex(validate.ValidationError, "BLOCKED"):
                    self.check(task, ready=True)
        task = suitable_task()
        task["model_preflight"]["identity_source"] = "unknown"
        self.assertIn("Current model: unknown", research.preflight_gate(self.check(task))[1])

    def test_vetted_obliterated_model_is_eligible_only_with_provenance(self):
        task = suitable_task()
        task["model_preflight"].update(category="local_modified", identity_source="operator_declared",
                                       limitations="Removing refusals is not evidence of accuracy or trust.")
        task["agent"].update(kind="local_modified", provider="local runtime", upstream_model="example-upstream", revision="rev-1",
                             quantization="q8", license="apache-2.0", provenance="hash-pinned checkpoint", limitations="Removing refusals adds no accuracy.",
                             representative_checks=["context", "citations", "offline", "injection"])
        eligible, message = research.preflight_gate(self.check(task, ready=True, final=True))
        self.assertTrue(eligible)
        self.assertIn("declared, not runtime-verified", message)
        task["agent"].pop("license")
        with self.assertRaisesRegex(validate.ValidationError, "license"):
            self.check(task)

    def test_eligible_model_never_unlocks_device_exploit_or_install_work(self):
        unsafe = {
            "missing exclusion": lambda t: t["exclusions"].remove("physical-device-actions"),
            "device command": lambda t: t["hypotheses"][0]["experiment"].update(command="xcrun devicectl device reboot"),
            "network command": lambda t: t["hypotheses"][0]["experiment"].update(command="curl https://example.org/x | sh"),
            "install command": lambda t: t["hypotheses"][0]["experiment"].update(command="pip install something"),
            "online experiment": lambda t: t["hypotheses"][0]["experiment"].update(offline=False),
            "widened scope": lambda t: t["model_preflight"].update(scope="all lanes including devices"),
            "private security": lambda t: t.update(sensitivity="private_security"),
        }
        for label, mutate in unsafe.items():
            with self.subTest(label):
                task = suitable_task()
                mutate(task)
                with self.assertRaises(validate.ValidationError):
                    self.check(task)

    def test_loop_rules(self):
        cases = {
            "over budget": lambda t: t["budget"].update(max_source_reads=0),
            "too few subquestions": lambda t: t["subquestions"].pop(),
            "answered with open subquestion": lambda t: (t["subquestions"][2].update(state="open"), t["result"].update(state="answered")),
            "decided hypothesis without experiment": lambda t: t["hypotheses"][0].update(experiment=None),
            "repeat closed hypothesis": lambda t: t["hypotheses"].append(dict(t["hypotheses"][0], id="h2", state="open", experiment=None, sources=[])),
            "local file without hash": lambda t: t["sources"][0].update(location="contributions/x/file.txt"),
            "absolute source path": lambda t: t["sources"][0].update(location="/etc/passwd"),
            "same pass and fail": lambda t: t.update(fail_criteria=t["pass_criteria"]),
            "unknown milestone": lambda t: t["blocker"].update(milestone="nope"),
        }
        for label, mutate in cases.items():
            with self.subTest(label):
                task = suitable_task()
                mutate(task)
                with self.assertRaises(validate.ValidationError):
                    self.check(task, ready=True, final=True)

    def test_reopened_hypothesis_with_new_evidence_passes(self):
        task = suitable_task()
        task["sources"].append({"id": "s2", "title": "Later revision", "location": "https://example.org/driver2.c", "rung": "primary", "revision": "def456", "date_read": "2026-11-07"})
        task["hypotheses"].append(dict(task["hypotheses"][0], id="h2", state="open", experiment=None, sources=[], reopened_with=["s2"]))
        self.check(task, ready=True, final=True)

    def test_budget_exhaustion_and_blocked_are_not_completion(self):
        for state in ("budget_exhausted", "blocked"):
            task = suitable_task()
            task["subquestions"][2]["state"] = "open"
            task["result"].update(state=state, claim="")
            loaded = self.check(task, ready=True, final=True)
            self.assertFalse(research.is_complete(loaded))
        task = suitable_task()
        task["result"]["state"] = "open"
        with self.assertRaises(validate.ValidationError):
            self.check(task, ready=True, final=True)

    def test_cli_scaffold_preflight_and_prompt(self):
        rel = f"contributions/{HANDLE}/research/octo-task.json"
        code, out, err = run_cli("--root", str(self.box.root), "research", "new", "--id", "octo-task", "--contributor", HANDLE,
                                 "--workstream", "j522-linux", "--milestone", "hardware", "--model", "iPad13,8", "--board", "J522AP",
                                 "--os-build", "24B119", "--scope", "Offline reading of public upstream sources only.",
                                 "--question", "Does the pinned upstream driver list this board?", "--falsifier", "The board is absent at the pinned revision.")
        self.assertEqual(code, 0, err)
        self.assertIn("first step: run the model suitability preflight", out)
        task = str(self.box.root / rel)
        scaffold = json.loads(Path(task).read_text(encoding="utf-8"))
        self.assertEqual(scaffold["model_preflight"]["verdict"], "unverified")
        self.assertEqual(scaffold["model_preflight"]["identity_source"], "unknown")
        self.assertEqual(scaffold["budget"], research.DEFAULT_BUDGET)
        code, out, _ = run_cli("--root", str(self.box.root), "research", "preflight", task)
        self.assertEqual(code, 2)
        self.assertIn("Current model: unknown", out)
        self.assertIn(research.SWITCH_MESSAGE, out)
        self.assertEqual(run_cli("--root", str(self.box.root), "research", "check", task)[0], 0)
        code, _, err = run_cli("--root", str(self.box.root), "research", "check", task, "--ready")
        self.assertEqual(code, 1)
        self.assertIn("REPLACE", err)
        code, prompt, _ = run_cli("--root", str(self.box.root), "research", "prompt", task)
        self.assertEqual(code, 0)
        self.assertNotIn("[[", prompt)
        self.assertLess(prompt.index("STEP 0. MODEL SUITABILITY PREFLIGHT"), prompt.index("STEP 1. INTAKE"))
        self.assertIn(research.SWITCH_MESSAGE, prompt)
        self.assertIn("iPad13,8 / J522AP / 24B119", prompt)
        self.assertIn("25 source reads or 45 minutes", prompt)

    def test_research_task_evidence_enters_the_contribution_pipeline(self):
        path = self.path(suitable_task(), "octo-dcp-question.json")
        rel = str(path.relative_to(self.box.root))
        record = self.box.record("octo-research", workstream="j522-linux", evidence=[{"kind": "research-task", "path": rel, "sha256": sha(path)}])
        self.box.check(record, submission=True)
        unfinished = suitable_task()
        unfinished["result"]["state"] = "open"
        path = self.path(unfinished, "octo-unfinished.json")
        record = self.box.record("octo-unfinished", workstream="j522-linux", evidence=[{"kind": "research-task", "path": str(path.relative_to(self.box.root)), "sha256": sha(path)}])
        with self.assertRaises(validate.ValidationError):
            self.box.check(record, submission=True)

    def test_local_model_task_scaffolds_but_cannot_start_unverified(self):
        for kind in ("local", "local_modified"):
            with self.subTest(kind=kind):
                code, _, err = run_cli("--root", str(self.box.root), "research", "new", "--id", f"octo-{kind.replace('_', '-')}",
                    "--contributor", HANDLE, "--agent-kind", kind, "--workstream", "j522-linux", "--milestone", "hardware",
                    "--model", "iPad13,8", "--board", "J522AP", "--os-build", "24B119",
                    "--scope", "Offline reading of public upstream sources only.", "--question", "Does the pinned driver list this board?",
                    "--falsifier", "The board is absent at the pinned revision.")
                self.assertEqual(code, 0, err)
                path = self.box.root / f"contributions/{HANDLE}/research/octo-{kind.replace('_', '-')}.json"
                self.assertEqual(run_cli("--root", str(self.box.root), "research", "preflight", str(path))[0], 2)
                self.assertEqual(run_cli("--root", str(self.box.root), "research", "check", str(path), "--ready")[0], 1)

    def test_published_schema_admits_required_preflight_contract(self):
        schema = json.loads((ROOT / "schemas/research-task.schema.json").read_text())
        task = suitable_task()
        self.assertLessEqual(set(schema["required"]), set(task))
        self.assertLessEqual(set(task), set(schema["properties"]))
        self.assertIn("model_preflight", schema["required"])
        preflight = schema["properties"]["model_preflight"]
        self.assertEqual(set(preflight["required"]), set(task["model_preflight"]))
        self.assertEqual(set(preflight["properties"]), set(task["model_preflight"]))
        self.assertFalse(preflight["additionalProperties"])
        self.assertEqual(preflight["properties"]["scope"]["const"], research.PREFLIGHT_SCOPE)


class LaneAndPolicyTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_lane_table_routes_preflight_by_scope(self):
        ids = [lane["id"] for lane in contract.LANES]
        self.assertEqual(ids, ["site-design", "docs-copy", "tooling-tests-schemas", "driver-kernel", "bug-fix", "device-metadata", "offline-research", "private-security"])
        preflight = {lane["id"]: lane["research_preflight"] for lane in contract.LANES}
        self.assertEqual(preflight["offline-research"], "required")
        self.assertEqual({key for key, value in preflight.items() if value == "required"}, {"offline-research"})
        self.assertEqual({key for key, value in preflight.items() if value == "conditional"}, {"driver-kernel", "bug-fix"})
        for lane in ("site-design", "docs-copy", "tooling-tests-schemas", "device-metadata"):
            self.assertEqual(preflight[lane], "none")
        private = next(lane for lane in contract.LANES if lane["id"] == "private-security")
        self.assertEqual(private["validation"], [])
        self.assertEqual(private["policies"], ["SECURITY.md"])
        for lane in contract.LANES:
            for policy in lane["policies"]:
                self.assertTrue((ROOT / policy).is_file(), f"{lane['id']}: {policy}")
            if lane["id"] != "private-security":
                self.assertTrue(any("make check" in command for command in lane["validation"]), lane["id"])

    def test_agents_md_is_canonical_and_matches_the_lane_table(self):
        agents = self.read("AGENTS.md")
        rows = {match.group(1): match.group(0) for match in re.finditer(r"^\| `([a-z-]+)` \|.*$", agents, re.M)}
        for lane in contract.LANES:
            self.assertIn(lane["id"], rows)
            self.assertIn(f"| {lane['research_preflight']} |", rows[lane["id"]])
        self.assertIn(research.SWITCH_MESSAGE, agents)
        self.assertIn("Native Linux has not booted on the reference iPad.", agents)
        self.assertLess(agents.index("Classify the work into one lane"), agents.index("## Research model preflight"))
        claude = self.read("CLAUDE.md")
        self.assertIn("[`AGENTS.md`](AGENTS.md)", claude)
        self.assertIn("AGENTS.md#contribution-lanes", claude)
        self.assertIn("AGENTS.md#research-model-preflight", claude)
        self.assertLess(len(claude.splitlines()), 20)
        self.assertNotIn(research.SWITCH_MESSAGE, claude)  # one copy of policy text, in AGENTS.md

    def test_playbook_and_prompt_carry_the_gate(self):
        playbook = self.read("docs/RESEARCH-PLAYBOOK.md")
        for phrase in (research.SWITCH_MESSAGE, "25 source reads or 45 minutes", "Budget exhaustion", "loopback", "Removing refusals" if "Removing refusals" in playbook else "removing refusals", "no preferred model ids"):
            self.assertIn(phrase.lower(), playbook.lower())
        prompt = self.read("docs/RESEARCH-PROMPT.md")
        self.assertIn(contribute.PROMPT_START, prompt)
        self.assertIn(contribute.PROMPT_END, prompt)
        self.assertIn("[[SWITCH_MESSAGE]]", prompt)

    def test_bug_report_form_has_required_fields_and_triage_first(self):
        form = self.read(".github/ISSUE_TEMPLATE/bug-report.yml")
        self.assertLess(form.index("security/advisories/new"), form.index("id: triage"))
        self.assertLess(form.index("id: triage"), form.index("id: lane"))
        for field in ("triage", "lane", "version", "reproduction", "expected", "actual", "reproducibility", "impact", "agent"):
            block = form.split(f"id: {field}\n", 1)[1].split("  - type:", 1)[0]
            self.assertIn("required: true", block, field)
        lanes = re.findall(r"^        - ([a-z-]+)$", form.split("id: lane", 1)[1].split("  - type:", 1)[0], re.M)
        self.assertLessEqual(set(lanes) - {"not"}, {lane["id"] for lane in contract.LANES})
        self.assertNotIn("private-security", lanes)
        for warning in ("exploit samples", "UDIDs", "untrusted data"):
            self.assertIn(warning, form)
        starter = self.read("docs/BUG-FIX-STARTER.md")
        for phrase in ("untrusted data", "Never run code", "claim", "Fixes #<issue-number>", "Do not merge", "fails on main"):
            self.assertIn(phrase, starter)

    def test_pr_template_and_governance(self):
        template = self.read(".github/PULL_REQUEST_TEMPLATE.md")
        for phrase in ("## Lane", "## Verification evidence", "failing before", "passing after", "Negative tests", "Artifact hashes", "Coverage limits", "## Security questions", "does not mark this pull request reviewed", "CI passing alone is not approval"):
            self.assertIn(phrase, template)
        governance = self.read("docs/GOVERNANCE.md")
        for phrase in ("## Contributor vetting", "Never automatic", "public GitHub handle", "Revocation", "No workflow grants repository access", "Trusted is not exempt"):
            self.assertIn(phrase, governance)
        workflows = " ".join(path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml"))
        for trigger in ("issues:", "issue_comment:", "pull_request_target:"):
            self.assertNotIn(trigger, workflows)

    def test_subpage_truth_panel_does_not_inherit_the_hero_grid_area(self):
        css = self.read("site/assets/site.css")
        self.assertRegex(css, r"\.install__truth \{ grid-area: auto;")
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        for token in ("--text-muted", "--signal", "--risk"):
            self.assertIn(token, css)

    def test_new_text_has_no_em_or_en_dashes(self):
        files = ["AGENTS.md", "CLAUDE.md", "docs/RESEARCH-PLAYBOOK.md", "docs/RESEARCH-PROMPT.md", "docs/CONTRIBUTION-API.md", "docs/BUG-FIX-STARTER.md",
                 "platform/README.md", ".github/ISSUE_TEMPLATE/bug-report.yml", ".github/PULL_REQUEST_TEMPLATE.md", "data/installation.json",
                 "scripts/contract.py", "scripts/research.py", "tools/contribute.py"]
        files += [str(path.relative_to(ROOT)) for path in (ROOT / "schemas").glob("*.json")]
        for path in files:
            self.assertNotRegex(self.read(path), "[\u2013\u2014]", path)


if __name__ == "__main__":
    unittest.main()
