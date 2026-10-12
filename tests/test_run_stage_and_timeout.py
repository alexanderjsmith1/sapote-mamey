"""audit P1 — stage logging, bounded-timeout fallback helper, batch-plan writer."""
import os, time, pathlib
import pytest
from mamey import cli


def test_with_timeout_returns_fast():
    assert cli._with_timeout(5, lambda: 42) == 42


def test_with_timeout_raises_on_overrun():
    if not hasattr(__import__("signal"), "SIGALRM"):
        pytest.skip("no SIGALRM")
    with pytest.raises(cli._BoundedTimeout):
        cli._with_timeout(1, lambda: time.sleep(3))


def test_stage_quiet_env(capsys):
    os.environ["MAMEY_QUIET_STAGES"] = "1"
    try:
        cli._stage("should be silent")
        assert "should be silent" not in capsys.readouterr().err
    finally:
        del os.environ["MAMEY_QUIET_STAGES"]


def test_batch_plan_written(tmp_path):
    cli._write_batch_plan(tmp_path, "TESTX", "smoke", "not supplied")
    p = tmp_path / "TESTX_BATCH_PLAN.md"
    assert p.exists() and "intake_harness.py" in p.read_text() and "--resume" in p.read_text()


def test_start_here_written(tmp_path):
    # v9.7.161: smoke removed — START_HERE header is unconditional (gold is the only mode).
    assert cli._write_start_here(tmp_path, "TESTY", "gold", "PASS", 71, 31, 25, 15, 47.25, "POOR") is True
    p = tmp_path / "START_HERE.md"
    t = p.read_text()
    assert p.exists()
    assert "EXTRACTION COMPLETE" in t and "JUDGMENT PENDING" in t
    assert "71 raw BGCs" in t and "31 Interior / 25 Edge / 15 Full-contig" in t
    assert "corrected 47.25" in t and "Assembly tier: POOR" in t
    assert "mode=gold, validation=PASS" in t
    assert "Extraction validation does not establish" in t
    assert "register separately from extraction and figure review" in t
    assert "a full Mode B card, DAPR, white paper or guide; those are optional authored formats" in t
    assert "Select the question and figure roster" in t
    assert "strain / full node-or-contig / region / BGC alias" in t
    assert "TESTY_2_inventory.csv" in t and "gold_figures/" in t and "locus_maps/" in t
    command = "python mamey_run.py render-figures --package <working-package-copy> --outdir <fresh-review-directory> --figure-set standard"
    assert command in t and "refresh integrity records" in t
    assert "docs/FIGURES_START_HERE.md" in t and "docs/EVIDENCE_TO_REPORT.md" in t
    assert "actual execution and visual-review evidence" in t and "unresolved holds" in t
    assert "A rendered image alone does not establish a scientific conclusion" in t
    assert t.index("Select the question and figure roster") < t.index(command) < t.index("Optional authored format")
    assert "Run full Sapote analysis on TESTY" in t and "Choose its named card/profile workflow" in t
    assert "Trigger the judgment layer" not in t
    assert "TESTY_BATCH_PLAN.md" in t and "TESTY_4A_RGGMCI_ranked_pairs.csv" in t
    root = pathlib.Path(__file__).resolve().parents[1]
    assert (root/"docs/FIGURES_START_HERE.md").is_file()
    assert (root/"docs/EVIDENCE_TO_REPORT.md").is_file()


def test_no_stale_v5_trigger_language():
    import pathlib, re
    root = pathlib.Path(__file__).resolve().parent.parent
    hits = []
    for p in list((root / "mamey").rglob("*.py")) + list((root / "tools").rglob("*.py")):
        if "Run v5 analysis" in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(p.name)
    assert not hits, f"stale 'Run v5 analysis' trigger in: {hits}"


def test_label_is_accession():
    acc = ["NZ_QHHY00000000.1", "QHHY00000000", "GCA_009862675.1", "GCF_000203835.1", "NC_003888.3"]
    names = ["SID-XXX", "S. coelicolor", "WWKC", "AGLAU", "Streptomyces-A1", "lab-strain-705"]
    for a in acc:
        assert cli._label_is_accession(a), f"{a} should be accession"
    for n in names:
        assert not cli._label_is_accession(n), f"{n} should be a strain name"
