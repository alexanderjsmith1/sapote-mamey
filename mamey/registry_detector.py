"""
registry_detector.py — B2 Phase 1: registry-backed detector loader.

Purpose
-------
Make deterministic detection CONSUME the canonical marker registry
(bundle_support/registry_inventory_v1.9.4.json) instead of relying on hardcoded regex
dicts scattered in source_scans.py.

B2 phasing (see docs/B2_REGISTRY_WIRING_SPEC.md)
-------------------------------------------
* Phase 1 (THIS MODULE): regex/motif markers only. The registry-derived
  pattern dicts MUST reproduce the hardcoded source_scans.py dicts
  bit-for-bit. This is the regression anchor — zero behavior change.
* Phase 2 (NOT here, runs where HMMER/DIAMOND/BLASTP + profile DBs exist):
  enable detector ∈ {pfam, tigrfam, hmm, diamond, blastp} targets. Those
  EXPAND detection and must be diffed family-by-family against ground truth.

Backend dispatch
----------------
Each registry entry's `targets` list carries per-target `type`:
    regex   -> active in Phase 1 (annotation-text regex)
    motif   -> active in Phase 1 (DNA TFBS motif)
    pfam / tigrfam / hmm -> defined but INACTIVE until Phase 2
    manual  -> human review route; never auto-fires
    diamond / blastp     -> reserved for Phase 2

ACTIVE_DETECTORS is the single switch governing what fires. In Phase 1 it is
frozen to {"regex", "motif"}. Do NOT widen it without proving parity first.

Mapping discipline
-------------------
The inventory groups entries by `library`, one library per legacy *_PATTERNS
dict. Within a library, entries appear in the SAME ORDER as the legacy dict's
keys, so we pair positionally and re-key with the legacy key names. This keeps
the produced dicts identical (same keys, same ordered pattern lists) to what
source_scans.py defined by hand, which is what the parity test asserts.
"""
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from typing import Any

from .ziputil import regular_file_names

# --- Phase 1 frozen detector set. Widen ONLY after Phase-2 parity work. ------
ACTIVE_DETECTORS: frozenset[str] = frozenset({"regex", "motif"})

# Inactive-but-defined target types (catalog/Phase-2). Surfaced for worklists.
PHASE2_DETECTORS: frozenset[str] = frozenset(
    {"pfam", "tigrfam", "hmm", "diamond", "blastp"}
)
MANUAL_DETECTORS: frozenset[str] = frozenset({"manual"})

# Library -> legacy source_scans.py dict name. Order of this list is
# documentation only; per-library positional pairing is what matters.
LIBRARY_TO_LEGACY_DICT: dict[str, str] = {
    "mamey_domain_class": "DOMAIN_CLASS_PATTERNS",
    "mamey_chitin_glycan": "CHITINASE_PATTERNS",
    "mamey_regulator": "REGULATOR_PATTERNS",
    "mamey_transporter": "TRANSPORTER_PATTERNS",
    "mamey_resistance": "RESISTANCE_PATTERNS",
    "mamey_cctt": "CCTT_PATTERNS",
    "mamey_flbr": "FLBR_PATTERNS",
    "mamey_cassette": "CASSETTE_PATTERNS",
    "mamey_umed": "UMED_PATTERNS",
    "mamey_tfbs": "TFBS_MOTIFS",
}

# The legacy keys, in the exact order they appear in source_scans.py. These are
# the canonical key names the rest of the pipeline expects in scan output.
# Keeping them here lets the loader re-key registry entries deterministically
# without parsing source_scans.py at runtime.
LEGACY_KEYS: dict[str, list[str]] = {
    "DOMAIN_CLASS_PATTERNS": [
        "NRPS_A", "NRPS_C", "NRPS_T_PCP", "NRPS_E", "TE_release",
        "PKS_KS", "PKS_AT", "PKS_DH", "PKS_ER", "PKS_KR", "PKS_ACP",
        "RiPP_precursor", "YcaO_TOMM", "Halogenase", "Glycosyltransferase",
        "Methyltransferase", "Oxidoreductase", "Aminotransferase",
        "Transporter", "Regulator",
    ],
    "CHITINASE_PATTERNS": ["GH18", "GH19", "AA10_LPMO", "CBM_CHITIN", "GlcNAc"],
    "REGULATOR_PATTERNS": [
        "DasR_GntR", "LuxR", "TetR", "LysR", "SARP", "MarR", "LacI", "AraC",
        "TwoComponent", "Fur_Zur", "IolR", "PhoP", "OsdR", "GBL",
    ],
    "TRANSPORTER_PATTERNS": ["ABC", "MFS", "RND", "MATE", "Efflux", "Export"],
    "RESISTANCE_PATTERNS": [
        "Beta_lactamase_fold", "Erm_methylase", "VanHAX_like", "APH_AAC",
        "Fosfomycin", "Self_resistance_general",
    ],
    "CCTT_PATTERNS": [
        "T43-HAL_halogenase", "T43-XHAL_fluorinase_chlorinase",
        "T43-PHO_phosphonate", "T43-NUC_nucleoside", "T43-BLA_betalactam", "T43-AMC_aminocyclitol",
        "T43-ENE_enediyne", "T43-LAN_lanthipeptide", "T43-LASSO_lassopeptide",
        "T43-THA_thioamide", "T43-DKP_cdps", "T43-IDC_indolocarbazole",
        "T43-PTM_hsaf_tetramate", "T43-TET_tetronate_spirotetronate",
        "T43-NN_n_n_bond",
        "T43-PYE_polyene_macrolide", "T43-GPA_glycopeptide", "T43-BLT_betalactone",
    ],
    "FLBR_PATTERNS": ["mod_KS", "hyb_KS", "tra_KS", "mega_NRPS"],
    "CASSETTE_PATTERNS": [
        "release_macrocyclization", "glycosylation", "halogenation",
        "phosphonate", "nucleoside", "aminoglycoside_aminocyclitol",
        "tetronate_spirotetronate", "thioamide_ycao", "lanthipeptide",
        "lassopeptide", "tomm_azole_ripp", "polyene_ptm_hsaf",
        "siderophore_metallophore", "transporter_resistance",
        "chitin_glycan_ecology",
    ],
    "UMED_PATTERNS": [
        "LanP_S8_protease", "LanT_C39_transporter_peptidase",
        "FlaP_AplP_S9_protease", "M16B_metalloprotease", "YcaO_TfuA_thioamide",
        "RiPP_RRE", "nucleoside_maturation",
    ],
    "TFBS_MOTIFS": [
        "DasR_like_palindrome", "DmdR_iron_box_like", "LexA_SOS_like",
        "BldD_like", "FuR_like", "Zur_like", "IolR_like", "PhoP_box_like",
        "ANR_FNR_like", "GBL_AdpA_like", "SARP_BTAD_like", "PAS_LuxR_like",
    ],
}


def default_registry_path() -> str:
    """Locate bundle_support/registry_inventory_v1.9.4.json at the bundle root."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    return os.path.join(root, "bundle_support/registry_inventory_v1.9.4.json")


def load_registry(path: str | None = None) -> list[dict[str, Any]]:
    path = path or default_registry_path()
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("registry inventory must be a JSON array of entries")
    return data


def _entries_by_library(registry: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for e in registry:
        out.setdefault(e.get("library", ""), []).append(e)
    return out


def _active_patterns_for_entry(entry: dict, want_type: str) -> list[str]:
    """Reconstruct the ordered pattern list for one entry, active types only.

    For regex targets the inventory packs alternations with '|'; we split them
    back into the individual pattern strings the legacy dict held, preserving
    order. Motif targets are taken verbatim.
    """
    pats: list[str] = []
    for t in entry.get("targets", []):
        ttype = t.get("type")
        if ttype != want_type or ttype not in ACTIVE_DETECTORS:
            continue
        value = t.get("value", "")
        if ttype == "regex":
            # Registry convention: '|' is ALWAYS an inter-entry delimiter, not an intra-pattern
            # alternation. Patterns that use '|' as alternation (e.g., "kinase|phosphatase") are
            # stored as single unsplit target values. This split unpacks compactly packed entries.
            pats.extend(value.split("|"))
        else:  # motif
            pats.append(value)
    return pats


def build_pattern_dicts(
    registry: list[dict] | None = None, path: str | None = None
) -> dict[str, dict[str, list[str]]]:
    """Build the Phase-1 pattern dicts from the registry.

    Returns a mapping legacy_dict_name -> {legacy_key: [patterns]} that should
    be byte-identical to the hardcoded dicts in source_scans.py. Raises if the
    registry's per-library entry count does not match the legacy key count
    (a guard against silent drift in the inventory).
    """
    reg = registry if registry is not None else load_registry(path)
    by_lib = _entries_by_library(reg)
    out: dict[str, dict[str, list[str]]] = {}

    for library, dict_name in LIBRARY_TO_LEGACY_DICT.items():
        keys = LEGACY_KEYS[dict_name]
        want_type = "motif" if dict_name.endswith("MOTIFS") else "regex"
        # Only entries carrying an active target of the wanted type participate
        # in Phase 1; HMM-only entries (e.g. T43-TOMM) are intentionally skipped.
        entries = [
            e
            for e in by_lib.get(library, [])
            if any(t.get("type") == want_type for t in e.get("targets", []))
        ]
        if len(entries) != len(keys):
            raise ValueError(
                f"registry/{library}: {len(entries)} active "
                f"{want_type} entries but legacy {dict_name} has {len(keys)} "
                f"keys; positional mapping unsafe (registry drift?)"
            )
        built: dict[str, list[str]] = {}
        for key, entry in zip(keys, entries):
            built[key] = _active_patterns_for_entry(entry, want_type)
        out[dict_name] = built
    return out


def inactive_marker_worklist(
    registry: list[dict] | None = None, path: str | None = None
) -> list[dict[str, Any]]:
    """List registry entries whose only targets are Phase-2/manual backends.

    These are defined-but-not-firing under Phase 1 — the worklist for the
    HMMER/DIAMOND/BLASTP wiring that must run where those tools and profile
    databases are available.
    """
    reg = registry if registry is not None else load_registry(path)
    work: list[dict[str, Any]] = []
    for e in reg:
        types = {t.get("type") for t in e.get("targets", [])}
        if types and not (types & ACTIVE_DETECTORS):
            work.append(
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "library": e.get("library"),
                    "target_types": sorted(types),
                    "evidence_tier": e.get("evidence_tier"),
                }
            )
    return work


def run_hmm_scan(zip_path: str, bgcs: list, strain_id: str) -> dict[str, Any]:
    """Run the existing ordered-domain HMM walker for each bound region GBK.

    This is the run-path adapter, not a second scanner. Optional dependency or
    database failures return one named degradation receipt and never masquerade
    as a biological negative.
    """
    from .hmm_blastp_adjudicate import resolve_hmm_db, walk_domains

    resolved = resolve_hmm_db()
    hmm_path = resolved.get("path") if isinstance(resolved, dict) else resolved
    if not hmm_path:
        reason = "HMM_SCAN_UNAVAILABLE: no resolved scanner HMM database"
        from . import degradation
        degradation.record("registry_detector.run_hmm_scan.unavailable", RuntimeError(reason))
        return {"schema_version": "mamey_hmm_scan_v1", "status": "HMM_SCAN_UNAVAILABLE",
                "reason": reason, "rows": []}

    rows = []
    with zipfile.ZipFile(zip_path) as archive:
        names = regular_file_names(archive)
        for bgc in bgcs:
            source = str(getattr(bgc, "source_gbk", "") or "")
            matches = [name for name in names if name == source or name.endswith("/" + source)]
            if len(matches) != 1:
                rows.append({
                    "strain": strain_id, "node_or_contig": getattr(bgc, "node_id", "") or bgc.contig,
                    "region": getattr(bgc, "antismash_region", ""), "bgc_alias": bgc.bgc_id,
                    "status": "SOURCE_GBK_UNBOUND", "gene_count": 0, "domain_hit_count": 0,
                })
                continue
            tmp_name = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".gbk", delete=False) as tmp:
                    tmp.write(archive.read(matches[0]))
                    tmp_name = tmp.name
                hits, genes, reason = walk_domains(tmp_name, hmm_file=hmm_path)
                rows.append({
                    "strain": strain_id, "node_or_contig": getattr(bgc, "node_id", "") or bgc.contig,
                    "region": getattr(bgc, "antismash_region", ""), "bgc_alias": bgc.bgc_id,
                    "status": "PASS" if not reason else "HMM_SCAN_UNAVAILABLE",
                    "reason": reason, "gene_count": len(genes),
                    "domain_hit_count": sum(len(values) for values in hits.values()),
                    "hits_by_gene": hits,
                })
            finally:
                if tmp_name:
                    try:
                        os.unlink(tmp_name)
                    except OSError:
                        pass
    status = "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "PASS_WITH_DEGRADATION"
    return {"schema_version": "mamey_hmm_scan_v1", "status": status,
            "hmm_database": os.path.basename(str(hmm_path)), "rows": rows}
