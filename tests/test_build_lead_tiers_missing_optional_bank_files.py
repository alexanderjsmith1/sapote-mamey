"""tools/build_lead_tiers.py must not crash on a freshly-banked cohort.

Found via a real deliverable run (BC2-408): `ingest_package.py --package <pkg> --merge` is the
documented, complete cohort-banking step, but neither it nor any other tool in this codebase ever
writes deep_data.json (a separate tool's output, tools/build_deep_data.py -- per the AUDIT_374
comment already fixed for this exact class of gap in tools/build_master.py's own
`_read_json_or()`) or a cohort-level modeb_verdicts.csv (written only per-PACKAGE by
mamey/cli.py's `_write_package`; no tool anywhere merges those per-strain rows into
`<banked_dir>/modeb_verdicts.csv`). `build_lead_tiers.py` read both with a bare, unguarded
`open()`/`_read_json()` -- a hard FileNotFoundError on exactly the common case, reached before this
tool's own v9.7.114 "empty-safe write" design (a cohort with zero CONFIRMs writes a valid
header-only CSV) ever got a chance to run. Every sibling consumer of modeb_verdicts.csv
(generate_bgc_atlas.py, build_thesis_vignettes.py, build_subset_panel.py, lead_board.py) already
guards this same read with `if os.path.exists(...)`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_minimal_bank(tmp_path):
    """A bank with only what ingest_package.py --merge actually writes -- no deep_data.json,
    no modeb_verdicts.csv (the two gaps this test targets)."""
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": []}), encoding="utf-8")
    (bank / "tfbs_coupling.json").write_text(json.dumps({}), encoding="utf-8")
    return bank


def test_missing_deep_data_and_modeb_verdicts_does_not_crash(tmp_path):
    bank = _make_minimal_bank(tmp_path)
    assert not (bank / "deep_data.json").exists()
    assert not (bank / "modeb_verdicts.csv").exists()
    out_csv = tmp_path / "ChemistryFirst_Recall.csv"

    result = subprocess.run(
        [sys.executable, "tools/build_lead_tiers.py", "--banked-dir", str(bank), "--out", str(out_csv)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"build_lead_tiers.py crashed on a bank missing only the two optional/enrichment files "
        f"(deep_data.json, modeb_verdicts.csv) that no tool actually writes on a fresh "
        f"`ingest_package.py --merge` bank.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert out_csv.exists()
    header = out_csv.read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("sid,bgc,modeb_class"), (
        "must still emit the v9.7.114 empty-safe header-only CSV, not just avoid crashing"
    )


def test_present_modeb_verdicts_still_reads_normally(tmp_path):
    """Regression guard: the fix must not break the normal case where modeb_verdicts.csv exists."""
    bank = _make_minimal_bank(tmp_path)
    (bank / "deep_data.json").write_text(json.dumps({"bgc_profile": []}), encoding="utf-8")
    (bank / "modeb_verdicts.csv").write_text(
        "strain,bgc,status,modeb_class,note\nAS-TEST,BGC001,CONFIRM,nrps,\n", encoding="utf-8"
    )
    (bank / "bgc_data.json").write_text(json.dumps({
        "strains": {"AS-TEST": {}},
        "bgcs": [{"sid": "AS-TEST", "bgc_id": "BGC001", "closest_kcb_product": "", "edge_status": "Full-contig", "length_kb": 10.0}],
    }), encoding="utf-8")
    out_csv = tmp_path / "ChemistryFirst_Recall.csv"

    result = subprocess.run(
        [sys.executable, "tools/build_lead_tiers.py", "--banked-dir", str(bank), "--out", str(out_csv)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    lines = out_csv.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "the one real CONFIRM row must still be written"
    assert "AS-TEST" in lines[1] and "BGC001" in lines[1]
