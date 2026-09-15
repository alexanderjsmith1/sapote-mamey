"""TREES_432_reference_metadata_resolver_ignores_biosample — the resolver consults the record's own
linked BioSample after the nuccore SOURCE feature, records provenance per value, keeps INSDC
null values verbatim, and gates the BioSample strain. No network: _http_get is routed to fixtures."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import resolve_reference_metadata as m  # noqa: E402

# --- fixtures shaped like the two 2026-09-14 cases in the card -------------------------------
GB_DENDRANTHEMAE = (  # NZ_VIWX01000001.1 / SAMN12024781: SOURCE carries nothing, BioSample says 'missing'
    "LOCUS       NZ_VIWX01000001   1 bp    DNA     linear   CON\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..100\n"
    '                     /organism="Saccharopolyspora dendranthemae"\n'
    '                     /strain="DSM 46699"\n'
    '                     /db_xref="BioSample:SAMN12024781"\n'
    "     gene            1..1000\n"
)
BS_DENDRANTHEMAE = """<?xml version="1.0"?>
<BioSampleSet><BioSample accession="SAMN12024781" id="12024781">
 <Ids><Id db="BioSample" is_primary="1">SAMN12024781</Id></Ids>
 <Attributes>
  <Attribute attribute_name="strain" harmonized_name="strain">DSM 46699</Attribute>
  <Attribute attribute_name="isolation source" harmonized_name="isolation_source">missing</Attribute>
  <Attribute attribute_name="geo_loc_name" harmonized_name="geo_loc_name">missing</Attribute>
  <Attribute attribute_name="type-material" harmonized_name="type-material">type strain of Saccharopolyspora dendranthemae</Attribute>
 </Attributes>
</BioSample></BioSampleSet>"""

GB_CRANIELLAE = (  # NZ_CP061725.1: SOURCE has values; BioSample adds lat_lon and type-material
    "LOCUS       NZ_CP061725   1 bp    DNA     linear   CON\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..100\n"
    '                     /organism="Micromonospora craniellae"\n'
    '                     /strain="LHW63014"\n'
    '                     /db_xref="BioSample:SAMN16176545"\n'
    '                     /isolation_source="ENVO: 01000161"\n'
    '                     /host="Sponge"\n'
    '                     /geo_loc_name="China:South China Sea"\n'
    "     gene            1..1000\n"
)
BS_CRANIELLAE = """<BioSampleSet><BioSample accession="SAMN16176545">
 <Attributes>
  <Attribute harmonized_name="strain">LHW63014</Attribute>
  <Attribute harmonized_name="isolation_source">ENVO: 01000161</Attribute>
  <Attribute harmonized_name="geo_loc_name">China:South China Sea</Attribute>
  <Attribute harmonized_name="lat_lon">16.75 N 112.35 E</Attribute>
  <Attribute harmonized_name="type-material">type strain of Micromonospora craniellae</Attribute>
 </Attributes>
</BioSample></BioSampleSet>"""

GB_NO_XREF = GB_DENDRANTHEMAE.replace('                     /db_xref="BioSample:SAMN12024781"\n', "")
ELINK_JSON = '{"linksets":[{"dbfrom":"nuccore","linksetdbs":[{"dbto":"biosample","linkname":"nuccore_biosample","links":["12024781"]}]}]}'
ELINK_EMPTY = '{"linksets":[{"dbfrom":"nuccore","ids":["1"]}]}'


def _route(monkeypatch, table):
    """Route _http_get by URL substring; refuse anything unrouted (proves no live network)."""
    calls = []

    def fake(url, timeout=30):
        calls.append(url)
        for key, body in table.items():
            if key in url:
                return body
        raise AssertionError(f"unrouted URL in test: {url}")
    monkeypatch.setattr(m, "_http_get", fake)
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    return calls


def test_parse_source_reads_biosample_xref():
    assert m.parse_source(GB_DENDRANTHEMAE)["biosample"] == "SAMN12024781"
    assert m.parse_source(GB_NO_XREF)["biosample"] == ""


def test_parse_biosample_attributes_verbatim():
    bs = m.parse_biosample(BS_DENDRANTHEMAE)
    assert bs["accession"] == "SAMN12024781"
    assert bs["isolation_source"] == "missing" and bs["geo_loc_name"] == "missing"
    assert bs["type_material"] == "type strain of Saccharopolyspora dendranthemae"
    assert bs["strain"] == "DSM 46699"
    assert m.parse_biosample("<BioSampleSet/>") == {}
    with pytest.raises(RuntimeError, match="2 samples"):
        m.parse_biosample(BS_DENDRANTHEMAE.replace("</BioSample></BioSampleSet>",
                                                    "</BioSample><BioSample accession='X'/></BioSampleSet>"))


def test_checked_null_is_distinct_from_unchecked(monkeypatch):
    _route(monkeypatch, {"db=nuccore": GB_DENDRANTHEMAE, "db=biosample": BS_DENDRANTHEMAE})
    r = m.resolve("NZ_VIWX01000001.1", expected_strain="DSM 46699")
    assert r["status"] == "STRAIN_CONFIRMED_NULL_DECLARED"
    assert r["isolation_source"] == "missing"          # verbatim, never binned to 'Not recorded'
    assert r["country"] == "missing"
    assert r["isolation_source_provenance"] == "biosample:SAMN12024781:isolation_source"
    assert r["location_provenance"] == "biosample:SAMN12024781:geo_loc_name"
    assert r["checked_biosample"] == "SAMN12024781"
    assert r["type_material"] == "type strain of Saccharopolyspora dendranthemae"


def test_nuccore_values_win_and_carry_nuccore_provenance(monkeypatch):
    _route(monkeypatch, {"db=nuccore": GB_CRANIELLAE, "db=biosample": BS_CRANIELLAE})
    r = m.resolve("NZ_CP061725.1", expected_strain="LHW63014")
    assert r["status"] == "STRAIN_CONFIRMED"
    assert r["isolation_source"] == "ENVO: 01000161"
    assert r["isolation_source_provenance"] == "nuccore:/isolation_source"
    assert r["location_provenance"] == "nuccore:/country|/geo_loc_name"
    assert r["checked_biosample"] == "SAMN16176545"
    assert r["type_material"] == "type strain of Micromonospora craniellae"


def test_elink_used_when_source_has_no_xref(monkeypatch):
    calls = _route(monkeypatch, {"efetch.fcgi?db=nuccore": GB_NO_XREF, "elink.fcgi": ELINK_JSON,
                                 "db=biosample": BS_DENDRANTHEMAE})
    r = m.resolve("NZ_VIWX01000001.1", expected_strain="DSM 46699")
    assert any("elink.fcgi" in c for c in calls)
    assert any("db=biosample&id=12024781" in c for c in calls)
    assert r["checked_biosample"] == "SAMN12024781"


def test_no_linked_biosample_is_unchecked_not_recorded(monkeypatch):
    _route(monkeypatch, {"efetch.fcgi?db=nuccore": GB_NO_XREF, "elink.fcgi": ELINK_EMPTY})
    r = m.resolve("NZ_VIWX01000001.1", expected_strain="DSM 46699")
    assert r["status"] == "STRAIN_CONFIRMED_NO_METADATA"
    assert r["isolation_source"] == "Not recorded"
    assert r["checked_biosample"] == ""
    assert "no BioSample linked" in r["unresolved"]


def test_biosample_strain_gate_refuses_other_strain(monkeypatch):
    other = BS_DENDRANTHEMAE.replace(">DSM 46699<", ">DSM 99999<").replace(">missing<", ">soil<")
    _route(monkeypatch, {"db=nuccore": GB_DENDRANTHEMAE, "db=biosample": other})
    r = m.resolve("NZ_VIWX01000001.1", expected_strain="DSM 46699")
    assert r["isolation_source"] == "Not recorded" and r["type_material"] == ""
    assert "BIOSAMPLE_STRAIN_MISMATCH" in r["unresolved"]
    assert r["status"] == "STRAIN_CONFIRMED_NO_METADATA"


def test_no_biosample_flag_keeps_legacy_path(monkeypatch):
    calls = _route(monkeypatch, {"db=nuccore": GB_DENDRANTHEMAE})
    r = m.resolve("NZ_VIWX01000001.1", expected_strain="DSM 46699", use_biosample=False)
    assert r["status"] == "STRAIN_CONFIRMED_NO_METADATA" and r["checked_biosample"] == ""
    assert all("biosample" not in c for c in calls)


def test_output_columns_are_additive_and_carry_provenance(monkeypatch, tmp_path):
    _route(monkeypatch, {"db=nuccore": GB_DENDRANTHEMAE, "db=biosample": BS_DENDRANTHEMAE})
    out = tmp_path / "t.tsv"
    assert m.main(["--accessions", "NZ_VIWX01000001.1", "--out", str(out)]) == 0
    head, row = out.read_text().splitlines()[:2]
    cols = head.split("\t")
    assert cols[:10] == ["identifier", "exact_accession", "isolation_source", "host", "location",
                         "geography", "evidence_url", "strain_match_basis", "verification_status",
                         "unresolved_issue"]
    assert cols[10:] == ["isolation_source_provenance", "location_provenance", "checked_biosample",
                         "type_material"]
    d = dict(zip(cols, row.split("\t")))
    assert d["checked_biosample"] == "SAMN12024781" and d["isolation_source"] == "missing"
