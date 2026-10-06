"""A partner track is named by the region that holds its matched genes, copied from the rescue table, not by the first
region on its contig. The bug: a contig with region001 at 18-40 kb and region002 at 62-73 kb, matched genes at 67-72 kb,
was labelled region001."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
import rescue_locus_comparison as rlc  # noqa: E402

R1 = "ISOLATE_001 / NODE_28_length_73283_cov_62.2 / region001 / BGC017"
R2 = "ISOLATE_001 / NODE_28_length_73283_cov_62.2 / region002 / BGC018"
OUT = "ISOLATE_001 / NODE_28_length_73283_cov_62.2 (no antiSMASH region)"


def _rows(*ids):
    return [{"best_region_identity": x} for x in ids]


def test_the_region_holding_every_matched_gene_names_the_track():
    assert rlc.partner_region(_rows(R2, R2)) == ("region002", "BGC018")


def test_genes_outside_every_region_carry_no_region_or_alias():
    assert rlc.partner_region(_rows(OUT, OUT)) == ("no antiSMASH region", "no BGC alias")


def test_genes_split_between_places_hold_the_identity():
    region, bgc = rlc.partner_region(_rows(R1, R2))
    assert bgc == "identity held" and "2 places" in region
    region, bgc = rlc.partner_region(_rows(R2, OUT))
    assert bgc == "identity held"


def test_the_first_region_on_the_contig_is_never_assumed():
    assert rlc.partner_region(_rows(R2)) != ("region001", "BGC017")


def test_the_partner_loop_does_not_rename_the_core_region():
    """The figure title names the core BGC; a partner's region must not overwrite that name inside manifest()."""
    import ast
    tree = ast.parse((ROOT / "tools/rescue_locus_comparison.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "manifest")
    loops = [n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.While))]
    in_loop = {id(x) for l in loops for x in ast.walk(l)}
    rebound = [t.id for n in ast.walk(fn) if isinstance(n, ast.Assign) and id(n) in in_loop
               for tgt in n.targets for t in ast.walk(tgt) if isinstance(t, ast.Name) and t.id in ("bgc", "region")]
    assert not rebound, rebound
