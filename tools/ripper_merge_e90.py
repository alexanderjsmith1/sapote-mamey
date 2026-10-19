"""Owned e90 merge proposal. Does not execute or attest HMM annotation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys

UPSTREAM_MERGE_SHA256 = "53a2418b860d413fc1e7b7b3170026e6f637b5092fe0d2b4712fd0c11969f051"
REVISION = "e90b3e6e74ddee99685183ca421323737012a991"
RAW_COLUMNS = "acc species ppser fastaid aaseq ppstrand testrand pptedist score".split()
HEADERS = "Accession Organism PPSerial FastaID Sequence SameStrand PP_TE_Distance Prodigalscore hname signif hdesc".split()
COLLECTIONS = {"pfam", "ripp"}
COMPLETE = {"COMPLETE_HIT", "COMPLETE_NO_HIT"}
STATES = COMPLETE | {"NOT_RUN", "UNAVAILABLE", "FAILED", "INTERRUPTED", "AMBIGUOUS"}
MAX_INPUT_BYTES = 16 * 1024 * 1024


class Refused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Refused(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value), "TABLE_IDENTIFIER_INVALID")
    return value


def text(value):
    require(value is not None and isinstance(value, (str, int, float)), "CELL_TYPE_INVALID")
    if isinstance(value, float):
        require(math.isfinite(value), "NONFINITE_CELL")
    result = str(value)
    require(not any(char in result for char in "\x00\t\r\n"), "TSV_CELL_DELIMITER")
    return result


def bound_bytes(role):
    require(isinstance(role, dict) and set(role) == {"path", "sha256"}, "FILE_ROLE_INVALID")
    require(isinstance(role["path"], str) and isinstance(role["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", role["sha256"]), "FILE_ROLE_INVALID")
    path = Path(role["path"])
    require(path.is_absolute() and path.is_file() and not path.is_symlink(), "ORDINARY_ABSOLUTE_INPUT_REQUIRED")
    before = path.stat()
    require(before.st_size <= MAX_INPUT_BYTES, "INPUT_BYTE_BUDGET")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "INPUT_CHANGED_DURING_READ")
    require(len(data) == before.st_size and digest(data) == role["sha256"], "INPUT_HASH_MISMATCH")
    return path, data


def checked_schema(db, raw_table, hit_table):
    raw = identifier(raw_table)
    hits = identifier(hit_table)
    raw_info = db.execute("pragma table_info(" + raw + ")").fetchall()
    hit_info = db.execute("pragma table_info(" + hits + ")").fetchall()
    require([row[1] for row in raw_info] == RAW_COLUMNS, "RAW_SCHEMA_MISMATCH")
    require({"qname", "hname", "signif", "hdesc", "collection"} <= {row[1] for row in hit_info}, "HIT_SCHEMA_MISMATCH")
    return {row[1]: row[2] for row in hit_info}


def render(db, coverage, raw_table="ripper", hit_table="pfamscan"):
    """Execute the source-derived SQLite selection; retain source affinity ordering."""
    affinity = checked_schema(db, raw_table, hit_table)
    db.row_factory = sqlite3.Row
    raw_rows = db.execute("select * from " + raw_table + " order by species").fetchall()
    ids = [row["fastaid"] for row in raw_rows]
    require(len(ids) == len(set(ids)), "AMBIGUOUS_RAW_FASTA_ID")
    require(all(isinstance(value, str) and value and not re.search(r"\s|\x00", value) for value in ids), "RAW_FASTA_ID_INVALID")
    require(isinstance(coverage, dict) and coverage.get("schema") == "ripper-annotation-coverage-proposal/1", "COVERAGE_SCHEMA")
    provenance = coverage.get("execution_provenance")
    require(isinstance(provenance, str) and provenance in
            {"FABRICATED_SOFTWARE_CONTROL", "OPERATOR_DECLARED_UNATTESTED"}, "PROVENANCE_INVALID")
    require(isinstance(coverage.get("pairs"), list), "PAIR_ROSTER_INVALID")
    pairs = {}
    for pair in coverage["pairs"]:
        require(isinstance(pair, dict) and set(pair) == {"FastaID", "collection", "state"}, "PAIR_INVALID")
        require(all(isinstance(pair[key], str) for key in ("FastaID", "collection", "state")), "PAIR_INVALID")
        key = (pair["FastaID"], pair["collection"])
        require(key[0] in ids and key[1] in COLLECTIONS and pair["state"] in STATES, "PAIR_IDENTITY_STATE")
        require(key not in pairs, "DUPLICATE_PAIR")
        pairs[key] = pair["state"]
    require(set(pairs) == {(item, collection) for item in ids for collection in COLLECTIONS}, "MISSING_PAIR")
    require(all(state in COMPLETE for state in pairs.values()), "ANNOTATION_INCOMPLETE")
    hit_rows = db.execute("select * from " + hit_table).fetchall()
    for hit in hit_rows:
        require(hit["qname"] in ids and hit["collection"] in COLLECTIONS, "UNBOUND_HIT_QUERY_COLLECTION")
        for key in ("hname", "signif", "hdesc"):
            text(hit[key])
        require(hit["hname"] not in {"", "none"}, "HIT_NAME_INVALID")
        try:
            number = float(hit["signif"])
        except (ValueError, TypeError):
            raise Refused("SIGNIFICANCE_INVALID") from None
        require(math.isfinite(number) and number >= 0, "SIGNIFICANCE_INVALID")
    for key, state in pairs.items():
        present = any((row["qname"], row["collection"]) == key for row in hit_rows)
        require(present == (state == "COMPLETE_HIT"), "PAIR_HIT_NOHIT_CONTRADICTION")
    main, distant, traces = [], [], []
    for row in raw_rows:
        fid = row["fastaid"]
        is_distant = re.search(r"_9\d{3,}$", fid) is not None
        # Exact producer/query identity must not inherit a NOCASE join.
        # Keep significance ordering under its actual SQLite comparator.
        sql = "select dense_rank() over (order by signif), * from " + hit_table
        sql += " where qname collate binary = ?"
        if is_distant:
            sql += " and collection = 'ripp'"
        sql += " order by signif"
        eligible = db.execute(sql, (fid,)).fetchall()
        require(all(item["qname"] == fid for item in eligible), "QUERY_COMPARISON_IDENTITY_MISMATCH")
        # Source chooses its first tied row without a secondary ORDER BY.
        # This proposal deliberately holds a tie rather than inventing a winner.
        # The leading rank is SQLite's ORDER BY peer group, not Python
        # equality or an invented numeric conversion of stored TEXT.
        require(len(eligible) < 2 or eligible[0][0] != eligible[1][0], "AMBIGUOUS_BEST_HIT_TIE")
        hit = eligible[0] if eligible else None
        values = [row[key] for key in ("acc", "species", "ppser", "fastaid", "aaseq")]
        require(row["ppstrand"] in {-1, 1} and row["testrand"] in {-1, 1}, "STRAND_INVALID")
        values += ["yes" if row["ppstrand"] == row["testrand"] else "no", row["pptedist"], row["score"]]
        values += [hit[key] for key in ("hname", "signif", "hdesc")] if hit else ["none"] * 3
        values = [text(value) for value in values]
        require(re.fullmatch(r"[A-Za-z*.-]+", values[4]), "FASTA_SEQUENCE_INVALID")
        admitted = not is_distant or hit is not None
        if admitted:
            (distant if is_distant else main).append(values)
        def hit_record(item):
            return {key: item[key] for key in ("qname", "hname", "signif", "hdesc", "collection")}
        traces.append({"FastaID": fid, "source_channel": "distant" if is_distant else "main",
                       "admitted": admitted, "selected_hit": hit_record(hit) if hit else None,
                       "eligible_hits": [hit_record(item) for item in eligible]})
    header = "\t".join(HEADERS) + "\n"
    def tsv(rows):
        return header + "".join("\t".join(row) + "\n" for row in rows)
    def fasta(rows):
        return "".join(">RiPP|" + row[3] + "\n" + "".join(row[4][i:i+60] + "\n" for i in range(0, len(row[4]), 60)) for row in rows)
    files = {"out.txt": tsv(main), "out.faa": fasta(main), "distant.txt": tsv(distant), "distant.faa": fasta(distant)}
    receipt = {"schema": "ripper-e90-merge-proposal/1", "state": "COMPLETE_MERGE_DECLARED_INPUTS",
               "source_revision": REVISION, "upstream_merge_sha256": UPSTREAM_MERGE_SHA256,
               "execution_provenance": provenance, "annotation_execution": "NOT_OBSERVED_BY_MERGE_ADAPTER",
               "annotation_source_compatibility": "UNVERIFIED_PARSER_BODY_UNREAD",
               "canonical_import": "NOT_ADMITTED", "biology": "UNASSESSED", "artifact_export_permission": False,
               "raw_input_count": len(raw_rows), "main_output_count": len(main), "distant_output_count": len(distant),
               "all_output_count": len(main) + len(distant), "hit_table_affinities": affinity,
               "query_identity_comparison": "SQLite BINARY predicate plus exact eligible qname guard",
               "significance_order": "SQLite ORDER BY signif under supplied column affinity/collation",
               "significance_tie_comparison": "SQLite dense_rank ORDER BY signif peer groups",
               "scope": "owned SQL merge executed; no HMM/model/precursor validation or upstream Perl execution",
               "departures": ["ambiguous best-hit tie holds", "exact query identity comparison", "coverage/hash/schema/scope guards",
                              "owned numeric/FASTA serialization; semantic compatibility, not byte equivalence"]}
    files["MERGE_TRACE.json"] = json.dumps({"rows": traces}, indent=2) + "\n"
    return files, receipt


def write_staging(path, data):
    with path.open("xb") as stream:
        written = stream.write(data)
        require(written == len(data), "OUTPUT_SHORT_WRITE")
        stream.flush()


def publish(out, files, receipt):
    out = Path(out)
    require(out.is_absolute() and out.parent.is_dir() and not out.parent.is_symlink(), "OUTPUT_PARENT_INVALID")
    require(not out.exists() and not out.is_symlink(), "OUTPUT_OCCUPIED")
    out.mkdir(mode=0o700)
    encoded = {name: value.encode("utf-8") for name, value in files.items()}
    receipt["outputs"] = [{"name": name, "bytes": len(data), "sha256": digest(data)} for name, data in encoded.items()]
    encoded["MERGE_RESULT.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    for name, data in encoded.items():
        write_staging(out / (name + ".staging"), data)
    for name in files:
        os.link(out / (name + ".staging"), out / name)
    # The result is the last publication, after all output streams closed.
    os.link(out / "MERGE_RESULT.json.staging", out / "MERGE_RESULT.json")
    return receipt


def run(spec, out):
    require(isinstance(spec, dict) and set(spec) == {"database", "coverage", "raw_table", "hit_table"}, "SPEC_INVALID")
    path, database = bound_bytes(spec["database"])
    _, coverage_bytes = bound_bytes(spec["coverage"])
    require(not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")), "SQLITE_SIDECAR_REFUSED")
    uri = path.as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("pragma query_only=on")
        files, receipt = render(db, json.loads(coverage_bytes), identifier(spec["raw_table"]), identifier(spec["hit_table"]))
    _, after = bound_bytes(spec["database"])
    require(database == after, "DATABASE_CHANGED_DURING_MERGE")
    bound_bytes(spec["coverage"])
    receipt["input_bindings"] = {"database": spec["database"], "coverage": spec["coverage"]}
    return publish(out, files, receipt)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = run(json.loads(Path(args.spec).read_text()), args.out)
    except (Refused, OSError, sqlite3.Error, ValueError) as exc:
        sys.stdout.write(json.dumps({"state": "HOLD_OR_REFUSED", "reason": str(exc), "candidate_count": None,
                                     "annotation_execution": "NOT_OBSERVED_BY_MERGE_ADAPTER"}) + "\n")
        return 2
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
