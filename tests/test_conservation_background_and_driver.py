"""v9.7.240: conservation background/saturation + the cohort BLASTp driver's artifact check.

Rank-1 identity against nr measures "has a close relative been sequenced", not "is this cluster
distinctive". On AS-421 (sister species S. saharense in nr) all 36 BGC overlays sit 92-99%, so an
absolute >=90% novelty floor fires 36/36. The background median is the reference the per-BGC value
must be read against."""
import csv, sys, pathlib, importlib.util
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.genome_explore import conservation_background, conservation_saturated

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _overlay(pkg, bgc, ids):
    d = pkg / "blastp_online"; d.mkdir(parents=True, exist_ok=True)
    with (d / f"{bgc}_online_blastp.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["locus_tag", "pct_identity", "query_coverage", "channel", "source_channel"])
        w.writeheader()
        for i, p in enumerate(ids):
            w.writerow({"locus_tag": f"g{i}", "pct_identity": p, "query_coverage": 90,
                        "channel": "nr", "source_channel": "nr"})


def test_background_is_median_across_all_overlays(tmp_path):
    _overlay(tmp_path, "BGC001", [90, 92, 94])
    _overlay(tmp_path, "BGC002", [96, 98, 100])
    bg, n = conservation_background(tmp_path)
    assert n == 6 and bg == 95.0


def test_saturated_when_background_clears_the_floor(tmp_path):
    _overlay(tmp_path, "BGC001", [95, 96, 97])          # near-relative in the DB
    assert conservation_saturated(tmp_path) is True     # per-BGC medians carry no novelty signal
    

def test_not_saturated_on_a_divergent_genome(tmp_path):
    _overlay(tmp_path, "BGC001", [60, 65, 70])
    assert conservation_saturated(tmp_path) is False


def test_background_none_when_no_overlays(tmp_path):
    assert conservation_background(tmp_path) == (None, 0)
    assert conservation_saturated(tmp_path) is False


def test_novelty_message_carries_background_and_saturation_note():
    from mamey.modeb_structure_gate import lint_card
    card = "## §11 Product family\nThis represents a novel scaffold with structural novelty.\n"
    f = lint_card(card, bgc_context={"conservation_median_id": 93.8, "conservation_background_id": 95.4,
                                     "conservation_background_n": 504, "conservation_saturated": True})
    msg = [x for x in f if x.get("code") == "NOVELTY_CONTRADICTION"][0]["message"]
    assert "background median is 95.4%" in msg and "-1.6 vs its own genome" in msg
    assert "near-relative is in the reference DB" in msg


def test_batch_cap_raised_to_30_default_stays_10():
    from mamey.blastp_online import MAX_BATCH, DEFAULT_BATCH, chunk_proteins
    assert MAX_BATCH == 30 and DEFAULT_BATCH == 10
    prots = [(f"q{i}", "M" * 50) for i in range(878)]
    assert len(chunk_proteins(prots, batch_size=30)) == 30      # matches the real AS-421 run (30 RIDs)


def test_driver_verifies_the_overlay_artifact_not_the_exit_code(tmp_path):
    spec = importlib.util.spec_from_file_location("drv", ROOT / "tools" / "cohort_blastp_driver.py")
    drv = importlib.util.module_from_spec(spec); spec.loader.exec_module(drv)
    ov = drv.overlay_path(tmp_path, "BGC001")
    assert drv.overlay_ok(ov) == (False, "overlay missing")
    _overlay(tmp_path, "BGC001", [95, 96])
    good, why = drv.overlay_ok(ov)
    assert good and "2 genes" in why


def test_chunk_proteins_defaults_to_the_courteous_batch_not_the_ceiling():
    """v9.7.245 (owned regression): .240 raised MAX_BATCH 10 -> 30 and added DEFAULT_BATCH = 10, but
    `chunk_proteins`' default arg stayed `MAX_BATCH`. Every caller that omitted batch_size silently
    tripled its submission size. DEFAULT_BATCH is the default; MAX_BATCH is only the hard clamp."""
    from mamey.blastp_online import chunk_proteins, MAX_BATCH, DEFAULT_BATCH
    prots = [(f"q{i}", "M" * 50) for i in range(60)]
    assert DEFAULT_BATCH == 10 and MAX_BATCH == 30
    assert [len(b) for b in chunk_proteins(prots)] == [10] * 6      # was [30, 30]
    assert [len(b) for b in chunk_proteins(prots, 30)] == [30, 30]  # explicit honored
    assert [len(b) for b in chunk_proteins(prots, 99)] == [30, 30]  # clamped
