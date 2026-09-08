"""Typed, user-visible issue and correction logging for sealed packages.

The historical ``issue_log.md`` is retained as the readable front door.  This
module adds machine-readable JSONL and TSV siblings and a provenance field that
states whether terminology or a rule came from a source, a standard, the user,
the software, or a locally proposed convention.

The log is an engineering and workflow surface.  It does not turn a warning
into biological evidence and it does not make release or publication decisions.
"""

from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


SEVERITIES = frozenset({"INFO", "WARN", "ERROR", "BLOCKING"})
CATEGORIES = frozenset({
    "SOFTWARE_ERROR",
    "VALIDATION_FAILURE",
    "EVIDENCE_HOLD",
    "DEGRADATION",
    "DESIGN_OR_INTERPRETATION_CORRECTION",
    "PRIVACY_HOLD",
    "OTHER",
})
ORIGIN_CLASSES = frozenset({
    "SOURCE_DERIVED",
    "ESTABLISHED_STANDARD",
    "USER_DECLARED",
    "SOFTWARE_REPORTED",
    "CODEX_PROPOSED",
    "UNCLASSIFIED",
})
STATUSES = frozenset({"OPEN", "HELD", "CORRECTED", "RESOLVED"})


@dataclass(frozen=True)
class IssueEvent:
    """One issue with explicit provenance and disposition.

    ``origin_class=CODEX_PROPOSED`` is required for a non-source, non-standard
    label, threshold, score, category, or heuristic proposed during an assisted
    workflow.  This makes local inventions visible instead of letting them look
    like established scientific conventions.
    """

    severity: str
    category: str
    summary: str
    stage: str = "UNSPECIFIED"
    origin_class: str = "UNCLASSIFIED"
    status: str = "OPEN"
    impact: str = ""
    correction: str = ""
    source_locator: str = ""
    user_visible: bool = True

    def validated(self) -> "IssueEvent":
        severity = str(self.severity).strip().upper()
        category = str(self.category).strip().upper()
        origin = str(self.origin_class).strip().upper()
        status = str(self.status).strip().upper()
        if severity not in SEVERITIES:
            raise ValueError(f"Unknown issue severity: {severity!r}")
        if category not in CATEGORIES:
            raise ValueError(f"Unknown issue category: {category!r}")
        if origin not in ORIGIN_CLASSES:
            raise ValueError(f"Unknown issue origin_class: {origin!r}")
        if status not in STATUSES:
            raise ValueError(f"Unknown issue status: {status!r}")
        if not str(self.summary).strip():
            raise ValueError("Issue summary is required")
        return IssueEvent(
            severity=severity,
            category=category,
            summary=str(self.summary).strip(),
            stage=str(self.stage or "UNSPECIFIED").strip(),
            origin_class=origin,
            status=status,
            impact=str(self.impact or "").strip(),
            correction=str(self.correction or "").strip(),
            source_locator=str(self.source_locator or "").strip(),
            user_visible=bool(self.user_visible),
        )


def _legacy_event(value: str) -> IssueEvent:
    """Map an existing free-text issue into the typed surface without guessing facts."""
    text = str(value).strip()
    upper = text.upper()
    severity = "WARN"
    if "[BLOCKING]" in upper or upper.startswith("BLOCKING"):
        severity = "BLOCKING"
    elif "[ERROR]" in upper or upper.startswith("ERROR"):
        severity = "ERROR"
    elif "[INFO]" in upper or upper.startswith("INFO"):
        severity = "INFO"

    if any(token in upper for token in ("VALIDATION", "CHECKSUM", "GATE FAIL", "MISMATCH")):
        category = "VALIDATION_FAILURE"
    elif any(token in upper for token in ("NOT RUN", "NOT RETURNED", "UNBOUND", "MISSING EVIDENCE")):
        category = "EVIDENCE_HOLD"
    elif any(token in upper for token in ("SKIPPED", "DEGRADED", "UNAVAILABLE", "TIMEOUT")):
        category = "DEGRADATION"
    else:
        category = "SOFTWARE_ERROR" if severity in {"ERROR", "BLOCKING"} else "OTHER"

    return IssueEvent(
        severity=severity,
        category=category,
        summary=text,
        origin_class="SOFTWARE_REPORTED",
    ).validated()


def normalize_issues(issues: Iterable[str | Mapping[str, Any] | IssueEvent]) -> list[IssueEvent]:
    normalized: list[IssueEvent] = []
    for value in issues or []:
        if isinstance(value, IssueEvent):
            event = value.validated()
        elif isinstance(value, Mapping):
            event = IssueEvent(**dict(value)).validated()
        else:
            event = _legacy_event(str(value))
        normalized.append(event)
    return normalized


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _rows(events: list[IssueEvent]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        row = {"event_id": f"ISSUE-{index:04d}", **asdict(event)}
        rows.append(row)
    return rows


def write_issue_surfaces(
    package_dir: str | Path,
    issues: Iterable[str | Mapping[str, Any] | IssueEvent],
    *,
    terminal_status: str = "",
) -> dict[str, Any]:
    """Write synchronized Markdown, TSV, and JSONL issue surfaces.

    Rewriting from the authoritative in-memory collection is deliberate: all
    three files represent one terminal snapshot and receive stable ordinal IDs.
    Callers may invoke this before and after sealing; the three filenames must
    therefore be listed as mutable receipts by the package checksum policy.
    """
    root = Path(package_dir)
    events = normalize_issues(issues)
    rows = _rows(events)

    jsonl = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    _atomic_text(root / "issue_log.jsonl", jsonl)

    columns = [
        "event_id", "severity", "category", "stage", "origin_class", "status",
        "summary", "impact", "correction", "source_locator", "user_visible",
    ]
    stream = io.StringIO(newline="")
    writer = _SafeDictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    _atomic_text(root / "issue_log.tsv", stream.getvalue())

    lines = [
        "# Issue and Correction Log",
        "",
        "This user-visible log distinguishes software errors, validation failures, evidence holds, degradation events, privacy holds, and corrected design or interpretation mistakes.",
        "",
        "`origin_class` identifies whether a term or rule is source-derived, an established standard, user-declared, software-reported, or explicitly proposed by Codex. A locally proposed convention must not be presented as an established meaning.",
        "",
        f"Terminal status: `{terminal_status or 'NOT_STAMPED'}`. Recorded events: {len(rows)}.",
        "",
    ]
    if not rows:
        lines.extend(["- No issues recorded.", ""])
    else:
        for row in rows:
            lines.extend([
                f"## {row['event_id']} - {row['severity']} - {row['category']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Stage: `{row['stage']}`",
                f"- Origin: `{row['origin_class']}`",
                f"- Summary: {row['summary']}",
            ])
            if row["impact"]:
                lines.append(f"- Impact: {row['impact']}")
            if row["correction"]:
                lines.append(f"- Correction: {row['correction']}")
            if row["source_locator"]:
                lines.append(f"- Source locator: `{row['source_locator']}`")
            lines.append("")
    lines.extend([
        "The presence or absence of a logged event is a workflow statement, not biological evidence. Missing, unbound, or unreturned evidence is not biological absence.",
        "",
    ])
    _atomic_text(root / "issue_log.md", "\n".join(lines))

    return {
        "schema_version": "sapote_issue_log_v1",
        "event_count": len(rows),
        "open_or_held_count": sum(row["status"] in {"OPEN", "HELD"} for row in rows),
        "blocking_count": sum(row["severity"] == "BLOCKING" for row in rows),
        "files": ["issue_log.md", "issue_log.tsv", "issue_log.jsonl"],
    }


def proposed_convention_issue(
    summary: str,
    *,
    stage: str,
    impact: str = "",
    correction: str = "",
    status: str = "OPEN",
) -> IssueEvent:
    """Create an explicitly disclosed Codex-proposed convention event."""
    return IssueEvent(
        severity="WARN",
        category="DESIGN_OR_INTERPRETATION_CORRECTION",
        summary=summary,
        stage=stage,
        origin_class="CODEX_PROPOSED",
        status=status,
        impact=impact,
        correction=correction,
    ).validated()
