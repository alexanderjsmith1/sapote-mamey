"""
b1_normalizer.py — normalize any divergent B1 source to the canonical frozen v1.1 schema.

The single source of truth for column names/order is the live builder's
CANONICAL_V1_HEADERS['B1_BGC_Master'] (45 cols). This tool maps divergent inputs
(build_master.py 15-col output, manifest-ingest, sandbox handoffs) onto it, leaving
HONEST BLANKS for absent columns and emitting a blank-by-source ledger.

Fail-safe: unrecognized columns are reported, never silently dropped without a ledger entry.
"""
import re

# Alias map: divergent column name -> canonical name. Case-insensitive match.
# Captures the real divergences seen in build_master.py output and manifest keys.
ALIASES = {
    "contig": "contig", "region": "region", "region_number": "region",
    "products": "products", "edge_status": "boundary", "boundary": "boundary",
    "length_kb": "length_kb",
    "kcb_top_hit": "kcb_top", "kcb_top": "kcb_top",
    "kcb_cumulative": "kcb_score", "kcb_score": "kcb_score",
    "kcb_proteins": "kcb_proteins", "kcb_protein_hits": "kcb_proteins",
    "closest_kcb_product": "closest_candidate_kcb_product_ALIAS",  # extra->note (not a frozen col)
    "closest_mibig": "closest_mibig_accession_ALIAS",
    "kcb_provenance": "closest_product_provenance",
    "closest_product_provenance": "closest_product_provenance",
    "source_kcb_file": "source_kcb_file", "source_kcb_locator": "source_kcb_locator",
    "riq": "novelty_auto", "riq_label": "novelty_auto", "novelty_auto": "novelty_auto",
    "arch": "arch", "architecture_confidence": "arch",
    "kcb_hit_rank": "kcb_hit_rank", "denominator_type": "denominator_type",
    "parse_confidence": "parse_confidence", "needs_manual_kcb_check": "needs_manual_kcb_check",
    "product_claim_ceiling": "product_claim_ceiling", "claim_ceiling": "claim_ceiling",
    "diagnostic_signal_score": "diagnostic_signal_score",
    "strain": "strain", "bgc_id": "BGC_ID", "taxonomy": "_A2_taxonomy",  # taxonomy belongs in A2
}

# Value-format normalizers
def _norm_products(v):
    if not v: return ""
    return ";".join(p.strip() for p in re.split(r"[;/]", str(v)) if p.strip())

def _norm_boundary(v):
    if not v: return ""
    s = str(v).strip().lower()
    return {"interior": "Interior", "edge": "Edge", "full-contig": "Full-contig",
            "full_contig": "Full-contig", "fc": "Full-contig"}.get(s, str(v).strip().capitalize())

def _norm_region(v):
    if v in (None, ""): return ""
    s = str(v).strip()
    if re.fullmatch(r"\d+", s):           # integer -> regionNNN
        return f"region{int(s):03d}"
    return s

VALUE_NORMALIZERS = {"products": _norm_products, "boundary": _norm_boundary, "region": _norm_region}

def normalize_row(src_row, canonical_headers):
    """Map one source row dict to a canonical row dict. Returns (row, notes).

    Resolution order for each source column:
      1. exact canonical-header match (identity passthrough) — a column already named
         canonically maps to itself, so canonical input survives unchanged;
      2. explicit ALIASES entry (divergent name -> canonical / extra / A2-route);
      3. otherwise -> unmapped (surfaced in ledger, never silently dropped).
    """
    out = {h: "" for h in canonical_headers}
    notes = {}
    canon_lower = {h.lower(): h for h in canonical_headers}
    for k, v in src_row.items():
        key = str(k).strip().lower()
        if key in canon_lower:            # (1) identity passthrough for canonical names
            canon = canon_lower[key]
        else:                             # (2) explicit alias
            canon = ALIASES.get(key)
        if canon is None:
            notes.setdefault("unmapped", []).append(k); continue
        if canon.endswith("_ALIAS"):
            notes.setdefault("extra_columns", []).append(k); continue
        if canon.startswith("_A2_"):
            notes.setdefault("route_to_A2", []).append(k); continue
        if canon in canonical_headers:
            nv = VALUE_NORMALIZERS.get(canon, lambda x: x)(v)
            out[canon] = nv
    # frozen-schema rule: if a product is present but needs_manual_kcb_check blank -> default 'yes'
    if out.get("kcb_top") and not str(out.get("needs_manual_kcb_check") or "").strip():
        out["needs_manual_kcb_check"] = "yes"
    return out, notes

def normalize_table(rows, canonical_headers):
    """Normalize a list of source rows. Returns (canonical_rows, ledger)."""
    canon_rows, all_notes = [], {"unmapped": set(), "extra_columns": set(), "route_to_A2": set()}
    for r in rows:
        cr, notes = normalize_row(r, canonical_headers)
        canon_rows.append(cr)
        for k in all_notes:
            all_notes[k].update(notes.get(k, []))
    # blank-by-source ledger
    blanks = {}
    for h in canonical_headers:
        n_blank = sum(1 for r in canon_rows if not str(r.get(h) or "").strip())
        if n_blank: blanks[h] = round(100*n_blank/max(1,len(canon_rows)), 1)
    ledger = {k: sorted(v) for k, v in all_notes.items()}
    ledger["blank_pct_by_column"] = blanks
    return canon_rows, ledger
