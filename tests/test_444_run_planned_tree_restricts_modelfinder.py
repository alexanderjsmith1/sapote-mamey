"""v9.7.444: the GToTree -> IQ-TREE runner uses the documented, restricted ModelFinder search by default.

docs/GTOTREE_WORKFLOW.md (section 5) prescribes `-m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G` for the protein
supermatrix and warns that bare `-m MFP` never finishes on ~30k columns. The runner passed bare `-m MFP`: on the
87-genome insect-set v5 alignment (20,910 columns) ModelFinder tested 24 of up to 1,232 models in about 2 hours.
"""
import importlib.util
import re
from pathlib import Path

from mamey import cli

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_planned_tree", ROOT / "tools" / "run_planned_tree.py")
rpt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpt)


def _cmd(model=""):
    return rpt.iqtree_command("iqtree", "aln.faa", "/w/iqtree", seed=12345, threads="4", outgroup="OG", model=model)


def _pairs(cmd):
    return dict(zip(cmd, cmd[1:]))


def test_default_is_the_documented_restricted_search():
    p = _pairs(_cmd())
    assert p["-m"] == "MFP"
    assert p["-mset"] == "LG,WAG,JTT,Q.pfam"
    assert p["-mrate"] == "G,I,I+G"


def test_default_matches_the_workflow_doc():
    doc = (ROOT / "docs" / "GTOTREE_WORKFLOW.md").read_text()
    m = re.search(r"-m MFP -mset (\S+) -mrate (\S+)", doc)
    assert m, "the documented ModelFinder line is gone from docs/GTOTREE_WORKFLOW.md"
    p = _pairs(_cmd())
    assert (p["-mset"], p["-mrate"]) == (m.group(1), m.group(2))


def test_fixed_model_override_drops_the_search():
    cmd = _cmd("LG+F+G4")
    assert _pairs(cmd)["-m"] == "LG+F+G4"
    assert "-mset" not in cmd and "-mrate" not in cmd


def test_unrestricted_search_stays_available():
    cmd = _cmd("MFP")
    assert _pairs(cmd)["-m"] == "MFP" and "-mset" not in cmd


def test_determinism_and_support_flags_are_kept():
    p = _pairs(_cmd())
    assert p["-seed"] == "12345" and p["-T"] == "4" and p["-o"] == "OG"
    assert p["-B"] == "1000" and p["-alrt"] == "1000" and p["--prefix"] == "/w/iqtree"


def test_phylo_run_forwards_the_model():
    sub = next(a for a in cli.build_parser()._subparsers._group_actions if "phylo-run" in a.choices)
    args = cli.build_parser().parse_args(["phylo-run", "--genome-list", "/g", "--workdir", "/w", "--outgroup", "OG",
                                          "--iqtree-model", "LG+F+G4"])
    assert args.iqtree_model == "LG+F+G4"
    assert "--iqtree-model" in {o for act in sub.choices["phylo-run"]._actions for o in act.option_strings}
