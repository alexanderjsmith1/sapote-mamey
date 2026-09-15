"""v9.7.430 release-integrity — verify_release_identity must not report PASS over an UNLISTED file.

SEAL-01 (v9.7.336) built the TIER_MANIFEST *membership* check after the v9.7.334 rev-b handoff
shipped a manifest listing 1399 files against a 1438-file tree — omitting 13 engine modules — while
`verify_release_identity`, `check_release_manifest`, `sync_version --check` and
`check_module_accretion` all passed on it. v9.7.409 then folded the CHECKSUM verdict into
`verify_release_identity`, closing the "a file was EDITED while its version strings stayed current"
half of that class.

The other half stayed open. An unlisted file has no manifest entry, so it has no checksum to
mismatch: `checksum_problems` is structurally blind to it. Reproduced before this fix — a tree
carrying `mamey/secret_payload.py` that is tracked by policy and named in NO manifest returned:

    release identity: PASS (bundle v9.9.999 / engine 9.9.9 · build TESTSTAMP)   exit 0

while `check_release_manifest` on the same tree returned
`TIER_MANIFEST omits 1 file(s) present in the tree (first: mamey/secret_payload.py)`, exit 1.

These tests build that exact tree and assert the membership verdict is (a) always VISIBLE and
(b) fail-closed under --strict-membership. Default stays advisory on purpose: membership
legitimately reports drift on an in-place working tree carrying run artifacts, and a hard failure
there would train operators to ignore the gate — the outcome this fix exists to prevent.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "verify_release_identity.py"
READ_PROOF = "The sky is not red, it is blue, just like the ocean."

_TOOLS = ("check_release_manifest.py", "verify_release_identity.py",
          "tracked_file_policy.py", "_console.py")


def _mk_bundle(tmp_path: Path, *, omit: list[str]) -> Path:
    """A minimal but faithful bundle root whose TIER_MANIFEST omits `omit`.

    Checksums are written over the LISTED files only — exactly what a real cut does, and the reason
    an unlisted file is invisible to a checksum-only gate rather than merely unverified.
    """
    b = tmp_path / "bundle"
    (b / "mamey").mkdir(parents=True)
    (b / "tools").mkdir(parents=True)
    for t in _TOOLS:
        shutil.copy2(ROOT / "tools" / t, b / "tools" / t)

    version, engine, stamp = "9.9.999", "9.9.9", "TESTSTAMP"
    (b / "pyproject.toml").write_text(
        f'[project]\nversion = "{engine}"\n\n[tool.sapote]\nbundle_version = "{version}"\n')
    (b / "mamey" / "__init__.py").write_text(
        f'__version__ = "{engine}"\nBUNDLE_VERSION = "{version}"\n')
    (b / "BUILD_STAMP.txt").write_text(
        f"version={version}\nbuild={stamp}\nengine={engine}\ntier=code\n")
    (b / "TAG").write_text(f"sapote-mamey v{version}\nengine: mamey v{engine}\nbuild: {stamp}\n")
    for name in ("AGENTS.md", "CLAUDE.md"):
        (b / name).write_text(f"# {name}\nv{version} / {engine} build {stamp}\n\n{READ_PROOF}\n")
    (b / "README.md").write_text(f"# README\nv{version} / {engine} build {stamp}\n")
    # the payload: a shipped engine module, tracked by policy
    (b / "mamey" / "secret_payload.py").write_text("# a shipped module nobody listed\nDANGER = 1\n")

    tracked = ["pyproject.toml", "mamey/__init__.py", "BUILD_STAMP.txt", "TAG", "AGENTS.md",
               "CLAUDE.md", "README.md", "mamey/secret_payload.py"] + [f"tools/{t}" for t in _TOOLS]
    listed = [t for t in tracked if t not in omit]
    (b / "TIER_MANIFEST.txt").write_text(
        f"# TIER_MANIFEST tier=code version={version} stamp={stamp}\n"
        + "\n".join(f"./{t}" for t in listed) + "\n")
    (b / "SOURCE_CHECKSUMS_SHA256.txt").write_text("\n".join(
        f"{hashlib.sha256((b / t).read_bytes()).hexdigest()}  ./{t}" for t in sorted(listed)) + "\n")
    return b


def _run(root: Path, *extra: str):
    return subprocess.run([sys.executable, str(GATE), "--root", str(root), *extra],
                          capture_output=True, text=True)


def test_control_a_complete_manifest_passes_silently(tmp_path):
    """CONTROL: nothing omitted — PASS, exit 0, and NO membership advisory.

    Without this the tests below prove nothing: an advisory that fires on every tree is noise, and
    the fix would be trading a blind gate for an ignored one.
    """
    b = _mk_bundle(tmp_path, omit=[])
    r = _run(b)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout, r.stdout
    assert "membership" not in r.stdout, r.stdout


def test_unlisted_module_is_visible_by_default(tmp_path):
    """PASS-AFTER: the gate still passes (deliberate) but the omission can no longer be invisible."""
    b = _mk_bundle(tmp_path, omit=["mamey/secret_payload.py"])
    r = _run(b)
    assert "ADVISORY:" in r.stdout, r.stdout
    assert "membership:" in r.stdout, r.stdout
    assert "secret_payload.py" in r.stdout, r.stdout
    assert "--strict-membership" in r.stdout, "the advisory must say how to make it blocking"


def test_unlisted_module_fails_closed_under_strict_membership(tmp_path):
    """PASS-AFTER: at cut time the same tree is refused, not merely annotated."""
    b = _mk_bundle(tmp_path, omit=["mamey/secret_payload.py"])
    r = _run(b, "--strict-membership")
    assert r.returncode != 0, r.stdout
    assert "FAIL: membership:" in r.stdout, r.stdout
    assert "secret_payload.py" in r.stdout, r.stdout


def test_control_b_strict_membership_does_not_fail_a_complete_manifest(tmp_path):
    """CONTROL: --strict-membership is not a blanket refusal — a correct tree still passes."""
    b = _mk_bundle(tmp_path, omit=[])
    r = _run(b, "--strict-membership")
    assert r.returncode == 0, r.stdout + r.stderr


def test_membership_advisory_is_reported_in_json(tmp_path):
    """A machine reader must see the advisory too, in its own key, never mixed into errors."""
    import json
    b = _mk_bundle(tmp_path, omit=["mamey/secret_payload.py"])
    r = _run(b, "--json")
    payload = json.loads(r.stdout)
    assert payload["status"] == "PASS", payload
    assert any("secret_payload.py" in m for m in payload["membership_advisories"]), payload
    assert not any("membership" in e for e in payload["errors"]), payload


def test_checksum_gate_alone_cannot_see_an_unlisted_file(tmp_path):
    """The WHY, asserted rather than asserted-in-a-comment: checksum_problems is structurally blind.

    This is the property that made the pre-fix PASS possible, and if it ever stops being true the
    reasoning in this file needs revisiting.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from check_release_manifest import checksum_problems, membership_problems
    b = _mk_bundle(tmp_path, omit=["mamey/secret_payload.py"])
    problems, _stats = checksum_problems(b)
    assert problems == [], f"checksum gate unexpectedly saw the unlisted file: {problems}"
    assert any("secret_payload.py" in p for p in membership_problems(b)), \
        "membership gate must see what the checksum gate cannot"


def test_release_entry_points_require_strict_membership():
    """The strict mode is useful only if every shipped cut path invokes it."""
    release_cut = (ROOT / "tools" / "release_cut.sh").read_text(encoding="utf-8")
    release_sh = (ROOT / "tools" / "release.sh").read_text(encoding="utf-8")
    assert release_cut.count("verify_release_identity.py --strict-membership") >= 2
    assert 'verify_release_identity.py" --root "$SRC" --tiers-dir "$OUT" --strict-membership' in release_sh
