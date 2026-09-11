#!/usr/bin/env python3
"""Gene-level protein-homology context against a user-provisioned MIBiG GBK set.

The historical filename is retained for CLI compatibility. This tool does not run
BiG-SCAPE and does not measure chemical or scaffold novelty. BLAST ``pident`` is
reported correctly as percent amino-acid identity. The output is an advisory,
non-ranking Mode B evidence stream: similarity is not identity; a homolog is not a
product assignment; sequence divergence is not proof of chemical novelty.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable


FIELDS = [
    "query_id", "query_sha256", "query_aa_length", "hit_rank",
    "mibig_accession", "subject_id", "subject_locus_tag", "subject_product",
    "subject_sha256", "subject_aa_length", "pct_identity", "pct_positives",
    "alignment_length", "query_coverage_pct", "subject_coverage_pct", "evalue",
    "bitscore", "evidence_state", "bounded_interpretation", "database_metadata",
    "database_receipt",
]


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _md_cell(value: object) -> str:
    """Escape untrusted display text without changing the exact TSV source value."""
    return " ".join(str(value or "").splitlines()).replace("|", r"\|")


def _portable_locator(path: Path, base: Path) -> str:
    """Return a movable locator relative to the artifact that records it."""
    return Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()


def _first(qualifiers: dict, key: str, default: str = "") -> str:
    value = qualifiers.get(key, [default])
    return str(value[0]) if value else default


def _seqio():
    try:
        from Bio import SeqIO  # type: ignore
    except ImportError:
        from mamey._gbk_shim import SeqIO  # type: ignore
    return SeqIO


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
    return token or "unknown"


def _mibig_accession(path: Path, record_id: str) -> str:
    for value in (path.stem, record_id):
        match = re.search(r"BGC\d{7}(?:\.\d+)?", value, re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return _safe_token(path.stem)


def iter_mibig_proteins(mibig_dir: str | Path, min_aa: int = 20) -> Iterable[dict]:
    """Yield sequence-bound CDS records, retaining small RiPP proteins by default."""
    root = Path(mibig_dir).resolve()
    SeqIO = _seqio()
    for gbk in sorted(root.rglob("*.gbk")):
        source_sha = _sha_file(gbk)
        for rec in SeqIO.parse(str(gbk), "genbank"):
            accession = _mibig_accession(gbk, str(rec.id))
            cds_index = 0
            for feature in rec.features:
                if feature.type != "CDS" or "translation" not in feature.qualifiers:
                    continue
                sequence = "".join(_first(feature.qualifiers, "translation").split()).upper()
                if len(sequence) < min_aa:
                    continue
                cds_index += 1
                locus_tag = _first(feature.qualifiers, "locus_tag")
                protein_id = _first(feature.qualifiers, "protein_id")
                gene = _first(feature.qualifiers, "gene")
                protein_key = locus_tag or protein_id or gene or f"cds{cds_index}"
                subject_id = f"MIBIG__{_safe_token(accession)}__{_safe_token(protein_key)}__{cds_index}"
                yield {
                    "subject_id": subject_id,
                    "mibig_accession": accession,
                    "record_id": str(rec.id),
                    "locus_tag": locus_tag,
                    "protein_id": protein_id,
                    "gene": gene,
                    "product": _first(feature.qualifiers, "product"),
                    "aa_length": len(sequence),
                    "protein_sha256": _sha_text(sequence),
                    "sequence": sequence,
                    "source_gbk": str(gbk.relative_to(root)),
                    "source_gbk_sha256": source_sha,
                }


def build_db(mibig_dir: str, db: str, *, mibig_release: str, min_aa: int = 20) -> dict:
    mibig_release = mibig_release.strip()
    if not mibig_release:
        raise ValueError("mibig_release is required for a versioned database receipt")
    db_path = Path(db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    faa = Path(f"{db}_proteins.faa")
    metadata = Path(f"{db}_metadata.tsv")
    source_manifest = Path(f"{db}_source_manifest.tsv")
    receipt = Path(f"{db}_build_receipt.json")
    rows = list(iter_mibig_proteins(mibig_dir, min_aa=min_aa))
    if not rows:
        raise ValueError("No translated CDS records were admitted from the supplied MIBiG GBKs")
    if len({row["subject_id"] for row in rows}) != len(rows):
        raise ValueError("Generated MIBiG subject IDs are not unique")

    with faa.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(f">{row['subject_id']}\n{row['sequence']}\n")
    meta_fields = [key for key in rows[0] if key != "sequence"]
    with metadata.open("w", encoding="utf-8", newline="") as out:
        writer = _SafeDictWriter(out, fieldnames=meta_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows({key: row[key] for key in meta_fields} for row in rows)

    source_rows = sorted({(row["source_gbk"], row["source_gbk_sha256"]) for row in rows})
    with source_manifest.open("w", encoding="utf-8", newline="") as out:
        writer = _SafeWriter(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["source_gbk", "sha256"])
        writer.writerows(source_rows)

    subprocess.run(
        ["makeblastdb", "-in", str(faa), "-dbtype", "prot", "-out", str(db_path)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    clusters = sorted({row["mibig_accession"] for row in rows})
    payload = {
        "schema": "mibig_protein_context_db_v1",
        "mibig_release": mibig_release,
        "mibig_source_root_label": Path(mibig_dir).resolve().name,
        "minimum_aa_length": min_aa,
        "cluster_count": len(clusters),
        "protein_count": len(rows),
        "fasta": _portable_locator(faa, receipt.parent),
        "fasta_sha256": _sha_file(faa),
        "metadata": _portable_locator(metadata, receipt.parent),
        "metadata_sha256": _sha_file(metadata),
        "source_manifest": _portable_locator(source_manifest, receipt.parent),
        "source_manifest_sha256": _sha_file(source_manifest),
        "claim_ceiling": "protein homology context only; not product identity or chemical novelty",
    }
    receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    emit(f"built {db}: {len(rows)} proteins from {len(clusters)} cluster accessions")
    return payload


def read_fasta(path: str | Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    current_id = ""
    chunks: list[str] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_id:
                records.append((current_id, "".join(chunks).upper()))
            current_id = line[1:].split()[0]
            chunks = []
        else:
            if not current_id:
                raise ValueError("FASTA sequence encountered before the first header")
            chunks.append(re.sub(r"\s+", "", line))
    if current_id:
        records.append((current_id, "".join(chunks).upper()))
    if not records:
        raise ValueError("No query proteins found")
    if len({record[0] for record in records}) != len(records):
        raise ValueError("Query FASTA identifiers must be unique")
    return records


def load_metadata(path: str | Path) -> dict[str, dict]:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return {row["subject_id"]: row for row in csv.DictReader(fh, delimiter="\t")}


def bounded_interpretation(
    *, exact_sequence: bool, pct_identity: float, query_coverage: float,
    subject_coverage: float, evalue: float, min_qcov: float, min_scov: float,
    max_evalue: float,
) -> tuple[str, str]:
    if evalue > max_evalue:
        return "BELOW_ADMISSION_THRESHOLD", "not admitted; weaker than the declared E-value threshold"
    if query_coverage < min_qcov or subject_coverage < min_scov:
        return (
            "PARTIAL_OR_LOW_BIDIRECTIONAL_COVERAGE_HIT",
            "partial protein-level context; query and subject coverage do not support a whole-protein interpretation",
        )
    if exact_sequence:
        return "EXACT_SEQUENCE_MATCH_TO_MIBIG_PROTEIN", "exact protein sequence occurs in the supplied MIBiG reference set; cluster/product equivalence not established"
    if pct_identity >= 90 and subject_coverage >= 60:
        return "CLOSE_MIBIG_PROTEIN_HOMOLOG", "close protein homolog in a characterized-cluster reference; function and product remain hypotheses"
    if pct_identity >= 55:
        return "MIBIG_PROTEIN_HOMOLOG", "protein homology supports class or role context only"
    return "DISTANT_MIBIG_PROTEIN_CONTEXT", "distant sequence context; divergence is a novelty prior, not proof of a new scaffold"


def parse_blast_rows(
    stdout: str, queries: list[tuple[str, str]], metadata: dict[str, dict],
    min_qcov: float, max_evalue: float, min_scov: float = 60.0,
) -> list[dict]:
    query_map = {qid: seq for qid, seq in queries}
    hits: dict[str, list[dict]] = {qid: [] for qid, _ in queries}
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        fields = raw.split("\t")
        if len(fields) != 13:
            raise ValueError(f"Unexpected BLAST outfmt row with {len(fields)} fields")
        qid, sid = fields[0], fields[1]
        if qid not in query_map:
            raise ValueError(f"BLAST returned unknown query ID: {qid}")
        if sid not in metadata:
            raise ValueError(f"BLAST subject lacks sequence-bound metadata: {sid}")
        pid, ppos = float(fields[2]), float(fields[3])
        aln_len, qlen, slen = map(int, fields[4:7])
        qstart, qend, sstart, send = map(int, fields[7:11])
        evalue, bitscore = float(fields[11]), float(fields[12])
        qcov = 100.0 * (abs(qend - qstart) + 1) / qlen if qlen else 0.0
        scov = 100.0 * (abs(send - sstart) + 1) / slen if slen else 0.0
        meta = metadata[sid]
        exact = _sha_text(query_map[qid]) == meta.get("protein_sha256", "")
        state, interpretation = bounded_interpretation(
            exact_sequence=exact, pct_identity=pid, query_coverage=qcov,
            subject_coverage=scov, evalue=evalue, min_qcov=min_qcov,
            min_scov=min_scov, max_evalue=max_evalue,
        )
        hits[qid].append({
            "query_id": qid, "query_sha256": _sha_text(query_map[qid]),
            "query_aa_length": qlen, "mibig_accession": meta.get("mibig_accession", ""),
            "subject_id": sid, "subject_locus_tag": meta.get("locus_tag", ""),
            "subject_product": meta.get("product", ""),
            "subject_sha256": meta.get("protein_sha256", ""), "subject_aa_length": slen,
            "pct_identity": f"{pid:.3f}", "pct_positives": f"{ppos:.3f}",
            "alignment_length": aln_len, "query_coverage_pct": f"{qcov:.3f}",
            "subject_coverage_pct": f"{scov:.3f}", "evalue": f"{evalue:.6g}",
            "bitscore": f"{bitscore:.3f}", "evidence_state": state,
            "bounded_interpretation": interpretation,
        })

    output: list[dict] = []
    for qid, sequence in queries:
        ranked = sorted(
            hits[qid],
            key=lambda row: (-float(row["bitscore"]), -float(row["query_coverage_pct"]),
                             -float(row["pct_identity"]), row["subject_id"]),
        )
        if not ranked:
            output.append({
                "query_id": qid, "query_sha256": _sha_text(sequence),
                "query_aa_length": len(sequence), "hit_rank": 0,
                "evidence_state": "NO_ADMITTED_MIBIG_PROTEIN_HIT",
                "bounded_interpretation": "no hit returned at the declared thresholds in this database/run; not biological absence or proof of novelty",
            })
            continue
        for rank, row in enumerate(ranked, 1):
            row["hit_rank"] = rank
            output.append(row)
    return output


def query(
    targets: str, db: str, out: str, *, max_targets: int = 5,
    min_qcov: float = 60.0, min_scov: float = 60.0, max_evalue: float = 1e-5,
) -> list[dict]:
    queries = read_fasta(targets)
    metadata_path = Path(f"{db}_metadata.tsv")
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing sequence-bound database metadata: {metadata_path}")
    receipt_path = Path(f"{db}_build_receipt.json")
    if not receipt_path.is_file():
        raise FileNotFoundError(f"Missing versioned database build receipt: {receipt_path}")
    receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt_data.get("schema") != "mibig_protein_context_db_v1":
        raise ValueError("Database receipt schema is missing or unsupported")
    if not str(receipt_data.get("mibig_release", "")).strip():
        raise ValueError("Database receipt lacks mibig_release")
    if receipt_data.get("metadata_sha256") != _sha_file(metadata_path):
        raise ValueError("Database metadata does not match the build receipt")
    source_manifest = Path(str(receipt_data.get("source_manifest", "")))
    if not source_manifest.is_absolute():
        source_manifest = (receipt_path.parent / source_manifest).resolve()
    if not source_manifest.is_file() or receipt_data.get("source_manifest_sha256") != _sha_file(source_manifest):
        raise ValueError("MIBiG source manifest is missing or does not match the build receipt")
    metadata = load_metadata(metadata_path)
    outfmt = "6 qseqid sseqid pident ppos length qlen slen qstart qend sstart send evalue bitscore"
    result = subprocess.run(
        ["blastp", "-query", targets, "-db", db, "-num_threads", "1",
         "-max_target_seqs", str(max_targets), "-max_hsps", "1",
         "-evalue", str(max_evalue), "-outfmt", outfmt],
        capture_output=True, text=True, check=True,
    )
    rows = parse_blast_rows(result.stdout, queries, metadata, min_qcov, max_evalue, min_scov)
    database_metadata_sha = _sha_file(metadata_path)
    database_receipt_sha = _sha_file(receipt_path)
    out_path = Path(out)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = _SafeDictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                **row,
                "database_metadata": (
                    f"{_portable_locator(metadata_path, out_path.parent)};"
                    f"sha256={database_metadata_sha}"
                ),
                "database_receipt": (
                    f"{_portable_locator(receipt_path, out_path.parent)};"
                    f"sha256={database_receipt_sha}"
                ),
            })
    emit(f"wrote {out}: {len(queries)} queries, {len(rows)} query/hit-state rows; values are percent identity and coverage")
    return rows


def render_modeb(results: str, out: str) -> str:
    with Path(results).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = sorted(set(FIELDS) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError("MIBiG context TSV lacks required columns: " + ", ".join(missing))
        rows = list(reader)
    lines = [
        "### MIBiG protein-homology context", "",
        "Route this table into Mode B §4, reconcile it in §8 and §11, record limitations and next steps in §15-§16, use only as a bounded prior in §24, cite the source in §28, and use admitted comparator proteins to plan §39-§41 and §46-§47 analyses.",
        "",
        "| Query | Best MIBiG protein context | % identity | Query coverage | Subject coverage | E-value | Evidence state | Interpretation |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    best: dict[str, dict] = {}
    for row in rows:
        qid = row.get("query_id", "")
        rank = int(row.get("hit_rank") or 0)
        if qid not in best or rank in (0, 1):
            best[qid] = row
    for qid in sorted(best):
        row = best[qid]
        subject = _md_cell(row.get("mibig_accession") or "no admitted hit")
        if row.get("subject_locus_tag"):
            subject += f" / {_md_cell(row['subject_locus_tag'])}"
        lines.append(
            f"| {_md_cell(qid)} | {subject} | {_md_cell(row.get('pct_identity') or 'NA')} | "
            f"{_md_cell(row.get('query_coverage_pct') or 'NA')} | {_md_cell(row.get('subject_coverage_pct') or 'NA')} | "
            f"{_md_cell(row.get('evalue') or 'NA')} | {_md_cell(row.get('evidence_state', ''))} | "
            f"{_md_cell(row.get('bounded_interpretation', ''))} |"
        )
    lines.extend([
        "",
        "**Claim ceiling.** These rows describe protein homology within the supplied, versioned MIBiG reference set. They do not establish the BGC product, pathway completeness, production, bioactivity, self-hit status, or chemical novelty. Interpret the locus from the multi-gene biosynthetic logic chain and cluster-level comparators, not from a single protein.",
    ])
    text = "\n".join(lines) + "\n"
    Path(out).write_text(text, encoding="utf-8")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("--mibig-dir", required=True)
    build.add_argument("--db", default="mibig_db")
    build.add_argument("--mibig-release", required=True,
                       help="exact supplied MIBiG release identifier, recorded in the build receipt")
    build.add_argument("--min-aa", type=int, default=20)
    run = sub.add_parser("query")
    run.add_argument("--targets", required=True)
    run.add_argument("--db", default="mibig_db")
    run.add_argument("--out", default="mibig_protein_context.tsv")
    run.add_argument("--max-targets", type=int, default=5)
    run.add_argument("--min-query-coverage", type=float, default=60.0)
    run.add_argument("--min-subject-coverage", type=float, default=60.0)
    run.add_argument("--max-evalue", type=float, default=1e-5)
    modeb = sub.add_parser("modeb")
    modeb.add_argument("--results", required=True)
    modeb.add_argument("--out", default="modeb_mibig_protein_context.md")
    args = parser.parse_args()
    if args.cmd == "build":
        build_db(args.mibig_dir, args.db, mibig_release=args.mibig_release, min_aa=args.min_aa)
    elif args.cmd == "query":
        query(args.targets, args.db, args.out, max_targets=args.max_targets,
              min_qcov=args.min_query_coverage, min_scov=args.min_subject_coverage,
              max_evalue=args.max_evalue)
    else:
        render_modeb(args.results, args.out)


if __name__ == "__main__":
    main()
