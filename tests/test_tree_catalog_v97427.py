from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tree_catalog


def test_phylo_staging_lowercase_host_column_is_loaded(tmp_path):
    import build_placement_ggtree_inputs as builder
    table = tmp_path / "PHYLO_STRAIN_METADATA.tsv"
    table.write_text(
        "strain\tcohort\thost\tlocation\tgenbank_accession\n"
        "AS-422\thymenoptera\tBombus sp.\tNew Jersey\tPX565017\n"
    )
    assert builder._load_hosts(table)["AS-422"] == {
        "host": "Bombus sp.", "region": "New Jersey", "acc": "PX565017",
        "experiment": "", "sample": "",
    }


def _touch_inputs(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    for name in ("hosts.tsv", "roster.tsv", "refs.sqlite", "required.tsv"):
        (tmp_path / name).write_text("fixture\n")
    return run


def test_plan_expands_ratio_and_geography_matrix(tmp_path):
    run = _touch_inputs(tmp_path)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": tree_catalog.SCHEMA,
        "defaults": {"views": ["publication", "publication-detailed", "publication-noloc"],
                     "reference_ratios": [1, 2, 3]},
        "trees": [{"id": "bee_streptomyces", "run_dir": str(run),
                   "group": "Streptomyces", "cohort_scope": ["bee"],
                   "taxonomic_scope": "Streptomyces", "reference_panel": "type_only",
                   "host_table": str(tmp_path / "hosts.tsv"),
                   "ref_source_db": str(tmp_path / "refs.sqlite"),
                   "required_reference_table": str(tmp_path / "required.tsv"),
                   "genus_roster": str(tmp_path / "roster.tsv")}]}))
    plan = tree_catalog.write_plan(catalog, tmp_path / "plan.json")
    assert plan["job_count"] == 9
    assert {job["job_id"] for job in plan["jobs"]} == {
        f"bee_streptomyces_r{ratio}_{suffix}"
        for ratio in (1, 2, 3) for suffix in ("concise", "detailed", "nogeo")
    }
    assert all(job["required_reference_table"].endswith("required.tsv") for job in plan["jobs"])


def test_spotlight_is_recorded_but_not_silently_pruned_at_render(tmp_path):
    run = _touch_inputs(tmp_path)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": tree_catalog.SCHEMA,
        "trees": [{"id": "rare_spotlight", "run_dir": str(run),
                   "group": "Kribbella", "cohort_scope": ["bee"],
                   "taxonomic_scope": "Kribbella", "reference_panel": "type_only",
                   "host_table": str(tmp_path / "hosts.tsv"),
                   "ref_source_db": str(tmp_path / "refs.sqlite"),
                   "spotlight_queries": ["AS-123"]}]}))
    _source, _data, jobs = tree_catalog.load_catalog(catalog)
    assert jobs[0]["spotlight_queries"] == ["AS-123"]
    with pytest.raises(ValueError, match="SPOTLIGHT_REQUIRES_DECLARED_QUERY_SUBSET_RUN"):
        tree_catalog.render(catalog, tmp_path / "rendered")


def test_catalog_refuses_undeclared_reference_panel(tmp_path):
    run = _touch_inputs(tmp_path)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": tree_catalog.SCHEMA,
        "trees": [{"id": "bad", "run_dir": str(run), "group": "Streptomyces",
                   "cohort_scope": ["bee"], "taxonomic_scope": "Streptomyces",
                   "reference_panel": "whatever_is_available",
                   "host_table": str(tmp_path / "hosts.tsv"),
                   "ref_source_db": str(tmp_path / "refs.sqlite")}]}))
    with pytest.raises(ValueError, match="REFERENCE_PANEL"):
        tree_catalog.load_catalog(catalog)


def test_small_genus_catalog_supports_four_references_per_query(tmp_path):
    run = _touch_inputs(tmp_path)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": tree_catalog.SCHEMA,
        "defaults": {"views": ["publication"], "reference_ratios": [1, 2, 3, 4]},
        "trees": [{"id": "bee_rare_genus", "run_dir": str(run),
                   "group": "Actinomadura", "cohort_scope": ["bee"],
                   "taxonomic_scope": "Actinomadura", "reference_panel": "type_only",
                   "host_table": str(tmp_path / "hosts.tsv"),
                   "ref_source_db": str(tmp_path / "refs.sqlite")}]}))
    _source, _data, jobs = tree_catalog.load_catalog(catalog)
    assert [job["reference_ratio"] for job in jobs] == [1, 2, 3, 4]


def test_catalog_refuses_ratio_above_four(tmp_path):
    run = _touch_inputs(tmp_path)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": tree_catalog.SCHEMA,
        "trees": [{"id": "too_many", "run_dir": str(run),
                   "group": "Kribbella", "cohort_scope": ["bee"],
                   "taxonomic_scope": "Kribbella", "reference_panel": "type_only",
                   "reference_ratios": [5],
                   "host_table": str(tmp_path / "hosts.tsv"),
                   "ref_source_db": str(tmp_path / "refs.sqlite")}]}))
    with pytest.raises(ValueError, match="TREE_CATALOG_RATIO"):
        tree_catalog.load_catalog(catalog)
