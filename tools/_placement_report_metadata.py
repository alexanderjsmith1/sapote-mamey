"""Stdlib contracts for placement report options and reviewed native-tip roles.

No database fetch, source/species inference, workspace probing, or tool execution.
"""
import csv
import hashlib
import json
import os
import stat
from pathlib import Path
import re

LIST_OPTIONS = (("owner_table", "--owner-table"), ("owner_table_original", "--owner-table-original"),
                ("resolved_metadata", "--resolved"), ("reviewed", "--reviewed"),
                ("query_override", "--query-override"))
SCHEMAS = {"owner_table": {"tip", "label", "source_category", "geography_category"},
           "owner_table_original": {"label"},
           "resolved_metadata": {"exact_accession", "verification_status", "isolation_source", "location"},
           "reviewed": {"accession"},
           "query_override": {"tip", "label", "source_category", "geography_category", "provenance"}}
TYPE_FIELDS = {"tip", "taxon", "role", "type_strain_of", "type_evidence", "source_accession", "strain",
               "review_state", "source_url", "strain_identity_basis"}
EXACT_ACCESSION = re.compile(r"[A-Z]{1,4}_?\d+\.\d+")


def metadata_path_argument(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("metadata path must be nonempty when supplied")
    return value


def add_arguments(parser, *, legacy_resolved_alias=False):
    for field, flag in LIST_OPTIONS:
        flags = [flag]
        if field == "resolved_metadata" and legacy_resolved_alias:
            flags.append("--reference-metadata")
        parser.add_argument(*flags, dest=field, action="append", default=[], type=metadata_path_argument, metavar="TSV")
    parser.add_argument("--query-prefix", default="AS")
    parser.add_argument("--rscript", default="Rscript", help="one Rscript executable, not a shell command")


def regular_path(path):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
        raise ValueError("REPORT_METADATA_PATH_INVALID")
    return path


def read_rows(path):
    path = regular_path(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)):
            raise ValueError("REPORT_METADATA_HEADERS_INVALID")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("REPORT_METADATA_ROW_INVALID")
    return set(fields), rows


def _positive_row_basics(row):
    if not TYPE_FIELDS <= set(row) or any(not row.get(key, "").strip() for key in TYPE_FIELDS):
        raise ValueError("HOLD_TYPE_EVIDENCE_MISSING")
    accession = row["source_accession"].strip()
    if not EXACT_ACCESSION.fullmatch(accession) or accession.startswith(("GCA_", "GCF_")):
        raise ValueError("HOLD_TYPE_SOURCE_ACCESSION_UNBOUND")
    if row["review_state"].strip() != "REVIEWED" or not re.fullmatch(r"[A-Z][A-Za-z-]+\s+[a-z][a-z-]+", row["type_strain_of"].strip()):
        raise ValueError("HOLD_TYPE_REVIEW_OR_TARGET_INVALID")
    if not re.match(r"https?://\S+$", row["source_url"].strip()):
        raise ValueError("HOLD_TYPE_SOURCE_URL_INVALID")


def normalize_options(namespace, *, context="report", validate=True):
    result = {}
    for field, flag in LIST_OPTIONS:
        values = getattr(namespace, field, None)
        if field == "resolved_metadata" and values is None and context == "report":
            legacy = getattr(namespace, "reference_metadata", None)
            if isinstance(legacy, (list, tuple)):
                values = legacy
            elif legacy not in (None, ""):
                raise ValueError("REPORT_RESOLVED_METADATA_REQUIRES_LIST")
        values = [] if values is None else values
        if not isinstance(values, (list, tuple)):
            raise ValueError("REPORT_METADATA_REQUIRES_LIST:" + field)
        admitted, identities = [], set()
        for raw in values:
            if not isinstance(raw, (str, Path)) or not str(raw).strip():
                raise ValueError("REPORT_METADATA_PATH_EMPTY:" + field)
            path = Path(raw).absolute()
            if validate:
                if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
                    raise ValueError("REPORT_METADATA_PATH_INVALID:" + field)
                state = path.stat()
                physical = (state.st_dev, state.st_ino)
                if physical in identities:
                    raise ValueError("REPORT_METADATA_DUPLICATE_INPUT:" + field)
                identities.add(physical)
                headers, rows = read_rows(path)
                if not SCHEMAS[field] <= headers:
                    raise ValueError("REPORT_METADATA_SCHEMA_INVALID:" + field)
                if field == "reviewed":
                    for row in rows:
                        if (row.get("role") or "").strip() == "type_reference":
                            _positive_row_basics(row)
            admitted.append(str(path))
        result[field] = admitted
    prefix = getattr(namespace, "query_prefix", "AS")
    rscript = getattr(namespace, "rscript", "Rscript")
    if not isinstance(prefix, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", prefix):
        raise ValueError("REPORT_QUERY_PREFIX_INVALID")
    if not isinstance(rscript, str) or not rscript.strip():
        raise ValueError("REPORT_RSCRIPT_EMPTY")
    result.update(query_prefix=prefix, rscript=rscript,
                  requested=any(result[field] for field, _flag in LIST_OPTIONS))
    return result


def to_argv(options):
    argv = []
    for field, flag in LIST_OPTIONS:
        for path in options[field]:
            argv += [flag, path]
    return argv + ["--query-prefix", options["query_prefix"], "--rscript", options["rscript"]]


def jplace_query_names(path):
    """Exact names from the admitted source file; no prefix or suffix guessing."""
    data = json.loads(regular_path(path).read_text())
    result = set()
    for placement in data.get("placements", []):
        if not isinstance(placement, dict) or ("n" in placement) == ("nm" in placement):
            raise ValueError("REPORT_JPLACE_QUERY_ROSTER_INVALID")
        entries = placement.get("n") if "n" in placement else placement.get("nm")
        if not isinstance(entries, list) or not entries:
            raise ValueError("REPORT_JPLACE_QUERY_ROSTER_INVALID")
        for entry in entries:
            name = entry if "n" in placement else entry[0] if isinstance(entry, list) and len(entry) == 2 else None
            if not isinstance(name, str) or not name or name in result:
                raise ValueError("REPORT_JPLACE_QUERY_ROSTER_INVALID")
            result.add(name)
    return result


def _source_accession(tip, label):
    # Exact native encoded accession or its exact labelmap accession; never assembly IDs.
    candidates = set()
    match = re.match(r"^([A-Z]{1,4}_?\d+)_(\d+)(?:_|$)", tip)
    if match:
        candidates.add(match.group(1) + "." + match.group(2))
    if EXACT_ACCESSION.fullmatch(tip):
        candidates.add(tip)
    for candidate in re.findall(r"(?<![A-Za-z0-9_])([A-Z]{1,4}_?\d+\.\d+)(?![A-Za-z0-9])", label or ""):
        if not candidate.startswith(("GCA_", "GCF_")):
            candidates.add(candidate)
    if any(value.startswith(("GCA_", "GCF_")) for value in candidates) or len(candidates) != 1:
        raise ValueError("TYPE_SOURCE_ACCESSION_AMBIGUOUS_OR_MISSING")
    return next(iter(candidates))


def _strain_anchor(tip, label):
    values = set()
    match = re.search(r"\bstrain\s+(.+?)(?=\s+(?:16S\b|23S\b|gene\b|ribosomal\b)|$)", label or "", re.I)
    encoded = re.search(r"_strain_(.+?)(?:_(?:16S|23S|gene|ribosomal)(?:_|$)|$)", tip, re.I)
    for found in (match, encoded):
        if found:
            values.add(re.sub(r"[\s_]+", " ", found.group(1)).strip().casefold())
    if len(values) > 1:
        raise ValueError("HOLD_TYPE_STRAIN_ANCHOR_CONFLICT")
    return next(iter(values), "")


def reviewed_type_map(paths, tip_labels, *, query_tips=(), resolved_paths=()):
    """Admit explicit reviewed roles for exact native sources; absence is unknown."""
    query_tips = set(query_tips)
    result, issues, negative = {}, [], set()
    refused_accessions = set()
    for path in resolved_paths:
        _headers, rows = read_rows(path)
        for row in rows:
            status = row.get("verification_status", "")
            if status not in {"STRAIN_CONFIRMED", "STRAIN_CONFIRMED_NO_METADATA", "STRAIN_CONFIRMED_NULL_DECLARED"}:
                refused_accessions.add(row.get("exact_accession", ""))
    for path in paths:
        _fields, rows = read_rows(path)
        for row in rows:
            role = (row.get("role") or "").strip()
            if role != "type_reference":
                tip = (row.get("tip") or "").strip()
                if tip and role == "cultured_non_type_reference":
                    negative.add(tip)
                    if tip in result:
                        raise ValueError("HOLD_TYPE_REVIEW_CONFLICT")
                if row.get("type_display"):
                    issues.append({"state": "UNVERIFIED_LEGACY_TYPE_MARK_SUPPRESSED", "tip": row.get("tip", "")})
                continue
            _positive_row_basics(row)
            tip = row["tip"].strip()
            if tip in negative:
                raise ValueError("HOLD_TYPE_REVIEW_CONFLICT")
            if tip not in tip_labels or tip in query_tips:
                raise ValueError("HOLD_TYPE_TIP_IDENTITY_UNBOUND")
            accession = row["source_accession"].strip()
            if (not EXACT_ACCESSION.fullmatch(accession) or accession.startswith(("GCA_", "GCF_")) or
                    accession != _source_accession(tip, tip_labels[tip])):
                raise ValueError("HOLD_TYPE_SOURCE_ACCESSION_UNBOUND")
            if accession in refused_accessions:
                raise ValueError("HOLD_TYPE_RESOLVER_IDENTITY_UNADMITTED")
            strain_anchor = _strain_anchor(tip, tip_labels[tip])
            if strain_anchor and strain_anchor != re.sub(r"[\s_]+", " ", row["strain"]).strip().casefold():
                raise ValueError("HOLD_TYPE_STRAIN_IDENTITY_CONFLICT")
            if row.get("accession") and row["accession"].strip() != accession:
                raise ValueError("HOLD_TYPE_SOURCE_ACCESSION_CONFLICT")
            value = {key: row[key].strip() for key in TYPE_FIELDS}
            if tip in result and result[tip] != value:
                raise ValueError("HOLD_TYPE_REVIEW_CONFLICT")
            result[tip] = value
    return {"schema": "sapote.reviewed-native-type-map.v1", "roles": result, "issues": issues,
            "unknown_role": "NOT_RECORDED", "authority": "explicit reviewed exact native-tip/source-sequence evidence; no accession-prefix inference"}


def file_binding(path):
    path = regular_path(path)
    state = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    sha = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode) or identity(state) != identity(opened):
            raise ValueError("REPORT_METADATA_SOURCE_CHANGED")
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
        finished = os.fstat(handle.fileno())
    after = regular_path(path).stat()
    if identity(state) != identity(after) or identity(state) != identity(finished):
        raise ValueError("REPORT_METADATA_SOURCE_CHANGED")
    return {"path": str(path), "sha256": sha.hexdigest(), "bytes": after.st_size,
            "physical_identity": list(identity(after))}
