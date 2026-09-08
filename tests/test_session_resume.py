"""test_session_resume.py — companion tests for mamey/session_resume.py.

Full test suite pending from Opus audit. This stub satisfies the module-has-tests
gate (test_new_mamey_modules_have_companion_tests) until the real suite arrives.
"""
import pathlib
import json
import pytest


def _make_pkg(tmp_path, strain_id="AS-XXX"):
    """Build a minimal fake package for testing."""
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)

    # manifest_short.json
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": strain_id,
        "assembly_tier": "POOR",
        "raw_bgcs": 10,
        "corrected_bgcs": 6.5,
        "interior_pct": 25.0,
        "release": "PRIVATE",
        "top_3_ab": [{"bgc_id": "BGC001", "ab_score": 55.0}],
        "top_3_af": [{"bgc_id": "BGC002", "af_score": 40.0}],
    }))

    # manifest.json
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": strain_id,
        "display_name": f"{strain_id} display",
        "taxonomy": "Streptomyces sp.",
        "source": "honeybee, Ontario",
        "release": "PRIVATE",
        "bgc_counts": {"assembly_tier": "POOR", "raw": 10, "corrected": 6.5, "interior_pct": 25.0},
    }))

    # triage board
    (pkg / f"{strain_id}_4_triage_board.csv").write_text(
        "BGC_ID,AB_score\nBGC001,55\nBGC002,40\nBGC003,30\n"
    )

    # register — two complete, one pending
    (pkg / f"{strain_id}_judgment_register.json").write_text(json.dumps({
        "schema_version": "1.0",
        "strain_id": strain_id,
        "bgcs": {
            "BGC001": {"status": "COMPLETE", "quality_tier": "FULL"},
            "BGC002": {"status": "COMPLETE", "quality_tier": "SHALLOW"},
            "BGC003": {"status": "PENDING"},
        }
    }))
    return pkg


def test_resume_reads_assembly_tier_from_manifest_short(tmp_path):
    """Bug fix: must read from manifest_short, not manifest['assembly_tier']."""
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg)
    assert result['assembly_tier'] == 'POOR', f"Got: {result['assembly_tier']}"
    assert result['assembly_tier'] != 'UNKNOWN', "Bug: assembly_tier still UNKNOWN"


def test_resume_counts_complete_bgcs_correctly(tmp_path):
    """Bug fix: register schema uses bgcs[id]['status']=='COMPLETE', not mode_b_quality."""
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg)
    assert result['done'] == ['BGC001', 'BGC002'], f"Got done: {result['done']}"
    assert result['pending'] == ['BGC003'], f"Got pending: {result['pending']}"


def test_resume_markdown_contains_strain_info(tmp_path):
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg)
    md = result['markdown']
    assert 'POOR' in md
    assert 'BGC001' in md or 'BGC002' in md  # done cards appear


def test_resume_no_register_returns_all_pending(tmp_path):
    """Without a register, all BGCs are pending."""
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    (pkg / "AS-XXX_judgment_register.json").unlink()
    result = build_resume(pkg)
    assert len(result['done']) == 0
    assert len(result['pending']) == 3


def test_resume_ranked_reorders_next_up(tmp_path):
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg, ranked="BGC003,BGC001,BGC002")
    # BGC001 and BGC002 are done; next_up should just be BGC003
    assert result['next_up'] == ['BGC003']


def test_resume_json_output_is_valid(tmp_path):
    from mamey.session_resume import build_resume
    import json
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg)
    # Must be JSON-serialisable
    dumped = json.dumps(result, default=str)
    parsed = json.loads(dumped)
    assert parsed['strain_id'] == 'AS-XXX'


def test_resume_quality_notes_flags_shallow(tmp_path):
    from mamey.session_resume import build_resume
    pkg = _make_pkg(tmp_path)
    result = build_resume(pkg)
    # BGC002 is COMPLETE but SHALLOW — should appear in quality_notes
    notes_bgcs = [bgc for bgc, _ in result.get('quality_notes', [])] if 'quality_notes' in result else []
    # The markdown should mention SHALLOW
    assert 'SHALLOW' in result['markdown'], result['markdown'][:400]  # v9.7.412: `or True` made this vacuous
