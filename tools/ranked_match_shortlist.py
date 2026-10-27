#!/usr/bin/env python3
"""Present saved top-three/five ranks within exact locus/run/evidence channel.

No scoring, search, cross-channel comparison, reference adoption or figure drawing.
The current source adapter is the retained KnownClusterBlast audit table.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

IDENTITY = re.compile(r"^AS-\d+ / \S+ / region\d{3} / BGC\d+$")
HASH = re.compile(r"^[a-f0-9]{64}$")
FIELDS = {"identity", "run", "selected", "rank", "mibig", "name", "distinct_query_genes", "distinct_reference_genes", "median_identity", "cumulative_blast_score"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(root, spec):
    p = (root / spec["path"]).resolve()
    b = p.read_bytes()
    if not HASH.fullmatch(str(spec.get("sha256", ""))) or sha(b) != spec["sha256"]:
        raise ValueError("SOURCE_HASH_MISMATCH: " + str(p))
    return b, {"path": str(p), "bytes": len(b), "sha256": sha(b)}


def table(data, required):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t")
    columns = reader.fieldnames or []
    if len(set(columns)) != len(columns) or not required.issubset(columns):
        raise ValueError("SOURCE_COLUMNS_MISSING_OR_DUPLICATE")
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("MALFORMED_SOURCE_ROW")
    return rows


def number(value, field, integer=False):
    if value in (None, "", "NA", "N/A", "null"):
        return None
    x = float(value)
    if not math.isfinite(x) or x < 0 or (integer and not x.is_integer()) or (field == "median_identity" and x > 100):
        raise ValueError("INVALID_NUMERIC_FIELD: " + field)
    if field == "rank" and x == 0:
        raise ValueError("INVALID_SAVED_RANK")
    return int(x) if integer else x


def normalize(rows, channel):
    result = []
    for line, row in enumerate(rows, 2):
        if row.get("evidence_channel") and row["evidence_channel"] != channel:
            raise ValueError("SOURCE_CHANNEL_MISMATCH")
        raw_selected = row["selected"].lower()
        if raw_selected not in {"true", "false", ""}:
            raise ValueError("INVALID_SELECTION_FIELD")
        result.append({"identity": row["identity"], "run": row["run"], "evidence_channel": channel,
                       "source_row": line, "saved_rank": number(row["rank"], "rank", True),
                       "reference_id": row["mibig"] or None, "reference_annotation": row["name"] or None,
                       "originally_selected": None if raw_selected == "" else raw_selected == "true",
                       "distinct_AS_genes_matched": number(row["distinct_query_genes"], "distinct_query_genes", True),
                       "distinct_reference_subjects_matched": number(row["distinct_reference_genes"], "distinct_reference_genes", True),
                       "median_identity_pct": number(row["median_identity"], "median_identity"),
                       "cumulative_BLAST_score_saved": number(row["cumulative_blast_score"], "cumulative_blast_score"),
                       "query_gene_denominator": None, "reference_gene_denominator": None, "alignment_coverage_rule": None,
                       "availability": "DENOMINATORS_AND_COVERAGE_RULE_NOT_IN_THIS_RANKING_TABLE"})
    return result


def indexed_metadata(rows):
    result = {}
    for row in rows:
        key = (row["identity"], row["run"])
        if key in result:
            raise ValueError("DUPLICATE_RUN_METADATA")
        result[key] = row
    return result


def shortlist(rows, top):
    ranked = sorted((r for r in rows if r["saved_rank"] is not None), key=lambda r: (r["saved_rank"], r["source_row"]))
    if not ranked:
        return {"requested": top, "cutoff_saved_rank": None, "rows": [], "state": "SAVED_RANK_UNAVAILABLE"}
    cutoff = ranked[min(top, len(ranked)) - 1]["saved_rank"]
    shown = [r for r in ranked if r["saved_rank"] <= cutoff]
    return {"requested": top, "cutoff_saved_rank": cutoff, "rows": shown,
            "state": "SAVED_ORDER_WITH_BOUNDARY_TIES" if len(shown) > top else "SAVED_ORDER"}


def project(rows, run_metadata, policies):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["identity"], row["run"], row["evidence_channel"])].append(row)
    output = []
    for (identity, run, channel), records in sorted(groups.items()):
        holds = []
        if not IDENTITY.fullmatch(identity):
            holds.append("COMPLETE_LOCUS_IDENTITY_HOLD")
        if not run:
            holds.append("RUN_CONTEXT_UNAVAILABLE")
        if any(not re.fullmatch(r"BGC\d+", str(r["reference_id"] or "")) for r in records):
            holds.append("REFERENCE_IDENTITY_HOLD")
        counts = Counter(r["reference_id"] for r in records)
        duplicates = [ref for ref, count in counts.items() if count > 1]
        if duplicates:
            holds.append("DUPLICATE_REFERENCE_ROWS_WITHIN_CONTEXT")
        ranks = Counter(r["saved_rank"] for r in records if r["saved_rank"] is not None)
        gene_counts = Counter(r["distinct_AS_genes_matched"] for r in records if r["distinct_AS_genes_matched"] is not None)
        for row in records:
            row["same_saved_rank_count"] = ranks.get(row["saved_rank"], 0) if row["saved_rank"] is not None else None
            row["same_AS_gene_count_candidate_count"] = gene_counts.get(row["distinct_AS_genes_matched"], 0) if row["distinct_AS_genes_matched"] is not None else None
        selected = [r for r in records if r["originally_selected"] is True]
        meta, policy = run_metadata.get((identity, run)), policies.get((identity, run))
        if meta is None:
            holds.append("RUN_METADATA_UNAVAILABLE")
        else:
            expected = meta.get("selected_reference")
            listed_selected = [r["reference_id"] for r in selected]
            if expected and listed_selected != [expected]:
                if expected not in counts and not listed_selected:
                    holds.append("ORIGINAL_SELECTION_NOT_IN_SAVED_RANKING")
                else:
                    holds.append("ORIGINAL_SELECTION_SOURCE_MISMATCH")
        if policy and meta and policy.get("selected_reference") != meta.get("selected_reference"):
            holds.append("SELECTION_POLICY_SOURCE_MISMATCH")
        if any(r["originally_selected"] is None for r in records):
            holds.append("SELECTION_FLAGS_PARTLY_UNAVAILABLE")
        block = any(h in holds for h in ("COMPLETE_LOCUS_IDENTITY_HOLD", "RUN_CONTEXT_UNAVAILABLE", "REFERENCE_IDENTITY_HOLD", "DUPLICATE_REFERENCE_ROWS_WITHIN_CONTEXT", "ORIGINAL_SELECTION_SOURCE_MISMATCH", "SELECTION_POLICY_SOURCE_MISMATCH"))
        output.append({"identity": identity, "run": run, "evidence_channel": channel,
                       "state": "REVIEW_HOLD" if holds else "SAVED_RANK_PREVIEW_NOT_ADOPTED", "holds": holds,
                       "candidate_rows_in_source_context": len(records), "duplicate_reference_ids": duplicates,
                       "top3": {"requested": 3, "cutoff_saved_rank": None, "rows": [], "state": "BLOCKED_BY_SOURCE_HOLD"} if block else shortlist(records, 3),
                       "top5": {"requested": 5, "cutoff_saved_rank": None, "rows": [], "state": "BLOCKED_BY_SOURCE_HOLD"} if block else shortlist(records, 5),
                       "retained_original_selection": selected,
                       "original_selection_from_run_metadata": (meta.get("selected_reference") or None) if meta else None,
                       "original_selection_metadata": None if not meta else {k: meta.get(k) or None for k in ("reference_review_state", "selected_name", "kcb_state", "kcb_member", "kcb_member_sha256")},
                       "selection_policy_snapshot": None if not policy else {k: policy.get(k) or None for k in ("selection_policy_state", "expected_reference_by_package_policy", "maximum_saved_query_genes", "tied_max_gene_candidates", "equal_gene_higher_identity_references", "flank_screen")},
                       "unranked_rows": [r for r in records if r["saved_rank"] is None], "all_source_rows": records})
    return output


def build(config, root):
    if config.get("schema") != "sapote.ranked_match_shortlist.v1":
        raise ValueError("UNSUPPORTED_CONFIG_SCHEMA")
    if config.get("evidence_channel") != "SAVED_KNOWNCLUSTERBLAST":
        raise ValueError("CURRENT_ADAPTER_SUPPORTS_SAVED_KNOWNCLUSTERBLAST_ONLY")
    data, source = pinned(root, config["rankings"])
    owner_data, owner = pinned(root, config["owner"])
    excerpt = config["owner"].get("excerpt")
    if not excerpt or excerpt not in owner_data.decode("utf-8"):
        raise ValueError("OWNER_SCOPE_EXCERPT_UNBOUND")
    run_data, run_source = pinned(root, config["run_metadata"])
    run_meta = indexed_metadata(table(run_data, {"identity", "run", "selected_reference"}))
    policies, sources = {}, [source, owner, run_source]
    if config.get("selection_policy"):
        b, source_policy = pinned(root, config["selection_policy"])
        policies = indexed_metadata(table(b, {"identity", "run", "selected_reference", "selection_policy_state"}))
        sources.append(source_policy)
    rows = normalize(table(data, FIELDS), config["evidence_channel"])
    all_contexts = len({(r["identity"], r["run"], r["evidence_channel"]) for r in rows})
    if config.get("contexts"):
        contexts = [(r["identity"], r["run"]) for r in config["contexts"]]
        if len(set(contexts)) != len(contexts):
            raise ValueError("DUPLICATE_REQUESTED_CONTEXT")
        present = {(r["identity"], r["run"]) for r in rows}
        if set(contexts) - present:
            raise ValueError("REQUESTED_CONTEXT_NOT_IN_RANKING_SOURCE")
        chosen = set(contexts)
        selected_rows = [r for r in rows if (r["identity"], r["run"]) in chosen]
    else:
        selected_rows = rows
    groups = project(selected_rows, run_meta, policies)
    return {"schema": "sapote.ranked_match_shortlist.result.v1", "state": "SOURCE_BOUND_SAVED_RANK_PREVIEW_NOT_ADOPTED", "sources": sources,
            "source_candidate_rows": len(rows), "source_exact_contexts": all_contexts, "displayed_contexts": len(groups), "groups": groups,
            "method": "Saved KCB rank order only; first3/5 ranked rows plus any tie at the boundary. No new ranking score or reference adoption.",
            "count_scope": "Distinct AS queries use the original audit's best-bitscore-per-query rule; distinct reference subjects are not a one-to-one orthology claim.",
            "limits": ["Saved KnownClusterBlast is a retained search channel, not a new or exhaustive MIBiG search.", "Native DIAMOND multi-reference comparisons use a different one-to-one genes/bitscore policy and are not merged here.", "Equal AS gene counts are annotated separately from saved-rank ties; neither creates a new optimality claim.", "Original selections and intentional paired run contexts remain visible, even outside top3/5.", "Gene denominators and coverage rules are null because they are not in this source table; rescue totals are not substituted.", "Snapshot input hashes and retained KCB member hashes do not constitute a fresh full-source sequence replay.", "Similarity does not establish compound identity, production, physical linkage or novelty."],
            "new_search": "NOT_PERFORMED", "browser_visual_review": "NOT_PERFORMED", "scientific_adoption": "NOT_GRANTED"}


def render(result):
    esc = lambda value: html.escape(str(value), quote=True)
    value = lambda x: "unavailable" if x is None or x == "" else esc(x)

    def rows_table(rows):
        body = ""
        for r in rows:
            body += "<tr>" + "".join("<td>" + value(r.get(k)) + "</td>" for k in ("saved_rank", "reference_id", "reference_annotation", "distinct_AS_genes_matched", "distinct_reference_subjects_matched", "median_identity_pct", "cumulative_BLAST_score_saved", "originally_selected", "same_saved_rank_count", "same_AS_gene_count_candidate_count")) + "</tr>"
        return '<div class="scroll"><table><tr><th>Saved KCB rank</th><th>Reference</th><th>Reference annotation</th><th>Distinct AS queries</th><th>Distinct reference subjects</th><th>Median identity %</th><th>Saved cumulative BLAST score</th><th>Originally selected</th><th>Same saved rank</th><th>Same AS gene count</th></tr>' + body + '</table></div>'

    groups = []
    for g in result["groups"]:
        s = '<section><h2>' + esc(g["identity"]) + '</h2><p>Run: <code>' + esc(g["run"]) + '</code><br>Channel: ' + esc(g["evidence_channel"]) + '<br>State: ' + esc(g["state"]) + '</p>'
        if g["holds"]:
            s += '<p>Holds: ' + esc("; ".join(g["holds"])) + '</p>'
        s += '<p>Source context contains ' + str(g["candidate_rows_in_source_context"]) + ' saved candidate rows. Denominators and alignment-coverage rule: unavailable in this source; no fractions inferred.</p>'
        for key in ("top3", "top5"):
            s += '<h3>' + esc(key) + ' · ' + esc(g[key]["state"]) + '</h3>' + rows_table(g[key]["rows"])
        s += '<h3>Original selection retained</h3><p>Run metadata reference: ' + value(g["original_selection_from_run_metadata"]) + '</p>' + rows_table(g["retained_original_selection"])
        s += '<p>Selection-policy snapshot: <code>' + esc(json.dumps(g["selection_policy_snapshot"], ensure_ascii=False)) + '</code></p>'
        s += '<p>Original ranking binding: <code>' + esc(json.dumps(g["original_selection_metadata"], ensure_ascii=False)) + '</code></p>'
        if g["unranked_rows"]:
            s += '<h3>Saved rank unavailable — retained for review</h3>' + rows_table(g["unranked_rows"])
        if g["duplicate_reference_ids"]:
            s += '<h3>Duplicate source rows — shortlist held</h3>' + rows_table(g["all_source_rows"])
        groups.append(s + '</section>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Saved top3 and top5 reference matches</title><style>body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1400px;padding:0 1rem;line-height:1.5}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #777;padding:.4rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}.scroll{overflow-x:auto}section{border-top:2px solid #777;margin-top:2rem;padding-top:1rem}code{overflow-wrap:anywhere}h2{font-size:1.2rem}</style><body><h1>Saved top3 and top5 reference matches</h1><p>' + esc(result["state"]) + '</p><p>' + esc(result["method"]) + '</p><p>Names describe reference annotations, not AS compound identities. Cumulative BLAST score is not a percentage. Shared gene counts are not saved-rank ties.</p>' + ''.join(groups) + '<h2>Scope and holds</h2><ul>' + ''.join('<li>' + esc(s) + '</li>' for s in result["limits"]) + '</ul><p>No new search, figure rendering, browser visual inspection or scientific adoption.</p></body></html>\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--json-out", type=Path, required=True)
    p.add_argument("--html-out", type=Path)
    p.add_argument("--replace-candidate", action="store_true")
    a = p.parse_args(argv)
    raw = a.config.read_bytes()
    config = json.loads(raw)
    root = a.config.resolve().parent
    inputs = {a.config.resolve()} | {(root / config[k]["path"]).resolve() for k in ("rankings", "owner", "run_metadata", "selection_policy") if config.get(k)}
    outputs = [a.json_out] + ([a.html_out] if a.html_out else [])
    if len({q.resolve() for q in outputs}) != len(outputs) or any(q.is_symlink() or q.resolve() in inputs for q in outputs):
        p.error("outputs must be distinct derived files, never source inputs or symlinks")
    result = build(config, root)
    result["config_file_sha256"] = sha(raw)
    texts = [json.dumps(result, indent=2, ensure_ascii=False) + "\n"] + ([render(result)] if a.html_out else [])
    for q, text in zip(outputs, texts):
        if q.exists() and q.read_text() != text and not a.replace_candidate:
            p.error("changed derived output exists; preserve it or explicitly use --replace-candidate")
    for q, text in zip(outputs, texts):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=q.parent, delete=False) as f:
            f.write(text)
            tmp = Path(f.name)
        os.replace(tmp, q)
    print(json.dumps({"state": result["state"], "contexts": len(result["groups"]), "contexts_with_holds": sum(bool(g["holds"]) for g in result["groups"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
