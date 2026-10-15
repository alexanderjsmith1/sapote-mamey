"""Fresh saved-row table rendering must retain the same tag families as replay.

Search, alignment, reference parsing and graphics are replaced by offline fixtures.
The production caller and pure table writer/row builder remain in the exercised path.
"""
import csv
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fresh_saved_split(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    gdr = importlib.import_module("gap_directed_rescue")
    table = importlib.import_module("gap_rescue_gene_table")
    core_id = "SYNTHETIC / NODE_1_length_900_cov_1 / region001 / BGC001"
    partner_id = "SYNTHETIC / NODE_2_length_900_cov_1 / region002 / BGC002"
    core = {"identity": core_id, "contig": "NODE_1_length_900_cov_1", "start": 0, "end": 900}
    regions = [core]
    prots = {
        "q000001": {"tag": "saved_piece_a", "family": "", "aa": "M", "start": 0, "end": 900,
                    "contig": "NODE_1_length_900_cov_1"},
        "q000002": {"tag": "saved_piece_b", "family": "", "aa": "M", "start": 0, "end": 900,
                    "contig": "NODE_2_length_900_cov_1"},
    }
    reference = tmp_path / "SYNTHETIC_REFERENCE.gbk"
    ref = [{"id": "g001", "name": "r_split", "aa": "M"}]
    rows = [{"reference_gene": "1", "name": "r_split", "status": "MISSING_NOT_FOUND",
             "reference_len_aa": "500", "reference_product": "Saved reference annotation",
             "best_locus": "", "best_protein": ""}]
    split = dict.fromkeys(gdr.SPLIT_COLS, "")
    split.update(reference_gene="1", name="r_split", status="SPLIT_ACROSS_CONTIG_ENDS", split_call="CLEAR",
                 piece1_locus="saved_piece_a", piece2_locus="saved_piece_b",
                 piece1_region_identity=core_id, piece2_region_identity=partner_id,
                 piece1_identity_pct="70", piece2_identity_pct="65")
    splits = [split]
    hits, partners, checks = [], [], {"verdicts": {}}
    db, pfam = tmp_path / "saved.dmnd", tmp_path / "saved.hmm"
    calls = []
    def saved_call(name, expected, result):
        def invoke(*args, **kwargs):
            assert args == expected and kwargs == {}
            calls.append(name)
            return result
        return invoke
    monkeypatch.setattr(gdr, "load_reference", saved_call("reference", (reference,), (ref, "Saved reference")))
    monkeypatch.setattr(gdr, "search", saved_call("search", (ref, prots, regions, hits, core), (rows, partners)))
    monkeypatch.setattr(gdr, "split_genes", saved_call("splits", (ref, prots, regions, hits), (splits, "run")))
    monkeypatch.setattr(gdr, "partner_checks", saved_call(
        "checks", (rows, prots, hits, core, "SYNTHETIC_REFERENCE", db, pfam, 3, "sensitive"), checks))
    def no_search(*args, **kwargs):
        raise AssertionError("No biological search is allowed in this saved-row caller fixture")
    monkeypatch.setattr(gdr, "run_diamond", no_search)
    monkeypatch.setattr(table, "reference_annotations", lambda path: {})
    monkeypatch.setattr(table, "_draw", lambda *args, **kwargs: False)
    return SimpleNamespace(gdr=gdr, table=table, core=core, core_id=core_id, regions=regions, prots=prots,
                           reference=reference, rows=rows, splits=splits, hits=hits, db=db, pfam=pfam,
                           calls=calls, out=tmp_path / "output")


@pytest.mark.parametrize("families,display", [
    (("Saved smCOG family A", "Saved Pfam family B"), "Saved smCOG family A / Saved Pfam family B"),
    (("Saved smCOG family A", ""), "Saved smCOG family A / -"),
    (("", ""), ""),
])
def test_fresh_split_table_receives_locus_tag_family_aliases(fresh_saved_split, monkeypatch, families, display):
    f = fresh_saved_split
    for protein, family in zip(f.prots.values(), families):
        protein["family"] = family
    map_calls, table_calls = [], []
    monkeypatch.setattr(f.gdr, "draw_locus_map", lambda *args, **kwargs: map_calls.append((args, kwargs)))
    original_writer = f.table.write_gene_table
    def capture_writer(*args, **kwargs):
        table_calls.append((args, kwargs))
        return original_writer(*args, **kwargs)
    monkeypatch.setattr(f.table, "write_gene_table", capture_writer)
    receipt = f.gdr.analyse_region(
        "SYNTHETIC", f.prots, f.regions, f.core, f.reference, "Explicit reference", "saved fixture", f.out,
        hits=f.hits, threads=3, sensitivity="sensitive", mibig_db=f.db, pfam=f.pfam,
        figure=True, write_proteins=False, anchor="r_split", gene_table=True)
    assert f.calls == ["reference", "search", "splits", "checks"]
    assert len(map_calls) == len(table_calls) == 1
    assert map_calls[0] == ((f.reference, f.rows, f.splits, f.prots, f.regions, f.core, "SYNTHETIC",
                             "Explicit reference", f.out / "gap_rescue.png", f.out / "gap_rescue.pdf"),
                            {"anchor": "r_split", "print_width": "double"})
    args, kwargs = table_calls[0]
    assert args[:6] == (f.out, f.rows, f.splits, f.core_id, "SYNTHETIC", f.reference)
    expected = {key: value.get("family", "") for key, value in f.prots.items()}
    expected.update({value["tag"]: value.get("family", "") for value in f.prots.values()})
    assert args[6] == expected
    assert args[7:] == ("Explicit reference", {}) and kwargs == {"pair_map": False}
    with (f.out / "gene_table.tsv").open(newline="") as stream:
        actual = list(csv.DictReader(stream, delimiter="\t"))
    assert len(actual) == 1
    assert actual[0]["CDS"] == "saved_piece_a + saved_piece_b"
    assert actual[0]["Protein family (antiSMASH)"] == display
    assert actual[0]["Reference size (aa)"] == "500"
    assert actual[0]["Local/reference size ratio"] == ""
    assert receipt["core"] == f.core_id and receipt["homology"] == "precomputed hits"
    assert not (f.out / "gap_rescue_proteins.faa").exists()


def test_gene_table_opt_out_keeps_saved_search_and_receipt_without_table(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    def no_table(*args, **kwargs):
        raise AssertionError("gene_table=False must never call the table writer")
    monkeypatch.setattr(f.table, "write_gene_table", no_table)
    receipt = f.gdr.analyse_region(
        "SYNTHETIC", f.prots, f.regions, f.core, f.reference, "Explicit reference", "saved fixture", f.out,
        hits=f.hits, threads=3, sensitivity="sensitive", mibig_db=f.db, pfam=f.pfam,
        figure=False, write_proteins=False, anchor="r_split", gene_table=False)
    assert f.calls == ["reference", "search", "splits", "checks"]
    assert receipt["core"] == f.core_id and receipt["split_genes"][0]["split_call"] == "CLEAR"
    assert (f.out / "gap_rescue.tsv").is_file() and (f.out / "gap_rescue_receipt.json").is_file()
    assert not (f.out / "gene_table.tsv").exists()


@pytest.mark.parametrize("prots,expected", [
    ({"q1": {"tag": "tag1", "family": "A"}, "q2": {"tag": "tag2", "family": "B"}},
     {"q1": "A", "q2": "B", "tag1": "A", "tag2": "B"}),
    ({"q1": {"tag": "q2", "family": "A"}, "q2": {"tag": "tag2", "family": "A"}},
     {"q1": "A", "q2": "A", "tag2": "A"}),
    ({"q1": {"tag": "same", "family": "A"}, "q2": {"tag": "same", "family": "A"}},
     {"q1": "A", "q2": "A", "same": "A"}),
    ({"q1": {"tag": "tag1", "family": ""}, "q2": {"tag": "tag2", "family": ""}},
     {"q1": "", "q2": "", "tag1": "", "tag2": ""}),
    ({"q1": {"tag": "q1"}, "q2": {"tag": "tag2"}},
     {"q1": "", "q2": "", "tag2": ""}),
])
def test_family_lookup_preserves_unambiguous_legacy_mappings(fresh_saved_split, prots, expected):
    before = {key: dict(value) for key, value in prots.items()}
    assert fresh_saved_split.table.protein_families(prots) == expected
    assert prots == before


def _conflicting_families(prots, kind, family_b="B"):
    first, second = prots.values()
    first["family"], second["family"] = "A", family_b
    if kind == "generated_id":
        first["tag"] = list(prots)[1]
    else:
        second["tag"] = first["tag"]


@pytest.mark.parametrize("kind", ["generated_id", "repeated_tag"])
@pytest.mark.parametrize("family_b", ["B", ""])
def test_family_lookup_refuses_conflicting_keys_without_mutation(fresh_saved_split, kind, family_b):
    f = fresh_saved_split
    _conflicting_families(f.prots, kind, family_b)
    before = {key: dict(value) for key, value in f.prots.items()}
    with pytest.raises(ValueError, match="Ambiguous protein-family key.*conflicting family annotations"):
        f.table.protein_families(f.prots)
    assert f.prots == before


@pytest.mark.parametrize("kind", ["generated_id", "repeated_tag"])
def test_fresh_table_refuses_family_collision_before_writer(fresh_saved_split, monkeypatch, kind):
    f = fresh_saved_split
    _conflicting_families(f.prots, kind)
    f.out.mkdir()
    previous = f.out / "gene_table.tsv"
    previous.write_bytes(b"prior table remains unchanged\n")
    def no_table(*args, **kwargs):
        raise AssertionError("An ambiguous family mapping must never reach the table writer")
    monkeypatch.setattr(f.table, "write_gene_table", no_table)
    with pytest.raises(ValueError, match="Ambiguous protein-family key"):
        f.gdr.analyse_region(
            "SYNTHETIC", f.prots, f.regions, f.core, f.reference, "Explicit reference", "saved fixture", f.out,
            hits=f.hits, threads=3, sensitivity="sensitive", mibig_db=f.db, pfam=f.pfam,
            figure=False, write_proteins=False, anchor="r_split", gene_table=True)
    assert f.calls == ["reference", "search", "splits", "checks"]
    assert previous.read_bytes() == b"prior table remains unchanged\n"


def _saved_replay(f, monkeypatch):
    import json
    f.out.mkdir()
    (f.out / "gap_rescue_receipt.json").write_text(json.dumps({
        "core": f.core_id, "label": "SYNTHETIC", "reference_name": "Explicit reference"}))
    with (f.out / "gap_rescue.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(f.rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(f.rows)
    with (f.out / "gap_rescue_split_genes.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(f.splits[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(f.splits)
    zip_path = f.out.parent / "SYNTHETIC.zip"
    def saved_genome(path, label):
        assert path == zip_path and label == "SYNTHETIC"
        return f.prots, f.regions
    monkeypatch.setattr(f.gdr, "load_genome", saved_genome)
    return ["--run", str(f.out), "--zip", str(zip_path), "--reference", str(f.reference)]


def test_replay_table_uses_shared_unambiguous_family_lookup(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    first, second = f.prots.values()
    first["family"], second["family"] = "A", "B"
    argv = _saved_replay(f, monkeypatch)
    calls = []
    def capture_writer(*args, **kwargs):
        calls.append((args, kwargs))
        return {"rows": 1}
    monkeypatch.setattr(f.table, "write_gene_table", capture_writer)
    assert f.table.main(argv) == 0
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:1] == (f.out,) and args[3:6] == (f.core_id, "SYNTHETIC", f.reference)
    assert args[6] == {"q000001": "A", "q000002": "B", "saved_piece_a": "A", "saved_piece_b": "B"}
    assert args[7:] == ("Explicit reference", {}, {"saved_piece_a", "saved_piece_b"})
    assert kwargs == {} and f.calls == []


@pytest.mark.parametrize("kind", ["generated_id", "repeated_tag"])
def test_replay_table_refuses_family_collision_before_writer(fresh_saved_split, monkeypatch, kind):
    f = fresh_saved_split
    _conflicting_families(f.prots, kind)
    argv = _saved_replay(f, monkeypatch)
    previous = f.out / "gene_table.tsv"
    previous.write_bytes(b"prior replay table remains unchanged\n")
    def no_table(*args, **kwargs):
        raise AssertionError("An ambiguous family mapping must never reach the replay table writer")
    monkeypatch.setattr(f.table, "write_gene_table", no_table)
    with pytest.raises(ValueError, match="Ambiguous protein-family key"):
        f.table.main(argv)
    assert previous.read_bytes() == b"prior replay table remains unchanged\n"
    assert f.calls == []
