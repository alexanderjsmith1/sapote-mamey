#!/usr/bin/env python3
"""build_dapr_rescue_sheets.py — deterministic (Mamey-layer) regeneration of the schema-v1.2
additions: the `Fragment_Rescue_Tiers` sheet (code D5) and the `Activity_Ref` column on the DAPR
boards (C1/C2). Both are pure functions of workbook data + the locked framework citation map, so
re-running reproduces them exactly. The Sapote judgment columns (Rank, AN_Score, WL_Score, Rationale)
and the *selection* of DAPR board rows are NOT touched.

Reads (from the master workbook):
  A2_Strain_Registry    -> strain, contigs, n50, assembly_tier
  A3_Run_Manifest        -> strain, raw_bgcs, corrected_bgcs (last row per strain = latest run)
  B4_Cross_Strain_Scans -> strain, EFLS_pairs, RGGMCI_HIGH, FLBR_megasynth
  D1_RGGMCI_All_Strains -> strain (sheet-presence check only -- see v9.7.371 note below)
  (v9.7.371: corrected TitleCase/A2-only reads below that never matched the real canonical-schema
  headers -- CANONICAL_V1_HEADERS in mamey/master_workbook.py -- and silently zeroed every
  strain's Fragment_Rescue_Tiers row via .get() defaults. Mirrors the identical fix already made
  in tools/export_figure_ready.py for the same A2-vs-A3 drift. See PATCH CARD for the
  reproduction. FLBR_megasynth has no canonical B4 column and remains best-effort/0 -- a separate,
  still-open schema gap, not resolved by this fix.)

Writes (in place):
  Fragment_Rescue_Tiers (D5) — rebuilt deterministically
  C1_DAPR_Antibacterial / C2_DAPR_Antifungal — Activity_Ref refreshed from the framework map

Usage: python tools/build_dapr_rescue_sheets.py <master_workbook.xlsx>
Dependency-light: openpyxl + stdlib. Mirrors docs/DAPR_CLASS_FRAMEWORK.md.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from _wbio import atomic_save

HDR = PatternFill("solid", fgColor="2C6FBB"); HF = Font(color="FFFFFF", bold=True)

# ---- LOCKED framework citation map: KCB nearest compound (substring) -> Activity_Ref tag ----
# Single source of truth for the deterministic Activity_Ref column (mirrors DAPR_CLASS_FRAMEWORK.md).
FRAMEWORK_REFS = [
    # antibacterial — VERIFIED
    ("streptomycin", "VERIFIED aminoglycoside (textbook)"),
    ("gentamicin", "VERIFIED aminoglycoside (textbook)"),
    ("kanamycin", "VERIFIED aminoglycoside (textbook)"),
    ("formicamycin", "VERIFIED formicamycin antibacterial"),
    ("surugamide", "VERIFIED surugamide"),
    ("carbapenem", "VERIFIED Hood 1979; mSphere 2025"),
    ("clavulan", "VERIFIED clavulanic acid (S. clavuligerus)"),
    ("glycinocin", "VERIFIED glycinocin"),
    ("a54145", "VERIFIED Boeck 1990; Miao 2006"),
    ("kijanimicin", "VERIFIED spirotetronate"),
    ("teicoplanin", "VERIFIED Parenti 1978"),
    # antifungal — VERIFIED
    ("filipin", "VERIFIED (S. avermitilis PteF)"),
    ("candicidin", "VERIFIED Gil 2003"),
    ("nystatin", "VERIFIED (S. noursei)"),
    ("linearmycin", "VERIFIED Sakuda 1995"),
    ("mediomycin", "VERIFIED Caffrey 2016"),
    ("dihydromaltophilin", "VERIFIED Yu 2021 AEM"),
    ("hsaf", "VERIFIED Yu 2021 AEM"),
    ("maltophilin", "VERIFIED Yu 2021 AEM"),
    # antifungal-adjacent (cytotoxic caution)
    ("maduramicin", "antifungal-adjacent (cytotoxic)"),
    ("oligomycin", "antifungal-adjacent (cytotoxic)"),
    ("salinomycin", "antifungal-adjacent (cytotoxic)"),
    # ROUTED-OUT — cytotoxic-adjacent
    ("cosmomycin", "ROUTED-OUT cytotoxic (anthracycline)"),
    ("kinamycin", "ROUTED-OUT cytotoxic (diazo)"),
    ("rebeccamycin", "ROUTED-OUT cytotoxic (indolocarbazole)"),
    ("k-252", "ROUTED-OUT cytotoxic (indolocarbazole)"),
    ("staurosporine", "ROUTED-OUT cytotoxic (indolocarbazole)"),
    ("herbimycin", "ROUTED-OUT cytotoxic (Hsp90 ansamycin)"),
    ("geldanamycin", "ROUTED-OUT cytotoxic (Hsp90 ansamycin)"),
    ("kedarcidin", "ROUTED-OUT cytotoxic (enediyne)"),
    ("streptonigrin", "ROUTED-OUT cytotoxic (aminoquinone)"),
    # ROUTED-OUT — ecological siderophore
    ("coelichelin", "ROUTED-OUT ecological (siderophore)"),
    ("desferrioxamine", "ROUTED-OUT ecological (siderophore)"),
    ("mirubactin", "ROUTED-OUT ecological (siderophore)"),
]


def activity_ref(kcb_text):
    t = (kcb_text or "").lower().replace("kcb~", "")
    for cpd, tag in FRAMEWORK_REFS:
        if cpd in t:
            return tag
    return ""  # unmapped -> leave for Sapote pass


def rtier(n50, efls):
    if n50 >= 1_000_000: return "A"
    if efls < 20: return "D"
    if efls >= 600: return "B"
    return "C"


REC = {"A": "Intact - reference-quality backbone; no rescue",
       "B": "High recovery upside - re-sequencing priority",
       "C": "Limited recovery - lower-yield re-sequencing",
       "D": "Failed assembly - negative control"}


def _index(ws):
    it = ws.iter_rows(values_only=True); hdr = list(next(it))
    return hdr, [dict(zip(hdr, r)) for r in it if r[0] is not None]


def main(path):
    wb = openpyxl.load_workbook(path)
    a2 = {r["strain"]: r for r in _index(wb["A2_Strain_Registry"])[1]}
    b4 = {r["strain"]: r for r in _index(wb["B4_Cross_Strain_Scans"])[1]}
    d1 = {r["strain"]: r for r in _index(wb["D1_RGGMCI_All_Strains"])[1]}
    # v9.7.371 fix: raw_bgcs/corrected_bgcs are NOT columns on A2_Strain_Registry under the
    # canonical schema -- they live on A3_Run_Manifest, keyed by strain (last row per strain wins
    # = latest run, since new runs are appended). Mirrors tools/export_figure_ready.py's identical
    # documented fix for the same drift.
    a3 = {}
    if "A3_Run_Manifest" in wb.sheetnames:
        for r in _index(wb["A3_Run_Manifest"])[1]:
            s = r.get("strain")
            if s is not None:
                a3[s] = r

    # --- D5 Fragment_Rescue_Tiers (deterministic rebuild) ---
    if "Fragment_Rescue_Tiers" in wb.sheetnames:
        del wb["Fragment_Rescue_Tiers"]
    fr = wb.create_sheet("Fragment_Rescue_Tiers")
    cols = ["Tier", "strain", "Assembly", "Contigs", "N50", "Frag_Loss",
            "EFLS_Pairs", "RG_GMCI_HIGH", "FLBR_Megasynth", "Recommendation"]
    for j, h in enumerate(cols, 1):
        c = fr.cell(1, j, h); c.fill = HDR; c.font = HF
    recs = []
    for sid, r in a2.items():
        # v9.7.371 fix: A2's real (canonical) headers are lowercase ("n50", "contigs",
        # "assembly_tier"); the prior TitleCase reads ("N50", "Contigs", "Assembly_Grade") never
        # matched any real column and silently defaulted to 0/blank for every strain via .get(),
        # making Tier A ("Intact - no rescue") unreachable regardless of true assembly quality.
        # "Assembly_Grade" has no canonical equivalent by that name; assembly_tier is the closest
        # real qualitative-grade field (see mamey/assembly.py::assembly_tier()).
        n50 = int(r.get("n50") or 0)
        efls = int(b4.get(sid, {}).get("EFLS_pairs") or 0)
        a3r = a3.get(sid, {})
        loss = round((a3r.get("raw_bgcs") or 0) - (a3r.get("corrected_bgcs") or 0), 1)
        # v9.7.371 fix: D1_RGGMCI_All_Strains has no "HIGH" column under the canonical schema.
        # B4_Cross_Strain_Scans.RGGMCI_HIGH is populated from ss.rggmci.get("high_pairs", 0)
        # (mamey/master_workbook.py:460) -- exactly the "HIGH (reference-anchored recovery
        # candidates)" count this module's own docstring already describes.
        recs.append((rtier(n50, efls), sid, r.get("assembly_tier", ""), r.get("contigs"),
                     n50, loss, efls, int(b4.get(sid, {}).get("RGGMCI_HIGH") or 0),
                     int(b4.get(sid, {}).get("FLBR_megasynth") or 0)))
    recs.sort(key=lambda x: ("ABCD".index(x[0]), x[5]))
    for i, t in enumerate(recs, 2):
        for j, v in enumerate(list(t) + [REC[t[0]]], 1):
            fr.cell(i, j, v)
    for j, w in enumerate([6, 9, 10, 9, 10, 10, 11, 13, 15, 42], 1):
        fr.column_dimensions[get_column_letter(j)].width = w

    # --- C1/C2 Activity_Ref refresh (deterministic; judgment cols untouched) ---
    refreshed = 0
    for sheet in ("C1_DAPR_Antibacterial", "C2_DAPR_Antifungal"):
        ws = wb[sheet]; hdr = [c.value for c in ws[1]]
        if "Activity_Ref" not in hdr:
            col = len(hdr) + 1; ws.cell(1, col, "Activity_Ref").font = Font(bold=True)
        else:
            col = hdr.index("Activity_Ref") + 1
        kcb_col = hdr.index("kcb_top") + 1
        for row in range(2, ws.max_row + 1):
            kcb = ws.cell(row, kcb_col).value
            if not kcb:
                continue
            tag = activity_ref(kcb)
            if tag:  # only overwrite when the framework map has an entry
                ws.cell(row, col, tag); refreshed += 1

    atomic_save(wb, path)
    emit(f"D5 Fragment_Rescue_Tiers rebuilt ({len(recs)} strains); Activity_Ref refreshed ({refreshed} rows)")
    emit("tier counts:", {t: sum(1 for r in recs if r[0] == t) for t in "ABCD"})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: build_dapr_rescue_sheets.py <master_workbook.xlsx>")
    main(sys.argv[1])
