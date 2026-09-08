"""Engine tests for mamey/modeb_domain_phylogeny.py — generalized domain-tree subsections (VGP-400).

IN-TREE: imports the INSTALLED module. A `.before` copy cannot exist in a shipped tree, so the
byte-compatibility claim is expressed here as CURRENT-BEHAVIOR INVARIANTS on `domain_phylogeny()`
(the `.360` `_4D` section must still render exactly as specified, unaffected by the additive
`domain_tree_sections()`); the before/after byte comparison stays in the packet as evidence.

Gate-safety invariant: the new blocks use `#### ` headings with NO section-number marker, so
modeb_structure_gate (which keys on §N headings) is unaffected.

Class-level context; non-scoring; judgment deferred.
"""
from mamey import modeb_domain_phylogeny as M


def _pkg(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "AS-1_2_inventory.csv").write_text("bgc_id\nBGC001\n")
    (pkg / "AS-1_4D_two_proof_rescue.csv").write_text(
        "bgc_a,bgc_b,verdict,rggmci_confidence,ks_clade_id,contig_a,contig_b,interpretation\n"
        "BGC001,BGC002,KS_CLADE_ONLY,HIGH,KC1,NODE_1,NODE_2,\n")
    return pkg


def _summary(root, cls, row):
    root.mkdir(parents=True, exist_ok=True)
    hdr = ("domain_class\tstrain\tbgc_id\tnode\ttip\tclade_id\tclade_support\t"
           "nearest_ref\tnearest_ref_family\tpatristic_to_ref\n")
    (root / f"{cls}_domain_tree_summary.tsv").write_text(hdr + row)


def test_4d_section_invariants_unchanged(tmp_path):
    """The .360 _4D section keeps its contract: gate-safe heading, claim-safety comment, the verdict
    row, and no section-number marker."""
    pkg = _pkg(tmp_path)
    out = M.domain_phylogeny(pkg, "BGC001")
    assert out.startswith("#### Domain phylogeny (KS/AT two-proof · _4D)")
    assert "gate-safe subsection" in out
    assert "KS_CLADE_ONLY" in out and "BGC002" in out
    # Composer narrowing (Black Cherry, .400 staging): the SEALED .360 claim-safety comment
    # itself contains the literal "(no §N marker; …)" (modeb_domain_phylogeny.py:138, sealed
    # .399, gate-passing) — a blanket no-§ assert fails on byte-untouched legacy output. Every
    # "§" must belong to that known comment phrase; anything else is a leak.
    assert out.count("§") == out.count("no §N marker"), \
        "no section-number marker may leak into a #### subsection beyond the sealed comment text"


def test_4d_section_handles_absent_and_untouched_regions(tmp_path):
    pkg = _pkg(tmp_path)
    miss = M.domain_phylogeny(pkg, "BGC404")
    assert "No cross-region KS/AT two-proof signal" in miss
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "AS-9_2_inventory.csv").write_text("bgc_id\nBGC001\n")
    nodata = M.domain_phylogeny(empty, "BGC001")
    assert "measurement gap, not a biological negative" in nodata


def test_domain_tree_sections_render_nothing_without_summaries(tmp_path):
    pkg = _pkg(tmp_path)
    assert M.domain_tree_sections(pkg, "BGC001") == ""                      # no tree_root
    assert M.domain_tree_sections(pkg, "BGC001", tree_root=tmp_path) == ""  # root, no files


def test_domain_tree_sections_render_module_core_and_tailoring(tmp_path):
    pkg = _pkg(tmp_path)
    root = tmp_path / "trees" / "AS-1" / "run1"
    _summary(root, "PKS_KS", "PKS_KS\tAS-1\tBGC001\tNODE_1\tAS-1__NODE_1__t\tKC1\t97\t\t\t\n")
    _summary(root, "halogenase",
             "halogenase\tAS-1\tBGC003\tNODE_3\tAS-1__NODE_3__h\tHC2\t88\tRef_A\thalogenase\t0.42\n")
    out = M.domain_tree_sections(pkg, "BGC001", tree_root=tmp_path / "trees")
    assert "#### Domain tree (PKS_KS)" in out and "#### Domain tree (halogenase)" in out
    assert "ITERATIVE-MODULE GUARD" in out          # module-core caveat
    assert "capacity context only" in out           # tailoring caveat (capacity, not identity)
    assert "Ref_A" in out and "0.42" in out
    assert "§" not in out, "gate-safety: no section-number marker in the new subsections"


def test_additive_function_does_not_disturb_the_4d_section(tmp_path):
    """Rendering the new sections must not change what domain_phylogeny() emits for the same package."""
    pkg = _pkg(tmp_path)
    before = M.domain_phylogeny(pkg, "BGC001")
    root = tmp_path / "trees" / "AS-1" / "run1"
    _summary(root, "PKS_KS", "PKS_KS\tAS-1\tBGC001\tNODE_1\tAS-1__NODE_1__t\tKC1\t97\t\t\t\n")
    M.domain_tree_sections(pkg, "BGC001", tree_root=tmp_path / "trees")
    assert M.domain_phylogeny(pkg, "BGC001") == before
