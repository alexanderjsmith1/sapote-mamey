#!/usr/bin/env python3
"""manuscript_revision.py — revise a multi-document manuscript from Markdown sources: staged find/replace edits, a Word change log, an answerable revision ledger and asks-only rounds.

Workflow and rules: docs/MANUSCRIPT_REVISION_WORKFLOW.md. Subcommands:

    apply          apply find-once/replace edits from a JSON file; all-or-nothing per document; append-only JSONL record
    changelog      before/after Word table from the change record, trimmed to the changed stretch
    ledger         landscape Word ledger: Part A author notes, Part B reviewer findings (FIX/CHECK/RULE), Part C packages
    read-answers   extract the answer column of an answered ledger; refuse when any other cell changed
    asks           asks-only round: drop answered, clear, FIX and CHECK rows
    check-numbers  flag edits that introduce a number found nowhere in the document or a named source file
    scan-names     flag internal names (paths, run numbers, builds, data files, configured names) in prose

Inputs are plain TSV, Markdown tables or JSON with the columns documented in the workflow guide. Exit codes:
0 clean, 1 findings or refused edits, 2 bad input or a refused read-back, 3 python-docx missing for a Word step.
The tool never edits a document except through `apply` without `--dry-run`.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text  # noqa: E402

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

import _manuscript_revision_docx as mdocx  # noqa: E402

_OUT = _get_logger(__name__)

EXIT_OK, EXIT_FINDINGS, EXIT_INPUT, EXIT_NO_DOCX = 0, 1, 2, 3
FINDING_TYPES = ("FIX", "CHECK", "RULE")
NOTE_COLUMNS = ("id", "location", "note", "action", "status")
FINDING_COLUMNS = ("id", "group", "location", "finding", "type", "recommendation", "overlap")
PACKAGE_COLUMNS = ("id", "title", "covers", "codes", "recommendation")
RESPONSE_COLUMNS = ("id", "status", "text")
EDIT_KEYS = ("doc", "find", "replace")


class InputError(ValueError):
    """A refused input: missing file, missing column, malformed edit or unsafe path."""


# ----------------------------------------------------------------------------------------------- table inputs

def _split_md_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells, cur, i = [], [], 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if body[i] == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(body[i])
        i += 1
    cells.append("".join(cur).strip())
    return cells


def read_table(path, required: tuple[str, ...]) -> list[dict[str, str]]:
    """Rows of a TSV (header line first) or of the first Markdown table in a .md file, keyed by lower-case header.

    Every name in `required` must be a header; extra columns are kept. Blank rows are skipped.
    """
    p = Path(path)
    if not p.is_file():
        raise InputError(f"input not found: {p}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".md", ".markdown"):
        lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
        if not lines:
            raise InputError(f"{p}: no Markdown table")
        header = [h.lower() for h in _split_md_row(lines[0])]
        body = [ln for ln in lines[1:] if not re.fullmatch(r"\|?[\s:|-]+\|?", ln.strip())]
        raw = [_split_md_row(ln) for ln in body]
    else:
        reader = list(csv.reader(io.StringIO(text), delimiter="\t"))
        if not reader:
            raise InputError(f"{p}: empty table")
        header = [h.strip().lower() for h in reader[0]]
        raw = reader[1:]
    missing = [c for c in required if c not in header]
    if missing:
        raise InputError(f"{p}: missing column(s) {', '.join(missing)}; header is {', '.join(header)}")
    rows = []
    for vals in raw:
        if not any(v.strip() for v in vals):
            continue
        vals = (list(vals) + [""] * len(header))[:len(header)]
        rows.append({h: v.strip() for h, v in zip(header, vals)})
    return rows


def write_tsv(path, header, rows) -> None:
    buf = io.StringIO()
    w = _SafeWriter(buf, delimiter="\t", lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    atomic_write_text(path, buf.getvalue())


# ----------------------------------------------------------------------------------------------- apply

def load_edits(path) -> list[dict]:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"edit file not found: {p}")
    try:
        edits = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{p}: not valid JSON ({exc})") from exc
    if not isinstance(edits, list):
        raise InputError(f"{p}: expected a JSON list of edits")
    for n, e in enumerate(edits, 1):
        if not isinstance(e, dict) or any(not isinstance(e.get(k), str) for k in EDIT_KEYS):
            raise InputError(f"{p}: edit {n} needs string fields doc, find and replace")
        if not e["find"]:
            raise InputError(f"{p}: edit {n} has an empty find")
    return edits


def doc_path(root: Path, doc: str) -> Path:
    """Resolve an edit's document inside the working copy; refuse absolute paths and escapes."""
    rel = Path(doc)
    if rel.is_absolute() or ".." in rel.parts:
        raise InputError(f"document path must be relative to the working copy: {doc}")
    p = root / rel
    if not p.is_file():
        raise InputError(f"document not found in the working copy: {doc}")
    return p


def plan_edits(root: Path, edits: list[dict]):
    """Apply edits in memory. Returns (new texts by doc, applied, already applied, refused with match counts).

    Per document, edits run in file order against the text as changed by the earlier edits. One refused edit
    refuses the whole document: none of its edits count as applied and its text is not returned.
    """
    by_doc: dict[str, list[dict]] = {}
    for e in edits:
        by_doc.setdefault(e["doc"], []).append(e)
    texts, applied, already, refused = {}, [], [], []
    for doc, es in by_doc.items():
        with open(doc_path(root, doc), encoding="utf-8", newline="") as fh:
            t = fh.read()
        doc_applied, ok = [], True
        for e in es:
            n = t.count(e["find"])
            if n == 1:
                t = t.replace(e["find"], e["replace"])
                doc_applied.append(e)
            elif n == 0 and e["replace"] and e["replace"] in t:
                already.append(e)
            else:
                refused.append((e, n))
                ok = False
        if ok:
            applied.extend(doc_applied)
            if doc_applied:
                texts[doc] = t
    return texts, applied, already, refused


def cmd_apply(a) -> int:
    root = Path(a.root)
    edits = load_edits(a.edits)
    record = Path(a.record) if a.record else root / "CHANGES.jsonl"
    texts, applied, already, refused = plan_edits(root, edits)
    if not a.dry_run:
        for doc, t in texts.items():
            atomic_write_text(doc_path(root, doc), t)
        if applied:
            stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(record, "a", encoding="utf-8") as fh:
                for e in applied:
                    fh.write(json.dumps({**e, "applied": stamp}, ensure_ascii=False) + "\n")
    _OUT.info(f"applied {len(applied)}, already applied {len(already)}, refused {len(refused)}"
         + (" (dry run, nothing written)" if a.dry_run else ""))
    for e, n in refused:
        _OUT.info(f"  REFUSED ({n} matches) {e['doc']} {e.get('ledger', '')} {e.get('row', '')}: {e['find'][:90]!r}")
    if refused:
        _OUT.info("  every edit in a refused document was held back; that document is unchanged")
    return EXIT_FINDINGS if refused else EXIT_OK


# ----------------------------------------------------------------------------------------------- changelog

def trim(a: str, b: str, ctx: int = 60) -> tuple[str, str]:
    """The changed stretch of a and b, with up to ctx characters of shared text either side."""
    p = 0
    while p < min(len(a), len(b)) and a[p] == b[p]:
        p += 1
    s = 0
    while s < min(len(a), len(b)) - p and a[-1 - s] == b[-1 - s]:
        s += 1
    lo = max(0, p - ctx)
    pre = "…" if lo > 0 else ""

    def cut(x: str) -> str:
        hi = len(x) - max(0, s - ctx)
        return pre + x[lo:hi] + ("…" if hi < len(x) else "")
    return cut(a), cut(b)


def read_record(path, first: int = 1) -> list[tuple[int, dict]]:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"change record not found: {p}")
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if i < first or not line.strip():
            continue
        try:
            out.append((i, json.loads(line)))
        except json.JSONDecodeError as exc:
            raise InputError(f"{p}: line {i} is not JSON ({exc})") from exc
    return out


def doc_labels(path) -> dict[str, str]:
    if not path:
        return {}
    return {r["prefix"]: r["label"] for r in read_table(path, ("prefix", "label"))}


def label_for(doc: str, labels: dict[str, str]) -> str:
    """Longest label prefix that starts the document name, else the document name itself."""
    name = Path(doc).name
    best = max((k for k in labels if name.startswith(k)), key=len, default=None)
    return labels[best] if best else doc


def cmd_changelog(a) -> int:
    recs = read_record(a.record, a.first)
    labels = doc_labels(a.doc_labels)
    d = mdocx.new_landscape_document(font=a.font, size_pt=a.font_size, margin_in=0.6)
    d.add_heading(a.title, 1)
    if a.intro:
        d.add_paragraph(a.intro)
    last = recs[-1][0] if recs else a.first
    d.add_paragraph(f"Records read: {len(recs)} (record lines {a.first} to {last}). Before and After show the changed "
                    "stretch with shared text trimmed. Record is the line number in the change record.")
    rows = []
    for n, (line, r) in enumerate(recs, 1):
        before, after = trim(r["find"], r["replace"], a.context)
        why = re.sub(r"\s+", " ", r.get("why", ""))
        tag = " ".join(x for x in (r.get("ledger", ""), r.get("row", "")) if x)
        rows.append([str(n), label_for(r["doc"], labels), before, after, why + (f" [{tag}]" if tag else ""), str(line)])
    mdocx.add_table(d, ["#", "Document", "Before", "After", "Why / ledger row", "Record"], [.3, 1.2, 3.1, 3.1, 1.6, .5], rows)
    d.save(a.out)
    _OUT.info(f"{a.out}: {len(recs)} change rows")
    return EXIT_OK


# ----------------------------------------------------------------------------------------------- ledger

def is_ask(note: dict) -> bool:
    status = note.get("status", "").strip().upper()
    return status == "ASK" or "[?]" in note.get("note", "") + note.get("action", "")


def load_findings(paths) -> list[dict]:
    rows = []
    for path in paths or []:
        for r in read_table(path, FINDING_COLUMNS):
            r["type"] = r["type"].upper()
            if r["type"] not in FINDING_TYPES:
                raise InputError(f"{path}: finding {r['id']} has type {r['type']!r}; use FIX, CHECK or RULE")
            rows.append(r)
    return rows


def cross_links(notes: list[dict], findings: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Pairs of (note, finding) that cover the same passage, read from either side.

    A finding's `overlap` cell names note ids; a note's text or action may name finding ids. Each pair is shown on both rows.
    """
    note_ids = {n["id"] for n in notes}
    find_ids = {f["id"] for f in findings}
    pairs = set()
    for f in findings:
        for tok in re.split(r"[\s,;]+", f.get("overlap", "")):
            if tok in note_ids:
                pairs.add((tok, f["id"]))
    for n in notes:
        blob = " ".join(n.get(k, "") for k in ("note", "action", "location"))
        for fid in find_ids:
            if re.search(rf"(?<![\w-]){re.escape(fid)}(?![\w-])", blob):
                pairs.add((n["id"], fid))
    by_note: dict[str, list[str]] = {}
    by_finding: dict[str, list[str]] = {}
    for nid, fid in sorted(pairs):
        by_note.setdefault(nid, []).append(fid)
        by_finding.setdefault(fid, []).append(nid)
    return by_note, by_finding


def _groups(findings: list[dict]) -> list[str]:
    seen = []
    for f in findings:
        if f["group"] not in seen:
            seen.append(f["group"])
    return seen


def cmd_ledger(a) -> int:
    notes = read_table(a.notes, NOTE_COLUMNS) if a.notes else []
    findings = load_findings(a.findings)
    packages = read_table(a.packages, PACKAGE_COLUMNS) if a.packages else []
    by_note, by_finding = cross_links(notes, findings)
    au, rv, ans = a.author_label, a.reviewer_label, a.answer_header
    n_ask = sum(is_ask(n) for n in notes)
    kinds = {k: sum(f["type"] == k for f in findings) for k in FINDING_TYPES}
    d = mdocx.new_landscape_document(font=a.font, size_pt=a.font_size)
    d.add_heading(a.title, 1)
    d.add_paragraph(
        f"Part A holds the {au.lower()}'s notes ({len(notes)} rows; {n_ask} marked ASK need an answer, the rest are applied as written "
        f"unless the answer says otherwise). Part B holds the {rv.lower()} findings ({len(findings)} rows): FIX {kinds['FIX']}, "
        f"CHECK {kinds['CHECK']}, RULE {kinds['RULE']}. FIX is a wording change made unless the answer is 'no'. CHECK means the "
        "record is looked up first, then the text changes. RULE is the author's call, with a recommendation. "
        f"Part C holds {len(packages)} revision packages. Where a note and a finding cover the same passage, each row names the other. "
        f"Write only in the {ans} column. R = take the recommendation. Blank on a FIX or a clear note = go ahead.")
    d.add_heading(f"Part A. {au} notes", 2)
    rows = []
    for n in notes:
        tag = "ASK" if is_ask(n) else "clear"
        link = by_note.get(n["id"])
        rows.append([n["id"], n["location"], n["note"],
                     f"[{tag}] {n['action']}" + (f"\nSame passage: {', '.join(link)}" if link else ""), ""])
    mdocx.add_table(d, ["#", "Location", "Note (as read)", "Proposed action", ans], [.6, 1.4, 3.4, 3.0, 1.6], rows)
    d.add_heading(f"Part B. {rv} findings", 2)
    for g in _groups(findings):
        d.add_heading(g or "Ungrouped", 3)
        rows = []
        for f in (x for x in findings if x["group"] == g):
            link = by_finding.get(f["id"])
            rows.append([f["id"], f["finding"] + (f"\n({f['location']})" if f["location"] else ""), f["type"],
                         f["recommendation"] + (f"\nSame passage: {', '.join(link)}" if link else ""), ""])
        mdocx.add_table(d, ["#", "Finding", "Type", "Recommendation", ans], [.8, 3.6, .6, 3.4, 1.6], rows)
    d.add_heading(f"Part C. {rv} revision packages", 2)
    mdocx.add_table(d, ["#", "Title", "What it covers", "Codes", "Recommendation", ans], [.7, 1.4, 2.6, 1.2, 2.6, 1.5],
                    [[p["id"], p["title"], p["covers"], p["codes"], p["recommendation"], ""] for p in packages])
    d.save(a.out)
    _OUT.info(f"{a.out}: notes {len(notes)} (ask {n_ask}), findings {len(findings)} {kinds}, packages {len(packages)}, "
         f"same-passage links {sum(len(v) for v in by_note.values())}")
    return EXIT_OK


# ----------------------------------------------------------------------------------------------- read-answers

def answer_column(table: list[list[str]], header: str) -> int | None:
    if not table:
        return None
    head = [c.strip() for c in table[0]]
    return len(head) - 1 - head[::-1].index(header) if header in head else None


def compare_answered(original, answered, header: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Answers by row id from `answered`, and every difference outside the answer column versus `original`."""
    t0, t1 = mdocx.read_tables(original), mdocx.read_tables(answered)
    changes: list[str] = []
    answers: list[tuple[str, str]] = []
    if len(t0) != len(t1):
        changes.append(f"table count {len(t0)} -> {len(t1)}")
        return answers, changes
    for ti, (a, b) in enumerate(zip(t0, t1), 1):
        if len(a) != len(b):
            changes.append(f"table {ti}: row count {len(a)} -> {len(b)}")
            continue
        col = answer_column(a, header)
        for ri, (ra, rb) in enumerate(zip(a, b)):
            if len(ra) != len(rb):
                changes.append(f"table {ti} row {ri}: cell count {len(ra)} -> {len(rb)}")
                continue
            for ci, (ca, cb) in enumerate(zip(ra, rb)):
                if ci == col and ri > 0:
                    continue
                if ca != cb:
                    changes.append(f"table {ti} row {ri} column {ci + 1}: {ca[:40]!r} -> {cb[:40]!r}")
            if col is not None and ri > 0 and rb[col].strip():
                answers.append((rb[0].strip(), rb[col].strip()))
    return answers, changes


def cmd_read_answers(a) -> int:
    answers, changes = compare_answered(a.original, a.answered, a.answer_header)
    if changes:
        _OUT.info(f"REFUSED: {len(changes)} cell(s) outside the {a.answer_header} column differ from the issued ledger; "
             "nothing written. Ask for the answers to be moved into the answer column.")
        for c in changes[:40]:
            _OUT.info(f"  {c}")
        return EXIT_INPUT
    write_tsv(a.out, ["id", "answer"], answers)
    _OUT.info(f"{a.out}: {len(answers)} answered rows")
    return EXIT_OK


# ----------------------------------------------------------------------------------------------- asks

def cmd_asks(a) -> int:
    notes = read_table(a.notes, NOTE_COLUMNS) if a.notes else []
    findings = load_findings(a.findings)
    packages = read_table(a.packages, PACKAGE_COLUMNS) if a.packages else []
    answered = {r["id"] for r in read_table(a.answers, ("id", "answer")) if r["answer"]} if a.answers else set()
    responses = read_table(a.responses, RESPONSE_COLUMNS) if a.responses else []
    drop_rx = re.compile(a.drop_regex, re.I) if a.drop_regex else None
    au, rv, ans = a.author_label, a.reviewer_label, a.answer_header
    need = [r for r in responses if a.need_status.upper() in r["status"].upper()]
    need_ids = {r["id"] for r in need}
    ask, dropped = [], []
    for n in notes:
        if n["id"] in answered or n["id"] in need_ids or not is_ask(n):
            continue
        if drop_rx and drop_rx.search(n["note"] + " " + n["action"]):
            dropped.append(n["id"])
            continue
        ask.append(n)
    rule = [f for f in findings if f["type"] == "RULE" and f["id"] not in answered]
    packs = [p for p in packages if p["id"] not in answered]
    total = len(need) + len(ask) + len(rule) + len(packs)
    d = mdocx.new_landscape_document(font=a.font, size_pt=a.font_size)
    d.add_heading(a.title, 1)
    d.add_paragraph(
        f"Only what needs an answer: {len(need)} details left from earlier answers, {len(ask)} {au.lower()} notes marked ASK, "
        f"{len(rule)} {rv.lower()} RULE rows and {len(packs)} packages ({total} in all). Answered rows, clear notes, and every "
        "FIX and CHECK row are off this list. Row ids match the full ledger. "
        + (f"Dropped by the configured pattern: {', '.join(dropped)}. " if dropped else "")
        + f"Write only in the {ans} column. R = take the recommendation.")
    d.add_heading("1. Details left from earlier answers", 2)
    mdocx.add_table(d, ["#", "Status", "What is still needed", ans], [.7, 1.2, 6.5, 1.6],
                    [[r["id"], r["status"], r["text"], ""] for r in need])
    d.add_heading(f"2. {au} notes marked ASK", 2)
    mdocx.add_table(d, ["#", "Location", "Note (as read)", "Recommendation", ans], [.6, 1.4, 3.4, 3.0, 1.6],
                    [[n["id"], n["location"], n["note"], n["action"], ""] for n in ask])
    d.add_heading(f"3. {rv} RULE rows", 2)
    mdocx.add_table(d, ["#", "Group", "Finding", "Recommendation", ans], [.8, 1.2, 3.2, 3.2, 1.6],
                    [[f["id"], f["group"], f["finding"] + (f"\n({f['location']})" if f["location"] else ""),
                      f["recommendation"], ""] for f in rule])
    d.add_heading(f"4. {rv} revision packages", 2)
    mdocx.add_table(d, ["#", "Title", "What it covers", "Codes", "Recommendation", ans], [.7, 1.4, 2.6, 1.2, 2.6, 1.5],
                    [[p["id"], p["title"], p["covers"], p["codes"], p["recommendation"], ""] for p in packs])
    d.save(a.out)
    _OUT.info(f"{a.out}: need {len(need)}, ask {len(ask)}, rule {len(rule)}, packages {len(packs)}, dropped {len(dropped)}")
    return EXIT_OK


# ----------------------------------------------------------------------------------------------- check-numbers

NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?")


def numbers(text: str) -> set[str]:
    return {m.rstrip(",") for m in NUMBER_RE.findall(text)}


def number_flags(root: Path, edits: list[dict], sources: list[Path]) -> list[tuple[dict, list[str]]]:
    """Edits whose replace text holds a number absent from its find text, its document and every source file."""
    pool = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sources)
    cache: dict[str, str] = {}
    out = []
    for e in edits:
        if e["doc"] not in cache:
            cache[e["doc"]] = doc_path(root, e["doc"]).read_text(encoding="utf-8")
        haystack_nums = numbers(cache[e["doc"]]) | numbers(pool)
        new = numbers(e["replace"]) - numbers(e["find"])
        missing = sorted(n for n in new if n not in haystack_nums)
        if missing:
            out.append((e, missing))
    return out


def cmd_check_numbers(a) -> int:
    edits = load_edits(a.edits)
    sources = [Path(s) for s in a.source or []]
    for s in sources:
        if not s.is_file():
            raise InputError(f"source file not found: {s}")
    flags = number_flags(Path(a.root), edits, sources)
    for e, missing in flags:
        _OUT.info(f"{e.get('row', '')}\t{e['doc']}\t{', '.join(missing)}\t{e.get('why', '')[:90]}")
    if a.out:
        write_tsv(a.out, ["row", "doc", "new_numbers", "why"],
                  [[e.get("row", ""), e["doc"], ", ".join(m), e.get("why", "")] for e, m in flags])
    _OUT.info(f"{len(edits)} edits checked; {len(flags)} introduce a number found in no document or source file")
    return EXIT_FINDINGS if flags else EXIT_OK


# ----------------------------------------------------------------------------------------------- scan-names

DEFAULT_NAME_PATTERNS = [
    ("path", r"(?:~|\.{1,2})?/(?:[\w.-]+/)+[\w.-]*|\b[A-Za-z]:\\[\w\\. -]+"),
    ("run number", r"\b[Rr]un[ _#-]?\d+\b"),
    ("build or version", r"\bv\d+\.\d+(?:\.\d+)+[\w-]*\b|\bbuild \d{6,}\w*\b"),
    ("data file", r"\b[\w.-]+\.(?:tsv|csv|jsonl?|py|sh|R|ipynb|xlsx|sqlite|zip|gbk|fna|faa|yml|yaml)\b"),
    ("snake_case name", r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b"),
]
DEFAULT_NOTE_TAG = r"[A-Z][A-Z0-9 ]*"


def load_name_patterns(path, replace: bool) -> list[tuple[str, re.Pattern]]:
    """Patterns file: one per line, `label<TAB>regex` or a bare literal word. `#` lines are comments."""
    pats = [] if replace else [(lab, re.compile(rx)) for lab, rx in DEFAULT_NAME_PATTERNS]
    if path:
        p = Path(path)
        if not p.is_file():
            raise InputError(f"patterns file not found: {p}")
        for raw in p.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if "\t" in raw:
                lab, rx = raw.split("\t", 1)
                try:
                    pats.append((lab.strip(), re.compile(rx.strip())))
                except re.error as exc:
                    raise InputError(f"{p}: bad pattern {rx!r} ({exc})") from exc
            else:
                pats.append(("configured name", re.compile(rf"\b{re.escape(raw.strip())}\b")))
    if not pats:
        raise InputError("no name patterns: give --patterns or drop --replace-defaults")
    return pats


def mask_ignored(text: str, note_tag: str) -> str:
    """Blank out HTML comments, bracketed author notes ([TAG: ...]) and Markdown link targets, keeping line breaks."""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(rf"\[(?:{note_tag}):[^\]]*\]", blank, text, flags=re.S)
    text = re.sub(r"\]\([^)\n]*\)", blank, text)
    return text


def scan_names(path: Path, pats, note_tag: str) -> list[tuple[int, str, str, str]]:
    raw = path.read_text(encoding="utf-8")
    masked = mask_ignored(raw, note_tag).splitlines()
    shown = raw.splitlines()
    hits = []
    for i, line in enumerate(masked, 1):
        for lab, rx in pats:
            for m in rx.finditer(line):
                ctx = shown[i - 1][max(0, m.start() - 30):m.end() + 30].strip()
                hits.append((i, lab, m.group(0), ctx))
    return hits


def cmd_scan_names(a) -> int:
    pats = load_name_patterns(a.patterns, a.replace_defaults)
    rows = []
    for f in a.files:
        p = Path(f)
        if not p.is_file():
            raise InputError(f"file not found: {p}")
        for line, lab, match, ctx in scan_names(p, pats, a.note_tag):
            rows.append([str(p), line, lab, match, ctx])
            _OUT.info(f"{p}:{line}\t{lab}\t{match}\t{ctx}")
    if a.out:
        write_tsv(a.out, ["file", "line", "kind", "match", "context"], rows)
    _OUT.info(f"{len(a.files)} files scanned; {len(rows)} internal-name hits")
    return EXIT_FINDINGS if rows else EXIT_OK


# ----------------------------------------------------------------------------------------------- CLI

def _word_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--font", default="Arial", help="body font (default Arial)")
    p.add_argument("--font-size", type=float, default=9, help="body font size in points (default 9)")


def _ledger_inputs(p: argparse.ArgumentParser) -> None:
    p.add_argument("--notes", help="author notes, TSV or .md table: " + " | ".join(NOTE_COLUMNS))
    p.add_argument("--findings", action="append", help="reviewer findings, TSV or .md table (repeatable): "
                   + " | ".join(FINDING_COLUMNS))
    p.add_argument("--packages", help="reviewer packages, TSV or .md table: " + " | ".join(PACKAGE_COLUMNS))
    p.add_argument("--author-label", default="Author", help="name for the author in headings (default Author)")
    p.add_argument("--reviewer-label", default="Reviewer", help="name for the reviewer in headings (default Reviewer)")
    p.add_argument("--answer-header", default="Answer", help="header of the answer column (default Answer)")
    _word_opts(p)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="manuscript_revision.py", description=__doc__.split("\n\n")[0],
                                 epilog="Guide: docs/MANUSCRIPT_REVISION_WORKFLOW.md")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("apply", help="apply find-once/replace edits from JSON")
    p.add_argument("edits", help="JSON list of {doc, find, replace, ledger, row, why}")
    p.add_argument("--root", required=True, help="working copy folder; each edit's doc is relative to it")
    p.add_argument("--record", help="append-only JSONL change record (default <root>/CHANGES.jsonl)")
    p.add_argument("--dry-run", action="store_true", help="report what would happen; write nothing")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("changelog", help="before/after Word change log from the change record")
    p.add_argument("record", help="JSONL change record written by apply")
    p.add_argument("--out", required=True, help="output .docx")
    p.add_argument("--first", type=int, default=1, help="first record line to include (default 1)")
    p.add_argument("--title", default="Change log", help="heading")
    p.add_argument("--intro", default="", help="optional paragraph under the heading")
    p.add_argument("--doc-labels", help="TSV or .md table: prefix | label (document name prefix to display label)")
    p.add_argument("--context", type=int, default=60, help="shared characters kept either side of a change (default 60)")
    _word_opts(p)
    p.set_defaults(func=cmd_changelog)

    p = sub.add_parser("ledger", help="build the answerable revision ledger (.docx)")
    _ledger_inputs(p)
    p.add_argument("--out", required=True, help="output .docx")
    p.add_argument("--title", default="Revision ledger", help="heading")
    p.set_defaults(func=cmd_ledger)

    p = sub.add_parser("read-answers", help="extract answers; refuse if any other cell changed")
    p.add_argument("answered", help="the answered ledger .docx")
    p.add_argument("--original", required=True, help="the ledger .docx exactly as issued")
    p.add_argument("--out", required=True, help="output TSV: id | answer")
    p.add_argument("--answer-header", default="Answer", help="header of the answer column (default Answer)")
    p.set_defaults(func=cmd_read_answers)

    p = sub.add_parser("asks", help="asks-only round (.docx)")
    _ledger_inputs(p)
    p.add_argument("--answers", help="TSV from read-answers: id | answer")
    p.add_argument("--responses", help="TSV or .md table: " + " | ".join(RESPONSE_COLUMNS) + " (your reply per answered row)")
    p.add_argument("--need-status", default="NEED", help="response status text that keeps a row on the list (default NEED)")
    p.add_argument("--drop-regex", help="drop ASK notes whose note or action matches (case-insensitive); listed by id")
    p.add_argument("--out", required=True, help="output .docx")
    p.add_argument("--title", default="Open questions", help="heading")
    p.set_defaults(func=cmd_asks)

    p = sub.add_parser("check-numbers", help="flag numbers an edit introduces that no document or source holds")
    p.add_argument("edits", help="JSON edit file")
    p.add_argument("--root", required=True, help="working copy folder")
    p.add_argument("--source", action="append", help="record file whose numbers count as sourced (repeatable)")
    p.add_argument("--out", help="optional TSV of flagged edits")
    p.set_defaults(func=cmd_check_numbers)

    p = sub.add_parser("scan-names", help="flag internal names in prose")
    p.add_argument("files", nargs="+", help="Markdown or text files")
    p.add_argument("--patterns", help="patterns file: label<TAB>regex, or one literal name per line")
    p.add_argument("--replace-defaults", action="store_true", help="use only --patterns, not the built-in set")
    p.add_argument("--note-tag", default=DEFAULT_NOTE_TAG,
                   help="regex for the tag of bracketed notes to ignore, as in [TAG: ...] (default: any upper-case tag)")
    p.add_argument("--out", help="optional TSV of hits")
    p.set_defaults(func=cmd_scan_names)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.func(a)
    except InputError as exc:
        _OUT.error("REFUSED: %s", exc)
        return EXIT_INPUT
    except mdocx.DocxUnavailable as exc:
        _OUT.error("REFUSED: %s", exc)
        return EXIT_NO_DOCX


if __name__ == "__main__":
    raise SystemExit(main())
