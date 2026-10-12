"""Common intake contracts specified from raw metadata, without scoring or homology.

The public subset expectations below are transcribed from VERSION, Orig. bounds,
and region product qualifiers, not from either reader's output. Synthetic records
exercise source admission/order/geometry; they do not represent biological truth.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest
from mamey import parsers

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "packaging/rggmci/build_rggmci_package.py"
PUBLIC = ROOT / "tests/fixtures/rggmci_public_VWPH00000000.1_subset.zip"


def feature(kind="region", start=10, end=30, **qualifiers):
    return NS(type=kind, location=NS(start=start, end=end), qualifiers=qualifiers)


def record(contig="CP000001.1", *, description="", topology="linear", features=None, length=100):
    return NS(id=contig, name=contig, description=description,
              annotations={"topology": topology}, features=features or [], seq="N" * length)


def bind(monkeypatch, entries, *, bounds=None, lengths=None, fallback=False):
    calls = []
    monkeypatch.setattr(parsers, "validate_region_intake_resources", lambda path: None)

    def read(path, region_only=False):
        calls.append(region_only)
        return [] if fallback and region_only else list(entries)

    monkeypatch.setattr(parsers, "read_genbank_records", read)
    monkeypatch.setattr(parsers, "_region_orig_bounds_from_zip", lambda path: bounds or {})
    monkeypatch.setattr(parsers, "_contig_length_map_from_zip", lambda path: lengths or {})
    return calls


def core(**kwargs):
    return [fields for _, _, fields, _ in parsers.iter_region_core_inputs("synthetic.zip", **kwargs)]


def test_absolute_bounds_full_identity_and_source_order(monkeypatch):
    p = record("CP000002.3", description="plasmid", features=[feature(product=["z", "a"])])
    c = record("CP000001.2", description="chromosome", features=[feature(product=["x"])])
    entries = [("a.region001.gbk", p), ("z.region001.gbk", c)]
    bind(monkeypatch, entries, bounds={"a.region001.gbk": (0, 20), "z.region001.gbk": (6000, 8000)},
         lengths={p.id: 20000, c.id: 20000})
    got = core()
    assert got == [
        dict(bgc_id="BGC001", contig="CP000001.2", region_number=1, start=6000, end=8000,
             contig_length=20000, products=["x"], edge_status="Interior", source_gbk="z.region001.gbk", subcluster_hits=[]),
        dict(bgc_id="BGC002", contig="CP000002.3", region_number=1, start=0, end=20,
             contig_length=20000, products=["a", "z"], edge_status="Edge", source_gbk="a.region001.gbk", subcluster_hits=[]),
    ]


def test_dedup_keeps_first_source_and_metadata_timing(monkeypatch):
    r = record(features=[feature(product=["x"])])
    bind(monkeypatch, [("b.region001.gbk", r), ("a.region001.gbk", r),
                       ("c.region001.gbk", record("CP000002.1", features=r.features))])
    visited = []
    got = core(embedded_metadata=lambda rec: visited.append(rec.id))
    assert visited == ["CP000001.1", "CP000001.1", "CP000002.1"]
    assert [(x["bgc_id"], x["source_gbk"], x["contig"]) for x in got] == [
        ("BGC001", "a.region001.gbk", "CP000001.1"), ("BGC002", "c.region001.gbk", "CP000002.1")]


def test_region_only_length_remains_unknown_and_local_bounds_are_preserved(monkeypatch):
    bind(monkeypatch, [("x.region004.gbk", record(features=[feature(start=4, end=20)]))])
    got = core()[0]
    assert (got["region_number"], got["start"], got["end"], got["contig_length"], got["edge_status"]) == (4, 5, 20, 0, "Unknown")


@pytest.mark.parametrize("physical,parsed", [
    ("NODE_1_length_20000_cov_55.054054", "NODE_1_length_20000_cov_55.54054"),
    ("NODE_1_length_20000_cov_55.1", "NODE_1_length_20000_cov_55.1"),
])
def test_full_node_locus_survives_version_normalization(monkeypatch, physical, parsed):
    r = record(parsed, features=[feature(start=6000, end=8000)])
    r.name = physical
    bind(monkeypatch, [("x.region002.gbk", r)], lengths={physical: 20000})
    got = core()[0]
    assert (got["contig"], got["contig_length"], got["edge_status"]) == (physical, 20000, "Interior")


def test_full_record_fallback_and_fallback_region_number(monkeypatch):
    calls = bind(monkeypatch, [("whole.gbk", record(features=[feature(start=4, end=20)]))], fallback=True)
    got = core()[0]
    assert calls == [True, False]
    assert (got["region_number"], got["start"], got["end"], got["contig_length"], got["edge_status"]) == (1, 5, 20, 100, "Edge")


def test_empty_intake_keeps_zero_denominator(monkeypatch):
    calls = bind(monkeypatch, [])
    assert core() == []
    assert calls == [True, False]


@pytest.mark.parametrize("topology,bounds,expected", [
    ("linear", (1, 100), "Edge"), ("circular", (1, 100), "Interior"),
    ("circular", (1, 19999), "Full-contig"), ("UNK", (6000, 8000), "Interior"),
])
def test_topology_and_full_contig_precedence(monkeypatch, topology, bounds, expected):
    bind(monkeypatch, [("x.region001.gbk", record(topology=topology))],
         bounds={"x.region001.gbk": bounds}, lengths={"CP000001.1": 20000})
    assert core()[0]["edge_status"] == expected


def test_product_fallback_caps_first_three_cds_and_sorts_unique(monkeypatch):
    fs = [feature("CDS", product=["z;a"]), feature("CDS", category=["b"]),
          feature("CDS", product=["a"]), feature("CDS", product=["not_admitted"])]
    bind(monkeypatch, [("x.region001.gbk", record(features=fs))])
    assert core()[0]["products"] == ["a", "b", "z"]


class BadInteger:
    def __init__(self, exc):
        self.exc = exc

    def __int__(self):
        raise self.exc


@pytest.mark.parametrize("exc", [TypeError("typed"), ValueError("value"), AttributeError("attribute")])
@pytest.mark.parametrize("embedded", [False, True])
def test_structural_coordinate_failure_preserves_partial_assignment(monkeypatch, exc, embedded):
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(start=4, end=BadInteger(exc))]))],
         lengths={"CP000001.1": 100})
    diagnostics = []
    kwargs = {"embedded_coordinate_diagnostic": lambda err, name: diagnostics.append((err, name))} if embedded else {}
    got = core(**kwargs)[0]
    assert (got["start"], got["end"]) == (5, 100)
    assert diagnostics == ([(exc, "x.region001.gbk")] if embedded else [])


def test_unexpected_coordinate_error_default_propagates(monkeypatch):
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(end=BadInteger(RuntimeError("unexpected")))]))])
    with pytest.raises(RuntimeError, match="unexpected"):
        core()


def test_embedded_unexpected_coordinate_error_propagates_without_degradation(monkeypatch):
    exc = RuntimeError("unexpected")
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(end=BadInteger(exc))]))])
    diagnostics = []
    with pytest.raises(RuntimeError, match="unexpected"):
        core(embedded_coordinate_diagnostic=lambda err, name: diagnostics.append((err, name)))
    assert diagnostics == []


@pytest.mark.parametrize("exc", [ValueError("expected"), RuntimeError("unexpected"),
                                 parsers.GbkSizeGuardRefusal("synthetic.gbk", "typed refusal")])
def test_actual_embedded_coordinate_callback_has_common_admission_and_breadcrumb(monkeypatch, exc):
    from mamey import degradation
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(end=BadInteger(exc))]))])
    degradation.drain()
    if type(exc) is ValueError:
        got = parsers.parse_bgcs_from_zip("synthetic.zip", evidence={})
        assert len(got) == 1
        events = degradation.drain()
        assert len(events) == 1 and events[0]["site"] == "parsers.parse_bgcs_from_zip.region_coords_fallback"
        assert events[0]["record"] == "x.region001.gbk"
    else:
        with pytest.raises(type(exc)):
            parsers.parse_bgcs_from_zip("synthetic.zip", evidence={})
        assert degradation.drain() == []


@pytest.mark.parametrize("embedded", [False, True])
def test_typed_resource_refusal_never_becomes_coordinate_fallback(monkeypatch, embedded):
    exc = parsers.GbkSizeGuardRefusal("synthetic.gbk", "synthetic resource refusal")
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(end=BadInteger(exc))]))])
    diagnostics = []
    kwargs = {"embedded_coordinate_diagnostic": lambda *args: diagnostics.append(args)} if embedded else {}
    with pytest.raises(parsers.GbkSizeGuardRefusal, match="synthetic resource refusal"):
        core(**kwargs)
    assert diagnostics == []


def test_member_reader_refusal_propagates_before_any_callback(monkeypatch):
    exc = parsers.GbkSizeGuardRefusal("synthetic.gbk", "reader refusal")
    bind(monkeypatch, [])
    def refused(*args, **kwargs):
        raise exc
    monkeypatch.setattr(parsers, "read_genbank_records", refused)
    with pytest.raises(parsers.GbkSizeGuardRefusal, match="reader refusal"):
        core(embedded_coordinate_diagnostic=lambda *args: pytest.fail("refusal was swallowed"))


def test_embedded_route_uses_common_projection_and_retains_notes(monkeypatch):
    bind(monkeypatch, [("x.region007.gbk", record(features=[feature(product=["test_class"])]))],
         bounds={"x.region007.gbk": (10, 30)})
    got = parsers.parse_bgcs_from_zip("synthetic.zip", evidence={})
    assert parsers.project_rggmci_records(got) == core()
    assert got[0].antismash_region == "region007"
    assert "absolute_coordinates_from_antismash_orig_start_end" in got[0].notes


def test_projection_copies_nested_mutable_fields(monkeypatch):
    bind(monkeypatch, [("x.region001.gbk", record(features=[feature(product=["x"])]))])
    fields = core()[0]
    fields["subcluster_hits"] = [{"nested": ["source"]}]
    r = NS(**fields)
    got = parsers.project_rggmci_records([r])
    got[0]["products"].append("changed")
    got[0]["subcluster_hits"][0]["nested"].append("changed")
    assert r.products == ["x"] and r.subcluster_hits == [{"nested": ["source"]}]


@pytest.fixture(scope="module")
def shared_package(tmp_path_factory):
    out = tmp_path_factory.mktemp("shared_region_package") / "pkg"
    run = subprocess.run([sys.executable, str(BUILD), "--bundle", str(ROOT), "--out", str(out)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    return out


# Independently transcribed source metadata, preserving the existing Orig. start convention.
PUBLIC_METADATA = [
    ("VWPH01000001.1", 3, 440169, 478259, ["saccharide", "terpene-precursor"]),
    ("VWPH01000004.1", 3, 365138, 450313, ["NRPS", "NRPS-like", "betalactone"]),
    ("VWPH01000008.1", 1, 0, 19338, ["terpene-precursor"]),
    ("VWPH01000010.1", 3, 150126, 269085, ["NRPS", "NRPS-like", "saccharide"]),
    ("VWPH01000014.1", 1, 188436, 239466, ["NRP-metallophore", "NRPS"]),
]


@pytest.mark.parametrize("without_bio", [False, True])
def test_generated_reader_public_full_projection_matches_known_source_metadata(shared_package, tmp_path, without_bio):
    expected = []
    for i, (contig, region, start, end, products) in enumerate(PUBLIC_METADATA, 1):
        expected.append(dict(bgc_id=f"BGC{i:03d}", contig=contig, region_number=region,
                             start=start, end=end, contig_length=0, products=products,
                             edge_status="Unknown", source_gbk=f"{contig}.region{region:03d}.gbk", subcluster_hits=[]))
    embedded = parsers.project_rggmci_records(parsers.parse_bgcs_from_zip(PUBLIC, evidence={}))
    assert embedded == expected
    script = """
import json, sys
if sys.argv[2] == 'True':
    sys.modules['Bio'] = None
from rggmci.reader import read_regions, project_rggmci_records
records = project_rggmci_records(read_regions(sys.argv[1]))
assert not any(x == 'mamey' or x.startswith('mamey.') for x in sys.modules)
print(json.dumps(records, sort_keys=True))
"""
    env = dict(os.environ, PYTHONPATH=str(shared_package / "src"), PYTHONDONTWRITEBYTECODE="1")
    run = subprocess.run([sys.executable, "-c", script, str(PUBLIC), str(without_bio)],
                         cwd=tmp_path, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout) == expected
