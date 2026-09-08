#!/usr/bin/env python3
"""Preflight Markdown before PDF rendering.

Boss-facing PDFs must not receive raw wide pipe tables. Pandoc/LaTeX will often
try to render them anyway, producing overlapping/clipped text while still leaving
a PDF on disk. This preflight routes wide tables to a sidecar appendix and leaves
a readable placeholder in the boss Markdown.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple

import sys as _sys
# v9.7.405: this tool is ALSO imported as `tools.sapote_md_preflight` by the test suite (package
# import, tools/ not on sys.path), so the sibling import needs its own directory on the path.
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wbio import atomic_dump_json, atomic_write_text  # noqa: E402

try:
    from mamey.render_safe import has_forbidden_render_string
except ImportError:  # pragma: no cover - allows tool use from an incomplete unpacked script path
    # BC2-398 (v9.7.398): the canonical mamey/render_safe.py check matches both "nan" and
    # "NaN" explicitly (pandas' DataFrame.to_string()/.to_markdown() render missing values as
    # capitalized "NaN" by default) plus "None". This fallback's bare `\bnan\b` was
    # case-sensitive and matched only lowercase "nan" — the exact common case a boss-facing
    # PDF preflight exists to catch. Mirrors the canonical policy's casing exactly.
    # CODEX_390: narrowed from bare `except Exception` to `except ImportError` so an
    # unrelated defect inside mamey.render_safe is not silently swallowed by this fallback.
    def has_forbidden_render_string(text: str) -> bool:
        return bool(re.search(r"\bnp\.|numpy\.|\b(?:nan|NaN)\b|\bNone\b", text or ""))


def _is_pipe_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _split_tables(lines: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if not _is_pipe_table_line(lines[i]):
            i += 1
            continue
        start = i
        while i < len(lines) and _is_pipe_table_line(lines[i]):
            i += 1
        if i - start >= 2:
            ranges.append((start, i))
    return ranges


def _table_cols(line: str) -> int:
    return max(0, len([p for p in line.strip().strip("|").split("|")]))


def _wide_table(lines: list[str], *, max_cols: int, max_line: int) -> bool:
    if not lines:
        return False
    return _table_cols(lines[0]) > max_cols or max(len(x) for x in lines) > max_line


def preflight_markdown(src: str, *, profile: str = "boss", max_cols: int = 6, max_line: int = 118) -> tuple[str, str, list[dict]]:
    """Return sanitized markdown, appendix markdown, and machine-readable findings."""
    lines = src.splitlines()
    table_ranges = _split_tables(lines)
    findings: list[dict] = []
    appendix_parts = ["# Routed Wide Tables Appendix", "", "These tables were omitted from the boss-facing PDF because they exceed the readability threshold.", ""]
    out: list[str] = []
    cursor = 0
    table_no = 0
    for start, end in table_ranges:
        out.extend(lines[cursor:start])
        tbl = lines[start:end]
        table_no += 1
        cols = _table_cols(tbl[0])
        max_len = max(len(x) for x in tbl)
        if profile == "boss" and _wide_table(tbl, max_cols=max_cols, max_line=max_line):
            title = f"Wide table {table_no}"
            findings.append({"type": "wide_table_routed", "table": table_no, "cols": cols, "max_line": max_len, "line_start": start + 1})
            out.extend([
                "",
                f"> **Table routed to appendix/workbook:** {title} has {cols} columns and/or long cells, so it is not rendered inline in the boss PDF.",
                "> Use the technical appendix, workbook, or CSV sidecar for the full table.",
                "",
            ])
            appendix_parts.extend([f"## {title}", "", *tbl, ""])
        else:
            out.extend(tbl)
        cursor = end
    out.extend(lines[cursor:])
    text = "\n".join(out) + "\n"
    if has_forbidden_render_string(text):
        findings.append({"type": "forbidden_render_string", "message": "raw computational value leaked into boss markdown"})
    appendix = "\n".join(appendix_parts) + "\n"
    return text, appendix, findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_md")
    ap.add_argument("output_md")
    ap.add_argument("--profile", default="boss", choices=["boss", "technical"])
    ap.add_argument("--appendix-md", default=None)
    ap.add_argument("--qa-json", default=None)
    ap.add_argument("--max-cols", type=int, default=6)
    ap.add_argument("--max-line", type=int, default=118)
    ns = ap.parse_args(argv)
    src = Path(ns.input_md).read_text(encoding="utf-8")
    text, appendix, findings = preflight_markdown(src, profile=ns.profile, max_cols=ns.max_cols, max_line=ns.max_line)
    forbidden = any(f["type"] == "forbidden_render_string" for f in findings)
    atomic_write_text(ns.output_md, text)
    if ns.appendix_md:
        atomic_write_text(ns.appendix_md, appendix)
    if ns.qa_json:
        atomic_dump_json({"status": "FAIL" if forbidden else "PASS", "findings": findings},
                         ns.qa_json, indent=2)
    return 1 if forbidden else 0


if __name__ == "__main__":
    raise SystemExit(main())
