"""Invented labels/short strings; synthetic subprocess and resource controls only."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import _protein_pcoa_resources as resource
from tools import _release_validation as monitor

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cluster_workspace_ordinate", ROOT / "tools/protein_pcoa_ordinate.py")
ordinate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ordinate)


@pytest.fixture
def safe_root():
    # A test-owned POSIX scratch child, independent of pytest's possibly spaced basetemp.
    with tempfile.TemporaryDirectory(prefix="synthetic-pcoa-", dir=Path("/tmp").resolve()) as path:
        yield Path(path).resolve()


def info():
    return dict(records=4, reference=4, mibig=0, cohort=0, fasta_bytes=200,
                metadata_bytes=120, maximum_line_bytes=60, maximum_id_bytes=24)


def limits():
    return dict(rss_limit_bytes=3_800_000_000, min_free_disk_bytes=1, timeout_seconds=30, threads=1)


def abundant(monkeypatch):
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda path: SimpleNamespace(free=10**12))


def policy(root, monkeypatch):
    (root / "diamond").write_text("SYNTHETIC_REFERENCE_NOT_EXECUTED")
    abundant(monkeypatch)
    return resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(root)), info(), limits())


@pytest.mark.parametrize("suffix", ["space path", "semi;colon", "dollar$", "tick`", "quote'", 'double"',
                                  "paren()", "pipe|", "amp&", "glob*", "bracket[", "unicode_é", "line\nbreak"])
def test_shell_unsafe_root_refuses_before_any_child(safe_root, monkeypatch, suffix):
    root = safe_root / suffix
    root.mkdir()
    monkeypatch.setattr(resource.subprocess, "run", lambda *a, **k: pytest.fail("child launched"))
    with pytest.raises(resource.ResourceRefusal, match="shell-safe"):
        resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(root)), info(), limits())
    assert list(root.iterdir()) == []


def test_explicit_symlink_refused_but_default_resolved_alias_admitted(safe_root, tmp_path, monkeypatch):
    abundant(monkeypatch)
    alias = tmp_path / "alias"
    alias.symlink_to(safe_root, target_is_directory=True)
    with pytest.raises(resource.ResourceRefusal, match="symlink"):
        resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(alias)), info(), limits())
    monkeypatch.setattr(resource.tempfile, "gettempdir", lambda: str(alias))
    p = resource.cluster_workspace_policy(SimpleNamespace(), info(), limits())
    assert p["root"] == str(safe_root) and p["estimate_not_guarantee"] is True


def test_low_scratch_disk_refuses_before_child_or_temp_creation(safe_root, monkeypatch):
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda path: SimpleNamespace(free=2))
    monkeypatch.setattr(resource.tempfile, "mkdtemp", lambda **kw: pytest.fail("scratch created before admission"))
    with pytest.raises(resource.ResourceRefusal, match="filesystem"):
        resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(safe_root)), info(), limits())


def test_cluster_uses_safe_local_relative_paths_and_binds_exact_bytes(safe_root, tmp_path, monkeypatch):
    p = policy(safe_root, monkeypatch)
    original = tmp_path / "original spaced receipt"
    original.mkdir()
    source = original / "refs.faa"
    raw = b">SYNTHETIC_REFERENCE_1\nMAAAAA\n>SYNTHETIC_REFERENCE_2\nMAAAAT\n"
    source.write_bytes(raw)
    output = original / "refs_clusters.tsv"
    table = b"SYNTHETIC_REFERENCE_1\tSYNTHETIC_REFERENCE_1\nSYNTHETIC_REFERENCE_1\tSYNTHETIC_REFERENCE_2\n"
    cwd_before = Path.cwd()
    observed = []
    def child(argv, **kwargs):
        cwd = kwargs["cwd"]
        observed.append(cwd)
        assert resource.shell_safe_path(cwd) == cwd and cwd.parent == safe_root
        assert argv[argv.index("-d") + 1] == "input.faa"
        assert argv[argv.index("-o") + 1] == "clusters.tsv"
        assert argv[argv.index("--tmpdir") + 1] == "tmp"
        assert argv[argv.index("--approx-id") + 1] == "70"
        assert argv[argv.index("--member-cover") + 1] == "80"
        assert argv[argv.index("--threads") + 1] == "1"
        assert kwargs == {"cwd": cwd, "check": True}  # no shell/new session/global chdir
        assert (cwd / "input.faa").read_bytes() == raw
        assert Path.cwd() == cwd_before
        (cwd / "clusters.tsv").write_bytes(table)
    monkeypatch.setattr(resource.subprocess, "run", child)
    result = resource.run_cluster_workspace(str(safe_root / "diamond"), source, output, name="refs", approx_id=70,
        threads=1, member_count=2, maximum_id_bytes=24, policy=p, limits=limits())
    assert source.read_bytes() == raw and output.read_bytes() == table
    assert result["input_copy"]["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["output_copy"]["copy"]["sha256"] == hashlib.sha256(table).hexdigest()
    assert result["cleanup"] == "OWNED_TEMP_REMOVED" and not observed[0].exists()
    terminal = json.loads((original / "refs_cluster_terminal.json").read_text())
    assert terminal["child_process_group"] == "INHERIT_WATCHED_WORKER"
    assert terminal["state"] == "SUCCEEDED"


@pytest.mark.parametrize("mode", ["nonzero", "missing", "oversized", "symlink", "input_drift"])
def test_cluster_failures_retain_diagnostics_without_result_claim(safe_root, tmp_path, monkeypatch, mode):
    p = policy(safe_root, monkeypatch)
    source = tmp_path / "refs.faa"
    source.write_bytes(b">SYNTHETIC_REFERENCE_1\nMAAAAA\n")
    output = tmp_path / "refs_clusters.tsv"
    outside = tmp_path / "sentinel"
    outside.write_text("SYNTHETIC_REFERENCE_SENTINEL")
    created = []
    def child(argv, **kw):
        cwd = kw["cwd"]; created.append(cwd)
        if mode == "nonzero":
            raise subprocess.CalledProcessError(7, argv)
        if mode == "missing":
            return
        if mode == "oversized":
            (cwd / "clusters.tsv").write_bytes(b"x" * 1000)
        elif mode == "symlink":
            (cwd / "clusters.tsv").symlink_to(outside)
        else:
            source.write_bytes(b">SYNTHETIC_REFERENCE_1\nMAAAAT\n")
            (cwd / "clusters.tsv").write_bytes(b"SYNTHETIC_REFERENCE_1\tSYNTHETIC_REFERENCE_1\n")
    monkeypatch.setattr(resource.subprocess, "run", child)
    with pytest.raises(resource.ResourceRefusal):
        resource.run_cluster_workspace(str(safe_root / "diamond"), source, output, name="refs", approx_id=70,
            threads=1, member_count=1, maximum_id_bytes=24, policy=p, limits=limits())
    terminal = json.loads((tmp_path / "refs_cluster_terminal.json").read_text())
    assert terminal["state"] == "FAILED" and terminal["cleanup"] == "OWNED_TEMP_REMOVED"
    assert outside.read_text() == "SYNTHETIC_REFERENCE_SENTINEL"
    assert not created[0].exists()
    assert not (tmp_path / "RUN_SYNTHETIC_REFERENCE.json").exists()


def test_copy_ceiling_and_occupied_target_preserve_sentinels(tmp_path):
    source = tmp_path / "input"
    source.write_bytes(b"SYNTHETIC_REFERENCE")
    output = tmp_path / "output"
    with pytest.raises(resource.ResourceRefusal, match="ceiling"):
        resource.bounded_copy(source, output, 2)
    assert not output.exists()
    output.write_bytes(b"SYNTHETIC_REFERENCE_SENTINEL")
    with pytest.raises(FileExistsError):
        resource.bounded_copy(source, output, 100)
    assert output.read_bytes() == b"SYNTHETIC_REFERENCE_SENTINEL"


def test_owned_scratch_replacement_refuses_cleanup_of_unowned_target(safe_root, tmp_path, monkeypatch):
    p = policy(safe_root, monkeypatch)
    source = tmp_path / "refs.faa"; source.write_bytes(b">SYNTHETIC_REFERENCE_1\nMAAAAA\n")
    sentinel = tmp_path / "sentinel"; sentinel.mkdir();(sentinel / "keep").write_text("SYNTHETIC_REFERENCE_SENTINEL")
    owned = []
    def child(argv, **kw):
        scratch = kw["cwd"]
        moved = scratch.with_name(scratch.name + "-moved"); scratch.rename(moved);owned.append((scratch,moved))
        scratch.symlink_to(sentinel, target_is_directory=True)
        raise subprocess.CalledProcessError(7, argv)
    monkeypatch.setattr(resource.subprocess, "run", child)
    with pytest.raises(resource.ResourceRefusal):
        resource.run_cluster_workspace(str(safe_root / "diamond"), source, tmp_path / "refs_clusters.tsv", name="refs",
            approx_id=70, threads=1, member_count=1, maximum_id_bytes=24, policy=p, limits=limits())
    assert (sentinel / "keep").read_text() == "SYNTHETIC_REFERENCE_SENTINEL"
    assert json.loads((tmp_path / "refs_cluster_terminal.json").read_text())["cleanup"] == "REFUSED"
    # Remove only test-created aliases/moved directories; product must leave them alone.
    owned[0][0].unlink()
    resource.shutil.rmtree(owned[0][1])


def test_coordinator_binds_work_root_and_monitors_both_filesystems(safe_root, tmp_path, monkeypatch):
    abundant(monkeypatch)
    kit = tmp_path / "spaced source kit"; kit.mkdir()
    (kit / "SYNTHETIC_REFERENCE_META.tsv").write_text("id\tsource\n" + "".join(f"SYNTHETIC_REFERENCE_{i}\treference\n" for i in range(4)))
    (kit / "SYNTHETIC_REFERENCE.faa").write_text("".join(f">SYNTHETIC_REFERENCE_{i}\nMAAAAA\n" for i in range(4)))
    a = SimpleNamespace(kit=str(kit), set="SYNTHETIC_REFERENCE", diamond=None, approx_id=None, threads=1,
        preflight=False, resource_receipt_dir=None, attempt_root=None, cluster_work_root=str(safe_root),
        rss_limit_bytes=3_800_000_000, min_free_disk_bytes=1, timeout_seconds=30)
    before = {p.name:p.read_bytes() for p in kit.iterdir()}
    def watch(argv, **kw):
        request = json.loads(Path(argv[3]).read_text())
        workspace = request["cluster_workspace"]
        assert workspace["root"] == str(safe_root)
        assert kw["additional_disk_floors"] == ((safe_root, workspace["monitor_min_free_bytes"]),)
        assert kw["cwd"].name == "RESOURCE_ATTEMPT"
        assert argv[2] == "--_ordinate-worker"
        return {"exit_code":1,"stop_reason":None,"cleanup_error":None}
    monkeypatch.setattr(resource, "run_watched", watch)
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(a, ROOT / "tools/protein_pcoa_ordinate.py")
    out = kit / "out_SYNTHETIC_REFERENCE"
    assert json.loads((out / "RESOURCE_ATTEMPT/terminal.json").read_text())["state"] == "FAILED"
    assert not (out / "RUN_SYNTHETIC_REFERENCE.json").exists()
    assert before == {name:(kit/name).read_bytes() for name in before}


def test_low_additional_disk_refuses_before_launch(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"; scratch.mkdir()
    monkeypatch.setattr(monitor.shutil, "disk_usage", lambda path: SimpleNamespace(free=1 if Path(path)==scratch else 1000))
    monkeypatch.setattr(monitor.subprocess, "Popen", lambda *a, **k: pytest.fail("child launched"))
    with pytest.raises(monitor.ValidationRefused, match="disk"):
        monitor.run_watched(["not-executed"],cwd=tmp_path,log=tmp_path/"watch.log",env={},min_disk=10,
            additional_disk_floors=((scratch,10),),sampler=lambda pid:0)
    assert not (tmp_path/"watch.log").exists()


def test_additional_disk_drop_stops_even_zero_exit_and_records_root(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"; scratch.mkdir()
    reads = []
    def usage(path):
        if Path(path)==scratch:
            reads.append(path)
            return SimpleNamespace(free=1000 if len(reads)==1 else 1)
        return SimpleNamespace(free=1000)
    monkeypatch.setattr(monitor.shutil,"disk_usage",usage)
    class Process:
        pid=123456
        def poll(self):return 0
        def wait(self):return 0
    class Tree:
        def __init__(self,pid):self.known={pid};self.cleanup_events=[]
        def refresh(self):return {}
        def stop(self,process):return None
    monkeypatch.setattr(monitor.subprocess,"Popen",lambda *a,**kw:Process())
    monkeypatch.setattr(monitor,"_OwnedProcessTree",Tree)
    result=monitor.run_watched(["not-executed"],cwd=tmp_path,log=tmp_path/"watch.log",env={},min_disk=10,
        additional_disk_floors=((scratch,10),),sampler=lambda pid:0)
    assert result["exit_code"]==0 and result["stop_reason"]=="DISK_LIMIT"
    assert result["disk_stop_root"]==str(scratch)
    assert {row["path"]:row["min_free_bytes"] for row in result["disk_floors"]}=={str(tmp_path):10,str(scratch):10}


@pytest.mark.parametrize("floor", [True, -1, 1.5, float("nan")])
def test_invalid_additional_disk_floor_refuses_before_child(tmp_path, monkeypatch, floor):
    monkeypatch.setattr(monitor.subprocess,"Popen",lambda *a,**kw:pytest.fail("child launched"))
    with pytest.raises(monitor.ValidationRefused,match="disk floor"):
        monitor.run_watched(["not-executed"],cwd=tmp_path,log=tmp_path/"watch.log",env={},
            additional_disk_floors=((tmp_path,floor),),sampler=lambda pid:0)
    assert not (tmp_path/"watch.log").exists()


def test_cluster_root_identity_drift_refuses_before_temp_or_child(safe_root, monkeypatch):
    p = policy(safe_root, monkeypatch)
    p["inode"] += 1
    monkeypatch.setattr(resource.tempfile,"mkdtemp",lambda **kw:pytest.fail("scratch created"))
    with pytest.raises(resource.ResourceRefusal,match="identity"):
        resource.checked_cluster_root(p,limits())


@pytest.mark.parametrize("fail_cluster", [False, True])
def test_real_watched_worker_cluster_transport_and_final_receipt(safe_root, tmp_path, monkeypatch, fail_cluster):
    """Real Python/watch chain with an invented DIAMOND protocol, not native DIAMOND."""
    kit = tmp_path / "source kit with spaces"; kit.mkdir()
    labels = [(f"SYNTHETIC_REFERENCE_{i}", "isolate" if i < 4 else "reference" if i < 6 else "MIBiG") for i in range(8)]
    (kit / "SYNTHETIC_REFERENCE_META.tsv").write_text("id\tsource\n"+"".join(f"{i}\t{s}\n" for i,s in labels))
    (kit / "SYNTHETIC_REFERENCE.faa").write_text("".join(f">{i}\nMAAAAA\n" for i,s in labels))
    source_before = {p.name:p.read_bytes() for p in kit.iterdir()}
    fake = safe_root / "diamond"
    fake.write_text("#!/usr/bin/env python3\n" + """import os,pathlib,re,sys
a=sys.argv[1:]
if a[0]=='version':
    print('SYNTHETIC_REFERENCE_DIAMOND_PROTOCOL')
elif a[0]=='cluster':
    assert re.fullmatch(r'[A-Za-z0-9_./-]+',str(pathlib.Path.cwd()))
    assert a[a.index('-d')+1]=='input.faa' and a[a.index('-o')+1]=='clusters.tsv'
    assert a[a.index('--tmpdir')+1]=='tmp'
    assert a[a.index('--member-cover')+1]=='80' and a[a.index('--approx-id')+1]=='70'
    if os.environ.get('SYNTHETIC_CLUSTER_FAIL')=='1':raise SystemExit(7)
    ids=[line[1:].strip() for line in pathlib.Path('input.faa').read_text().splitlines() if line.startswith('>')]
    pathlib.Path('clusters.tsv').write_text(''.join(f'{ids[0]}\\t{i}\\n' for i in ids))
elif a[0]=='makedb':
    pathlib.Path(a[a.index('-d')+1]+'.dmnd').write_text('SYNTHETIC_REFERENCE')
elif a[0]=='blastp':
    ids=[line[1:].strip() for line in pathlib.Path(a[a.index('-q')+1]).read_text().splitlines() if line.startswith('>')]
    pathlib.Path(a[a.index('-o')+1]).write_text(''.join(f'{q}\\t{s}\\t{100 if q==s else 50}\\n' for q in ids for s in ids))
else:raise SystemExit(2)
""")
    fake.chmod(0o700)
    if fail_cluster:monkeypatch.setenv("SYNTHETIC_CLUSTER_FAIL","1")
    else:monkeypatch.delenv("SYNTHETIC_CLUSTER_FAIL",raising=False)
    a=SimpleNamespace(kit=str(kit),set="SYNTHETIC_REFERENCE",diamond=str(fake),approx_id=70,threads=1,
        preflight=False,resource_receipt_dir=None,attempt_root=None,cluster_work_root=str(safe_root),
        rss_limit_bytes=3_800_000_000,min_free_disk_bytes=1,timeout_seconds=30)
    output=kit/"out_SYNTHETIC_REFERENCE"
    if fail_cluster:
        with pytest.raises(resource.ResourceRefusal):
            resource.coordinate(a,ROOT/"tools/protein_pcoa_ordinate.py")
        assert not (output/"RUN_SYNTHETIC_REFERENCE.json").exists()
        assert json.loads((output/"RESOURCE_ATTEMPT/terminal.json").read_text())["state"]=="FAILED"
        cluster=json.loads((output/"RESOURCE_ATTEMPT/scratch/refs_cluster_terminal.json").read_text())
        assert cluster["state"]=="FAILED" and cluster["cleanup"]=="OWNED_TEMP_REMOVED"
    else:
        result=resource.coordinate(a,ROOT/"tools/protein_pcoa_ordinate.py")
        assert result["points"]==6 and result["isolate_sequences"]==4
        assert result["reference_sequences"]==2 and result["mibig_sequences"]==2 and result["centroids"]==2
        assert len(result["cluster_attempts"])==2
        for binding in result["cluster_attempts"]:
            terminal=Path(binding["terminal"]["path"])
            assert hashlib.sha256(terminal.read_bytes()).hexdigest()==binding["terminal"]["sha256"]
            assert not Path(json.loads(terminal.read_text())["temporary_directory"]).exists()
        assert json.loads((output/"RESOURCE_ATTEMPT/terminal.json").read_text())["state"]=="SUCCEEDED"
        watch=json.loads((output/"RESOURCE_ATTEMPT/monitored_resource.json").read_text())["watch"]
        assert str(safe_root) in {row["path"] for row in watch["disk_floors"]}
        assert watch["exit_code"]==0 and watch["stop_reason"] is None
    assert source_before=={name:(kit/name).read_bytes() for name in source_before}
    assert not list(safe_root.glob("mamey-pcoa-cluster-*"))
