"""Importing a phylogeny or 16S tool reads no workspace data.

These tools once located the 16S store, the RefSeq BLAST database or the outgroup registry at import. That
opened OFFICIAL_DATA files before any command ran, and the release cut's sandboxed import check held them.
Each import below runs in a fresh interpreter under an audit hook that fails on any open under OFFICIAL_DATA.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ["outgroup_registry", "phylo_preflight", "phylo_16s_audit_merges", "phylo_16s_build_db",
         "phylo_16s_esearch", "phylo_16s_fetch", "phylo_16s_from_genome", "phylo_16s_panel",
         "phylo_16s_rank", "phylo_16s_validate_db"]
PROBE = """
import sys
def hook(event, args):
    if event == "open" and args and "OFFICIAL_DATA" in str(args[0]):
        raise RuntimeError("opened at import: " + str(args[0]))
sys.addaudithook(hook)
sys.path[:0] = [sys.argv[1], sys.argv[1] + "/tools"]
__import__(sys.argv[2])
"""


@pytest.mark.parametrize("name", TOOLS)
def test_import_opens_no_workspace_file(name, tmp_path):
    # Run from a folder whose parent holds OFFICIAL_DATA, so a parent-directory search would find it.
    (tmp_path / "OFFICIAL_DATA").mkdir()
    (tmp_path / "OFFICIAL_DATA" / "OUTGROUP_REGISTRY.tsv").write_text("genus\toutgroup\n")
    (tmp_path / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text("asset_id\tkind\tpath\tsize\tguards\n")
    work = tmp_path / "work"
    work.mkdir()
    env = {"PATH": "/usr/bin:/bin", "SAPOTE_WORKSPACE_ROOT": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-c", PROBE, str(ROOT), name], cwd=work, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]


@pytest.mark.parametrize("name,attr", [("outgroup_registry", "REGISTRY"), ("phylo_preflight", "REGISTRY")])
def test_lazy_registry_still_resolves(name, attr):
    sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
    mod = __import__(name)
    assert isinstance(getattr(mod, attr), str) and getattr(mod, attr)
