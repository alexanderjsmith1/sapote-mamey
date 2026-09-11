"""Exercise each declared typed contract code at its real producer and CLI boundary."""

import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "tools" / "build_placement_ggtree_inputs.py"
FUSED = (
    "NR_026535_1_Streptomyces_odorifer_strain_DSM_40347_16S_ribosomal_RNA_partial_sequence"
    "_NR_119341_1_Streptomyces_albidoflavus_strain_DSM_40455_16S_ribosomal_RNA_partial_sequence"
)
CLI_CODES = {
    "BIOASSAY_METADATA_SCHEMA",
    "BIOASSAY_METADATA_IDENTITY",
    "BIOASSAY_METADATA_VALUE",
    "BIOASSAY_METADATA_DUPLICATE",
    "BIOASSAY_METADATA_CONFLICT",
    "AUX_METADATA_SCHEMA",
    "AUX_METADATA_IDENTITY_OR_WIDTH",
    "AUX_METADATA_CONFLICT",
    "REFERENCE_ACCESSION_CONFLICT",
    "REFERENCE_SOURCE_ACCESSION_INVALID",
    "REFERENCE_SOURCE_FIELD_INVALID",
    "REFERENCE_SOURCE_CONFLICT",
    "HOST_METADATA_CONFLICT",
    "REQUIRED_REFERENCE_TABLE_SCHEMA",
    "REQUIRED_REFERENCE_TABLE_WIDTH",
    "REQUIRED_REFERENCE_TABLE_IDENTITY",
    "REQUIRED_REFERENCE_TABLE_CONFLICT",
}


def _tree(path, reference="Streptomyces_coelicolor_NC_003888.3"):
    path.write_text(f"(SID_1:0.1,{reference}:0.1);\n", encoding="utf-8")


def _finals(prefix):
    return [Path(str(prefix) + suffix) for suffix in (
        "_pruned.nwk", "_ggtree_annotation.tsv", "_metadata_receipt.json"
    )]


def _sentinels(prefix):
    outputs = _finals(prefix)
    for index, path in enumerate(outputs):
        path.write_bytes(f"prior-{index}".encode("ascii"))
    return {path: path.read_bytes() for path in outputs}


def _db(path, rows):
    with sqlite3.connect(path) as con:
        con.execute(
            "CREATE TABLE record("
            "acc_base, isolation_source, host, country)"
        )
        con.executemany("INSERT INTO record VALUES (?,?,?,?)", rows)


def _cli_case(tmp_path, code):
    tree = tmp_path / "tree.nwk"
    reference = FUSED if code == "REFERENCE_ACCESSION_CONFLICT" else "Streptomyces_coelicolor_NC_003888.3"
    _tree(tree, reference)
    prefix = tmp_path / "result"
    before = _sentinels(prefix)
    args = [
        sys.executable, str(PRODUCER), "--graft", str(tree),
        "--out-prefix", str(prefix), "--keep-all-refs",
    ]

    if code.startswith("BIOASSAY_"):
        table = tmp_path / "bioassay.csv"
        cases = {
            "BIOASSAY_METADATA_SCHEMA": "wrong,anti_Candida,anti_MRSA\nSID_1,positive,negative\n",
            "BIOASSAY_METADATA_IDENTITY": "strain,anti_Candida,anti_MRSA\n,positive,negative\n",
            "BIOASSAY_METADATA_VALUE": "strain,anti_Candida,anti_MRSA\nSID_1,posiitve,negative\n",
            "BIOASSAY_METADATA_DUPLICATE": "strain,anti_Candida,anti_MRSA\nSID_1,positive,negative\nSID_1,positive,negative\n",
            "BIOASSAY_METADATA_CONFLICT": "strain,anti_Candida,anti_MRSA\nSID_1,positive,negative\nSID_1,negative,positive\n",
        }
        table.write_text(cases[code], encoding="utf-8")
        args += ["--bioassay-table", str(table)]
    elif code.startswith("REQUIRED_REFERENCE_TABLE_"):
        table = tmp_path / "required.tsv"
        cases = {
            "REQUIRED_REFERENCE_TABLE_SCHEMA": "wrong\treference_species\nSID_1\tStreptomyces coelicolor\n",
            "REQUIRED_REFERENCE_TABLE_WIDTH": "strain\treference_species\nSID_1\tStreptomyces coelicolor\textra\n",
            "REQUIRED_REFERENCE_TABLE_IDENTITY": "strain\treference_species\nSID_1\tS. coelicolor\n",
            "REQUIRED_REFERENCE_TABLE_CONFLICT": (
                "strain\treference_species\n"
                "SID_1\tStreptomyces coelicolor\n"
                "SID_1\tStreptomyces sampsonii\n"
            ),
        }
        table.write_text(cases[code], encoding="utf-8")
        args += ["--required-reference-table", str(table)]
    elif code.startswith("AUX_"):
        aux1 = tmp_path / "aux1.tsv"
        if code == "AUX_METADATA_SCHEMA":
            aux1.write_text("wrong\thost\nSID_1\tmoss\n", encoding="utf-8")
        elif code == "AUX_METADATA_IDENTITY_OR_WIDTH":
            aux1.write_text(
                "strain\thost\tregion\taccession\nSID_1\tmoss\tOntario\n",
                encoding="utf-8",
            )
        else:
            aux2 = tmp_path / "aux2.tsv"
            aux1.write_text(
                "strain\thost\tregion\taccession\nSID_1\tmoss\tOntario\tA1\n",
                encoding="utf-8",
            )
            aux2.write_text(
                "strain\thost\tregion\taccession\nSID_1\tant\tOntario\tA1\n",
                encoding="utf-8",
            )
            args += ["--aux-table", str(aux2)]
        args += ["--aux-table", str(aux1)]
    elif code == "HOST_METADATA_CONFLICT":
        host = tmp_path / "host.tsv"
        host.write_text(
            "Strain Number\tHost\tLocation\tGenbank Accession\n"
            "SID_1\tmoss\tOntario\tA1\n",
            encoding="utf-8",
        )
        aux = tmp_path / "aux.tsv"
        aux.write_text(
            "strain\thost\tregion\taccession\nSID_1\tant\tOntario\tA1\n",
            encoding="utf-8",
        )
        args += ["--host-table", str(host), "--aux-table", str(aux)]
    elif code.startswith("REFERENCE_SOURCE_"):
        db = tmp_path / "source.sqlite"
        if code == "REFERENCE_SOURCE_ACCESSION_INVALID":
            rows = [("not-an-accession", "soil", "", "Canada")]
        elif code == "REFERENCE_SOURCE_FIELD_INVALID":
            rows = [("NC_003888.3", sqlite3.Binary(b"bad\nfield"), "", "Canada")]
        else:
            rows = [
                ("NC_003888.3", "soil", "", "Canada"),
                ("NC_003888.3", "water", "", "Canada"),
            ]
        _db(db, rows)
        args += ["--ref-source-db", str(db)]

    proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return proc, before


@pytest.mark.parametrize("code", sorted(CLI_CODES))
def test_real_cli_producer_refuses_and_preserves_existing_outputs(tmp_path, code):
    proc, before = _cli_case(tmp_path, code)
    assert proc.returncode == 2, proc.stderr
    assert code in proc.stderr
    assert "Traceback" not in proc.stderr
    assert {path: path.read_bytes() for path in before} == before


def test_real_producer_matrix_exactly_covers_the_declared_registry():
    assert CLI_CODES | {"METADATA_SOURCE_CHANGED_DURING_RUN"} == _mod()._TYPED_CODES


def _mod():
    spec = importlib.util.spec_from_file_location("_placement_source_change", PRODUCER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_change_code_runs_from_main_and_preserves_existing_outputs(tmp_path, monkeypatch, capsys):
    module = _mod()
    tree = tmp_path / "tree.nwk"
    _tree(tree)
    prefix = tmp_path / "result"
    before = _sentinels(prefix)

    from Bio import Phylo
    original_write = Phylo.write

    def write_then_change(*args, **kwargs):
        result = original_write(*args, **kwargs)
        tree.write_text(tree.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
        return result

    monkeypatch.setattr(Phylo, "write", write_then_change)
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])
    with pytest.raises(SystemExit) as caught:
        module._run_or_refuse()

    assert caught.value.code == 2
    assert "METADATA_SOURCE_CHANGED_DURING_RUN" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in before} == before


def test_unmatched_bioassay_warning_agrees_with_output(tmp_path):
    import csv
    tree = tmp_path / "tree.nwk"
    _tree(tree)
    table = tmp_path / "bioassay.csv"
    table.write_text("strain,anti_Candida,anti_MRSA\nSID_2,not_tested,not_tested\n")
    prefix = tmp_path / "result"
    proc = subprocess.run([
        sys.executable, str(PRODUCER), "--graft", str(tree),
        "--out-prefix", str(prefix), "--keep-all-refs", "--bioassay-table", str(table),
    ], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    with Path(str(prefix) + "_ggtree_annotation.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    query = next(row for row in rows if row["bioassay_status"])
    assert query["bioassay_status"] == "NOT_RECORDED"
    assert "bioassay_status will read NOT_RECORDED" in proc.stderr
    assert "bioassay_status will read NOT_TESTED" not in proc.stderr
