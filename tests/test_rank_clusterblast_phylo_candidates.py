import csv
import importlib.util
import json
import pathlib
import sys
import zipfile

import pytest


TOOL = pathlib.Path(__file__).parents[1] / "tools" / "rank_clusterblast_phylo_candidates.py"
SPEC = importlib.util.spec_from_file_location("rank_clusterblast_phylo_candidates", TOOL)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def block(rank, ref, source, q="q1", s="s1", ident=70, coverage=90, score=100):
    return (
        f"\n>>\n{rank}. {ref}\nSource: {source}\nType: NRPS\n"
        "Number of proteins with BLAST hits to this cluster: 1\n"
        f"Cumulative BLAST score: {score}.0\n\n"
        "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
        f"{q}\t{s}\t{ident}\t{score}\t{coverage}\t1e-20\n"
    )


def write_inputs(tmp_path):
    zpath = tmp_path / "AS-1.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("input/AS-1.fna", ">a\nAAAACCCC\n>b\nGGGGTTTT\n")
        zf.writestr("clusterblast/ctgA_c1.txt",
                    "ClusterBlast scores for ctgA\n" +
                    block(1, "NZ_REF1", "Organism one", "q1", "s1", 80, 95, 200) +
                    block(2, "NZ_REF2", "Organism one alias", "q2", "s2", 70, 85, 150) +
                    block(3, "NZ_HOLD", "Unresolved organism", "q3", "s3", 60, 75, 120))
        zf.writestr("clusterblast/ctgB_c1.txt",
                    "ClusterBlast scores for ctgB\n" +
                    block(1, "NZ_REF1", "Organism one", "q4", "s4", 75, 90, 180))
        zf.writestr("knownclusterblast/ctgA_c1.txt",
                    "KnownClusterBlast\n" + block(1, "BGC0000001", "named compound"))
        zf.writestr("subclusterblast/ctgA_c1.txt",
                    "SubClusterBlast\n" + block(1, "SUB001", "subcluster"))
    inventory = tmp_path / "inventory.csv"
    inventory.write_text("BGC_ID,Contig,Region\nBGC001,ctgA,1\nBGC002,ctgB,1\n")
    legacy = tmp_path / "clusterblast.csv"
    legacy.write_text("bgc_id,query_gene,reference,pct_identity,pct_coverage\nBGC001,q1,NZ_REF1,80,95\n")
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "strain_id\tcohort\tantismash_zip\tassembly_member\tbgc_inventory_csv\tmamey_clusterblast_csv\n"
        f"AS-1\tAS\t{zpath}\tinput/AS-1.fna\t{inventory}\t{legacy}\n"
    )
    resolver = tmp_path / "resolver.tsv"
    resolver.write_text(
        "reference_accession\tassembly_accession\torganism_label\tresolution_evidence\n"
        "NZ_REF1\tGCF_000000001.1\tOrganism one\tcurator accession crosswalk\n"
        "NZ_REF2\tGCF_000000001.1\tOrganism one\tcurator accession crosswalk\n"
    )
    return manifest, resolver, zpath


def read_tsv(path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_complete_assembly_member_provenance(tmp_path):
    manifest, _, _ = write_inputs(tmp_path)
    source = mod.read_manifest(manifest)[0]
    row = mod.assembly_provenance(source)
    assert row["assembly_member"] == "input/AS-1.fna"
    assert row["assembly_records"] == 2
    assert row["assembly_total_bp"] == 16
    assert len(row["antismash_zip_sha256"]) == 64
    assert len(row["assembly_member_sha256"]) == 64
    assert len(row["assembly_content_sha256"]) == 64


def test_relative_manifest_paths_are_resolved_from_manifest_directory(tmp_path):
    manifest, _, _ = write_inputs(tmp_path)
    rows = list(csv.DictReader(manifest.open(), delimiter="\t"))
    for key in ("antismash_zip", "bgc_inventory_csv", "mamey_clusterblast_csv"):
        rows[0][key] = pathlib.Path(rows[0][key]).name
    relative = tmp_path / "relative.tsv"
    with relative.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    source = mod.read_manifest(relative)[0]
    assert source.antismash_zip == (tmp_path / pathlib.Path(rows[0]["antismash_zip"])).resolve()


def test_channels_are_separate_and_only_raw_clusterblast_is_ranked(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    receipt = mod.build(manifest, tmp_path / "out", resolver, 5)
    channels = read_tsv(tmp_path / "out/channel_inventory.tsv")
    counts = {r["channel"]: int(r["txt_members"]) for r in channels}
    assert counts["clusterblast"] == 2
    assert counts["knownclusterblast"] == 1
    assert counts["subclusterblast"] == 1
    assert counts["mibig"] == counts["nr"] == 0
    genes = read_tsv(tmp_path / "out/clusterblast_gene_hits.tsv")
    assert genes and {r["channel"] for r in genes} == {"clusterblast"}
    assert "BGC0000001" not in {r["reference_accession"] for r in genes}
    assert receipt["channel_policy"]["knownclusterblast"] == "NOT USED; kept separate"


def test_distinct_bgcs_raise_priority_but_repeated_genes_do_not(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    mod.build(manifest, tmp_path / "out", resolver, 5)
    candidates = read_tsv(tmp_path / "out/clusterblast_phylo_candidates.tsv")
    resolved = next(r for r in candidates if r["assembly_accession"] == "GCF_000000001.1")
    assert resolved["evidence_rank"] == "1"
    assert resolved["n_distinct_query_bgcs"] == "2"
    assert resolved["n_bgc_child_rows"] == "2"
    assert int(resolved["total_gene_hit_rows"]) == 3
    assert resolved["n_reference_accessions_collapsed"] == "2"


def test_collapsed_accessions_preserve_one_child_per_exact_strain_bgc(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    mod.build(manifest, tmp_path / "out", resolver, 5)
    children = read_tsv(tmp_path / "out/clusterblast_bgc_children.tsv")
    resolved = [r for r in children if r["assembly_accession"] == "GCF_000000001.1"]
    assert {(r["strain_id"], r["bgc_id"]) for r in resolved} == {
        ("AS-1", "BGC001"), ("AS-1", "BGC002")
    }
    bgc1 = next(r for r in resolved if r["bgc_id"] == "BGC001")
    assert bgc1["n_reference_accessions_collapsed"] == "2"
    assert bgc1["support_unit"] == "ONE_DISTINCT_QUERY_BGC"


def test_unresolved_nucleotide_accession_is_hold_request(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    mod.build(manifest, tmp_path / "out", resolver, 5)
    holds = read_tsv(tmp_path / "out/assembly_accession_holds.tsv")
    assert len(holds) == 1
    assert holds[0]["candidate_key"] == "UNRESOLVED:NZ_HOLD"
    assert holds[0]["selection_status"] == "HOLD_REQUEST_ASSEMBLY_ACCESSION"
    assert holds[0]["resolved_pool_top20"] == "NO"


def test_user_visible_candidate_pools_are_20_40_60_and_resolved_only(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    receipt = mod.build(manifest, tmp_path / "out", resolver, 5)
    assert receipt["panel_total_tip_options"] == [20, 40, 60]
    candidates = read_tsv(tmp_path / "out/clusterblast_phylo_candidates.tsv")
    resolved = next(r for r in candidates if r["assembly_accession"])
    assert resolved["resolved_candidate_rank"] == "1"
    assert [resolved[f"resolved_pool_top{x}"] for x in (20, 40, 60)] == ["YES", "YES", "YES"]
    assert "not final total-tip trees" in receipt["candidate_pool_note"]


def test_legacy_mamey_export_without_channel_is_audit_only(tmp_path):
    manifest, resolver, _ = write_inputs(tmp_path)
    mod.build(manifest, tmp_path / "out", resolver, 5)
    audit = read_tsv(tmp_path / "out/legacy_mamey_export_audit.tsv")[0]
    assert audit["channel_column_present"] == "False"
    assert audit["use"] == "AUDIT_ONLY_CHANNEL_COLLAPSED_NOT_RANKED"


def test_no_network_or_tree_runner_code_path():
    text = TOOL.read_text()
    assert "import subprocess" not in text
    assert "requests" not in text
    assert "urllib" not in text
    assert "datasets download" not in text
    assert "subprocess.run" not in text
