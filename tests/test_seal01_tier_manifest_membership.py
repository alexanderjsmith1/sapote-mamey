"""SEAL-01 (v9.7.336) — `check_release_manifest` now verifies TIER_MANIFEST *membership*.

Checks 1-3 verified the checksum manifest and that `TIER_MANIFEST stamp=` equals
`BUILD_STAMP build=`. Nothing verified that TIER_MANIFEST's **file list** described the tree, so a
bundle could ship a manifest naming a different tree and every gate still passed.

Not hypothetical. The v9.7.334 rev-b handoff source shipped a TIER_MANIFEST listing 1399 files
against a 1438-file tree. It omitted 42 files — including **13 engine modules**: every module added
across v9.7.330-.333 (`discover.py`, `genus_appendix.py`, `mibig_per_gene.py`,
`antismash_tables.py`, `length_weighted.py`, `class_believability.py`, `cohort_context.py`,
`strain_modeb.py`, `modeb_cards.py`, `series_common.py`, `companion_tools.py`, plus
`data/companion_tools.json` and `data/tool_citations.json`) — and named three files the tree did
not contain. `verify_release_identity`, `check_release_manifest`, `sync_version --check` and
`check_module_accretion` all passed on it.

These tests build the known-bad shapes directly and assert the gate refuses them.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_release_manifest.py"


def _mk_tree(tmp_path: Path, *, listed: list[str], present: list[str]) -> Path:
    """Build a minimal tree whose TIER_MANIFEST lists `listed` while the tree holds `present`."""
    root = tmp_path / "bundle"
    (root / "mamey").mkdir(parents=True)
    for rel in present:
        fp = root / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(f"content of {rel}\n", encoding="utf-8")

    (root / "BUILD_STAMP.txt").write_text(
        "version=9.9.999\nbuild=TESTSTAMP\nengine=9.9.9\ntier=code\n", encoding="utf-8")
    # BUILD_STAMP.txt is a tracked file in a real cut, so it belongs in the listing; including it
    # here keeps the fixture faithful and any FAIL attributable to the membership case under test.
    (root / "TIER_MANIFEST.txt").write_text(
        "# TIER_MANIFEST tier=code version=9.9.999 stamp=TESTSTAMP\n"
        + "\n".join(f"./{r}" for r in list(listed) + ["BUILD_STAMP.txt"]) + "\n", encoding="utf-8")

    # a correct checksum manifest over everything actually present, so any FAIL is attributable
    # to membership rather than to checksum drift
    import hashlib
    lines = []
    for rel in sorted(present + ["BUILD_STAMP.txt"]):
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  ./{rel}")
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _run(root: Path):
    return subprocess.run([sys.executable, str(GATE), "--root", str(root)],
                          capture_output=True, text=True)


def test_control_matching_manifest_passes(tmp_path):
    """Control: when the list matches the tree the gate passes, so a FAIL below is attributable."""
    files = ["mamey/alpha.py", "mamey/beta.py", "docs/readme.md"]
    root = _mk_tree(tmp_path, listed=files, present=files)
    r = _run(root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_omitting_a_shipped_engine_module_fails(tmp_path):
    """KNOWN-BAD: the rev-b shape — a module ships but the manifest never lists it."""
    present = ["mamey/alpha.py", "mamey/beta.py", "mamey/discover.py", "docs/readme.md"]
    listed = ["mamey/alpha.py", "mamey/beta.py", "docs/readme.md"]  # discover.py omitted
    root = _mk_tree(tmp_path, listed=listed, present=present)
    r = _run(root)
    assert r.returncode != 0, r.stdout
    assert "omits 1 file" in r.stdout, r.stdout
    assert "discover.py" in r.stdout, r.stdout


def test_manifest_naming_an_absent_file_fails(tmp_path):
    """KNOWN-BAD: the other half of the rev-b shape — the manifest names files not in the tree."""
    present = ["mamey/alpha.py", "docs/readme.md"]
    listed = present + [".gitignore", ".github/workflows/ci.yml"]
    root = _mk_tree(tmp_path, listed=listed, present=present)
    r = _run(root)
    assert r.returncode != 0, r.stdout
    assert "names 2 file" in r.stdout, r.stdout


def test_build_caches_are_not_counted_as_membership_drift(tmp_path):
    """Control: __pycache__ / .pyc / editor backups must not trip the gate."""
    files = ["mamey/alpha.py", "docs/readme.md"]
    root = _mk_tree(tmp_path, listed=files, present=files)
    (root / "mamey" / "__pycache__").mkdir()
    (root / "mamey" / "__pycache__" / "alpha.cpython-312.pyc").write_text("x", encoding="utf-8")
    (root / "mamey" / "alpha.py.orig").write_text("x", encoding="utf-8")
    (root / "mamey" / "alpha.py~").write_text("x", encoding="utf-8")
    r = _run(root)
    assert r.returncode == 0, r.stdout + r.stderr
