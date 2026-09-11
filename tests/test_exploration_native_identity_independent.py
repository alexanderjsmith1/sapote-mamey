"""Independent native producer display compatibility; database keys stay unchanged."""
from dataclasses import asdict
import copy
import json
from types import SimpleNamespace
import pytest
from mamey.crosswalk import enrich_bgc_crosswalk
from mamey.models import BGCRecord
from mamey import genome_explore as ge
from mamey.exact_identity import ExactLocusIdentityError, exact_locus_from_mapping

def install(tmp_path, monkeypatch, data):
    row = data["bgcs"][0]
    root = tmp_path / f"SYNTHETIC-001__{row['contig']}__region001__BGC001"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(data))
    def observation(pkg, man, alias):
        return {"median_id": 60, "n_genes": 1, "multispecies_hits": 0,
                "source": "nr", "status": "ADMITTED", "invalid_source": None,
                "identities": [60]}
    monkeypatch.setattr(ge, "_conservation_observation", observation)
    monkeypatch.setattr(ge, "_gene_context", lambda pkg: {"BGC001": [{"locus_tag": "synthetic_gene", "product": "transposase"}]})
    return root


STRAIN = "SYNTHETIC-001"
CONTIGS = ["NODE_1_length_1000_cov_1.5", "ctg10_extra_suffix", "scaffold_42_segment_A", "CP123456.1"]

def native(contig=CONTIGS[0], alias="BGC001"):
    record = BGCRecord(bgc_id=alias, contig=contig, region_number=1,
                       start=1, end=1000, contig_length=1000, products=["synthetic class"])
    enrich_bgc_crosswalk(record, "unused.region001.gbk")
    return asdict(record)

def run(root, as_json, monkeypatch):
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    assert ge.explore_command(SimpleNamespace(package=str(root), top=8, json=as_json)) == 0
    assert len(emitted) == 1
    return emitted[0]

@pytest.mark.parametrize("contig", CONTIGS)
@pytest.mark.parametrize("as_json", [False, True])
def test_native_full_contig_display_preserves_producer_fields(tmp_path, monkeypatch, contig, as_json):
    row = native(contig)
    original = copy.deepcopy(row)
    data = {"strain_id": STRAIN, "bgcs": [row]}
    root = install(tmp_path, monkeypatch, data)
    before = (root / "manifest.json").read_bytes()
    output = run(root, as_json, monkeypatch)
    expected = f"{STRAIN} / {contig} / region001 / BGC001"
    if as_json:
        payload = json.loads(output)
        for section in ("exploration_board", "divergence", "co_capture"):
            assert payload[section]
            assert all(item["exact_locus"] == expected for item in payload[section])
    else:
        assert expected in output
    assert row == original
    assert (root / "manifest.json").read_bytes() == before

@pytest.mark.parametrize("as_json", [False, True])
def test_normalized_key_collision_keeps_distinct_full_contigs(tmp_path, monkeypatch, as_json):
    rows = [native("NODE_1_length_1000_cov_1.5"), native("NODE_1_length_1000_cov_1.9", "BGC002")]
    assert rows[0]["node_id"] == rows[1]["node_id"]
    root = install(tmp_path, monkeypatch, {"strain_id": STRAIN, "bgcs": rows})
    output = run(root, as_json, monkeypatch)
    for row in rows:
        assert f"{STRAIN} / {row['contig']} / region001 / {row['bgc_id']}" in output

@pytest.mark.parametrize("field,value", [
    ("node_id", "NODE_9_length_1000_cov_1"),
    ("Full_Node_ID", "NODE_9_length_1000_cov_1.5"),
    ("Contig", "NODE_9_length_1000_cov_1.5"),
    ("region", "region002"),
    ("strain_id", "SYNTHETIC-999"),
])
@pytest.mark.parametrize("as_json", [False, True])
def test_native_adapter_must_not_hide_real_conflicts(tmp_path, monkeypatch, field, value, as_json):
    row = native(); row[field] = value
    root = install(tmp_path, monkeypatch, {"strain_id": STRAIN, "bgcs": [row]})
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)):
        ge.explore_command(SimpleNamespace(package=str(root), top=8, json=as_json))
    assert emitted == []

def test_generic_synonym_owner_stays_strict_for_normalized_values():
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_mapping(STRAIN, native())

@pytest.mark.parametrize("case", ["empty_node", "null_node", "missing_contig", "missing_native_region", "filename_fallback", "broad_cov_equivalence"])
@pytest.mark.parametrize("as_json", [False, True])
def test_explicit_native_contract_never_silently_downgrades(tmp_path, monkeypatch, case, as_json):
    row = native()
    if case == "empty_node": row["node_id"] = ""
    elif case == "null_node": row["node_id"] = None
    elif case == "missing_contig": row.pop("contig")
    elif case == "missing_native_region":
        row.pop("antismash_region"); row["region"] = "region001"
    elif case == "filename_fallback":
        row["contig"] = "CP123456.1"
        row["source_gbk"] = "NODE_1_length_1000_cov_1.region001.gbk"
    elif case == "broad_cov_equivalence": row["node_id"] = "NODE_1_length_1000_cov_99"
    # The directory carries the complete known fixture identity even for damaged input.
    root = tmp_path / "SYNTHETIC-001__NODE_1_length_1000_cov_1.5__region001__BGC001"
    root.mkdir(); (root / "manifest.json").write_text(json.dumps({"strain_id": STRAIN, "bgcs": [row]}))
    emitted = []; monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)):
        ge.explore_command(SimpleNamespace(package=str(root), top=0, json=as_json))
    assert emitted == []

@pytest.mark.parametrize("as_json", [False, True])
def test_duplicate_physical_locus_under_distinct_aliases_refuses(tmp_path, monkeypatch, as_json):
    rows = [native("CP123456.1"), native("CP123456.1", "BGC002")]
    root = install(tmp_path, monkeypatch, {"strain_id": STRAIN, "bgcs": rows})
    emitted = []; monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)):
        ge.explore_command(SimpleNamespace(package=str(root), top=0, json=as_json))
    assert emitted == []

def test_database_normalized_key_exact_missing_and_ambiguous_states_are_preserved():
    import sqlite3
    from mamey.bgc_l0_program import _exact_region
    row = native()
    assert row["node_id"] == "NODE_1_length_1000_cov_1"
    assert row["contig"] == "NODE_1_length_1000_cov_1.5"
    db = sqlite3.connect(":memory:"); db.row_factory = sqlite3.Row
    try:
        db.executescript("""
        CREATE TABLE regions(region_key TEXT,strain TEXT,assembly_sha256 TEXT,node_id TEXT);
        CREATE TABLE sources(source_id TEXT,archive_sha256 TEXT,antismash_version TEXT);
        CREATE TABLE region_calls(region_key TEXT,source_id TEXT,profile TEXT,region_id TEXT,products_json TEXT,contig_edge TEXT);
        INSERT INTO sources VALUES('source','synthetic_archive_hash','8.0.4');
        """)
        db.execute("INSERT INTO regions VALUES(?,?,?,?)", ("r1", STRAIN, "synthetic_assembly_hash", row["node_id"]))
        db.execute("INSERT INTO region_calls VALUES(?,?,?,?,?,?)", ("r1", "source", "relaxed", "region001", "[]", "False"))
        found,status = _exact_region(db, strain=STRAIN, node=row["node_id"], region_id="region001", profile="relaxed")
        assert status == "EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND" and found["region_key"] == "r1"
        found,status = _exact_region(db, strain=STRAIN, node=row["contig"], region_id="region001", profile="relaxed")
        assert found is None and status == "SOURCE_LOCATOR_BOUND_EXACT_REGION_JOIN_MISSING"
        db.execute("INSERT INTO regions VALUES(?,?,?,?)", ("r2", STRAIN, "another_synthetic_assembly_hash", row["node_id"]))
        db.execute("INSERT INTO region_calls VALUES(?,?,?,?,?,?)", ("r2", "source", "relaxed", "region001", "[]", "False"))
        found,status = _exact_region(db, strain=STRAIN, node=row["node_id"], region_id="region001", profile="relaxed")
        assert found is None and status == "SOURCE_LOCATOR_AMBIGUOUS_2_EXACT_REGION_CANDIDATES"
    finally:
        db.close()
