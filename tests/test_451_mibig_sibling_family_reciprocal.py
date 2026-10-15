"""Sibling reference entries must be considered by the reciprocal family check.
Compound names are complete strings, and chemical-prefix matching must avoid unrelated stems.
"""
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from mamey import ref_completion as rc  # noqa: E402

A2, D = "BGC0000469", "BGC0000470"
LISTS = {A2: ["bottromycin A2"], D: ["bottromycin D"]}


def _gdr():
    spec = importlib.util.spec_from_file_location("gap_directed_rescue_451s", ROOT / "tools/gap_directed_rescue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sibling_entries_of_one_compound_are_one_family():
    assert rc.same_family(D, A2, LISTS)
    assert not rc.same_family(D, A2, {})


def test_string_valued_names_are_read_as_names_not_characters():
    # load_mibig_names gives one string per accession, several names joined by "/"
    assert rc.same_family(D, A2, {A2: "bottromycin A2", D: "bottromycin D"})
    assert rc.compound_names("abyssomicin M/abyssomicin N") == ["abyssomicin M", "abyssomicin N"]
    assert rc.same_family("X", "Y", {"X": "abyssomicin M/abyssomicin N", "Y": "abyssomicin C"})
    assert rc.compound_names(None) == [] and rc.compound_names(["a"]) == ["a"]


def test_a_name_inside_another_name_is_not_a_family():
    assert not rc.same_family("I", "D", {"I": ["istamycin"], "D": ["disgocidine", "distamycin", "congocidine"]})
    assert not rc.same_family("P", "S", {"P": ["phosphonoglycans"], "S": ["S-layer glycan"]})


def test_chemical_prefixes_still_join_a_family():
    assert rc.same_family("N", "A", {"N": ["Neoabyssomicin B"], "A": ["abyssomicin C", "atrop-abyssomicin C"]})
    assert rc.same_family("K", "B", {"K": ["kendomycin"], "B": ["kendomycin B"]})
    assert rc.same_family("I", "S", {"I": ["isomigrastatin"], "S": ["migrastatin"]})


def _partner_case(compounds):
    prots = {"p1": {"tag": "ctg69_6", "contig": "N69", "start": 100, "end": 1200, "aa": "M" * 358},
             "p2": {"tag": "ctg69_7", "contig": "N69", "start": 1400, "end": 2600, "aa": "M" * 391}}
    rows = [{"status": "MISSING_FOUND_CLEAR", "best_protein": "p1", "reference_gene": "6"},
            {"status": "MISSING_FOUND_CLEAR", "best_protein": "p2", "reference_gene": "5"}]
    core = {"contig": "N28", "start": 0, "end": 5000}

    def search(query, db, **kw):
        hits = []
        for q in ("p1", "p2"):
            hits.append({"qseqid": q, "sseqid": f"{D}|g1", "bitscore": "900", "pident": "99.8"})
            hits.append({"qseqid": q, "sseqid": f"{A2}|g1", "bitscore": "600", "pident": "77.0"})
        return {"ok": True, "hits": hits}

    rc.partner_checks(rows, prots, [], core, A2, mibig_db="mibig.dmnd", search=search, compounds=compounds)
    return [r["partner_verdict"] for r in rows]


def test_a_find_matching_a_sibling_entry_is_not_a_paralog_family():
    assert _partner_case(LISTS) == ["SUPPORTED", "SUPPORTED"]
    assert _partner_case({A2: "bottromycin A2", D: "bottromycin D"}) == ["SUPPORTED", "SUPPORTED"]
    assert _partner_case({}) == ["PARALOG_FAMILY", "PARALOG_FAMILY"]


def test_analyse_region_passes_compounds_to_the_partner_check(monkeypatch, tmp_path):
    gdr = _gdr()

    class Seen(Exception):
        pass

    def fake_checks(*a, **k):
        raise Seen(k.get("compounds"))

    monkeypatch.setattr(gdr, "load_reference", lambda ref: ([], ""))
    monkeypatch.setattr(gdr, "search", lambda *a, **k: ([], []))
    monkeypatch.setattr(gdr, "split_genes", lambda *a, **k: ([], {}))
    monkeypatch.setattr(gdr, "partner_checks", fake_checks)
    with pytest.raises(Seen) as e:
        gdr.analyse_region("AS-0", {}, [], {"contig": "c"}, "BGC0000469.gbk", "bottromycin A2", "given", tmp_path,
                           hits=[], write_proteins=False, figure=False, gene_table=False, compounds=LISTS)
    assert e.value.args[0] == LISTS


def test_both_runners_hand_the_names_to_analyse_region():
    gdr = _gdr()
    assert "compounds=names" in inspect.getsource(gdr.main)
    spec = importlib.util.spec_from_file_location("gap_rescue_all_regions_451s", ROOT / "tools/gap_rescue_all_regions.py")
    allr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(allr)
    assert "compounds=names" in inspect.getsource(allr._run_all)
