"""Tests for tools/archive_leak_scan.py (archive-content private-ID leak guard).

Closes future_improvements Item 3: the leak-audit chain scanned archives only for cache/hygiene
artifacts (preflight_zip_hygiene) or private IDs inside a single .xlsx (audit_public_cut) — a strain
ID buried in a committed .zip/.docx/.pptx member escaped every automated gate. These tests build
synthetic archives in tmp_path (never in the tree, and only with clearly-synthetic IDs) and lock:
  * private IDs in zipped-XML prose are caught (the generalized xlsx-incident class),
  * nested archives are recursed,
  * the public natural-product carve-out (enterocin AS-48) is NOT flagged,
  * held-cohort prose is caught,
  * SID is gated by --include-sid,
  * a clean archive stays clean (no false positive),
and — belt and suspenders — that the tool reuses the redact_public_tier private-ID SSOT rather than
hand-rolling its own pattern (so it can't drift from the enforced redactor).
"""
import importlib.util
import io
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = importlib.util.spec_from_file_location("archive_leak_scan", TOOLS / "archive_leak_scan.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_archive(tmp_path, name, entries):
    """entries: dict of arcname -> str/bytes content. Returns the archive Path."""
    p = tmp_path / name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for arc, content in entries.items():
            zf.writestr(arc, content)
    p.write_bytes(buf.getvalue())
    return p


def _real(findings):
    return [f for f in findings if f["kind"] in ("private_identifier", "held_phrase", "denylist_term")]


def test_clean_archive_passes(tmp_path):
    m = _load()
    zp = _make_archive(tmp_path, "clean.zip", {"mamey/cli.py": "x = 1\n", "README.md": "# hi\n"})
    assert _real(m.scan_archive(zp)) == []


def test_private_id_in_zipped_xml_prose_caught(tmp_path):
    """The xlsx-incident class, generalized: an ID in a .docx word/document.xml prose part."""
    m = _load()
    zp = _make_archive(tmp_path, "deliverable.docx", {
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "<w:p>Draft on sequenced isolate AS-777 (moss host).</w:p>",
    })
    hits = _real(m.scan_archive(zp))
    assert any(f["kind"] == "private_identifier" and f["token"] == "AS-777" for f in hits), hits


def test_nested_archive_recursed(tmp_path):
    m = _load()
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("result/regions.gbk", "LOCUS strain AJS-31 region001\n")
    zp = _make_archive(tmp_path, "antismash_results.zip",
                       {"run1/inner.zip": inner.getvalue(), "run1/log.txt": "ok"})
    hits = _real(m.scan_archive(zp))
    assert any(f["token"] == "AJS-31" for f in hits), hits


def test_public_carveout_not_flagged(tmp_path):
    """enterocin AS-48 is a real public bacteriocin — the SSOT excludes it, so must not flag."""
    m = _load()
    zp = _make_archive(tmp_path, "carveout.zip",
                       {"notes.txt": "strain produces enterocin AS-48, a published bacteriocin"})
    assert _real(m.scan_archive(zp)) == []


def test_held_phrase_caught(tmp_path):
    m = _load()
    zp = _make_archive(tmp_path, "held.pptx",
                       {"ppt/slides/slide1.xml": "<p>cohort split (AS held) - 12 strains</p>"})
    hits = _real(m.scan_archive(zp))
    assert any(f["kind"] == "held_phrase" for f in hits), hits


def test_sid_gated_by_flag(tmp_path):
    m = _load()
    zp = _make_archive(tmp_path, "sid.zip", {"members.csv": "strain\nSID12345\n"})
    assert _real(m.scan_archive(zp, as_only=True)) == []            # default: SID public
    hits = _real(m.scan_archive(zp, as_only=False))                 # --include-sid
    assert any(f["token"] == "SID12345" for f in hits), hits


def test_binary_member_skipped_no_crash(tmp_path):
    m = _load()
    # a PNG-extension member with a NUL-laden body must be skipped, not decoded/scanned/crashed
    zp = _make_archive(tmp_path, "withimg.zip",
                       {"img/logo.png": b"\x89PNG\x00\x00AS-777\x00", "readme.txt": "clean"})
    # AS-777 lives only inside the .png bytes -> must NOT be reported (binary skip)
    assert _real(m.scan_archive(zp)) == []


def test_scan_tree_counts_and_flags(tmp_path):
    m = _load()
    _make_archive(tmp_path, "a_clean.zip", {"a.txt": "ok"})
    _make_archive(tmp_path, "b_leak.docx", {"word/document.xml": "<p>isolate AS-902</p>"})
    findings, n = m.scan_tree(tmp_path)
    assert n == 2
    assert any(f["token"] == "AS-902" for f in _real(findings)), findings


def test_reuses_redactor_ssot_not_handrolled():
    """Guard against drift: the tool must import the private-ID definition from the enforced
    redactor, not define its own AS/AJS/PENDING regex."""
    src = (TOOLS / "archive_leak_scan.py").read_text(encoding="utf-8")
    assert "from redact_public_tier import private_id_matches" in src
