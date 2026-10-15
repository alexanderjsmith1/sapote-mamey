"""In-run locus maps: a failed v8 map is reported for that figure, never replaced by the legacy
renderer, and the map manifest lists only this run's maps (no stale files from a glob)."""
import csv

import mamey.cli as cli
import mamey.locus_map as locus_map
import mamey.locus_map_v8 as locus_map_v8

STRAIN = "SYNLM1"


def _run(tmp_path, zip_path):
    lm_dir = tmp_path / STRAIN / "package" / "locus_maps"
    lm_dir.mkdir(parents=True)
    (lm_dir / "STALE_NODE_9_locus.png").write_bytes(b"stale")  # left by an earlier run
    res = cli.run_one_strain(
        strain_id=STRAIN, display_name=STRAIN, input_zip=str(zip_path), outdir=str(tmp_path),
        mode="full", taxonomy="", source="", bioactivity="", master_path=None, json_mode="off",
        locus_maps="on",
    )
    with (lm_dir / "locus_map_manifest.csv").open(newline="", encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    return res, manifest


def test_v8_failure_is_reported_and_legacy_is_not_substituted(tmp_path, monkeypatch,
                                                               synthetic_single_contig_full_locus_zip):
    legacy_titles = []

    def v8_fails(*args, **kwargs):
        raise RuntimeError("synthetic v8 failure")

    def legacy_spy(panels, *args, **kwargs):
        legacy_titles.append(kwargs.get("suptitle", ""))

    monkeypatch.setattr(locus_map_v8, "render_bgc_v8", v8_fails)
    monkeypatch.setattr(locus_map, "render_locus_map", legacy_spy)
    res, manifest = _run(tmp_path, synthetic_single_contig_full_locus_zip)
    assert not [t for t in legacy_titles if "pair" not in t], legacy_titles
    failed = [i for i in res.get("issues", []) if i.startswith("LOCUS_MAP_V8_FAILED:")]
    assert failed and all("synthetic v8 failure" in i for i in failed)
    assert all(row["kind"] == "pair" for row in manifest)
    assert "STALE_NODE_9_locus.png" not in {row["filename"] for row in manifest}


def test_v8_success_manifest_lists_this_runs_maps_only(tmp_path, monkeypatch,
                                                       synthetic_single_contig_full_locus_zip):
    rendered = []

    def v8_writes(package_dir, bgc_id, *, out_dir, **kwargs):
        (out_dir / f"{bgc_id}_locus_map.png").write_bytes(b"png")
        (out_dir / f"{bgc_id}_locus_map_data.csv").write_text("locus_tag\n", encoding="utf-8")
        rendered.append((bgc_id, kwargs.get("node", "")))
        return {}

    monkeypatch.setattr(locus_map_v8, "render_bgc_v8", v8_writes)
    res, manifest = _run(tmp_path, synthetic_single_contig_full_locus_zip)
    assert rendered
    singles = {row["filename"]: row["data_csv"] for row in manifest if row["kind"] == "single"}
    assert singles == {f"{b}_{n}_locus.png": f"{b}_{n}_locus_data.csv" for b, n in rendered}
    assert "STALE_NODE_9_locus.png" not in {row["filename"] for row in manifest}
    assert not [i for i in res.get("issues", []) if i.startswith("LOCUS_MAP_V8_FAILED:")]
