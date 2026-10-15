"""Cluster-first admission is the default for a set with reference or MIBiG sequences.

Those sequences are clustered in every run, so admitting the unclustered upper bound first refused sets that fit after
clustering (the Paper 4 F7 case ran only with a hand-set --cluster-first). A cohort-only set is never clustered and keeps
the upper-bound admission. An explicit --cluster-first / --no-cluster-first wins, and the receipt says which applied.
SYN-only metadata preflights; no clustering or DIAMOND run happens here.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcoa_default_owner", ROOT / "tools/protein_pcoa_ordinate.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
resource = owner._resources


def _limits():
    return dict(rss_limit_bytes=3_800_000_000, min_free_disk_bytes=2_000_000_000, timeout_seconds=60, threads=4)


def _counts(cohort, reference, mibig=0):
    return dict(records=cohort + reference + mibig, cohort=cohort, reference=reference, mibig=mibig,
                fasta_bytes=1_000_000, metadata_bytes=1_000_000, maximum_line_bytes=100, maximum_id_bytes=20)


def _preflight(tmp_path, monkeypatch, counts, **flag):
    kit = tmp_path / "kit"
    kit.mkdir()
    args = SimpleNamespace(kit=str(kit), set="SYN", preflight=True, resource_receipt_dir=str(tmp_path / "receipt"),
                           attempt_root=None, diamond=None, approx_id=None, **flag, **_limits())
    monkeypatch.setattr(resource, "read_inputs", lambda *a, **k: (counts, [], {}, {}))
    monkeypatch.setattr(resource, "cluster_workspace_policy", lambda *a, **k: None)
    monkeypatch.setattr(resource.shutil, "disk_usage", lambda p: SimpleNamespace(free=10**12))
    monkeypatch.setattr(resource, "run_watched", lambda *a, **k: pytest.fail("metadata preflight launched a child"))
    return args, lambda: resource.coordinate(args, ROOT / "tools/protein_pcoa_ordinate.py")


def test_a_reference_set_is_admitted_cluster_first_by_default(tmp_path, monkeypatch):
    args, run = _preflight(tmp_path, monkeypatch, _counts(4, 19996))
    result = run()
    assert result["admission_mode"] == "CLUSTER_FIRST" and result["admission_mode_source"] == "DEFAULT"
    assert result["state"] == "PREFLIGHT_CLUSTER_ADMITTED_ORDINATION_PENDING"
    assert args.cluster_first is True            # the resolved mode reaches the workspace policy and the worker
    terminal = json.loads((tmp_path / "receipt" / "terminal.json").read_text())
    assert terminal["admission_mode_source"] == "DEFAULT"


def test_a_mibig_only_reference_set_is_also_cluster_first(tmp_path, monkeypatch):
    _args, run = _preflight(tmp_path, monkeypatch, _counts(4, 0, mibig=19996))
    assert run()["admission_mode"] == "CLUSTER_FIRST"


def test_a_cohort_only_set_keeps_the_upper_bound_admission(tmp_path, monkeypatch):
    args, run = _preflight(tmp_path, monkeypatch, _counts(20000, 0))
    with pytest.raises(resource.ResourceRefusal, match="RSS"):
        run()
    assert args.cluster_first is False


def test_an_explicit_no_cluster_first_refuses_a_large_reference_set_up_front(tmp_path, monkeypatch):
    _args, run = _preflight(tmp_path, monkeypatch, _counts(4, 19996), cluster_first=False)
    with pytest.raises(resource.ResourceRefusal, match="RSS"):
        run()


def test_an_explicit_flag_is_recorded_as_explicit(tmp_path, monkeypatch):
    _args, run = _preflight(tmp_path, monkeypatch, _counts(4, 20), cluster_first=False)
    result = run()
    assert result["admission_mode"] == "UPPER_BOUND_FIRST" and result["admission_mode_source"] == "EXPLICIT"


def test_the_cli_flag_defaults_to_unset_and_has_a_negative_form():
    text = (ROOT / "tools/protein_pcoa_ordinate.py").read_text()
    assert 'o.add_argument("--cluster-first", action=argparse.BooleanOptionalAction, default=None,' in text
