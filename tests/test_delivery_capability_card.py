import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools/delivery_capability_card.py"
spec = importlib.util.spec_from_file_location("delivery_card", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CapabilityCard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "viewer.html"
        self.artifact.write_text("<h1>Saved viewer</h1>")
        self.config = {"schema": "sapote.delivery_capability_card.v1", "artifact": {"path": "viewer.html", "sha256": mod.sha(self.artifact), "bytes": self.artifact.stat().st_size}}

    def tearDown(self):
        self.tmp.cleanup()

    def receipt(self, value, kind="program_behavior", adapter="delivery_check_v1", name="receipt.json", **more):
        p = self.root / name
        p.write_text(json.dumps(value))
        self.config.setdefault("checks", []).append({"kind": kind, "adapter": adapter, "path": name, "sha256": mod.sha(p), **more})
        return p

    def check(self, kind="program_behavior"):
        return next(r for r in mod.build(self.config, self.root)["checks"] if r["kind"] == kind)

    def native(self, kind="program_behavior", result="PASS"):
        return {"schema": "sapote.delivery_check.v1", "kind": kind, "artifact": {"sha256": self.config["artifact"]["sha256"], "bytes": self.config["artifact"]["bytes"]}, "method": "purposeful fixture", "scope": "Fixture behavior only, not rendering.", "result": result}

    def test_no_selected_check_is_not_performed(self):
        self.assertEqual(self.check()["state"], "NOT_PERFORMED")

    def test_bound_program_claim_is_scope_limited(self):
        self.receipt(self.native())
        r = self.check()
        self.assertEqual(r["state"], "BOUND_REPORTED_PASS")
        self.assertTrue(r["producer_claim_only"])
        self.assertIn("not rendering", r["scope"])
        self.assertEqual(self.check("browser_compatibility")["state"], "NOT_PERFORMED")

    def test_missing_receipt_distinct_from_no_check(self):
        self.config["checks"] = [{"kind": "program_behavior", "adapter": "delivery_check_v1", "path": "missing.json", "sha256": "0" * 64}]
        self.assertEqual(self.check()["state"], "RECEIPT_MISSING")

    def test_unpinned_receipt_is_hold(self):
        self.receipt(self.native())
        del self.config["checks"][0]["sha256"]
        self.assertEqual(self.check()["state"], "RECEIPT_REVISION_NOT_PINNED")

    def test_receipt_drift_is_hold(self):
        p = self.receipt(self.native())
        p.write_text('{}')
        self.assertEqual(self.check()["state"], "RECEIPT_HASH_MISMATCH")

    def test_legacy_pass_without_artifact_hash_is_unbound(self):
        self.receipt({"combined": {"status": "PASS"}, "scope": "DOM harness only"}, adapter="unbound_legacy")
        self.assertEqual(self.check()["state"], "RECEIPT_UNBOUND")

    def test_stale_receipt_cannot_pass_new_exact_target(self):
        value = self.native()
        value["artifact"]["sha256"] = "0" * 64
        self.receipt(value)
        self.assertEqual(self.check()["state"], "RECEIPT_STALE_FOR_TARGET")

    def test_changed_artifact_cannot_reuse_pass(self):
        self.receipt(self.native())
        self.artifact.write_text("changed")
        self.assertEqual(self.check()["state"], "ARTIFACT_BINDING_HOLD")
        self.assertEqual(mod.build(self.config, self.root)["artifact"]["state"], "ARTIFACT_CHANGED")

    def test_bound_fail_and_unrun_are_not_passes(self):
        for result in ["FAIL", "NOT_PERFORMED", "HELD"]:
            self.config["checks"] = []
            self.receipt(self.native(result=result))
            self.assertEqual(self.check()["state"], "BOUND_REPORTED_" + result)

    def test_kind_cannot_be_relabelled(self):
        self.receipt(self.native("data_syntax"), kind="browser_compatibility")
        self.assertEqual(self.check("browser_compatibility")["state"], "RECEIPT_INVALID")

    def test_browser_pass_needs_environment_and_date(self):
        self.receipt(self.native("browser_compatibility"), kind="browser_compatibility")
        self.assertEqual(self.check("browser_compatibility")["state"], "BROWSER_RECEIPT_ENVIRONMENT_UNSPECIFIED")

    def test_browser_pass_remains_environment_specific(self):
        data = self.native("browser_compatibility")
        data.update(checked_at="2026-10-24T12:00:00-07:00", environment={"browser": "FixtureBrowser", "browser_version": "1.0", "os": "FixtureOS"})
        self.receipt(data, kind="browser_compatibility")
        r = self.check("browser_compatibility")
        self.assertEqual(r["state"], "BOUND_REPORTED_PASS")
        self.assertEqual(r["environment"]["browser"], "FixtureBrowser")

    def test_invalid_or_undated_browser_context_is_not_pass(self):
        for stamp in ["yesterday", "2026-10-24T12:00:00"]:
            self.config["checks"] = []
            data = self.native("browser_compatibility")
            data.update(checked_at=stamp, environment={"browser": "FixtureBrowser", "browser_version": "1.0", "os": "FixtureOS"})
            self.receipt(data, kind="browser_compatibility")
            self.assertEqual(self.check("browser_compatibility")["state"], "BROWSER_RECEIPT_ENVIRONMENT_UNSPECIFIED")

    def test_declared_api_is_not_compatibility_measurement(self):
        p = self.root / "producer.md"
        p.write_text("Requires DecompressionStream.")
        self.config["declared_capabilities"] = [{"name": "DecompressionStream", "requirement": "REQUIRED", "evidence": {"path": p.name, "sha256": mod.sha(p), "excerpt": "Requires DecompressionStream."}}, {"name": "WebGL", "requirement": "NOT_DECLARED"}]
        data = mod.build(self.config, self.root)
        self.assertEqual(data["declared_capabilities"][0]["state"], "SOURCE_BOUND_DECLARATION_UNMEASURED")
        self.assertEqual(data["declared_capabilities"][0]["measured_compatibility"], "NOT_MEASURED_BY_THIS_CARD")
        self.assertEqual(data["declared_capabilities"][1]["state"], "NOT_DECLARED")

    def test_stale_and_misquoted_declaration_are_held(self):
        p = self.root / "producer.md"
        p.write_text("Requires API.")
        self.config["declared_capabilities"] = [{"name": "API", "requirement": "REQUIRED", "evidence": {"path": p.name, "sha256": mod.sha(p), "excerpt": "Not there"}}]
        self.assertEqual(mod.build(self.config, self.root)["declared_capabilities"][0]["state"], "DECLARATION_EXCERPT_NOT_FOUND")
        p.write_text("changed")
        self.assertEqual(mod.build(self.config, self.root)["declared_capabilities"][0]["state"], "DECLARATION_SOURCE_CHANGED")

    def test_static_receipt_binds_only_its_member_and_scope(self):
        data = {"schema": "sapote.standalone_delivery.receipt.v1", "status": "PASS_STATIC_CONTRACT", "files_checked": [{"path": "viewer.html", "sha256": self.config["artifact"]["sha256"], "bytes": self.config["artifact"]["bytes"], "state": "MATCH"}], "errors": [], "limits": ["No execution"]}
        self.receipt(data, kind="static_dependencies", adapter="tb03_static", member="viewer.html")
        self.assertEqual(self.check("static_dependencies")["state"], "BOUND_REPORTED_PASS")
        self.config["checks"][0]["member"] = "different.html"
        self.assertEqual(self.check("static_dependencies")["state"], "RECEIPT_UNBOUND")

    def test_data_syntax_hash_receipt_does_not_create_program_pass(self):
        self.receipt({"status": "PASS_DATA_BINDINGS_AND_JS_SYNTAX", "HTML_sha256": self.config["artifact"]["sha256"], "standalone_HTML_bytes": self.config["artifact"]["bytes"], "errors": []}, kind="data_syntax", adapter="locus_data_syntax")
        self.assertEqual(self.check("data_syntax")["state"], "BOUND_REPORTED_PASS")
        self.assertEqual(self.check()["state"], "NOT_PERFORMED")

    def test_pdf_visual_receipt_cannot_validate_html(self):
        self.receipt({"status": "RENDERED_PAGES_INSPECTED", "reviewed_PDFs": [{"path": "/report.pdf", "sha256": "0" * 64}]}, kind="visual_review", adapter="report_visual")
        self.assertEqual(self.check("visual_review")["state"], "RECEIPT_SCOPE_MISMATCH")

    def test_html_card_escapes_receipt_scope(self):
        value = self.native()
        value["scope"] = '<script src="https://example.org/a.js"></script>'
        self.receipt(value)
        rendered = mod.render(mod.build(self.config, self.root))
        self.assertNotIn("<script", rendered)
        self.assertIn("&lt;script", rendered)

    def test_output_cannot_overwrite_any_input(self):
        p = self.root / "config.json"
        p.write_text(json.dumps(self.config))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            mod.main(["--config", str(p), "--json-out", str(self.artifact), "--replace-candidate"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.artifact.read_text(), "<h1>Saved viewer</h1>")

    def test_same_config_replays_and_changed_output_needs_explicit_flag(self):
        p = self.root / "config.json"
        p.write_text(json.dumps(self.config))
        output = self.root / "card.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main(["--config", str(p), "--json-out", str(output)]), 0)
            self.assertEqual(mod.main(["--config", str(p), "--json-out", str(output)]), 0)
        output.write_text("old derived candidate")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            mod.main(["--config", str(p), "--json-out", str(output)])


if __name__ == "__main__":
    unittest.main()
