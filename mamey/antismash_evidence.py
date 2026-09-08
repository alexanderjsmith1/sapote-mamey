from __future__ import annotations
import json, re, zipfile, os, statistics, sys
from mamey.fragment_ceiling import apply_to_bgc as _apply_fragment_ceiling
from decimal import Decimal
from pathlib import Path
from typing import Any
from .ziputil import regular_file_names


def _riq_median(scores):
    """Median RiQ across regions carrying a RiQ score.

    Uses statistics.median so an even-length score list averages its two central
    values. The previous form (scores[len(scores) // 2] on a sorted list) returned
    the UPPER of the two central values, biasing even-length genome RiQ medians high.
    v9.7.331 RED-02 correctness fix; scores is already sorted at the call site.
    """
    return statistics.median(scores)

# F5: stream the (large) antiSMASH records document instead of json.loads-ing it whole.
# Benchmarked ~300x lower peak memory on a 115 MB genome (617 MB -> 2 MB) at ~4.7x wall time.
#
# DECISION IS SIZE-ADAPTIVE (E2): real actinomycete antiSMASH JSONs are 55-130 MB and the legacy
# full-load peaks near 1 GB — each record-level extractor json.loads-es the whole doc independently —
# which is the dominant cause of the large-genome stalls. Above the size floor we stream (flat
# memory); below it we full-load (json.loads is faster than event streaming, esp. under the
# pure-Python/cffi ijson backends). Streaming output is byte-identical to full-load (use_float=True;
# verified on WWKJ00000000, 114 BGCs, full-package parity under fixed PYTHONHASHSEED), so the floor
# only trades wall time, never results. No hidden env gate: the default streams large JSONs on its
# own. MAMEY_STREAM_JSON overrides the size decision — 1/on/always = always stream,
# 0/off/never = always full-load (legacy); absent ijson, both paths fall back to json.loads.
# ── CUT A (v9.7.223): KCB coverage + class-mismatch gate for the product-claim ceiling ──
# The ONE coverage rule, reconciled with function_and_novelty (blastp_online.py) and _claim_ceiling
# (chatgpt_commands.py). A product-level ceiling requires a SUBSTANTIAL protein-hit count (>=5, the
# function_and_novelty floor) AND no hard biosynthetic-class disagreement between the KCB comparator
# and the antiSMASH product class. BGC065 (AS-XXX): 3-gene lankacidin shell (kp=3 < 5) with a
# NRPS/PKS comparator over a RiPP/cofactor core — fails both, so it caps at source-derived.
_KCB_PKSNRPS_RE = re.compile(r"\b(pks|nrps|t1pks|t2pks|t3pks|hr-t2pks|transat|type[\s_-]?i{1,3}\+?)\b", re.I)
_KCB_RIPP_RE    = re.compile(r"\b(ripp|lanthipeptide|lanthi|lasso|thiopeptide|sactipeptide|ranthipeptide|bottromycin|azole|redox[\s_-]?cofactor|cofactor|nucleoside)\b", re.I)

def kcb_class_mismatch(comparator_type: str, product_classes: str) -> bool:
    """True when the KCB comparator biosynthetic type disagrees HARD with the antiSMASH product
    class (PKS/NRPS anchor over a RiPP/cofactor core, or the reverse). Similarity, not identity."""
    ct = comparator_type or ""; pc = product_classes or ""
    comp_pn = bool(_KCB_PKSNRPS_RE.search(ct)); comp_rp = bool(_KCB_RIPP_RE.search(ct))
    prod_pn = bool(_KCB_PKSNRPS_RE.search(pc)); prod_rp = bool(_KCB_RIPP_RE.search(pc))
    if comp_pn and not comp_rp and prod_rp and not prod_pn:
        return True
    if comp_rp and not comp_pn and prod_pn and not prod_rp:
        return True
    return False

def kcb_coverage_substantial(kcb_protein_hits) -> bool:
    """function_and_novelty's substantial floor: a product-level anchor needs >=5 shared genes.
    A 3-gene KCB shell is a class/source signal, not a product-identity signal."""
    try:
        return int(kcb_protein_hits or 0) >= 5
    except (TypeError, ValueError):
        return False

_STREAM_JSON_MODE = os.environ.get("MAMEY_STREAM_JSON", "auto").strip().lower()
# 20 MB cleanly separates real genome JSONs (55-130 MB -> stream) from fixtures/small genomes
# (KB-low-MB -> full-load). Tunable; not a result-affecting parameter (parity holds either side).
_STREAM_JSON_MIN_BYTES = 20 * 1024 * 1024
# Optional streaming JSON parser, bound under two names for two code paths:
#   _ijson — _iter_records (record streaming, default-on when ijson present)
#   ijson  — bounded JSON mode (_stream_kcb_riq, KCB/RiQ leaf streaming)
# If ijson is absent, both paths degrade gracefully (streaming -> json.loads;
# bounded -> 'off' with a recorded note). Both call sites guard on _HAVE_IJSON.
try:
    import ijson  # system install (fastest if the yajl C backend is present)
    _ijson = ijson
    _HAVE_IJSON = True
except Exception:
    # Vendored pure-Python fallback. ijson uses absolute self-imports (from ijson.x import y),
    # so we put _vendor on sys.path and import it as top-level `ijson` rather than as a submodule.
    import os as _os, sys as _sys
    _vd = _os.path.join(_os.path.dirname(__file__), "_vendor")
    if _os.path.isdir(_os.path.join(_vd, "ijson")) and _vd not in _sys.path:
        _sys.path.append(_vd)
    try:
        import ijson
        _ijson = ijson
        _HAVE_IJSON = True
    except Exception:
        ijson = None
        _ijson = None
        _HAVE_IJSON = False


def _should_stream(zf: "zipfile.ZipFile", name: str) -> bool:
    """Per-file streaming decision. Size-adaptive by default; MAMEY_STREAM_JSON forces either way.

    Both _iter_records and the extractor eager-list guards call this so they always agree on a
    given file. Absent ijson, always False (full-load fallback).
    """
    if not _HAVE_IJSON:
        return False
    if _STREAM_JSON_MODE in ("0", "off", "false", "no", "never"):
        return False
    if _STREAM_JSON_MODE in ("1", "on", "true", "yes", "always"):
        return True
    # auto (default): stream only files at/above the size floor.
    try:
        return zf.getinfo(name).file_size >= _STREAM_JSON_MIN_BYTES
    except Exception:
        return False


def _iter_records(zf: "zipfile.ZipFile", name: str):
    """Yield antiSMASH record dicts. Streams large JSONs via ijson; full-loads small ones (see
    _should_stream). Both paths yield identical record dicts (use_float=True keeps numbers float)."""
    if _should_stream(zf, name):
        with zf.open(name) as stream:               # binary, lazy — raw text never fully materialised
            # use_float=True: ijson yields JSON numbers as Decimal by default, which are not
            # json.dumps-serializable and crash _write_package. float matches the json.loads
            # fallback path below byte-for-byte (verified parity on WWKJ, 114 BGCs).
            yield from _ijson.items(stream, "records.item", use_float=True)
    else:
        yield from json.loads(_read_text(zf, name)).get("records", [])

# (ijson import is consolidated near the top of this module — see the dual-name
# binding that provides both `_ijson` and `ijson` plus `_HAVE_IJSON`.)

# JSON evidence modes (the `run` CLI default is "bounded" — see cli.py add_argument):
#   "off"     — do not open JSON at all. TXT clusterblast files carry KCB data,
#               but TIGRFAM diagnostics (JSON-only) are unavailable. Fastest;
#               safe for any genome size. Forced in capped / ChatGPT-safe runs.
#   "bounded" — DEFAULT. Stream the JSON with ijson, extracting only
#               knownclusterblast / region_to_region / RiQ / TIGRFAM keys, with a
#               hard cap on records and bytes. Never materialises the whole
#               document. Falls back to 'off' if ijson is unavailable, or mid-run
#               if the stream exceeds the wall-clock budget (cli.py logs a WARN).
#   "full"    — legacy: json.loads the whole file and flatten twice. Refuses
#               files >20 MB (would hang). Only for small JSON.

JSON_MODE_DEFAULT = "bounded"   # v9.3.2: bounded when ijson present; falls back to off gracefully
BOUNDED_MAX_RECORDS = 5000
# Flat-memory streaming (system/vendored ijson) can afford a far larger leaf budget; the old
# 5000 cap was sized against the retired 25 MB byte cap and truncated RiQ on large genomes.
BOUNDED_MAX_RECORDS_STREAMING = 200_000
BOUNDED_MAX_JSON_BYTES = 25_000_000
# When a streaming parser (system or vendored ijson) is present, bounded mode reads at flat
# memory, so a much larger file is safe. Real actinomycete antiSMASH JSONs run 55–90 MB.
BOUNDED_MAX_JSON_BYTES_STREAMING = 250_000_000
FULL_MAX_JSON_BYTES = 20_000_000

# ── Diagnostic Pfam/domain names extracted from antiSMASH sec_met_domain qualifiers ──
# antiSMASH runs its own HMMER internally; these results live in the GBK files.
# We surface them without re-running HMMER.
DIAGNOSTIC_SEC_MET_DOMAINS = {
    # TIER_1_DIAGNOSTIC — resolve sub-grades and annotation gaps
    "YcaO":           ("PF02624", "azoline-forming cyclodehydratase — LAP/thiopeptide"),
    "PF02624":        ("PF02624", "azoline-forming cyclodehydratase — LAP/thiopeptide"),
    "TOMM_dh":        ("PF04825", "TOMM dehydrogenase — thiopeptide/LAP maturation"),
    "Condensation":   ("PF00668", "NRPS condensation domain"),
    "AMP-binding":    ("PF00501", "NRPS adenylation domain — A-domain"),
    "PF00501":        ("PF00501", "NRPS adenylation domain — A-domain"),
    "PKS_KS":         ("PF00109", "PKS ketosynthase"),
    "PKS_AT":         ("PF00698", "PKS acyltransferase — cis-AT"),
    "Acyl_transf_1":  ("PF00698", "PKS acyltransferase"),
    "Trans_AT_docking": ("PF14765", "Trans-AT docking domain — modular PKS coupler"),
    "PKS_Docking_Cterm": ("PF14765","PKS C-terminal docking — assembly-line coupler"),
    "PKS_Docking_Nterm": ("PF02801","PKS N-terminal docking — assembly-line coupler"),
    "Thioesterase":   ("PF00975", "PKS/NRPS thioesterase — release/cyclisation"),
    # Spirotetronate
    "FkbH":           ("PF04113", "FkbH phosphodiesterase — spirotetronate starter unit (TET-A)"),
    "PF04113":        ("PF04113", "FkbH phosphodiesterase — spirotetronate starter unit"),
    "Diels_aldr":     ("PF13570", "Diels-Alderase — spirotetronate ring closure (TET-A confirmation)"),
    "PF13570":        ("PF13570", "Diels-Alderase — spirotetronate ring closure"),
    # Tetronate (non-spiro) ring closure — FabH-family KSIII. FkbH is necessary-not-sufficient
    # for a tetronate; the ring needs this closure enzyme co-located with the FkbH+ACP pair.
    # (v9.7.183 — the AS-XXX BGC010 completeness gate.)
    "fabH":           ("PF08541", "FabH-family KSIII — tetronate ring closure (TET-B)"),
    "ACP_syn_III":    ("PF08541", "3-oxoacyl-ACP synthase III (KSIII) — tetronate ring closure"),
    "ACP_syn_III_C":  ("PF08545", "KSIII C-terminus — tetronate ring closure"),
    "Chal_sti_synt_N":("PF00195", "chalcone/KSIII-type synthase N — tetronate ring-closure candidate"),
    "Chal_sti_synt_C":("PF02797", "chalcone/KSIII-type synthase C — tetronate ring-closure candidate"),
    "ksIII":          ("PF08541", "KSIII — tetronate ring closure"),
    # Enediyne
    "HMGL-like":      ("PF00682", "HMGL-like — enediyne pathway enzyme"),
    "CLF":            ("PF14765", "chain length factor — type II PKS/enediyne context"),
    "Radical_SAM":    ("PF04055", "radical SAM enzyme — enediyne/RiPP/thioamide context"),
    "PF04055":        ("PF04055", "radical SAM enzyme"),
    # Lanthipeptide
    "LANC_like":      ("PF05147", "LanC — class I/II lanthipeptide cyclase"),
    "DUF4135":        ("PF13575", "LanM — class II lanthipeptide synthetase"),
    "Pkinase":        ("PF00069", "LanL kinase — class III/IV lanthipeptide"),
    # RiPP
    "RRE":            ("PF13575", "RiPP recognition element — RiPP specificity determinant"),
    # Phosphonate
    "PEP_mutase":     ("PF05042", "phosphoenolpyruvate mutase — C-P bond biosynthesis (PHO class)"),
    "PF05042":        ("PF05042", "phosphoenolpyruvate mutase — C-P bond biosynthesis"),
    # Housekeeping exclusions (do not confuse with diagnostic signals)
    "TIGR02353":      ("TIGR02353","ε-poly-L-lysine synthetase — NAPAA housekeeping, not a discovery target"),
    "NRPS-like":      (None,      "NRPS-like — class-supporting, not diagnostic alone"),
    # Diagnostic Pfam/domain names extracted from antiSMASH sec_met_domain qualifiers
    "ketoacyl-synt":  ("PF00109", "PKS ketosynthase (ketoacyl-synt)"),
    "PP-binding":     ("PF00550", "phosphopantetheine-binding domain — ACP/PCP carrier"),
    "Trp_halogenase": ("PF04820", "tryptophan halogenase — flavin-dependent HAL"),
    "Flavoprotein":   ("PF01494", "FAD-dependent oxidoreductase — halogenase context"),
    "RRE_domain":     ("PF13575", "RiPP recognition element"),
    "lant_dehyd_N":   ("PF04738", "lanthipeptide dehydratase N-terminus — class I LanB"),
    "lant_dehyd_C":   ("PF14028", "lanthipeptide dehydratase C-terminus — class I LanB"),
    "DUF4218":        ("PF13927", "thiopeptide radical SAM enzyme"),
}

# Set of domain names that are tier-1 diagnostic (exact match)
_TIER1_DOMAIN_NAMES: frozenset[str] = frozenset({
    "YcaO", "PF02624", "TOMM_dh", "PF04825",
    "FkbH", "PF04113", "Diels_aldr", "PF13570",
    "PEP_mutase", "PF05042",
    "Radical_SAM", "PF04055",
    "LANC_like", "PF05147",
    "DUF4135", "PF13575",
    "HMGL-like", "PF00682",
    "AMP-binding", "PF00501",   # A-domain: enables Stachelhaus substrate prediction
    "lant_dehyd_N", "lant_dehyd_C",  # class I lanthipeptide dehydratase
    "DUF4218", "PF13927",       # thiopeptide radical SAM
    "Trp_halogenase", "PF04820",
    # TIGRFAM diagnostics (v9.4.1-tigrfix): these live in the JSON
    # antismash.detection.tigrfam module, NOT in GBK sec_met_domain, and were
    # previously dropped. Identifiers are the TIGR accessions.
    "TIGR01454",  # AHBA_synth_RP — ansamycin/rifamycin precursor (AHBA synthase)
    "TIGR03604",  # TOMM/thiopeptide cyclodehydratase (HMM-only CCTT marker)
    "TIGR03828",  # ene_KS — enediyne PKS
    "TIGR04186",  # NikJ-family — nucleoside antibiotic diagnostic
    # §8 diagnostic-combination markers (v9.6.15-tigr8): previously dropped by
    # the 4-ID DIAGNOSTIC_TIGRFAM allowlist, which silently disabled the §8
    # combos that key on these accessions. NAPAA (TIGR02353) is intentionally
    # NOT tier-1 (housekeeping, excluded from comparative claims).
    "TIGR04462", "TIGR04460",              # enduracididine-type NRPS
    "TIGR03550", "TIGR03551", "TIGR03620", # F420-embedded polyketide
    "TIGR04363", "TIGR04364",              # FxLD class-I lanthipeptide
    "TIGR01181",                           # glycosylated T2PKS
})

# TIGRFAM diagnostics (accession → (class_label, description, tier1_diagnostic)).
# Extracted from the JSON antismash.detection.tigrfam module and merged into
# gbk_pfam_hits.  The §8-block accessions were added in v9.6.15-tigr8: the prior
# 4-ID allowlist surfaced only TIGR03604 of the §8 set, silently disabling every
# §8 diagnostic-domain combination that keys on a TIGRFAM ID.  Keep this list
# in sync with the SECTION 8 diagnostic-domain table.
DIAGNOSTIC_TIGRFAM = {
    # --- original v9.4.1-tigrfix diagnostics ---
    "TIGR01454": ("ansamycin",   "AHBA_synth_RP: AHBA synthesis associated protein", True),
    "TIGR03604": ("thiopeptide", "TOMM/thiopeptide cyclodehydratase", True),
    "TIGR03828": ("enediyne",    "ene_KS: enediyne polyketide synthase", True),
    "TIGR04186": ("nucleoside",  "NikJ-family nucleoside antibiotic enzyme", True),
    # --- §8 diagnostic-combination markers (v9.6.15-tigr8) ---
    "TIGR04462": ("enduracididine", "enduracididine-type NRPS marker (lipid II inhibitor class)", True),
    "TIGR04460": ("enduracididine", "enduracididine-type NRPS marker (lipid II inhibitor class)", True),
    "TIGR03550": ("F420_polyketide", "F420-embedded polyketide marker", True),
    "TIGR03551": ("F420_polyketide", "F420-embedded polyketide marker", True),
    "TIGR03620": ("F420_polyketide", "F420-embedded polyketide marker", True),
    "TIGR04363": ("lanthipeptide_FxLD", "FxLD class-I lanthipeptide marker", True),
    "TIGR04364": ("lanthipeptide_FxLD", "FxLD class-I lanthipeptide marker", True),
    "TIGR01181": ("glyco_T2PKS", "glycosylated T2PKS marker", True),
    # NAPAA is common and treated as NEUTRAL (build -r) — neither excluded from comparative
    # claims nor tier-1 weighted; surfaced for §8 combo detection (PF12029 + TIGR02353) only.
    "TIGR02353": ("NAPAA_marker",
                  "ε-poly-L-lysine synthetase — NAPAA marker; common, treated as neutral (combo-detection only, not tier-1)", False),
}
# e.g. "YcaO (E-value: 3.2e-64, bitscore: 206.5, seeds: 57, tool: rule-based-clusters)"
_SEC_MET_RE = re.compile(
    r'^([A-Za-z0-9_\-\.]+(?:\s+[A-Za-z0-9_\-\.]+)?)\s*\(E-value:\s*([\d.e+\-]+)'
    r'(?:,\s*bitscore:\s*([\d.]+))?'
)


def _read_text(zf, name):
    return zf.read(name).decode("utf-8", errors="replace")


def extract_gbk_pfam_hits(zip_path: str | Path) -> dict[str, list[dict]]:
    """Extract sec_met_domain Pfam/domain hits from antiSMASH region GBK files.

    antiSMASH runs HMMER internally and stores results as /sec_met_domain
    qualifiers in every region GBK.  This function surfaces those results
    without re-running any external tool.

    Returns: dict keyed by region_key (e.g. "NODE_2_length_..._c1") →
             list of dicts with keys: domain_name, pfam_acc, evalue,
             bitscore, locus_tag, tier1_diagnostic.
    """
    hits: dict[str, list[dict]] = {}
    try:
        from ._gbk_shim import parse_genbank_text
    except ImportError:
        return hits

    with zipfile.ZipFile(zip_path) as zf:
        from .parsers import is_macos_cruft  # PARSE-P03 (deferred: parsers imports this module)
        gbk_names = [n for n in regular_file_names(zf)
                     if n.lower().endswith(".gbk") and "region" in n.lower() and not is_macos_cruft(n)]
        for name in gbk_names:
            _, region_num, region_key = _region_key_from_name(name)
            if region_key is None:
                continue
            try:
                text = _read_text(zf, name)
                records = parse_genbank_text(text)
            except Exception:
                continue
            region_hits: list[dict] = []
            for rec in records:
                for feat in rec.features:
                    if feat.type not in ("CDS", "aSDomain", "domain"):
                        continue
                    locus = (feat.qualifiers.get("locus_tag", [""])[0] or
                             feat.qualifiers.get("protein_id", [""])[0])
                    for smd_val in feat.qualifiers.get("sec_met_domain", []):
                        m = _SEC_MET_RE.match(smd_val.strip())
                        if not m:
                            continue
                        dom_name = m.group(1).strip()
                        evalue   = m.group(2)
                        bitscore = m.group(3) or ""
                        info     = DIAGNOSTIC_SEC_MET_DOMAINS.get(dom_name)
                        pfam_acc = info[0] if info else None
                        desc     = info[1] if info else None
                        is_tier1 = dom_name in _TIER1_DOMAIN_NAMES or (pfam_acc in _TIER1_DOMAIN_NAMES if pfam_acc else False)
                        region_hits.append({
                            "domain_name":     dom_name,
                            "pfam_acc":        pfam_acc,
                            "description":     desc,
                            "evalue":          evalue,
                            "bitscore":        bitscore,
                            "locus_tag":       locus,
                            "tier1_diagnostic": is_tier1,
                        })
            if region_hits:
                hits.setdefault(region_key, []).extend(region_hits)
    return hits


def extract_tigrfam_hits(zip_path: str | Path) -> dict[str, list[dict]]:
    """Extract diagnostic TIGRFAM hits from the antiSMASH JSON.

    antiSMASH stores TIGRFAM results in records[].modules
    ``antismash.detection.tigrfam.hits[]`` — NOT in the GBK sec_met_domain
    qualifiers that :func:`extract_gbk_pfam_hits` reads.  Diagnostics such as
    AHBA_synth_RP (TIGR01454, ansamycin), ene_KS (TIGR03828, enediyne),
    TIGR03604 (thiopeptide) and NikJ-family (TIGR04186, nucleoside) were
    therefore dropped from the package evidence — the v9.4.1-tigrfix defect.

    Only the diagnostics in DIAGNOSTIC_TIGRFAM are surfaced (keeping the
    extraction targeted; the full TIGRFAM set is large and mostly housekeeping).
    Returns the same shape as extract_gbk_pfam_hits: region_key → list[dict].
    """
    out: dict[str, list[dict]] = {}
    _run_record_extractors(zip_path, [(_tigrfam_from_rec, out)])
    return out


def merge_tigrfam_into_pfam_hits(gbk_hits: dict[str, list[dict]],
                                  tigrfam_hits: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Merge TIGRFAM diagnostic hits into the gbk_pfam_hits structure.

    Append-only: TIGRFAM hits are added alongside any existing Pfam hits for
    the same region.  When a locus already has a (weaker, generic) Pfam call
    AND a TIGRFAM diagnostic, BOTH are retained — the consumer can then see the
    strong diagnostic (e.g. AHBA_synth_RP) instead of only the generic HAD_2.
    """
    for region_key, hlist in tigrfam_hits.items():
        gbk_hits.setdefault(region_key, []).extend(hlist)
    return gbk_hits




# ---- single-pass record evidence ----------------------------------------------------------------
# Each _X_from_rec is the per-record body of the matching public extractor (single source of truth).
# _run_record_extractors makes ONE pass over the JSON records, feeding every handler — collapsing
# four independent full-JSON parses (each ~1 GB peak on a large genome) into one streamed pass.
# Per-handler try/except: a bad record for one handler never aborts the shared pass or the others
# (>= the isolation of the old separate single-purpose passes). The public extract_X functions remain
# as thin wrappers (one pass each) for API/back-compat; the package path uses _extract_record_evidence.

# v9.7.87 P-10 (see _product_class_from_rec) fixed this exact bug class for t2pks/terpene
# predictions by resolving the true region via genomic coordinate overlap instead of
# broadcasting to a single hardcoded bucket. TIGRFAM hits were never given the same fix. A
# hit's own `location` field is a Biopython-style "[start:end](strand)" string.
_TIGRFAM_LOC_RE = re.compile(r"[<\[]?(\d+)\s*:\s*>?(\d+)")


def _tigrfam_from_rec(rec, name, out):
    # out is a dict region_key -> list[dict] (shape matches extract_gbk_pfam_hits).
    rec_id = rec.get("id") or ""
    tf = (rec.get("modules", {})
             .get("antismash.detection.tigrfam", {}))
    # `areas` gives every region's [start,end) span in antiSMASH's own sequential region-
    # numbering order (areas[0]=region001, areas[1]=region002, ...) -- the SAME convention
    # nrps_predictions.py::extract_region_polymers already relies on in the forward direction
    # (`areas[region_number - 1]`). Used here in reverse: given a hit's coordinate, find which
    # area contains it.
    areas = rec.get("areas") or []
    for h in tf.get("hits", []):
        acc = h.get("identifier") or h.get("domain")
        if acc not in DIAGNOSTIC_TIGRFAM:
            continue
        cls, desc, tier1 = DIAGNOSTIC_TIGRFAM[acc]
        # BC2-408: was unconditionally `f"{rec_id}_c1"` regardless of which region the hit
        # actually falls in -- correct only by coincidence on a genome where every contig
        # carries exactly one region. On any contig with >=2 antiSMASH regions, every TIGRFAM
        # hit (including TIER_1_DIAGNOSTIC markers: ansamycin/AHBA_synth_RP, enediyne/ene_KS,
        # thiopeptide/TIGR03604, nucleoside/NikJ-family, ...) was silently mis-keyed: region 1's
        # BGC absorbed hits from every sibling region on the same contig, and every other
        # region's own BGC lost its real hits entirely. Confirmed downstream: lead_board.py's
        # `_tigrfam_hits_for_region` and antismash_tables.py's `build_hmm_table` both do an
        # EXACT region_key dict lookup against this output, so both silently inherited the
        # misattribution -- not just a display-adjacent bug, a diagnostic-evidence bug feeding
        # the actual per-strain Lead Board and the antiSMASH HMM hit table. Resolve the hit's
        # real region by genomic coordinate overlap; fall back to the historical "_c1" only when
        # location or areas are unavailable, so a genuinely unresolvable hit still surfaces
        # (degrades to the old behaviour) rather than being silently dropped.
        region_num = None
        loc_match = _TIGRFAM_LOC_RE.search(str(h.get("location") or ""))
        if loc_match and areas:
            hit_start = int(loc_match.group(1))
            for idx, area in enumerate(areas, start=1):
                a_start, a_end = area.get("start"), area.get("end")
                if a_start is not None and a_end is not None and a_start <= hit_start < a_end:
                    region_num = idx
                    break
        region_key = (f"{rec_id}_c{region_num}" if rec_id and region_num
                      else (f"{rec_id}_c1" if rec_id else "_unkeyed"))
        out.setdefault(region_key, []).append({
            "domain_name":      acc,
            "pfam_acc":         acc,
            "description":      h.get("description") or desc,
            "evalue":           str(h.get("evalue", "")),
            "bitscore":         str(h.get("score", "")),
            "locus_tag":        h.get("locus_tag") or h.get("label") or "",
            "tier1_diagnostic": tier1,
            "source":           "tigrfam_json",
            "tigrfam_class":    cls,
        })


def _nrps_pks_from_rec(rec, name, out):
    rec_id = rec.get("id") or ""
    nrps = (rec.get("modules", {})
              .get("antismash.modules.nrps_pks", {}))
    domain_predictions = nrps.get("domain_predictions", {})
    for field in ("consensus", "consensus_transat"):
        values = nrps.get(field, {})
        if not isinstance(values, dict):
            continue
        for domain_id, substrate in values.items():
            if substrate in (None, ""):
                continue
            out.append({
                "source": name,
                "record_id": rec_id,
                "domain_id": str(domain_id),
                "locus_tag": str(domain_id),
                "prediction_field": field,
                "consensus_substrate": substrate,
                "domain_prediction": domain_predictions.get(domain_id, {}),
            })


def _active_site_from_rec(rec, name, out):
    rec_id = rec.get("id") or ""
    asf = (rec.get("modules", {})
             .get("antismash.modules.active_site_finder", {}))
    for pair in asf.get("pairings", []):
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        domain_id, calls = pair
        out.append({
            "source": name,
            "record_id": rec_id,
            "domain_id": str(domain_id),
            "locus_tag": str(domain_id),
            "active_site_calls": calls,
        })


def _product_class_from_rec(rec, name, out):
    rec_id = rec.get("id") or ""
    for mod in ("antismash.modules.t2pks", "antismash.modules.terpene"):
        pp = (rec.get("modules", {}).get(mod, {})
                .get("protocluster_predictions", {}))
        if not isinstance(pp, dict):
            continue
        for protocluster_id, pred in pp.items():
            if not isinstance(pred, dict):
                continue
            out.append({
                "source": name,
                "record_id": rec_id,
                "module": mod,
                "protocluster_id": str(protocluster_id),
                "product_classes": pred.get("product_classes", []),
                "products": pred.get("products", []),
                "starter_units": pred.get("starter_units", []),
                "elongations": pred.get("elongations", []),
                # v9.7.87 P-10: the prediction's own genomic coordinates, so the caller can
                # match a prediction to the BGC it actually falls in (by coordinate overlap)
                # instead of broadcasting every contig-level prediction to every BGC on the
                # contig. On a complete single-contig genome the contig key collapses to one
                # bucket, mislabelling all BGCs; coordinate overlap is the correct granularity.
                "start": pred.get("start"),
                "end": pred.get("end"),
                "prediction": pred,
            })


# Reference list of the RiPP families antiSMASH historically emitted as motif modules. NOT an
# extraction allowlist anymore (v9.7.99): _ripp_from_rec is data-driven and captures EVERY
# antismash.modules.<family> carrying a RiPP-shaped 'motifs' dict, so families beyond these four
# (ranthipeptides, thioamitides, lipolanthines, microviridins, cyanobactins, bottromycins, …) are no
# longer silently dropped. Kept for documentation/cross-reference only.
_RIPP_MODULES = ("lanthipeptides", "lassopeptides", "sactipeptides", "thiopeptides")

_RIPP_MODULE_PREFIX = "antismash.modules."


def _ripp_from_rec(rec, name, out):
    rec_id = rec.get("id") or ""
    modules = rec.get("modules", {})
    # Data-driven (v9.7.99): iterate every antismash.modules.<family> that carries a 'motifs' dict,
    # rather than a hardcoded family tuple. antiSMASH 8 detects more RiPP families than the original
    # four; a hardcoded list silently drops any it does not enumerate. Non-RiPP modules are naturally
    # excluded — their motif entries lack a 'core' and are skipped below.
    for mod_key, mod_val in modules.items():
        if not mod_key.startswith(_RIPP_MODULE_PREFIX) or not isinstance(mod_val, dict):
            continue
        motifs = mod_val.get("motifs", {})
        if not isinstance(motifs, dict) or not motifs:
            continue
        family = mod_key[len(_RIPP_MODULE_PREFIX):]
        for locus, motif_list in motifs.items():
            items = motif_list if isinstance(motif_list, list) else [motif_list]
            for idx, motif in enumerate(items):
                if not isinstance(motif, dict):
                    continue
                core = motif.get("core") or motif.get("core_sequence") or ""
                if not core:
                    continue
                out.append({
                    "source": name,
                    "record_id": rec_id,
                    "module": f"antismash.modules.{family}",
                    "ripp_family": family,
                    "locus_tag": str(locus),
                    "motif_index": idx,
                    "core": core,
                    "core_sequence": core,
                    "peptide_class": motif.get("peptide_class", ""),
                    "peptide_subclass": motif.get("peptide_subclass", ""),
                    "leader": motif.get("leader", ""),
                    "tail": motif.get("tail", ""),
                    "motif": motif,
                })


def _rrefinder_from_rec(rec, name, out):
    """Preserve one normalized source row per antiSMASH RRE-Finder hit.

    ``hits_by_protocluster`` and ``hits_by_cds`` are two indices over the same
    calls.  Emitting from both would double-count them, so the former is used
    only to annotate each CDS with its protocluster bucket(s), while the latter
    remains the sole row source.
    """
    rec_id = rec.get("id") or ""
    module = (rec.get("modules", {})
                 .get("antismash.modules.rrefinder", {}))
    if not isinstance(module, dict):
        return
    by_cds = module.get("hits_by_cds", {})
    if not isinstance(by_cds, dict) or not by_cds:
        return
    protoclusters_by_locus: dict[str, list[str]] = {}
    for protocluster, loci in (module.get("hits_by_protocluster", {}) or {}).items():
        if not isinstance(loci, list):
            continue
        for locus in loci:
            key = str(locus)
            protoclusters_by_locus.setdefault(key, []).append(str(protocluster))
    seen = set()
    for locus, hits in by_cds.items():
        items = hits if isinstance(hits, list) else [hits]
        for hit in items:
            if not isinstance(hit, dict):
                continue
            key = (
                rec_id,
                str(locus),
                str(hit.get("location", "")),
                str(hit.get("domain", "")),
                str(hit.get("identifier", "")),
                str(hit.get("evalue", "")),
                str(hit.get("score", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "source": name,
                "record_id": rec_id,
                "protoclusters": sorted(set(protoclusters_by_locus.get(str(locus), []))),
                "locus_tag": str(hit.get("locus_tag") or hit.get("label") or locus),
                "location": str(hit.get("location", "")),
                "rre_family": str(hit.get("domain", "")),
                "rre_description": str(hit.get("description", "")),
                "rrefam_identifier": str(hit.get("identifier", "")),
                "evalue": hit.get("evalue"),
                "bitscore": hit.get("score"),
                "protein_start": hit.get("protein_start"),
                "protein_end": hit.get("protein_end"),
                "module_schema_version": module.get("schema_version"),
                "bitscore_cutoff": module.get("bitscore_cutoff"),
                "minimum_protein_length": module.get("min_length"),
            })


def _run_record_extractors(zip_path, handlers):
    """One pass over every JSON record, feeding each handler.

    handlers: iterable of (handler_fn, out_list). handler_fn(rec, name, out_list) appends its
    evidence. Per-handler try/except isolates failures: a malformed record for one handler skips
    only that record for that handler, never aborting the shared pass or the other handlers.
    Streaming/full-load is decided once per file by _should_stream, so memory stays flat on large
    genomes while every handler sees the same records in the same (name, record) order.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            from .parsers import is_macos_cruft  # PARSE-P08 (deferred import: parsers imports this module)
            json_names = [n for n in regular_file_names(zf) if n.lower().endswith(".json") and not is_macos_cruft(n)]
            for name in json_names:
                try:
                    _recs = _iter_records(zf, name)
                    if not _should_stream(zf, name):
                        # PARSE-05: the non-streaming branch json.loads-es the whole doc. Guard it
                        # so an oversized JSON is skipped rather than full-loaded unbounded.
                        if zf.getinfo(name).file_size > FULL_MAX_JSON_BYTES:
                            continue
                        _recs = list(_recs)   # non-stream: force parse now so a bad JSON file is skipped here
                except Exception:
                    continue
                for rec in _recs:
                    for fn, out in handlers:
                        try:
                            fn(rec, name, out)
                        except Exception:
                            continue
    except Exception:
        return


def extract_nrps_pks_consensus(zip_path: str | Path) -> list[dict[str, Any]]:
    """Extract antiSMASH NRPS/PKS consensus substrate predictions.

    antiSMASH stores A-domain/CAL-domain/AT-domain substrate calls in
    records[].modules["antismash.modules.nrps_pks"].consensus and consensus_transat. These are not
    Pfam hits and must be conserved as separate append-only package evidence, keyed by record + domain id.
    """
    out: list[dict[str, Any]] = []
    _run_record_extractors(zip_path, [(_nrps_pks_from_rec, out)])
    return out


def extract_active_site_pairings(zip_path: str | Path) -> list[dict[str, Any]]:
    """Extract antiSMASH active-site / stereochemistry pairings.

    Preserves records[].modules["antismash.modules.active_site_finder"].pairings as append-only
    evidence keyed by record + domain id.
    """
    out: list[dict[str, Any]] = []
    _run_record_extractors(zip_path, [(_active_site_from_rec, out)])
    return out


def extract_product_class_predictions(zip_path: str | Path) -> list[dict[str, Any]]:
    """Extract t2pks/terpene protocluster product-class predictions.

    Preserves direct antiSMASH product-class/protocluster predictions as append-only evidence keyed
    by record + module + protocluster id.
    """
    out: list[dict[str, Any]] = []
    _run_record_extractors(zip_path, [(_product_class_from_rec, out)])
    return out


def extract_ripp_cores(zip_path: str | Path) -> list[dict[str, Any]]:
    """Extract antiSMASH RiPP motif core-peptide sequences.

    antiSMASH stores RiPP precursor/core calls in records[].modules["antismash.modules.<family>"].motifs,
    where motifs is a dict keyed by locus and each value is a list of motif dictionaries. These core
    sequences are the diagnostic product-backbone evidence for lanthipeptide/lasso/sacti/thiopeptide
    BGCs and must be conserved as append-only package evidence.
    """
    out: list[dict[str, Any]] = []
    _run_record_extractors(zip_path, [(_ripp_from_rec, out)])
    return out


def extract_rrefinder_hits(zip_path: str | Path) -> list[dict[str, Any]]:
    """Extract de-duplicated antiSMASH RRE-Finder HMM calls."""
    out: list[dict[str, Any]] = []
    _run_record_extractors(zip_path, [(_rrefinder_from_rec, out)])
    return out


def _extract_record_evidence(zip_path: str | Path,
                              include_extras: bool = True,
                              want_tigrfam: bool = True) -> dict[str, Any]:
    """Single-pass extraction of record-level evidence (one JSON parse for everything requested).

    want_tigrfam   — extract TIGRFAM diagnostics (only the consumer that feeds the gbk/Pfam merge
                     needs them; the BGC-evidence-application path does not, so it opts out to avoid
                     a wasted pass).
    include_extras — extract the five json-evidence record kinds (nrps_pks consensus, active-site
                     pairings, product-class predictions, RiPP cores, RRE-Finder); set when
                     json_mode != 'off'.

    Everything requested is gathered in ONE pass. If nothing is requested (off mode + no tigrfam),
    no pass is made at all.
    """
    tigrfam: dict[str, list[dict]] = {}
    nrps: list[dict[str, Any]] = []
    asite: list[dict[str, Any]] = []
    pclass: list[dict[str, Any]] = []
    ripp: list[dict[str, Any]] = []
    rrefinder: list[dict[str, Any]] = []
    handlers: list = []
    if want_tigrfam:
        handlers.append((_tigrfam_from_rec, tigrfam))
    if include_extras:
        handlers += [
            (_nrps_pks_from_rec, nrps),
            (_active_site_from_rec, asite),
            (_product_class_from_rec, pclass),
            (_ripp_from_rec, ripp),
            (_rrefinder_from_rec, rrefinder),
        ]
    if handlers:
        _run_record_extractors(zip_path, handlers)
    return {
        "tigrfam_hits": tigrfam,
        "nrps_pks_consensus": nrps,
        "active_site_pairings": asite,
        "product_class_predictions": pclass,
        "ripp_cores": ripp,
        "rrefinder_hits": rrefinder,
    }


def _flatten(obj, prefix=""):
    """Legacy full-document flattener. Only used in json_mode='full'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _region_key_from_name(name: str) -> tuple[str | None, int | None, str | None]:
    """Extract a stable antiSMASH region key from a filename.

    antiSMASH restarts the ``_cN``/``regionNNN`` counter on every contig.
    Therefore the bare integer is NOT a valid key for multi-contig assemblies.
    The stable key is the full contig + cluster composite, for example
    ``WOFH01000001.1_c1`` or ``CP073042.1_c38``.
    """
    base = Path(name).name

    # Standard region GBK/TXT names: <contig>.region001.gbk
    m = re.match(r"(.+?)\.region0*(\d+)\.[^.]+$", base, flags=re.I)
    if m:
        contig = m.group(1)
        region = int(m.group(2))
        return contig, region, f"{contig}_c{region}"

    # antiSMASH clusterblast names: <contig>_c1.txt.  Contigs may be accessions
    # like WOFH01000001.1 or CP073042.1, not just NODE_*.
    m = re.match(r"(.+?)_c0*(\d+)\.txt$", base, flags=re.I)
    if m:
        contig = m.group(1)
        region = int(m.group(2))
        return contig, region, f"{contig}_c{region}"

    # Last-resort region number, deliberately not used for KCB assignment unless
    # no contig can be recovered. This prevents cross-contig score pooling.
    m = re.search(r"region0*(\d+)", base, flags=re.I)
    if m:
        return None, int(m.group(1)), None
    return None, None, None


def _region_key_for_bgc(bgc) -> str | None:
    if getattr(bgc, "contig", None) and getattr(bgc, "region_number", None) is not None:
        return f"{bgc.contig}_c{int(bgc.region_number)}"
    return None


def _parse_txt_evidence(zf, names: list[str], evidence: dict) -> None:
    """Parse TXT knownclusterblast / clusterblast / MIBiG files.

    Primary KCB source. Fast regardless of genome size.
    """
    txts = [n for n in names
            if n.lower().endswith(".txt")
            and ("clusterblast" in n.lower() or "mibig" in n.lower())]
    for name in txts:
        evidence["txt_files"].append(name)
        text = _read_text(zf, name)
        _, region, region_key = _region_key_from_name(name)
        compounds = []
        mibigs = re.findall(r"BGC\d{7,}\.\d+|BGC\d{7,}", text)

        # Parse antiSMASH ClusterBlast detail blocks.  The previous parser
        # treated every line containing the word "score" as numeric evidence,
        # which incorrectly extracted accession fragments such as CP073042.1
        # from the header "ClusterBlast scores for CP073042.1".  It also
        # counted all BLAST rows across all subject clusters as protein hits.
        # KCB score/protein-hit values should be from a single subject-cluster
        # block; we use the block with the highest cumulative BLAST score and
        # carry its matching "Number of proteins" value.
        block_records = []
        blocks = re.split(r"\n>>\s*\n", text)
        for block in blocks:
            score_m = re.search(r"Cumulative\s+BLAST\s+score:\s*([0-9][0-9,]*(?:\.\d+)?)", block, flags=re.I)
            if not score_m:
                continue
            score = float(score_m.group(1).replace(",", ""))
            prot_m = re.search(r"Number\s+of\s+proteins\s+with\s+BLAST\s+hits\s+to\s+this\s+cluster:\s*(\d+)", block, flags=re.I)
            prot_hits_block = int(prot_m.group(1)) if prot_m else None
            src_m = re.search(r"Source:\s*(.+)", block)
            typ_m = re.search(r"Type:\s*(.+)", block)
            mibig_m = re.search(r"(BGC\d{7,}\.\d+|BGC\d{7,})", block)
            label_parts = []
            if mibig_m:
                label_parts.append(mibig_m.group(1))
            if src_m:
                label_parts.append(src_m.group(1).strip())
            if typ_m:
                label_parts.append(f"Type: {typ_m.group(1).strip()}")
            block_records.append({
                "score": score,
                "protein_hits": prot_hits_block,
                "label": " | ".join(label_parts)[:300] if label_parts else None,
            })
        # BUGFIX (2026-07-01, KCB rank-vs-score): antiSMASH's "Significant hits" list is
        # ordered by BLAST significance (rank 1 = most significant / closest known cluster),
        # NOT by raw Cumulative BLAST score — a lower-ranked hit (e.g. a broad-spectrum PKS
        # comparator) can carry a numerically higher score than the file's own rank-1 hit
        # without being the more meaningful comparator. max(block_records, key=score) was
        # picking whichever block had the single largest number anywhere in the file,
        # regardless of rank. Confirmed on AS-XXX BGC058: rank 46 (tetrafibricin, 61753.0)
        # outscored rank 1 (aculeximycin, 37992.0), so the old code silently reported
        # tetrafibricin as the "top" KCB hit. Fix: take the FIRST block encountered, which
        # corresponds to rank 1 in the file's own ordering (blocks are split in file order,
        # which matches the ">>"-delimited hit sequence antiSMASH writes rank-first).
        best = block_records[0] if block_records else None

        significant_hits = []
        in_significant = False
        for line in text.splitlines():
            low_line = line.lower().strip()
            if low_line.startswith("significant hits"):
                in_significant = True
                continue
            if in_significant and (low_line.startswith("details") or low_line.startswith(">>")):
                in_significant = False
            if in_significant:
                m_hit = re.match(r"\s*(\d+)\.\s+(BGC\d{7,}(?:\.\d+)?)\s+(.+?)\s*$", line)
                if m_hit:
                    significant_hits.append({
                        "rank": int(m_hit.group(1)),
                        "accession": m_hit.group(2),
                        "product": re.sub(r"\s+", " ", m_hit.group(3).strip()),
                        "line": re.sub(r"\s+", " ", line.strip()),
                    })
            if any(x in line.lower() for x in
                   ["mibig", "knownclusterblast", "most similar", "compound", "biosynthetic"]):
                clean = re.sub(r"\s+", " ", line.strip())
                if clean and len(clean) < 300:
                    compounds.append(clean)
        if best and best.get("label"):
            compounds.insert(0, str(best["label"]))

        is_knownclusterblast = "knownclusterblast" in name.lower()
        rec = {
            "source": name,
            "source_kind": "knownclusterblast" if is_knownclusterblast else "clusterblast",
            "mibig_hits": sorted(set(mibigs)),
            "mibig_reference_hits": significant_hits if is_knownclusterblast else [],
            "candidate_lines": compounds[:20],
            "cumulative_score": best["score"] if best else None,
            "protein_hits": best.get("protein_hits") if best else None,
            # v9.7.166: top-N ranked hits WITH organism labels, in file (rank) order — the data
            # the previous parser discarded after taking rank-1. Only for clusterblast (organism
            # hits); knownclusterblast MIBiG hits are already in mibig_reference_hits.
            "clusterblast_ranked": [
                {"rank": i + 1, "label": r["label"], "score": r["score"],
                 "protein_hits": r.get("protein_hits")}
                for i, r in enumerate(block_records[:10]) if r.get("label")
            ] if not is_knownclusterblast else [],
            "kcb_parse_method": "best_subject_cluster_block_v1.9.2+significant_hits_v1.1",
        }
        if region_key is not None:
            rec["region_key"] = region_key
            rec["region_number"] = region
            evidence["by_region"].setdefault(region_key, []).append(rec)
        else:
            rec["region_number"] = region
            evidence["loose_hits"].append(rec)


def _parse_json_bounded(zf, name: str, evidence: dict) -> None:
    """Stream the JSON with ijson, extracting only KCB/RiQ-relevant leaves.

    Never materialises the whole document. Memory stays flat regardless of file size.

    RiQ region mapping: antiSMASH writes region_to_region RiQ under
    ``records.item.modules...cluster_compare...by_region.<N>.RegionToRegion_RiQ...``.
    Under ``ijson.parse`` array elements collapse to the literal token ``item``, so the
    prefix alone cannot say WHICH record a leaf belongs to. Aggregate scores inside each
    record and bind them only when that record closes: JSON object key order is arbitrary,
    so the id can follow the scores. An absent id must never inherit the previous record's
    identity. Incomplete records and scores outside a record remain explicitly unassigned.
    Pending storage retains only a maximum and observation count per region, not all hits.
    """
    # Flat-memory streaming admits a far larger leaf budget than the old 25 MB-byte regime.
    cap = BOUNDED_MAX_RECORDS_STREAMING if _HAVE_IJSON else BOUNDED_MAX_RECORDS
    matched = 0
    current_rec_id = None
    record_open = False
    record_id_count = 0
    containers: list[tuple[str, str]] = []
    pending_riq: dict[int, tuple[float, str, int]] = {}
    riq_by_region: dict[str, float] = {}
    riq_unmapped = 0

    def flush_record(record_id, reason):
        nonlocal riq_unmapped
        for region, (score, prefix, count) in pending_riq.items():
            if record_id:
                rk = f"{record_id}_c{region}"
                riq_by_region[rk] = max(riq_by_region.get(rk, score), score)
            else:
                riq_unmapped += count
                evidence["loose_hits"].append({
                    "source": name, "path": prefix, "riq_score": score,
                    "riq_identity_status": reason,
                    "riq_observation_count": count,
                })
        pending_riq.clear()

    try:
        with zf.open(name) as raw:
            parser = ijson.parse(raw)
            for prefix, event, value in parser:
                if event in ("start_map", "start_array"):
                    # Prefixes alone cannot distinguish records[] from an object
                    # named records.item (or records: {item: ...}).
                    if (prefix == "records.item" and event == "start_map"
                            and containers == [("", "start_map"), ("records", "start_array")]):
                        current_rec_id = None
                        record_id_count = 0
                        record_open = True
                    containers.append((prefix, event))
                    continue
                if event in ("end_map", "end_array"):
                    if record_open and len(containers) == 3 and prefix == "records.item":
                        flush_record(current_rec_id if record_id_count == 1 else None,
                                     "UNMAPPED_DUPLICATE_RECORD_ID" if record_id_count > 1
                                     else "UNMAPPED_MISSING_RECORD_ID")
                        current_rec_id = None
                        record_open = False
                    containers.pop()
                    continue
                if record_open and len(containers) == 3:
                    if event == "map_key" and value == "id":
                        record_id_count += 1
                        current_rec_id = None
                    if prefix == "records.item.id":
                        current_rec_id = value if event == "string" and value.strip() else None
                        continue
                    continue
                if event not in ("string", "number"):
                    continue
                low = prefix.lower()
                # RiQ scores are the primary value of the JSON pass, cheap (a handful per region),
                # and may sit behind earlier records' bulky clusterblast leaves. Capture observed
                # scores before the leaf-cap check; later unobserved scores can still be truncated.
                # Genuine score = 0–1 ratio
                # under ...RegionToRegion_RiQ.scores_by_region.<ref>; the surrounding subtree also holds
                # coordinate/bitscore integers, so require scores_by_region + the [0,1] range.
                if ("scores_by_region" in low and isinstance(value, (int, float, Decimal))
                        and 0.0 <= float(value) <= 1.0):
                    m = re.search(r"by_region\.(\d+)\.", prefix)
                    if m and record_open and prefix.startswith("records.item."):
                        region = int(m.group(1))
                        score = float(value)
                        prev = pending_riq.get(region)
                        pending_riq[region] = (
                            max(prev[0], score) if prev else score,
                            prefix if prev is None or score > prev[0] else prev[1],
                            prev[2] + 1 if prev else 1,
                        )
                    else:
                        riq_unmapped += 1
                        evidence["loose_hits"].append({
                            "source": name, "path": prefix, "riq_score": float(value),
                            "riq_identity_status": "UNMAPPED_RECORD_OR_REGION"})
                    continue
                if matched >= cap:
                    evidence["json_bounded_truncated"] = True
                    break
                if any(k in low for k in
                       ["knownclusterblast", "clusterblast", "region_to_region", "riq", "mibig"]):
                    if isinstance(value, str) and re.search(r"BGC\d{7}", value):
                        evidence["loose_hits"].append({
                            "source": name, "path": prefix,
                            "mibig_hits": re.findall(r"BGC\d{7,}\.?\d*", value)})
                        matched += 1
                    elif isinstance(value, str) and len(value) < 500 and "_riq" not in low:
                        # Skip the RegionToRegion_RiQ / ProtoToRegion_RiQ hit-detail strings: they are
                        # an unused similarity matrix that otherwise floods the record cap. KCB/MIBiG
                        # naming (the useful strings) live outside the *_RiQ subtree and still pass.
                        evidence["loose_hits"].append({
                            "source": name, "path": prefix, "value": value})
                        matched += 1
    except Exception as exc:
        evidence.setdefault("json_errors", []).append(
            f"{name}: {type(exc).__name__}: {exc}")
    finally:
        # A cap or parse error can stop before end_map. Preserve observed values
        # without assigning them from a partial record's potentially unfinished id.
        flush_record(None, "UNMAPPED_INCOMPLETE_RECORD")

    # Fold mapped RiQ into by_region so the per-BGC assignment loop sees it.
    for rk, score in riq_by_region.items():
        evidence["by_region"].setdefault(rk, []).append(
            {"source": name, "region_key": rk, "riq_score": score})
    if riq_by_region or riq_unmapped:
        scores = sorted(riq_by_region.values())
        evidence["riq_mapped_count"] = len(riq_by_region)
        evidence["riq_unmapped_count"] = riq_unmapped
        evidence["riq_mapping_status"] = "MAPPED" if riq_by_region else "UNMAPPED_LOOSE_VALUES_NOT_ASSIGNED_TO_BGC"
        if scores:
            evidence["riq_genome_summary"] = {
                "regions_with_riq": len(scores),
                "median": _riq_median(scores),
                "max": scores[-1]}


def _parse_json_full(zf, name: str, evidence: dict) -> None:
    """Legacy full flatten. Refuses files above FULL_MAX_JSON_BYTES."""
    info = zf.getinfo(name)
    if info.file_size > FULL_MAX_JSON_BYTES:
        evidence.setdefault("json_skipped", []).append(
            f"{name}: {info.file_size:,} bytes exceeds full-mode cap "
            f"({FULL_MAX_JSON_BYTES:,}); use --json-evidence bounded or off")
        return
    try:
        data = json.loads(_read_text(zf, name))
    except Exception as exc:
        evidence.setdefault("json_errors", []).append(f"{name}: {exc}")
        return
    for path, val in _flatten(data):
        low = path.lower()
        if any(k in low for k in
               ["knownclusterblast", "clusterblast", "region_to_region", "riq", "mibig"]):
            if isinstance(val, str) and re.search(r"BGC\d{7}", val):
                evidence["loose_hits"].append({
                    "source": name, "path": path,
                    "mibig_hits": re.findall(r"BGC\d{7,}\.?\d*", val)})
            elif "riq" in low and isinstance(val, (int, float)):
                evidence["loose_hits"].append({
                    "source": name, "path": path, "riq_score": float(val)})
            else:
                evidence["loose_hits"].append({
                    "source": name, "path": path, "value": str(val)[:500]})


def parse_antismash_evidence(zip_path: str | Path,
                              json_mode: str = JSON_MODE_DEFAULT,
                              want_tigrfam: bool = False,
                              include_structured: bool = False) -> dict[str, Any]:
    """Best-effort antiSMASH evidence parser.

    json_mode: 'off' (default) | 'bounded' | 'full'.
        off     — main JSON walker disabled; structured override or TIGRFAM
                  requests can still open JSON through the separate record path.
        bounded — stream JSON with ijson; cap records and size; flat memory.
                  Falls back to 'off' if ijson is unavailable.
        full    — legacy full flatten; refuses files >20 MB (would hang).

    The TXT clusterblast/knownclusterblast files carry KCB cumulative scores,
    protein-hit counts, and MIBiG accessions. JSON adds RiQ region_to_region
    links (optional). For large genomes (e.g. the 159 MB Actinomadura rubrisoli
    JSON), json_mode='off' is correct — TXT files already provide KCB data and
    the JSON flatten is what hangs.
    """
    requested_mode = json_mode
    if json_mode == "bounded" and not _HAVE_IJSON:
        json_mode = "off"

    evidence = {
        "status": "NO_KCB_SOURCE_FOUND",
        "json_mode": json_mode,
        "json_mode_requested": requested_mode,
        "record_extras_requested": requested_mode != "off" or include_structured,
        "tigrfam_requested": want_tigrfam,
        "by_region": {},
        "loose_hits": [],
        "json_files": [],
        "txt_files": [],
    }
    if requested_mode == "bounded" and not _HAVE_IJSON:
        evidence.setdefault("json_skipped", []).append(
            "bounded mode requested but ijson is not installed; "
            "fell back to off. Install ijson for streaming JSON evidence.")

    with zipfile.ZipFile(zip_path) as zf:
        names = regular_file_names(zf)
        # v9.7.409 (DEEP_AUDIT2_antismash_parse, fix seed 2): remember whether the archive actually
        # carries region GBKs, so the schema sentinel below can distinguish "a genome that truly has
        # no BGCs" (no region GBKs -> no warning) from "region GBKs exist but every JSON extractor
        # came back empty" (a probable unrecognised/renamed schema -> loud warning).
        _has_region_gbk = any(re.search(r"\.region0*\d+\.[^.]+$", n, flags=re.I) for n in names)

        # 1. TXT clusterblast — always first; primary KCB source.
        _parse_txt_evidence(zf, names, evidence)

        # 2. JSON — only if explicitly requested and not degraded to off.
        if json_mode != "off":
            from .parsers import is_macos_cruft
            jsons = [n for n in names if n.lower().endswith(".json") and not is_macos_cruft(n)]
            for name in jsons:
                evidence["json_files"].append(name)
                size = zf.getinfo(name).file_size
                if json_mode == "bounded":
                    # When a streaming parser is available (system or vendored ijson), bounded mode
                    # reads at flat memory, so the small byte cap is self-defeating — real
                    # actinomycete antiSMASH JSONs are 55–90 MB. Raise the cap when streaming is on.
                    _cap = BOUNDED_MAX_JSON_BYTES_STREAMING if _HAVE_IJSON else BOUNDED_MAX_JSON_BYTES
                    if size > _cap:
                        evidence.setdefault("json_skipped", []).append(
                            f"{name}: {size:,} bytes exceeds bounded cap "
                            f"({_cap:,})")
                        continue
                    _parse_json_bounded(zf, name, evidence)
                elif json_mode == "full":
                    _parse_json_full(zf, name, evidence)

    # Single pass over the JSON records. tigrfam diagnostics are extracted only when this caller
    # consumes them (want_tigrfam — the cli status path that feeds the gbk/Pfam merge); the five
    # json-evidence record extractors run only when json evidence was requested. This folds what used
    # to be a separate tigrfam parse (cli) into this same pass, without adding a wasted tigrfam pass
    # to the BGC-evidence-application caller (which does not consume tigrfam).
    _rec_ev = _extract_record_evidence(zip_path,
                                       include_extras=(requested_mode != "off" or include_structured),
                                       want_tigrfam=want_tigrfam)
    if want_tigrfam:
        evidence["tigrfam_hits"] = _rec_ev["tigrfam_hits"]
    if requested_mode != "off" or include_structured:
        if _rec_ev["nrps_pks_consensus"]:
            evidence["nrps_pks_consensus"] = _rec_ev["nrps_pks_consensus"]
        if _rec_ev["active_site_pairings"]:
            evidence["active_site_pairings"] = _rec_ev["active_site_pairings"]
        if _rec_ev["product_class_predictions"]:
            evidence["product_class_predictions"] = _rec_ev["product_class_predictions"]
        if _rec_ev["ripp_cores"]:
            evidence["ripp_cores"] = _rec_ev["ripp_cores"]
        # Preserve a valid empty list when RRE-Finder ran but found no hits.
        # This keeps "not detected" distinct from a parser omission.
        evidence["rrefinder_hits"] = _rec_ev["rrefinder_hits"]

    if evidence["by_region"] or evidence["loose_hits"]:
        evidence["status"] = "SOURCE_DERIVED_BEST_EFFORT"

    # v9.7.409 (DEEP_AUDIT2_antismash_parse, fix seed 2): schema sentinel. When JSON evidence was
    # requested and JSON files were present AND at least one was actually parsed (not all skipped for
    # size), yet EVERY record extractor came back empty on an archive that DOES carry region GBKs,
    # the most likely cause is an unrecognised/renamed antiSMASH schema (a future/older major), not a
    # genome that genuinely lacks NRPS substrate / TIGRFAM / module evidence. Surface a loud, typed
    # ANTISMASH_SCHEMA_UNRECOGNIZED warning so "unparsed" is distinguishable from "absent". WARN
    # only, never a refusal, and gated on region GBKs so a true no-BGC genome does not trip it.
    _json_present = bool(evidence.get("json_files"))
    _json_all_skipped = _json_present and (
        len(evidence.get("json_skipped", []) or []) >= len(evidence["json_files"]))
    _any_record_evidence = bool(
        evidence["by_region"]
        or evidence.get("tigrfam_hits")
        or evidence.get("nrps_pks_consensus")
        or evidence.get("active_site_pairings")
        or evidence.get("product_class_predictions")
        or evidence.get("ripp_cores")
        or evidence.get("rrefinder_hits"))
    if (json_mode != "off" and _json_present and not _json_all_skipped
            and _has_region_gbk and not _any_record_evidence):
        _warn = (f"ANTISMASH_SCHEMA_UNRECOGNIZED: parsed {len(evidence['json_files'])} antiSMASH "
                 f"JSON record file(s) on an archive with region GBKs, but every structured "
                 f"extractor returned empty. This is 'unparsed', not necessarily 'absent' — the "
                 f"antiSMASH version may use a schema this parser does not recognise. Verify "
                 f"NRPS substrate / TIGRFAM / module evidence by hand.")
        evidence.setdefault("schema_warnings", []).append(_warn)
        print(_warn, file=sys.stderr)

    return evidence


def _kcb_recycling_audit(bgcs, evidence: dict[str, Any]) -> None:
    """Flag suspicious KCB reuse patterns caused by parser/keying mistakes.

    Reuse can be legitimate for duplicated/split regions, but a small number of
    identical KCB bundles assigned to most BGCs is structurally suspicious and
    should block manuscript/comparative use until inspected.
    """
    from collections import Counter
    pairs = Counter((b.kcb_cumulative, b.kcb_protein_hits) for b in bgcs if b.kcb_cumulative is not None or b.kcb_protein_hits is not None)
    repeated = {str(k): v for k, v in pairs.items() if v >= 5}
    distinct = len(pairs)
    total = sum(pairs.values())
    # Guard against regexes accidentally parsing contig accession tails such as
    # CP073042.1 -> 73042.1 as if they were cumulative KCB scores.
    accession_tail_hits = []
    for b in bgcs:
        score = getattr(b, "kcb_cumulative", None)
        contig = str(getattr(b, "contig", "") or "")
        if score is None or not contig:
            continue
        m = re.search(r"[A-Za-z]+0*([0-9]+(?:\.[0-9]+)?)$", contig)
        if m:
            try:
                if abs(float(m.group(1)) - float(score)) < 1e-6:
                    accession_tail_hits.append(b.bgc_id)
            except Exception:
                pass

    evidence["kcb_assignment_audit"] = {
        "assigned_bgcs": total,
        "distinct_score_protein_pairs": distinct,
        "repeated_pairs_ge5": repeated,
        "accession_tail_score_bgcs": accession_tail_hits,
        "status": "PASS"
    }
    if total >= 20 and (distinct <= max(3, total // 5)):
        evidence["kcb_assignment_audit"]["status"] = "FAIL_SUSPICIOUS_RECYCLING"
        evidence.setdefault("warnings", []).append(
            "Suspicious KCB recycling detected: too few distinct score/protein-hit pairs for the number of assigned BGCs. "
            "Check region keying before using KCB-derived novelty or comparisons."
        )
    if accession_tail_hits:
        evidence["kcb_assignment_audit"]["status"] = "FAIL_ACCESSION_TAIL_MISPARSE"
        evidence.setdefault("warnings", []).append(
            "Suspicious KCB score equals the numeric tail of the contig accession for one or more BGCs. "
            "Do not use KCB scores until the parser is fixed."
        )


def apply_evidence_to_bgcs(bgcs, evidence: dict[str, Any]) -> None:
    by_region = evidence.get("by_region", {})
    for bgc in bgcs:
        region_key = _region_key_for_bgc(bgc)
        recs = by_region.get(region_key, []) if region_key else []
        # Safe fallback only for single-contig assemblies where region numbers are globally unique.
        if not recs and bgc.region_number is not None:
            contigs = {getattr(b, "contig", None) for b in bgcs}
            if len(contigs) <= 1:
                recs = by_region.get(str(bgc.region_number), [])
        # Default to a qualified null; only concrete source locators upgrade it.
        bgc.closest_mibig_accession = "UNRESOLVED"
        bgc.closest_candidate_kcb_product = "UNRESOLVED"
        bgc.closest_product_provenance = "UNRESOLVED"
        bgc.source_kcb_file = "UNRESOLVED"
        bgc.source_kcb_locator = "UNRESOLVED"
        bgc.kcb_hit_rank = "UNRESOLVED"
        bgc.denominator_type = "UNRESOLVED"
        bgc.parse_confidence = "LOW"
        bgc.needs_manual_kcb_check = "yes"
        bgc.product_claim_ceiling = "unresolved; do not use product name"
        bgc.kcb_evidence_state = "UNKNOWN_KCB"
        if recs:
            mibigs, score_vals, prot_hits, candidate_lines, riq_vals = [], [], [], [], []
            first_reference = None
            # BUGFIX (2026-07-01, KCB source-precedence): _region_key_for_bgc collapses
            # knownclusterblast/, clusterblast/, and subclusterblast/ TXT files onto the
            # same region key (they share the identical <contig>_c<N>.txt filename across
            # all three antiSMASH output folders). Blindly max()-ing cumulative_score across
            # every rec in `recs` therefore lets a generic whole-genome clusterblast hit
            # (not a curated MIBiG comparator at all — e.g. a raw BLAST hit against an
            # unrelated reference genome) silently outscore and overwrite the correct
            # knownclusterblast MIBiG-comparator score. Confirmed on AS-XXX BGC058: the
            # corrupted score (73038.0) traces to clusterblast/..._c1.txt's top hit against
            # "Streptomyces violaceusniger Tu 4113, complete sequence" — not a MIBiG cluster —
            # while knownclusterblast/..._c1.txt correctly reports 37992.0 for aculeximycin
            # (BGC0000002.5). Fix: only aggregate from knownclusterblast records when any
            # are present for this region; fall back to clusterblast/subclusterblast only
            # if no knownclusterblast record exists (better than nothing, but flagged).
            kcb_recs = [r for r in recs if r.get("source_kind") == "knownclusterblast"]
            source_recs = kcb_recs if kcb_recs else recs
            bgc.kcb_evidence_state = (
                "KNOWNCLUSTERBLAST_OBSERVED" if kcb_recs
                else "CLUSTERBLAST_FALLBACK_OBSERVED"
            )
            if not kcb_recs and recs:
                bgc.parse_confidence = "LOW"
                bgc.needs_manual_kcb_check = "yes"
            for r in source_recs:
                mibigs.extend(r.get("mibig_hits") or [])
                refs = r.get("mibig_reference_hits") or []
                if refs and first_reference is None:
                    first_reference = {**refs[0], "source": r.get("source")}
                if refs and not bgc.mibig_ranked:
                    # #2: keep the full ranked MIBiG list (top-10), not just rank-1
                    bgc.mibig_ranked = [
                        {"rank": h.get("rank"), "accession": h.get("accession"), "product": h.get("product")}
                        for h in refs[:10]
                    ]
                if r.get("cumulative_score") is not None:
                    score_vals.append(r["cumulative_score"])
                if r.get("protein_hits") is not None:
                    prot_hits.append(r["protein_hits"])
                if r.get("riq_score") is not None:
                    riq_vals.append(r["riq_score"])
                candidate_lines.extend(r.get("candidate_lines") or [])
            # v9.7.166: clusterblast_ranked (organism hits) lives in the PLAIN clusterblast recs,
            # which are excluded from source_recs when knownclusterblast (MIBiG) recs exist. Scan
            # ALL recs for the organism ranking, independent of the MIBiG-vs-clusterblast split.
            for r in recs:
                if r.get("clusterblast_ranked") and not bgc.clusterblast_ranked:
                    bgc.clusterblast_ranked = r["clusterblast_ranked"]
            if mibigs:
                bgc.mibig_hits = sorted(set(mibigs))
            if score_vals:
                bgc.kcb_cumulative = max(score_vals)
            if prot_hits:
                bgc.kcb_protein_hits = max(prot_hits)
            if candidate_lines:
                # raw rank-1 line. For a cluster excised from a sequenced genome that is in the KCB database,
                # this is the genome SELF-HIT (whole-genome match), which masks the MIBiG compound. Preserve it
                # here; kcb_top is overridden with the MIBiG identity line below when a reference line exists.
                bgc.clusterblast_top = candidate_lines[0][:120]
                bgc.kcb_top = candidate_lines[0][:120]
            if first_reference:
                source = first_reference.get("source") or "UNRESOLVED"
                rank = first_reference.get("rank")
                accession = first_reference.get("accession") or "UNRESOLVED"
                product = first_reference.get("product") or "UNRESOLVED"
                bgc.closest_mibig_accession = accession
                bgc.closest_candidate_kcb_product = product
                bgc.closest_product_provenance = "MIBIG_REFERENCE_LINE"
                # surface the MIBiG identity (compound) in kcb_top rather than the genome self-hit; the raw
                # rank-1 line remains available in clusterblast_top so gates/audits that need it can read both.
                bgc.kcb_top = f"{accession} | {product} | knownclusterblast #{rank}"
                bgc.source_kcb_file = source
                bgc.source_kcb_locator = (
                    f"BGC_ID={bgc.bgc_id};knownclusterblast_file={source};"
                    f"knownclusterblast_hit={rank};accession={accession}"
                )
                bgc.kcb_hit_rank = str(rank)
                bgc.denominator_type = "knownclusterblast significant hits"
                bgc.parse_confidence = "HIGH"
                bgc.needs_manual_kcb_check = "no"
                # CUT A: coverage + class-mismatch gate. A MIBiG reference line alone no longer grants
                # a product-level ceiling — require a substantial protein-hit count AND class concordance.
                _comparator = "; ".join(filter(None, [getattr(bgc, "clusterblast_top", "") or "", str(product)]))
                _prodcls = "; ".join(getattr(bgc, "products", []) or [])
                _substantial = kcb_coverage_substantial(getattr(bgc, "kcb_protein_hits", None))
                _mismatch = kcb_class_mismatch(_comparator, _prodcls)
                if _substantial and not _mismatch:
                    bgc.product_claim_ceiling = "candidate product-level similarity, manual check required"
                else:
                    bgc.product_claim_ceiling = "source-derived similarity anchor only"
                    bgc.claim_ceiling_gate = ("kcb_coverage<5;" if not _substantial else "") + \
                                             ("class_mismatch;" if _mismatch else "")
                _apply_fragment_ceiling(bgc)  # P4: large backbone on sub-45kb fragment -> class-capacity
            elif getattr(bgc, "kcb_top", None):
                bgc.closest_product_provenance = "KCB_TOP_FIELD"
                bgc.source_kcb_file = "self:KCB_top"
                bgc.source_kcb_locator = "self:KCB_top"
                bgc.kcb_hit_rank = "UNRESOLVED"
                bgc.denominator_type = "clusterblast best subject cluster"
                bgc.parse_confidence = "MEDIUM"
                bgc.needs_manual_kcb_check = "yes"
                bgc.product_claim_ceiling = "source-derived similarity anchor only"
                _apply_fragment_ceiling(bgc)  # P4: also fires on source-derived named products
            if riq_vals:
                bgc.riq_score = float(riq_vals[0])
                bgc.riq_label = riq_label(float(riq_vals[0]))

    _kcb_recycling_audit(bgcs, evidence)

    loose_riq = [h.get("riq_score") for h in evidence.get("loose_hits", [])
                 if isinstance(h, dict) and h.get("riq_score") is not None]
    if loose_riq and evidence.get("riq_mapping_status") != "MAPPED":
        evidence["riq_unmapped_count"] = sum(
            h.get("riq_observation_count", 1) for h in evidence.get("loose_hits", [])
            if isinstance(h, dict) and h.get("riq_score") is not None)
        evidence["riq_mapping_status"] = "UNMAPPED_LOOSE_VALUES_NOT_ASSIGNED_TO_BGC"


def riq_label(score: float) -> str:
    if score >= 0.85:
        return "Likely known"
    if score >= 0.50:
        return "Possibly novel / structural variant"
    return "Potentially novel"


# Tetronate ring-closure marker sets (v9.7.183 — the AS-XXX BGC010 completeness gate).
_TET_STARTER = frozenset({"FkbH", "PF04113"})
_TET_ACP = frozenset({"PP-binding", "PF00550", "ACP", "PCP"})
_TET_KSIII_CLOSURE = frozenset({"fabH", "ACP_syn_III", "ACP_syn_III_C", "Chal_sti_synt_N",
                                "Chal_sti_synt_C", "ksIII", "PF08541", "PF08545"})
_TET_SPIRO_CLOSURE = frozenset({"Diels_aldr", "PF13570"})


def tetronate_cassette_completeness(cluster_domains, partner_domains=None,
                                    edge_truncated: bool = False,
                                    partner_binding_state: str = "UNBOUND") -> dict:
    """Grade a T43-TET (tetronate) CCTT trigger by cassette completeness instead of firing it on
    FkbH alone. FkbH is necessary-not-sufficient: a tetronate ring needs a FabH-family KSIII
    closure enzyme co-located with the FkbH+ACP pair (or a Diels-Alderase for the spiro sub-class).

    Mirrors the §8 KCB coverage tier and the §4 BLASTp reconcile: the trigger carries a grade, so a
    starter-only FkbH is never read as a confirmed tetronate. Surfaced by AS-XXX BGC010, where FkbH
    was present but no KSIII existed anywhere reachable → STARTER_ONLY, tipping the PTM-vs-TET fork
    to tetramate.

    cluster_domains  : iterable of domain names in the firing cluster
    partner_domains  : iterable of domain names in RGGMCI partners / reachable edges (optional)
    edge_truncated   : True if a required contig runs into a truncated/low-complexity terminus
    Returns {grade, has_starter, has_acp, has_ksiii, has_spiro, reason}.
    """
    here = set(cluster_domains or [])
    reachable = here | set(partner_domains or [])
    has_starter = bool(here & _TET_STARTER)
    has_acp = bool(here & _TET_ACP)
    has_ksiii = bool(reachable & _TET_KSIII_CLOSURE)
    has_spiro = bool(reachable & _TET_SPIRO_CLOSURE)
    closure_in_cluster = bool(here & (_TET_KSIII_CLOSURE | _TET_SPIRO_CLOSURE))
    ambiguous_partner = bool(
        edge_truncated and (has_ksiii or has_spiro) and not closure_in_cluster
        and partner_binding_state != "EXACT_RGGMCI_PARTNER"
    )

    if not has_starter:
        grade, reason = "TET_NO_STARTER", "no FkbH starter — T43-TET should not fire"
    elif ambiguous_partner:
        grade, reason = "TET_CASSETTE_INDETERMINATE", (
            "AMBIGUOUS_PARTNER: edge-adjacent FabH/KSIII or Diels-Alderase evidence "
            "is not bound to one exact RG-GMCI partner; long-read or exact partner "
            "binding is required before ring-closure support"
        )
    elif has_spiro:
        grade, reason = "TET_CASSETTE_SPIRO", ("FkbH + Diels-Alderase present — spirotetronate "
                                               "ring closure supported")
    elif has_ksiii:
        # AUDIT_371: reason text must reflect what was actually verified. has_ksiii alone
        # used to be worded as if ACP co-location were also confirmed ("FkbH + ACP + FabH/KSIII"),
        # even when has_acp is False -- overstating evidence in a claim-safety-relevant grade that
        # flows into cctt["tetronate_cassette_grades"] and on into scan-state/judgment materials.
        # Grade is unchanged (still TET_CASSETTE_COMPLETE on KSIII alone, per the existing
        # necessary-not-sufficient FkbH design) -- only the reason string now names what was and
        # was not confirmed. Whether ACP should itself gate the COMPLETE grade is a separate,
        # scientific-threshold question left to domain review, not decided here.
        if has_acp:
            grade, reason = "TET_CASSETTE_COMPLETE", ("FkbH + ACP + FabH/KSIII co-located — tetronate "
                                                      "ring closure supported")
        else:
            grade, reason = "TET_CASSETTE_COMPLETE", ("FkbH + FabH/KSIII co-located (ACP not confirmed "
                                                      "in the firing cluster) — tetronate ring closure "
                                                      "supported")
    elif edge_truncated:
        grade, reason = "TET_CASSETTE_INDETERMINATE", ("FkbH present; a required contig is "
                                                       "edge-truncated so ring-closure absence "
                                                       "cannot be proven — long-read only")
    else:
        grade, reason = "TET_CASSETTE_STARTER_ONLY", ("FkbH present but no ring-closure enzyme "
                                                      "(FabH/KSIII or Diels-Alderase) anywhere "
                                                      "reachable — starter-unit signal only; FkbH "
                                                      "also feeds non-tetronate glyceryl/glycolate "
                                                      "starter routes. Downgrade the T43-TET claim.")
    return {"grade": grade, "has_starter": has_starter, "has_acp": has_acp,
            "has_ksiii": has_ksiii, "has_spiro": has_spiro,
            "partner_binding_state": partner_binding_state,
            "ambiguous_partner": ambiguous_partner, "reason": reason}
