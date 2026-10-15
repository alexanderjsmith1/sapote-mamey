"""SYN-only engineering admission tests; native clustering is explicitly stubbed."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(os.environ.get("N5_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location("n5_cluster_owner", ROOT / "tools/protein_pcoa_ordinate.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
resource = owner._resources


def limits():
    return dict(rss_limit_bytes=3_800_000_000, min_free_disk_bytes=2_000_000_000, timeout_seconds=60, threads=4)


def large_counts(cohort=4):
    return dict(records=20000, cohort=cohort, reference=20000-cohort, mibig=0,
                fasta_bytes=1_000_000, metadata_bytes=1_000_000,
                maximum_line_bytes=100, maximum_id_bytes=20)


def test_cluster_admission_does_not_require_unclustered_dense_matrix():
    info = large_counts()
    with pytest.raises(resource.ResourceRefusal, match="RSS"):
        resource.admit(info, limits())
    stage = resource.cluster_stage_estimate(info, limits())
    assert stage["stage"] == "CLUSTER_ONLY"
    assert stage["final_ordination_admission"] == "PENDING_CLUSTERED_N"
    assert stage["estimated_rss_bytes"] < limits()["rss_limit_bytes"] * .8
    assert resource.admit(info, limits(), n=12)["retained_n"] == 12
    assert resource.DEFAULT_RSS == 3_800_000_000


def test_cluster_admission_cannot_reduce_irreducible_cohort():
    with pytest.raises(resource.ResourceRefusal, match="RSS"):
        resource.cluster_stage_estimate(large_counts(cohort=20000), limits())


def test_cluster_admission_preserves_input_memory_margin():
    info = large_counts()
    info["fasta_bytes"] = 400_000_000
    with pytest.raises(resource.ResourceRefusal, match="cluster-stage"):
        resource.cluster_stage_estimate(info, limits())


@pytest.mark.parametrize("cluster_first", [False, True])
def test_metadata_preflight_distinguishes_cluster_pending_from_final_admission(tmp_path, monkeypatch, cluster_first):
    kit = tmp_path / "kit"
    kit.mkdir()
    receipt = tmp_path / "receipt"
    args = SimpleNamespace(kit=str(kit), set="SYN", preflight=True, resource_receipt_dir=str(receipt),
                           attempt_root=None, diamond=None, approx_id=None, cluster_first=cluster_first,
                           **limits())
    monkeypatch.setattr(resource, "read_inputs", lambda *a, **k: (large_counts(), [], {}, {}))
    monkeypatch.setattr(resource, "cluster_workspace_policy", lambda *a, **k: None)
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda p: SimpleNamespace(free=10**12))
    monkeypatch.setattr(resource, "run_watched", lambda *a, **k: pytest.fail("metadata preflight launched a child"))
    if not cluster_first:
        with pytest.raises(resource.ResourceRefusal, match="RSS"):
            resource.coordinate(args, ROOT / "tools/protein_pcoa_ordinate.py")
    else:
        result = resource.coordinate(args, ROOT / "tools/protein_pcoa_ordinate.py")
        assert result["state"] == "PREFLIGHT_CLUSTER_ADMITTED_ORDINATION_PENDING"
        assert result["compute"] == "NOT_EXECUTED"
        assert result["estimate"]["stage"] == "CLUSTER_ONLY"
        assert result["unclustered_upper_bound_estimate"]["retained_n"] == 20000
        assert not (kit / "out_SYN").exists()
        terminal = json.loads((receipt / "terminal.json").read_text())
        assert terminal["state"] == result["state"]
        assert terminal["estimate"] == result["estimate"]


def synthetic_compute(tmp_path, monkeypatch, *, disk=10**12, refuse_matrix=False):
    kit = tmp_path / "kit"
    kit.mkdir()
    sources = ["isolate"]*2 + ["reference_held"]*3 + ["MIBiG"]*3
    ids = [f"SYN-{n}" for n in range(len(sources))]
    (kit / "SYN.faa").write_text("".join(f">{i}\nMAAA\n" for i in ids))
    (kit / "SYN_META.tsv").write_text("id\tsource\n"+"".join(f"{i}\t{s}\n" for i,s in zip(ids,sources)))
    _, inputs, _, _ = resource.read_inputs(kit, "SYN", limits())
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    events=[]
    def cluster(exe, source, destination, **kwargs):
        group = [line[1:].strip() for line in source.read_text().splitlines() if line.startswith(">")]
        assert len(group)==3
        assert kwargs["approx_id"] == 90 and kwargs["threads"] == 4
        events.append(("cluster", kwargs["name"], tuple(group)))
        destination.write_text("".join(f"{group[0]}\t{m}\n" for m in group))
        return dict(name=kwargs["name"], fixture="SYN_CLUSTER_STUB")
    monkeypatch.setattr(resource, "run_cluster_workspace", cluster)
    monkeypatch.setattr(owner, "diamond_exe", lambda *a: "SYN-NOT-EXECUTED")
    real_admit = resource.admit
    def admit(info, policy, *, n=None):
        events.append(("matrix_admit", n))
        if refuse_matrix:
            raise resource.ResourceRefusal("SYN matrix refusal")
        return real_admit(info, policy, n=n)
    monkeypatch.setattr(resource, "admit", admit)
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda p: SimpleNamespace(free=disk))
    def command(argv):
        events.append(("child", argv[1]))
        if argv[1] == "blastp":
            kept=[line[1:].strip() for line in (scratch / "kept.faa").read_text().splitlines() if line.startswith(">")]
            (scratch / "allvsall.tsv").write_text("".join(f"{q}\t{s}\t50\n" for q in kept for s in kept))
    monkeypatch.setattr(owner, "run", command)
    args = SimpleNamespace(kit=str(kit), set="SYN", diamond=None, approx_id=None, threads=4)
    request = dict(scratch=str(scratch), limits=limits(), inputs=inputs, cluster_first=True, keep_allvsall=False)
    return args, request, events, scratch


def test_group_clustering_precedes_exact_n_admission_and_preserves_cohort(tmp_path, monkeypatch):
    args, request, events, scratch = synthetic_compute(tmp_path, monkeypatch)
    result = owner._ordinate_compute(args, request)
    assert [e[0] for e in events] == ["cluster", "cluster", "matrix_admit", "child", "child"]
    assert events[0][1:] == ("refs", ("SYN-2", "SYN-3", "SYN-4"))
    assert events[1][1:] == ("mibig", ("SYN-5", "SYN-6", "SYN-7"))
    assert events[2] == ("matrix_admit", 4)
    assert result["points"] == 4 and result["isolate_sequences"] == 2
    assert result["centroids"] == 2
    matrix = json.loads((scratch / "matrix_admission.json").read_text())
    assert matrix["retained_n"] == 4 and matrix["input_counts"]["records"] == 8
    assert result["matrix_admission"]["sha256"] == resource.digest(scratch / "matrix_admission.json")["sha256"]
    assert [r["id"] for r in owner.read_tsv(scratch / "PCOA_SYN.tsv")] == ["SYN-0", "SYN-1", "SYN-2", "SYN-5"]


def test_post_cluster_rss_refusal_precedes_allvsall_and_matrix(tmp_path, monkeypatch):
    args, request, events, scratch = synthetic_compute(tmp_path, monkeypatch, refuse_matrix=True)
    with pytest.raises(resource.ResourceRefusal, match="SYN matrix refusal"):
        owner._ordinate_compute(args, request)
    assert not any(e[0] == "child" for e in events)
    assert not (scratch / "kept.faa").exists()


def test_post_cluster_disk_refusal_precedes_allvsall(tmp_path, monkeypatch):
    args, request, events, scratch = synthetic_compute(tmp_path, monkeypatch, disk=2_000_000_000)
    with pytest.raises(owner.OrdinateRefusal, match="scratch growth"):
        owner._ordinate_compute(args, request)
    assert not any(e[0] == "child" for e in events)
    assert not (scratch / "kept.faa").exists()


def test_cluster_admission_derives_irreducible_count_from_parser_categories(tmp_path, monkeypatch):
    sources = ["isolate"] * 4 + ["reference_held"] * 2 + ["SID_held"] + ["MIBiG"] * 3
    ids = [f"SYN-{n}" for n in range(len(sources))]
    (tmp_path / "SYN.faa").write_text("".join(f">{i}\nMAAA\n" for i in ids))
    (tmp_path / "SYN_META.tsv").write_text("id\tsource\n" + "".join(f"{i}\t{s}\n" for i, s in zip(ids, sources)))
    info, _, _, _ = resource.read_inputs(tmp_path, "SYN", limits())
    assert (info["cohort"], info["reference"], info["mibig"], info["records"]) == (4, 3, 3, 10)
    observed = []
    original_admit = resource.admit
    def observe(info, limits, *, n=None):
        observed.append(n)
        return original_admit(info, limits, n=n)
    monkeypatch.setattr(resource, "admit", observe)
    resource.cluster_stage_estimate(info, limits())
    assert observed == [info["cohort"]]


def test_cluster_admission_refuses_inconsistent_membership_counts():
    info = large_counts()
    info["reference"] = info["records"] + 1
    with pytest.raises(resource.ResourceRefusal, match="inconsistent input membership counts"):
        resource.cluster_stage_estimate(info, limits())
