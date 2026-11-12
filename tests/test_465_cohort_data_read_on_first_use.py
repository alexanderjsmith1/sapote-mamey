"""Importing a cohort module reads no workspace cohort data.

These modules read the workspace exclusions, assembly-tier, attine-roster and co-assembly files at import. In
the release cut's sandboxed import check the reads were refused, exclusions.py printed a warning, and the cut
was held. Each import runs in a fresh interpreter under an audit hook that fails on any open under OFFICIAL_DATA.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["mamey.assembly_line", "mamey.compound_family_report", "mamey.p450_tailoring",
           "mamey.cohort_figures_extended", "mamey.interactive_figures.widget_data",
           "mamey.interactive_figures.figure_atlas", "tools.build_cohort_precompute",
           "tools.blastp_coverage_wave", "tools.materialize_strain_data",
           "tools.cohort_figure_prototypes", "tools.build_owner_kept_figure_inputs",
           "mamey.dualpass_ledger", "mamey.cli", "tools.ingest_swissprot_local"]
PROBE = """
import sys
def hook(event, args):
    if event == "open" and args and "OFFICIAL_DATA" in str(args[0]):
        raise RuntimeError("opened at import: " + str(args[0]))
sys.addaudithook(hook)
sys.path[:0] = [sys.argv[1], sys.argv[1] + "/tools"]
__import__(sys.argv[2])
"""


@pytest.mark.parametrize("name", MODULES)
def test_import_reads_no_cohort_file(name, tmp_path):
    data = tmp_path / "OFFICIAL_DATA"
    data.mkdir()
    for f in ("exclusions.json", "co_assembly.json", "cohort_assembly_tiers.json", "attine_ant_cohort.json"):
        (data / f).write_text("{}")
    env = {"PATH": "/usr/bin:/bin", "SAPOTE_WORKSPACE_ROOT": str(tmp_path), "MAMEY_DATA_ROOT": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1",
           "MPLCONFIGDIR": str(tmp_path / "mpl")}
    r = subprocess.run([sys.executable, "-c", PROBE, str(ROOT), name], cwd=tmp_path, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    assert "could not read" not in r.stderr, r.stderr[-800:]
