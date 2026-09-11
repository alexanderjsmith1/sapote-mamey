"""Manifest-bound read-only inspection, separate from ingestion and selection.

Only frozen rollback-journal SQLite files are supported. Stop external writers;
native SQLite read transactions plus pre/post hashes detect ordinary drift, not
hostile filesystem replacement-and-restoration. No platform-specific file locks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sqlite3
import time
import zlib

from .exact_identity import exact_locus_display, ExactLocusIdentityError

SCHEMA = "tool_database_release_manifest/1"
BLASTP_ADAPTERS = {
    "blastp-nr-v1": ("ncbi_nr", "0.1.0"),
    "blastp-clustered-nr-v1": ("ncbi_clustered_nr", "0.1.0"),
    "blastp-swissprot-v2": ("local_swissprot", "0.2.0"),
}
ADAPTERS = ("manifest", "gene-census-v1", "keyword-gene-v1", *BLASTP_ADAPTERS, "package-scan-states-v1", "package-scan-genes-v1")
BLASTP_VIEWS = ("genes", "searches", "hits", "hsps", "history")
PACK_LIMIT = 8 * 1024 * 1024
HIT_OBSERVATION = "HITS_UNDER_RECORDED_SETTINGS"
NO_HIT_OBSERVATION = "NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE"
KEYWORD_CHANNELS = {
    "mamey_regulator_keywords", "chitinase_annotation_keywords",
    "resistance_annotation_keywords", "transporters_annotation_keywords",
}
IDENTITY_COLUMNS = ("locus_key", "strain", "full_node", "region", "bgc_alias", "exact_identity")
GENE_COLUMNS = ("locus_key", "gene_order", "locus_tag", "protein_sha256", "protein_length")
CENSUS_COLUMNS = ("cds_start", "cds_end", "strand", "membership", "product", "hold")
KEYWORD_COLUMNS = ("state", "groups_json")
CEILING = "Inspection only; no scientific admission, selection, biological absence, function, activity, production or release acceptance."


class ToolDatabaseInspectionError(ValueError):
    """Stable refusal code, without echoing private paths or raw database errors."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code):
    raise ToolDatabaseInspectionError(code)


def _digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def _relative_file(root, base, locator):
    if (not isinstance(locator, str) or not locator or "\\" in locator
            or PureWindowsPath(locator).drive or PurePosixPath(locator).is_absolute()
            or any(p in {"", ".", ".."} for p in locator.split("/"))):
        _fail("UNSAFE_RELATIVE_LOCATOR")
    p = base.joinpath(*PurePosixPath(locator).parts)
    try:
        components = p.relative_to(root).parts
    except ValueError:
        _fail("PATH_OUTSIDE_ROOT")
    current = root
    for part in components:
        current = current / part
        if current.is_symlink():
            _fail("SYMLINK_INPUT_REFUSED")
    resolved = p.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        _fail("INPUT_NOT_CONTAINED_FILE")
    return resolved


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_MANIFEST_KEY")
        result[key] = value
    return result


def _stamp(path):
    s = path.stat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def _no_sidecars(path):
    if any(Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
           for suffix in ("-wal", "-shm", "-journal")):
        _fail("LIVE_OR_JOURNALED_DATABASE_REFUSED")


def _table(c, name, required):
    row = c.execute("SELECT type,sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
    if not row or row[0] != "table" or not row[1] or "VIRTUAL TABLE" in row[1].upper():
        _fail("ADAPTER_TABLE_SHAPE_MISMATCH")
    # Names are fixed adapter constants, never caller/database-provided SQL.
    columns = {r[1] for r in c.execute('PRAGMA table_info("' + name + '")')}
    if not set(required) <= columns:
        _fail("ADAPTER_COLUMN_SHAPE_MISMATCH")


def _evidence_json(raw):
    if not isinstance(raw, (str, bytes)) or len(raw) > PACK_LIMIT:
        _fail("EVIDENCE_JSON_SIZE_OR_TYPE_HOLD")
    try:
        return json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: _fail("NONFINITE_EVIDENCE_HOLD"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ToolDatabaseInspectionError):
            raise
        raise ToolDatabaseInspectionError("MALFORMED_EVIDENCE_JSON") from exc


def _unpack(blob, expected=None):
    if not isinstance(blob, bytes) or len(blob) > PACK_LIMIT:
        _fail("COMPRESSED_EVIDENCE_SIZE_HOLD")
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(blob, PACK_LIMIT + 1)
        if len(raw) > PACK_LIMIT or decoder.unconsumed_tail:
            _fail("DECOMPRESSED_EVIDENCE_SIZE_HOLD")
        if not decoder.eof or decoder.unused_data:
            _fail("INVALID_COMPRESSED_EVIDENCE")
    except zlib.error as exc:
        raise ToolDatabaseInspectionError("INVALID_COMPRESSED_EVIDENCE") from exc
    if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        _fail("EVIDENCE_PACK_HASH_MISMATCH")
    return _evidence_json(raw)


def _page(records, total, limit, offset):
    return {"records": records, "total_records": total, "returned_records": len(records),
            "limit": limit, "offset": offset,
            "next_offset": offset + len(records) if offset + len(records) < total else None,
            "omitted_records": total - len(records),
            "retention_semantics": "Counts cover source-retained records only; not all possible database matches."}


def _blastp_schema(c, manifest, adapter):
    channel, version = BLASTP_ADAPTERS[adapter]
    if (manifest.get("channel"), manifest.get("version")) != (channel, version):
        _fail("ADAPTER_MANIFEST_VARIANT_MISMATCH")
    swiss = channel == "local_swissprot"
    shapes = {
        "metadata": ("key", "value"),
        "partition": ("locus_key", "exact_identity", "gene_count"),
        "binding": (*IDENTITY_COLUMNS, "gene_order", "locus_tag", "query_sha256", "binding_state"),
        "protein": ("query_sha256", "aa_length", "state") if swiss else
                   ("query_sha256", "protein_length", "availability_state", "search_count"),
    }
    if swiss:
        shapes.update({"outcome": ("query_sha256", "dataset_id", "batch_index", "observation", "hit_count", "receipt_query_json"),
                       "dataset": ("dataset_id", "provenance_json"),
                       "batch": ("dataset_id", "batch_index", "provenance_json"),
                       "source_metadata": ("key", "value"),
                       "_query_key": ("id", "query_sha256"),
                       "_hit_pack": ("query_id", "source_texts_zlib", "uncompressed_sha256"),
                       "_hit": ("query_id", "source_rank", "subject_id", "query_union_coverage_pct"),
                       "_subject": ("id", "details_json")})
    else:
        shapes.update({"search": ("id", "xml_id", "query_sha256", "query_title", "observation", "query_proof_json", "admission_state"),
                       "hit": ("search_id", "source_rank", "all_evidence_zlib"),
                       "source_xml": ("id", "original_locator", "sha256", "source_status", "detail", "channel"),
                       "source_metadata": ("xml_id", "metadata_json"),
                       "source_job": ("id", "xml_id", "source_provenance_zlib", "source_status")})
    for name, fields in shapes.items():
        _table(c, name, fields)
    metadata = list(c.execute("SELECT key,value FROM metadata LIMIT 257"))
    if len(metadata) > 256 or len(dict(metadata)) != len(metadata):
        _fail("METADATA_ROW_LIMIT_OR_DUPLICATE_HOLD")
    metadata = dict(metadata)
    if (metadata.get("channel"), metadata.get("schema_version")) != (channel, version):
        _fail("ADAPTER_METADATA_VARIANT_MISMATCH")
    return swiss, metadata


def _blastp_search_rows(c, q, swiss, limit, offset):
    if swiss:
        rows = list(c.execute("SELECT * FROM outcome WHERE query_sha256=? LIMIT ? OFFSET ?", (q, limit, offset)))
        total = c.execute("SELECT count(*) FROM outcome WHERE query_sha256=?", (q,)).fetchone()[0]
        if total > 1:
            _fail("DUPLICATE_QUERY_OUTCOME_HOLD")
    else:
        rows = list(c.execute("SELECT * FROM search WHERE query_sha256=? ORDER BY id LIMIT ? OFFSET ?", (q, limit, offset)))
        total = c.execute("SELECT count(*) FROM search WHERE query_sha256=?", (q,)).fetchone()[0]
    result = []
    for raw in rows:
        r = dict(raw)
        retained = r["hit_count"] if swiss else c.execute("SELECT count(*) FROM hit WHERE search_id=?", (r["id"],)).fetchone()[0]
        if (type(retained) is not int or retained < 0 or r["observation"] not in (HIT_OBSERVATION, NO_HIT_OBSERVATION)
                or (retained > 0) != (r["observation"] == HIT_OBSERVATION)):
            _fail("SEARCH_OBSERVATION_HIT_COUNT_CONFLICT")
        r["source_retained_hit_count"] = retained
        if swiss:
            r["search_id"] = 1
            r["search_id_semantics"] = "QUERY_SCOPED_READER_SELECTOR_NOT_ORIGINAL_SEARCH_ID"
            r["receipt_query"] = _evidence_json(r.pop("receipt_query_json"))
            ds = list(c.execute("SELECT provenance_json FROM dataset WHERE dataset_id=? LIMIT 2", (r["dataset_id"],)))
            bs = list(c.execute("SELECT provenance_json FROM batch WHERE dataset_id=? AND batch_index=? LIMIT 2", (r["dataset_id"], r["batch_index"])))
            if len(ds) != 1 or len(bs) != 1:
                _fail("MISSING_OR_CONFLICTING_SEARCH_PROVENANCE")
            r["dataset_provenance"] = _evidence_json(ds[0][0])
            r["batch_provenance"] = _evidence_json(bs[0][0])
            sm = list(c.execute("SELECT key,value FROM source_metadata LIMIT 257"))
            if len(sm) > 256 or len(dict(sm)) != len(sm):
                _fail("SOURCE_METADATA_LIMIT_OR_DUPLICATE_HOLD")
            r["source_metadata"] = dict(sm)
            r["admission_state"] = "SEQUENCE_BOUND_CURRENT_LOCUS_PROJECTION_NOT_HISTORICAL_JOB_LOCUS_ADMISSION"
        else:
            r["search_id"] = r.pop("id")
            r["query_proof"] = _evidence_json(r.pop("query_proof_json"))
            xs = list(c.execute("SELECT * FROM source_xml WHERE id=? LIMIT 2", (r["xml_id"],)))
            ms = list(c.execute("SELECT metadata_json FROM source_metadata WHERE xml_id=? LIMIT 2", (r["xml_id"],)))
            if len(xs) != 1 or len(ms) != 1:
                _fail("MISSING_OR_CONFLICTING_SEARCH_PROVENANCE")
            r["source_xml"] = dict(xs[0])
            r["source_metadata"] = _evidence_json(ms[0][0])
            jobs = list(c.execute("SELECT id,source_provenance_zlib,source_status FROM source_job WHERE xml_id=? ORDER BY id LIMIT 257", (r["xml_id"],)))
            if len(jobs) > 256:
                _fail("SOURCE_JOB_LIMIT_HOLD")
            r["source_jobs"] = [{"id": j[0], "provenance": _unpack(j[1]), "source_status": j[2]} for j in jobs]
        r["provenance_verification"] = "RECORDED_ONLY_EXTERNAL_SOURCES_NOT_OPENED"
        result.append(r)
    return _page(result, total, limit, offset)


def _blastp_hit_evidence(c, q, swiss, search_id, limit, offset, hit_rank=None):
    if swiss:
        bound = list(c.execute("SELECT observation,hit_count FROM outcome WHERE query_sha256=? LIMIT 2", (q,)))
        if search_id != 1 or len(bound) != 1:
            _fail("SEARCH_NOT_BOUND_TO_EXACT_GENE")
        observation, retained = bound[0]
        if (type(retained) is not int or retained < 0 or observation not in (HIT_OBSERVATION, NO_HIT_OBSERVATION)
                or (retained > 0) != (observation == HIT_OBSERVATION)):
            _fail("SEARCH_OBSERVATION_HIT_COUNT_CONFLICT")
        packs = list(c.execute("SELECT p.source_texts_zlib,p.uncompressed_sha256 FROM _hit_pack p JOIN _query_key k ON p.query_id=k.id WHERE k.query_sha256=? LIMIT 2", (q,)))
        if len(packs) > 1:
            _fail("DUPLICATE_EVIDENCE_PACK_HOLD")
        texts = _unpack(packs[0][0], packs[0][1]) if packs else []
        if not isinstance(texts, list) or any(not isinstance(t, str) for t in texts):
            _fail("INVALID_EVIDENCE_PACK_SHAPE")
        evidence = [_evidence_json(t) for t in texts]
        ranks = [e.get("source_rank") if isinstance(e, dict) else None for e in evidence]
        if any(type(r) is not int or r < 1 for r in ranks) or ranks != sorted(set(ranks)):
            _fail("INVALID_OR_DUPLICATE_HIT_RANK")
        expected = c.execute("SELECT hit_count FROM outcome WHERE query_sha256=?", (q,)).fetchone()[0]
        physical = c.execute("SELECT count(*) FROM _hit h JOIN _query_key k ON h.query_id=k.id WHERE k.query_sha256=?", (q,)).fetchone()[0]
        if len(evidence) != expected or physical != expected:
            _fail("RETAINED_HIT_COUNT_CONFLICT")
        summaries = list(c.execute("SELECT h.source_rank,h.query_union_coverage_pct,s.details_json FROM _hit h JOIN _query_key k ON h.query_id=k.id LEFT JOIN _subject s ON s.id=h.subject_id WHERE k.query_sha256=? ORDER BY h.source_rank", (q,)))
        if len(summaries) != len(evidence):
            _fail("HIT_SUMMARY_EVIDENCE_CONFLICT")
        for e, s in zip(evidence, summaries):
            ds = e.get("descriptions")
            if not isinstance(ds, list) or any(not isinstance(d, dict) for d in ds):
                _fail("INVALID_HIT_DESCRIPTION_SHAPE")
            first = ds[0] if ds else {}
            if (s[0] != e["source_rank"] or s[1] != e.get("query_union_coverage_pct")
                    or _evidence_json(s[2]) != [first.get("accession"), first.get("title"), e.get("subject_length")]):
                _fail("HIT_SUMMARY_EVIDENCE_CONFLICT")
        selected = evidence if hit_rank is None else [e for e in evidence if e["source_rank"] == hit_rank]
        total = len(selected)
        selected = selected[offset:offset + limit]
    else:
        bound = list(c.execute("SELECT observation,xml_id FROM search WHERE id=? AND query_sha256=? LIMIT 2", (search_id, q)))
        if len(bound) != 1:
            _fail("SEARCH_NOT_BOUND_TO_EXACT_GENE")
        retained = c.execute("SELECT count(*) FROM hit WHERE search_id=?", (search_id,)).fetchone()[0]
        if bound[0][0] not in (HIT_OBSERVATION, NO_HIT_OBSERVATION) or (retained > 0) != (bound[0][0] == HIT_OBSERVATION):
            _fail("SEARCH_OBSERVATION_HIT_COUNT_CONFLICT")
        source = list(c.execute("SELECT channel FROM source_xml WHERE id=? LIMIT 2", (bound[0][1],)))
        channel = c.execute("SELECT value FROM metadata WHERE key='channel'").fetchone()
        if len(source) != 1 or channel is None or source[0][0] != channel[0]:
            _fail("SEARCH_SOURCE_CHANNEL_CONFLICT")
        params = (search_id,) if hit_rank is None else (search_id, hit_rank)
        where = "search_id=?" if hit_rank is None else "search_id=? AND source_rank=?"
        total, distinct = c.execute("SELECT count(*),count(DISTINCT source_rank) FROM hit WHERE " + where, params).fetchone()
        if total != distinct:
            _fail("INVALID_OR_DUPLICATE_HIT_RANK")
        selected = []
        for rank, blob in c.execute("SELECT source_rank,all_evidence_zlib FROM hit WHERE " + where + " ORDER BY source_rank LIMIT ? OFFSET ?", (*params, limit, offset)):
            e = _unpack(blob)
            if not isinstance(e, dict) or type(rank) is not int or rank < 1 or e.get("source_rank") != rank:
                _fail("HIT_RANK_EVIDENCE_CONFLICT")
            selected.append(e)
    for e in selected:
        if not isinstance(e, dict) or not isinstance(e.get("hsps"), list) or any(not isinstance(h, dict) for h in e["hsps"]):
            _fail("INVALID_HSP_EVIDENCE_SHAPE")
    return selected, total


def _blastp_gene(c, binding, swiss):
    g = dict(binding); q = g["query_sha256"]
    if q is not None and (not isinstance(q, str) or not re.fullmatch(r"[0-9a-f]{64}", q)):
        _fail("INVALID_QUERY_HASH_HOLD")
    ps = list(c.execute("SELECT * FROM protein WHERE query_sha256=? LIMIT 2", (q,))) if q else []
    if len(ps) > 1:
        _fail("DUPLICATE_PROTEIN_HOLD")
    g["protein_length"] = ps[0]["aa_length" if swiss else "protein_length"] if ps else None
    g["availability_state"] = ps[0]["state" if swiss else "availability_state"] if ps else "MISSING_OR_UNBOUND_PROTEIN_HOLD"
    table = "outcome" if swiss else "search"
    observations = list(c.execute("SELECT observation,count(*) FROM " + table + " WHERE query_sha256=? GROUP BY observation LIMIT 4", (q,))) if q else []
    g["search_count"] = sum(n for _, n in observations)
    if not swiss and q and c.execute("SELECT count(DISTINCT id) FROM search WHERE query_sha256=?", (q,)).fetchone()[0] != g["search_count"]:
        _fail("DUPLICATE_SEARCH_ID_HOLD")
    states = {s for s, _ in observations}
    if not states <= {HIT_OBSERVATION, NO_HIT_OBSERVATION}:
        _fail("UNKNOWN_SEARCH_OBSERVATION_HOLD")
    derived = ("NO_VERIFIED_SEARCH" if not states else "VERIFIED_MIXED_OUTCOMES" if len(states) == 2
               else "VERIFIED_HITS" if HIT_OBSERVATION in states else "VERIFIED_NO_HIT")
    if ps:
        if not swiss and ps[0]["search_count"] != g["search_count"]:
            _fail("SEARCH_COUNT_CONFLICT")
        if (g["availability_state"] != derived or swiss and g["search_count"] > 1
                or type(g["protein_length"]) is not int or g["protein_length"] < 1):
            _fail("PROTEIN_STATE_OR_LENGTH_CONFLICT")
    elif g["search_count"]:
        _fail("SEARCH_WITHOUT_BOUND_PROTEIN_HOLD")
    return g


def _blastp_report(c, manifest, adapter, identity, limit, offset, gene_order, view, search_id, hit_rank):
    swiss, metadata = _blastp_schema(c, manifest, adapter)
    result = {"state": "SUPPORTED_SCHEMA_VERIFIED", "view": view, "recorded_metadata": metadata,
              "locus_query_state": "NOT_REQUESTED", "binding_ceiling": "SEQUENCE_PROJECTION_NOT_ORIGINAL_JOB_LOCUS_ADMISSION",
              "observed_counts": {"loci": c.execute("SELECT count(*) FROM partition").fetchone()[0],
                                  "genes": c.execute("SELECT count(*) FROM binding").fetchone()[0]}}
    if identity is None:
        return result
    display = exact_locus_display(*identity)
    result["exact_identity"] = display
    partitions = list(c.execute("SELECT locus_key,gene_count FROM partition WHERE exact_identity=? LIMIT 2", (display,)))
    if not partitions:
        result["locus_query_state"] = "LOCUS_NOT_FOUND_NOT_BIOLOGICAL_ABSENCE"
        return result
    if len(partitions) != 1 or not partitions[0][0]:
        _fail("HELD_IDENTITY_CONFLICT")
    key, declared = partitions[0]
    if c.execute("SELECT count(*) FROM partition WHERE locus_key=?", (key,)).fetchone()[0] != 1:
        _fail("HELD_IDENTITY_CONFLICT")
    bindings = list(c.execute("SELECT locus_key,gene_order,locus_tag,query_sha256,binding_state,strain,full_node,region,bgc_alias,exact_identity FROM binding WHERE locus_key=? ORDER BY gene_order LIMIT 10001", (key,)))
    if len(bindings) > 10000:
        _fail("LOCUS_GENE_CEILING_HOLD")
    if len(bindings) != declared or any(tuple(b[k] for k in IDENTITY_COLUMNS[1:5]) != tuple(identity) or b["exact_identity"] != display for b in bindings):
        _fail("HELD_IDENTITY_OR_ROSTER_CONFLICT")
    orders = [b["gene_order"] for b in bindings]
    if any(type(n) is not int or n < 0 for n in orders) or len(set(orders)) != len(orders):
        _fail("HELD_DUPLICATE_OR_NULL_GENE_ORDER")
    genes = []
    for b in bindings:
        if gene_order is not None and b["gene_order"] != gene_order:
            continue
        genes.append(_blastp_gene(c, b, swiss))
    result["locus_query_state"] = "RECORDED_ROWS_NOT_ADMITTED"
    if view == "history":
        # One verified read transaction, complete search histories; one explicitly
        # source-ranked representative PER search, never a cross-search top hit.
        for gene in genes:
            history = _blastp_search_rows(c, gene["query_sha256"], swiss, 1000, 0)
            if history["next_offset"] is not None:
                _fail("SEARCH_HISTORY_LIMIT_HOLD")
            for search in history["records"]:
                if not swiss and search["source_xml"]["channel"] != manifest["channel"]:
                    _fail("SEARCH_SOURCE_CHANNEL_CONFLICT")
                hits, count = _blastp_hit_evidence(c, gene["query_sha256"], swiss,
                                                 search["search_id"], 1, 0)
                search["representative"] = hits[0] if hits else None
                search["retained_hit_count"] = count
                search["representative_semantics"] = "LOWEST_RETAINED_SOURCE_RANK_WITHIN_THIS_SEARCH_NOT_BEST_BIOLOGICAL_COMPARATOR"
            gene["search_history"] = history["records"]
        result.update(_page(genes[offset:offset + limit], len(genes), limit, offset))
        return result
    if view == "genes":
        result.update(_page(genes[offset:offset + limit], len(genes), limit, offset))
        if gene_order is not None and not genes:
            result["gene_query_state"] = "GENE_NOT_FOUND_NOT_BIOLOGICAL_ABSENCE"
        return result
    if len(genes) != 1:
        _fail("EXACT_GENE_NOT_FOUND")
    gene = genes[0]; q = gene["query_sha256"]
    result["gene"] = gene
    if gene["availability_state"] == "MISSING_OR_UNBOUND_PROTEIN_HOLD":
        result["gene_query_state"] = "MISSING_OR_UNBOUND_PROTEIN_HOLD"
        return result
    if view == "searches":
        result.update(_blastp_search_rows(c, q, swiss, limit, offset))
        if not swiss and any(r["source_xml"]["channel"] != manifest["channel"] for r in result["records"]):
            _fail("SEARCH_SOURCE_CHANNEL_CONFLICT")
    else:
        es, total = _blastp_hit_evidence(c, q, swiss, search_id, limit if view == "hits" else 1,
                                        offset if view == "hits" else 0, hit_rank)
        if view == "hits":
            rows = [{"evidence": {k: v for k, v in e.items() if k != "hsps"},
                     "retained_hsp_count": len(e["hsps"]), "hsp_view": {"view": "hsps", "search_id": search_id, "hit_rank": e["source_rank"]}} for e in es]
            result.update(_page(rows, total, limit, offset))
        else:
            if total != 1:
                _fail("HIT_NOT_BOUND_TO_EXACT_SEARCH")
            result.update(_page(es[0]["hsps"][offset:offset + limit], len(es[0]["hsps"]), limit, offset))
            result["raw_hit_context"] = {k: v for k, v in es[0].items() if k != "hsps"}
        result["search_id"] = search_id
        result["hit_rank"] = hit_rank
    return result


def _adapter_report(c, manifest, adapter, identity, limit, offset, gene_order=None, view="genes", search_id=None, hit_rank=None):
    if adapter in ("package-scan-states-v1", "package-scan-genes-v1"):
        return _saved_package_scan_report(c, manifest, identity, limit, offset, genes=adapter == "package-scan-genes-v1")
    if adapter in BLASTP_ADAPTERS:
        return _blastp_report(c, manifest, adapter, identity, limit, offset, gene_order, view, search_id, hit_rank)
    if adapter == "manifest":
        return {"state": "RESULT_ADAPTER_NOT_SELECTED", "locus_query_state": "NOT_SUPPORTED" if identity else "NOT_REQUESTED"}
    channel = manifest.get("channel")
    if adapter == "gene-census-v1":
        if channel is not None or manifest.get("version") != "0.1.1":
            _fail("ADAPTER_MANIFEST_VARIANT_MISMATCH")
        fields = GENE_COLUMNS + CENSUS_COLUMNS
    else:
        if channel not in KEYWORD_CHANNELS or manifest.get("version") != "0.1.0":
            _fail("ADAPTER_MANIFEST_VARIANT_MISMATCH")
        fields = GENE_COLUMNS + KEYWORD_COLUMNS
    _table(c, "locus", IDENTITY_COLUMNS)
    _table(c, "gene", fields)
    _table(c, "section_profile", ("profile_sha256", "bundle_version"))
    profiles = [dict(r) for r in c.execute("SELECT profile_sha256,bundle_version FROM section_profile LIMIT 101")]
    if len(profiles) > 100:
        _fail("PROFILE_ROW_LIMIT_EXCEEDED")
    result = {"state": "SUPPORTED_SCHEMA_VERIFIED", "observed_counts": {
        "loci": c.execute("SELECT count(*) FROM locus").fetchone()[0],
        "genes": c.execute("SELECT count(*) FROM gene").fetchone()[0]},
        "recorded_profiles": profiles, "profile_validation": "RECORDED_METADATA_ONLY_NOT_CONTRACT_ACCEPTANCE",
        "locus_query_state": "NOT_REQUESTED"}
    if adapter == "keyword-gene-v1":
        states = list(c.execute("SELECT state,count(*) n FROM gene GROUP BY state ORDER BY state LIMIT 257"))
        if len(states) > 256:
            _fail("STATE_SUMMARY_LIMIT_EXCEEDED")
        result["observed_state_counts"] = [{"state": r[0], "rows": r[1]} for r in states]
    if identity is None:
        return result
    rows = list(c.execute("SELECT locus_key,strain,full_node,region,bgc_alias,exact_identity FROM locus WHERE strain=? AND full_node=? AND region=? AND bgc_alias=? LIMIT 2", identity))
    display = exact_locus_display(*identity)
    result["exact_identity"] = display
    if not rows:
        result["locus_query_state"] = "LOCUS_NOT_FOUND_NOT_BIOLOGICAL_ABSENCE"
        return result
    if len(rows) != 1 or rows[0]["exact_identity"] != display or not rows[0]["locus_key"]:
        result["locus_query_state"] = "HELD_IDENTITY_CONFLICT"
        return result
    key = rows[0]["locus_key"]
    if adapter == "gene-census-v1":
        columns = {r[1] for r in c.execute("PRAGMA table_info(locus)")}
        if {"region_start_1based", "region_end_1based"} <= columns:
            result["locus_geometry"] = dict(c.execute(
                "SELECT region_start_1based,region_end_1based FROM locus WHERE locus_key=?", (key,)).fetchone())
    if c.execute("SELECT count(*) FROM locus WHERE locus_key=?", (key,)).fetchone()[0] != 1:
        result["locus_query_state"] = "HELD_IDENTITY_CONFLICT"
        return result
    counts = c.execute("SELECT count(*),count(DISTINCT gene_order) FROM gene WHERE locus_key=?", (key,)).fetchone()
    if counts[0] != counts[1]:
        result["locus_query_state"] = "HELD_DUPLICATE_OR_NULL_GENE_ORDER"
        return result
    records = [dict(r) for r in c.execute("SELECT " + ",".join(fields) + " FROM gene WHERE locus_key=? ORDER BY gene_order LIMIT ? OFFSET ?", (key, limit, offset))]
    for row in records:
        row["exact_identity"] = display
    result.update({"locus_query_state": "RECORDED_ROWS_NOT_ADMITTED" if counts[0] else "LOCUS_PRESENT_NO_GENE_ROWS_HELD",
                   "records": records, "total_records": counts[0], "limit": limit, "offset": offset,
                   "returned_records": len(records), "next_offset": offset + len(records) if offset + len(records) < counts[0] else None})
    return result


def inspect_tool_database(root, manifest, *, adapter="manifest", identity=None,
                          limit=100, offset=0, expected_manifest_sha256=None,
                          gene_order=None, view="genes", search_id=None, hit_rank=None):
    """Inspect a user-selected static manifest/database, returning no admitted evidence.

    Manifest and database locators are relative beneath the explicit existing root.
    Only selected fixed-schema adapters query result rows. No SQL or write mode.
    Without expected_manifest_sha256, the manifest is selected, not authenticated.
    """
    if adapter not in ADAPTERS:
        _fail("UNSUPPORTED_ADAPTER")
    if view not in BLASTP_VIEWS or any(n is not None and (type(n) is not int or n < floor)
                                     for n, floor in ((gene_order, 0), (search_id, 1), (hit_rank, 1))):
        _fail("INVALID_BLASTP_SELECTOR")
    if adapter not in BLASTP_ADAPTERS and (view != "genes" or any(n is not None for n in (gene_order, search_id, hit_rank))):
        _fail("BLASTP_SELECTOR_REQUIRES_BLASTP_ADAPTER")
    if ((gene_order is not None or view != "genes") and identity is None
            or view not in ("genes", "history") and gene_order is None
            or view in ("genes", "searches", "history") and (search_id is not None or hit_rank is not None)
            or view in ("hits", "hsps") and search_id is None
            or view == "hsps" and hit_rank is None):
        _fail("INCOMPLETE_OR_CONFLICTING_BLASTP_SELECTOR")
    if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
        _fail("INVALID_PAGINATION")
    if identity is not None:
        if not isinstance(identity, (tuple, list)) or len(identity) != 4 or any(not isinstance(x, str) or x != x.strip() for x in identity):
            _fail("COMPLETE_EXACT_IDENTITY_REQUIRED")
        try:
            exact_locus_display(*identity)
        except ExactLocusIdentityError:
            _fail("COMPLETE_EXACT_IDENTITY_REQUIRED")
    c = None
    try:
        if root is None or not str(root).strip():
            _fail("EXPLICIT_ROOT_REQUIRED")
        root = Path(root).expanduser()
        if root.is_symlink():
            _fail("SYMLINK_ROOT_REFUSED")
        root = root.resolve(strict=True)
        if not root.is_dir():
            _fail("ROOT_NOT_DIRECTORY")
        mp = _relative_file(root, root, manifest)
        if mp.stat().st_size > 1048576:
            _fail("MANIFEST_SIZE_LIMIT_EXCEEDED")
        manifest_stamp = _stamp(mp)
        raw = mp.read_bytes(); manifest_hash = hashlib.sha256(raw).hexdigest()
        if expected_manifest_sha256 is not None and expected_manifest_sha256 != manifest_hash:
            _fail("MANIFEST_HASH_MISMATCH")
        m = json.loads(raw, object_pairs_hook=_unique_object,
                       parse_constant=lambda _: _fail("NONFINITE_MANIFEST_VALUE"))
        if not isinstance(m, dict) or m.get("schema") != SCHEMA:
            _fail("UNSUPPORTED_MANIFEST_SCHEMA")
        expected = m.get("database_sha256"); size = m.get("bytes")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or type(size) is not int or size < 100:
            _fail("INVALID_DATABASE_HASH_OR_SIZE")
        dp = _relative_file(root, mp.parent, m.get("database"))
        if "files" in m:
            if not isinstance(m["files"], list) or any(not isinstance(x, dict) for x in m["files"]):
                _fail("INVALID_MANIFEST_FILES")
            matches = [x for x in m["files"] if x.get("path") == m["database"]]
            if len(matches) != 1 or matches[0].get("sha256") != expected or matches[0].get("bytes") != size:
                _fail("MANIFEST_DATABASE_ENTRY_CONFLICT")
        _no_sidecars(dp); before = _stamp(dp)
        if dp.stat().st_size != size:
            _fail("DATABASE_SIZE_MISMATCH")
        with dp.open("rb") as f:
            header = f.read(100)
        if header[:16] != b"SQLite format 3\x00":
            _fail("NOT_SQLITE_DATABASE")
        if header[18:20] != b"\x01\x01":
            _fail("WAL_OR_UNSUPPORTED_SQLITE_FORMAT")
        c = sqlite3.connect(dp.as_uri() + "?mode=ro", uri=True, timeout=1)
        # Bound SQLite value materialization as well as zlib expansion.
        c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, PACK_LIMIT + 65536)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON"); c.execute("PRAGMA trusted_schema=OFF")
        c.execute("BEGIN"); c.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        _no_sidecars(dp)
        if _digest(dp) != expected:
            _fail("DATABASE_HASH_MISMATCH")
        deadline = time.monotonic() + 10
        c.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        if c.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            _fail("SQLITE_INTEGRITY_HOLD")
        result = {"schema": "mamey_tool_database_inspection/1", "integrity_state": "MANIFEST_DATABASE_HASH_SIZE_AND_QUICK_CHECK_VERIFIED",
                  "manifest_sha256": manifest_hash, "manifest_trust": "EXPECTED_HASH_MATCHED" if expected_manifest_sha256 else "USER_SELECTED_NOT_EXTERNALLY_AUTHENTICATED",
                  "database_sha256": expected, "database_bytes": size, "manifest_schema": m["schema"],
                  "channel": m.get("channel", "NOT_RECORDED"), "version": m.get("version", "NOT_RECORDED"),
                  "source_status": m.get("status", "NOT_RECORDED"),
                  "declared_coverage_not_recomputed": {k: m[k] for k in ("counts", "row_counts", "availability", "held_records") if k in m},
                  "declared_profile_and_versions": {k: m[k] for k in ("profile_sha256", "section_profile_sha256", "profile_overlay_sha256", "section_requirements_unchanged") if k in m},
                  "declared_binding_summary": {k: v for k, v in m.get("binding", {}).items() if isinstance(v, (str, int, float, bool))} if isinstance(m.get("binding", {}), dict) else {},
                  "dependencies_state": "NOT_OPENED_OR_VERIFIED", "adapter": adapter,
                  "scientific_admission": "NOT_PERFORMED", "claim_ceiling": CEILING,
                  "results": _adapter_report(c, m, adapter, identity, limit, offset, gene_order, view, search_id, hit_rank)}
        _no_sidecars(dp)
        if _digest(dp) != expected or _stamp(dp) != before or _digest(mp) != manifest_hash or _stamp(mp) != manifest_stamp:
            _fail("INPUT_CHANGED_DURING_INSPECTION")
        try:
            encoded = json.dumps(result, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            _fail("UNSUPPORTED_RESULT_VALUE")
        if len(encoded) > 2097152:
            _fail("RESULT_SIZE_LIMIT_EXCEEDED")
        return result
    except (OSError, UnicodeError, json.JSONDecodeError, OverflowError) as exc:
        raise ToolDatabaseInspectionError("INPUT_UNREADABLE_OR_MALFORMED") from exc
    except sqlite3.Error as exc:
        raise ToolDatabaseInspectionError("SQLITE_READ_OR_BUDGET_HOLD") from exc
    finally:
        if c is not None:
            c.close()


def inspection_command(args):
    """CLI adapter: structured stdout only, typed nonzero refusal, no file output."""
    try:
        result = inspect_tool_database(args.root, args.manifest, adapter=args.adapter,
                                       identity=args.locus, limit=args.limit, offset=args.offset,
                                       expected_manifest_sha256=args.manifest_sha256,
                                       gene_order=getattr(args, "gene_order", None), view=getattr(args, "view", "genes"),
                                       search_id=getattr(args, "search_id", None), hit_rank=getattr(args, "hit_rank", None))
    except ToolDatabaseInspectionError as exc:
        print(json.dumps({"status": "HELD", "code": exc.code, "scientific_admission": "NOT_PERFORMED"}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


# Candidate function body appended to the existing governed reader by prepare_patch.py.
# Existing reader owns manifest pins, containment, SQLite transaction, budgets and drift checks.
def _saved_package_scan_report(c, manifest, identity, limit, offset, genes=False):
    if (manifest.get('channel'), manifest.get('version')) != ('current_package_scan_states', '0.1.0'):
        _fail('ADAPTER_MANIFEST_VARIANT_MISMATCH')
    shapes = {
        'metadata': ('key', 'value'),
        'package': ('package_id', 'manifest_sha256', 'strain', 'input_zip_sha256', 'bundle_version', 'engine_version', 'recorded_status', 'context_json'),
        'locus': (*IDENTITY_COLUMNS, 'package_id', 'frozen_binding_state', 'frozen_context_json', 'guards_json'),
        'signal': ('locus_key', 'channel', 'state', 'saved_status', 'source_locator', 'source_sha256', 'raw_zlib', 'raw_sha256', 'compatible_channel', 'evidence_index_state'),
        'gene': (*GENE_COLUMNS, 'cds_start', 'cds_end', 'strand', 'membership', 'state', 'source_fields_json'),
        'section_profile': ('profile_sha256', 'bundle_version'),
    }
    for name, fields in shapes.items():
        _table(c, name, fields)
    meta = list(c.execute('SELECT key,value FROM metadata LIMIT 257'))
    if len(meta) > 256 or len(dict(meta)) != len(meta):
        _fail('METADATA_ROW_LIMIT_OR_DUPLICATE_HOLD')
    meta = dict(meta)
    if (meta.get('channel'), meta.get('schema_version')) != ('current_package_scan_states', '0.1.0'):
        _fail('ADAPTER_METADATA_VARIANT_MISMATCH')
    result = {'state': 'SAVED_PACKAGE_SCAN_CONTEXT_NOT_ADMITTED', 'view': 'genes' if genes else 'signals',
              'recorded_metadata': meta, 'locus_query_state': 'NOT_REQUESTED',
              'new_scans_or_matching': 'NOT_PERFORMED',
              'observed_counts': {t: c.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in ('package', 'locus', 'gene', 'signal')}}
    if identity is None:
        return result
    display = exact_locus_display(*identity)
    loci = [dict(r) for r in c.execute('SELECT * FROM locus WHERE strain=? AND full_node=? AND region=? AND bgc_alias=? ORDER BY package_id LIMIT 101', identity)]
    if len(loci) > 100:
        _fail('PACKAGE_OCCURRENCE_LIMIT_HOLD')
    result['exact_identity'] = display
    if not loci:
        result['locus_query_state'] = 'LOCUS_NOT_FOUND_NOT_BIOLOGICAL_ABSENCE'
        return result
    if len({r['package_id'] for r in loci}) != len(loci):
        _fail('DUPLICATE_PACKAGE_LOCUS_HOLD')
    packages = []
    for loc in loci:
        if loc['exact_identity'] != display or not re.fullmatch(r'[0-9a-f]{64}', loc['locus_key'] or ''):
            _fail('HELD_IDENTITY_CONFLICT')
        if c.execute('SELECT count(*) FROM locus WHERE locus_key=?', (loc['locus_key'],)).fetchone()[0] != 1:
            _fail('HELD_IDENTITY_CONFLICT')
        rows = list(c.execute('SELECT * FROM package WHERE package_id=? LIMIT 2', (loc['package_id'],)))
        if len(rows) != 1 or rows[0]['strain'] != identity[0] or rows[0]['manifest_sha256'] != loc['package_id'] or not re.fullmatch(r'[0-9a-f]{64}', loc['package_id'] or ''):
            _fail('PACKAGE_PROVENANCE_CONFLICT_HOLD')
        p = dict(rows[0]); p['recorded_context'] = _evidence_json(p.pop('context_json'))
        p['frozen_binding_state'] = loc['frozen_binding_state']
        p['frozen_comparison'] = _evidence_json(loc['frozen_context_json'])
        p['guards'] = _evidence_json(loc['guards_json'])
        packages.append(p)
    result.update(package_occurrences=packages, locus_query_state='MULTIPLE_PACKAGE_OCCURRENCES_NOT_MERGED' if len(loci) > 1 else 'RECORDED_PACKAGE_OCCURRENCE_NOT_ADMITTED')
    table = 'gene' if genes else 'signal'
    order = 'gene_order' if genes else 'channel'
    where = 'l.strain=? AND l.full_node=? AND l.region=? AND l.bgc_alias=?'
    total = c.execute('SELECT count(*) FROM ' + table + ' s JOIN locus l ON l.locus_key=s.locus_key WHERE ' + where, identity).fetchone()[0]
    for loc in loci:
        n, unique = c.execute('SELECT count(*),count(DISTINCT ' + order + ') FROM ' + table + ' WHERE locus_key=?', (loc['locus_key'],)).fetchone()
        if n != unique:
            _fail('DUPLICATE_OR_NULL_PACKAGE_RECORD_HOLD')
    rows = [dict(r) for r in c.execute('SELECT s.*,l.package_id FROM ' + table + ' s JOIN locus l ON l.locus_key=s.locus_key WHERE ' + where + ' ORDER BY l.package_id,s.' + order + ' LIMIT ? OFFSET ?', (*identity, limit, offset))]
    mapping = {'domain_architecture': 'domain', 'antismash_structured': 'domain', 'mibig_per_gene': 'mibig', 'clusterblast_genes': 'clusterblast', 'rggmci': 'rggmci'}
    for row in rows:
        row['exact_identity'] = display
        if genes:
            if type(row['gene_order']) is not int or row['gene_order'] < 0:
                _fail('INVALID_GENE_ORDER_HOLD')
            digest = row['protein_sha256']
            if digest is not None and not re.fullmatch(r'[0-9a-f]{64}', digest):
                _fail('INVALID_PROTEIN_HASH_HOLD')
            if digest is None and 'HOLD' not in row['state']:
                _fail('UNEXPLAINED_MISSING_PROTEIN_HASH_HOLD')
            row['source_fields'] = _evidence_json(row.pop('source_fields_json'))
        else:
            if not re.fullmatch(r'[0-9a-f]{64}', row['source_sha256'] or '') or not row['source_locator'].startswith('package://'):
                _fail('INVALID_SAVED_SOURCE_PROVENANCE_HOLD')
            expected_channel = mapping.get(row['channel'])
            expected_state = 'UNBOUND' if expected_channel else 'UNSUPPORTED_CHANNEL_NOT_COERCED'
            if row['compatible_channel'] != expected_channel or row['evidence_index_state'] != expected_state:
                _fail('UNSUPPORTED_OR_FALSE_BOUND_CHANNEL_HOLD')
            row['recorded_value'] = _unpack(row.pop('raw_zlib'), row.pop('raw_sha256'))
            row['saved_status'] = _evidence_json(row['saved_status'])
    result.update(_page(rows, total, limit, offset))
    return result


def saved_scan_evidence_index_rows(inspection):
    """Project compatible saved context as UNBOUND rows, never evidence admission.

    Caller writes one complete identity at a time using the existing evidence-index
    columns and loader. Variants carry distinct manifest commitments in their notes.
    A page only exports that page; inspect next_offset to obtain remaining records.
    """
    if inspection.get('adapter') != 'package-scan-states-v1':
        _fail('SAVED_SCAN_EXPORT_REQUIRES_SIGNAL_ADAPTER')
    result = inspection.get('results', {})
    if result.get('state') != 'SAVED_PACKAGE_SCAN_CONTEXT_NOT_ADMITTED':
        _fail('INVALID_SAVED_SCAN_EXPORT_HOLD')
    identity = result.get('exact_identity', '').split(' / ')
    if len(identity) != 4 or exact_locus_display(*identity) != result.get('exact_identity'):
        _fail('HELD_IDENTITY_CONFLICT')
    rows = []
    for source in result.get('records', []):
        channel = source.get('compatible_channel')
        if channel is None:
            continue
        if channel not in {'domain', 'mibig', 'clusterblast', 'rggmci'} or source.get('evidence_index_state') != 'UNBOUND':
            _fail('UNSUPPORTED_OR_FALSE_BOUND_CHANNEL_HOLD')
        rows.append(dict(zip(('strain', 'full_node', 'region', 'bgc_alias'), identity), channel=channel, gene='', evidence_state='UNBOUND', source_locator=source['source_locator'], source_sha256=source['source_sha256'], note='Saved package context; no gene/protein admission. package_manifest_sha256=' + source['package_id'] + '; source_channel=' + source['channel'] + '; state=' + source['state']))
    return rows
