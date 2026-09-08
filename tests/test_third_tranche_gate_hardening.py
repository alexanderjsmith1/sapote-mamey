"""Regression guards for the third v9.7.390 candidate tool-hardening tranche."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS))


def _load(name):
    spec = importlib.util.spec_from_file_location(f"third_{name}", TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_version_refuses_all_mutation_when_any_rule_is_invalid(monkeypatch, tmp_path):
    """A late missing anchor must not leave earlier version files rewritten."""
    sv = _load("sync_version")
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("version=old\n", encoding="utf-8")
    second.write_text("anchor=present\n", encoding="utf-8")
    monkeypatch.setattr(sv, "ROOT", tmp_path)
    monkeypatch.setattr(sv, "RULES", [
        ("first.txt", re.compile(r"version=old"), "version=new"),
        ("second.txt", re.compile(r"anchor=missing"), "anchor=new"),
    ])
    monkeypatch.setattr(sv, "sync_build_stamp_patch", lambda check: [])
    bootstrap_calls = []
    monkeypatch.setattr(sv, "sync_bootstrap_contract",
                        lambda check: bootstrap_calls.append(check) or (True, []))

    with pytest.raises(SystemExit) as exc:
        sv.main([])
    assert exc.value.code == 1
    assert first.read_text(encoding="utf-8") == "version=old\n"
    assert second.read_text(encoding="utf-8") == "anchor=present\n"
    assert bootstrap_calls == []


def test_sync_version_refuses_anchor_writes_when_bootstrap_generator_fails(monkeypatch, tmp_path):
    sv = _load("sync_version")
    target = tmp_path / "version.txt"
    target.write_text("version=old\n", encoding="utf-8")
    monkeypatch.setattr(sv, "ROOT", tmp_path)
    monkeypatch.setattr(sv, "RULES", [
        ("version.txt", re.compile(r"version=old"), "version=new"),
    ])
    monkeypatch.setattr(sv, "sync_build_stamp_patch", lambda check: [])
    monkeypatch.setattr(
        sv, "sync_bootstrap_contract",
        lambda check: (False, ["bootstrap-contract sync timed out after 120 seconds (--apply)"]),
    )
    with pytest.raises(SystemExit) as exc:
        sv.main([])
    assert exc.value.code == 1
    assert target.read_text(encoding="utf-8") == "version=old\n"


def test_judgment_count_fails_closed_when_structure_gate_crashes(monkeypatch, tmp_path):
    sjr = _load("sapote_judgment_receipt")
    card = tmp_path / "card.md"
    card.write_text("<!-- MODE B: BGC001 -->\n", encoding="utf-8")
    monkeypatch.setattr(sjr, "_structure_linter", lambda: (
        lambda *a, **k: (_ for _ in ()).throw(ValueError("broken gate"))))
    with pytest.raises(RuntimeError, match="refusing completeness credit"):
        sjr.count_modeb_cards([str(card)], enforce_structure=True)


def test_judgment_suite_timeout_is_typed(monkeypatch, tmp_path):
    sjr = _load("sapote_judgment_receipt")
    manifest = tmp_path / "manifest.md"
    manifest.write_text("x", encoding="utf-8")
    checker = tmp_path / "check_deliverable_suite.py"
    checker.write_text("print('{}')\n", encoding="utf-8")
    monkeypatch.setattr(sjr.subprocess, "run", lambda *a, **k: (
        (_ for _ in ()).throw(subprocess.TimeoutExpired(a[0], 120))))
    state, detail = sjr.suite_pass(str(manifest), "gold", str(tmp_path))
    assert state is None
    assert "timed out after 120 seconds" in detail


def test_markdown_preflight_blocks_forbidden_computational_repr(tmp_path):
    smp = _load("sapote_md_preflight")
    src = tmp_path / "input.md"
    out = tmp_path / "safe.md"
    qa = tmp_path / "qa.json"
    src.write_text("# Report\n\nMeasured value: np.int64(48)\n", encoding="utf-8")
    rc = smp.main([str(src), str(out), "--qa-json", str(qa)])
    assert rc == 1
    receipt = json.loads(qa.read_text(encoding="utf-8"))
    assert receipt["status"] == "FAIL"
    assert any(f["type"] == "forbidden_render_string" for f in receipt["findings"])


def test_phylo_file_probe_timeout_is_fail_not_warning(monkeypatch, tmp_path):
    pp = _load("phylo_preflight")
    hmm = tmp_path / "hmm"
    hmm.mkdir()
    (hmm / "Actinobacteria.hmm").write_text("fixture", encoding="utf-8")
    monkeypatch.setenv("GToTree_HMM_dir", str(hmm))
    monkeypatch.setattr(pp, "_which", lambda name: f"/fixture/{name}")

    def fake_run(cmd, **kwargs):
        if cmd[0] == "file":
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 20))
        return SimpleNamespace(stdout="GToTree v1.8.19\n", stderr="", returncode=0)

    monkeypatch.setattr(pp.subprocess, "run", fake_run)
    report = pp.Report()
    pp.check_env(report)
    e1c = next(item for item in report.items if item["check"] == "E1c")
    assert e1c["status"] == "FAIL"


def test_phylo_genome_hash_is_streamed_and_correct(tmp_path):
    pp = _load("phylo_preflight")
    genome = tmp_path / "genome.fna"
    payload = (b">contig\n" + b"ACGT" * 700_000)
    genome.write_bytes(payload)
    assert pp._sha256_file(genome, chunk_size=8192) == hashlib.sha256(payload).hexdigest()


def test_gate_outputs_are_wired_to_shared_atomic_helpers():
    sync_src = (TOOLS / "sync_version.py").read_text(encoding="utf-8")
    judgment_src = (TOOLS / "sapote_judgment_receipt.py").read_text(encoding="utf-8")
    md_src = (TOOLS / "sapote_md_preflight.py").read_text(encoding="utf-8")
    phylo_src = (TOOLS / "phylo_preflight.py").read_text(encoding="utf-8")
    assert "from _wbio import atomic_write_text" in sync_src
    assert "atomic_dump_json(receipt, a.out" in judgment_src
    assert "atomic_write_text(ns.output_md" in md_src and "atomic_dump_json(" in md_src
    # v9.7.405: the candidate writes this receipt through the NEWER owner-scoped helper
    # (atomic_dump_json_owned, aliased _atomic_write_json); either atomic path satisfies the gate.
    assert ("atomic_dump_json(rep.items, a.json" in phylo_src
            or "atomic_dump_json_owned(" in phylo_src or "_atomic_write_json(" in phylo_src)
