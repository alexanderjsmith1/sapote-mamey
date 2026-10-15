"""Synthetic numeric tables and fake executable; no biological computation."""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(os.environ.get("N5_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location("n5_distance_owner", ROOT / "tools/protein_pcoa_ordinate.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


def test_factored_distance_matches_original_definition_and_gzip(tmp_path):
    ids = ["SYN-A", "SYN-B", "SYN-C", "SYN-D"]
    raw = "SYN-A\tSYN-B\t20\nSYN-B\tSYN-A\t80\nSYN-A\tSYN-B\t40\nSYN-C\tSYN-C\t50\n"
    plain = tmp_path / "hits.tsv"
    plain.write_text(raw)
    zipped = tmp_path / "hits.tsv.gz"
    with gzip.open(zipped, "wt") as out:
        out.write(raw)
    expected = np.ones((4, 4), dtype=np.float32)
    idx = {identifier: k for k, identifier in enumerate(ids)}
    for line in raw.splitlines():
        q, s, p = line.split("\t")
        i, j, d = idx[q], idx[s], 1 - float(p) / 100
        if d < expected[i, j]:
            expected[i, j] = expected[j, i] = d
    np.fill_diagonal(expected, 0)
    for path in (plain, zipped):
        observed = owner.distance_matrix(path, ids)
        np.testing.assert_array_equal(observed, expected)
        assert observed.dtype == np.float32
        assert observed[0, 3] == 1 and observed[2, 2] == 0


def test_duplicate_matrix_order_refuses(tmp_path):
    path = tmp_path / "empty.tsv"
    path.write_text("")
    with pytest.raises(owner.OrdinateRefusal, match="unique"):
        owner.distance_matrix(path, ["SYN-A", "SYN-A"])


def test_unknown_hit_id_is_not_silently_dropped(tmp_path):
    path = tmp_path / "hits.tsv"
    path.write_text("SYN-A\tSYN-OUTSIDE\t20\n")
    with pytest.raises(KeyError):
        owner.distance_matrix(path, ["SYN-A", "SYN-B"])


def test_retention_gzip_is_deterministic_and_binds_input(tmp_path):
    source = tmp_path / "hits.tsv"
    source.write_text("SYN-A\tSYN-B\t42\n")
    one, two = tmp_path / "one.gz", tmp_path / "two.gz"
    first = owner._retain_allvsall(source, one, ["SYN-A", "SYN-B"])
    second = owner._retain_allvsall(source, two, ["SYN-A", "SYN-B"])
    assert one.read_bytes() == two.read_bytes()
    assert gzip.decompress(one.read_bytes()) == source.read_bytes()
    assert first["sha256"] == second["sha256"] == hashlib.sha256(one.read_bytes()).hexdigest()
    assert first["uncompressed_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert first["id_order_sha256"] == hashlib.sha256(b"SYN-A\nSYN-B\n").hexdigest()


def synthetic_kit(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    ids = [f"SYN-{i}" for i in range(4)]
    (kit / "SYN.faa").write_text("".join(f">{i}\nMAAA\n" for i in ids))
    (kit / "SYN_META.tsv").write_text("id\tsource\n" + "".join(f"{i}\tisolate\n" for i in ids))
    binary = tmp_path / "fake_diamond"
    binary.write_text("#!" + sys.executable + "\n" + '''import sys
from pathlib import Path
args=sys.argv[1:]
if args[0]=='version': print('SYN fake executable'); raise SystemExit(0)
if args[0]=='makedb': Path(args[args.index('-d')+1]+'.dmnd').write_text('SYN dummy'); raise SystemExit(0)
if args[0]=='blastp':
    ids=[line[1:].strip() for line in Path(args[args.index('-q')+1]).read_text().splitlines() if line.startswith('>')]
    Path(args[args.index('-o')+1]).write_text(''.join(q+'\\t'+s+'\\t'+('100' if q==s else '40')+'\\n' for q in ids for s in ids))
    raise SystemExit(0)
raise SystemExit(2)
''')
    binary.chmod(0o700)
    return kit, ids, binary


@pytest.mark.parametrize("keep", [False, True])
def test_worker_promotes_only_requested_hits_with_receipt(tmp_path, keep, monkeypatch):
    # The outer task test runner watches this process tree. The production nested
    # ps monitor is denied by the task sandbox, so this fixture substitutes only
    # that monitor transport and actually launches the unchanged private worker.
    def synthetic_monitor(command, **kwargs):
        with Path(kwargs["log"]).open("w") as log:
            completed = subprocess.run(command, cwd=kwargs["cwd"], env=kwargs["env"],
                                       stdout=log, stderr=subprocess.STDOUT, timeout=60)
        return dict(exit_code=completed.returncode, stop_reason=None, cleanup_error=None,
                    test_scope="SYNTHETIC_MONITOR_TRANSPORT; OUTER_TEST_WATCH_REQUIRED")
    monkeypatch.setattr(owner._resources, "run_watched", synthetic_monitor)
    kit, ids, binary = synthetic_kit(tmp_path)
    args = SimpleNamespace(kit=str(kit), set="SYN", diamond=str(binary), approx_id=None,
        threads=1, preflight=False, resource_receipt_dir=None, attempt_root=None,
        rss_limit_bytes=3_800_000_000, min_free_disk_bytes=2_000_000_000,
        timeout_seconds=60, keep_allvsall=keep)
    result = owner.cmd_ordinate(args)
    out = kit / "out_SYN"
    assert set(result["outputs"]) == {"PCOA_SYN.tsv", "REFERENCE_CLUSTERS_SYN.tsv"}
    assert (out / "allvsall.tsv.gz").exists() is keep
    assert ("retained_allvsall" in result) is keep
    assert not (out / "RESOURCE_ATTEMPT/scratch/allvsall.tsv").exists()
    if keep:
        retained = result["retained_allvsall"]
        assert retained["relative_path"] == "allvsall.tsv.gz"
        assert retained["sha256"] == hashlib.sha256((out / "allvsall.tsv.gz").read_bytes()).hexdigest()
        assert retained["uncompressed_sha256"] == hashlib.sha256(gzip.decompress((out / "allvsall.tsv.gz").read_bytes())).hexdigest()
        assert owner.distance_matrix(out / "allvsall.tsv.gz", ids).shape == (4, 4)
    terminal = json.loads((out / "RESOURCE_ATTEMPT/terminal.json").read_text())
    assert terminal["state"] == "SUCCEEDED"


def test_retention_refuses_drift_from_distance_binding(tmp_path):
    path = tmp_path / "hits.tsv"
    path.write_text("SYN-A\tSYN-B\t20\n")
    binding = owner._resources.digest(path)
    path.write_text("SYN-A\tSYN-B\t80\n")
    with pytest.raises(owner.OrdinateRefusal, match="distance-consumed"):
        owner._retain_allvsall(path, tmp_path / "out.gz", ["SYN-A", "SYN-B"], expected_source=binding)


def test_compute_refuses_hits_changed_during_distance(tmp_path, monkeypatch):
    kit, ids, binary = synthetic_kit(tmp_path)
    args = SimpleNamespace(kit=str(kit), set="SYN", diamond=str(binary), approx_id=None, threads=1)
    limits = dict(rss_limit_bytes=3_800_000_000, min_free_disk_bytes=2_000_000_000, threads=1)
    _, inputs, _, _ = owner._resources.read_inputs(kit, "SYN", limits)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    def fake_run(command):
        if command[1] == "blastp":
            (scratch / "allvsall.tsv").write_text("SYN-0\tSYN-1\t40\n")
    monkeypatch.setattr(owner, "run", fake_run)
    real = owner.distance_matrix
    def changed(path, order):
        matrix = real(path, order)
        Path(path).write_text("SYN-0\tSYN-1\t80\n")
        return matrix
    monkeypatch.setattr(owner, "distance_matrix", changed)
    with pytest.raises(owner.OrdinateRefusal, match="distance consumed"):
        owner._ordinate_compute(args, dict(scratch=str(scratch), limits=limits, inputs=inputs, keep_allvsall=True))
    assert not (scratch / "allvsall.tsv.gz").exists()
