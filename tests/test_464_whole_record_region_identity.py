"""Without region GBKs, a whole record's BGC takes its boundary and number from its one region feature."""
import io
import zipfile

from mamey import parsers

SEQ = "acgt" * 250  # 1,000 bp


def _record(name, features=""):
    lines = ["".join(SEQ[i:i + 60]) for i in range(0, len(SEQ), 60)]
    origin = "\n".join(f"{i * 60 + 1:>9} {l}" for i, l in enumerate(lines))
    return (f"LOCUS       {name:<16} {len(SEQ)} bp    DNA     linear   UNK 01-JAN-2026\n"
            f"DEFINITION  synthetic.\nACCESSION   {name}\nVERSION     {name}\n"
            f"FEATURES             Location/Qualifiers\n{features}ORIGIN\n{origin}\n//\n")


def _feature(kind, span, product, region_number=None):
    text = f'     {kind:<16}{span}\n                     /product="{product}"\n'
    if region_number is not None:
        text += f'                     /region_number="{region_number}"\n'
    return text


REGION4 = _feature("region", "101..900", "NRPS", 4)
NESTED = _feature("protocluster", "201..500", "NRPS")


def _zip(tmp_path, text, member="genome.gbk"):
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(member, text)
    return z


def _parse(tmp_path, text, member="genome.gbk"):
    return parsers.parse_bgcs_from_zip(_zip(tmp_path, text, member), json_mode="off")


def _hold_codes(tmp_path, text, member="genome.gbk"):
    diagnostics = []
    list(parsers.iter_region_core_inputs(_zip(tmp_path, text, member), intake_diagnostics=diagnostics))
    return [d["code"] for d in diagnostics if d["code"].startswith("WHOLE_RECORD_")]


def test_region_number_comes_from_the_region_feature(tmp_path):
    bgcs = _parse(tmp_path, _record("ctgA", REGION4))
    assert [(b.contig, b.region_number, b.antismash_region) for b in bgcs] == [("ctgA", 4, "region004")]


def test_nested_protocluster_does_not_replace_the_region_boundary(tmp_path):
    bgcs = _parse(tmp_path, _record("ctgA", REGION4 + NESTED))
    assert [(b.start, b.end, b.region_number) for b in bgcs] == [(101, 900, 4)]


def test_protoclusters_without_a_region_are_held(tmp_path):
    text = _record("ctgA", _feature("protocluster", "101..400", "NRPS")
                   + _feature("protocluster", "601..900", "terpene"))
    assert _parse(tmp_path, text) == []
    assert _hold_codes(tmp_path, text) == ["WHOLE_RECORD_REGION_FEATURE_MISSING_HELD"]


def test_region_without_a_region_number_is_held(tmp_path):
    text = _record("ctgA", _feature("region", "101..900", "NRPS"))
    assert _parse(tmp_path, text) == []
    assert _hold_codes(tmp_path, text) == ["WHOLE_RECORD_REGION_NUMBER_MISSING_HELD"]


def test_well_formed_biopython_record_keeps_region_identity_and_bounds(tmp_path):
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    from Bio import SeqIO
    rec = SeqRecord(Seq(SEQ.upper()), id="ctgA", name="ctgA", description="synthetic",
                    annotations={"molecule_type": "DNA", "topology": "linear"})
    rec.features = [
        SeqFeature(FeatureLocation(100, 900), type="region",
                   qualifiers={"product": ["NRPS"], "region_number": ["4"]}),
        SeqFeature(FeatureLocation(200, 500), type="protocluster", qualifiers={"product": ["NRPS"]}),
    ]
    buf = io.StringIO()
    SeqIO.write(rec, buf, "genbank")
    bgcs = _parse(tmp_path, buf.getvalue())
    assert [(b.contig, b.region_number, b.start, b.end) for b in bgcs] == [("ctgA", 4, 101, 900)]


def _inspect(tmp_path, text, capsys):
    from types import SimpleNamespace
    from mamey import package_inspector
    rc = package_inspector.inspect_command(SimpleNamespace(zip=str(_zip(tmp_path, text))))
    return rc, capsys.readouterr().out


def test_inspect_admits_what_run_admits(tmp_path, capsys):
    rc, out = _inspect(tmp_path, _record("ctgA", REGION4 + NESTED), capsys)
    assert rc == 0
    assert "Whole records     : 1 admitted" in out


def test_inspect_refuses_and_names_held_whole_records(tmp_path, capsys):
    text = _record("ctgA", _feature("protocluster", "101..400", "NRPS")
                   + _feature("protocluster", "601..900", "terpene"))
    rc, out = _inspect(tmp_path, text, capsys)
    assert rc == 1
    assert "WHOLE_RECORD_REGION_FEATURE_MISSING_HELD" in out
