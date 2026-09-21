"""Tests for tools/chitinase_hmm_confirm.py -- no sealed package or HMMER run required.

These exercise the decision logic that carries the scientific claims: what counts as a
chitinase, the GH18 catalytic-motif call, foreign-contig provenance, the secretion screen,
and the refuse-rather-than-zero contract. The hmmsearch call itself is not mocked into a
fake positive -- parse_domtbl is fed a real-format domtbl line instead.
"""
import importlib.util, json, os, sys, tempfile, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "chitinase_hmm_confirm.py")
if not os.path.exists(SRC):
    SRC = os.path.join(HERE, "..", "tools", "chitinase_hmm_confirm.py")
spec = importlib.util.spec_from_file_location("chitinase_hmm_confirm", SRC)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def _hit(domain, s=1, e=100, ev=1e-30):
    return dict(domain=domain, acc="PF0", tlen=300, iEval=ev, score=99.0, s=s, e=e)


def test_accessory_domain_alone_is_not_a_chitinase():
    """A carbohydrate-binding module binds chitin; it does not cut it. This is the
    distinction the keyword scan cannot make, and the reason the tool exists."""
    rows = m.classify({"p1": "M" * 300}, {"p1": [_hit("CBM_5_12")]})
    assert rows[0]["classification"] == "CHITIN_BINDING_ACCESSORY_ONLY"
    assert rows[0]["catalytic_domains"] == "NONE"
    assert m.summarise(rows)["chitinase"] == 0
    assert m.summarise(rows)["chitin_binding"] == 1


def test_catalytic_domain_makes_a_candidate_and_families_are_partitioned():
    rows = m.classify({"a": "M" * 300, "b": "M" * 300},
                      {"a": [_hit("Glyco_hydro_18")], "b": [_hit("Glyco_hydro_19")]})
    s = m.summarise(rows)
    assert s["chitinase"] == 2
    assert s["families"] == {"GH18": 1, "GH19": 1}


def test_gh18_catalytic_motif_present_vs_absent():
    """Losing the terminal catalytic glutamate marks a chitinase-like binding protein.
    A raw GH18 count cannot see this; 31% of the bee/wasp cohort's GH18 lack it."""
    intact = "A" * 20 + "DGLDLDIE" + "A" * 72
    lost = "A" * 20 + "DGLDLDIQ" + "A" * 72
    rows = m.classify({"i": intact, "l": lost},
                      {"i": [_hit("Glyco_hydro_18", 1, 100)],
                       "l": [_hit("Glyco_hydro_18", 1, 100)]})
    by = {r["protein"]: r for r in rows}
    assert by["i"]["gh18_catalytic_motif"] == "DxxDxDxE_PRESENT"
    assert by["l"]["gh18_catalytic_motif"] == "DxxDxDxE_ABSENT"
    s = m.summarise(rows)
    assert s["gh18_motif_present"] == 1 and s["gh18_motif_absent"] == 1


def test_foreign_contig_is_flagged_and_excluded_from_counts_but_not_deleted():
    """AS-932's five 'chitinases' sat at GC 44-50% against a 67.7% core genome. Without
    this the cohort reads '4 of 5 Nocardia lack chitinase, one exception'."""
    contigs = {"big": {"length": 500000, "gc": 68.0, "cov": 15.0},
               "small": {"length": 3000, "gc": 46.0, "cov": 3.0}}
    rows = m.classify({"native": "M" * 300, "foreign": "M" * 300},
                      {"native": [_hit("Glyco_hydro_18")], "foreign": [_hit("Glyco_hydro_18")]},
                      contig_of={"native": "big", "foreign": "small"}, contigs=contigs)
    by = {r["protein"]: r for r in rows}
    assert by["foreign"]["contig_provenance"] == "FOREIGN_CONTIG_SUSPECT"
    assert by["native"]["contig_provenance"] == "CONSISTENT_WITH_CORE_GENOME"
    assert by["foreign"]["contig_provenance_basis"]          # basis recorded, not silent
    s = m.summarise(rows)
    assert s["chitinase"] == 1                                # excluded from the count
    assert s["excluded_foreign_contig"] == 1                  # but still reported
    assert len(rows) == 2                                     # and NOT deleted


def test_secretion_screen_is_labelled_not_signalp():
    sec = "MRKLAALLTAALLAGCSSAAEA" + "G" * 80          # charged n, hydrophobic h, A-X-A
    cyto = "MGDDEEGGDDEEGGDDEEGG" + "G" * 80
    rows = m.classify({"s": sec, "c": cyto},
                      {"s": [_hit("Glyco_hydro_18")], "c": [_hit("Glyco_hydro_18")]})
    by = {r["protein"]: r for r in rows}
    assert by["s"]["secretion_state"] != "NO_SIGNAL_DETECTED"
    assert by["c"]["secretion_state"] == "NO_SIGNAL_DETECTED"
    assert all(r["secretion_method"] == "RULE_BASED_SCREEN_NOT_SIGNALP" for r in rows)


def test_missing_hmmer_refuses_rather_than_returning_zero():
    """A zero count reads as 'no chitinase'. Missing evidence is not biological absence."""
    with pytest.raises(m.ChitinaseConfirmError) as e:
        m._require("hmmsearch_definitely_not_installed_xyz")
    assert "cannot substitute a keyword scan" in str(e.value)


def test_parse_domtbl_reads_real_format():
    line = ("prot1 - 300 Glyco_hydro_18 PF00704.35 250 1e-40 140.0 0.1 1 1 "
            "1e-42 2e-38 138.0 0.1 5 240 10 260 12 258 0.95 chitinase\n")
    with tempfile.NamedTemporaryFile("w", suffix=".domtbl", delete=False) as fh:
        fh.write("# comment\n" + line.replace(" ", "\t")); p = fh.name
    try:
        hits = m.parse_domtbl(p)
        assert "prot1" in hits and hits["prot1"][0]["domain"] == "Glyco_hydro_18"
    finally:
        os.unlink(p)


def test_every_row_carries_a_claim_ceiling():
    rows = m.classify({"p": "M" * 300}, {"p": [_hit("Glyco_hydro_18")]})
    assert all("judgment deferred" in r["claim_ceiling"] for r in rows)
    assert "not expression" in m.summarise(rows)["claim_safety"]
