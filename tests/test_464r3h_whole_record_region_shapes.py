"""Whole-record intake holds a region whose number or boundary would have to be guessed.

Each case is one synthetic record with one antiSMASH region feature. Biopython writes the GenBank text,
so the shapes are legal GenBank; only the annotation is ambiguous.
"""
import io
import zipfile

import pytest

pytest.importorskip("Bio")
from Bio import SeqIO  # noqa: E402
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import AfterPosition, BeforePosition, CompoundLocation, FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402

from mamey import parsers


def _zip(tmp_path, numbers, location, topology="linear"):
    rec = SeqRecord(Seq("ACGT" * 250), id="SYNTH_CONTIG", name="SYNTH_CONTIG", description="synthetic",
                    annotations={"molecule_type": "DNA", "topology": topology})
    rec.features = [SeqFeature(location, type="region",
                               qualifiers={"product": ["terpene"], "region_number": numbers})]
    text = io.StringIO()
    SeqIO.write(rec, text, "genbank")
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("genome.gbk", text.getvalue())
    return z


def _run(z):
    diagnostics = []
    core = list(parsers.iter_region_core_inputs(z, intake_diagnostics=diagnostics))
    return core, parsers.parse_bgcs_from_zip(z, json_mode="off"), [d["code"] for d in diagnostics]


def test_valid_region_keeps_number_and_bounds(tmp_path):
    core, bgcs, codes = _run(_zip(tmp_path, ["4"], FeatureLocation(100, 900)))
    assert len(core) == 1 and len(bgcs) == 1
    assert (bgcs[0].region_number, bgcs[0].start, bgcs[0].end) == (4, 101, 900)
    assert not [c for c in codes if c.startswith("WHOLE_RECORD_")]


def test_repeated_same_number_is_not_a_conflict(tmp_path):
    _, bgcs, _ = _run(_zip(tmp_path, ["4", "4"], FeatureLocation(100, 900)))
    assert [b.region_number for b in bgcs] == [4]


@pytest.mark.parametrize("numbers, location, topology, code", [
    (["0"], FeatureLocation(100, 900), "linear", "WHOLE_RECORD_REGION_NUMBER_INVALID_HELD"),
    (["-1"], FeatureLocation(100, 900), "linear", "WHOLE_RECORD_REGION_NUMBER_INVALID_HELD"),
    (["4", "5"], FeatureLocation(100, 900), "linear", "WHOLE_RECORD_REGION_NUMBER_CONFLICT_HELD"),
    (["4"], FeatureLocation(100, 1100), "linear", "WHOLE_RECORD_REGION_OUTSIDE_RECORD_HELD"),
    (["4"], FeatureLocation(BeforePosition(100), AfterPosition(900)), "linear",
     "WHOLE_RECORD_REGION_FUZZY_BOUNDS_HELD"),
    (["4"], CompoundLocation([FeatureLocation(900, 1000), FeatureLocation(0, 100)]), "circular",
     "WHOLE_RECORD_REGION_COMPOUND_LOCATION_HELD"),
], ids=["zero", "negative", "conflict", "outside_record", "fuzzy", "origin_join"])
def test_ambiguous_region_is_held_not_guessed(tmp_path, numbers, location, topology, code):
    core, bgcs, codes = _run(_zip(tmp_path, numbers, location, topology))
    assert core == [] and bgcs == []
    assert code in codes
