"""A region whose product has no class rule (nucleoside, fatty_acid, RiPP-like ...) lists each gene's domain families
instead of an empty "What the genes show" section."""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402


def _D():
    dom = defaultdict(list)
    dom["ctg1_1"] = [(1e-50, "TruD", "tRNA pseudouridine synthase D", "PFAM_domain")]
    dom["ctg1_2"] = [(1e-90, "Radical_SAM", "", "aSDomain"), (1e-40, "Radical_SAM", "", "PFAM_domain"),
                     (1e-10, "SPASM", "", "PFAM_domain"), (1e-5, "Fer4_12", "", "PFAM_domain")]
    gfeat = defaultdict(list)
    gfeat["ctg1_3"] = [{"domain": "PF00155", "i_evalue": "1e-20"}]
    return {"genes": {"BGC001": [{"locus_tag": t} for t in ("ctg1_1", "ctg1_2", "ctg1_3", "ctg1_4")]},
            "dom": dom, "gfeat": gfeat, "pfam": {"PF00155": "Aminotran_1_2"}}


def _text(paras):
    return "\n".join("".join(r[0] for r in p) for p in paras)


def test_each_gene_gets_its_domains_and_the_unannotated_gene_is_named():
    t = _text(ss.domain_paras(_D(), "BGC001"))
    assert "ctg1_1 TruD" in t
    assert "ctg1_2 Radical_SAM + SPASM" in t  # two names at most, best first, duplicates merged
    assert "ctg1_3 Aminotran_1_2" in t  # GECCO's Pfam row when the package has none
    assert "No domain annotated: ctg1_4." in t
    assert "not a measured reaction or a product call" in t


def test_no_domains_gives_nothing():
    D = _D()
    D["dom"], D["gfeat"] = defaultdict(list), defaultdict(list)
    assert ss.domain_paras(D, "BGC001") == []
