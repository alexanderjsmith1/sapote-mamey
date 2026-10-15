"""SubClusterBlast NO_HITS must come from a region's own search, not from another region's hits.

One region carrying SubClusterBlast hits used to turn every other region's empty list into NO_HITS
on the triage board. Here one region gets hits; the others must stay blank (not established).
"""
import csv

import mamey.cli as cli


def test_one_region_with_hits_does_not_mark_others_no_hits(tmp_path, monkeypatch,
                                                           synthetic_single_contig_full_locus_zip):
    real_write_package = cli._write_package
    seen = {}

    def write_with_one_region_hit(run, package_dir, *args, **kwargs):
        first = sorted(run.bgcs, key=lambda b: b.bgc_id)[0]
        first.subcluster_hits = [{"ref": "SYNREF1", "rank": 1, "nprot": 3, "mean_identity": 55.0}]
        seen["hit_bgc"] = first.bgc_id
        seen["n_bgcs"] = len(run.bgcs)
        return real_write_package(run, package_dir, *args, **kwargs)

    monkeypatch.setattr(cli, "_write_package", write_with_one_region_hit)
    strain_id = "SYNSCB1"
    cli.run_one_strain(
        strain_id=strain_id, display_name=strain_id,
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path), mode="full",
        taxonomy="", source="", bioactivity="", master_path=None, json_mode="off",
    )
    assert seen.get("n_bgcs", 0) >= 2, "fixture needs at least two regions"
    board = tmp_path / strain_id / "package" / f"{strain_id}_4_triage_board.csv"
    with board.open(newline="", encoding="utf-8") as fh:
        rows = {r["BGC_ID"]: r["SubCluster_hits"] for r in csv.DictReader(fh)}
    assert rows[seen["hit_bgc"]] == "SYNREF1(55.0)"
    others = {bid: cell for bid, cell in rows.items() if bid != seen["hit_bgc"]}
    assert others and all(cell == "" for cell in others.values()), others
