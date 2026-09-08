#!/usr/bin/env python3
"""gene_modeb_enrichment.py -- gene-level assembly-line block for a Mode B card, floors enforced.

Produces the gene-level assembly-line section that slots into a strain's Mode B card (BGC cited by
node.region), built from the reliable per-gene parser + substrate/product-class tools + optional BLASTp.
It ENFORCES the project rules so the gene layer can live in the same deliverable as the rest of Mode B:

  * 15 kb confidence FLOOR: very likely (best member >=15kb AND complete core) / likely (>=15kb) /
    fragment (<15kb). Nothing below 15 kb is called likely.
  * Capacity language only: "capacity consistent with", never "produces" / "makes".
  * BLASTp pident is percent amino-acid identity; it is sequence-similarity evidence, not
    biological identity or a product assignment. KCB remains a separate cluster-level channel.
  * BGC cited by node.region. Module counts are PER GENE (region sums are unreliable).
  * NAPAA excluded from comparative claims; over-broad anchors (platensimycin) flagged low-confidence.
  * No em-dashes in the emitted card text.

CLI:
  python gene_modeb_enrichment.py REGION.gbk [--blastp-pct 75.3 --blastp-hit BGC0001462 --blastp-producer "A. coloradensis"]
Emits markdown for the card's gene-level section. Import make_section() to embed programmatically.
Depends on the sibling tools (imported).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, hashlib, json, os, re, importlib.util
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
GAL = _load("gene_assembly_line")
NS = _load("nrps_substrate")
PKS = _load("pks_product_class")

OVER_BROAD = {"platensimycin"}
FLOOR = 15000
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MIBIG_STATES = {
    "BELOW_ADMISSION_THRESHOLD",
    "PARTIAL_OR_LOW_BIDIRECTIONAL_COVERAGE_HIT",
    "EXACT_SEQUENCE_MATCH_TO_MIBIG_PROTEIN",
    "CLOSE_MIBIG_PROTEIN_HOMOLOG",
    "MIBIG_PROTEIN_HOMOLOG",
    "DISTANT_MIBIG_PROTEIN_CONTEXT",
    "NO_ADMITTED_MIBIG_PROTEIN_HIT",
}
_RESULT_COLUMNS = {
    "query_id", "query_sha256", "query_aa_length", "hit_rank", "evidence_state",
    "database_metadata", "database_receipt",
}


def _contig_len(loc):
    m = re.search(r"length_(\d+)", loc or "")
    return int(m.group(1)) if m else 0


def confidence_tier(loc, complete):
    L = _contig_len(loc)
    if L >= FLOOR and complete:
        return "very likely"
    if L >= FLOOR:
        return "likely"
    return "fragment"


def _sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _expected_sha(value, label):
    value = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{label} must be an explicit lowercase SHA-256")
    return value


def _canonical_identity(value):
    parts = [part.strip() for part in str(value or "").split(" / ")]
    if len(parts) != 4 or not all(parts):
        raise ValueError("complete_identity must be strain / full node-or-contig / region / BGC alias")
    if not re.fullmatch(r"region\d+", parts[2], re.I) or not re.fullmatch(r"BGC\d+", parts[3], re.I):
        raise ValueError("complete_identity has invalid region or BGC alias")
    return " / ".join(parts)


def _bound_locator(value, base, label):
    match = re.fullmatch(r"(.+);sha256=([0-9a-f]{64})", str(value or "").strip())
    if not match:
        raise ValueError(f"{label} must be path;sha256=<lowercase SHA-256>")
    path = Path(match.group(1)).expanduser()
    path = path.resolve() if path.is_absolute() else (Path(base) / path).resolve()
    if not path.is_file() or _sha256_file(path) != match.group(2):
        raise ValueError(f"{label} path is missing or hash-drifted")
    return path, match.group(2)


def _pick(row, *names):
    for name in names:
        if row.get(name) not in (None, ""):
            return str(row[name]).strip()
    return ""


def _protein_roster(path, expected_sha256, complete_identity):
    if not path:
        raise ValueError("mibig_protein_roster is required with mibig_protein_tsv")
    roster_path = Path(path).resolve()
    if not roster_path.is_file() or _sha256_file(roster_path) != _expected_sha(expected_sha256, "protein roster SHA"):
        raise ValueError("protein roster is missing or hash-drifted")
    with roster_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if not rows:
        raise ValueError("protein roster has no rows")
    roster = {}
    for line_number, row in enumerate(rows, 2):
        identity = _canonical_identity(_pick(row, "complete_identity", "display_identity"))
        if identity != complete_identity:
            raise ValueError(f"protein roster row {line_number} identity conflict")
        gene = _pick(row, "gene", "locus_tag")
        if not gene or gene in roster:
            raise ValueError(f"protein roster row {line_number} has empty or duplicate gene")
        try:
            length = int(_pick(row, "length_aa", "canonical_length_aa", "exact_roster_length_aa"))
        except ValueError as exc:
            raise ValueError(f"protein roster row {line_number} length is invalid") from exc
        roster[gene] = (length, _expected_sha(
            _pick(row, "translation_sha256", "canonical_translation_sha256"),
            f"protein roster row {line_number} translation SHA",
        ))
    return roster


def _mibig_context_rows(path, *, expected_tsv_sha256, roster_path,
                        expected_roster_sha256, complete_identity):
    result_path = Path(path).resolve()
    if not result_path.is_file() or _sha256_file(result_path) != _expected_sha(
        expected_tsv_sha256, "MIBiG result TSV SHA"
    ):
        raise ValueError("MIBiG result TSV is missing or hash-drifted")
    identity = _canonical_identity(complete_identity)
    roster = _protein_roster(roster_path, expected_roster_sha256, identity)
    with result_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = sorted(_RESULT_COLUMNS - set(reader.fieldnames or ()))
        if missing:
            raise ValueError("MIBiG result TSV lacks required columns: " + ", ".join(missing))
        rows = list(reader)
    if not rows:
        raise ValueError("MIBiG result TSV has no rows")
    metadata_locators = {row.get("database_metadata", "") for row in rows}
    receipt_locators = {row.get("database_receipt", "") for row in rows}
    if len(metadata_locators) != 1 or len(receipt_locators) != 1:
        raise ValueError("MIBiG result rows do not share one database metadata and receipt binding")
    metadata_path, metadata_sha = _bound_locator(metadata_locators.pop(), result_path.parent, "database metadata")
    receipt_path, _ = _bound_locator(receipt_locators.pop(), result_path.parent, "database receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "mibig_protein_context_db_v1" or not str(receipt.get("mibig_release", "")).strip():
        raise ValueError("database receipt schema or mibig_release is invalid")
    if receipt.get("metadata_sha256") != metadata_sha:
        raise ValueError("database receipt does not bind the result metadata")
    source_manifest = Path(str(receipt.get("source_manifest", ""))).expanduser()
    if not source_manifest.is_absolute():
        source_manifest = (receipt_path.parent / source_manifest).resolve()
    if not source_manifest.is_file() or receipt.get("source_manifest_sha256") != _sha256_file(source_manifest):
        raise ValueError("database receipt source manifest is missing or hash-drifted")
    groups = {}
    for line_number, row in enumerate(rows, 2):
        qid = row.get("query_id", "").strip()
        if qid not in roster:
            raise ValueError(f"MIBiG result row {line_number} query is absent from the exact protein roster")
        try:
            qlen = int(row.get("query_aa_length", "")); rank = int(row.get("hit_rank", ""))
        except ValueError as exc:
            raise ValueError(f"MIBiG result row {line_number} length/rank is invalid") from exc
        qsha = _expected_sha(row.get("query_sha256", ""), f"MIBiG result row {line_number} query SHA")
        if (qlen, qsha) != roster[qid]:
            raise ValueError(f"MIBiG result row {line_number} does not bind the roster protein")
        if row.get("evidence_state", "") not in _MIBIG_STATES:
            raise ValueError(f"MIBiG result row {line_number} has unsupported evidence_state")
        groups.setdefault(qid, []).append(rank)
    for qid, ranks in groups.items():
        if ranks == [0]:
            continue
        if sorted(ranks) != list(range(1, len(ranks) + 1)) or len(ranks) != len(set(ranks)):
            raise ValueError(f"MIBiG result ranks are not unique and contiguous for {qid}")
    best = {}
    for row in rows:
        qid = row.get("query_id", "")
        rank = int(row.get("hit_rank") or 0)
        if qid and (qid not in best or rank in (0, 1)):
            best[qid] = row
    return [best[qid] for qid in sorted(best)]


def _display(value):
    return " ".join(str(value or "").splitlines()).replace("|", r"\|")


def make_section(gbk_path, blastp_pct=None, blastp_hit=None, blastp_producer=None,
                 mibig_protein_tsv=None, mibig_protein_tsv_sha256=None,
                 mibig_protein_roster=None, mibig_protein_roster_sha256=None,
                 complete_identity=None):
    base = os.path.basename(gbk_path)
    node = re.search(r"(NODE_\d+_length_\d+)", base) or re.search(r"([\w.]+)\.region", base)
    reg = re.search(r"(region\d+)", base)
    loc = f"{node.group(1)}.{reg.group(1)}" if (node and reg) else base
    if complete_identity:
        loc = _canonical_identity(complete_identity)
    rows = GAL.catalog_region(gbk_path)
    L = []
    L.append("### Gene-level assembly line")
    if not rows:
        L.append(f"No NRPS/PKS assembly-line genes resolved in {loc}.")
        return "\n".join(L)
    best = max(rows, key=lambda r: r["modules"])
    tier = confidence_tier(loc, best["complete"])
    kinds = sorted(set(r["kind"] for r in rows))
    L.append(f"Locus {loc}. {len(rows)} assembly-line gene(s) ({', '.join(kinds)}); largest single gene "
             f"{best['modules']} module(s) ({best['kind']}, {'complete' if best['complete'] else 'partial'} core). "
             f"Module counts are per gene, not region sums.")
    L.append(f"Confidence (15 kb floor): {tier} "
             f"(best contig {round(_contig_len(loc)/1000)} kb; very likely needs >=15 kb and a complete core).")
    # predicted chemistry
    subs, sig, conf = NS.region_signature(gbk_path)
    if any(r["kind"] == "NRPS" for r in rows) and subs:
        nonp = [s for s in subs if s not in NS.PROTEINOGENIC and s != "X"]
        L.append(f"Predicted backbone (A-domain substrate calls, capacity-level): {' '.join(subs)}.")
        if nonp:
            L.append(f"Nonproteinogenic residues: {', '.join(nonp)}.")
        for cls, note in conf.items():
            L.append(f"Signature: capacity consistent with a {cls} ({note}).")
    for r in rows:
        if r["kind"] == "PKS":
            for gene, order in PKS.gene_domain_order(gbk_path, r["gene"]).items():
                if "PKS_KS" in order:
                    L.append(f"PKS {gene}: capacity consistent with a {PKS.classify(PKS.module_states(order))}.")
            break
    if mibig_protein_tsv:
        L.append("MIBiG protein-homology context (sequence-bound advisory stream):")
        for row in _mibig_context_rows(
            mibig_protein_tsv,
            expected_tsv_sha256=mibig_protein_tsv_sha256,
            roster_path=mibig_protein_roster,
            expected_roster_sha256=mibig_protein_roster_sha256,
            complete_identity=complete_identity,
        ):
            qid = _display(row.get("query_id", "unresolved-query"))
            state = _display(row.get("evidence_state", "UNRESOLVED"))
            if state == "NO_ADMITTED_MIBIG_PROTEIN_HIT":
                L.append(f"- {qid}: {state}; no admitted hit in this database/run, not biological absence or proof of novelty.")
                continue
            L.append(
                f"- {qid}: {_display(row.get('mibig_accession') or 'unresolved reference')}; "
                f"{_display(row.get('pct_identity') or 'NA')}% amino-acid identity; "
                f"query coverage {_display(row.get('query_coverage_pct') or 'NA')}%; "
                f"subject coverage {_display(row.get('subject_coverage_pct') or 'NA')}%; "
                f"E={_display(row.get('evalue') or 'NA')}; {state}. "
                f"{_display(row.get('bounded_interpretation', ''))}"
            )
        L.append("This gene-level MIBiG stream must be reconciled with KCB/cluster-level evidence and the multi-gene biosynthetic logic chain.")
    elif blastp_pct is not None:
        prod = f" (nearest characterized producer {blastp_producer})" if blastp_producer else ""
        hit = f" [{blastp_hit}]" if blastp_hit else ""
        L.append(f"Manual unbound summary (not sufficient for a finished card): core protein reported at "
                 f"{blastp_pct}% amino-acid identity to a MIBiG relative{hit}{prod}. Query coverage, "
                 f"subject coverage, exact sequence hashes, and database-build provenance are missing; "
                 f"rerun with --mibig-protein-tsv before evidence admission. This is similarity, not identity "
                 f"or a product assignment.")
    L.append("Capacity-level: architecture and substrate predictions indicate biosynthetic potential, "
             "not compound production or bioactivity. NAPAA is excluded from comparative claims; "
             "platensimycin and other over-broad anchors are low-confidence.")
    text = "\n".join(L)
    # v9.7.374 fix: this cleanup only ever stripped ASCII stand-ins (" - ", "--") -- it never
    # touched a REAL Unicode em-dash (U+2014), so a caller-supplied string that legitimately
    # contains one (e.g. --blastp-producer sourced from a literature title or an LLM-assembled
    # value, per this module's own "Import make_section() to embed programmatically" usage) sails
    # straight through into the emitted card text, directly violating this file's own documented
    # rule ("No em-dashes in the emitted card text") and this exact line's own comment. Reproduced
    # live: blastp_producer="Streptomyces sp. \u2014 soil isolate" left a literal em-dash in the
    # output; tests/test_gene_level_v9_7_294.py's existing "no em-dash" assertion never caught it
    # because its fixture never passed an em-dash-bearing value.
    text = text.replace("\u2014", "-").replace(" - ", " ").replace("--", " ")
    return text  # no em-dashes in stamps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gbk")
    ap.add_argument("--blastp-pct", type=float)
    ap.add_argument("--blastp-hit")
    ap.add_argument("--blastp-producer")
    ap.add_argument("--mibig-protein-tsv", help="sequence-bound TSV from bigscape_blastp_novelty.py query")
    ap.add_argument("--mibig-protein-tsv-sha256")
    ap.add_argument("--mibig-protein-roster")
    ap.add_argument("--mibig-protein-roster-sha256")
    ap.add_argument("--complete-identity", help="strain / full node-or-contig / region / BGC alias")
    a = ap.parse_args()
    emit(make_section(a.gbk, a.blastp_pct, a.blastp_hit, a.blastp_producer,
                       a.mibig_protein_tsv, a.mibig_protein_tsv_sha256,
                       a.mibig_protein_roster, a.mibig_protein_roster_sha256,
                       a.complete_identity))


if __name__ == "__main__":
    main()
