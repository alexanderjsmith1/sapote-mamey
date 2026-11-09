"""build_modeb_locus_inventory.py refuses an existing --out and records its coverage limit.

It used to write straight to --out with write_text, replacing any existing
file that was not an input. It also implied the member holds every contig,
which it never checked: it reconciles package CDS keys only.
"""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("Bio")
from Bio import SeqIO  # noqa: E402
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402

TOOL = Path(__file__).parents[1] / "tools/build_modeb_locus_inventory.py"


def _module():
    spec = importlib.util.spec_from_file_location("inventory_exporter_464r3", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inputs(tmp_path):
    record = SeqRecord(Seq("ATG" * 33 + "A"), id="CP000001.1", name="CP000001",
                       description="synthetic public fixture")
    record.annotations["molecule_type"] = "DNA"
    record.features = [SeqFeature(FeatureLocation(0, 9, strand=1), type="CDS",
                                  qualifiers={"locus_tag": ["gene_1"], "translation": ["MMM"]})]
    source = tmp_path / "whole.gbk"
    SeqIO.write([record], source, "genbank")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "PUBLIC-1_cds_table.csv").write_text(
        "strain,contig,locus_tag,start,end,strand,length_aa,region,bgc_id\n"
        "PUBLIC-1,CP000001.1,gene_1,1,9,1,3,region001,BGC001\n")
    return source, pkg


def test_existing_output_is_refused_and_unchanged(tmp_path):
    source, pkg = _inputs(tmp_path)
    out = tmp_path / "inventory.json"
    out.write_text("earlier inventory\n")
    with pytest.raises(ValueError, match="fresh"):
        _module().export(source, None, pkg, "PUBLIC-1", out)
    assert out.read_text() == "earlier inventory\n"


def test_new_output_records_coverage_hold_and_leaves_no_temp(tmp_path):
    source, pkg = _inputs(tmp_path)
    out = tmp_path / "inventory.json"
    _module().export(source, None, pkg, "PUBLIC-1", out)
    data = json.loads(out.read_text())
    assert data["coverage_check"] == {
        "package_cds_reconciled": True,
        "contigs_with_translated_cds": 1,
        "whole_assembly_contig_coverage": "NOT_VERIFIED_NO_INDEPENDENT_CONTIG_ROSTER",
    }
    assert sorted(p.name for p in tmp_path.iterdir()) == ["inventory.json", "pkg", "whole.gbk"]
