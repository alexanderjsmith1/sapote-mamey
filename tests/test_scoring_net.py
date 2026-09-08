"""test_scoring_net.py — CANDIDATE (Indigo2 §1+§2, 2026-08-15) → tests/ in the .367 cut.

Runs against the PATCHED engine (net_build/ on sys.path via conftest-free path insert).
The cross-engine identical-output proof lives in run_engine_case.py (executed separately,
sealed vs patched). Here: fingerprint neutrality (LOAD-BEARING per Cerulean condition 1),
collector contract, coverage-guard warn branch + gold-only wiring, handler persistence.
"""
import ast
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

from mamey import degradation                     # noqa: E402
import mamey as _mamey_pkg                        # noqa: E402

# Source-reading tests must find the ACTUAL imported package, not assume a layout:
# beside this file in the candidate build, one level up when installed under tests/.
PKG = Path(_mamey_pkg.__file__).parent
from mamey.models import BGCRecord                # noqa: E402
from mamey.packaging import (                     # noqa: E402
    DETERMINISM_WHITELIST, MUTABLE_RECEIPT_NAMES, repro_fingerprint,
)
from mamey.scoring import assert_full_scoring_coverage, triage_bgcs  # noqa: E402


def _pkg(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    for i, s in enumerate(DETERMINISM_WHITELIST):
        (pkg / f"NET{s}").write_text(f"a,b\n{i},{i}\n")
    return pkg


# ---- LOAD-BEARING: breadcrumb receipts never enter the fingerprint ----

def test_fingerprint_identical_after_breadcrumb_receipt(tmp_path):
    pkg = _pkg(tmp_path)
    before = repro_fingerprint(pkg)
    row = {"phase": "degradation_events", "status": "WARN", "n": 2,
           "events": [{"site": "scoring.triage_bgcs.cctt_per_bgc", "error": "RuntimeError('x')"}]}
    with (pkg / "run_phase_receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    after = repro_fingerprint(pkg)
    assert after["fingerprint"] == before["fingerprint"]
    assert after["components"] == before["components"]


def test_receipt_channel_is_outside_whitelist_by_name():
    assert "run_phase_receipts.jsonl" in MUTABLE_RECEIPT_NAMES
    assert not any("run_phase_receipts.jsonl".endswith(s) for s in DETERMINISM_WHITELIST)


# ---- collector contract ----

def test_record_drain_peek_roundtrip():
    degradation.drain()
    degradation.record("a.b.c", RuntimeError("boom"), bgc_id="BGC007")
    assert degradation.peek() == [{"site": "a.b.c", "error": "RuntimeError('boom')", "bgc_id": "BGC007"}]
    assert degradation.drain()[0]["site"] == "a.b.c"
    assert degradation.peek() == []


def test_record_never_raises_on_hostile_input():
    degradation.drain()

    class Unrepr:
        def __repr__(self):
            raise ValueError("no repr")
    degradation.record("x", Unrepr())          # repr() raises inside record
    degradation.record("y", "plain-string")    # non-exception payload OK
    assert any(e["site"] == "y" for e in degradation.drain())


# ---- coverage guard: warn branch + wiring ----

def _bgcs(n):
    return [BGCRecord(f"BGC{i:03d}", f"NODE_{i}_length_9000_cov_30", 1, 1, 8000, 9000,
                      products=["t1pks"]) for i in range(1, n + 1)]


def test_coverage_warn_fires_on_partial_and_not_on_full():
    bgcs = _bgcs(4)
    full = triage_bgcs(bgcs)
    assert assert_full_scoring_coverage(bgcs, full, strain="NET", raise_on_fail=False) == ""
    lead_only = full[:1]  # the BeeCohort failure shape: leads carried, rest dropped
    msg = assert_full_scoring_coverage(bgcs, lead_only, strain="NET", raise_on_fail=False)
    assert "SCORING-COVERAGE FAIL" in msg and "[NET]" in msg
    # warn branch must not raise even at 0 coverage
    assert "SCORING-COVERAGE FAIL" in assert_full_scoring_coverage(bgcs, [], raise_on_fail=False)


def test_cli_wiring_is_warn_only_and_gold_only():
    src = (PKG / "cli.py").read_text(encoding="utf-8")
    block = src.split("assert_full_scoring_coverage")
    assert len(block) >= 2, "coverage guard not wired in cli"
    call_ctx = src[src.index("assert_full_scoring_coverage") - 600: src.index("assert_full_scoring_coverage") + 400]
    assert 'analysis_mode", "") == "gold"' in call_ctx, "gold-only gate missing"
    assert "raise_on_fail=False" in call_ctx, "warn-only missing"
    assert '"scoring_coverage", "WARN"' in call_ctx, "receipt routing missing"


# ---- handler persistence (sites not exercisable without antiSMASH fixtures) ----

@pytest.mark.parametrize("fname,site", [
    ("source_scans.py", "source_scans.apply_cctt_vetoes.tetronate_completeness"),
    ("source_scans.py", "source_scans.run_source_scans.concordance_per_bgc"),
    ("source_scans.py", "source_scans.run_source_scans.concordance_module"),
    ("source_scans.py", "source_scans.registry_detector_activation"),
    ("parsers.py", "parsers.parse_bgcs_from_zip.region_coords_fallback"),
    # v9.7.403 — ("packaging.py", "packaging.write_manifest.base_reload") REMOVED, and this is a
    # net STRENGTHENING of the invariant, not a deleted safety net. C402-T01 replaced that
    # soft-fallback (record a degradation breadcrumb, then rebuild the manifest from an EMPTY
    # base — i.e. silently overwrite a corrupt manifest and carry on) with a typed refusal:
    # `packaging.ManifestRecoveryRequired`, raised by `_load_existing_manifest()` and caught
    # NOWHERE (verified: no handler for it anywhere in mamey/ or tools/, and neither caller at
    # cli.py:970 / cli.py:2103 wraps it), so a corrupt manifest now fails the run outright.
    # The replacement invariant is locked harder than the breadcrumb ever was, by
    # tests/test_packaging_manifest_recovery_v97402.py::
    # test_unreadable_or_nonobject_manifest_is_not_replaced — it asserts the prior manifest is
    # byte-identical afterwards AND that none of checksums_sha256.txt, package_status.json,
    # claim_safety_status.json or repro_fingerprint.json are written. Four concrete non-effects
    # in place of one breadcrumb string. This list intentionally no longer covers that site.
])
def test_breadcrumb_present_and_guard_kept(fname, site):
    src = (PKG / fname).read_text(encoding="utf-8")
    assert site in src, f"breadcrumb site string missing: {site}"
    tree = ast.parse(src)
    # every degradation.record call still lives INSIDE an except handler (guards kept)
    handlers = [h for h in ast.walk(tree) if isinstance(h, ast.ExceptHandler)]
    in_handler = any(site in ast.unparse(h) for h in handlers)
    assert in_handler, f"record call for {site} is not inside an except handler"


def test_scoring_all_five_sites_instrumented():
    src = (PKG / "scoring.py").read_text(encoding="utf-8")
    for slot in ("cctt_per_bgc", "cctt_uncorrob_by_bgc", "rt_per_bgc", "pm_per_bgc", "mis_per_bgc"):
        assert f'_degradation.record("scoring.triage_bgcs.{slot}"' in src


# ---- surface 2 (merge) wiring — added after Cerulean round-2 ruling ----

def test_merge_surface_wired_b1_only_warn_only():
    src = (PKG / "master_workbook.py").read_text(encoding="utf-8")
    i = src.index("master_workbook.B1_BGC_Master.coverage")
    ctx = src[i - 900: i + 300]
    assert "assert_full_scoring_coverage" in ctx, "canonical guard not reused"
    assert "raise_on_fail=False" in ctx, "warn-only missing"
    assert "DAPR C1/C2" in ctx and "exempt" in ctx, "DAPR exemption not documented at site"
    tree = ast.parse(src)
    # the whole check sits inside a never-raises wrapper (never breaks a merge).
    # v9.7.370 swallow triage: the wrapper may be a try/except OR a
    # `with contextlib.suppress(Exception)` block — the .370 conversion replaced the
    # anonymous `except: pass` with named deliberate suppression; the INVARIANT this
    # test pins (the coverage check can never fail a merge) is identical either way.
    def _never_raises_wrappers(t):
        for n in ast.walk(t):
            if isinstance(n, ast.Try):
                yield n
            elif isinstance(n, ast.With) and "suppress" in ast.unparse(n.items[0]):
                yield n
    assert any("B1_BGC_Master.coverage" in ast.unparse(n)
               for n in _never_raises_wrappers(tree)), "check not wrapped in a never-raises block"


def test_cli_drains_merge_breadcrumbs_after_master_update():
    src = (PKG / "cli.py").read_text(encoding="utf-8")
    call = src.index("update_master_workbook(run, master_path_p, master_out)")
    after = src[call: call + 900]
    assert '"master_coverage", "WARN"' in after, "merge drain receipt missing"
    assert "_deg_m.drain()" in after, "drain not wired after master update"


def test_merge_and_perstrain_use_same_guard_semantics():
    # both surfaces call the ONE canonical guard — no second implementation anywhere
    for fname in ("cli.py", "master_workbook.py"):
        src = (PKG / fname).read_text(encoding="utf-8")
        assert "assert_full_scoring_coverage" in src
    sc = (PKG / "scoring.py").read_text(encoding="utf-8")
    assert sc.count("def assert_full_scoring_coverage") == 1
