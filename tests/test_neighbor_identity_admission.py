"""Synthetic identity-admission checks; no trees or renderers are invoked."""
import importlib.util
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("neighbor_candidate", ROOT / "tools/bgc_neighbor_layer.py")
layer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layer)


def row(**updates):
    value = dict(strain="STRAIN-1", genome_file="public_reference.fna", related_organism="Public reference", accession="ACC", status="downloaded")
    value.update(updates)
    return value


@pytest.mark.parametrize("strain", ["", "  ", None])
def test_missing_strain_refused(strain):
    with pytest.raises(ValueError, match="nonblank strain"):
        layer.build_layer([row(strain=strain)])


@pytest.mark.parametrize("filename", ["", " ", None, ".fna"])
def test_missing_tip_refused(filename):
    with pytest.raises(ValueError, match="nonblank genome tip"):
        layer.build_layer([row(genome_file=filename)])


@pytest.mark.parametrize("filename", ["STRAIN-10.fna", "STRAIN-1_extra.fna", "path/STRAIN-1extra.fasta"])
def test_prefix_only_identity_held(filename):
    with pytest.raises(ValueError, match="ambiguous query-prefix"):
        layer.build_layer([row(genome_file=filename)])


@pytest.mark.parametrize("updates", [dict(genome_file="path/STRAIN-1.FNA"), dict(related_organism="STRAIN-1"), dict(genome_file="STRAIN-1_decorated.fna", related_organism="STRAIN-1")])
def test_exact_existing_query_mappings_retained(updates):
    assert layer.build_layer([row(**updates)])[0]["layer"] == "query"


def test_neighbor_and_type_contract_retained():
    assert layer.build_layer([row()])[0]["layer"] == "bgc_neighbor"
    assert layer.build_layer([row()], type_names=["Public reference"])[0]["layer"] == "type_16S"
    assert layer.build_layer([row(strain="STRAIN-2")], strain_filter="STRAIN-1") == []


def test_cli_refusal_preserves_output_and_inputs(tmp_path):
    import csv
    source = tmp_path / "neighbors.csv"
    output = tmp_path / "layer.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row()))
        writer.writeheader()
        writer.writerow(row(strain=""))
    before = source.read_bytes()
    output.write_bytes(b"existing output must survive")
    with pytest.raises(SystemExit) as error:
        layer.main(["--csv", str(source), "--out", str(output)])
    assert error.value.code == 2
    assert output.read_bytes() == b"existing output must survive"
    assert source.read_bytes() == before
