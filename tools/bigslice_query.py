#!/usr/bin/env python3
"""Bound BiG-SLiCE 2.0.0/schema-1.0.1 query, cluster and read adapter.

External computation is optional and requires an admitted runtime/source manifest.
Query MUTATES an explicitly writable working result/model directory. --out is a
separate fresh receipt/export root. Results describe the selected model/run only;
nearest-centroid distance is not compound identity, production or universal novelty.
See docs/BIGSLICE_WORKFLOW.md for the input crosswalk and compatibility migration.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit
import argparse
import contextlib
import csv
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter
from mamey.exact_identity import (ExactLocusIdentityError, exact_locus_display,
                                  exact_locus_from_native_manifest_bgc)
from mamey.bigscape_namespace import NamespaceError, load_membership_tsv, public_error
from _release_validation import (ValidationRefused, atomic_json, canonical_json,
                                  run_watched, sha256_file, utc_now)

PROFILE = "bigslice-2.0.0-schema-1.0.1"
SCHEMA = "1.0.1"
MAX_ROWS = 100000
MAX_FILE = 64 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,99}")
CROSSWALK_FIELDS = ("relative_path", "bytes", "sha256", "strain", "full_contig", "region", "bgc_alias",
                    "manifest_path", "manifest_sha256", "inventory_row_sha256",
                    "source_zip", "source_zip_sha256", "source_member")
EXPORT_FIELDS = ("strain", "full_contig", "region", "bgc_alias", "exact_locus", "relative_path",
                 "input_sha256", "inventory_row_sha256", "attempt_id", "report_id", "query_bgc_id",
                 "model_sha256", "model_run_id", "clustering_id", "gcf_id", "gcf_id_in_run",
                 "qualified_family_id", "normalization", "rank", "membership_value", "interpretation_scope")
MODEL_COLUMNS = {"schema": {"ver"}, "run": {"id", "status", "hmm_db_id", "prog_params"},
                 "clustering": {"id", "run_id", "clustering_method", "num_centroids", "threshold", "random_seed"},
                 "hmm_db": {"id", "md5_biosyn_pfam", "md5_sub_pfam"},
                 "gcf": {"id", "id_in_run", "clustering_id"}}
BGC_COLUMNS = {"bgc": {"id", "orig_folder", "orig_filename", "length_nt"},
               "gcf_membership": {"bgc_id", "gcf_id", "rank", "membership_value"}}


class AdapterError(ValueError):
    """Typed expected refusal; no private path/payload in the public diagnostic."""
    def __init__(self, code, message):
        self.code = code
        self.public_message = message
        super().__init__(f"BIGSLICE_ERROR[{code}]: {message}")


def refuse(code, message):
    raise AdapterError(code, message)


def positive(value):
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        refuse("INVALID_ID", "expected a canonical positive integer")
    return int(value)


def digest_text(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def digest(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        refuse("INVALID_DIGEST", "expected an exact lower-case SHA256")
    return value


def file_binding(path):
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        refuse("FILE_REQUIRED", "a required input is not a regular file")
    return {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)}


def same_bytes(path, expected):
    actual = file_binding(path)
    if actual["sha256"] != digest(expected):
        refuse("SOURCE_CHANGED", "bound input bytes do not match")
    return actual


def read_json(path):
    p = Path(path)
    if p.stat().st_size > MAX_FILE:
        refuse("METADATA_LIMIT", "metadata input exceeds the supported byte limit")
    with p.open(encoding="utf-8") as handle:
        return json.load(handle)


def inside(path, root):
    return path == root or root in path.parents


def safe_relative(value):
    p = PurePosixPath(value)
    if (not value or p.is_absolute() or ".." in p.parts or "\\" in value or
            any(ord(c) < 32 for c in value) or p.as_posix() != value):
        refuse("RELATIVE_PATH_INVALID", "input relative path must be canonical and contained")
    return p


def resolve_paths(a):
    # Resolve write boundaries before reserving outputs, leases or staging anything.
    write_root = Path(a.write_root).resolve(strict=True)
    out = Path(a.out).expanduser().absolute()
    target = out.resolve()
    protected = [Path(__file__).resolve().parents[1]] + [Path(p).resolve(strict=True) for p in a.read_only_root]
    sources = [Path(a.input).resolve(strict=True), Path(a.identity_tsv).resolve(strict=True)]
    if a.mode == "read":
        sources += [Path(a.model_db).resolve(strict=True), Path(a.model_profile).resolve(strict=True)]
        if a.query_db:
            sources += [Path(a.query_db).resolve(strict=True), Path(a.reports_db).resolve(strict=True), Path(a.query_receipt).resolve(strict=True)]
    else:
        sources += [Path(a.program_db_folder).resolve(strict=True), Path(a.runtime_manifest).resolve(strict=True)]
        if a.mode == "query":
            sources += [Path(a.model_profile).resolve(strict=True)]
    if not inside(target, write_root) or target == write_root or os.path.lexists(out):
        refuse("OUTPUT_OCCUPIED_OR_OUTSIDE_ROOT", "--out must be a fresh child of the permitted write root")
    for p in protected + sources:
        if inside(target, p) or inside(p, target):
            refuse("WRITE_ALIAS", "output aliases protected inputs or source")
    work = None
    if a.mode == "query":
        if not a.allow_model_write:
            refuse("MODEL_WRITE_NOT_ACKNOWLEDGED", "query requires explicit --allow-model-write")
        work = Path(a.working_model).resolve(strict=True)
        if not work.is_dir() or not inside(work, write_root) or work == write_root:
            refuse("MODEL_WRITE_BOUNDARY", "working model must be an existing child of the permitted write root")
        for p in protected + sources + [target]:
            if inside(work, p) or inside(p, work):
                refuse("MODEL_WRITE_ALIAS", "working model aliases a protected input or output")
        if not os.access(work, os.W_OK):
            refuse("MODEL_NOT_WRITABLE", "working model is not writable")
    return out, work, protected


@contextlib.contextmanager
def readonly_db(path, columns):
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        refuse("DATABASE_REQUIRED", "an explicit regular SQLite database is required")
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(p) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            refuse("DATABASE_NOT_QUIESCENT", "checkpointed quiescent SQLite inputs are required")
    before = file_binding(p)
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True, timeout=1)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA query_only=ON")
        for table, needed in columns.items():
            found = {r[1] for r in con.execute('PRAGMA table_info("' + table + '")')}
            if not needed <= found:
                refuse("SCHEMA_UNSUPPORTED", "required schema table/columns are absent")
        yield con
    finally:
        con.close()
        if file_binding(p) != before:
            refuse("DATABASE_CHANGED", "SQLite source changed during readback")


def rows(con, sql, params=()):
    found = con.execute(sql, params).fetchmany(MAX_ROWS + 1)
    if len(found) > MAX_ROWS:
        refuse("ROW_LIMIT", "selected metadata exceeds the supported row limit")
    return [dict(r) for r in found]


def model_scope(path, run_id, normalization):
    run_id = positive(run_id)
    with readonly_db(path, MODEL_COLUMNS) as con:
        if rows(con, "SELECT ver FROM schema") != [{"ver": SCHEMA}]:
            refuse("SCHEMA_UNSUPPORTED", "only declared schema 1.0.1 is supported")
        selected = rows(con, "SELECT r.id AS run_id,r.status,r.prog_params,r.hmm_db_id,c.id AS clustering_id,"
                        "c.clustering_method,c.num_centroids,c.threshold,c.random_seed,h.md5_biosyn_pfam,h.md5_sub_pfam "
                        "FROM run r JOIN clustering c ON c.run_id=r.id JOIN hmm_db h ON h.id=r.hmm_db_id WHERE r.id=?", (run_id,))
        if len(selected) != 1 or selected[0]["status"] != 7:
            refuse("MODEL_RUN_NOT_FINISHED", "select exactly one finished run and linked clustering/HMM library")
        scope = selected[0]
        positive(scope["clustering_id"]); positive(scope["hmm_db_id"])
        if (not isinstance(scope["threshold"], (int, float)) or not math.isfinite(scope["threshold"]) or scope["threshold"] < 0 or
                not isinstance(scope["random_seed"], int) or scope["random_seed"] < 0 or
                any(not isinstance(scope[k], str) or not re.fullmatch(r"[0-9a-f]{32}", scope[k]) for k in ("md5_biosyn_pfam", "md5_sub_pfam"))):
            refuse("MODEL_METADATA_INVALID", "selected clustering/HMM metadata is invalid")
        families = rows(con, "SELECT id,id_in_run FROM gcf WHERE clustering_id=? ORDER BY id", (scope["clustering_id"],))
        if not families or len({r["id"] for r in families}) != len(families) or len({r["id_in_run"] for r in families}) != len(families):
            refuse("MODEL_FAMILIES_INVALID", "selected clustering has no unique GCF roster")
        if positive(scope["num_centroids"]) != len(families):
            refuse("MODEL_FAMILIES_INVALID", "GCF roster differs from declared centroid count")
        for row in families:
            positive(row["id"]); positive(row["id_in_run"])
        scope.update({"families": families, "model": file_binding(path), "normalization": normalization, "profile": PROFILE})
        return scope


def region_header(path, full_contig, region):
    """Metadata-only single-record/simple-region admission; retain no sequence text."""
    headers = []
    header_bytes = 0
    loci = 0
    origin = False
    with Path(path).open("rb") as handle:
        for line in handle:
            if line.startswith(b"LOCUS "):
                loci += 1
            if not origin:
                headers.append(line)
                header_bytes += len(line)
                if header_bytes > 1024 * 1024:
                    refuse("GBK_METADATA_LIMIT", "region header exceeds the supported bound")
            if line.startswith(b"ORIGIN"):
                origin = True
    text = b"".join(headers).decode("utf-8", errors="strict")
    versions = re.findall(r"^VERSION\s+(\S+)", text, re.M)
    locations = re.findall(r"^     region\s+(\d+)\.\.(\d+)\s*$", text, re.M)
    count = len(re.findall(r"^     region\s+", text, re.M))
    numbers = re.findall(r'/region_number="([0-9]+)"', text)
    locus = re.findall(r"^LOCUS\s+\S+\s+(\d+)\s+bp\b", text, re.M)
    names = re.findall(r"^LOCUS\s+(\S+)\s+\d+\s+bp\b", text, re.M)
    # antiSMASH writes a SPAdes contig's VERSION without the 0 after the coverage point
    # (NODE_1_length_9000_cov_71.028267 -> VERSION NODE_1_length_9000_cov_71.28267); LOCUS keeps it.
    # Admit exactly that form, and only when LOCUS names the full contig; any other mismatch still refuses.
    spades = re.fullmatch(r"(NODE_\d+_length_\d+_cov_\d+)\.(\d+)", full_contig)
    version_ok = versions == [full_contig] or (
        spades is not None and names == [full_contig] and versions == [f"{spades.group(1)}.{int(spades.group(2))}"])
    if (loci != 1 or not origin or not version_ok or count != 1 or len(locations) != 1 or
            len(numbers) != 1 or int(numbers[0]) != int(region[6:]) or len(locus) != 1):
        refuse("GBK_REGION_UNSUPPORTED", "one exact versioned record/simple numbered region is required")
    lo, hi = map(int, locations[0])
    if not 1 <= lo <= hi <= int(locus[0]):
        refuse("GBK_REGION_BOUNDS", "region feature lies outside its source record")
    return hi - lo + 1


def bounded_tsv(path, required, schema_code):
    if Path(path).stat().st_size > MAX_FILE:
        refuse("METADATA_LIMIT", "TSV metadata exceeds the supported byte limit")
    found = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not set(required) <= set(reader.fieldnames or ()):
            refuse(schema_code, "required exact metadata columns are absent")
        for row in reader:
            if len(found) >= MAX_ROWS:
                refuse("CSV_ROW_LIMIT", "TSV metadata exceeds the supported row limit")
            found.append(row)
    return found


def load_crosswalk(a):
    root = Path(a.input).resolve(strict=True)
    if not root.is_dir():
        refuse("INPUT_REQUIRED", "input view must be an existing directory")
    raw = bounded_tsv(a.identity_tsv, CROSSWALK_FIELDS, "CROSSWALK_SCHEMA")
    if not raw or len(raw) > MAX_ROWS:
        refuse("CROSSWALK_EMPTY_OR_LIMIT", "crosswalk must contain a bounded nonempty selected roster")
    manifests, archives, source_bindings, selected, identities = {}, {}, {}, {}, set()
    physical_loci, aliases = set(), set()
    try:
        for row in raw:
            rel = safe_relative(row["relative_path"]).as_posix()
            obj = (root / rel).resolve(strict=True)
            if not inside(obj, root) or not re.fullmatch(r".+\.region[0-9]+\.gbk", Path(rel).name):
                refuse("INPUT_VIEW_INVALID", "only contained antiSMASH region GBKs are supported")
            binding = same_bytes(obj, row["sha256"])
            if binding["bytes"] != positive(row["bytes"]) or binding["bytes"] > MAX_FILE:
                refuse("INPUT_BYTES", "input byte count is invalid or exceeds the limit")
            identity = exact_locus_display(row["strain"], row["full_contig"], row["region"], row["bgc_alias"])
            physical = (row["strain"], row["full_contig"], row["region"])
            alias = (row["strain"], row["bgc_alias"])
            if rel in selected or identity in identities or physical in physical_loci or alias in aliases:
                refuse("CROSSWALK_DUPLICATE", "crosswalk input and complete locus identities must be unique")
            mp = Path(row["manifest_path"]).resolve(strict=True)
            if mp not in manifests:
                source_bindings[str(mp)] = same_bytes(mp, row["manifest_sha256"])
                manifests[mp] = read_json(mp)
            elif source_bindings[str(mp)]["sha256"] != digest(row["manifest_sha256"]):
                refuse("SOURCE_CHANGED", "one manifest has conflicting supplied bindings")
            manifest = manifests[mp]
            if manifest.get("strain_id") != row["strain"]:
                refuse("INVENTORY_STRAIN", "manifest and crosswalk strain disagree")
            matches = [r for r in manifest.get("bgcs", []) if digest_text(r) == row["inventory_row_sha256"]]
            if len(matches) != 1:
                refuse("INVENTORY_ROW", "exact unique source inventory row is required")
            native = exact_locus_from_native_manifest_bgc(row["strain"], matches[0])
            if native.exact_locus != identity or matches[0].get("source_gbk") != row["source_member"]:
                refuse("INVENTORY_BINDING", "physical identity/source member disagrees with bound inventory")
            zp = Path(row["source_zip"]).resolve(strict=True)
            if zp not in archives:
                source_bindings[str(zp)] = same_bytes(zp, row["source_zip_sha256"])
                archives[zp] = zipfile.ZipFile(zp)
            elif source_bindings[str(zp)]["sha256"] != digest(row["source_zip_sha256"]):
                refuse("SOURCE_CHANGED", "one archive has conflicting supplied bindings")
            if manifest.get("input_zip_sha256") != row["source_zip_sha256"]:
                refuse("ARCHIVE_BINDING", "source archive does not match the manifest input digest")
            members = [i for i in archives[zp].infolist() if i.filename == row["source_member"]]
            if len(members) != 1 or members[0].file_size != binding["bytes"]:
                refuse("SOURCE_MEMBER", "source archive member must be exact and unique")
            h = hashlib.sha256()
            with archives[zp].open(members[0]) as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    h.update(block)
            if h.hexdigest() != binding["sha256"]:
                refuse("SOURCE_MEMBER_CHANGED", "input view differs from the bound original archive member")
            selected[rel] = {**row, "exact_locus": identity, "absolute_path": str(obj), "bytes": binding["bytes"],
                             "source_region_length_nt": region_header(obj, row["full_contig"], row["region"])}
            identities.add(identity); physical_loci.add(physical); aliases.add(alias)
    finally:
        for archive in archives.values():
            archive.close()
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*.gbk") if p.is_file()}
    if actual != set(selected):
        refuse("INPUT_DENOMINATOR", "all GBKs in the selected input view must have exact crosswalk rows")
    return selected, list(source_bindings.values())


def admit_runtime(a, out):
    manifest_path = Path(a.runtime_manifest).resolve(strict=True)
    data = read_json(manifest_path)
    if data.get("schema") != "bigslice-runtime-admission:v1" or data.get("profile") != PROFILE or data.get("version") != "2.0.0":
        refuse("RUNTIME_NOT_ADMITTED", "an explicitly reviewed 2.0.0/schema-1.0.1 runtime manifest is required")
    distribution = data.get("distribution")
    if (not isinstance(distribution, dict) or "version" not in distribution or distribution.get("name") != "bigslice" or
            distribution.get("mode") not in ("source-tree", "installed-distribution") or
            (distribution.get("mode") == "source-tree" and distribution.get("version") is not None) or
            (distribution.get("mode") == "installed-distribution" and
             (not isinstance(distribution.get("version"), str) or not distribution["version"].strip()))):
        refuse("RUNTIME_DISTRIBUTION", "separate exact distribution/source-tree provenance must be explicitly admitted")
    executable = Path(a.bigslice).expanduser().absolute()
    binding = same_bytes(executable, data.get("executable_sha256"))
    if not isinstance(data.get("source_pin"), str) or not data["source_pin"].strip() or data.get("review_status") != "ADMITTED_BY_OPERATOR":
        refuse("RUNTIME_NOT_ADMITTED", "runtime source pin/operator review and executable are required")
    interpreter = Path(data["interpreter_path"]).expanduser().absolute()
    interpreter_binding = same_bytes(interpreter, data["interpreter_sha256"])
    if not os.access(interpreter, os.X_OK):
        refuse("RUNTIME_INTERPRETER", "explicit Python interpreter is unavailable")
    # Operator admission is provenance, not a cryptographic assertion of human authorization.
    required = {"bigslice", "modules/data/schema.sql", "modules/data/schema_query_mode.sql",
                "modules/data/schema_reports_index.sql", "modules/data/bgc.py", "modules/clustering/membership.py"}
    source_root = Path(data["source_root"]).resolve(strict=True)
    source_rows = data.get("source_files", [])
    if len({r.get("relative_path") for r in source_rows}) != len(source_rows) or not required <= {r.get("relative_path") for r in source_rows}:
        refuse("RUNTIME_SOURCE_BINDING", "required reviewed upstream source/schema file bindings are missing")
    declared_entry = next(r for r in source_rows if r["relative_path"] == "bigslice")
    if binding["sha256"] != digest(declared_entry["sha256"]):
        refuse("RUNTIME_ENTRY_SOURCE", "executed entry bytes must equal the declared source-root entry")
    files = []
    for row in source_rows:
        p = (source_root / safe_relative(row["relative_path"])).resolve(strict=True)
        if not inside(p, source_root):
            refuse("RUNTIME_SOURCE_BINDING", "runtime source binding escapes its declared root")
        files.append(same_bytes(p, row["sha256"]))
    actual_files = set()
    for p in source_root.rglob("*"):
        if not inside(p.resolve(strict=True), source_root):
            refuse("RUNTIME_SOURCE_BINDING", "runtime source tree contains an escaping link")
        if p.is_file():
            actual_files.add(p.relative_to(source_root).as_posix())
    if actual_files != {r["relative_path"] for r in source_rows}:
        refuse("RUNTIME_SOURCE_BINDING", "runtime source inventory must cover its complete declared package root")
    hmm = Path(a.program_db_folder).resolve(strict=True)
    hmm_files = []
    for p in sorted(hmm.rglob("*")):
        if not inside(p.resolve(strict=True), hmm):
            refuse("HMM_BOUNDARY", "HMM assets must not escape the declared root")
        if p.is_file():
            hmm_files.append(file_binding(p))
        if len(hmm_files) > MAX_ROWS:
            refuse("HMM_LIMIT", "HMM inventory exceeds supported bound")
    md5s = []
    for name in ("biosynthetic_pfams/biopfam.md5sum", "sub_pfams/corepfam.md5sum"):
        value = (hmm / name).read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{32}", value):
            refuse("HMM_IDENTITY", "HMM identity files must carry exact MD5 identifiers")
        md5s.append(value)
    return {"executable": binding, "command_prefix": [str(interpreter), str(executable)], "interpreter": interpreter_binding, "manifest": file_binding(manifest_path), "source_files": files,
            "source_pin": data["source_pin"], "profile": PROFILE, "distribution": distribution, "hmm_files": hmm_files, "hmm_md5s": md5s}


def verify_bindings(bindings):
    for binding in bindings:
        if file_binding(binding["path"]) != binding:
            refuse("SOURCE_CHANGED", "immutable source bytes changed during the attempt")


def report_tree(work):
    """Bind even unindexed report destinations before a native query can write."""
    root = work / "reports"
    found = []
    if root.exists():
        for p in sorted(root.rglob("*")):
            if len(found) >= MAX_ROWS or not inside(p.resolve(strict=True), work):
                refuse("REPORT_TREE_INVALID", "report tree is unbounded or escapes its working root")
            found.append({"relative_path": p.relative_to(root).as_posix(),
                          "kind": "file" if p.is_file() else "directory",
                          "binding": file_binding(p) if p.is_file() else None})
    return found


def report_index(path):
    if not Path(path).exists():
        return []
    with readonly_db(path, {"reports": {"id", "type", "name", "creation_date"}, "reports_run": {"report_id", "run_id"}}) as con:
        reports = rows(con, "SELECT id,type,name,creation_date FROM reports ORDER BY id")
        links = rows(con, "SELECT report_id,run_id FROM reports_run ORDER BY report_id,run_id")
    return {"reports": reports, "links": links}


def resolve_report(path, before, name, run_id):
    after = report_index(path)
    if not after:
        refuse("QUERY_INCOMPLETE", "query did not create its exact report database")
    previous = {r["id"]: r for r in before["reports"]} if before else {}
    old_links = before["links"] if before else []
    if [r for r in after["reports"] if r["id"] in previous] != list(previous.values()):
        refuse("REPORT_HISTORY_CHANGED", "existing report rows changed")
    fresh = [r for r in after["reports"] if r["id"] not in previous]
    if len(fresh) != 1 or fresh[0]["type"] != "query" or fresh[0]["name"] != name:
        refuse("REPORT_DELTA_AMBIGUOUS", "exactly one new declared query report is required")
    selected_links = [r for r in after["links"] if r["report_id"] == fresh[0]["id"]]
    if selected_links != [{"report_id": fresh[0]["id"], "run_id": run_id}] or after["links"] != sorted(old_links + selected_links, key=lambda r: (r["report_id"], r["run_id"])):
        refuse("REPORT_RUN_MISMATCH", "query report must bind exactly the selected model run")
    return fresh[0]["id"], after


def admit_model_profile(a, scope):
    binding = file_binding(a.model_profile)
    data = read_json(a.model_profile)
    if (data.get("schema") != "bigslice-model-profile:v1" or data.get("profile") != PROFILE or
            data.get("model_sha256") != scope["model"]["sha256"] or
            data.get("run_id") != scope["run_id"] or data.get("normalization") != a.normalization or
            not data.get("provenance") or data.get("review_status") != "ADMITTED_BY_OPERATOR"):
        refuse("MODEL_PROFILE_NOT_ADMITTED", "exact model/run/normalization/provenance admission is required")
    return binding


def cache_inventory(work):
    root = work / "result/cache"
    found = []
    if root.exists():
        if not inside(root.resolve(strict=True), work):
            refuse("MODEL_CACHE_ALIAS", "model cache escapes the writable working result root")
        for p in sorted(root.rglob("*")):
            if not inside(p.resolve(strict=True), work):
                refuse("MODEL_CACHE_ALIAS", "cached resource escapes its working model")
            if p.is_file():
                found.append(file_binding(p))
            if len(found) > MAX_ROWS:
                refuse("MODEL_CACHE_LIMIT", "cached resource inventory exceeds supported bound")
    return found


def read_selected(a, scope, selected, report_id=None, query_db=None, cluster=False):
    database = query_db or Path(a.model_db)
    columns = dict(BGC_COLUMNS)
    if query_db:
        columns["schema"] = {"ver", "parent_schema_ver"}
    else:
        columns.update(MODEL_COLUMNS)
    with readonly_db(database, columns) as con:
        if query_db and rows(con, "SELECT ver,parent_schema_ver FROM schema") != [{"ver": SCHEMA, "parent_schema_ver": SCHEMA}]:
            refuse("QUERY_SCHEMA_UNSUPPORTED", "query and model schemas must both match 1.0.1")
        if query_db:
            bgcs = rows(con, "SELECT id,orig_folder,orig_filename,length_nt FROM bgc ORDER BY id")
            memberships = rows(con, "SELECT bgc_id,gcf_id,rank,membership_value FROM gcf_membership ORDER BY bgc_id,rank,gcf_id")
        else:
            # Model bgc rows from other runs are deliberately outside the selected denominator.
            if "run_bgc_status" not in {r["name"] for r in rows(con, "SELECT name FROM sqlite_master WHERE type='table'")}:
                refuse("SCHEMA_UNSUPPORTED", "clustering readback requires run_bgc_status")
            bgcs = rows(con, "SELECT b.id,b.orig_folder,b.orig_filename,b.length_nt FROM bgc b JOIN run_bgc_status s "
                        "ON s.bgc_id=b.id WHERE s.run_id=? AND s.status=7 ORDER BY b.id", (scope["run_id"],))
            memberships = rows(con, "SELECT m.bgc_id,m.gcf_id,m.rank,m.membership_value FROM gcf_membership m "
                               "JOIN gcf g ON g.id=m.gcf_id WHERE g.clustering_id=? ORDER BY m.bgc_id,m.rank,m.gcf_id", (scope["clustering_id"],))
    if len(bgcs) != len(selected) or not bgcs:
        refuse("PARSED_DENOMINATOR", "parsed BGC count must equal the complete selected input roster")
    mapped, seen_paths = {}, set()
    for bgc in bgcs:
        positive(bgc["id"])
        if Path(bgc["orig_filename"]).name != bgc["orig_filename"] or "\\" in bgc["orig_filename"]:
            refuse("DB_INPUT_PATH", "database orig_filename must be a literal basename")
        raw = Path(bgc["orig_folder"]) / bgc["orig_filename"]
        if cluster:
            if raw.is_absolute() or raw.parts != ("cohort", bgc["orig_filename"]):
                refuse("DB_INPUT_PATH", "clustering source path does not match the declared staged view")
            candidates = [r for r in selected.values() if Path(r["relative_path"]).name == bgc["orig_filename"]]
        else:
            resolved = raw.resolve(strict=True)
            candidates = [r for r in selected.values() if r["absolute_path"] == str(resolved)]
        if len(candidates) != 1 or candidates[0]["relative_path"] in seen_paths or bgc["id"] in mapped:
            refuse("DB_INPUT_AMBIGUOUS", "each database BGC must bind one unique original input record")
        if positive(bgc["length_nt"]) != candidates[0]["source_region_length_nt"]:
            refuse("DB_INPUT_LENGTH", "database BGC length differs from its bound source region feature")
        mapped[bgc["id"]] = candidates[0]
        seen_paths.add(candidates[0]["relative_path"])
    families = {r["id"]: r["id_in_run"] for r in scope["families"]}
    seen, ranks, output = set(), {key: set() for key in mapped}, []
    for m in memberships:
        key = (m["bgc_id"], m["rank"])
        if m["bgc_id"] not in mapped or m["gcf_id"] not in families or key in seen:
            refuse("MEMBERSHIP_CONFLICT", "orphan, duplicate rank or out-of-clustering GCF membership")
        rank, value = m["rank"], m["membership_value"]
        if isinstance(rank, bool) or not isinstance(rank, int) or not 0 <= rank < a.n_ranks or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            refuse("MEMBERSHIP_VALUE", "membership rank/value is invalid for this declared request")
        seen.add(key); ranks[m["bgc_id"]].add(rank)
        row = mapped[m["bgc_id"]]
        namespace = ["bigslice-gcf:v1", scope["model"]["sha256"], scope["run_id"], scope["clustering_id"], m["gcf_id"], families[m["gcf_id"]], PROFILE, scope["normalization"]]
        output.append({"strain": row["strain"], "full_contig": row["full_contig"], "region": row["region"], "bgc_alias": row["bgc_alias"],
                       "exact_locus": row["exact_locus"], "relative_path": row["relative_path"], "input_sha256": row["sha256"],
                       "inventory_row_sha256": row["inventory_row_sha256"], "attempt_id": a.attempt_id, "report_id": report_id or "",
                       "query_bgc_id": m["bgc_id"], "model_sha256": scope["model"]["sha256"], "model_run_id": scope["run_id"],
                       "clustering_id": scope["clustering_id"], "gcf_id": m["gcf_id"], "gcf_id_in_run": families[m["gcf_id"]],
                       "qualified_family_id": canonical_json(namespace).decode(), "normalization": scope["normalization"],
                       "rank": rank, "membership_value": value, "interpretation_scope": "NEAREST_CENTROID_IN_SELECTED_MODEL_NOT_PRODUCT_OR_NOVELTY"})
    if any(r != set(range(a.n_ranks)) for r in ranks.values()):
        refuse("MEMBERSHIP_DENOMINATOR", "every selected BGC must retain all declared ranks")
    return sorted(output, key=lambda r: (r["exact_locus"], r["rank"])), {"selected_inputs": len(selected), "parsed_bgcs": len(bgcs), "membership_rows": len(output), "excluded": 0}


def input_identity_projection(records):
    fields = ("relative_path", "sha256", "strain", "full_contig", "region", "bgc_alias")
    return sorted(tuple(r[k] for k in fields) for r in records)


def admit_query_receipt(a, scope, selected, report_id, query_db, index_rows):
    """Require a closed producer receipt, not a same-ID guess across models.

    Hash closure proves supplied artifact consistency, not human authorization.
    Legacy/external native queries without this explicit provenance stay held.
    Later unrelated index entries are allowed; the exact selected row/link is not.
    """
    receipt_path = Path(a.query_receipt).resolve(strict=True)
    if receipt_path.name != "SELECTED_RESULT.json":
        refuse("QUERY_PROVENANCE", "query read requires an explicit adapter-produced SELECTED_RESULT.json")
    state_path, manifest_path = receipt_path.parent / "RUN_STATE.json", receipt_path.parent / "RUN_MANIFEST.json"
    bindings = [file_binding(p) for p in (receipt_path, state_path, manifest_path)]
    result, state, manifest = (read_json(p) for p in (receipt_path, state_path, manifest_path))
    if (state.get("status") != "COMPLETE" or state.get("mode") != "query" or state.get("release") != "PRIVATE" or
            state.get("schema") != "mamey-bigslice-attempt:v1" or manifest.get("schema") != state["schema"] or
            manifest.get("mode") != "query" or manifest.get("release") != "PRIVATE" or manifest.get("status") != "PLANNED" or
            manifest.get("attempt_id") != state.get("attempt_id") or
            state.get("result_sha256") != bindings[0]["sha256"] or state.get("manifest_sha256") != bindings[2]["sha256"] or
            result.get("schema") != "mamey-bigslice-selected-result:v1"):
        refuse("QUERY_PROVENANCE", "producer query receipt/state/manifest is incomplete or lacks exact integrity closure")
    model_root = Path(a.reports_db).resolve(strict=True).parent.parent
    if (Path(scope["model"]["path"]) != model_root / "result/data.db" or
            manifest.get("working_model") != str(model_root) or result.get("model_scope") != scope or
            manifest.get("model_scope") != scope or scope["model"] not in manifest.get("immutable_bindings", [])):
        refuse("QUERY_MODEL_PROVENANCE", "query distances are not bound to this exact original model fingerprint/run/clustering/profile")
    if (result.get("query_db") != file_binding(query_db) or result.get("report_id") != report_id or
            state.get("denominator") != result.get("denominator") or
            result.get("denominator", {}).get("selected_inputs") != len(selected) or
            input_identity_projection(manifest.get("selected_inputs", [])) != input_identity_projection(selected.values())):
        refuse("QUERY_INPUT_PROVENANCE", "query DB/input identity denominator differs from the exact producer receipt")
    reports = [r for r in index_rows["reports"] if r["id"] == report_id]
    links = [r for r in index_rows["links"] if r["report_id"] == report_id]
    if result.get("query_provenance") != {"schema": "bigslice-query-provenance:v1", "query_name": a.query_name,
            "report_row": reports[0], "run_link": links[0]}:
        refuse("QUERY_REPORT_PROVENANCE", "selected report row/link differs from the original producer closure")
    return bindings


def bigscape_comparison(a, output):
    if not a.bigscape_tsv:
        return {"status": "NOT_REQUESTED"}
    source = file_binding(a.bigscape_tsv)
    if source["bytes"] > MAX_FILE:
        refuse("METADATA_LIMIT", "BiG-SCAPE metadata exceeds the supported byte limit")
    families = load_membership_tsv(a.bigscape_tsv, key_fields=("qualified_family_id",))
    if not a.bigscape_bridge:
        return {"status": "HOLD_EXACT_LOCUS_BRIDGE_REQUIRED", "source": source}
    bridge_binding = file_binding(a.bigscape_bridge)
    bridge = bounded_tsv(a.bigscape_bridge, ("strain", "full_contig", "region", "bgc_alias", "qualified_family_id", "member_locator"), "COMPARISON_BRIDGE")
    family_members = {r["qualified_family_id"]: {v.strip() for v in (r.get("members_locators") or "").split(";") if v.strip()} for r in families}
    joined = {}
    for row in bridge:
        identity = exact_locus_display(row["strain"], row["full_contig"], row["region"], row["bgc_alias"])
        family = row["qualified_family_id"]
        if family not in family_members or row.get("member_locator") not in family_members[family] or identity in joined:
            refuse("COMPARISON_BRIDGE", "bridge must uniquely bind exact loci to validated BiG-SCAPE families")
        # Explicit bridge is operator-supplied evidence, not a native Mamey identity inference.
        joined[identity] = family
    top = [r for r in output if r["rank"] == 0]
    if file_binding(a.bigscape_tsv) != source or file_binding(a.bigscape_bridge) != bridge_binding:
        refuse("COMPARISON_CHANGED", "BiG-SCAPE source changed during comparison")
    return {"status": "BOUND_OPERATOR_BRIDGE_NO_AGREEMENT_STATISTIC", "source": source,
            "bridge": bridge_binding, "selected_bgcs": len(top),
            "covered_bgcs": sum(r["exact_locus"] in joined for r in top),
            "excluded_bgcs": sum(r["exact_locus"] not in joined for r in top)}


def watched(a, command, out, label):
    env = dict(os.environ)
    env.update({"TMPDIR": str(out / "scratch"), "PYTHONDONTWRITEBYTECODE": "1",
                "OMP_NUM_THREADS": str(a.threads), "OPENBLAS_NUM_THREADS": str(a.threads), "MKL_NUM_THREADS": str(a.threads)})
    # The existing watcher measures filesystem free space. This is a conservative
    # consumption proxy, not exact per-job allocation accounting or a kernel quota.
    if shutil.which("nice") is None:
        refuse("RESOURCE_MONITOR", "the admitted native route requires nice15 support")
    receipt = run_watched(command, cwd=out, log=out / (label + ".log"), env=env,
                          rss_limit=a.rss_limit, min_disk=a.disk_floor, timeout=a.timeout)
    atomic_json(out / (label + "_process.json"), receipt)
    if receipt["exit_code"] != 0 or receipt["stop_reason"]:
        refuse("CHILD_FAILED", "external child failed or crossed its recorded resource boundary")
    return receipt


def run_attempt(a):
    if not 1 <= a.n_ranks <= 100 or not 1 <= a.threads <= 4 or not math.isfinite(a.timeout) or a.timeout <= 0 or a.rss_limit <= 0 or a.disk_budget <= 0 or a.min_free_disk < 0:
        refuse("RESOURCE_POLICY", "invalid ranks/threads/resource policy; interactive threads must be 1..4")
    if a.normalization == "legacy-unnormalized" and not a.allow_legacy_profile:
        refuse("NORMALIZATION_NOT_ADMITTED", "legacy querying requires explicit --allow-legacy-profile")
    out, work, protected = resolve_paths(a)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    a.disk_floor = max(a.min_free_disk, shutil.disk_usage(out).free - a.disk_budget)
    a.attempt_id = "bs-" + uuid.uuid4().hex
    state = {"schema": "mamey-bigslice-attempt:v1", "attempt_id": a.attempt_id, "status": "RUNNING", "started_utc": utc_now(), "mode": a.mode, "release": "PRIVATE"}
    atomic_json(out / "RUN_STATE.json", state)
    with (out / "REQUEST.json").open("x", encoding="utf-8") as handle:
        json.dump(vars(a), handle, indent=2, sort_keys=True); handle.write("\n")
    def event():
        with (out / "EVENTS.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(state).decode() + "\n")
    event()
    lease = None
    lease_owned = False
    try:
        selected, source_bindings = load_crosswalk(a)
        # All metadata/source targets discovered through the crosswalk are also write-protected.
        for binding in source_bindings:
            p = Path(binding["path"])
            if inside(p, out.resolve()) or (work and (inside(work, p) or inside(p, work))):
                refuse("SOURCE_WRITE_ALIAS", "write root aliases a crosswalk-bound source")
        (out / "scratch").mkdir()
        runtime = None
        before = None
        cache_before = []
        reports_before = []
        model_profile = None
        if a.mode == "query":
            name = a.query_name or a.attempt_id
            if not TOKEN.fullmatch(name):
                refuse("QUERY_NAME_INVALID", "query name must be a literal alphanumeric/dot/hyphen token")
            index = work / "reports/reports.db"
            # Take the single-writer lease BEFORE any model reads/probe; never break it.
            lease = work / ".mamey-bigslice-lease"
            with lease.open("x", encoding="utf-8") as handle:
                handle.write(a.attempt_id + "\n")
            lease_owned = True
            for subdir in ("result", "reports", "result/cache"):
                if not inside((work / subdir).resolve(), work):
                    refuse("MODEL_PATH_ALIAS", "native model write path escapes its working root")
            if work.stat().st_dev != out.stat().st_dev:
                refuse("RESOURCE_FILESYSTEM", "working model and output must share the monitored filesystem")
            for native_root in (work / "reports", work / "result/cache"):
                if native_root.exists():
                    observed_paths = 0
                    for p in native_root.rglob("*"):
                        observed_paths += 1
                        if observed_paths > MAX_ROWS or not inside(p.resolve(strict=True), work):
                            refuse("MODEL_PATH_ALIAS", "mutable native path is unbounded or escapes its working root")
            cache_before = cache_inventory(work)
            if index.resolve() == (work / "result/data.db").resolve():
                refuse("MODEL_PATH_ALIAS", "report index aliases immutable model data")
            before = report_index(index)
            reports_before = report_tree(work)
            indexed_ids = {str(r["id"]) for r in before["reports"]} if before else set()
            if any(PurePosixPath(r["relative_path"]).parts[0].isdigit() and
                   PurePosixPath(r["relative_path"]).parts[0] not in indexed_ids for r in reports_before):
                refuse("ORPHAN_REPORT_DESTINATION", "unindexed numeric report destination is preserved; fresh query cannot adopt or overwrite it")
            if before and any(r["name"].casefold() == name.casefold() for r in before["reports"]):
                refuse("QUERY_NAME_OCCUPIED", "query name already exists; choose a fresh attempt")
            a.model_db = str(work / "result/data.db")
            if not inside(Path(a.model_db).resolve(strict=True), work):
                refuse("MODEL_DATABASE_ALIAS", "model database escapes the writable working result root")
        if a.mode != "read":
            runtime = admit_runtime(a, out)
        if a.mode == "cluster":
            if a.normalization != "l2":
                refuse("CLUSTER_NORMALIZATION", "the admitted v2 cluster route uses l2 normalization")
            if not math.isfinite(a.threshold) or not 0 <= a.threshold <= 1.2:
                refuse("THRESHOLD_PROFILE", "v2 clustering threshold must be finite in 0..1.2")
            names = [Path(r).name for r in selected]
            if len(set(names)) != len(names):
                refuse("STAGING_COLLISION", "flat cluster staging would collide; use a distinct bound input view")
            stage = out / "input_view/cohort"; stage.mkdir(parents=True)
            for rel, row in selected.items():
                (stage / Path(rel).name).symlink_to(row["absolute_path"])
            (stage.parent / "datasets.tsv").write_text("# Dataset name\tPath to folder\tPath to taxonomy\tDescription\ncohort\tcohort\t\toperator-selected region panel; taxonomy unspecified\n", encoding="utf-8")
            result = out / "native_result"  # Must remain nonexistent until upstream creates it.
            command = [*runtime["command_prefix"], "-i", str(stage.parent), str(result), "--threshold", str(a.threshold),
                       "--n_ranks", str(a.n_ranks), "-t", str(a.threads), "--program_db_folder", str(Path(a.program_db_folder).resolve()), "--scratch"]
            scope = None
        else:
            scope = model_scope(a.model_db, a.model_run_id, a.normalization)
            model_profile = admit_model_profile(a, scope)
            if a.n_ranks > len(scope["families"]):
                refuse("RANK_COUNT", "requested ranks exceed selected model GCF count")
            if runtime and runtime["hmm_md5s"] != [scope["md5_biosyn_pfam"], scope["md5_sub_pfam"]]:
                refuse("HMM_MODEL_MISMATCH", "HMM identities disagree with the selected model run")
            command = None
            if a.mode == "query":
                command = [*runtime["command_prefix"], "--query", str(Path(a.input).resolve()), str(work), "--run_id", str(scope["run_id"]),
                           "--query_name", name, "--n_ranks", str(a.n_ranks), "-t", str(a.threads), "--program_db_folder", str(Path(a.program_db_folder).resolve())]
                if a.normalization == "legacy-unnormalized":
                    command.append("--no_normalize_feature")
        immutable = source_bindings + [file_binding(a.identity_tsv)] + [file_binding(r["absolute_path"]) for r in selected.values()]
        if runtime:
            immutable += [runtime["executable"], runtime["interpreter"], runtime["manifest"], *runtime["source_files"], *runtime["hmm_files"]]
        if scope:
            immutable += [scope["model"], model_profile]
        immutable += cache_before
        for binding in immutable:
            p = Path(binding["path"])
            if inside(p, out.resolve()) or (work and p != Path(a.model_db).resolve() and not inside(p, work / "result/cache") and (inside(work, p) or inside(p, work))):
                refuse("SOURCE_WRITE_ALIAS", "runtime or source resource aliases a mutable write target")
        # Historical reports are intentionally within the writable working root,
        # but immutable in this attempt. Add them after resource alias admission.
        immutable += [r["binding"] for r in reports_before if r["binding"] and Path(r["binding"]["path"]) != index.resolve()]
        manifest = {**state, "status": "PLANNED", "out": str(out.resolve()), "working_model": str(work) if work else None,
                    "command": command, "model_scope": scope, "model_profile": model_profile, "runtime": runtime, "cache_before": cache_before, "report_index_before": before, "report_tree_before": reports_before,
                    "selected_inputs": sorted(selected.values(), key=lambda r: r["relative_path"]), "immutable_bindings": immutable,
                    "resource_policy": {k: getattr(a, k) for k in ("threads", "rss_limit", "min_free_disk", "disk_budget", "disk_floor", "timeout")},
                    "disk_monitor_scope": "filesystem-free-space proxy across one admitted filesystem; not exact per-job quota",
                    "interpretation": "selected-model centroid evidence only; no product/activity/novelty inference"}
        with (out / "RUN_MANIFEST.json").open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True); handle.write("\n")
        emit("BiG-SLiCE write/export boundary:", str(out.resolve()), "working model:", str(work), "selected run:", str(a.model_run_id))
        if runtime:
            identity_code = "import sys,platform,json,importlib.metadata as m; names=['bigslice','biopython','numpy','scipy','scikit-learn','pandas','pyhmmer']; d={x.metadata.get('Name','').lower():x.version for x in m.distributions()}; print(json.dumps({'executable':sys.executable,'version':sys.version,'prefix':sys.prefix,'platform':platform.platform(),'distributions':{n:d.get(n) for n in names}},sort_keys=True))"
            watched(a, [runtime["command_prefix"][0], "-c", identity_code], out, "runtime_identity")
            identity = json.loads((out / "runtime_identity.log").read_text())
            if Path(identity["executable"]).absolute() != Path(runtime["command_prefix"][0]).absolute():
                refuse("RUNTIME_INTERPRETER", "actual child interpreter differs from its admitted invocation")
            atomic_json(out / "RUNTIME_IDENTITY.json", identity)
            if identity["distributions"].get("bigslice") != runtime["distribution"]["version"]:
                refuse("RUNTIME_DISTRIBUTION", "actual installed distribution differs from its separate admission; CLI banner is insufficient")
            # Upstream --version rewrites argv and reads a default adjacent HMM
            # folder. Help exits during argparse before those model reads.
            probe_command = [*runtime["command_prefix"], "--help"]
            probe = watched(a, probe_command, out, "runtime_probe")
            text = (out / "runtime_probe.log").read_text()
            versions = re.findall(r"\[\s*Version\s+([^\s\]]+)\s*\]", text)
            atomic_json(out / "RUNTIME_PROBE.json", {"kind": "UPSTREAM_HELP_BANNER", "command": probe_command,
                        "cli_expected_version": "2.0.0", "cli_observed_versions": versions,
                        "actual_distribution_version": identity["distributions"].get("bigslice"), "admitted_distribution": runtime["distribution"],
                        "source_pin": runtime["source_pin"], "log": file_binding(out / "runtime_probe.log"),
                        "process": file_binding(out / "runtime_probe_process.json"), "admitted": versions == ["2.0.0"]})
            if versions != ["2.0.0"]:
                refuse("RUNTIME_VERSION", "help must report exactly one admitted CLI version; distribution/source admission remains separate")
            watched(a, command, out, "native")
        report_id, query_db, query_provenance = None, None, None
        if a.mode == "query":
            report_id, report_after = resolve_report(index, before, name, scope["run_id"])
            query_provenance = {"schema": "bigslice-query-provenance:v1", "query_name": name,
                                "report_row": next(r for r in report_after["reports"] if r["id"] == report_id),
                                "run_link": next(r for r in report_after["links"] if r["report_id"] == report_id)}
            query_db = work / "reports" / str(report_id) / "data.db"
            if any(PurePosixPath(r["relative_path"]).parts[0] == str(report_id) for r in reports_before):
                refuse("STALE_REPORT_DESTINATION", "selected query report destination existed before this attempt; preserved unchanged")
            if not inside(query_db.resolve(strict=True), work):
                refuse("QUERY_DATABASE_ALIAS", "query database escapes the working result root")
        elif a.mode == "cluster":
            a.model_db = str(result / "result/data.db")
            with readonly_db(a.model_db, MODEL_COLUMNS) as con:
                finished = rows(con, "SELECT id FROM run WHERE status=7 ORDER BY id")
            if len(finished) != 1:
                refuse("CLUSTER_RUN_AMBIGUOUS", "fresh clustering must produce exactly one finished run")
            scope = model_scope(a.model_db, finished[0]["id"], a.normalization)
            immutable.append(scope["model"])
            atomic_json(out / "CLUSTER_MODEL_BINDING.json", {"model": scope["model"], "requested_threshold": a.threshold,
                        "actual_threshold": scope["threshold"], "expected_method": "birch", "actual_method": scope["clustering_method"]})
            if scope["threshold"] != a.threshold or scope["clustering_method"] != "birch":
                refuse("CLUSTER_CONFIG_MISMATCH", "produced clustering must match the declared birch method and exact requested threshold")
            if runtime["hmm_md5s"] != [scope["md5_biosyn_pfam"], scope["md5_sub_pfam"]]:
                refuse("HMM_MODEL_MISMATCH", "cluster result HMM identity disagrees with admitted resources")
        elif a.query_db:
            if not a.report_id or not a.query_name:
                refuse("READ_QUERY_SELECTION", "query readback requires explicit report ID and query name")
            index_rows = report_index(a.reports_db)
            chosen = [r for r in index_rows["reports"] if r["id"] == positive(a.report_id) and r["type"] == "query" and r["name"] == a.query_name] if index_rows else []
            links = [r for r in index_rows["links"] if r["report_id"] == positive(a.report_id)] if index_rows else []
            if len(chosen) != 1 or links != [{"report_id": positive(a.report_id), "run_id": scope["run_id"]}]:
                refuse("READ_QUERY_SELECTION", "exact report/name/run binding is absent or ambiguous")
            expected = Path(a.reports_db).resolve().parent / str(positive(a.report_id)) / "data.db"
            if Path(a.query_db).resolve(strict=True) != expected.resolve(strict=True):
                refuse("READ_QUERY_SELECTION", "query database path does not match the selected report")
            report_id, query_db = positive(a.report_id), Path(a.query_db)
            immutable += admit_query_receipt(a, scope, selected, report_id, query_db, index_rows)
        if query_db:
            immutable += [file_binding(query_db), file_binding(index if a.mode == "query" else a.reports_db)]
        output, denominator = read_selected(a, scope, selected, report_id, query_db, cluster=(a.mode == "cluster" or a.cluster_view))
        comparison = bigscape_comparison(a, output)
        verify_bindings(immutable)
        with (out / "bigslice_assignment.tsv").open("x", encoding="utf-8", newline="") as handle:
            writer = SafeDictWriter(handle, fieldnames=EXPORT_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader(); writer.writerows(output)
        atomic_json(out / "SELECTED_RESULT.json", {"schema": "mamey-bigslice-selected-result:v1", "model_scope": scope, "report_id": report_id, "query_provenance": query_provenance, "query_db": file_binding(query_db) if query_db else None, "cache_after": cache_inventory(work) if work else None,
                                                  "denominator": denominator, "comparison": comparison, "assignment": file_binding(out / "bigslice_assignment.tsv")})
        state.update({"status": "COMPLETE", "completed_utc": utc_now(), "denominator": denominator,
                      "result_sha256": sha256_file(out / "SELECTED_RESULT.json"), "manifest_sha256": sha256_file(out / "RUN_MANIFEST.json")})
        atomic_json(out / "RUN_STATE.json", state)
        event()
        emit("BiG-SLiCE complete selected-model export:", str(out / "bigslice_assignment.tsv"))
        return 0
    except BaseException as error:
        state.update({"status": "FAILED", "completed_utc": utc_now(), "error_code": getattr(error, "code", type(error).__name__),
                      "message": getattr(error, "public_message", "attempt incomplete; diagnostics retained; no success export admitted")})
        atomic_json(out / "RUN_STATE.json", state)
        event()
        raise
    finally:
        # Remove only this process's own cooperative lease; never clear someone else's.
        if lease_owned and lease and lease.exists() and lease.read_text().strip() == a.attempt_id:
            lease.unlink()


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    for mode in ("query", "cluster", "read"):
        p = sub.add_parser(mode)
        p.add_argument("--input", required=True)
        p.add_argument("--identity-tsv", required=True)
        p.add_argument("--out", required=True, help="fresh receipt/export root; never the query working model")
        p.add_argument("--write-root", required=True, help="permitted writable ancestor; not authority to write read-only research")
        p.add_argument("--read-only-root", action="append", default=[])
        p.add_argument("--n-ranks", type=int, default=5)
        p.add_argument("--threads", type=int, default=1)
        p.add_argument("--rss-limit", type=int, default=3800000000)
        p.add_argument("--min-free-disk", type=int, default=2000000000)
        p.add_argument("--disk-budget", type=int, default=2000000000)
        p.add_argument("--timeout", type=float, default=1800)
        p.add_argument("--normalization", choices=("l2", "legacy-unnormalized"), default="l2")
        p.add_argument("--allow-legacy-profile", action="store_true")
        p.add_argument("--bigscape-tsv")
        p.add_argument("--bigscape-bridge")
        p.set_defaults(working_model=None, model_db=None, model_run_id=None, query_db=None, reports_db=None,
                       report_id=None, query_name=None, query_receipt=None, cluster_view=False, allow_model_write=False)
        if mode != "read":
            p.add_argument("--bigslice", required=True, help="exact upstream Python entry-script path; interpreter bound by runtime manifest")
            p.add_argument("--runtime-manifest", required=True)
            p.add_argument("--program-db-folder", required=True)
        if mode == "query":
            p.add_argument("--working-model", "--bigfam-model", dest="working_model", required=True,
                           help="existing MUTABLE result/model root; --bigfam-model is deprecated")
            p.add_argument("--model-run-id", required=True)
            p.add_argument("--model-profile", required=True)
            p.add_argument("--query-name")
            p.add_argument("--allow-model-write", action="store_true")
        elif mode == "cluster":
            p.add_argument("--threshold", type=float, default=0.4)
        else:
            p.add_argument("--model-db", required=True)
            p.add_argument("--model-run-id", required=True)
            p.add_argument("--model-profile", required=True)
            p.add_argument("--query-db")
            p.add_argument("--query-receipt", help="explicit closed adapter producer SELECTED_RESULT.json; external/legacy queries remain held")
            p.add_argument("--reports-db")
            p.add_argument("--report-id")
            p.add_argument("--query-name")
            p.add_argument("--cluster-view", action="store_true", help="explicit cohort/filename staged-path grammar")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "read" and args.query_receipt and not args.query_db:
            refuse("READ_QUERY_SELECTION", "a query producer receipt requires explicit query/report database selection")
        if args.mode == "read" and args.query_db and not args.query_receipt:
            refuse("QUERY_PROVENANCE_REQUIRED", "query read requires --query-receipt; external/legacy provenance is not inferred")
        if args.mode == "read" and bool(args.query_db) != bool(args.reports_db):
            refuse("READ_QUERY_SELECTION", "query and report-index database paths must be supplied together")
        return run_attempt(args)
    except NamespaceError as error:
        sys.stderr.write(public_error(error) + "\n")
        return 2
    except (AdapterError, ExactLocusIdentityError, ValidationRefused) as error:
        sys.stderr.write(str(error) + "\n")
        return 2
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        sys.stderr.write("BIGSLICE_ERROR[INPUT_OR_RUNTIME_INVALID]: incomplete attempt; retained state/logs\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
