from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


validate = load("validate", ROOT / "scripts/validate.py")
import sys
sys.modules["validate"] = validate
build_site = load("build_site", ROOT / "scripts/build_site.py")
collector = load("collect_readonly", ROOT / "tools/collect_readonly.py")
workflow_policy = load("workflow_policy", ROOT / "scripts/workflow_policy.py")


class ProjectTests(unittest.TestCase):
    def test_progress_and_contributions_validate(self):
        validate.validate_all(ROOT)

    def test_dashboard_build_has_no_placeholders_or_external_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build_site.build(ROOT, output, "https://github.com/baney75/omarchy-on-ipad", "https://baney75.github.io/omarchy-on-ipad/")
            page = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("{{", page)
            self.assertIn('aria-label="Milestone checks passed: 5 of 29"', page)
            self.assertIn("Native Linux has not booted", page)
            self.assertNotRegex(page, r'src=["\']https://')
            self.assertNotIn('<link rel="stylesheet" href="http', page)
            self.assertTrue((output / "assets/mark.svg").exists())
            self.assertTrue((output / "schemas/progress.schema.json").exists())

    def test_readonly_collector_drops_identifiers(self):
        payload = json.loads((ROOT / "tests/fixtures/devicectl.json").read_text(encoding="utf-8"))
        clean = collector.sanitize(payload)
        rendered = json.dumps(clean)
        self.assertEqual(len(clean["devices"]), 1)
        self.assertEqual(clean["devices"][0]["model"], "iPad13,8")
        self.assertEqual(clean["devices"][0]["board"], "J522AP")
        for forbidden in ("SECRET-DEVICE-ID", "Private device name", "PRIVATE123", "192.0.2.2", "serial", "identifier"):
            self.assertNotIn(forbidden, rendered)

    def test_current_truth_cannot_be_softened(self):
        data = json.loads((ROOT / "data/progress.json").read_text(encoding="utf-8"))
        data["goal"]["current_truth"] = "Everything is progressing."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(validate.ValidationError):
                validate.validate_progress(path)

    def test_builder_refuses_unmarked_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-ours"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_site.build(ROOT, output, "https://github.com/baney75/omarchy-on-ipad", "https://baney75.github.io/omarchy-on-ipad/")
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_workflows_are_pinned_and_avoid_pull_request_target(self):
        self.assertEqual(workflow_policy.main(), 0)
        codeql = (ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
        self.assertIn("  actions: read\n", codeql)
        self.assertIn("  workflow_dispatch:\n", codeql)
        self.assertIn("github.event.repository.private == false", codeql)

    def test_live_progress_form_preserves_truth_and_safety_gates(self):
        form = (ROOT / ".github/ISSUE_TEMPLATE/progress-update.yml").read_text(encoding="utf-8")
        self.assertIn("live public work log", form)
        self.assertIn("not proof that Linux booted or Omarchy was installed", form)
        self.assertIn("did not use malformed input, a device write, reboot/recovery action, or exploit payload", form)


if __name__ == "__main__":
    unittest.main()
