"""Independent presentation tests use producer-shaped identity, not lookup aliases."""
import copy
import json
from types import SimpleNamespace
import pytest
from mamey import genome_explore as ge
from mamey.exact_identity import ExactLocusIdentityError, exact_locus_from_mapping

KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
IDENTITIES = {
    "BGC001": "SYNTHETIC-001 / NODE_1_length_1000_cov_1 / region001 / BGC001",
    "BGC002": "SYNTHETIC-001 / NODE_2_length_1000_cov_1 / region002 / BGC002",
}

def manifest():
    return {"strain_id": "SYNTHETIC-001", "bgcs": [
        {"bgc_id": alias, "contig": f"NODE_{i}_length_1000_cov_1", "antismash_region": f"region00{i}",
         "region_number": i, "products": ["synthetic class"], "ab_score": 80, "af_score": 20}
        for i, alias in enumerate(IDENTITIES, 1)]}

def install(tmp_path, monkeypatch, data=None):
    root = tmp_path / KEY
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(data if data is not None else manifest()))
    # Controlled numeric evidence isolates the presentation bridge while retaining real
    # scan, board, renderer and command code. File admission is tested in other modules.
    def observation(pkg, man, alias):
        return {"median_id": 60 if alias == "BGC001" else 65, "n_genes": 1,
                "multispecies_hits": 0, "source": "nr" if alias == "BGC001" else "clusterblast",
                "status": "ADMITTED", "invalid_source": None, "identities": [60]}
    monkeypatch.setattr(ge, "_conservation_observation", observation)
    monkeypatch.setattr(ge, "_gene_context", lambda pkg: {"BGC001": [{"locus_tag": "synthetic_gene", "product": "transposase"}]})
    return root


def test_all_four_human_sections_display_complete_identity(tmp_path, monkeypatch):
    root = install(tmp_path, monkeypatch)
    text = ge.render_explore(root)
    assert text.count(IDENTITIES["BGC001"]) >= 3  # top, confirmed, co-capture
    assert text.count(IDENTITIES["BGC002"]) >= 2  # top, unconfirmed
    import re
    for line in text.splitlines():
        if re.search(r"BGC[0-9]+", line):
            assert any(identity in line for identity in IDENTITIES.values()), line


def test_json_public_rows_carry_the_same_complete_identity(tmp_path, monkeypatch):
    root = install(tmp_path, monkeypatch)
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    assert ge.explore_command(SimpleNamespace(package=str(root), top=8, json=True)) == 0
    assert len(emitted) == 1
    payload = json.loads(emitted[0])
    for section in ("exploration_board", "divergence", "co_capture"):
        assert payload[section]
        for row in payload[section]:
            assert row.get("exact_locus") == IDENTITIES[row["bgc_id"]]


def damage(data, kind):
    row = data["bgcs"][0]
    if kind == "strain": data.pop("strain_id")
    elif kind == "contig": row.pop("contig")
    elif kind == "short_contig": row["contig"] = "NODE_1"
    elif kind == "region": row.pop("antismash_region")
    elif kind == "malformed_region": row["antismash_region"] = "region1"
    elif kind == "alias": row.pop("bgc_id")
    elif kind == "node_conflict": row["node_id"] = "NODE_9_length_1000_cov_1"
    elif kind == "region_conflict": row["region"] = "region009"
    elif kind == "alias_conflict": row["bgc_alias"] = "BGC009"
    elif kind == "strain_conflict": row["strain_id"] = "SYNTHETIC-999"
    elif kind == "duplicate_alias": data["bgcs"].append(copy.deepcopy(row))
    elif kind == "late_bad_record": data["bgcs"].append({"contig": "NODE_3_length_1000_cov_1", "antismash_region": "region003"})

@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("kind", ["strain", "contig", "short_contig", "region", "malformed_region", "alias",
                                  "node_conflict", "region_conflict", "alias_conflict", "strain_conflict",
                                  "duplicate_alias", "late_bad_record"])
def test_invalid_identity_aborts_before_any_public_emit(tmp_path, monkeypatch, kind, as_json):
    data = manifest()
    damage(data, kind)
    root = install(tmp_path, monkeypatch, data)
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)) as refusal:
        ge.explore_command(SimpleNamespace(package=str(root), top=8, json=as_json))
    assert emitted == []
    if kind == "duplicate_alias" and "BGC001" in str(refusal.value):
        assert IDENTITIES["BGC001"] in str(refusal.value)
    if isinstance(refusal.value, SystemExit):
        assert refusal.value.code not in (None, 0)


def test_owner_accepts_current_producer_region_spelling():
    row = manifest()["bgcs"][0]
    assert exact_locus_from_mapping("SYNTHETIC-001", row) == IDENTITIES["BGC001"]


def test_owner_keeps_region_synonym_conflict_guard():
    row = manifest()["bgcs"][0]
    row["region"] = "region002"
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_mapping("SYNTHETIC-001", row)


def test_low_level_numeric_contract_does_not_require_presentation_identity(tmp_path, monkeypatch):
    data = manifest()
    data["bgcs"][0]["bgc_alias"] = "different lookup alias"
    root = install(tmp_path, monkeypatch, data)
    rows = ge.scan_divergence(root)
    assert rows[0]["median_id"] == 60
    assert rows[0]["divergence_tier"] == "DIVERGENT"


@pytest.mark.parametrize("as_json", [False, True])
def test_real_cli_identity_refusal_is_nonzero_without_output_or_traceback(tmp_path, as_json):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = tmp_path / KEY
    root.mkdir()
    data = manifest()
    data["bgcs"][1].pop("antismash_region")
    (root / "manifest.json").write_text(json.dumps(data))
    code_root = Path(ge.__file__).resolve().parent.parent
    command = [sys.executable, str(code_root / "mamey_run.py"), "explore", str(root)]
    if as_json:
        command.append("--json")
    result = subprocess.run(command, cwd=code_root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, text=True, capture_output=True)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "identity" in result.stderr.lower()
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("as_json", [False, True])
def test_top_cap_cannot_hide_invalid_raw_identity(tmp_path, monkeypatch, as_json):
    data = manifest()
    data["bgcs"][1]["contig"] = "NODE_2"
    root = install(tmp_path, monkeypatch, data)
    def conserved(pkg, man, alias):
        return {"median_id": 99, "n_genes": 1, "multispecies_hits": 0, "source": "nr",
                "status": "ADMITTED", "invalid_source": None, "identities": [99]}
    monkeypatch.setattr(ge, "_conservation_observation", conserved)
    monkeypatch.setattr(ge, "_gene_context", lambda pkg: {})
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)) as refusal:
        ge.explore_command(SimpleNamespace(package=str(root), top=0, json=as_json))
    assert emitted == []
    if isinstance(refusal.value, SystemExit):
        assert refusal.value.code not in (None, 0)


@pytest.mark.parametrize("as_json", [False, True])
def test_unadmitted_scan_row_refuses_without_alias_fallback_label(tmp_path, monkeypatch, as_json):
    root = install(tmp_path, monkeypatch)
    monkeypatch.setattr(ge, "_gene_context", lambda pkg: {"UNADMITTED_ALIAS": [{"locus_tag": "synthetic_gene", "product": "transposase"}]})
    emitted = []
    monkeypatch.setattr(ge, "emit", emitted.append)
    with pytest.raises((ExactLocusIdentityError, SystemExit)) as refusal:
        ge.explore_command(SimpleNamespace(package=str(root), top=8, json=as_json))
    assert emitted == []
    assert "UNADMITTED_ALIAS" not in str(refusal.value)
    if isinstance(refusal.value, SystemExit):
        assert refusal.value.code not in (None, 0)
