from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "refresh_literature_atlas.py"


def build_store(path: Path) -> str:
    exact = "AS-1 / NODE_7_length_9000_cov_42.0 / region001 / BGC001"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        create table metadata(key text primary key, value text);
        create table current_locus(
            strain text, bgc_alias text, exact_identity text,
            manifest_sha256 text, manifest_path text
        );
        create table owner_record(
            exact_identity text, owner_state text, binding_state text, source_path text
        );
        create table locus_binding(exact_identity text, sha256 text);
        create table document(sha256 text, report_kind text, format text);
        """
    )
    connection.execute(
        "insert into metadata values (?,?)",
        ("authority_ceiling", "HISTORICAL_REVIEW_ONLY_NOT_CURRENT_EVIDENCE"),
    )
    connection.execute(
        "insert into current_locus values (?,?,?,?,?)",
        ("AS-1", "BGC001", exact, "a" * 64, "portable/manifest.json"),
    )
    connection.execute(
        "insert into owner_record values (?,?,?,?)",
        (exact, "CURRENT_REVIEW", "EXACT", "portable/card.md"),
    )
    connection.commit()
    connection.close()
    return exact


def run_tool(tmp_path: Path, markdown: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    legacy = tmp_path / "legacy" / "AS-1"
    legacy.mkdir(parents=True)
    (legacy / "report.md").write_text(markdown, encoding="utf-8")
    store = tmp_path / "evidence.sqlite"
    build_store(store)
    output = tmp_path / "output"
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--legacy-strain-reports",
            str(legacy.parent),
            "--evidence-store",
            str(store),
            "--output-root",
            str(output),
            "--artifact-tag",
            "FIXTURE_R001",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed, output


def test_refresh_emits_complete_exact_identity(tmp_path: Path) -> None:
    completed, output = run_tool(
        tmp_path,
        "# Legacy\n\n## Rank 1: AS-1 BGC001 - comparator family\n\nHistorical analysis.\n",
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output / "REFRESH_SUMMARY.json").read_text())
    assert summary["reports_generated"] == 1
    index = (output / "REFRESH_INDEX.tsv").read_text()
    assert "source_markdown_sha256" in index
    assert "source_docx_sha256" in index
    report = next((output / "strain_reports" / "AS-1").glob("*.md")).read_text()
    assert "AS-1 / NODE_7_length_9000_cov_42.0 / region001 / BGC001" in report
    assert "CURRENT_REVIEW / EXACT / portable/card.md" in report
    assert "## Rank 1: AS-1 BGC001" not in report


def test_refresh_withholds_entire_report_when_one_rank_is_unbound(tmp_path: Path) -> None:
    completed, output = run_tool(
        tmp_path,
        "# Legacy\n\n"
        "## Rank 1: AS-1 BGC001 - bound family\n\nHistorical analysis.\n\n"
        "## Rank 2: AS-1 BGC002 - unbound family\n\nHistorical analysis.\n",
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output / "REFRESH_SUMMARY.json").read_text())
    assert summary["reports_generated"] == 0
    assert summary["reports_withheld"] == 1
    assert not (output / "strain_reports").exists()
    holds = (output / "UNBOUND_REPORT_HOLDS.tsv").read_text()
    assert "REPORT_WITHHELD_UNBOUND_CURRENT_LOCI" in holds
    assert "2" in holds


def test_output_must_be_outside_immutable_legacy_root(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy" / "AS-1"
    legacy.mkdir(parents=True)
    (legacy / "report.md").write_text(
        "## Rank 1: AS-1 BGC001 - family\n", encoding="utf-8"
    )
    store = tmp_path / "evidence.sqlite"
    build_store(store)
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--legacy-strain-reports",
            str(legacy.parent),
            "--evidence-store",
            str(store),
            "--output-root",
            str(legacy.parent / "new"),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode != 0
    assert "outside the immutable legacy report root" in completed.stderr
