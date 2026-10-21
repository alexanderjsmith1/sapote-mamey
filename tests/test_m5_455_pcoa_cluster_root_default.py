"""Card m5_455_pcoa_cluster_root_default: without --cluster-work-root, DIAMOND clustering scratch goes under the
attempt's own RESOURCE_ATTEMPT folder (system temp only when that path is not shell-safe), recorded as root_source.
Invented labels and synthetic subprocess/resource controls only; no DIAMOND run."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import _protein_pcoa_resources as resource

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def safe_root(tmp_path):
    # pytest's own temp folder; run with a shell-safe --basetemp (no spaces) for the default-root cases.
    root = tmp_path.resolve()
    if any(c.isspace() for c in str(root)):
        pytest.skip("basetemp path is not shell-safe; rerun with a shell-safe --basetemp")
    return root


def info(reference=4, mibig=0):
    return dict(records=4, reference=reference, mibig=mibig, cohort=0, fasta_bytes=200,
                metadata_bytes=120, maximum_line_bytes=60, maximum_id_bytes=24)


def limits():
    return dict(rss_limit_bytes=3_800_000_000, min_free_disk_bytes=1, timeout_seconds=30, threads=1)


@pytest.fixture(autouse=True)
def abundant(monkeypatch):
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda path: SimpleNamespace(free=10**12))


def test_default_root_is_the_attempt_receipt(safe_root):
    receipt = safe_root / "out_SYN" / "RESOURCE_ATTEMPT"; receipt.mkdir(parents=True)
    p = resource.cluster_workspace_policy(SimpleNamespace(), info(), limits(), default_root=receipt)
    assert p["root"] == str(receipt.resolve()) and p["root_source"] == "ATTEMPT_RECEIPT_DEFAULT"


def test_unsafe_receipt_path_falls_back_to_system_temp_and_says_so(safe_root, monkeypatch):
    receipt = safe_root / "spaced kit" / "RESOURCE_ATTEMPT"; receipt.mkdir(parents=True)
    tmp = safe_root / "systmp"; tmp.mkdir()
    monkeypatch.setattr(resource.tempfile, "gettempdir", lambda: str(tmp))
    p = resource.cluster_workspace_policy(SimpleNamespace(), info(), limits(), default_root=receipt)
    assert p["root"] == str(tmp) and p["root_source"] == "SYSTEM_TEMP_FALLBACK_ATTEMPT_PATH_NOT_SHELL_SAFE"


def test_explicit_root_wins_and_a_refused_explicit_root_is_never_replaced(safe_root):
    receipt = safe_root / "RESOURCE_ATTEMPT"; receipt.mkdir()
    chosen = safe_root / "chosen"; chosen.mkdir()
    p = resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(chosen)), info(), limits(), default_root=receipt)
    assert p["root"] == str(chosen) and p["root_source"] == "EXPLICIT"
    bad = safe_root / "space path"; bad.mkdir()
    with pytest.raises(resource.ResourceRefusal, match="shell-safe"):
        resource.cluster_workspace_policy(SimpleNamespace(cluster_work_root=str(bad)), info(), limits(), default_root=receipt)


def test_no_default_root_keeps_the_sealed_system_temp_behaviour(safe_root, monkeypatch):
    monkeypatch.setattr(resource.tempfile, "gettempdir", lambda: str(safe_root))
    p = resource.cluster_workspace_policy(SimpleNamespace(), info(), limits())
    assert p["root"] == str(safe_root) and p["root_source"] == "SYSTEM_TEMP_DEFAULT"


def test_cohort_only_set_has_no_cluster_workspace(safe_root):
    assert resource.cluster_workspace_policy(SimpleNamespace(), info(reference=0, mibig=0), limits(), default_root=safe_root) is None


def test_coordinator_default_puts_cluster_scratch_in_resource_attempt(safe_root, monkeypatch):
    kit = safe_root / "kit"; kit.mkdir()
    (kit / "SYN_META.tsv").write_text("id\tsource\n" + "".join(f"SYN_{i}\treference\n" for i in range(4)))
    (kit / "SYN.faa").write_text("".join(f">SYN_{i}\nMAAAAA\n" for i in range(4)))
    a = SimpleNamespace(kit=str(kit), set="SYN", diamond=None, approx_id=None, threads=1, preflight=False,
                        resource_receipt_dir=None, attempt_root=None, cluster_work_root=None,
                        rss_limit_bytes=3_800_000_000, min_free_disk_bytes=1, timeout_seconds=30)
    seen = {}
    def watch(argv, **kw):
        request = json.loads(Path(argv[3]).read_text())
        seen.update(request["cluster_workspace"])
        assert kw["additional_disk_floors"][0][0] == Path(seen["root"])
        return {"exit_code": 1, "stop_reason": None, "cleanup_error": None}
    monkeypatch.setattr(resource, "run_watched", watch)
    with pytest.raises(resource.ResourceRefusal):
        resource.coordinate(a, ROOT / "tools/protein_pcoa_ordinate.py")
    assert seen["root"] == str((kit / "out_SYN" / "RESOURCE_ATTEMPT").resolve())
    assert seen["root_source"] == "ATTEMPT_RECEIPT_DEFAULT"
