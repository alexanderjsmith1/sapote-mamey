"""test_render_all_figures.py — tests for Gap 3 / W9-N14 (v9.7.150e+).

The post-seal aggregate `mamey render-all-figures` runs every applicable
figure module against a sealed package, non-blocking per module.

These tests verify the dispatch + non-blocking behaviour without
requiring matplotlib (each per-set dispatcher must degrade gracefully when
the underlying module is absent or the input data isn't available).

All fixtures use AS-XXX.
"""
from __future__ import annotations

import json
import pathlib

import pytest

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _bare_pkg(tmp_path: pathlib.Path) -> pathlib.Path:
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-XXX",
        "taxonomy": "Streptomyces sp.",
        "source": "Apis mellifera, Ontario",
    }))
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": "AS-XXX",
        "assembly_tier": "POOR",
        "interior_pct": 25.0,
    }))
    return pkg


# ---------------------------------------------------------------------------
# Top-level run_all() behaviour
# ---------------------------------------------------------------------------

def test_render_all_refuses_when_manifest_missing(tmp_path):
    from mamey.render_all_figures import render_all
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    # No manifest.json
    summary = render_all(pkg)
    assert summary["ok"] is False
    assert "manifest.json not found" in summary["error"]


def test_render_all_default_sets_against_bare_package(tmp_path):
    """Missing lead input is a child refusal, not successful optional absence."""
    from mamey.render_all_figures import render_all
    pkg = _bare_pkg(tmp_path)
    summary = render_all(pkg)
    assert set(summary["sets"].keys()) >= {"smoke", "brief", "locus-maps",
                                            "figure-suite", "domain-level"}
    result = summary["sets"]["figure-suite"]
    assert result["status"] == "ERRORED"
    assert result["exit_code"] == 1
    assert result["figures"] == 0
    assert result["error"] == (
        "render_figures_command failed with exit code 1; "
        "inspect child diagnostics under figures_rendered/"
    )
    assert summary["ok"] is False
    assert summary["completion_state"] == "FAIL"
    assert summary["independent_gates"]["render_execution"] == "FAIL"
    assert "Triage board missing" in (
        pkg / "figures_rendered" / "NO_FIGURES_RENDERED.md"
    ).read_text(encoding="utf-8")



def test_render_all_dry_run_lists_sets_without_running(tmp_path):
    from mamey.render_all_figures import render_all
    pkg = _bare_pkg(tmp_path)
    summary = render_all(pkg, dry_run=True)
    assert summary["dry_run"] is True
    for s in summary["sets"].values():
        assert s["status"] == "DRY_RUN"


def test_render_all_include_filter_restricts_sets(tmp_path):
    from mamey.render_all_figures import render_all
    pkg = _bare_pkg(tmp_path)
    summary = render_all(pkg, include=["smoke"], dry_run=True)
    assert list(summary["sets"].keys()) == ["smoke"]


def test_render_all_exclude_filter_removes_sets(tmp_path):
    from mamey.render_all_figures import render_all
    pkg = _bare_pkg(tmp_path)
    summary = render_all(pkg, exclude=["brief", "domain-level"], dry_run=True)
    assert "brief" not in summary["sets"]
    assert "domain-level" not in summary["sets"]
    assert "smoke" in summary["sets"]


def test_render_all_unknown_set_name_reports_but_does_not_crash(tmp_path):
    from mamey.render_all_figures import render_all
    pkg = _bare_pkg(tmp_path)
    summary = render_all(pkg, include=["smoke", "not-a-real-set"])
    assert summary["sets"]["not-a-real-set"]["status"] == "UNKNOWN_SET"
    assert summary["ok"] is False
    assert summary["completion_state"] == "FAIL"
    # Other sets still ran (or skipped) cleanly
    assert "smoke" in summary["sets"]


def test_render_all_continue_on_error_default_true(tmp_path, monkeypatch):
    """If one set raises an unexpected exception, the others must still run
    by default (non-blocking aggregate)."""
    from mamey import render_all_figures as raf

    def _broken(pkg, **kw):
        raise RuntimeError("simulated module failure")

    monkeypatch.setattr(raf, "_run_brief", _broken)
    summary = raf.render_all(_bare_pkg(tmp_path))
    assert summary["sets"]["brief"]["status"] == "ERRORED"
    # Continue means later independent sets run; it must not rewrite an error
    # into aggregate success.
    assert summary["ok"] is False
    assert summary["completion_state"] == "FAIL"
    assert summary["independent_gates"]["publication_approval"] == "NOT_ASSESSED"
    # Other sets present
    assert "smoke" in summary["sets"]
    assert "locus-maps" in summary["sets"]


def test_render_all_fail_fast_stops_on_first_error(tmp_path, monkeypatch):
    """With continue_on_error=False, the run halts on the first error."""
    from mamey import render_all_figures as raf

    def _broken(pkg, **kw):
        raise RuntimeError("simulated module failure")

    # The default set order is smoke, brief, locus-maps, figure-suite, domain-level
    # — break the FIRST one so we can verify the rest never ran.
    monkeypatch.setattr(raf, "_run_smoke", _broken)
    summary = raf.render_all(_bare_pkg(tmp_path), continue_on_error=False)
    assert summary["ok"] is False
    assert summary["sets"]["smoke"]["status"] == "ERRORED"
    # Subsequent sets should not have run
    assert "brief" not in summary["sets"]


def test_render_all_default_sets_excludes_workbook_required(tmp_path):
    """The default set list must not include cohort-class or mamey-native
    (those need --workbook). Otherwise a default run would always show
    SKIPPED for two sets, which is noisy."""
    from mamey.render_all_figures import DEFAULT_SETS, ALL_SETS
    assert "cohort-class" not in DEFAULT_SETS
    assert "mamey-native" not in DEFAULT_SETS
    assert "cohort-class" in ALL_SETS
    assert "mamey-native" in ALL_SETS


# ---------------------------------------------------------------------------
# Workbook-requiring sets skip cleanly without --workbook
# ---------------------------------------------------------------------------

def test_cohort_class_skips_without_workbook(tmp_path):
    from mamey.render_all_figures import _run_cohort_class
    pkg = _bare_pkg(tmp_path)
    res = _run_cohort_class(pkg, workbook=None)
    assert res["status"] == "SKIPPED"
    assert "workbook" in res.get("skipped_reason", "").lower()


def test_cohort_class_threads_real_skip_reason(tmp_path, monkeypatch):
    """render_cohort_class_heatmap reports its own specific SKIPPED reason (e.g. "no B2
    data") under the key "reason". _run_cohort_class must surface that as skipped_reason
    rather than silently dropping it and letting the --all summary fall back to the
    generic "likely matplotlib/addon missing or no data" line, which was indistinguishable
    from a real config problem."""
    from mamey.render_all_figures import _run_cohort_class
    import mamey.cohort_class_heatmap as cch

    monkeypatch.setattr(
        cch, "render_cohort_class_heatmap",
        lambda *a, **kw: {"status": "SKIPPED", "reason": "no B2 data", "n_strains": 0},
    )
    pkg = _bare_pkg(tmp_path)
    (tmp_path / "wb.xlsx").write_bytes(b"")
    res = _run_cohort_class(pkg, workbook=str(tmp_path / "wb.xlsx"))
    assert res["status"] == "SKIPPED", res
    assert res.get("skipped_reason") == "cohort-class heatmap: no B2 data"


def test_cohort_class_accepts_renderer_uppercase_ok(tmp_path, monkeypatch):
    """A written cohort heatmap returns status OK and must be reported RAN."""
    from mamey.render_all_figures import _run_cohort_class
    import mamey.cohort_class_heatmap as cch

    monkeypatch.setattr(
        cch, "render_cohort_class_heatmap",
        lambda *a, **kw: {"status": "OK", "n_strains": 3, "n_classes": 4},
    )
    pkg = _bare_pkg(tmp_path)
    workbook = tmp_path / "wb.xlsx"
    workbook.write_bytes(b"")
    res = _run_cohort_class(pkg, workbook=str(workbook))
    assert res["status"] == "RAN"
    assert res["figures"] == 1


def test_domain_level_attempt_failure_is_not_downgraded_to_missing_data(tmp_path, monkeypatch):
    """A producer failure is distinct from an optional domain-level absence."""
    from mamey import render_all_figures as subject
    import mamey.domain_level as domain_level

    pkg = _bare_pkg(tmp_path)
    monkeypatch.setattr(
        domain_level, "run_domain_level",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("output unavailable")),
    )

    result = subject._run_domain_level(pkg)

    assert result["status"] == "ERRORED"
    assert "output unavailable" in result["error"]


def test_domain_level_expected_unavailable_result_remains_skip(tmp_path, monkeypatch):
    """Negative control: the producer's typed optional absence remains nonblocking."""
    from mamey import render_all_figures as subject
    import mamey.domain_level as domain_level

    pkg = _bare_pkg(tmp_path)
    monkeypatch.setattr(
        domain_level, "run_domain_level",
        lambda *_args, **_kwargs: {"status": "SKIPPED", "reason": "no sealed domain context"},
    )

    result = subject._run_domain_level(pkg)

    assert result["status"] == "SKIPPED"
    assert result["skipped_reason"] == "no sealed domain context"


def test_gather_marks_untracked_prior_files(tmp_path):
    from mamey.render_all_figures import gather_figures

    pkg = _bare_pkg(tmp_path)
    source = pkg / "smoke_figures"
    source.mkdir()
    (source / "current.svg").write_text("<svg/>", encoding="utf-8")
    gathered = pkg / "figures"
    gathered.mkdir()
    (gathered / "old.svg").write_text("<svg/>", encoding="utf-8")
    result = gather_figures(pkg, {"sets": {"smoke": {"out": str(source)}}})
    assert result["gathered"] == 1
    assert result["untracked_or_stale"] == 1
    index = (gathered / "FIGURE_INDEX.csv").read_text(encoding="utf-8")
    assert "UNTRACKED_OR_STALE" in index
    assert "sha256" in index.splitlines()[0]


def test_gather_records_copy_failure_instead_of_dropping_figure(tmp_path, monkeypatch):
    """A failed copy stays nonblocking but is retained in the structured handoff."""
    from mamey import render_all_figures as subject

    pkg = _bare_pkg(tmp_path)
    source = pkg / "smoke_figures"
    source.mkdir()
    (source / "lost.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setattr(
        subject.shutil, "copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    result = subject.gather_figures(pkg, {"sets": {"smoke": {"out": str(source)}}})

    assert result["gathered"] == 0
    assert result["copy_failures"] == [{
        "source_locator": "smoke_figures/lost.svg",
        "error": "OSError: disk full",
    }]


def test_gather_raises_when_figure_index_cannot_be_written(tmp_path, monkeypatch):
    """The command-level nonblocking handler must see an index-write failure."""
    from mamey import render_all_figures as subject

    pkg = _bare_pkg(tmp_path)
    source = pkg / "smoke_figures"
    source.mkdir()
    (source / "figure.svg").write_text("<svg/>", encoding="utf-8")

    class BrokenWriter:
        def __init__(self, *_args, **_kwargs):
            pass

        def writeheader(self):
            raise OSError("disk full")

    monkeypatch.setattr(subject, "_SafeDictWriter", BrokenWriter)
    with pytest.raises(OSError, match="disk full"):
        subject.gather_figures(pkg, {"sets": {"smoke": {"out": str(source)}}})


def test_mamey_native_skips_without_workbook(tmp_path):
    from mamey.render_all_figures import _run_mamey_native
    pkg = _bare_pkg(tmp_path)
    res = _run_mamey_native(pkg, workbook=None)
    assert res["status"] == "SKIPPED"
    assert "workbook" in res.get("skipped_reason", "").lower()


def test_mamey_native_skips_not_errors_on_strain_only_workbook(tmp_path):
    """A single-strain per-strain workbook (no Strain_Registry/DAPR/RG-GMCI cohort sheets)
    is the normal, expected shape before a strain is merged into a master workbook — this
    must report SKIPPED with a clear reason, not ERRORED, so a real error (e.g. a corrupt
    workbook) isn't masked by the same status as "no cohort data yet"."""
    from mamey.render_all_figures import _run_mamey_native
    import openpyxl

    pkg = _bare_pkg(tmp_path)
    wb = openpyxl.Workbook()
    wb.active.title = "BGC_Master"
    wb.active.append(["BGC_ID"])
    wb_path = tmp_path / "AS-000_5_workbook.xlsx"
    wb.save(wb_path)

    res = _run_mamey_native(pkg, workbook=str(wb_path))
    assert res["status"] == "SKIPPED", res
    reason = res.get("skipped_reason", "")
    assert "cohort" in reason.lower() or "master-workbook" in reason.lower()
    assert "Strain_Registry" in reason


def test_mamey_native_still_errors_on_genuine_failure(tmp_path, monkeypatch):
    """A real failure in the mamey-native figure engine (anything other than the expected
    missing-cohort-sheets ValueError) must still report ERRORED, not be silently downgraded
    to SKIPPED by the new handling above."""
    from mamey.render_all_figures import _run_mamey_native
    import mamey.mamey_native_figures as mnf

    def _boom(*a, **kw):
        raise RuntimeError("simulated genuine failure")

    monkeypatch.setattr(mnf, "render_mamey_native_figure_set", _boom)
    pkg = _bare_pkg(tmp_path)
    (tmp_path / "wb.xlsx").write_bytes(b"")  # path just needs to exist as a string arg
    res = _run_mamey_native(pkg, workbook=str(tmp_path / "wb.xlsx"))
    assert res["status"] == "ERRORED", res
    assert "simulated genuine failure" in res.get("error", "")


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def test_cli_dispatch_dry_run(tmp_path):
    from mamey.render_all_figures import render_all_figures_command

    class _Args:
        package = str(_bare_pkg(tmp_path))
        include = None
        exclude = None
        all_sets = False
        workbook = None
        top_n = 10
        fail_fast = False
        dry_run = True

    rc = render_all_figures_command(_Args())
    assert rc == 0


def test_cli_dispatch_with_include_smoke_only(tmp_path):
    from mamey.render_all_figures import render_all_figures_command

    class _Args:
        package = str(_bare_pkg(tmp_path))
        include = "smoke"
        exclude = None
        all_sets = False
        workbook = None
        top_n = 10
        fail_fast = False
        dry_run = False

    rc = render_all_figures_command(_Args())
    # smoke skips silently on a bare package; rc should still be 0
    assert rc == 0


def test_cli_writes_summary_json(tmp_path):
    from mamey.render_all_figures import render_all_figures_command
    pkg = _bare_pkg(tmp_path)

    class _Args:
        package = str(pkg)
        include = "smoke"
        exclude = None
        all_sets = False
        workbook = None
        top_n = 10
        fail_fast = False
        dry_run = False

    render_all_figures_command(_Args())
    assert (pkg / "render_all_figures_summary.json").exists()
    data = json.loads(
        (pkg / "render_all_figures_summary.json").read_text(encoding="utf-8"))
    # v9.7.414: three properties, deliberately asserted together.
    # 1. NO absolute path — the shipped JSON must never embed the operator's layout
    #    (CLAUDE_409 / DEEP_AUDIT3 F1). The pre-.409 absolute assertion is gone for good.
    # 2. `package` stays the "." anchor, matching manifest.json / PACKAGE_MAP.json.
    # 3. …and the receipt must still NAME its subject. Those two files pair the "."
    #    anchor with a strain_id; this one carried no identifier at all, so a shipped
    #    summary named nothing. Asserting 2 and 3 together stops either being
    #    "fixed" by breaking the other.
    assert str(pkg.resolve()) not in json.dumps(data), "shipped summary leaks an absolute path"
    assert data["package"] == "."
    assert data.get("strain_id") == "AS-XXX", "shipped summary cannot identify its package"
    assert "smoke" in data["sets"]


# Synthetic adapter controls: no biological data or rendering dependency.
def _synthetic_aggregate_package(tmp_path):
    pkg = tmp_path / "SYNTHETIC_REFERENCE_FIGURE_PACKAGE"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({"strain_id": "SYNTHETIC_REFERENCE_FIGURE_SUBJECT"}),
        encoding="utf-8",
    )
    return pkg


@pytest.mark.parametrize("exit_code", [1, 2])
@pytest.mark.parametrize("old_figure", [False, True])
def test_figure_suite_child_failure_is_error(tmp_path, monkeypatch, exit_code, old_figure):
    from mamey import render_all_figures as subject
    from mamey import chatgpt_commands

    pkg = _synthetic_aggregate_package(tmp_path)
    old = pkg / "figures_rendered" / "prior.svg"
    if old_figure:
        old.parent.mkdir()
        old.write_text("<svg><!-- prior synthetic marker --></svg>", encoding="utf-8")
    calls = []

    def child(args):
        calls.append((args.package, args.outdir, args.figure_set))
        return exit_code

    monkeypatch.setattr(chatgpt_commands, "render_figures_command", child)
    result = subject._run_figure_suite(pkg)
    assert calls == [(str(pkg), str(pkg / "figures_rendered"), "standard")]
    assert result == {
        "status": "ERRORED", "figures": 0,
        "out": str(pkg / "figures_rendered"), "exit_code": exit_code,
        "error": f"render_figures_command failed with exit code {exit_code}; "
                 "inspect child diagnostics under figures_rendered/",
    }
    assert old.exists() is old_figure
    if old_figure:
        assert old.read_text(encoding="utf-8") == "<svg><!-- prior synthetic marker --></svg>"


@pytest.mark.parametrize("produce_figure", [False, True])
def test_figure_suite_zero_controls(tmp_path, monkeypatch, produce_figure):
    from mamey import render_all_figures as subject
    from mamey import chatgpt_commands

    pkg = _synthetic_aggregate_package(tmp_path)

    def child(args):
        if produce_figure:
            out = pathlib.Path(args.outdir)
            out.mkdir()
            (out / "current.svg").write_text("<svg/>", encoding="utf-8")
        return 0

    monkeypatch.setattr(chatgpt_commands, "render_figures_command", child)
    result = subject._run_figure_suite(pkg)
    assert result["status"] == ("RAN" if produce_figure else "SKIPPED")
    assert result["figures"] == int(produce_figure)
    assert result["exit_code"] == 0


@pytest.mark.parametrize("fail_fast", [False, True])
def test_figure_suite_child_failure_propagates_to_cli_receipt(tmp_path, monkeypatch, capsys, fail_fast):
    from types import SimpleNamespace
    from mamey import render_all_figures as subject
    from mamey import chatgpt_commands

    pkg = _synthetic_aggregate_package(tmp_path)
    calls = []

    def child(args):
        calls.append("child")
        return 2

    def later(_pkg, **_kwargs):
        calls.append("later")
        return {"status": "SKIPPED", "figures": 0,
                "skipped_reason": "synthetic optional absence"}

    monkeypatch.setattr(chatgpt_commands, "render_figures_command", child)
    monkeypatch.setattr(subject, "_run_smoke", later)
    monkeypatch.setattr(subject, "figure_stack_preflight", lambda: (True, "synthetic preflight"))
    args = SimpleNamespace(package=str(pkg), include="figure-suite,smoke", exclude=None,
                           all_sets=False, workbook=None, top_n=10,
                           fail_fast=fail_fast, dry_run=False)
    assert subject.render_all_figures_command(args) == 1
    assert calls == (["child"] if fail_fast else ["child", "later"])
    summary = json.loads((pkg / "render_all_figures_summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is False
    assert summary["completion_state"] == "FAIL"
    assert summary["independent_gates"] == {
        "render_execution": "FAIL", "publication_approval": "NOT_ASSESSED",
        "biological_validation": "NOT_ASSESSED", "release_approval": "NOT_ASSESSED",
    }
    result = summary["sets"]["figure-suite"]
    assert result["status"] == "ERRORED"
    assert result["exit_code"] == 2
    assert result["figures"] == 0
    assert result["out"] == "figures_rendered"
    assert ("smoke" in summary["sets"]) is (not fail_fast)
    assert summary["package"] == "."
    assert str(pkg) not in json.dumps(summary)
    assert "ERRORED" in capsys.readouterr().err


@pytest.mark.parametrize("mode", ["exclude", "dry-run"])
def test_figure_suite_excluded_and_dry_run_controls(tmp_path, monkeypatch, mode):
    from types import SimpleNamespace
    from mamey import render_all_figures as subject
    from mamey import chatgpt_commands

    pkg = _synthetic_aggregate_package(tmp_path)

    def forbidden(_args):
        pytest.fail("excluded/dry-run child must not execute")

    monkeypatch.setattr(chatgpt_commands, "render_figures_command", forbidden)
    monkeypatch.setattr(subject, "figure_stack_preflight", lambda: (True, "synthetic preflight"))
    args = SimpleNamespace(package=str(pkg), include="figure-suite",
                           exclude="figure-suite" if mode == "exclude" else None,
                           all_sets=False, workbook=None, top_n=10, fail_fast=False,
                           dry_run=mode == "dry-run")
    assert subject.render_all_figures_command(args) == 0
    receipt = pkg / "render_all_figures_summary.json"
    if mode == "dry-run":
        assert not receipt.exists()
        summary = subject.render_all(pkg, include=["figure-suite"], dry_run=True)
        assert summary["sets"] == {"figure-suite": {"status": "DRY_RUN"}}
        assert summary["completion_state"] == "DRY_RUN"
    else:
        summary = json.loads(receipt.read_text(encoding="utf-8"))
        assert summary["requested"] == []
        assert summary["sets"] == {}
        assert summary["ok"] is True
        assert summary["completion_state"] == "PASS"
