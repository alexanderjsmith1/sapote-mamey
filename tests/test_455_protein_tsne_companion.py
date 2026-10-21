"""t-SNE companion layout for a protein PCoA kit: synthetic identity tables only, no biological computation."""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("sklearn")
pytest.importorskip("scipy")

ROOT = Path(os.environ.get("N5_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location("tsne_companion_owner", ROOT / "tools/protein_pcoa_ordinate.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
from tools import protein_pcoa_render as render  # noqa: E402

SET = "SYN"


def synthetic_kit(tmp_path, retain=True):
    """Three groups of 30 synthetic ids: 90% identity within a group, 30% between neighbouring groups."""
    kit = tmp_path / "kit"
    out = kit / f"out_{SET}"
    out.mkdir(parents=True)
    ids = [f"SYN-{g}-{k:02d}" for g in "ABC" for k in range(30)]
    rows = ["id\tPC1\tPC2\tPC3"] + [f"{i}\t0\t0\t0" for i in ids]
    (out / f"PCOA_{SET}.tsv").write_text("\n".join(rows) + "\n")
    lines = []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            if a.split("-")[1] == b.split("-")[1]:
                lines.append(f"{a}\t{b}\t90")
            elif {a.split("-")[1], b.split("-")[1]} == {"A", "B"}:
                lines.append(f"{a}\t{b}\t30")
    hits = tmp_path / "hits.tsv"
    hits.write_text("\n".join(lines) + "\n")
    run = {"set": SET, "points": len(ids)}
    if retain:
        run["retained_allvsall"] = owner._retain_allvsall(hits, out / "allvsall.tsv.gz", ids)
    (out / f"RUN_{SET}.json").write_text(json.dumps(run))
    return kit, ids, hits


def fit(kit, *extra):
    return owner.main(["tsne", "--kit", str(kit), "--set", SET, "--threads", "1", *extra])


def test_fit_writes_render_table_and_bound_sidecar(tmp_path):
    kit, ids, _ = synthetic_kit(tmp_path)
    assert fit(kit) == 0
    out = kit / f"out_{SET}"
    table, sidecar = out / f"TSNE_{SET}.tsv", out / f"TSNE_{SET}.json"
    rows = owner.read_tsv(table)
    assert [r["id"] for r in rows] == ids and set(rows[0]) == {"id", "TSNE1", "TSNE2"}
    rec = json.loads(sidecar.read_text())
    assert rec["coordinates_sha256"] == hashlib.sha256(table.read_bytes()).hexdigest()
    assert rec["tsne"]["seed"] == owner.TSNE_SEED and rec["tsne"]["parameters"]["perplexity"] == owner.TSNE_PERPLEXITY
    assert rec["input"]["binding"] == "RUN_RETAINED_ALLVSALL"
    assert 0.0 <= rec["scores"]["trustworthiness"] <= 1.0 and -1.0 <= rec["scores"]["spearman_global"] <= 1.0
    meta = render.embedding_meta(table, ["pcoa", "tsne"])
    assert meta["state"] == "SUPPLIED_COORDINATE_BOUND"
    assert meta["by_layout"]["tsne"]["seed"] == owner.TSNE_SEED
    assert meta["by_layout"]["tsne"]["version"].startswith("scikit-learn ")


def test_same_seed_gives_identical_coordinates(tmp_path):
    kit, _, _ = synthetic_kit(tmp_path)
    assert fit(kit, "--out-dir", str(tmp_path / "one")) == 0
    assert fit(kit, "--out-dir", str(tmp_path / "two")) == 0
    assert (tmp_path / "one" / f"TSNE_{SET}.tsv").read_bytes() == (tmp_path / "two" / f"TSNE_{SET}.tsv").read_bytes()


def test_groups_stay_together(tmp_path):
    kit, ids, _ = synthetic_kit(tmp_path)
    assert fit(kit) == 0
    rec = json.loads((kit / f"out_{SET}" / f"TSNE_{SET}.json").read_text())
    assert rec["scores"]["trustworthiness"] > 0.9


def test_existing_outputs_are_refused(tmp_path):
    kit, _, _ = synthetic_kit(tmp_path)
    assert fit(kit) == 0
    assert fit(kit) == 2


def test_changed_retained_table_is_refused(tmp_path):
    kit, _, _ = synthetic_kit(tmp_path)
    gz = kit / f"out_{SET}" / "allvsall.tsv.gz"
    gz.write_bytes(gzip.compress(gzip.decompress(gz.read_bytes()) + b"SYN-A-00\tSYN-C-00\t99\n"))
    assert fit(kit) == 2
    assert not (kit / f"out_{SET}" / f"TSNE_{SET}.tsv").exists()


def test_no_retained_table_needs_explicit_input(tmp_path):
    kit, _, hits = synthetic_kit(tmp_path, retain=False)
    assert fit(kit) == 2
    assert fit(kit, "--allvsall", str(hits)) == 0
    rec = json.loads((kit / f"out_{SET}" / f"TSNE_{SET}.json").read_text())
    assert rec["input"]["binding"] == "SUPPLIED_NOT_BOUND_BY_RUN"


def test_perplexity_must_be_below_point_count(tmp_path):
    kit, _, _ = synthetic_kit(tmp_path)
    assert fit(kit, "--perplexity", "500") == 2


def test_memory_estimate_refuses_before_allocation(tmp_path):
    kit, _, _ = synthetic_kit(tmp_path)
    assert fit(kit, "--rss-limit-bytes", "1000") == 2
    assert not (kit / f"out_{SET}" / f"TSNE_{SET}.tsv").exists()
