"""tools/build_deep_data.py must be able to run on a genuinely FRESH bank.

Found via a real deliverable run (BC2-408): this tool's own module docstring says its job is to
"bank the full per-BGC deep_data for strains ingested core-only" -- i.e. to ADD deep_data.json/
gene_data.json enrichment to a bank that only carries the core `tools/ingest_package.py --merge`
outputs. But its own `main()` guard demanded `deep_data.json` already exist in the banked dir before
it would run at all -- a bootstrapping bug that refused to do its one job on exactly the case it
exists for. Verified live against this cycle's own real AS-705 deliverable bank (produced purely via
the documented `ingest_package.py --merge` workflow, which never writes deep_data.json):
`error: banked dir ... does not contain deep_data.json`, exit 2. The tool's real hard prerequisite
is `bgc_data.json` (read unconditionally for `all_sids`); `deep_data.json`/`gene_data.json` are its
own outputs and should start from an empty shape on a first run, matching the exact idiom
tools/build_modeb_deepdive.py already uses for the identical missing-file case.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_MINIMAL_SNAPSHOT = {
    "source_scans": {"domain_architecture": {"per_bgc": {
        "BGC001": {"domain_counts": {"PKS_KS": 1}, "domains": []}
    }}}
}


def _make_fresh_bank_and_packages(tmp_path):
    """A bank with only bgc_data.json (what ingest_package.py --merge writes) -- no
    deep_data.json, no gene_data.json -- plus a real-shaped package snapshot findable via
    MAMEY_PACKAGES, matching find_snaps()'s own discovery convention."""
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(
        json.dumps({"strains": {"SID100": {}}, "bgcs": []}), encoding="utf-8"
    )
    packages_root = tmp_path / "packages"
    pkg_dir = packages_root / "SID100" / "package"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "SID100_Project_Memory_Snapshot.json").write_text(
        json.dumps(_MINIMAL_SNAPSHOT), encoding="utf-8"
    )
    return bank, packages_root


def test_fresh_bank_with_no_deep_data_json_does_not_crash(tmp_path):
    bank, packages_root = _make_fresh_bank_and_packages(tmp_path)
    assert not (bank / "deep_data.json").exists()
    assert not (bank / "gene_data.json").exists()

    env = dict(os.environ, MAMEY_PACKAGES=str(packages_root))
    result = subprocess.run(
        [sys.executable, "tools/build_deep_data.py", str(bank)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 0, (
        f"build_deep_data.py refused to run on a fresh bank missing only its own output files "
        f"(deep_data.json, gene_data.json), which no tool ever pre-creates.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert (bank / "deep_data.json").exists()
    assert (bank / "gene_data.json").exists()
    deep = json.loads((bank / "deep_data.json").read_text(encoding="utf-8"))
    assert len(deep.get("bgc_profile", [])) == 1, (
        "the one real strain's bgc_profile must actually get banked, not just avoid crashing"
    )


def test_missing_bgc_data_json_still_refuses_with_a_clear_message(tmp_path):
    """Regression guard: bgc_data.json is the genuine hard prerequisite and must still be enforced
    -- the fix must narrow the guard, not remove it entirely."""
    bank = tmp_path / "bank_no_core"
    bank.mkdir()
    result = subprocess.run(
        [sys.executable, "tools/build_deep_data.py", str(bank)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 2
    assert "bgc_data.json" in result.stderr
