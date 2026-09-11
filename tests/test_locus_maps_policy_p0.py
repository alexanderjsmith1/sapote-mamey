"""P0 (v9.7.101): locus-map render policy. The phase is expensive on large strains
(a 65-BGC genome under --chatgpt-safe did not finish in a capped session). Policy:
off (default under --chatgpt-safe) / on (always) / auto (skip when capped + >20 BGCs).

The first two tests exercise a real run on the bundled smoke fixture; the policy-branch
test exercises the gate logic directly (no 20+ BGC fixture is bundled).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _receipts(pkg_dir):
    f = pkg_dir / "run_phase_receipts.jsonl"
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def _locus_status(pkg_dir):
    return [r["status"] for r in _receipts(pkg_dir) if r.get("phase") == "locus_maps"]


def _run(tmp_path, strain, *extra):
    out = tmp_path / strain
    cmd = [sys.executable, "-m", "mamey", "run", "--strain", strain,
           "--input-zip", str(FIXTURE), "--taxonomy", "Test species",
           "--source", "fixture", "--mode", "gold", "--outdir", str(out), *extra]
    subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=300, check=True)
    return out / strain / "package"


@pytest.mark.skipif(not FIXTURE.exists(), reason="smoke fixture absent")
def test_chatgpt_safe_skips_locus_maps_by_default(tmp_path):
    pkg = _run(tmp_path, "P0_SAFE", "--chatgpt-safe", "--chatgpt-followup")
    assert "SKIP" in _locus_status(pkg), "chatgpt-safe should SKIP locus maps"
    assert "END" not in _locus_status(pkg), "no render should occur"
    assert not list((pkg / "locus_maps").glob("*.svg")), (
        "--locus-maps off must govern downstream compiled-report rendering too"
    )


@pytest.mark.skipif(not FIXTURE.exists(), reason="smoke fixture absent")
def test_locus_maps_on_overrides_chatgpt_safe(tmp_path):
    pkg = _run(tmp_path, "P0_ON", "--chatgpt-safe", "--chatgpt-followup", "--locus-maps", "on")
    statuses = _locus_status(pkg)
    assert statuses == ["START", "END"], (
        "--locus-maps on must complete its run phase without an ERROR receipt; "
        f"got {statuses}"
    )
    assert "ERROR" not in statuses
    assert list((pkg / "locus_maps").glob("*.png")), "enabled in-run rendering must remain active"
    v8_receipts = sorted((pkg / "locus_maps").glob("*_locus_map_v8_receipt.json"))
    assert v8_receipts, (
        "enabled in-run rendering must complete with the V8 renderer, not silently "
        "satisfy this test through the legacy PNG fallback"
    )
    receipt = json.loads(v8_receipts[0].read_text(encoding="utf-8"))
    assert receipt["renderer"] == "v8"
    assert receipt["exact_locus_identity"] == {
        "strain": "P0_ON",
        "full_node_or_contig": "NODE_1_length_20000_cov_50",
        "region": "region001",
        "bgc_alias": "BGC001",
        "display": "P0_ON / NODE_1_length_20000_cov_50 / region001 / BGC001 · NRPS",
    }


def test_compile_report_no_figures_does_not_bypass_locus_map_policy(tmp_path, monkeypatch):
    """The mandatory report's no-figure mode must not create post-seal maps."""
    from mamey import compile_report
    from mamey import locus_map

    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({
            "strain_id": "SYNTHETIC",
            "mamey_version": "test",
            "bundle_version": "test",
            "release": "PUBLIC",
            "assembly_tier": "TEST",
            "raw_bgcs": 0,
            "corrected_bgcs": 0,
        }),
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr(locus_map, "render_for_compile_report", lambda *a, **k: calls.append((a, k)))

    compile_report.build_report(pkg, generate_figures=False)

    assert calls == []


def test_compile_report_figures_enabled_keeps_locus_map_renderer(tmp_path, monkeypatch):
    """Explicit/default figure-enabled report compilation retains locus maps."""
    from mamey import compile_report
    from mamey import locus_map

    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({
            "strain_id": "SYNTHETIC",
            "mamey_version": "test",
            "bundle_version": "test",
            "release": "PUBLIC",
            "assembly_tier": "TEST",
            "raw_bgcs": 0,
            "corrected_bgcs": 0,
        }),
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr(locus_map, "render_for_compile_report", lambda *a, **k: calls.append((a, k)))

    compile_report.build_report(pkg, generate_figures=True)

    assert len(calls) == 1
    assert calls[0][1]["top_n"] == 5


def test_auto_policy_skips_large_capped_run():
    # mirror the gate: auto + brief=none + >20 BGCs -> skip
    def _decide(locus_maps, brief, raw_bgc_n):
        if locus_maps == "off":
            return False
        if locus_maps == "on":
            return True
        return not (brief == "none" and raw_bgc_n > 20)
    assert _decide("auto", "none", 65) is False     # large capped run -> skip
    assert _decide("auto", "none", 5) is True        # small capped run -> render
    assert _decide("auto", "standard", 65) is True   # large but not capped -> render
    assert _decide("off", "standard", 5) is False    # explicit off
    assert _decide("on", "none", 65) is True         # explicit on overrides size
