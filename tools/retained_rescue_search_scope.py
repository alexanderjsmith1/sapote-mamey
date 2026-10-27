#!/usr/bin/env python3
"""Account for one retained gap-rescue run; export only positively bound pairs.

This adapter performs no search, no scoring, no negative-outcome inference and no
source writes. Historical reference->genome search direction stays explicit.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # run as tools/<name>.py from the bundle root
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

STATUS = {"PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS", "MISSING_NOT_FOUND"}
AA = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""): h.update(block)
    return h.hexdigest()


def pin(value): return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)): raise ValueError("TABLE_HEADER_HOLD")
        rows = list(reader)
    if any(None in r or None in r.values() for r in rows): raise ValueError("MALFORMED_TABLE_HOLD")
    return rows


def read_fasta(path):
    seqs, key, pieces = {}, None, []
    def save():
        if key is None: return
        if key in seqs: raise ValueError("DUPLICATE_FASTA_IDENTIFIER")
        aa = "".join("".join(pieces).split()).upper().rstrip("*")
        if not aa or set(aa) - AA: raise ValueError("INVALID_SAVED_PROTEIN_STRING")
        seqs[key] = {"length": len(aa), "sha256": hashlib.sha256(aa.encode()).hexdigest()}
    for line in Path(path).read_text().splitlines():
        if line.startswith(">"):
            save(); key = line[1:].split()[0]; pieces = []
        elif line.strip():
            if key is None: raise ValueError("FASTA_SEQUENCE_BEFORE_IDENTIFIER")
            pieces.append(line)
    save()
    if not seqs: raise ValueError("EMPTY_SAVED_FASTA")
    return seqs


def account(receipt, rows, inventory, saved_subjects, current_reference):
    identity = receipt.get("core", "")
    if not re.fullmatch(r"[^/\n]+ / [^/\n]+ / region[0-9]{3,} / BGC[0-9]+", identity):
        raise ValueError("FOCAL_IDENTITY_HOLD")
    if not rows or len(rows) != receipt.get("reference_genes"):
        raise ValueError("REFERENCE_OUTCOME_DENOMINATOR_HOLD")
    refs = [r.get("reference_gene", "") for r in rows]
    if any(not r for r in refs) or len(refs) != len(set(refs)):
        raise ValueError("REFERENCE_ROW_ID_HOLD")
    if any(r.get("status") not in STATUS for r in rows): raise ValueError("UNKNOWN_SOURCE_STATUS")
    counts = collections.Counter(r["status"] for r in rows)
    if any(receipt.get(s.lower()) != counts[s] for s in STATUS):
        raise ValueError("RECEIPT_STATUS_COUNTS_HOLD")
    inv = {}
    for gene in inventory:
        if gene.get("identity") != identity or not gene.get("locus_tag") or not pin(gene.get("protein_sha256")):
            raise ValueError("FOCAL_INVENTORY_BINDING_HOLD")
        if gene["locus_tag"] in inv: raise ValueError("AMBIGUOUS_FOCAL_GENE")
        inv[gene["locus_tag"]] = gene
    if not inv: raise ValueError("EMPTY_FOCAL_INVENTORY")
    ref_by_id = {x["reference_gene_id"]: x for x in current_reference}
    if len(ref_by_id) != len(current_reference): raise ValueError("DUPLICATE_CURRENT_REFERENCE_ROW")
    if any(x.get("reference_id") != Path(receipt["reference"]).stem for x in current_reference):
        raise ValueError("CURRENT_REFERENCE_IDENTIFIER_HOLD")
    observed, export, holds = [], [], []
    for row in rows:
        ref_id = row["reference_gene"]
        current = ref_by_id.get(ref_id)
        current_roster = bool(current and current.get("reference_name") == row.get("name")
                              and str(current.get("reference_length_aa")) == row.get("reference_len_aa"))
        item = {"reference_gene_id": ref_id, "source_status": row["status"], "best_protein": row.get("best_protein", ""),
                "best_locus": row.get("best_locus", ""), "best_region_identity": row.get("best_region_identity", ""),
                "current_reference_roster_consistency": "NAME_LENGTH_CONSISTENT_NOT_HISTORICAL_SEQUENCE_PROOF" if current_roster else "CURRENT_REFERENCE_ROSTER_HOLD",
                "export_state": "NOT_EXPORTED", "reason": ""}
        if row["status"] == "MISSING_NOT_FOUND":
            item["reason"] = "Saved reference-level status retained; never inverted into an AS-gene searched-no-hit assertion."
        elif row["status"] != "PRESENT_IN_CORE":
            item["reason"] = "External or ambiguous candidate retained; not adopted as a focal gene match."
        else:
            subject = saved_subjects.get(row.get("best_protein", ""))
            gene = inv.get(row.get("best_locus", ""))
            try:
                metrics = [float(row.get(k, "")) for k in ("best_identity_pct", "best_coverage_pct")]
                metrics_ok = all(math.isfinite(x) and 0 <= x <= 100 for x in metrics)
                length_ok = bool(subject and subject["length"] == int(row.get("best_len_aa", "")))
            except (ValueError, TypeError): metrics_ok = length_ok = False
            if row.get("best_region_identity") != identity:
                item["reason"] = "SOURCE_FOCAL_LOCATION_HOLD"
            elif not current_roster:
                item["reason"] = "CURRENT_REFERENCE_ROSTER_HOLD"
            elif not subject or not gene or not length_ok or not metrics_ok:
                item["reason"] = "SUBJECT_OR_METRIC_BINDING_HOLD"
            elif subject["sha256"] != gene["protein_sha256"].lower():
                item["reason"] = "CURRENT_GENE_SEQUENCE_DIFFERS_FROM_SAVED_SUBJECT"
            else:
                item["export_state"] = "POSITIVE_RETAINED_PAIR_CURRENT_AS_SEQUENCE_BOUND"
                item["AS_protein_sha256"] = subject["sha256"]
                export.append({"identity": identity, "locus_tag": row["best_locus"], "protein_sha256": subject["sha256"],
                               "state": "MATCHED", "scope": "FOCAL_REGION", "reference_id": Path(receipt["reference"]).stem,
                               "reference_gene_id": ref_id, "reason": "Retained source PRESENT_IN_CORE pair; current AS full-protein hash equals saved genome-subject string. Historical reference sequence, raw HSP and execution provenance remain held; not a new search or product claim."})
        if item["reason"].endswith("HOLD") or item["reason"].startswith("CURRENT_GENE_SEQUENCE_DIFFERS"):
            holds.append({"reference_gene_id": ref_id, "reason": item["reason"]})
        observed.append(item)
    return observed, export, {"focal_identity": identity, "focal_inventory_entries": len(inv),
            "retained_reference_outcome_rows": len(rows), "source_status_counts": counts,
            "saved_genome_subject_sequences": len(saved_subjects), "exported_positive_pair_rows": len(export),
            "distinct_AS_genes_with_exported_pairs": len({x["locus_tag"] for x in export}),
            "AS_genes_not_evaluated_from_selected_outcomes": len(inv) - len({x["locus_tag"] for x in export}),
            "searched_no_hit_AS_genes_exported": 0, "pair_binding_holds": holds}


def build(config):
    paths, bindings = {}, []
    for role, source in config["sources"].items():
        path = Path(source["path"])
        actual = sha(path)
        if not pin(source.get("sha256")) or actual != source["sha256"].lower():
            raise ValueError("SOURCE_PIN_HOLD: " + role)
        paths[role] = path
        bindings.append({"role": role, "path": str(path.resolve()), "sha256": actual, "bytes": path.stat().st_size})
    receipt = json.loads(paths["receipt"].read_text())
    inventory = read_tsv(paths["focal_inventory"])
    prep = json.loads(paths["preparation_receipt"].read_text())
    if (prep.get("identity") != receipt.get("core") or prep.get("full_current_CDS_count") != len(inventory)
            or prep.get("focal_inventory_sha256") != sha(paths["focal_inventory"])):
        raise ValueError("INVENTORY_PREPARATION_RECEIPT_HOLD")
    observed, export, summary = account(receipt, read_tsv(paths["outcomes"]), inventory,
                                         read_fasta(paths["saved_subject_fasta"]), read_tsv(paths["current_reference_inventory"]))
    split_rows = read_tsv(paths["split_outcomes"])
    if len(split_rows) != len(receipt.get("split_genes", [])):
        raise ValueError("SPLIT_OUTCOME_COUNTS_HOLD")
    summary["retained_split_candidate_rows"] = len(split_rows)
    for row in export:
        row["evidence_path"] = str(paths["outcomes"].resolve())
        row["evidence_sha256"] = sha(paths["outcomes"])
    log_text = paths["run_log"].read_text() if "run_log" in paths else ""
    terminal_summary = "[gap_directed_rescue] " + receipt["core"]
    completion_observed = terminal_summary in log_text
    scope = {"schema": "retained-gap-rescue-search-scope-v1", "status": "POSITIVE_ACCOUNTING_WITH_SEARCH_SCOPE_HOLDS",
             "summary": summary, "reference_id": Path(receipt["reference"]).stem,
             "actual_search_direction": {"query_role": "reference proteins", "subject_role": "whole-genome proteins"},
             "requested_scope": {"reference_outcome_roster": "SAVED_TABLE_AND_RECEIPT_COUNT_AGREE", "reference_gene_rows": len(observed),
                                 "AS_subject_roster": "SAVED_GENOME_FASTA_ROSTER_PRESENT; WHOLE_GENOME_COMPLETENESS_NOT_INDEPENDENTLY_REPLAYED; NOT_A_FOCAL_QUERY_LIST", "declared_homology": receipt.get("homology", "NOT_RECORDED")},
             "execution_proof": {"retained_terminal_summary": completion_observed,
                                 "state": ("PRODUCER_COMPLETION_SUMMARY_AND_OUTPUTS" if completion_observed else "RETAINED_OUTPUTS_ONLY; COMPLETION_SUMMARY_NOT_VERIFIED") + "; NO_RETAINED_BACKEND_EXIT_OR_RAW_HSP_ATTESTATION",
                                 "forward_alignment_receipt_present": bool(receipt.get("forward_alignment")),
                                 "historical_executable_version": "NOT_RECORDED_IN_SELECTED_RUN_RECEIPT",
                                 "effective_argv_and_backend_defaults": "NOT_RECORDED_IN_SELECTED_RUN_RECEIPT"},
             "sequence_and_database_scope": {"AS_pair_sequences": "SAVED_SUBJECT_STRING_HASH_EQUALS_CURRENT_CANONICAL_TRANSLATION_FOR_EXPORTED_ROWS",
                                             "historical_reference_query_sequences": "NOT_RETAINED; CURRENT_GBK_NAME_LENGTH_ROSTER_CONSISTENCY_ONLY",
                                             "historical_temporary_subject_database": "NOT_RETAINED; SAVED_SUBJECT_FASTA_HASH_BOUND",
                                             "historical_domain_entries": "NOT_USED_OR_REBOUND"},
             "selection_scope": {"retained_outcomes": "ONE_SELECTED_BEST_GENOME_PROTEIN_PER_REFERENCE_GENE",
                                 "raw_HSP_roster": "NOT_PRESENT_IN_SELECTED_RUN_FOLDER",
                                 "all_AS_gene_outcomes": "NOT_DERIVABLE_FROM_REFERENCE_CENTRIC_SELECTED_ROWS",
                                 "negative_export_policy": "NEVER_EXPORT_SEARCHED_NO_HIT_FROM_THIS_ADAPTER"},
             "source_bindings": bindings, "observed_pairs": observed, "retained_split_candidates": split_rows,
             "limits": "Legacy observation accounting, not execution revalidation or new alignment. Current code/GBK hashes do not retroactively prove historical code/reference revisions. No contig linkage, function, product or production inference."}
    refs = [{"reference_id": scope["reference_id"], "reference_gene_id": x["reference_gene_id"]} for x in observed]
    for binding in bindings:
        if sha(binding["path"]) != binding["sha256"]: raise ValueError("SOURCE_CHANGED_DURING_READ")
    return scope, export, refs


def safe(value):
    s = str(value)
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) else s


def write_tsv(path, rows, fields):
    with Path(path).open("w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader()
        for row in rows: w.writerow({k: safe(row.get(k, "")) for k in fields})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True); p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.exists(): p.error("fresh output directory required; original receipts preserved")
    scope, pairs, refs = build(json.loads(Path(a.config).read_text()))
    scope["config_sha256"] = sha(a.config)
    out.mkdir(parents=True)
    (out / "SEARCH_SCOPE_MANIFEST.json").write_text(json.dumps(scope, indent=2) + "\n")
    write_tsv(out / "TB02_POSITIVE_EVIDENCE.tsv", pairs, ["identity", "locus_tag", "protein_sha256", "state", "scope", "reference_id", "reference_gene_id", "evidence_path", "evidence_sha256", "reason"])
    write_tsv(out / "TB02_REFERENCE_INVENTORY.tsv", refs, ["reference_id", "reference_gene_id"])
    print(json.dumps(scope["summary"]))


if __name__ == "__main__": main()
