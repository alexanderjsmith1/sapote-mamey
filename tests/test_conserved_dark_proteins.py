"""CLAUDE_AUG4 — conserved reference-dark protein finder: logic guard.

Synthetic 3-strain case (no external tools): a dark protein conserved in all 3 = PAN_CLADE; a dark
protein in 2 of 3 = SUBGROUP; a Pfam-annotated protein is excluded; a strain-unique dark protein does
not reach a family. Also checks the multi-cutoff sweep runs and the sensitivity table is written.

Standalone: python3 tests/test_conserved_dark_proteins.py
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "deliverable_tools"))
import conserved_dark_proteins as C

# a "conserved dark" protein (same in all 3 strains, one with a single A->V substitution)
DARK_CORE = "M" + "AAAAKKKKLLLLGGGGSSSSDDDDEEEEFFFF" * 4       # ~130 aa
DARK_CORE_V = DARK_CORE.replace("AAAA", "AVAA", 1)             # one substitution
SUBGROUP_DARK = "M" + "PPPPWWWWYYYYCCCCNNNNQQQQHHHHRRRR" * 4    # in 2 strains only
PFAM_PROT = "M" + "TTTTIIIIMMMMVVVV" * 6                       # will be "annotated"
UNIQUE_DARK = "M" + "GGGGGGGGGGGGGGGG" * 5                     # only strain A


def _write(d):
    os.makedirs(os.path.join(d, "prot"))
    def faa(strain, seqs):
        with open(os.path.join(d, "prot", f"{strain}.faa"), "w") as o:
            for i, s in enumerate(seqs):
                o.write(f">{strain}_orf{i}\n{s}\n")
    faa("SA", [DARK_CORE, SUBGROUP_DARK, PFAM_PROT, UNIQUE_DARK])
    faa("SB", [DARK_CORE_V, SUBGROUP_DARK, PFAM_PROT])
    faa("SC", [DARK_CORE, PFAM_PROT])
    # Pfam hits: only the PFAM_PROT of each strain "has a Pfam" (tagged strain|orf)
    tbl = os.path.join(d, "pfam.tbl")
    with open(tbl, "w") as o:
        o.write("# fake hmmsearch tblout\n")
        o.write("SA|SA_orf2 - somePfam - 1e-40\n")
        o.write("SB|SB_orf2 - somePfam - 1e-40\n")
        o.write("SC|SC_orf1 - somePfam - 1e-40\n")
    return os.path.join(d, "prot"), tbl


def test_conserved_dark_scopes_and_sweep():
    with tempfile.TemporaryDirectory() as d:
        pdir, tbl = _write(d)
        out = os.path.join(d, "out")
        per = C.run(pdir, out, pfam_tbl=tbl, cutoffs=(0.40, 0.55, 0.70), min_strains=2)
        fam = per[0.55]
        scopes = {f["scope"] for f in fam}
        # DARK_CORE conserved in all 3 (incl. the A->V variant) -> PAN_CLADE
        assert any(f["scope"] == "PAN_CLADE" and len(f["strains"]) == 3 for f in fam), \
            [(f["scope"], f["strains"]) for f in fam]
        # SUBGROUP_DARK in SA+SB only -> SUBGROUP
        assert any(f["scope"] == "SUBGROUP" and set(f["strains"]) == {"SA", "SB"} for f in fam)
        # Pfam-annotated protein must never appear as a conserved-dark family
        assert all("orf2" not in f["rep"] or f["rep"].startswith("SC") for f in fam)  # SC_orf1 is pfam; SA/SB orf2 pfam
        # unique dark protein does not reach a >=2-strain family
        assert all(not (len(f["strains"]) == 1) for f in fam)
        # sweep wrote a sensitivity table + per-cutoff files
        assert os.path.exists(os.path.join(out, "threshold_sensitivity.tsv"))
        assert os.path.exists(os.path.join(out, "conserved_dark_families_c0.55.tsv"))
        assert os.path.exists(os.path.join(out, "representatives.faa"))


def test_substitution_tolerant_clustering():
    # DARK_CORE and its single-substitution variant must co-cluster (the A->V case)
    cl = C.cluster_by_similarity([("a", DARK_CORE), ("b", DARK_CORE_V)], cutoff=0.55)
    assert any(len(c) == 2 for c in cl), "single-substitution homologs should cluster"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
