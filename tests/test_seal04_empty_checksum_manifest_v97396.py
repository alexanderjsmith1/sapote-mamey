"""SEAL-04 (v9.7.396): a checksum manifest that exists but lists NOTHING must not validate clean.

`verify_checksums` has two passes and, before this fix, both were silent on an empty manifest:

  * the forward pass iterates the manifest's lines — an empty file has none;
  * the SEAL-03 reciprocal pass is guarded on `tracked` being non-empty, deliberately, so that a
    degenerate manifest does not flag every file in the tree as untracked.

The net effect was a zero-scan PASS: emptying `checksums_sha256.txt` inside a TAMPERED sealed
package produced an empty error list, so `validate_package` reported `checksum_integrity=PASS`
and `status=MAMEY_COMPLETE` — the engine's terminal "this package is good" verdict, identical to
the verdict for the pristine package. Reproduced on a real sealed package before the fix.

A *missing* manifest was already an error (`checksums_sha256.txt missing`); an *empty* one is the
same claim — integrity unverified — and must be reported the same way.

The SEAL-03 guarantee is preserved exactly: the new error deliberately does not contain the
substring "untracked", so `test_empty_checksums_manifest_does_not_trigger_reciprocal` (which
asserts no PER-FILE untracked errors on an empty manifest) still holds.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from mamey.validate import verify_checksums


def _sealed(tmp_path: Path, manifest_text: str | None = "AUTO") -> Path:
    """A minimal sealed package: two tracked files plus a real checksum manifest."""
    pkg = tmp_path / "AS-SEAL04"
    pkg.mkdir(parents=True)
    payload = {
        "AS-SEAL04_2_inventory.csv": b"BGC_ID,Depth_floor\nBGC001,full_mode_b\n",
        "AS-SEAL04_1_intake.json": b'{"strain": "AS-SEAL04"}\n',
    }
    lines = []
    for name, data in payload.items():
        (pkg / name).write_bytes(data)
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    if manifest_text == "AUTO":
        manifest_text = "\n".join(lines) + "\n"
    if manifest_text is not None:
        (pkg / "checksums_sha256.txt").write_text(manifest_text, encoding="utf-8")
    return pkg


def _unverified(errors: list[str]) -> list[str]:
    return [e for e in errors if "UNVERIFIED" in e]


def test_control_real_manifest_verifies_clean(tmp_path):
    assert verify_checksums(_sealed(tmp_path)) == []


def test_empty_manifest_is_an_integrity_error(tmp_path):
    """The defect: a zero-byte manifest returned no errors at all."""
    pkg = _sealed(tmp_path, manifest_text="")
    assert _unverified(verify_checksums(pkg)), verify_checksums(pkg)


def test_comment_only_manifest_is_an_integrity_error(tmp_path):
    """Not just zero bytes: a manifest whose every line is a comment tracks nothing either."""
    pkg = _sealed(tmp_path, manifest_text="# checksums\n# written by packaging.write_manifest\n")
    assert _unverified(verify_checksums(pkg)), verify_checksums(pkg)


def test_tampered_file_is_not_laundered_by_emptying_the_manifest(tmp_path):
    """The whole point: tampering must not become invisible by truncating the manifest."""
    pkg = _sealed(tmp_path)
    assert verify_checksums(pkg) == []
    (pkg / "AS-SEAL04_1_intake.json").write_bytes(b'{"strain": "AS-SEAL04", "injected": true}\n')
    assert verify_checksums(pkg), "tamper must be caught while the manifest is intact"
    (pkg / "checksums_sha256.txt").write_text("", encoding="utf-8")
    assert verify_checksums(pkg), "emptying the manifest must not clear the integrity verdict"


def test_missing_and_empty_manifests_agree(tmp_path):
    """A missing manifest was always an error; an empty one makes the same claim."""
    missing = _sealed(tmp_path / "a", manifest_text=None)
    empty = _sealed(tmp_path / "b", manifest_text="")
    assert verify_checksums(missing), "missing manifest must error (pre-existing behaviour)"
    assert verify_checksums(empty), "empty manifest must error too"


def test_seal03_no_per_file_untracked_errors_on_empty_manifest(tmp_path):
    """SEAL-03's deliberate guard is preserved: no per-file 'untracked' spam on a degenerate
    manifest. Only the single UNVERIFIED error is added."""
    pkg = _sealed(tmp_path, manifest_text="")
    errors = verify_checksums(pkg)
    assert not [e for e in errors if "untracked" in e], errors
    assert len(_unverified(errors)) == 1, errors
