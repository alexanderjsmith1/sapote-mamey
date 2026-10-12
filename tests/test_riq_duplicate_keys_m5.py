"""Raw-JSON known-answer ambiguity controls; no biological sequences or tools."""
import importlib
import io
import json
import zipfile

import pytest
from mamey import antismash_evidence as ae

CONTIG = "SYNTHETIC_FULL_CONTIG.1"
MODULE = "antismash.modules.cluster_compare"


@pytest.fixture(autouse=True, params=["selected", "python"])
def backend(request, monkeypatch):
    assert ae._HAVE_IJSON
    if request.param == "python":
        monkeypatch.setattr(ae, "ijson", importlib.import_module("ijson.backends.python"))


def obj(*pairs):
    return "{" + ",".join(json.dumps(k) + ":" + v for k, v in pairs) + "}"


def document(duplicate=None, *, same=False):
    # Raw JSON intentionally preserves duplicate keys: dict/json.dumps cannot.
    def field(role, key, low, high):
        if role == duplicate:
            return [(key, low), (key, low if same else high.replace(":0.2", ":0.9"))]
        return [(key, low)]
    def branch(score):
        scores = obj(*field("reference", "reference.accession.1", str(score), "0.9"))
        variant = obj(*field("scores", "scores_by_region", scores, scores))
        variants = obj(*field("variant", "RegionToRegion_RiQ", variant, variant))
        regions = obj(*field("region", "1", variants, variants))
        result = obj(*field("by_region", "by_region", regions, regions))
        databases = obj(*field("database", "database.name.1", result, result))
        module = obj(*field("module_record_id", "record_id", json.dumps(CONTIG), json.dumps("OTHER_FULL_CONTIG.1")),
                     *field("db_results", "db_results", databases, databases))
        modules = obj(*field("module", MODULE, module, module))
        return obj(*field("record_id", "id", json.dumps(CONTIG), json.dumps("OTHER_FULL_CONTIG.1")),
                   *field("modules", "modules", modules, modules))
    record = branch(0.2)
    return obj(*field("version", "version", '"8.0.4"', '"8.0.3"'),
               *field("schema", "schema", "4", "3"),
               *field("records", "records", "[" + record + "]", "[" + branch(0.9) + "]"))


def parse(raw):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("synthetic.json", raw)
    stream.seek(0)
    evidence = {"by_region": {}, "loose_hits": [], "json_files": ["synthetic.json"],
                "json_mode": "bounded", "json_mode_requested": "bounded"}
    with zipfile.ZipFile(stream) as archive:
        ae._parse_json_bounded(archive, "synthetic.json", evidence)
    return evidence


def maxima(evidence):
    return {key: max(row["riq_score"] for row in rows if "riq_score" in row)
            for key, rows in evidence["by_region"].items()}


@pytest.mark.parametrize("role", ["records", "version", "schema", "record_id", "modules",
    "module", "module_record_id", "db_results", "database", "by_region", "region",
    "variant", "scores", "reference"])
@pytest.mark.parametrize("same", [False, True])
def test_duplicate_authority_or_channel_never_assigns_score(role, same):
    ev = parse(document(role, same=same))
    receipt = ev["json_bounded_walks"][0]
    assert receipt["walk_complete"]
    assert maxima(ev) == {}
    assert receipt["riq_observations_mapped"] == receipt["riq_mapped_maxima"] == 0
    assert receipt["riq_authority_status"] == "HOLD"
    assert receipt["riq_authority_holds"] == ["DUPLICATE_AUTHORITY_OR_CHANNEL_KEY"]
    assert receipt["riq_authority_duplicate_events"] >= 1
    assert not receipt["riq_authority_tracking_exhausted"]
    assert ev["riq_mapping_status"] == "UNMAPPED_SOURCE_AUTHORITY_HOLD"


def test_late_duplicate_root_cannot_retain_earlier_closed_record_maximum():
    raw = document()
    raw = raw[:-1] + ',"records":[]}'
    ev = parse(raw)
    assert maxima(ev) == {}
    receipt = ev["json_bounded_walks"][0]
    assert receipt["records_closed"] == 1
    assert receipt["riq_observations_seen"] == receipt["riq_observations_unassigned"] == 1
    assert receipt["riq_observations_mapped"] == 0


def test_unambiguous_dotted_reference_and_database_are_preserved():
    ev = parse(document())
    assert maxima(ev) == {CONTIG + "_c1": 0.2}
    receipt = ev["json_bounded_walks"][0]
    assert receipt["riq_authority_status"] == "CHECKED_WITHIN_CAP"
    assert receipt["riq_authority_duplicate_events"] == 0
    assert receipt["riq_authority_holds"] == []
    assert receipt["riq_observations_seen"] == receipt["riq_observations_mapped"] == 1


@pytest.mark.parametrize("extra", [
    '"unrelated":{"scores_by_region":{"reference":0.8,"reference":0.9}}',
    '"ProtoToRegion_RiQ":{"scores_by_region":{"reference":0.8,"reference":0.9}}',
    '"db_results.database.by_region.1.RegionToRegion_RiQ.scores_by_region":{"reference":0.8,"reference":0.9}',
])
def test_unrelated_proto_or_flattened_duplicate_keys_cannot_hold_or_inflate_channel(extra):
    # Insert at the region variants object, beside the admitted named variant.
    raw = document().replace('"RegionToRegion_RiQ":', extra + ',"RegionToRegion_RiQ":', 1)
    ev = parse(raw)
    assert maxima(ev) == {CONTIG + "_c1": 0.2}
    assert ev["json_bounded_walks"][0]["riq_authority_status"] == "CHECKED_WITHIN_CAP"


def test_reference_tracking_count_exhaustion_is_explicit_and_bounded(monkeypatch):
    monkeypatch.setattr(ae, "BOUNDED_MAX_RIQ_AUTHORITY_KEYS", 24)
    refs = obj(*[("reference" + str(i), "0.9") for i in range(100)])
    raw = document().replace('{"reference.accession.1":0.2}', refs)
    ev = parse(raw)
    receipt = ev["json_bounded_walks"][0]
    assert maxima(ev) == {}
    assert receipt["walk_complete"] and receipt["riq_observations_seen"] == 100
    assert receipt["riq_authority_tracking_exhausted"]
    assert receipt["riq_authority_keys_peak"] <= 24
    assert receipt["riq_authority_holds"] == ["AUTHORITY_KEY_TRACKING_CAP_EXCEEDED"]
    assert ev["json_bounded_truncated"] is True


def test_reference_tracking_character_exhaustion_does_not_retain_huge_key(monkeypatch):
    monkeypatch.setattr(ae, "BOUNDED_MAX_RIQ_AUTHORITY_KEY_CHARS", 256)
    raw = document().replace('reference.accession.1', 'x' * 10000)
    ev = parse(raw)
    receipt = ev["json_bounded_walks"][0]
    assert maxima(ev) == {}
    assert receipt["riq_authority_tracking_exhausted"]
    assert receipt["riq_authority_key_chars_peak"] <= 256
    assert receipt["riq_authority_holds"] == ["AUTHORITY_KEY_TRACKING_CAP_EXCEEDED"]


def test_tracking_budget_releases_closed_reference_maps(monkeypatch):
    monkeypatch.setattr(ae, "BOUNDED_MAX_RIQ_AUTHORITY_KEYS", 24)
    raw_record = json.loads(document())["records"][0]
    # Distinct physical records, same reference/database keys: per-map identity.
    records = []
    for index in range(30):
        record = json.loads(json.dumps(raw_record))
        record["id"] = "SYNTHETIC_FULL_CONTIG_%d.1" % index
        record["modules"][MODULE]["record_id"] = record["id"]
        records.append(record)
    ev = parse(json.dumps({"version": "8.0.4", "schema": 4, "records": records}))
    receipt = ev["json_bounded_walks"][0]
    assert len(maxima(ev)) == 30
    assert receipt["riq_observations_mapped"] == 30
    assert receipt["riq_authority_status"] == "CHECKED_WITHIN_CAP"
    assert receipt["riq_authority_keys_peak"] <= 24


def test_ambiguous_member_does_not_remove_preexisting_other_source_evidence():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("synthetic.json", document("reference"))
    stream.seek(0)
    old = {"source": "other.json", "riq_score": 0.4}
    evidence = {"by_region": {CONTIG + "_c1": [old]}, "loose_hits": []}
    with zipfile.ZipFile(stream) as archive:
        ae._parse_json_bounded(archive, "synthetic.json", evidence)
    row = evidence["by_region"][CONTIG + "_c1"][0]
    assert row["riq_score"] == 0.4
    assert row["riq_source_observations"] == [{"source": "other.json", "riq_score": 0.4}]
    assert row["riq_sources"] == ["other.json"]
    assert len(evidence["by_region"][CONTIG + "_c1"]) == 1
    assert evidence["json_bounded_walks"][0]["riq_observations_mapped"] == 0
