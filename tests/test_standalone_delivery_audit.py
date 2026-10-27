"""Behavioral regression fixtures, no scientific data or browser required."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

TOOL = Path(__file__).resolve().parents[1] / "tools/standalone_delivery_audit.py"
spec = importlib.util.spec_from_file_location("standalone_audit", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DeliveryAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, entries):
        rows = []
        for name, text in entries.items():
            b = text.encode()
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
            rows.append({"path": name, "bytes": len(b), "sha256": mod.digest(b)})
        return {"schema": mod.SCHEMA, "entrypoints": ["index.html"], "files": rows}

    def check(self, entries, optional=None):
        manifest = self.make(entries)
        if optional:
            manifest["optional_provenance"] = optional
        return mod.audit(manifest, mod.Folder(self.root))

    def codes(self, result):
        return {r["code"] for r in result["errors"]}

    def test_inline_only_and_fragment(self):
        r = self.check({"index.html": '<h1 id="gene">Genes</h1><a href="#gene">go</a><img src="data:image/png;base64,AA==">'})
        self.assertEqual(r["status"], "PASS_STATIC_CONTRACT")
        self.assertEqual(r["browser_visual_inspection"], "NOT_PERFORMED")

    def test_css_asset_chain_and_internal_parent(self):
        r = self.check({"index.html": '<link rel="stylesheet" href="styles/main.css">',
                        "styles/main.css": '@import "detail.css";body{background:url(../art.svg)}',
                        "styles/detail.css": "body{color:black}", "art.svg": "<svg/>"})
        self.assertEqual(r["status"], "PASS_STATIC_CONTRACT")
        self.assertEqual(r["reference_counts"]["RESOLVES_TO_BOUND_MEMBER"], 3)

    def test_missing_dependency_is_not_no_hit(self):
        r = self.check({"index.html": '<script src="lost.js"></script>'})
        self.assertIn("REFERENCE_NOT_IN_MANIFEST", self.codes(r))

    def test_unavailable_declared_dependency(self):
        m = self.make({"index.html": '<img src="art.svg">', "art.svg": "<svg/>"})
        (self.root / "art.svg").unlink()
        r = mod.audit(m, mod.Folder(self.root))
        self.assertIn("DECLARED_FILE_UNAVAILABLE", self.codes(r))
        self.assertIn("REFERENCE_FILE_UNAVAILABLE", self.codes(r))

    def test_exact_bytes_detect_drift(self):
        m = self.make({"index.html": "first"})
        (self.root / "index.html").write_text("later")
        self.assertIn("EXACT_BYTES_MISMATCH", self.codes(mod.audit(m, mod.Folder(self.root))))

    def test_remote_runtime_blocked_navigation_allowed(self):
        r = self.check({"index.html": '<a href="https://example.org/paper">source</a><script src="https://cdn.example.org/viewer.js"></script>'})
        self.assertEqual(r["reference_counts"]["OPTIONAL_EXTERNAL_NAVIGATION_NOT_FETCHED"], 1)
        self.assertIn("EXTERNAL_RUNTIME_OR_NONPORTABLE_REFERENCE", self.codes(r))

    def test_optional_source_anchor_explicitly_held(self):
        url = "file:///unavailable/source.tsv"
        r = self.check({"index.html": '<a href="' + url + '">Original source</a>'},
                       [{"from": "index.html", "url": url, "reason": "Provenance-only source; full table is embedded."}])
        self.assertEqual(r["status"], "PASS_STATIC_CONTRACT")
        self.assertEqual(r["reference_counts"]["OPTIONAL_PROVENANCE_NOT_CHECKED"], 1)

    def test_runtime_cannot_be_downgraded(self):
        url = "https://cdn.example.org/a.js"
        r = self.check({"index.html": '<script src="' + url + '"></script>'},
                       [{"from": "index.html", "url": url, "reason": "Attempted exemption"}])
        self.assertIn("EXTERNAL_RUNTIME_OR_NONPORTABLE_REFERENCE", self.codes(r))
        self.assertIn("UNUSED_OPTIONAL_PROVENANCE_DECLARATION", self.codes(r))

    def test_executable_provenance_and_ambiguous_attributes_refused(self):
        url = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "provenance declaration"):
            self.check({"index.html": '<a href="' + url + '">bad source</a>'},
                       [{"from": "index.html", "url": url, "reason": "Attempted exemption"}])
        r = self.check({"index.html": '<script src="https://cdn.example.org/a.js" src="a.js"></script>', "a.js": ""})
        self.assertIn("DUPLICATE_HTML_ATTRIBUTE_REQUIRES_REVIEW", self.codes(r))

    def test_encoded_traversal_and_absolute_paths(self):
        r = self.check({"index.html": '<img src="%2e%2e/out.svg"><img src="/Users/me/a.svg">'})
        self.assertEqual(sum(e["code"] == "REFERENCE_ESCAPES_DELIVERY_ROOT" for e in r["errors"]), 2)

    def test_symlink_refused_without_reading_target(self):
        m = self.make({"index.html": "<h1>ok</h1>", "asset.txt": "inside"})
        (self.root / "asset.txt").unlink()
        (self.root / "asset.txt").symlink_to(TOOL)
        self.assertIn("DECLARED_FILE_UNAVAILABLE", self.codes(mod.audit(m, mod.Folder(self.root))))

    def test_missing_fragment(self):
        r = self.check({"index.html": '<a href="details.html#gene">go</a>', "details.html": '<h1 id="other">other</h1>'})
        self.assertIn("MISSING_HTML_FRAGMENT", self.codes(r))

    def test_external_svg_resource_and_css_import(self):
        r = self.check({"index.html": '<img src="a.svg"><link href="a.css" rel="stylesheet">',
                        "a.svg": '<svg><image href="https://example.org/image.png"/></svg>',
                        "a.css": '@import "https://example.org/style.css";'})
        self.assertEqual(sum(e["code"] == "EXTERNAL_RUNTIME_OR_NONPORTABLE_REFERENCE" for e in r["errors"]), 2)

    def test_unsupported_base_and_srcset_fail_closed(self):
        r = self.check({"index.html": '<base href="https://example.org/"><img srcset="a.png 1x,b.png 2x">'})
        self.assertIn("HTML_BASE_REQUIRES_REVIEW", self.codes(r))
        self.assertIn("SRCSET_REQUIRES_REVIEW", self.codes(r))

    def test_dynamic_program_not_claimed_executed(self):
        r = self.check({"index.html": '<script>fetch(location.hash.slice(1))</script>'})
        self.assertEqual(r["javascript_execution"], "NOT_PERFORMED")
        self.assertEqual(r["program_lexical_hints"][0]["lexical_hints_only"], ["fetch"])

    def test_duplicate_manifest_refused(self):
        m = self.make({"index.html": "<h1>ok</h1>"})
        m["files"] += m["files"]
        with self.assertRaisesRegex(ValueError, "duplicate manifest"):
            mod.audit(m, mod.Folder(self.root))

    def test_zip_read_without_extraction(self):
        m = self.make({"index.html": '<img src="a.svg">', "a.svg": "<svg/>"})
        p = self.root / "delivery.zip"
        with zipfile.ZipFile(p, "w") as z:
            for row in m["files"]:
                z.write(self.root / row["path"], row["path"])
        store = mod.Archive(p)
        try:
            self.assertEqual(mod.audit(m, store)["status"], "PASS_STATIC_CONTRACT")
        finally:
            store.z.close()

    def test_receipt_cannot_write_into_audited_root(self):
        m = self.make({"index.html": "<h1>ok</h1>"})
        p = self.root / "manifest.json"
        p.write_text(json.dumps(m))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            mod.main(["--root", str(self.root), "--manifest", str(p), "--receipt", str(self.root / "receipt.json")])
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse((self.root / "receipt.json").exists())

    def test_zip_member_escape_duplicate_and_symlink_refused(self):
        for name, mode, duplicate in [("../escape", 0, False), ("safe.txt", 0, True), ("link", stat.S_IFLNK | 0o777, False)]:
            p = self.root / "bad.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(p, "w") as z:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    z.writestr(info, "x")
                    if duplicate:
                        z.writestr(name, "y")
            with self.assertRaises(ValueError):
                mod.Archive(p)


if __name__ == "__main__":
    unittest.main()
