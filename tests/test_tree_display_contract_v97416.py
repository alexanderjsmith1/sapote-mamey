"""Generic behavior tests for display collapse, receipts and retained distances."""
import csv
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
pytest.importorskip("Bio", reason="tree behavior tests require optional Biopython")
from Bio import Phylo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import collapse_near_identical as collapse
import gate_stem_aware as gate
import add_reference_source_labels as sources

BASE = "ACGT" * 150
PARAMETERS = dict(max_nt=2, min_cols=500, protect=[], prune_outgroup=False)


def mutate(seq, *positions):
    result = list(seq)
    for i in positions:
        result[i] = "C" if result[i] == "A" else "A"
    return "".join(result)


def table(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def panel(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    tree = tmp_path / "analysis tree.nwk"
    tree.write_text("((((REF_A:0.010000123456789,REF_B:0.010000323456789):0.005000432198,"
                    "REF_C:0.015000555654789):0.02,(QUERY_A:0.012345678912345,REF_D:0.013456789123456):"
                    "0.021234567891234):0.025678912345678,OUTGROUP_REF:0.081234567891234);\n")
    seqs = dict(REF_A=BASE, REF_B=mutate(BASE, 0), REF_C=mutate(BASE, 1),
                QUERY_A=BASE, REF_D=BASE, OUTGROUP_REF=BASE)
    aln = tmp_path / "alignment.fasta"
    aln.write_text("".join(f">{key}\n{value}\n" for key, value in seqs.items()))
    rows = []
    for i, key in enumerate(seqs):
        role = "query" if key == "QUERY_A" else "outgroup" if key == "OUTGROUP_REF" else "reference"
        organism = "Example gamma reference" if role == "outgroup" else "Query isolate Q01" if role == "query" else f"Example organism {key}"
        rows.append(dict(tip=key, label=f"{organism} [source {i}] (NR_12345{i}.1)",
                         role=role, taxon="Example alpha" if key != "REF_D" else "Example beta",
                         source=f"source {i}", category="plant", accession=f"NR_12345{i}.1"))
    meta = tmp_path / "metadata.tsv"
    meta.write_bytes(collapse.tsv_bytes(list(rows[0]), rows))
    return aln, tree, meta


def make_display(tmp_path, **parameters):
    aln, tree, meta = panel(tmp_path)
    receipt, sha = collapse.create_display(aln, tree, meta, tmp_path / "panel", {**PARAMETERS, **parameters})
    return aln, tree, meta, receipt, sha


def display_paths(receipt):
    data = json.loads(receipt.read_text())
    return {k: (receipt.parent / v["path"]).resolve() for k, v in data["outputs"].items()}


def verify(case):
    _, parent, _, receipt, sha = case
    paths = display_paths(receipt)
    return gate.verify_display(receipt, sha, paths["tree"], paths["metadata"], parent)


@pytest.mark.parametrize("prune", [False, True])
def test_collapse_preserves_queries_members_metadata_and_precise_distances(tmp_path, prune):
    case = make_display(tmp_path, prune_outgroup=prune)
    aln, parent, meta, receipt, sha = case
    before = {p: p.read_bytes() for p in (aln, parent, meta)}
    paths = display_paths(receipt)
    original = Phylo.read(parent, "newick")
    displayed = Phylo.read(paths["tree"], "newick")
    tips = {t.name for t in displayed.get_terminals()}
    assert {"REF_A", "QUERY_A", "REF_D"} <= tips
    assert "REF_B" not in tips and "REF_C" not in tips
    assert ("OUTGROUP_REF" in tips) == (not prune)
    for x, y in itertools.combinations(tips, 2):
        assert displayed.distance(x, y) == pytest.approx(original.distance(x, y), abs=1e-15, rel=1e-14)
    ledger = table(paths["ledger"])
    assert len(ledger) == 6 and len({r["tip"] for r in ledger}) == 6
    assert {r["tip"]: json.loads(r["original_metadata_json"]) for r in ledger} == {r["tip"]: r for r in table(meta)}
    rep = next(r for r in table(paths["metadata"]) if r["tip"] == "REF_A")
    assert rep["source"] == "" and rep["category"] == "" and rep["accession"] == ""
    assert "source 0" not in rep["label"] and "3 reference isolates" in rep["label"]
    assert next(r for r in ledger if r["tip"] == "REF_A")["max_pair_mismatches"] == "2"
    assert all(p.read_bytes() == b for p, b in before.items())
    verify(case)


def test_nonclade_neighbors_and_named_taxa_do_not_merge(tmp_path):
    aln, tree, meta = panel(tmp_path)
    rows = table(meta)
    rows[2]["taxon"] = "Example gamma"
    meta.write_bytes(collapse.tsv_bytes(list(rows[0]), rows))
    data = collapse.build_display(aln, tree, meta, PARAMETERS)
    rows = list(csv.DictReader(data["ledger"].decode().splitlines(), delimiter="\t"))
    assert next(r for r in rows if r["tip"] == "REF_C")["action"] == "RETAINED"
    assert next(r for r in rows if r["tip"] == "REF_D")["action"] == "RETAINED"
    assert next(r for r in rows if r["tip"] == "REF_B")["action"] == "COLLAPSED_MEMBER"


def test_complete_linkage_checks_member_pairs_and_finds_smaller_clades(tmp_path):
    aln, tree, meta = panel(tmp_path)
    seqs = collapse.read_fasta(aln)
    seqs["REF_C"] = mutate(BASE, 1, 2)  # A-C=2, B-C=3; whole clade must not merge.
    aln.write_text("".join(f">{n}\n{s}\n" for n, s in seqs.items()))
    data = collapse.build_display(aln, tree, meta, PARAMETERS)
    assert "REF_C:" in data["tree"].decode() and "REF_B:" not in data["tree"].decode()


def test_ambiguous_columns_are_excluded_and_threshold_is_exact(tmp_path):
    assert collapse.mismatches("ACGTRY-N?", "ACGTAAANA") == (0, 4)
    aln, tree, meta = panel(tmp_path)
    data = collapse.build_display(aln, tree, meta, {**PARAMETERS, "min_cols": 601})
    assert len(Phylo.read(__import__('io').StringIO(data["tree"].decode()), "newick").get_terminals()) == 6
    data = collapse.build_display(aln, tree, meta, {**PARAMETERS, "min_cols": 600, "max_nt": 1})
    assert "REF_C:" in data["tree"].decode() and "REF_B:" not in data["tree"].decode()


@pytest.mark.parametrize("change,error", [
    ("duplicate_fasta", "DUPLICATE_FASTA"), ("duplicate_meta", "DUPLICATE_METADATA"),
    ("duplicate_tree", "DUPLICATE_OR_EMPTY_TREE"), ("unequal", "UNEQUAL_LENGTHS"),
    ("missing_aln", "SETS_DIFFER"), ("missing_meta", "SETS_DIFFER"),
    ("invalid_symbol", "INVALID_DNA"), ("query_conflict", "QUERY_ROLE_CONFLICT"),
    ("outgroup_conflict", "OUTGROUP_ROLE_CONFLICT"), ("row_width", "ROW_WIDTH"),
    ("negative_branch", "NONNEGATIVE_BRANCH"), ("missing_branch", "NONNEGATIVE_BRANCH"),
])
def test_invalid_inputs_refuse_before_any_output(tmp_path, change, error):
    aln, tree, meta = panel(tmp_path)
    if change == "duplicate_fasta": aln.write_text(aln.read_text() + ">REF_A\n" + BASE + "\n")
    elif change == "duplicate_meta": meta.write_text(meta.read_text() + meta.read_text().splitlines()[1] + "\n")
    elif change == "duplicate_tree": tree.write_text(tree.read_text().replace("REF_B", "REF_A"))
    elif change == "unequal": aln.write_text(aln.read_text().replace(BASE, BASE[:-1], 1))
    elif change == "missing_aln": aln.write_text("\n".join(aln.read_text().splitlines()[:-2]) + "\n")
    elif change == "missing_meta": meta.write_text("\n".join(meta.read_text().splitlines()[:-1]) + "\n")
    elif change == "invalid_symbol": aln.write_text(aln.read_text().replace(BASE, "Z" + BASE[1:], 1))
    elif change == "query_conflict": meta.write_text(meta.read_text().replace("\tquery\t", "\treference\t"))
    elif change == "outgroup_conflict": meta.write_text(meta.read_text().replace("\toutgroup\t", "\treference\t"))
    elif change == "row_width": meta.write_text(meta.read_text().rstrip() + "\textra\n")
    elif change == "negative_branch": tree.write_text(tree.read_text().replace("REF_A:0.", "REF_A:-0."))
    elif change == "missing_branch": tree.write_text(tree.read_text().replace(":0.010000123456789", ""))
    with pytest.raises(ValueError, match=error):
        collapse.create_display(aln, tree, meta, tmp_path / "refused", PARAMETERS)
    assert not list(tmp_path.glob("refused*"))


@pytest.mark.parametrize("parameters", [{"max_nt": -1}, {"min_cols": 0}, {"protect": ["MISSING"]}])
def test_invalid_parameters_fail_closed(tmp_path, parameters):
    aln, tree, meta = panel(tmp_path)
    with pytest.raises(ValueError): collapse.build_display(aln, tree, meta, {**PARAMETERS, **parameters})


def test_additional_protection_and_outgroup_pruning_are_explicit(tmp_path):
    aln, tree, meta = panel(tmp_path)
    data = collapse.build_display(aln, tree, meta, {**PARAMETERS, "protect": ["REF_A"]})
    assert "REF_A:" in data["tree"].decode() and "REF_B:" in data["tree"].decode()
    with pytest.raises(ValueError, match="PROTECTED"):
        collapse.build_display(aln, tree, meta, {**PARAMETERS, "protect": ["OUTGROUP_REF"], "prune_outgroup": True})
    tree.write_text("((REF_A:0.01,OUTGROUP_REF:0.03):0.01,(REF_B:0.01,REF_C:0.01,QUERY_A:0.01,REF_D:0.01):0.01);")
    with pytest.raises(ValueError, match="EXCLUSIVE_ROOT_SISTER"):
        collapse.build_display(aln, tree, meta, {**PARAMETERS, "prune_outgroup": True})


@pytest.mark.parametrize("target", ["alignment", "analysis_tree", "input_metadata", "tree", "metadata", "ledger", "receipt"])
def test_every_bound_input_and_output_and_receipt_is_checked(tmp_path, target):
    case = make_display(tmp_path)
    aln, parent, meta, receipt, sha = case
    path = {"alignment": aln, "analysis_tree": parent, "input_metadata": meta, "receipt": receipt,
            **display_paths(receipt)}[target]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="HASH_MISMATCH|BOUND_FILE_CHANGED"):
        verify(case)


def test_rehashed_arbitrary_display_cannot_pass_replay(tmp_path):
    case = make_display(tmp_path)
    aln, parent, meta, receipt, sha = case
    paths = display_paths(receipt)
    paths["tree"].write_text(paths["tree"].read_text().replace("0.02", "0.03", 1))
    data = json.loads(receipt.read_text())
    data["outputs"]["tree"] = collapse.binding(paths["tree"], receipt.parent)
    receipt.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="REPLAY_MISMATCH"):
        gate.verify_display(receipt, collapse.digest(receipt.read_bytes()), paths["tree"], paths["metadata"], parent)


def test_relocated_receipt_and_output_bundle_remains_valid(tmp_path):
    case = make_display(tmp_path / "first")
    shutil.copytree(tmp_path / "first", tmp_path / "moved with spaces")
    _, _, _, receipt, sha = case
    moved = tmp_path / "moved with spaces" / receipt.name
    paths = display_paths(moved)
    gate.verify_display(moved, sha, paths["tree"], paths["metadata"])


def test_existing_output_is_never_overwritten(tmp_path):
    case = make_display(tmp_path)
    _, _, _, receipt, _ = case
    before = receipt.read_bytes()
    with pytest.raises(ValueError, match="OUTPUT_EXISTS"):
        collapse.create_display(*case[:3], tmp_path / "panel", PARAMETERS)
    assert receipt.read_bytes() == before


def test_alignment_order_does_not_change_outputs(tmp_path):
    aln, tree, meta = panel(tmp_path)
    first = collapse.build_display(aln, tree, meta, PARAMETERS)
    seqs = collapse.read_fasta(aln)
    aln.write_text("".join(f">{n}\n{s}\n" for n, s in reversed(list(seqs.items()))))
    assert first == collapse.build_display(aln, tree, meta, PARAMETERS)


def test_sibling_checker_resolution_and_visible_unavailable(tmp_path):
    assert gate._engine_gate() == (ROOT / "tools/tree_sanity_check.py").resolve()
    tool_dir = tmp_path / "tools"; tool_dir.mkdir()
    package = tmp_path / "mamey"; package.mkdir()
    (package / "__init__.py").write_text("")
    shutil.copy(ROOT / "mamey/csv_safety.py", package)
    wrapper = tool_dir / "gate_stem_aware.py"
    shutil.copy(ROOT / "tools/gate_stem_aware.py", wrapper)
    shutil.copy(ROOT / "tools/collapse_near_identical.py", tool_dir)
    shutil.copy(ROOT / "tools/_console.py", tool_dir)
    tree = tmp_path / "test.nwk"; tree.write_text("(A:0.1,OUTGROUP_X:0.1);")
    cp = subprocess.run([sys.executable, str(wrapper), str(tree)], text=True, capture_output=True,
                        env=dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ROOT)))
    assert cp.returncode == 3 and "GATE_UNAVAILABLE" in cp.stderr


def test_stem_exemption_uses_structure_and_retains_other_checks(tmp_path):
    tree = tmp_path / "test.nwk"
    tree.write_text("((A:0.01,B:0.01):0.8,OUTGROUP_X:0.8);")
    ok, report = gate.gate(tree)
    assert ok and "stem-exemption" in report
    tree.write_text("((A:0.91,B:0.01):0.8,OUTGROUP_X:0.8);")
    assert not gate.gate(tree)[0]
    tree.write_text("(((A:0.01,B:0.01):0.8,C:0.01):0.001,OUTGROUP_X:0.8);")
    assert not gate.gate(tree)[0]
    tree.write_text("((A:0.01,B:0.01):0.8,C:0.8);")
    assert not gate.gate(tree)[0]


def test_wrong_parent_same_filename_ledger_and_missing_receipt_do_not_authorize(tmp_path):
    case = make_display(tmp_path)
    _, parent, _, receipt, sha = case
    paths = display_paths(receipt)
    other = tmp_path / "other.nwk"; other.write_text(parent.read_text())
    with pytest.raises(ValueError, match="PARENT_DOES_NOT_MATCH"):
        gate.verify_display(receipt, sha, paths["tree"], paths["metadata"], other)
    cp = subprocess.run([sys.executable, str(ROOT / "tools/gate_stem_aware.py"), str(paths["tree"]),
                         "--parent", str(parent)], capture_output=True, text=True)
    assert cp.returncode == 2 and "hash-bound display receipt" in cp.stderr


def source_fixture(tmp_path):
    import sqlite3
    _, _, meta = panel(tmp_path)
    rows = table(meta)
    for row in rows:
        row["label"] = f'Example organism {row["tip"]} (T) ({row["accession"]})'
    meta.write_bytes(collapse.tsv_bytes(list(rows[0]), rows))
    db = tmp_path / "source.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE record(acc_version TEXT, isolation_source TEXT, host TEXT, geo_loc_name TEXT)")
        con.executemany("INSERT INTO record VALUES(?,?,?,?)", [
            ("NR_123450.1", "rhizosphere soil", "host A", "country A"),
            ("NR_123451.2", "wrong version habitat", "", ""),
            ("NR_123452.1", "", "host C", ""),
            ("NR_123454.1", "", "", "country D")])
    return meta, db


def test_source_labels_use_exact_versions_preserve_records_and_ordinary_outgroup(tmp_path):
    meta, db = source_fixture(tmp_path)
    before = {p: p.read_bytes() for p in (meta, db)}
    rows = sources.enrich(meta, db, tmp_path / "enriched.tsv")
    by_tip = {r["tip"]: r for r in rows}
    assert "[rhizosphere soil] (T) (NR_123450.1)" in by_tip["REF_A"]["label"]
    assert by_tip["REF_B"]["source_label_state"] == "RECORD_MISSING"
    assert "[host C]" in by_tip["REF_C"]["label"]
    assert "[location: country D]" in by_tip["REF_D"]["label"]
    assert by_tip["REF_A"]["source_record_field"] == "isolation_source"
    original = {r["tip"]: r for r in table(meta)}
    for tip in ("QUERY_A", "OUTGROUP_REF"):
        assert by_tip[tip]["label"] == original[tip]["label"]
    assert all(p.read_bytes() == b for p, b in before.items())


def test_source_ambiguity_and_existing_source_are_preserved_as_holds(tmp_path):
    import sqlite3
    meta, db = source_fixture(tmp_path)
    rows = table(meta)
    rows[2]["label"] += " [old source]"
    rows[4]["label"] += " (NR_765432.1)"
    meta.write_bytes(collapse.tsv_bytes(list(rows[0]), rows))
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO record VALUES('NR_123450.1','other source','','')")
    result = {r["tip"]: r for r in sources.enrich(meta, db, tmp_path / "enriched.tsv")}
    assert result["REF_A"]["source_label_state"] == "RECORD_AMBIGUOUS"
    assert result["REF_C"]["source_label_state"] == "EXISTING_LABEL_RETAINED_REVIEW_SOURCE"
    assert result["REF_D"]["source_label_state"] == "ACCESSION_UNBOUND_OR_CONFLICTING"


def test_missing_source_database_does_not_create_a_database(tmp_path):
    _, _, meta = panel(tmp_path)
    absent = tmp_path / "absent.sqlite"
    with pytest.raises(ValueError, match="DATABASE_MISSING"):
        sources.enrich(meta, absent, tmp_path / "enriched.tsv")
    assert not absent.exists() and not (tmp_path / "enriched.tsv").exists()
