#!/usr/bin/env python3
"""Seed mamey/data/reference_bgc_library.json from the validated reference set.

The library is a versioned bundle artifact: compound -> {class, genus, expected size, marker_set}. It is
SEEDED here from what is known/measured now, and the LIT-pending fields (mibig_accession, expected_size_kb,
expected_marker_set) are filled by the ChatGPT LIT punch card. `concordance_check` (mamey/concordance.py)
consults it to produce concordance EVIDENCE for Sapote.

Provenance discipline (per project standard — observed / computed / seed / LIT):
  * found_size_kb, found_markers   = OBSERVED (measured by the engine from the antiSMASH output)
  * class, genus, expected_bioactivity = SEED (curated below; well-characterised compounds; LIT verifies)
  * expected_marker_set            = SEED where class-definitional (e.g. enediyne->T43-ENE), else PENDING_LIT
  * mibig_accession, expected_size_kb = PENDING_LIT (UNRESOLVED until ChatGPT sheet returns)
Honest UNRESOLVED is used wherever genus/class is not confidently known (no fabrication).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, json, os, sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


LIB_VERSION = "0.1.0"  # library artifact versions independently; bumps as references/LIT land
OUT = os.path.join(os.path.dirname(__file__), "..", "mamey", "data", "reference_bgc_library.json")
# Bundle-relative default; overridable by env or CLI so the seed process is portable, not tied to
# one machine's /mnt path. Order: CLI arg > MAMEY_SEED_STRUCT env > bundled resource.
_DEFAULT_STRUCT = os.path.join(os.path.dirname(__file__), "..", "resources",
                               "reference_seed_inputs", "reference_bgc_structural.csv")
# One-release migration fallback for bundles or operator workspaces created before
# v9.7.390. It is input-only: new documentation and validator output use the generic
# reference-BGC filename. Remove after the published deprecation window.
_LEGACY_STRUCT = os.path.join(os.path.dirname(__file__), "..", "resources",
                              "reference_seed_inputs", "wac_validation_structural.csv")


def _resolve_struct(argv):
    pos = [a for a in argv if not a.startswith("-")]
    explicit = pos[0] if pos else os.environ.get("MAMEY_SEED_STRUCT")
    cand = explicit or _DEFAULT_STRUCT
    if not explicit and not os.path.exists(cand) and os.path.exists(_LEGACY_STRUCT):
        emit(
            "DEPRECATION: using the pre-v9.7.390 reference-panel seed filename; "
            "rename it to resources/reference_seed_inputs/reference_bgc_structural.csv",
            file=sys.stderr,
        )
        cand = _LEGACY_STRUCT
    if not os.path.exists(cand):
        sys.exit(f"seed input not found: {cand}\n"
                 f"  provide it via:  python tools/seed_reference_library.py <STRUCT.csv>\n"
                 f"  or env:          MAMEY_SEED_STRUCT=/path/to/STRUCT.csv\n"
                 f"  or place it at:  resources/reference_seed_inputs/reference_bgc_structural.csv")
    return cand

# Curated annotation (SEED). genus/class only where confidently established; UNRESOLVED otherwise.
# seed_markers = engine T43-* prefixes that are class-DEFINITIONAL (safe to expect); [] = PENDING_LIT.
ANN = {
    # compound:        (class,                       genus,           bioactivity,            seed_markers)
    "HSAF":            ("PTM/tetramate-polyketide",  "Lysobacter",    "antifungal",           ["T43-PTM"]),
    "nystatin":        ("polyene",                   "Streptomyces",  "antifungal",           []),
    "candicidin":      ("polyene",                   "Streptomyces",  "antifungal",           []),
    "C-1027":          ("enediyne",                  "Streptomyces",  "cytotoxic/antitumor",  ["T43-ENE"]),
    "streptothricin":  ("streptothricin",            "Streptomyces",  "antibacterial",        []),
    "notonesomycin A": ("oligosaccharide-macrolide", "Streptomyces",  "antibacterial",        []),
    "nostophycin":     ("NRPS-PKS (cyanobacterial)", "Nostoc",        "cytotoxic",            []),
    "pekiskomycin":    ("glycopeptide",              "Streptomyces",  "antibacterial",        []),
    "ibomycin":        ("macrolide-polyketide",      "Streptomyces",  "UNRESOLVED",           []),
    "A54145":          ("lipopeptide",               "Streptomyces",  "antibacterial",        []),
    "A-94964":         ("polyketide (detail UNRESOLVED)", "UNRESOLVED","antibacterial",       []),
    "lipopeptide 8D1": ("lipopeptide",               "UNRESOLVED",    "UNRESOLVED",           []),
    "pacidamycin":     ("nucleoside-peptide (antibacterial)", "Streptomyces", "antibacterial", []),
    "corallopyronin":  ("alpha-pyrone (RNAP inhibitor)", "Corallococcus", "antibacterial",    []),
    "monensin":        ("polyether ionophore",       "Streptomyces",  "ionophore",            []),
    "A23187":          ("ionophore (benzoxazole)",   "Streptomyces",  "ionophore",            []),
    "nocardicin":      ("beta-lactam (monocyclic)",  "Nocardia",      "antibacterial",        ["T43-BLA"]),
    # --- reference panel additions (2026-06-13): class/genus OBSERVED from MIBiG GBK organism+product; ---
    # --- seed_markers asserted only where class-definitional AND confirmed to fire in reference_panel_ledger ---
    "lobophorin":      ("spirotetronate (glycosylated T1PKS)", "Streptomyces", "antibacterial",     []),
    "aurachin C":      ("prenylated quinoline alkaloid", "Streptomyces", "UNRESOLVED",               []),
    "angustmycin A":   ("nucleoside (adenosine analog; non-peptidyl)", "Streptomyces", "antibacterial", []),
    "deoxyhangtaimycin": ("UNRESOLVED (antiSMASH product=unknown)", "Streptomyces", "UNRESOLVED",     []),
}


def short(m):  # "T43-ENE_enediyne" -> "T43-ENE"; pass through bare prefixes
    m = m.strip()
    return m.split("_")[0] if m.startswith("T43-") else m


_RICH = ("class_lit", "core_genes", "lit_diagnostic_genes", "source_doi", "hard_scan_verdict",
         "gene_symbol_concordance")


def _rich_count(entries):
    return sum(1 for e in entries if any(e.get(k) not in (None, "", "PENDING_LIT", [])
                                         for k in _RICH))


def main():
    argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        emit("usage: python tools/seed_reference_library.py [STRUCT.csv] [--force] [--dry-run]\n"
              "  Rebuild mamey/data/reference_bgc_library.json from a structural CSV.\n"
              "  STRUCT.csv: seed input (default: env MAMEY_SEED_STRUCT or resources/reference_seed_inputs/).\n"
              "  --dry-run : report what would change; do not write.\n"
              "  --force   : overwrite even if it would shrink the library or drop curated fields.\n"
              "  Safety: this tool emits a SIMPLE schema. The shipped JSON is hand-curated and richer;\n"
              "  a plain run will REFUSE to overwrite it (the JSON is the source of truth). A timestamped\n"
              "  .bak is always written before any overwrite.")
        return
    force = "--force" in argv
    dry = "--dry-run" in argv
    struct = _resolve_struct(argv)
    rows = list(csv.DictReader(open(struct)))
    entries = []
    for r in rows:
        comp = r["compound"]
        cls, genus, bioact, seed_markers = ANN.get(comp, ("UNRESOLVED", "UNRESOLVED", "UNRESOLVED", []))
        found_markers = [] if r["engine_markers_fired"] in ("(none)", "") else \
            [short(x) for x in r["engine_markers_fired"].split(",")]
        entries.append({
            "compound": comp,
            "aliases": sorted({comp.lower(), r["kcb_anchor"].strip().lower()}),
            "class": cls,
            "genus": genus,
            "accession": r["accession"],
            "mibig_accession": "PENDING_LIT",
            "expected_size_kb": None,                 # PENDING_LIT
            "found_size_kb": float(r["found_size_kb"]),
            "found_markers": found_markers,           # OBSERVED
            "expected_marker_set": seed_markers,      # SEED where definitional, else PENDING_LIT ([] )
            "marker_set_source": "seed" if seed_markers else "PENDING_LIT",
            "expected_bioactivity": bioact,
            "source": "validation_set_v9.7.20",
        })
    lib = {
        "schema_version": "1.0",
        "library_version": LIB_VERSION,
        "generated": "2026-06-13",
        "marker_vocabulary": "mamey CCTT T43-* trigger prefixes (see mamey/mamey_markers.py)",
        "provenance_legend": {"found_*": "observed (engine)", "class/genus/bioactivity": "seed (curated)",
                              "expected_marker_set": "seed if class-definitional else PENDING_LIT",
                              "mibig_accession/expected_size_kb": "PENDING_LIT (ChatGPT punch card)"},
        "note": ("Seeded from the v9.7.20 validation set. PENDING_LIT fields are filled by the "
                 "LIT_Reference_Concordance sheet. Genus-targeted toward Nocardia/Actinomadura as references are added."),
        "entries": entries,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # No-silent-downgrade guard: this tool emits a simpler schema than the hand-curated JSON.
    if os.path.exists(OUT):
        try:
            old = _read_json(OUT).get("entries", [])
        except Exception:
            old = []
        old_n, new_n = len(old), len(entries)
        old_rich = _rich_count(old)
        new_rich = _rich_count(entries)  # this tool emits no rich fields -> 0
        shrink = new_n < old_n
        drop_rich = new_rich < old_rich
        if (shrink or drop_rich) and not force:
            sys.exit(
                f"REFUSING to overwrite {OUT}.\n"
                f"  entries: {old_n} -> {new_n}{'  (SHRINK)' if shrink else ''}\n"
                f"  curated (rich) entries: {old_rich} -> {new_rich}{'  (WOULD DROP CURATION)' if drop_rich else ''}\n"
                f"  The shipped JSON is hand-maintained and richer than this seed tool emits.\n"
                f"  Re-seeding would discard curated literature fields ({', '.join(_RICH)}).\n"
                f"  If you really mean to, re-run with --force (a .bak is written first).")
        if dry:
            emit(f"[dry-run] would write {new_n} entries (current {old_n}; curated {old_rich} -> {new_rich}). No changes made.")
            return
        bak = f"{OUT}.bak.{__import__('time').strftime('%Y%m%d-%H%M%S')}"
        __import__('shutil').copy(OUT, bak)
        emit(f"backup written: {bak}")
    elif dry:
        emit(f"[dry-run] would create {OUT} with {len(entries)} entries. No changes made.")
        return

    _tmp = OUT + ".tmp"
    with open(_tmp, "w") as _f:
        json.dump(lib, _f, indent=2)
    os.replace(_tmp, OUT)
    n_seed = sum(1 for e in entries if e["marker_set_source"] == "seed")
    n_genus = sum(1 for e in entries if e["genus"] != "UNRESOLVED")
    emit(f"wrote {OUT}: {len(entries)} entries | {n_seed} with seed markers | {n_genus} genus-resolved | "
          f"{len(entries)-n_genus} genus UNRESOLVED")


if __name__ == "__main__":
    main()
