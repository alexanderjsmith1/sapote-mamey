#!/usr/bin/env python3
"""Build a strain roster with an evidence map: which sources list each strain, and what data exist where.

Why: a paper's denominators (isolates indexed, screened, sequenced, assayed) must come from one roster,
not from whichever spreadsheet a figure script happened to read. Publication tables are deliberately
compact, and other tables of the same strains disagree on membership and on field values. This tool
takes the union of the member tables, shows which table lists each strain, maps where each strain's
data are stored, and lists every disagreement for the owner. It resolves none of them.

Spec (schema sapote.paper-cohort-spec.v2). Study names, strain patterns and paths live in the spec,
never in this code:
  root          workspace folder; spec paths are relative to it, and so is every *_where cell
  strain_regex  default pattern with a named group 'strain', searched in each ID cell
  aliases       {"recorded ID": "strain"} applied to every ID read; aliases_path names a JSON file
                holding the same mapping
  not_recorded  values that mean "nothing recorded" (for example "N/A"); they are not compared, and are
                stored as written
  members       tables whose union is the roster. Each: name, path, [sheet, header_row, filter,
                strain_column, strain_regex, label_column, fields {field: column},
                compare {field: strip|state|percent|accession|genus|ignore}, covers_cohort]
  exclusions    TSV flag and reason columns, or JSON key lists; no row is ever dropped
  evidence      one entry per data stream: name, stage, meaning, kind, and the kind's options:
                  table        path or paths, strain_column, [sheet, header_row, filter, strain_regex,
                               value yes|rows|values, value_columns]
                  files        glob or globs (** allowed); strain_regex is searched in the relative path
                  bundle_home  item antismash_zip|mamey_package, [flavor]; asks the bundle's own
                               resolver (mamey.strain_data_home), never a hand-written glob
  summary_by    a member name; SUMMARY.md counts strains by that member's label

Field values shown in the roster come from the first member, in spec order, that declares the field
and lists the strain; <field>_from names that member. Values are stored exactly as written (dates
become ISO dates). Normalisers are used only to compare values; a blank or not_recorded value is not
compared. Percent compares 0.986, 98.6 and 789/790 at the less precise value's precision; genus
compares the first word, and an initial such as "S." matches any genus with that first letter.

Outputs in a new --out-dir (refused if it exists and is not empty):
  ROSTER.tsv    one row per strain: in_<member>, fields with their source, exclusions, evidence and *_where
  HELD.tsv      kind, strain, field, value, value_source, other_value, other_source, note
  COLUMNS.tsv   what each roster column means, its workflow stage and its source
  SUMMARY.md    strain counts by label, per membership and evidence column
  RECEIPT.json  input paths, SHA-256 and row counts; counts per column and per HELD kind; spec SHA-256

HELD kinds: UNRECOGNISED_ID (a member cell holds no strain ID), DUPLICATE_IN_SOURCE, NOT_IN_SOURCE
(a member with "covers_cohort": true lacks a roster strain), FIELD_DIFFERS, EXCLUSION_DISAGREES (one
exclusion source excludes a strain that another lists as included).

An evidence cell of "no" means the named source does not list the strain. It is not a negative result.

Usage:
  paper_cohort_registry.py build --spec <spec.json> --out-dir <new_dir>
Exit 0 = built, silently: read SUMMARY.md and HELD.tsv (HELD rows are normal). Exit 2 = refused; the
reason is printed as an argparse error (spec, input or output problem).
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import csv
import datetime as _dt
import glob
import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


SPEC_SCHEMA = "sapote.paper-cohort-spec.v2"
RECEIPT_SCHEMA = "sapote.paper-cohort-receipt.v2"
HELD_COLUMNS = ["kind", "strain", "field", "value", "value_source", "other_value", "other_source", "note"]
STATE_MAP = {"+": "+", "pos": "+", "positive": "+", "-": "-", "−": "-", "–": "-", "neg": "-",
             "negative": "-", "n.t.": "n.t.", "nt": "n.t.", "n.t": "n.t.", "not tested": "n.t.", "": ""}
NORMALISERS = ("strip", "state", "percent", "accession", "genus", "ignore")
WHERE_SHOWN = 3


class Refused(Exception):
    """The spec, an input or the output location is unusable; nothing is written."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        return value.date().isoformat() if value.time() == _dt.time(0) else value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    return str(value)


def _read_table(path: Path, sheet: str | None, header_row: int) -> list[dict[str, str]]:
    if not path.is_file():
        raise Refused(f"input not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if sheet is not None and sheet not in workbook.sheetnames:
            raise Refused(f"sheet {sheet!r} not in {path.name}: {workbook.sheetnames}")
        rows = [[_cell(c) for c in row] for row in (workbook[sheet] if sheet else workbook.worksheets[0]).iter_rows(values_only=True)]
        workbook.close()
    else:
        delimiter = "\t" if path.suffix.lower() in (".tsv", ".txt") else ","
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = [list(r) for r in csv.reader(stream, delimiter=delimiter)]
    if len(rows) < header_row:
        raise Refused(f"{path.name} has no header row {header_row}")
    header = [h.strip() for h in rows[header_row - 1]]
    out = []
    for row in rows[header_row:]:
        if not any(str(c).strip() for c in row):
            continue
        out.append({h: (row[i] if i < len(row) else "") for i, h in enumerate(header) if h})
    return out


def _norm(value: str, how: str) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if how == "state":
        return STATE_MAP.get(text.casefold(), text.casefold())
    if how == "accession":
        return text.upper()
    if how == "genus":
        return text.split(" ")[0].casefold() if text else ""
    if how in ("strip", "percent"):
        return text.casefold()
    raise Refused(f"unknown normaliser {how!r}")


def _percent(text: str) -> tuple[Decimal, int] | None:
    ratio = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", text)
    if ratio and int(ratio.group(2)):
        return Decimal(ratio.group(1)) * 100 / Decimal(ratio.group(2)), 2
    try:
        number = Decimal(text.strip().rstrip("%").strip())
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    places = max(-number.as_tuple().exponent, 0)
    if number <= 1:
        number, places = number * 100, max(places - 2, 0)
    return number, places


def _same(a: str, b: str, how: str) -> bool:
    """Equal after the declared normaliser. Percent: 0.986 equals 98.6, and 98.63 equals 98.6, because
    the less precise value is compared at its own precision (half-up)."""
    if how == "percent":
        pa, pb = _percent(a), _percent(b)
        if pa and pb:
            step = Decimal(1).scaleb(-min(pa[1], pb[1]))
            return pa[0].quantize(step, ROUND_HALF_UP) == pb[0].quantize(step, ROUND_HALF_UP)
    na, nb = _norm(a, how), _norm(b, how)
    if how == "genus" and na and nb and re.fullmatch(r"\w\.", na) != re.fullmatch(r"\w\.", nb):
        return na[0] == nb[0]
    return na == nb


def _resolve(root: Path, raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else root / path


def _rel(path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _name(entry: dict, label: str, taken: set[str]) -> str:
    name = entry.get("name") or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise Refused(f"{label}: each entry needs a name of letters, digits and underscores")
    if name in taken:
        raise Refused(f"{label}: name {name!r} used twice")
    taken.add(name)
    return name


def _regex(entry: dict, default: str | None, label: str):
    pattern = entry.get("strain_regex", default)
    if pattern is None:
        return None
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise Refused(f"{label}: bad strain_regex: {exc}") from exc
    if "strain" not in compiled.groupindex:
        raise Refused(f"{label}: strain_regex needs a named group 'strain'")
    return compiled


class _Ids:
    """Strain IDs from cells: search the pattern, then apply aliases. Text around the ID is kept."""

    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases
        self.applied: dict[str, int] = {}

    def __call__(self, value, pattern) -> tuple[str | None, str]:
        text = str(value or "").strip()
        if not text:
            return None, ""
        if pattern is None:
            strain, rest = text, ""
        else:
            match = pattern.search(text)
            if not match:
                return None, ""
            strain = match.group("strain")
            rest = (text[:match.start("strain")] + text[match.end("strain"):]).strip()
        if strain in self.aliases:
            self.applied[strain] = self.applied.get(strain, 0) + 1
            rest = f"{rest} (recorded as {strain})".strip()
            strain = self.aliases[strain]
        return strain, rest


def _load(root: Path, src: dict, label: str, need_strain: bool = True) -> tuple[Path, list[dict[str, str]]]:
    if not src.get("path"):
        raise Refused(f"{label}: missing 'path'")
    path = _resolve(root, src["path"])
    rows = _read_table(path, src.get("sheet"), int(src.get("header_row", 1)))
    if need_strain:
        if not src.get("strain_column"):
            raise Refused(f"{label}: missing 'strain_column'")
        if rows and src["strain_column"] not in rows[0]:
            raise Refused(f"{label}: strain column {src['strain_column']!r} not in {path.name}")
    for column in [*src.get("filter", {}), *(src.get("fields") or {}).values(), *src.get("value_columns", [])]:
        if rows and column not in rows[0]:
            raise Refused(f"{label}: column {column!r} not in {path.name}")
    keep = [row for row in rows
            if all(_norm(row.get(col, ""), "strip") == _norm(val, "strip") for col, val in src.get("filter", {}).items())]
    return path, keep


def _where(paths: list[str]) -> str:
    shown = " | ".join(paths[:WHERE_SHOWN])
    return shown + (f" (+{len(paths) - WHERE_SHOWN} more)" if len(paths) > WHERE_SHOWN else "")


def _natural(strain: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", strain)]


def _evidence_table(root, entry, label, pattern, ids, roster, inputs):
    mode = entry.get("value", "values" if entry.get("value_columns") else "yes")
    if mode not in ("yes", "rows", "values") or (mode == "values" and not entry.get("value_columns")):
        raise Refused(f"{label}: value must be yes, rows, or values with value_columns")
    raw_paths = entry.get("paths") or ([entry["path"]] if entry.get("path") else [])
    if not raw_paths:
        raise Refused(f"{label}: missing 'path' or 'paths'")
    values: dict[str, list] = {}
    where: dict[str, list[str]] = {}
    for raw in raw_paths:
        path, rows = _load(root, {**entry, "path": raw}, label)
        outside = 0
        for row in rows:
            strain, _ = ids(row.get(entry["strain_column"], ""), pattern)
            if strain not in roster:
                outside += 1
                continue
            got = values.setdefault(strain, [])
            if mode == "values":
                got.append("/".join(str(row.get(c, "")).strip() for c in entry["value_columns"]))
            else:
                got.append("yes")
            rel = _rel(path, root)
            if rel not in where.setdefault(strain, []):
                where[strain].append(rel)
        inputs.append({"role": "evidence", "name": entry["name"], "path": _rel(path, root), "sha256": _sha256(path),
                       "rows": len(rows), "rows_for_other_strains": outside})
    cells = {}
    for strain, got in values.items():
        cells[strain] = ("yes" if mode == "yes" else str(len(got)) if mode == "rows"
                         else "; ".join(sorted(set(got), key=_natural)))
    return cells, {s: _where(w) for s, w in where.items()}


def _evidence_files(root, entry, label, pattern, ids, roster, inputs):
    patterns = entry.get("globs") or ([entry["glob"]] if entry.get("glob") else [])
    if not patterns or pattern is None:
        raise Refused(f"{label}: files evidence needs glob or globs and a strain_regex")
    found: dict[str, list[str]] = {}
    for raw in patterns:
        matched = sorted(glob.glob(str(_resolve(root, raw)), recursive=True))
        kept = 0
        for path in matched:
            rel = _rel(path, root)
            strain, _ = ids(rel, pattern)
            if strain in roster:
                kept += 1
                found.setdefault(strain, []).append(rel)
        inputs.append({"role": "evidence", "name": entry["name"], "glob": raw, "matches": len(matched),
                       "matches_for_roster": kept})
    return ({s: str(len(p)) for s, p in found.items()}, {s: _where(sorted(p)) for s, p in found.items()})


def _evidence_bundle_home(root, entry, label, roster, inputs):
    from mamey import __version__ as engine_version
    from mamey import strain_data_home as home
    item, flavor = entry.get("item"), entry.get("flavor")
    if item not in ("antismash_zip", "mamey_package"):
        raise Refused(f"{label}: item must be antismash_zip or mamey_package")
    resolve = home.resolve_antismash_zip if item == "antismash_zip" else home.resolve_mamey_package
    cells, where = {}, {}
    for strain in roster:
        path = resolve(strain, root=str(root), flavor=flavor)
        if path:
            version = re.search(r"_v(\d+\.\d+\.\d+)_", Path(path).name)
            cells[strain] = version.group(1) if item == "mamey_package" and version else "yes"
            where[strain] = _rel(path, root)
    inputs.append({"role": "evidence", "name": entry["name"], "resolver": f"mamey.strain_data_home.{resolve.__name__}",
                   "resolver_sha256": _sha256(Path(home.__file__)), "engine_version": engine_version,
                   "flavor": flavor, "searched_homes": list(home._package_homes()), "found": len(cells)})
    return cells, where


def build(spec_path: Path, out_dir: Path) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema") != SPEC_SCHEMA:
        raise Refused(f"spec schema must be {SPEC_SCHEMA}")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise Refused(f"--out-dir exists and is not empty: {out_dir}")
    root = _resolve(spec_path.parent, spec.get("root", "."))
    aliases = dict(spec.get("aliases") or {})
    inputs: list[dict] = []
    if spec.get("aliases_path"):
        alias_path = _resolve(root, spec["aliases_path"])
        if not alias_path.is_file():
            raise Refused(f"aliases file not found: {alias_path}")
        aliases.update(json.loads(alias_path.read_text(encoding="utf-8")))
        inputs.append({"role": "aliases", "name": "aliases", "path": _rel(alias_path, root), "sha256": _sha256(alias_path)})
    ids = _Ids(aliases)
    default_regex = spec.get("strain_regex")
    unrecorded = {_norm(v, "strip") for v in spec.get("not_recorded", [])}
    names: set[str] = set()
    held: list[list[str]] = []

    members = spec.get("members") or []
    if not members:
        raise Refused("spec needs at least one member table")
    listed: dict[str, dict[str, dict[str, str]]] = {}
    labels: dict[str, dict[str, str]] = {}
    roster: dict[str, dict[str, str]] = {}
    for member in members:
        name = _name(member, "member", names)
        for field, how in (member.get("compare") or {}).items():
            if how not in NORMALISERS:
                raise Refused(f"member {name}: unknown normaliser {how!r} for {field!r}")
        pattern = _regex(member, default_regex, f"member {name}")
        path, rows = _load(root, member, f"member {name}")
        inputs.append({"role": "member", "name": name, "path": _rel(path, root), "sha256": _sha256(path), "rows": len(rows)})
        seen: dict[str, dict[str, str]] = {}
        for row in rows:
            cell = str(row.get(member["strain_column"], "")).strip()
            strain, rest = ids(cell, pattern)
            if strain is None:
                if cell:
                    shown_cell = cell if len(cell) <= 120 else cell[:117] + "..."
                    held.append(["UNRECOGNISED_ID", shown_cell, member["strain_column"], "", "", shown_cell, name,
                                 "no strain ID found in this cell; row left out"])
                continue
            if strain in seen:
                held.append(["DUPLICATE_IN_SOURCE", strain, member["strain_column"], "", "", cell, name,
                             "another row has this strain ID after aliases; this row is ignored"])
                continue
            seen[strain] = row
            label = str(row.get(member.get("label_column", ""), "")).strip() or "yes"
            labels.setdefault(name, {})[strain] = f"{label} {rest}".strip()
            roster.setdefault(strain, {})
        listed[name] = seen

    for member in members:
        name = member["name"]
        if member.get("covers_cohort"):
            for strain in sorted(set(roster) - set(listed[name]), key=_natural):
                held.append(["NOT_IN_SOURCE", strain, "", "", "", "", name,
                             "listed by another member, absent from a source that covers the cohort"])

    fields: list[str] = []
    for member in members:
        for field in member.get("fields") or {}:
            if not re.fullmatch(r"[A-Za-z0-9_]+", field):
                raise Refused(f"member {member['name']}: bad field name {field!r}")
            if field not in fields:
                fields.append(field)
    for strain, values in roster.items():
        for member in members:
            values[f"in_{member['name']}"] = labels.get(member["name"], {}).get(strain, "no")
        for field in fields:
            holders = [m for m in members if field in (m.get("fields") or {}) and strain in listed[m["name"]]]
            if not holders:
                values[field], values[f"{field}_from"] = "", ""
                continue
            first = holders[0]
            shown = str(listed[first["name"]][strain].get(first["fields"][field], ""))
            values[field], values[f"{field}_from"] = shown, first["name"]
            for other in holders[1:]:
                theirs = str(listed[other["name"]][strain].get(other["fields"][field], ""))
                how = (other.get("compare") or {}).get(field) or (first.get("compare") or {}).get(field) or "strip"
                if how == "ignore" or _norm(shown, "strip") in unrecorded | {""} or _norm(theirs, "strip") in unrecorded | {""}:
                    continue
                if not _same(shown, theirs, how):
                    held.append(["FIELD_DIFFERS", strain, field, shown, first["name"], theirs, other["name"],
                                 f"compared with {how}"])

    excluded_by: dict[str, list[str]] = {s: [] for s in roster}
    reasons: dict[str, list[str]] = {s: [] for s in roster}
    included: dict[str, set[str]] = {}
    for source in spec.get("exclusions", []):
        name = _name(source, "exclusion", names)
        path = _resolve(root, source.get("path", ""))
        if not path.is_file():
            raise Refused(f"exclusion source not found: {path}")
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = 0
            for key in source.get("json_keys", []):
                for raw in data.get(key, []):
                    rows += 1
                    strain, _ = ids(raw, None)
                    if strain in roster:
                        excluded_by[strain].append(name)
                        reasons[strain].append(f"{name}:{key}")
        else:
            _, table = _load(root, source, f"exclusion {name}")
            rows = len(table)
            pattern = _regex(source, default_regex, f"exclusion {name}")
            truthy = {v.casefold() for v in source.get("excluded_values", ["yes", "true", "1", "excluded"])}
            for row in table:
                strain, _ = ids(row.get(source["strain_column"], ""), pattern)
                if strain not in roster:
                    continue
                if _norm(row.get(source.get("flag_column", ""), ""), "strip") in truthy:
                    excluded_by[strain].append(name)
                    reasons[strain].append(str(row.get(source.get("reason_column", ""), "")).strip() or name)
                else:
                    included.setdefault(strain, set()).add(name)
        inputs.append({"role": "exclusion", "name": name, "path": _rel(path, root), "sha256": _sha256(path), "rows": rows})
    for strain in roster:
        if excluded_by[strain] and included.get(strain):
            held.append(["EXCLUSION_DISAGREES", strain, "excluded", ";".join(excluded_by[strain]), "exclusions",
                         "not excluded", ";".join(sorted(included[strain])), "excluded by one source, included by another"])
        roster[strain]["excluded_by"] = ";".join(excluded_by[strain])
        roster[strain]["exclusion_reasons"] = ";".join(reasons[strain])

    describe: list[list[str]] = [["strain", "identity", "", "", "Strain ID after aliases; the union of all member tables"]]
    for member in members:
        describe.append([f"in_{member['name']}", "membership", "", _rel(_resolve(root, member["path"]), root),
                         (f"the source's {member['label_column']!r} value" if member.get("label_column") else "yes")
                         + " when this table lists the strain, else no; text around the ID in the source cell is kept"])
    for field in fields:
        describe.append([field, "field", "", "see the _from column", "value exactly as written in the first member that declares it"])
        describe.append([f"{field}_from", "field", "", "", f"member that supplied {field}"])
    describe.append(["excluded_by", "exclusion", "", "", "exclusion sources that exclude the strain; the row is kept"])
    describe.append(["exclusion_reasons", "exclusion", "", "", "reasons as written in those sources"])
    evidence_names: list[str] = []
    for entry in spec.get("evidence", []):
        name = _name(entry, "evidence", names)
        label = f"evidence {name}"
        kind = entry.get("kind")
        if kind == "table":
            cells, where = _evidence_table(root, entry, label, _regex(entry, default_regex, label), ids, roster, inputs)
            source = " | ".join(entry.get("paths") or [entry.get("path", "")])
        elif kind == "files":
            cells, where = _evidence_files(root, entry, label, _regex(entry, default_regex, label), ids, roster, inputs)
            source = " | ".join(entry.get("globs") or [entry.get("glob", "")])
        elif kind == "bundle_home":
            cells, where = _evidence_bundle_home(root, entry, label, roster, inputs)
            source = (f"bundle resolver mamey.strain_data_home ({entry.get('item')}, flavor {entry.get('flavor') or 'any'}; "
                      "package homes searched are in RECEIPT.json)")
        else:
            raise Refused(f"{label}: kind must be table, files or bundle_home")
        evidence_names.append(name)
        for strain, values in roster.items():
            values[name] = cells.get(strain, "no")
            values[f"{name}_where"] = where.get(strain, "")
        describe.append([name, "evidence", entry.get("stage", ""), source,
                         (entry.get("meaning") or kind) + "; no = the source does not list the strain, not a negative result"])
        describe.append([f"{name}_where", "evidence", entry.get("stage", ""), "",
                         f"where {name} is stored, relative to the workspace root"
                         + (f"; first {WHERE_SHOWN} shown" if kind != "bundle_home" else "")])

    order = sorted(roster, key=_natural)
    columns = ["strain", *[f"in_{m['name']}" for m in members],
               *[c for f in fields for c in (f, f"{f}_from")], "excluded_by", "exclusion_reasons",
               *[c for n in evidence_names for c in (n, f"{n}_where")]]
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "ROSTER.tsv", columns, [[s, *[roster[s].get(c, "") for c in columns[1:]]] for s in order])
    _write(out_dir / "HELD.tsv", HELD_COLUMNS, held)
    _write(out_dir / "COLUMNS.tsv", ["column", "kind", "stage", "source", "meaning"], describe)

    present = {c: sum(1 for s in order if roster[s][c] not in ("no", "")) for c in columns[1:]
               if c.startswith("in_") or c in evidence_names}
    present["excluded_by"] = sum(1 for s in order if roster[s]["excluded_by"])
    kinds: dict[str, int] = {}
    for row in held:
        kinds[row[0]] = kinds.get(row[0], 0) + 1
    by = spec.get("summary_by")
    if by and by not in listed:
        raise Refused(f"summary_by names no member: {by!r}")
    (out_dir / "SUMMARY.md").write_text(_summary(spec, roster, order, by, present, kinds, len(held)), encoding="utf-8")
    receipt = {"schema": RECEIPT_SCHEMA, "cohort": spec.get("cohort", ""),
               "built_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
               "tool": {"path": str(Path(__file__).resolve()), "sha256": _sha256(Path(__file__).resolve())},
               "root": str(root), "spec": {"path": str(spec_path), "sha256": _sha256(spec_path)},
               "inputs": inputs, "strains": len(roster), "present": present,
               "aliases_applied": dict(sorted(ids.applied.items())),
               "held": {"total": len(held), "by_kind": dict(sorted(kinds.items()))},
               "note": "HELD rows are for the owner to rule on; this tool resolves none of them. "
                       "An evidence cell of 'no' is not a negative result."}
    (out_dir / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def _write(path: Path, header: list[str], rows) -> None:
    from mamey.csv_safety import SafeWriter   # formula-injection guard for spreadsheet readers
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = SafeWriter(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _summary(spec, roster, order, by, present, kinds, n_held) -> str:
    groups: dict[str, list[str]] = {}
    for strain in order:
        key = roster[strain].get(f"in_{by}", "") if by else "all"
        groups.setdefault("not listed" if key == "no" else key, []).append(strain)
    heads = sorted(groups, key=lambda g: (g == "not listed", _natural(g)))
    lines = [f"# Strain roster and evidence map: {spec.get('cohort', '')}", "",
             f"{len(order)} strains, the union of {len(spec.get('members') or [])} member tables. "
             f"HELD rows for the owner: {n_held} {dict(sorted(kinds.items()))}.", "",
             "Counts are strains with a value in the column. \"no\" in an evidence column means the source does "
             "not list the strain; it is not a negative result.", ""]
    if by:
        lines.append(f"Grouped by `in_{by}`.")
        lines.append("")
    lines.append("| Column | " + " | ".join(f"{h} ({len(groups[h])})" for h in heads) + f" | All ({len(order)}) |")
    lines.append("|---" * (len(heads) + 2) + "|")
    for column in present:
        counts = [sum(1 for s in groups[h] if roster[s][column] not in ("no", "")) for h in heads]
        lines.append(f"| `{column}` | " + " | ".join(str(c) for c in counts) + f" | {present[column]} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build ROSTER, HELD, COLUMNS, SUMMARY and RECEIPT from a spec")
    b.add_argument("--spec", required=True, type=Path)
    b.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        build(args.spec, args.out_dir)
    except (Refused, json.JSONDecodeError, OSError) as exc:
        b.error(f"REFUSED: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
