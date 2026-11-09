"""User-visible engine text carries no version chatter, assistant ritual or British spelling.

Covered: the run banner, the MULTIBATCH and OVER_MERGE_CANDIDATES issue text, the
ANALYSIS_FORWARD worklist, the output checklist row, the master workbook Missingness row and
`run --help`.
"""
from __future__ import annotations

import inspect
import re
import subprocess
import sys
from pathlib import Path

from mamey import cli, master_workbook, output_checklist, package_addons

BUNDLE = Path(__file__).resolve().parents[1]


def test_run_banner_names_the_current_judgment_layer():
    assert "Mamey v1.2 prompt" not in cli.RUN_STATEMENT
    assert "Sapote judgment layer" in cli.RUN_STATEMENT


def test_issue_text_has_no_llm_batches_and_quotes_the_antismash_kind():
    source = inspect.getsource(cli)
    assert "LLM batches" not in source
    assert "Mode B review is easier in about {batches} batches" in source
    assert "_multibatch_issue(_mb_reason, _batches, _rggmci_high)" in source
    assert "neighbouring/interleaved" not in source
    assert 'antiSMASH kind \\"neighbouring\\"' in source  # antiSMASH's own token, quoted


def test_worklist_has_no_trigger_ritual_or_stale_section_count():
    source = inspect.getsource(package_addons.write_analysis_forward)
    assert "Trigger:" not in source
    assert "Compilation order:" not in source
    assert "\\u00a71\\u2013\\u00a78" not in source and "§1–§8" not in source
    checklist = inspect.getsource(output_checklist)
    assert "\\u00a71\\u2013\\u00a78" not in checklist and "§1–§8" not in checklist


def test_master_workbook_missingness_row_is_current():
    source = inspect.getsource(master_workbook)
    assert "Mamey v1.2 prompt" not in source
    assert "Run standard or gold judgment session" not in source


def test_run_help_has_no_version_chatter_or_british_spelling():
    out = subprocess.run([sys.executable, "mamey_run.py", "run", "--help"], cwd=BUNDLE,
                         capture_output=True, text=True, timeout=120).stdout
    assert "--capped-session" in out
    assert not re.search(r"\bv9\.7\.\d+", out), out
    assert "P0" not in out.replace("CP0", "")
    assert "Legacy no-op" not in out
    assert "BR6" not in out
    for word in ("neighbour", "honour", "homologue"):
        assert word not in out


def test_top_level_help_has_no_version_tags():
    out = subprocess.run([sys.executable, "mamey_run.py", "--help"], cwd=BUNDLE,
                         capture_output=True, text=True, timeout=120).stdout
    assert "emit-modeb-template" in out
    assert not re.search(r"\bv9\.7\.\d+", out), [l for l in out.splitlines() if re.search(r"v9\.7\.", l)]
