#!/usr/bin/env python3
"""build_family_map.py  (patch P03 — lexicon growth)

Grow the diagnostic-rescue KCB family map from the bundled MIBiG reference index (offline). The concordance
gate needs families at the COMPOUND-CLASS level (a true split tiles two halves of one compound), so we
derive families from MIBiG `compounds` names via a curated stem lexicon — NOT from `region`/`subclasses`,
which are far too coarse (804 'Type I', 571 'Unknown') and would manufacture false concordance.

Conservative by design: an accession matches a family only via a specific compound-name stem (or a small
set of unambiguous specific subclasses). Unmatched accessions are LEFT OUT → resolve to `unknown` → the
pair stays MODERATE. Recall grows; precision is protected (the 11 adjudicated discordant pairs must remain
non-concordant — enforced by --validate).

  python tools/build_family_map.py --out mamey/data/families/kcb_compound_family.json [--validate adj.csv]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import csv
import json
import os
import re
import sys as _sys, os as _os


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_dump_json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIBIG = [os.path.join(ROOT, "mamey/data/mibig/mibig_reference_index.bacterial.json"),
         os.path.join(ROOT, "mamey/data/mibig/mibig_reference_index.fungal.json")]

# Curated overrides — authoritative, from intake adjudication. Never overwritten by stem matching.
CURATED = {
    "BGC0000809": "indolocarbazole", "BGC0002460": "indolocarbazole",
    "BGC0002381": "tambjamine_bipyrrole", "BGC0001500": "angucyclinone",
    "BGC0001301": "macrolide_polyketide", "BGC0001215": "macrodiolide_oxazole",
    "BGC0000469": "thioamide_ripp", "BGC0002732": "benanomicin_aromatic",
    "BGC0001178": "glycopeptide", "BGC0000257": "prodiginine",
    "BGC0001448": "lipopeptide_cda", "BGC0001550": "lasso_peptide", "BGC0000140": "tetronate",
}

# Compound-class stem lexicon. family -> substrings to match against compound names (lowercased).
# Ordered most-specific first; first hit wins. Curated for actinomycete natural-product classes.
FAMILY_STEMS = [
    ("indolocarbazole", ["indolocarbazole", "staurosporine", "rebeccamycin", "at2433", "k-252",
                          "k252", "loonamycin", "holyrine", "arcyriaflavin"]),
    ("siderophore",     ["bactin", "chelin", "ferrioxamine", "desferri", "coelichelin", "enterobactin",
                          "mycobactin", "yersiniabactin", "pyochelin", "staphyloferrin", "vibrioferrin",
                          "amychelin", "griseobactin", "heterobactin", "foroxymithine", "petrobactin",
                          "achromobactin", "fimsbactin", "gobichelin", "ochrobactin", "siderophore"]),
    ("glycopeptide",    ["vancomycin", "teicoplanin", "balhimycin", "a47934", "chloroeremomycin",
                          "ristocetin", "complestatin", "a40926", "kistamicin", "pekiskomycin",
                          "dalbavancin", "ristomycin"]),
    ("aminoglycoside",  ["kanamycin", "neomycin", "streptomycin", "gentamicin", "apramycin", "tobramycin",
                          "butirosin", "ribostamycin", "paromomycin", "spectinomycin", "hygromycin",
                          "kasugamycin", "fortimicin"]),
    ("ansamycin",       ["rifamycin", "ansamitocin", "geldanamycin", "naphthomycin", "herbimycin",
                          "maytansine", "ansamycin", "rubradirin", "awamycin"]),
    ("enediyne",        ["calicheamicin", "dynemicin", "esperamicin", "c-1027", "neocarzinostatin",
                          "maduropeptin", "kedarcidin", "enediyne", "tiancimycin", "uncialamycin",
                          "yangpumicin", "sporolide"]),
    ("polyene_macrolide", ["amphotericin", "nystatin", "candicidin", "pimaricin", "natamycin", "filipin",
                           "rimocidin", "pentamycin"]),
    ("macrolide",       ["erythromycin", "pikromycin", "tylosin", "rosamicin", "oleandomycin", "methymycin",
                          "spiramycin", "azithromycin", "mycinamicin", "chalcomycin", "midecamycin",
                          "concanamycin", "bafilomycin", "elaiophylin", "macrolide"]),
    ("tetracycline",    ["tetracycline", "oxytetracycline", "chlortetracycline", "doxycycline",
                          "chelocardin", "dactylocycline", "sf2575"]),
    ("angucycline",     ["jadomycin", "landomycin", "urdamycin", "gilvocarcin", "kinamycin", "simocyclinone",
                          "angucyclin", "saquayamycin", "fredericamycin", "lugdunomycin", "moromycin"]),
    ("aromatic_polyketide_t2", ["actinorhodin", "tetracenomycin", "mithramycin", "chromomycin",
                                "granaticin", "medermycin", "resistomycin", "spore pigment", "whie"]),
    ("anthracycline",   ["doxorubicin", "daunorubicin", "aclacinomycin", "nogalamycin", "steffimycin",
                          "cosmomycin", "anthracycline"]),
    ("aminocoumarin",   ["novobiocin", "clorobiocin", "coumermycin", "aminocoumarin", "simocyclinone"]),
    ("beta_lactam",     ["clavulanic", "cephamycin", "penicillin", "cephalosporin", "nocardicin",
                          "carbapenem", "thienamycin", "beta-lactam", "lactivicin"]),
    ("phenazine",       ["phenazine", "pyocyanin", "endophenazine", "lomofungin", "esmeraldin"]),
    ("prodiginine",     ["prodigiosin", "prodiginine", "undecylprodigiosin", "streptorubin", "metacycloprodigiosin"]),
    ("lasso_peptide",   ["lasso", "lariatin", "microcin j25", "capistruin", "sviceucin", "citrulassin",
                          "ulleungdin", "albusnodin", "sphaericin", "klebsidin"]),
    ("lanthipeptide",   ["lanthipeptide", "nisin", "lacticin", "microbisporicin", "planosporicin",
                          "actagardine", "mersacidin", "cinnamycin", "duramycin", "lanthidin", "venezuelin"]),
    ("thiopeptide",     ["thiostrepton", "nosiheptide", "thiopeptide", "ge2270", "ge37468", "micrococcin",
                          "berninamycin", "siomycin", "geninthiocin", "thiomuracin", "cyclothiazomycin"]),
    ("thioamide_ripp",  ["thioviridamide", "thioamitide", "thioalbamide", "prethioviridamide"]),
    ("nucleoside",      ["polyoxin", "nikkomycin", "blasticidin", "puromycin", "tunicamycin", "caprazamycin",
                          "a-90289", "capuramycin", "muraymycin", "liposidomycin", "sphaerimicin", "nucleoside"]),
    ("pyrrole_bipyrrole", ["tambjamine", "marinopyrrole", "bipyrrole", "pyoluteorin", "chlorizidine"]),
    ("lipopeptide",     ["daptomycin", "calcium-dependent antibiotic", "friulimicin", "amphomycin",
                          "a54145", "taromycin", "laspartomycin", "stenothricin", "cadasides"]),
    ("butyrolactone",   ["butyrolactone", "a-factor", "avenolide", "methylenomycin furan"]),
    ("isocyanide",      ["isocyanide", "isonitrile"]),
    ("ectoine",         ["ectoine"]),
    ("melanin",         ["melanin"]),
    ("carotenoid",      ["carotenoid", "isorenieratene", "lycopene", "zeaxanthin", "spheroidene"]),
    ("indole_alkaloid", ["indolmycin", "borregomycin", "spiroindimicin", "lynamicin"]),
    ("tetronate",       ["tetronate", "tetronasin", "chlorothricin", "kijanimicin", "tetronomycin",
                          "agglomerin", "abyssomicin", "quartromicin"]),
    ("aurodox_elfamycin", ["aurodox", "kirromycin", "efrotomycin", "elfamycin", "factumycin"]),
]
# A few specific subclass values that ARE compound-class level (safe fallback). Excludes the coarse
# 'Type I'/'Unknown'/'RiPP'/'other'/'(none)' values.
SUBCLASS_FAMILY = {
    "aminocoumarin": "aminocoumarin", "phenazine": "phenazine", "nucleoside": "nucleoside",
    "non-nrp beta-lactam": "beta_lactam", "Diterpene": "diterpene", "Sesquiterpene": "sesquiterpene",
    "Monoterpene": "monoterpene", "Triterpene": "triterpene", "Carotenoid": "carotenoid",
    "Type II aromatic": "aromatic_polyketide_t2",
}
# Curated legitimate cross-family pairings (a split can tile two different-but-compatible families).
COMPATIBLE_PAIRS = [
    ["indolocarbazole", "indolocarbazole"],
    ["aminocoumarin", "aromatic_polyketide_t2"],  # simocyclinone: angucycline core + aminocoumarin arm
]


def _family_for(entry):
    comps = " ".join(entry.get("compounds") or []).lower()
    for fam, stems in FAMILY_STEMS:
        if any(s in comps for s in stems):
            return fam
    for sc in (entry.get("subclasses") or []):
        if sc in SUBCLASS_FAMILY:
            return SUBCLASS_FAMILY[sc]
    return None


def build():
    by_acc = dict(CURATED)
    src_counts = {"curated": len(CURATED), "stem": 0, "subclass": 0}
    total = 0
    for path in MIBIG:
        if not os.path.exists(path):
            continue
        for e in _read_json(path).get("entries", []):
            total += 1
            acc = e.get("accession")
            if not acc or acc in by_acc:
                continue
            fam = _family_for(e)
            if fam:
                by_acc[acc] = fam
                src_counts["subclass" if fam in SUBCLASS_FAMILY.values() and not any(
                    s in " ".join(e.get("compounds") or []).lower()
                    for _, ss in FAMILY_STEMS for s in ss) else "stem"] += 1
    return by_acc, src_counts, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "mamey/data/families/kcb_compound_family.json"))
    ap.add_argument("--validate", default=None, help="adjudicated CSV to check precision is preserved")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    by_acc, src, total = build()
    fams = sorted(set(by_acc.values()))
    out = {
        "schema_version": "kcb-family-0.2",
        "note": ("MIBiG-accession -> compound-class family. Grown from the bundled MIBiG reference index "
                 "via a curated compound-name stem lexicon (P03). Families are compound-class level so the "
                 "diagnostic-rescue concordance gate can confirm a split tiles two halves of one class. "
                 "Unmatched accessions are intentionally absent -> resolve to 'unknown' -> MODERATE."),
        "by_accession": dict(sorted(by_acc.items())),
        "compatible_pairs": COMPATIBLE_PAIRS,
    }
    emit(f"# Family map: {len(by_acc)} accessions ({src['curated']} curated + {len(by_acc)-src['curated']} "
          f"derived) across {len(fams)} families, from {total} MIBiG entries.")
    emit(f"  coverage: {100*len(by_acc)/max(total,1):.1f}% of MIBiG entries now carry a family.", f"  families: {', '.join(fams[:18])}{' …' if len(fams)>18 else ''}", sep="\n")

    if a.validate and os.path.exists(a.validate):
        import sys
        sys.path.insert(0, ROOT)
        from mamey import diagnostic_rescue as DR
        fmap = out
        bad = []
        rows = list(csv.DictReader(open(a.validate)))
        gained = 0
        for r in rows:
            cf = DR.kcb_family(r.get("core_kcb", ""), fmap)
            af = DR.kcb_family(r.get("arm_kcb", ""), fmap)
            conc = DR._concordance(cf, af, fmap)
            if r["verdict"] == "DISCORDANT_FALSE" and conc == "concordant":
                bad.append(f"{r['strain']} {r['pair']}: false-concordant ({cf}/{af})")
            if r["verdict"] == "DISCORDANT_FALSE" and conc == "discordant":
                gained += 1
            if r["verdict"] == "CONCORDANT_TRUE" and conc != "concordant":
                bad.append(f"{r['strain']} {r['pair']}: TRUE split lost concordance ({cf}/{af}={conc})")
        emit(f"\n## Validation against {len(rows)} adjudicated pairs", f"  discordant pairs now explicitly resolved (not just unknown): {gained}", sep="\n")
        if bad:
            emit("  ✗ PRECISION REGRESSION — refusing to write:")
            for b in bad:
                emit(f"    {b}")
            sys.exit(1)
        emit("  ✓ precision preserved: no DISCORDANT_FALSE became concordant; TRUE split intact.")

    if a.dry_run:
        emit("\n(dry-run — not written)")
        return
    atomic_dump_json(out, a.out, indent=2)
    emit(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
