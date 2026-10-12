"""Synthetic resource/refusal and completion-chain controls; no genome jobs."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import _protein_pcoa_resources as resource

EXPECTED_THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_THREAD_LIMIT")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcoa_resource_ordinate", ROOT / "tools/protein_pcoa_ordinate.py")
ordinate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ordinate)
spec = importlib.util.spec_from_file_location("pcoa_resource_render", ROOT / "tools/protein_pcoa_render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def options(kit, **changes):
    values = dict(kit=str(kit), set="SYNTHETIC_REFERENCE", diamond=None, approx_id=None, threads=1,
                  preflight=False, resource_receipt_dir=None, attempt_root=None,
                  rss_limit_bytes=3_800_000_000, min_free_disk_bytes=2_000_000_000,
                  timeout_seconds=30)
    return SimpleNamespace(**dict(values, **changes))


@pytest.fixture
def kit(tmp_path):
    root = tmp_path / "kit"
    root.mkdir()
    (root / "SYNTHETIC_REFERENCE_META.tsv").write_text("id\tsource\n" + "".join(
        f"SYNTHETIC_REFERENCE_{n}\tisolate\n" for n in range(4)))
    (root / "SYNTHETIC_REFERENCE.faa").write_text("".join(
        f">SYNTHETIC_REFERENCE_{n}\nMAAAAA\n" for n in range(4)))
    return root


@pytest.mark.parametrize("n", [399, 400, 401, 7999, 8000, 8001])
def test_estimate_covers_every_reachable_branch_without_arrays(n):
    info = dict(records=n, fasta_bytes=0, metadata_bytes=0, maximum_line_bytes=0, maximum_id_bytes=10)
    measured = resource.estimate(info)
    assert measured["estimated_rss_bytes"] >= max(resource.solver_bytes(k) for k in range(4, n + 1))
    assert measured["estimate_not_guarantee"] is True
    if n == 8000:
        assert resource.solver_bytes(7999) > resource.solver_bytes(8000)
        assert 7999 in measured["reachable_solver_endpoints"]


@pytest.mark.parametrize("key,value", [("threads", 0), ("threads", -1), ("threads", 1.5),
    ("rss_limit_bytes", 0), ("timeout_seconds", float("nan")), ("timeout_seconds", float("inf")),
    ("min_free_disk_bytes", -1)])
def test_invalid_budget_refuses(kit, key, value):
    with pytest.raises(resource.ResourceRefusal):
        resource.budget(options(kit, **{key: value}))


def test_portable_configuration_can_exceed_campaign_defaults(kit):
    limits = resource.budget(options(kit, threads=8, rss_limit_bytes=8_000_000_000, timeout_seconds=1800))
    assert limits["threads"] == 8 and limits["rss_limit_bytes"] == 8_000_000_000
    assert "available_cpu_observation" in limits


def test_preflight_requires_explicit_fresh_write_target(kit):
    with pytest.raises(resource.ResourceRefusal, match="explicit"):
        resource.coordinate(options(kit, preflight=True), ROOT / "tools/protein_pcoa_ordinate.py")
    assert not (kit / "out_SYNTHETIC_REFERENCE").exists()


def test_preflight_never_discovers_tools_or_launches_worker(kit, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("preflight attempted heavy execution")
    monkeypatch.setattr(resource, "run_watched", forbidden)
    monkeypatch.setattr(ordinate, "diamond_exe", forbidden)
    before = {p.name: resource.digest(p) for p in kit.iterdir()}
    receipt = tmp_path / "explicit_receipt"
    result = resource.coordinate(options(kit, preflight=True, resource_receipt_dir=str(receipt)),
                                 ROOT / "tools/protein_pcoa_ordinate.py")
    assert result["counts"]["records"] == 4 and result["compute"] == "NOT_EXECUTED"
    assert not (kit / "out_SYNTHETIC_REFERENCE").exists()
    assert before == {p.name: resource.digest(p) for p in kit.iterdir()}
    assert json.loads((receipt / "terminal.json").read_text())["state"] == "PREFLIGHT_ADMITTED"


def test_upperbound_refuses_before_worker_and_preserves_source(kit, tmp_path, monkeypatch):
    monkeypatch.setattr(resource, "run_watched", lambda *a, **kw: pytest.fail("worker launched"))
    receipt = tmp_path / "refused"
    before = {p.name: p.read_bytes() for p in kit.iterdir()}
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(options(kit, preflight=True, resource_receipt_dir=str(receipt), rss_limit_bytes=100_000_000),
                            ROOT / "tools/protein_pcoa_ordinate.py")
    assert json.loads((receipt / "terminal.json").read_text())["state"] == "FAILED"
    assert before == {p.name: p.read_bytes() for p in kit.iterdir()}


@pytest.mark.parametrize("kind", ["duplicate_fasta", "missing_fasta", "duplicate_meta", "long_line"])
def test_streaming_membership_and_line_guards(kit, kind):
    fasta = kit / "SYNTHETIC_REFERENCE.faa"
    meta = kit / "SYNTHETIC_REFERENCE_META.tsv"
    if kind == "duplicate_fasta":
        fasta.write_text(fasta.read_text() + ">SYNTHETIC_REFERENCE_0\nMAAAAA\n")
    elif kind == "missing_fasta":
        fasta.write_text(">SYNTHETIC_REFERENCE_0\nMAAAAA\n")
    elif kind == "duplicate_meta":
        meta.write_text(meta.read_text() + "SYNTHETIC_REFERENCE_0\tisolate\n")
    else:
        fasta.write_text(">SYNTHETIC_REFERENCE_0\n" + "A" * (16 * 1024**2 + 1))
    with pytest.raises(resource.ResourceRefusal):
        resource.read_inputs(kit, "SYNTHETIC_REFERENCE", resource.budget(options(kit)))


def test_worker_consumed_stream_rejects_changed_input(kit):
    limits = resource.budget(options(kit))
    _, bound, _, _ = resource.read_inputs(kit, "SYNTHETIC_REFERENCE", limits)
    fasta = kit / "SYNTHETIC_REFERENCE.faa"
    fasta.write_text(fasta.read_text().replace("MAAAAA", "MAAAAT"))
    with pytest.raises(resource.ResourceRefusal, match="binding"):
        resource.read_inputs(kit, "SYNTHETIC_REFERENCE", limits, materialize=True, expected=bound)


def test_actual_n_admission_precedes_allvsall_and_dense_allocation(kit, tmp_path, monkeypatch):
    import numpy as np
    limits = resource.budget(options(kit))
    _, inputs, _, _ = resource.read_inputs(kit, "SYNTHETIC_REFERENCE", limits)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(ordinate, "diamond_exe", lambda value: "synthetic-not-executed")
    monkeypatch.setattr(ordinate, "run", lambda *a: pytest.fail("heavy child before actual-n admission"))
    monkeypatch.setattr(np, "ones", lambda *a, **kw: pytest.fail("dense allocation before actual-n admission"))
    def reject_actual(info, policy, *, n=None):
        assert n == 4
        raise resource.ResourceRefusal("synthetic actual-n refusal")
    monkeypatch.setattr(resource, "admit", reject_actual)
    with pytest.raises(resource.ResourceRefusal, match="actual-n"):
        ordinate._ordinate_compute(options(kit), dict(scratch=str(scratch), limits=limits, inputs=inputs))
    assert not (scratch / "kept.faa").exists()
    assert not (scratch / "RUN_SYNTHETIC_REFERENCE.json").exists()


def test_nonfinite_timeout_refuses_before_any_write(kit):
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(options(kit, timeout_seconds=float("nan")), ROOT / "tools/protein_pcoa_ordinate.py")
    assert not (kit / "out_SYNTHETIC_REFERENCE").exists()


@pytest.mark.parametrize("state", ["nonzero", "stop_with_zero", "cleanup", "monitor_refused", "missing_completion"])
def test_worker_failure_cannot_publish_run(kit, monkeypatch, state):
    def watch(command, **kwargs):
        assert command[:2] == [sys.executable, str(ROOT / "tools/protein_pcoa_ordinate.py")]
        assert command[2] == "--_ordinate-worker"  # watched root is Python, not only DIAMOND
        assert kwargs["rss_limit"] <= 3_800_000_000 and kwargs["timeout"] <= 900
        assert resource.THREAD_ENVIRONMENT_KEYS == EXPECTED_THREAD_KEYS
        assert {key: kwargs["env"].get(key) for key in EXPECTED_THREAD_KEYS} == {key: "1" for key in EXPECTED_THREAD_KEYS}
        request = json.loads(Path(command[3]).read_text())
        assert request["thread_environment"] == {key: "1" for key in EXPECTED_THREAD_KEYS}
        if state == "monitor_refused":
            raise resource.ValidationRefused("synthetic monitor refusal")
        return {"exit_code": 1 if state == "nonzero" else 0,
                "stop_reason": "MEMORY_LIMIT" if state == "stop_with_zero" else None,
                "cleanup_error": "synthetic cleanup failure" if state == "cleanup" else None}
    monkeypatch.setattr(resource, "run_watched", watch)
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(options(kit), ROOT / "tools/protein_pcoa_ordinate.py")
    out = kit / "out_SYNTHETIC_REFERENCE"
    assert not (out / "RUN_SYNTHETIC_REFERENCE.json").exists()
    assert json.loads((out / "RESOURCE_ATTEMPT/terminal.json").read_text())["state"] == "FAILED"


@pytest.mark.parametrize("kind", ["occupied", "symlink", "ancestor_alias"])
def test_output_refusal_preserves_unowned_contents(kit, tmp_path, kind):
    marker = tmp_path / "sentinel"
    marker.mkdir()
    (marker / "keep.txt").write_text("SYNTHETIC_REFERENCE_SENTINEL")
    out = kit / "out_SYNTHETIC_REFERENCE"
    a = options(kit)
    if kind == "occupied":
        out.mkdir(); (out / "keep.txt").write_text("SYNTHETIC_REFERENCE_SENTINEL")
    elif kind == "symlink":
        out.symlink_to(marker, target_is_directory=True)
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(kit, target_is_directory=True)
        a = options(alias)
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(a, ROOT / "tools/protein_pcoa_ordinate.py")
    assert (marker / "keep.txt").read_text() == "SYNTHETIC_REFERENCE_SENTINEL"


def test_historical_unknown_is_not_current_renderer_version():
    assert render.historical_producer({"pct_axes": [30, 20]}) == {"state": "NOT_RECORDED"}
    assert render.historical_producer({"producer": {"version": "historical-example"}}) == {
        "state": "SUPPLIED_UNVERIFIED", "metadata": {"producer": {"version": "historical-example"}}}


@pytest.mark.parametrize("key", ["VECLIB_MAXIMUM_THREADS", "OMP_THREAD_LIMIT"])
@pytest.mark.parametrize("value", [None, "2"])
def test_worker_refuses_changed_bound_thread_context_before_compute(tmp_path, monkeypatch, key, value):
    script = ROOT / "tools/protein_pcoa_ordinate.py"
    request = dict(schema=resource.SCHEMA, sources=resource.source_bindings(script),
                   thread_environment={name: "1" for name in EXPECTED_THREAD_KEYS})
    path = tmp_path / "request.json"
    resource.write_json(path, request)
    bound = resource.digest(path)["sha256"]
    monkeypatch.setenv("MAMEY_PCOA_REQUEST", bound)
    for name in EXPECTED_THREAD_KEYS:
        monkeypatch.setenv(name, "1")
    if value is None:
        monkeypatch.delenv(key)
    else:
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(ordinate, "diamond_exe", lambda *a: pytest.fail("tool discovery before thread admission"))
    with pytest.raises(ordinate.OrdinateRefusal, match="thread context"):
        ordinate._ordinate_worker(path, bound)


def test_new_attempt_missing_final_run_is_not_legacy(tmp_path):
    (tmp_path / "RESOURCE_ATTEMPT").mkdir()
    with pytest.raises(render.RenderRefusal, match="incomplete"):
        render.admit_resource_run(tmp_path, "SYNTHETIC_REFERENCE", {}, {}, [], [], {})


def test_real_small_watched_worker_has_acyclic_receipts(kit, tmp_path):
    """Real watched Python/NumPy + invented DIAMOND protocol, no external tool/data."""
    fake = tmp_path / "synthetic_diamond"
    fake.write_text("#!/usr/bin/env python3\n" + '''import pathlib,sys
a=sys.argv[1:]
if a[0]=='version':
    print('SYNTHETIC_REFERENCE_DIAMOND_PROTOCOL')
elif a[0]=='makedb':
    pathlib.Path(a[a.index('-d')+1]+'.dmnd').write_text('synthetic')
elif a[0]=='blastp':
    ids=[x[1:].strip() for x in pathlib.Path(a[a.index('-q')+1]).read_text().splitlines() if x.startswith('>')]
    pathlib.Path(a[a.index('-o')+1]).write_text(''.join(f'{q}\\t{s}\\t{100 if q==s else 50}\\n' for q in ids for s in ids))
else:
    raise SystemExit(2)
''')
    fake.chmod(0o700)
    before = {p.name: p.read_bytes() for p in kit.iterdir()}
    result = resource.coordinate(options(kit, diamond=str(fake)), ROOT / "tools/protein_pcoa_ordinate.py")
    out = kit / "out_SYNTHETIC_REFERENCE"
    run_path = out / "RUN_SYNTHETIC_REFERENCE.json"
    monitor = out / "RESOURCE_ATTEMPT/monitored_resource.json"
    terminal = json.loads((out / "RESOURCE_ATTEMPT/terminal.json").read_text())
    assert result["points"] == 4 and result["isolate_sequences"] == 4
    assert resource.THREAD_ENVIRONMENT_KEYS == EXPECTED_THREAD_KEYS
    assert result["diamond"]["thread_environment"] == {key: "1" for key in EXPECTED_THREAD_KEYS}
    assert terminal["state"] == "SUCCEEDED"
    assert terminal["run"]["sha256"] == hashlib.sha256(run_path.read_bytes()).hexdigest()
    assert result["resource_receipt"]["sha256"] == hashlib.sha256(monitor.read_bytes()).hexdigest()
    assert "run" not in json.loads(monitor.read_text())  # no cyclic hash dependency
    assert before == {name: (kit / name).read_bytes() for name in before}
    inputs = [out / "PCOA_SYNTHETIC_REFERENCE.tsv", run_path]
    bindings = [render.file_binding(p) for p in inputs]
    admitted = {p.absolute(): v for p, v in zip(inputs, bindings)}
    render.admit_resource_run(out, "SYNTHETIC_REFERENCE", result, bindings[1], inputs, bindings, admitted)
    altered = dict(result, attempt_id="synthetic-wrong-attempt")
    with pytest.raises(render.RenderRefusal):
        render.admit_resource_run(out, "SYNTHETIC_REFERENCE", altered, bindings[1], [], [], {})
