"""Portable exact-locus AS/SID/reference BGC-protein comparison.

This post-seal module builds a content-addressed protein-occurrence catalog from
ordinary Mamey package directories, then ranks focal BGC proteins against each
named cohort.  It is deliberately separate from NCBI nr, ClusteredNR and
Swiss-Prot: this is a measured *within-project* comparison channel.

Protein SHA-256 is the molecular identity.  The occurrence identity is the
complete ``strain / full node-or-contig / region / BGC alias`` display plus
locus tag and protein SHA.  Similarity is not identity; neighborhood recurrence
is not pathway identity; capacity is not production.
"""
from __future__ import annotations

import sys as _sys
def emit(*a, **k):
    """print-compatible writer; holds strict-health print_calls flat."""
    k.pop("file", None); end = k.pop("end", "\n"); sep = k.pop("sep", " ")
    _sys.stdout.write(sep.join(str(x) for x in a) + end)

import argparse
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import heapq
import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


SCHEMA = "mamey.cohort-protein-occurrence/1"
CLAIM_CEILING = (
    "Within-project protein similarity and exact-neighborhood navigation only; "
    "not orthology, identical function, pathway identity, product, production, "
    "activity, resistance, ecology, or novelty."
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_sequence(value: str) -> str:
    sequence = re.sub(r"\s+", "", value).upper().rstrip("*")
    if not sequence or re.search(r"[^A-Z]", sequence):
        raise ValueError("protein sequence is empty or contains non-letter symbols")
    return sequence


def _parse_fasta(path: Path) -> Iterator[tuple[str, str, str]]:
    header = ""
    parts: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header:
                    yield header.split()[0], header, _clean_sequence("".join(parts))
                header, parts = line[1:].strip(), []
            else:
                parts.append(line)
    if header:
        yield header.split()[0], header, _clean_sequence("".join(parts))


def _one(package: Path, pattern: str) -> Path:
    candidates = sorted(package.glob(pattern))
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one {pattern} under {package}; found {len(candidates)}")
    return candidates[0]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _exact_display(strain: str, node: str, region: str, alias: str) -> str:
    values = (strain.strip(), node.strip(), region.strip(), alias.strip())
    if not all(values):
        raise ValueError("exact-locus display is incomplete")
    return " / ".join(values)


def _package_strain(package: Path, inventory_rows: list[dict[str, str]]) -> str:
    intake = sorted(package.glob("*_1_intake.json"))
    if len(intake) == 1:
        value = json.loads(intake[0].read_text(encoding="utf-8")).get("strain_id")
        if value:
            return str(value)
    if inventory_rows:
        name = next(iter(package.glob("*_2_inventory.csv"))).name
        return name.split("_2_inventory.csv")[0]
    raise ValueError(f"cannot resolve strain for {package}")


def _discover_packages(root: Path) -> list[Path]:
    root = root.resolve()
    if root.is_dir() and list(root.glob("*_2_inventory.csv")):
        return [root]
    found = {path.parent.resolve() for path in root.rglob("*_2_inventory.csv")}
    return sorted(found)


def _parse_cohort_root(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("cohort root must be LABEL=PATH")
    label, raw_path = value.split("=", 1)
    if not label.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("cohort root must be LABEL=PATH")
    return label.strip(), Path(raw_path).expanduser().resolve()


def _gene_context(package: Path) -> dict[tuple[str, str], dict[str, str]]:
    files = sorted(package.glob("*_gene_by_gene_all_bgcs.csv"))
    if len(files) != 1:
        return {}
    return {(row.get("bgc_id", ""), row.get("locus_tag", "")): row for row in _read_rows(files[0])}


def _package_occurrences(cohort: str, package: Path) -> tuple[list[dict], list[dict]]:
    inventory_path = _one(package, "*_2_inventory.csv")
    fasta_path = _one(package, "*_proteins.faa")
    inventory_rows = _read_rows(inventory_path)
    strain = _package_strain(package, inventory_rows)
    inventory = {row.get("BGC_ID", ""): row for row in inventory_rows}
    context = _gene_context(package)
    inv_sha = _sha256_file(inventory_path)
    fasta_sha = _sha256_file(fasta_path)
    occurrences: list[dict] = []
    quarantine: list[dict] = []
    for gene, header, sequence in _parse_fasta(fasta_path):
        match = re.search(r"(?:^|\s)bgc=(BGC\d+)(?:\s|$)", header)
        alias = match.group(1) if match else ""
        row = inventory.get(alias)
        if not alias or not row:
            quarantine.append({
                "cohort": cohort, "package": str(package), "gene": gene,
                "state": "QUARANTINED_MISSING_BGC_OR_INVENTORY_BINDING",
            })
            continue
        node = row.get("Contig", "")
        region = row.get("antiSMASH_Region", "")
        try:
            display = _exact_display(strain, node, region, alias)
        except ValueError:
            quarantine.append({
                "cohort": cohort, "package": str(package), "gene": gene,
                "state": "QUARANTINED_INCOMPLETE_EXACT_LOCUS",
            })
            continue
        ctx = context.get((alias, gene), {})
        occurrences.append({
            "cohort": cohort, "strain": strain, "full_node_or_contig": node,
            "region": region, "bgc_alias": alias, "exact_locus": display,
            "locus_tag": gene, "gene_order": ctx.get("rank", ""),
            "start_1based": ctx.get("cds_start", ""), "end_1based": ctx.get("cds_end", ""),
            "strand": ctx.get("strand", ""), "aa_length": len(sequence),
            "protein_sha256": _sha256_bytes(sequence.encode("ascii")), "sequence": sequence,
            "product": ctx.get("product_qualifier", ""),
            "sec_met_domains": ctx.get("sec_met_domains", ""),
            "gene_function_inference": ctx.get("gene_function_inference", ""),
            "edge_core_overlap": ctx.get("edge_core_overlap", ""),
            "resistance_tier": ctx.get("resistance_tier", ""),
            "source_package": str(package), "source_fasta": str(fasta_path),
            "source_fasta_sha256": fasta_sha, "source_inventory": str(inventory_path),
            "source_inventory_sha256": inv_sha,
        })
    return occurrences, quarantine


def _gbk_register_occurrences(register: Path) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Extract translated CDSs from a governed exact-locus GBK register.

    Required TSV columns are ``cohort,strain,full_node_or_contig,region,``
    ``bgc_alias,gbk_path``.  The adapter is intentionally register-driven: it
    never infers a strain or alias from a filename.
    """
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError("--gbk-register requires the optional bio extra: pip install 'mamey[bio]'") from exc
    with register.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"cohort", "strain", "full_node_or_contig", "region", "bgc_alias", "gbk_path"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"GBK register missing columns: {sorted(missing)}")
        source_rows = list(reader)
    occurrences: list[dict] = []
    quarantine: list[dict] = []
    row_counts: dict[str, int] = defaultdict(int)
    register_sha = _sha256_file(register)
    for source in source_rows:
        cohort = source["cohort"].strip()
        row_counts[cohort] += 1
        path = Path(source["gbk_path"]).expanduser().resolve()
        try:
            display = _exact_display(
                source["strain"], source["full_node_or_contig"], source["region"], source["bgc_alias"]
            )
        except ValueError:
            quarantine.append({"cohort": cohort, "package": str(register), "gene": "",
                               "state": "QUARANTINED_INCOMPLETE_EXACT_LOCUS_REGISTER_ROW"})
            continue
        if not path.is_file():
            quarantine.append({"cohort": cohort, "package": str(register), "gene": "",
                               "state": f"QUARANTINED_GBK_NOT_FOUND: {path}"})
            continue
        expected_sha = source.get("gbk_sha256", "").strip()
        actual_sha = _sha256_file(path)
        if expected_sha and expected_sha != actual_sha:
            quarantine.append({"cohort": cohort, "package": str(register), "gene": "",
                               "state": f"QUARANTINED_GBK_SHA_MISMATCH: {path}"})
            continue
        try:
            record = SeqIO.read(path, "genbank")
        except Exception as exc:
            quarantine.append({"cohort": cohort, "package": str(register), "gene": "",
                               "state": f"QUARANTINED_GBK_PARSE_FAILURE: {type(exc).__name__}: {path}"})
            continue
        order = 0
        for feature in record.features:
            if feature.type != "CDS" or not feature.qualifiers.get("translation"):
                continue
            order += 1
            gene = feature.qualifiers.get("locus_tag", [""])[0]
            if not gene:
                quarantine.append({"cohort": cohort, "package": str(register), "gene": f"CDS_ORDER_{order}",
                                   "state": "QUARANTINED_CDS_MISSING_LOCUS_TAG"})
                continue
            sequence = _clean_sequence(feature.qualifiers["translation"][0])
            occurrences.append({
                "cohort": cohort, "strain": source["strain"],
                "full_node_or_contig": source["full_node_or_contig"], "region": source["region"],
                "bgc_alias": source["bgc_alias"], "exact_locus": display, "locus_tag": gene,
                "gene_order": order, "start_1based": int(feature.location.start) + 1,
                "end_1based": int(feature.location.end), "strand": str(int(feature.location.strand or 0)),
                "aa_length": len(sequence), "protein_sha256": _sha256_bytes(sequence.encode("ascii")),
                "sequence": sequence, "product": feature.qualifiers.get("product", [""])[0],
                "sec_met_domains": ";".join(feature.qualifiers.get("sec_met_domain", [])),
                "gene_function_inference": ";".join(feature.qualifiers.get("gene_functions", [])),
                "edge_core_overlap": "", "resistance_tier": "",
                "source_package": "REGISTER_DRIVEN_GBK_SOURCE", "source_fasta": str(path),
                "source_fasta_sha256": actual_sha, "source_inventory": str(register),
                "source_inventory_sha256": register_sha,
            })
    return occurrences, quarantine, dict(row_counts)


_OCCURRENCE_COLUMNS = [
    "cohort", "strain", "full_node_or_contig", "region", "bgc_alias", "exact_locus",
    "locus_tag", "gene_order", "start_1based", "end_1based", "strand", "aa_length",
    "protein_sha256", "sequence", "product", "sec_met_domains", "gene_function_inference",
    "edge_core_overlap", "resistance_tier", "source_package", "source_fasta",
    "source_fasta_sha256", "source_inventory", "source_inventory_sha256",
]


def build_catalog(cohort_roots: Iterable[tuple[str, Path]], out: Path, *, replace: bool = False,
                  gbk_registers: Iterable[Path] = ()) -> dict:
    """Build a content-addressed occurrence catalog from Mamey packages."""
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not replace:
        raise FileExistsError(f"catalog already exists: {out}; pass --replace to rebuild")
    all_rows: list[dict] = []
    quarantine: list[dict] = []
    packages_by_cohort: dict[str, int] = defaultdict(int)
    for cohort, root in cohort_roots:
        packages = _discover_packages(root)
        if not packages:
            quarantine.append({"cohort": cohort, "package": str(root), "gene": "",
                               "state": "QUARANTINED_NO_PACKAGES_DISCOVERED"})
        for package in packages:
            packages_by_cohort[cohort] += 1
            try:
                rows, held = _package_occurrences(cohort, package)
                all_rows.extend(rows)
                quarantine.extend(held)
            except (FileNotFoundError, ValueError) as exc:
                quarantine.append({"cohort": cohort, "package": str(package), "gene": "",
                                   "state": f"QUARANTINED_PACKAGE_BINDING_FAILURE: {exc}"})
    gbk_register_rows_by_cohort: dict[str, int] = defaultdict(int)
    for register in gbk_registers:
        try:
            rows, held, counts = _gbk_register_occurrences(Path(register).expanduser().resolve())
            all_rows.extend(rows)
            quarantine.extend(held)
            for cohort, count in counts.items():
                gbk_register_rows_by_cohort[cohort] += count
                packages_by_cohort.setdefault(cohort, 0)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            quarantine.append({"cohort": "REGISTER", "package": str(register), "gene": "",
                               "state": f"QUARANTINED_GBK_REGISTER_FAILURE: {exc}"})
    with tempfile.NamedTemporaryFile(prefix=out.name + ".", suffix=".tmp", dir=out.parent, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        con = sqlite3.connect(temp_path)
        con.executescript("""
          CREATE TABLE protein_occurrence (
            occurrence_id INTEGER PRIMARY KEY,
            cohort TEXT NOT NULL, strain TEXT NOT NULL, full_node_or_contig TEXT NOT NULL,
            region TEXT NOT NULL, bgc_alias TEXT NOT NULL, exact_locus TEXT NOT NULL,
            locus_tag TEXT NOT NULL, gene_order INTEGER, start_1based INTEGER, end_1based INTEGER,
            strand TEXT, aa_length INTEGER NOT NULL, protein_sha256 TEXT NOT NULL,
            sequence TEXT NOT NULL, product TEXT, sec_met_domains TEXT,
            gene_function_inference TEXT, edge_core_overlap TEXT, resistance_tier TEXT,
            source_package TEXT NOT NULL, source_fasta TEXT NOT NULL,
            source_fasta_sha256 TEXT NOT NULL, source_inventory TEXT NOT NULL,
            source_inventory_sha256 TEXT NOT NULL,
            UNIQUE(cohort,strain,full_node_or_contig,region,bgc_alias,locus_tag,protein_sha256)
          );
          CREATE TABLE quarantine (
            cohort TEXT NOT NULL, package TEXT NOT NULL, gene TEXT, state TEXT NOT NULL
          );
          CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE INDEX idx_protein_sha ON protein_occurrence(protein_sha256);
          CREATE INDEX idx_protein_cohort ON protein_occurrence(cohort,strain);
          CREATE INDEX idx_protein_length ON protein_occurrence(aa_length);
          CREATE INDEX idx_protein_locus ON protein_occurrence(cohort,strain,full_node_or_contig,region,bgc_alias);
        """)
        insert = "INSERT OR IGNORE INTO protein_occurrence (" + ",".join(_OCCURRENCE_COLUMNS) + ") VALUES (" + ",".join("?" for _ in _OCCURRENCE_COLUMNS) + ")"
        con.executemany(insert, [[row.get(column, "") for column in _OCCURRENCE_COLUMNS] for row in all_rows])
        con.executemany("INSERT INTO quarantine VALUES (?,?,?,?)", [
            [row.get("cohort", ""), row.get("package", ""), row.get("gene", ""), row.get("state", "")]
            for row in quarantine
        ])
        metadata = {
            "schema": SCHEMA, "created_utc": datetime.now(timezone.utc).isoformat(),
            "identity_contract": "protein SHA-256 primary; exact locus plus locus tag disambiguates occurrences",
            "claim_ceiling": CLAIM_CEILING,
        }
        con.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
        con.commit()
        stats = {
            "schema": SCHEMA, "status": "PASS_WITH_TYPED_QUARANTINE" if quarantine else "PASS",
            "packages_by_cohort": dict(sorted(packages_by_cohort.items())),
            "gbk_register_rows_by_cohort": dict(sorted(gbk_register_rows_by_cohort.items())),
            "candidate_occurrence_rows": len(all_rows),
            "unique_occurrences": con.execute("SELECT COUNT(*) FROM protein_occurrence").fetchone()[0],
            "typed_quarantine_rows": len(quarantine), "cohorts": {}, "claim_ceiling": CLAIM_CEILING,
        }
        for cohort in sorted(packages_by_cohort):
            stats["cohorts"][cohort] = {
                "distinct_strains": con.execute("SELECT COUNT(DISTINCT strain) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
                "distinct_exact_loci": con.execute("SELECT COUNT(DISTINCT exact_locus) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
                "protein_occurrences": con.execute("SELECT COUNT(*) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
                "distinct_protein_sequences": con.execute("SELECT COUNT(DISTINCT protein_sha256) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
            }
        con.close()
        os.replace(temp_path, out)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    receipt = out.with_suffix(".receipt.json")
    stats["database"] = {"path": str(out), "sha256": _sha256_file(out), "byte_count": out.stat().st_size}
    receipt.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats


def _role(row: dict[str, str]) -> str:
    text = " ".join(str(row.get(key, "")) for key in (
        "product_qualifier", "gene_function_inference", "sec_met_domains", "resistance_tier"
    )).lower()
    if row.get("edge_core_overlap", "").lower() == "core" or re.search(r"nrps|pks|ketosynth|adenylation|terpene|prenyl|phosphopantethein", text):
        return "CORE_OR_BIOSYNTHETIC_MACHINERY"
    if row.get("resistance_tier", "") and "null" not in row.get("resistance_tier", "").lower():
        return "RESISTANCE_ROUTING_CANDIDATE"
    if re.search(r"transporter|transport |abc|mfs|efflux|bioy|ecf", text):
        return "TRANSPORT_CANDIDATE"
    return "CONTEXT"


def _load_query(package: Path, alias: str, genes: list[str] | None) -> tuple[str, list[dict]]:
    inventory_rows = _read_rows(_one(package, "*_2_inventory.csv"))
    strain = _package_strain(package, inventory_rows)
    matches = [row for row in inventory_rows if row.get("BGC_ID") == alias]
    if len(matches) != 1:
        raise ValueError(f"{alias} does not resolve exactly once in {package}")
    inv = matches[0]
    display = _exact_display(strain, inv.get("Contig", ""), inv.get("antiSMASH_Region", ""), alias)
    context_rows = [row for row in _gene_context(package).values() if row.get("bgc_id") == alias]
    context = {row.get("locus_tag", ""): row for row in context_rows}
    sequence_by_gene = {}
    for gene, header, sequence in _parse_fasta(_one(package, "*_proteins.faa")):
        match = re.search(r"(?:^|\s)bgc=(BGC\d+)(?:\s|$)", header)
        if match and match.group(1) == alias:
            sequence_by_gene[gene] = sequence
    selected = genes or [gene for gene, row in context.items() if _role(row) != "CONTEXT"]
    query = []
    for gene in selected:
        sequence = sequence_by_gene.get(gene)
        if not sequence:
            continue
        row = context.get(gene, {})
        query.append({
            "query_exact_locus": display, "query_strain": strain, "query_gene": gene,
            "query_role": _role(row), "query_gene_order": row.get("rank", ""),
            "query_length_aa": len(sequence), "query_protein_sha256": _sha256_bytes(sequence.encode("ascii")),
            "sequence": sequence,
        })
    if not query:
        raise ValueError("no query proteins resolved for requested BGC/genes")
    return display, query


# v9.7.409 (DEEP_AUDIT2_resource_dos #1): PairwiseAligner.align() builds an O(len(query)*len(subject))
# DP matrix; a multi-MB crafted sequence makes that matrix so large the OS SIGKILLs the process
# uncatchably. Refuse any pair with an over-long sequence BEFORE .align(). Env-overridable.
_DEFAULT_MAX_ALIGN_AA = 10_000


def _max_align_aa() -> int:
    """Per-sequence residue ceiling for local alignment (env-overridable, read at call time)."""
    try:
        return int(os.environ.get("MAMEY_MAX_ALIGN_AA", str(_DEFAULT_MAX_ALIGN_AA)))
    except (TypeError, ValueError):
        return _DEFAULT_MAX_ALIGN_AA


def _aligner():
    try:
        from Bio.Align import PairwiseAligner, substitution_matrices
    except ImportError as exc:
        raise RuntimeError("cohort protein comparison requires the optional bio extra: pip install 'mamey[bio]'") from exc
    aligner = PairwiseAligner()
    aligner.mode = "local"
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.open_gap_score = -11
    aligner.extend_gap_score = -1
    return aligner


def _metrics(aligner, query: str, subject: str) -> dict:
    cap = _max_align_aa()
    if len(query) > cap or len(subject) > cap:
        # v9.7.409 (DEEP_AUDIT2_resource_dos #1): refuse an over-long pair before .align() — the DP
        # matrix is O(len(query)*len(subject)) and a multi-MB sequence SIGKILLs uncatchably. Return
        # a neutral, typed "skipped" metrics dict (comparison_state -> WEAK) instead of aligning.
        return {
            "identical_residues": 0, "blosum_positive_residues": 0,
            "alignment_columns_including_gaps": 0,
            "identity_pct": 0.0, "positives_pct": 0.0,
            "query_aligned_residues": 0, "query_coverage_pct": 0.0,
            "subject_aligned_residues": 0, "subject_coverage_pct": 0.0,
            "local_alignment_score_blosum62": 0.0,
            "alignment_skipped": (f"sequence exceeds MAX_ALIGN_AA={cap} "
                                  f"(query={len(query)}, subject={len(subject)})"),
        }
    alignment = aligner.align(query, subject)[0]
    q_aligned, s_aligned = str(alignment[0]), str(alignment[1])
    columns = len(q_aligned)
    identical = sum(a == b for a, b in zip(q_aligned, s_aligned) if a != "-" and b != "-")
    positive = sum(aligner.substitution_matrix[a, b] > 0 for a, b in zip(q_aligned, s_aligned) if a != "-" and b != "-")
    q_res = sum(char != "-" for char in q_aligned)
    s_res = sum(char != "-" for char in s_aligned)
    return {
        "identical_residues": identical, "blosum_positive_residues": positive,
        "alignment_columns_including_gaps": columns,
        "identity_pct": round(100 * identical / columns, 1),
        "positives_pct": round(100 * positive / columns, 1),
        "query_aligned_residues": q_res, "query_coverage_pct": round(100 * q_res / len(query), 1),
        "subject_aligned_residues": s_res, "subject_coverage_pct": round(100 * s_res / len(subject), 1),
        "local_alignment_score_blosum62": round(float(alignment.score), 1),
    }


def _comparison_state(metrics: dict) -> str:
    if metrics["identity_pct"] >= 60 and metrics["query_coverage_pct"] >= 80 and metrics["subject_coverage_pct"] >= 80:
        return "STRONG_WHOLE_PROTEIN_FAMILY_NAVIGATION"
    if metrics["identity_pct"] >= 40 and metrics["query_coverage_pct"] >= 70 and metrics["subject_coverage_pct"] >= 70:
        return "MODERATE_WHOLE_PROTEIN_FAMILY_NAVIGATION"
    return "WEAK_CLOSEST_AVAILABLE"


def _top_prefilter(con: sqlite3.Connection, cohort: str, query: str, limit: int, exclude_strain: str | None) -> list[dict]:
    low, high = int(len(query) * 0.55), int(len(query) * 1.80)
    sql = "SELECT * FROM protein_occurrence WHERE cohort=? AND aa_length BETWEEN ? AND ?"
    params: list = [cohort, low, high]
    if exclude_strain:
        sql += " AND strain<>?"
        params.append(exclude_strain)
    qkmers = {query[i:i + 4] for i in range(max(0, len(query) - 3))}
    heap: list[tuple[float, int, dict]] = []
    serial = 0
    for row in con.execute(sql, params):
        subject = row["sequence"]
        skmers = {subject[i:i + 4] for i in range(max(0, len(subject) - 3))}
        shared = len(qkmers & skmers) / max(1, len(qkmers))
        if not shared:
            continue
        serial += 1
        item = (shared, serial, dict(row))
        if len(heap) < limit:
            heapq.heappush(heap, item)
        elif shared > heap[0][0]:
            heapq.heapreplace(heap, item)
    return [dict(row, candidate_kmer_shared_fraction=round(shared, 4)) for shared, _, row in sorted(heap, reverse=True)]


def compare_catalog(database: Path, package: Path, alias: str, outdir: Path, *,
                    genes: list[str] | None = None, top_n: int = 3,
                    prefilter_n: int = 40, query_cohort: str | None = None) -> dict:
    """Compare selected focal proteins to every cohort and emit Mode-B-ready tables."""
    database, package, outdir = database.resolve(), package.resolve(), outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    display, query = _load_query(package, alias, genes)
    con = sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    cohorts = [row[0] for row in con.execute("SELECT DISTINCT cohort FROM protein_occurrence ORDER BY cohort")]
    denominator = {
        cohort: {
            "distinct_strains": con.execute("SELECT COUNT(DISTINCT strain) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
            "distinct_exact_loci": con.execute("SELECT COUNT(DISTINCT exact_locus) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
            "protein_occurrences": con.execute("SELECT COUNT(*) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
            "distinct_protein_sequences": con.execute("SELECT COUNT(DISTINCT protein_sha256) FROM protein_occurrence WHERE cohort=?", (cohort,)).fetchone()[0],
        } for cohort in cohorts
    }
    aligner = _aligner()
    matches: list[dict] = []
    for q in query:
        for cohort in cohorts:
            exclude = q["query_strain"] if cohort == query_cohort else None
            candidates = _top_prefilter(con, cohort, q["sequence"], prefilter_n, exclude)
            aligned = []
            for candidate in candidates:
                metrics = _metrics(aligner, q["sequence"], candidate["sequence"])
                aligned.append({
                    **{key: value for key, value in q.items() if key != "sequence"},
                    "comparator_cohort": cohort, "comparator_exact_locus": candidate["exact_locus"],
                    "comparator_gene": candidate["locus_tag"],
                    "comparator_gene_order": candidate["gene_order"],
                    "comparator_length_aa": candidate["aa_length"],
                    "comparator_protein_sha256": candidate["protein_sha256"],
                    "comparator_product": candidate["product"],
                    "comparator_source_package": candidate["source_package"],
                    "candidate_kmer_shared_fraction": candidate["candidate_kmer_shared_fraction"],
                    **metrics, "comparison_state": _comparison_state(metrics),
                    "claim_ceiling": CLAIM_CEILING,
                })
            aligned.sort(key=lambda row: (
                -row["local_alignment_score_blosum62"], -row["query_coverage_pct"],
                -row["identity_pct"], row["comparator_exact_locus"], row["comparator_gene"]
            ))
            seen_loci: set[str] = set()
            rank = 0
            for row in aligned:
                if row["comparator_exact_locus"] in seen_loci:
                    continue
                seen_loci.add(row["comparator_exact_locus"])
                rank += 1
                row["rank_within_query_and_cohort"] = rank
                matches.append(row)
                if rank >= top_n:
                    break
    con.close()
    exact_locus_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in matches:
        exact_locus_groups[(row["comparator_cohort"], row["comparator_exact_locus"])].append(row)
    neighborhoods = []
    for (cohort, locus), rows in exact_locus_groups.items():
        by_query = {}
        for row in rows:
            prior = by_query.get(row["query_gene"])
            if prior is None or row["rank_within_query_and_cohort"] < prior["rank_within_query_and_cohort"]:
                by_query[row["query_gene"]] = row
        selected = sorted(by_query.values(), key=lambda row: (int(row["query_gene_order"] or 10**9), row["query_gene"]))
        subject_orders = [int(row["comparator_gene_order"]) for row in selected if str(row["comparator_gene_order"]).isdigit()]
        if len(selected) < 2:
            order_state = "SINGLE_QUERY_GENE_ONLY"
        elif len(subject_orders) != len(selected):
            order_state = "MULTI_GENE_SAME_LOCUS_ORDER_UNMEASURED"
        elif subject_orders == sorted(subject_orders):
            order_state = "MULTI_GENE_SAME_LOCUS_ORDER_CONCORDANT"
        elif subject_orders == sorted(subject_orders, reverse=True):
            order_state = "MULTI_GENE_SAME_LOCUS_REVERSE_ORDER"
        else:
            order_state = "MULTI_GENE_SAME_LOCUS_ORDER_MIXED"
        neighborhoods.append({
            "query_exact_locus": display, "comparator_cohort": cohort,
            "comparator_exact_locus": locus, "matched_query_gene_count": len(selected),
            "query_genes": ", ".join(row["query_gene"] for row in selected),
            "comparator_genes": ", ".join(row["comparator_gene"] for row in selected),
            "count_first_sequence_evidence": "; ".join(
                f"{row['query_gene']}->{row['comparator_gene']} "
                f"{row['identical_residues']}/{row['alignment_columns_including_gaps']} identical "
                f"({row['identity_pct']:.1f}%), qcov {row['query_coverage_pct']:.1f}%"
                for row in selected
            ),
            "neighborhood_state": order_state,
            "allowed_inference": "component-level within-project navigation; not complete pathway identity",
        })
    neighborhoods.sort(key=lambda row: (-row["matched_query_gene_count"], row["comparator_cohort"], row["comparator_exact_locus"]))
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "__", display)
    matches_path = outdir / f"{stem}__COHORT_PROTEIN_MATCHES.tsv"
    neighborhood_path = outdir / f"{stem}__COHORT_NEIGHBORHOOD_SUMMARY.tsv"
    payload_path = outdir / f"{stem}__MODEB_SECTION45_PAYLOAD.md"
    receipt_path = outdir / f"{stem}__COHORT_PROTEIN_COMPARISON_RECEIPT.json"
    _write_tsv(matches_path, matches)
    _write_tsv(neighborhood_path, neighborhoods)
    lines = [
        f"# Mode B Section 45 payload — {display}", "",
        "## Measured denominator", "",
        "| Cohort | Distinct strains | Exact BGC loci | Protein occurrences | Distinct protein sequences |",
        "|---|---:|---:|---:|---:|",
    ]
    for cohort in cohorts:
        d = denominator[cohort]
        lines.append(f"| {cohort} | {d['distinct_strains']} | {d['distinct_exact_loci']} | {d['protein_occurrences']} | {d['distinct_protein_sequences']} |")
    lines += ["", "## Closest measured proteins", "",
              "The complete ranked, count-first table is in the sibling TSV. Weak closest-available rows are retained rather than rewritten as absence.", "",
              "| Query gene | Role | Cohort | Rank | Comparator exact locus | Comparator gene | Identity count | Identity | Positives | Query coverage | State |",
              "|---|---|---|---:|---|---|---:|---:|---:|---:|---|"]
    for row in matches:
        lines.append(
            f"| {row['query_gene']} | {row['query_role']} | {row['comparator_cohort']} | {row['rank_within_query_and_cohort']} | "
            f"{row['comparator_exact_locus']} | {row['comparator_gene']} | "
            f"{row['identical_residues']}/{row['alignment_columns_including_gaps']} | {row['identity_pct']:.1f}% | "
            f"{row['positives_pct']:.1f}% | {row['query_coverage_pct']:.1f}% | {row['comparison_state']} |"
        )
    lines += ["", "## Same-locus multi-gene aggregation", "",
              "| Cohort | Comparator exact locus | Query genes | Comparator genes | Sequence / synteny evidence | Agreement and mismatch | Allowed inference |",
              "|---|---|---|---|---|---|---|"]
    for row in neighborhoods:
        if row["matched_query_gene_count"] < 2:
            continue
        lines.append(
            f"| {row['comparator_cohort']} | {row['comparator_exact_locus']} | {row['query_genes']} | "
            f"{row['comparator_genes']} | {row['count_first_sequence_evidence']} | "
            f"{row['neighborhood_state']} | {row['allowed_inference']} |"
        )
    lines += ["", f"Claim ceiling: {CLAIM_CEILING}", ""]
    payload_path.write_text("\n".join(lines), encoding="utf-8")
    receipt = {
        "schema": "mamey.cohort-protein-comparison/1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS", "query_exact_locus": display, "query_gene_count": len(query),
        "query_genes": [row["query_gene"] for row in query], "cohort_denominator": denominator,
        "query_cohort": query_cohort, "target_strain_excluded_from_query_cohort": bool(query_cohort),
        "candidate_prefilter": f"top {prefilter_n} length-gated 4-mer candidates per query gene and cohort",
        "alignment": "local BLOSUM62; gap open -11; gap extend -1; identity/positives denominator includes gaps",
        "rank_rule": "local alignment score, then query coverage, identity, exact locus and gene",
        "claim_ceiling": CLAIM_CEILING, "artifacts": {},
    }
    for path in (matches_path, neighborhood_path, payload_path):
        receipt["artifacts"][str(path)] = {"sha256": _sha256_file(path), "byte_count": path.stat().st_size}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def _write_tsv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("state\nZERO_ROWS\n", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def command(args: argparse.Namespace) -> int:
    if args.cohort_protein_action == "build":
        if not args.cohort and not args.gbk_register:
            raise ValueError("build requires at least one --cohort LABEL=PATH or --gbk-register TSV")
        stats = build_catalog(
            args.cohort or [], Path(args.out), replace=args.replace,
            gbk_registers=[Path(path) for path in (args.gbk_register or [])],
        )
        emit(json.dumps(stats, indent=2))
        return 0
    genes = [part.strip() for part in (args.genes or "").split(",") if part.strip()] or None
    receipt = compare_catalog(
        Path(args.database), Path(args.package), args.bgc, Path(args.outdir), genes=genes,
        top_n=args.top_n, prefilter_n=args.prefilter_n, query_cohort=args.query_cohort,
    )
    emit(json.dumps(receipt, indent=2))
    return 0


def add_cli_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "cohort-proteins",
        help="Build/query an exact-locus within-project BGC-protein occurrence catalog",
    )
    actions = parser.add_subparsers(dest="cohort_protein_action", required=True)
    build = actions.add_parser("build", help="Build a protein occurrence SQLite catalog from Mamey package roots")
    build.add_argument("--cohort", action="append", type=_parse_cohort_root, metavar="LABEL=PATH",
                       help="Named cohort package root; repeat for AS, SID, TYPE, or other cohorts")
    build.add_argument("--gbk-register", action="append", default=None, metavar="TSV",
                       help="Governed exact-locus region-GBK register; repeat as needed. Required columns: cohort,strain,full_node_or_contig,region,bgc_alias,gbk_path")
    build.add_argument("--out", required=True, help="Output SQLite path")
    build.add_argument("--replace", action="store_true", help="Atomically replace an existing catalog")
    build.set_defaults(func=command)
    compare = actions.add_parser("compare", help="Rank focal BGC proteins against every catalog cohort")
    compare.add_argument("--database", required=True, help="Catalog SQLite from cohort-proteins build")
    compare.add_argument("--package", required=True, help="Focal sealed Mamey package directory")
    compare.add_argument("--bgc", required=True, help="Secondary BGC alias resolved inside the focal package")
    compare.add_argument("--genes", default=None, help="Comma-separated locus tags; default auto-selects core/resistance/transport genes")
    compare.add_argument("--query-cohort", default=None, help="Cohort label containing the focal strain; excludes that strain from within-cohort ranking")
    compare.add_argument("--top-n", type=int, default=3, help="Nonredundant exact comparator loci retained per query gene/cohort")
    compare.add_argument("--prefilter-n", type=int, default=40, help="Length/4-mer candidates aligned per query gene/cohort")
    compare.add_argument("--outdir", required=True, help="Additive output directory")
    compare.set_defaults(func=command)
    return parser


if __name__ == "__main__":
    top = argparse.ArgumentParser(description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    add_cli_parser(sub)
    raise SystemExit(command(top.parse_args()))
