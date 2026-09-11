#!/usr/bin/env python3
"""Build unified per-strain BGC dossiers (md + landscape docx) for the AS cohort.

Merges: roster_v2.json (coverage denominators) + AS_cohort_novelty_board.csv
(reference-dark cores) + COMPREHENSIVE_clusterblast_both.csv (MIBiG anchors
this AS strain has that no SID strain has) + the existing v3 roster md
(lead-ranking table + per-BGC 4-channel detail, reused verbatim).

Claim-safety: every %id is homology/capacity only; predicted != measured;
judgment deferred; a null channel means NOT RUN, never a biological zero.
Every count carries its denominator.

Usage:
  python build_strain_dossier.py --strain AS-XXX
  python build_strain_dossier.py --all
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, sys, glob, collections
import os

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
BASE = os.path.join(ROOT, "sapote_deliverables")
ROSTER_DIR = os.path.join(BASE, "roster_v2")
DOSSIER_DIR = os.path.join(BASE, "dossiers")
MASTER_DIR = os.path.join(ROOT, "strain_data")
BOARD_CSV = os.path.join(BASE, "AS_cohort_novelty_board.csv")
COMP_CSV = os.path.join(BASE, "COMPREHENSIVE_clusterblast_both.csv")

import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
try:  # cohort exclusions come from the governed SSOT, never hardcoded here
    from mamey.exclusions import raw_analysis_excluded
    EXCLUDE = raw_analysis_excluded()
except Exception as _exc:  # pragma: no cover - standalone use without mamey
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    ) from _exc
CHANNELS = ["nr", "swissprot", "mibig", "clusterblast"]

# ---- cohort-level caches (loaded once) ----------------------------------
_BOARD = None
_SID_COMPOUNDS = None
_AS_COMPOUNDS = None

def load_board():
    global _BOARD
    if _BOARD is None:
        _BOARD = collections.defaultdict(list)
        with open(BOARD_CSV) as f:
            for r in csv.DictReader(f):
                _BOARD[r["strain"]].append(r)
    return _BOARD

def load_clusterblast():
    """SID compound universe + per-AS-strain compound -> best anchor stats."""
    global _SID_COMPOUNDS, _AS_COMPOUNDS
    if _SID_COMPOUNDS is None:
        _SID_COMPOUNDS = set()
        _AS_COMPOUNDS = collections.defaultdict(dict)  # strain -> {compound: (n_genes,max_pid,max_med)}
        with open(COMP_CSV) as f:
            for r in csv.DictReader(f):
                comp = r["compound"]
                try:
                    ng, mp, mx = int(r["n_genes"]), float(r["median_pid"]), float(r["max_pid"])
                except ValueError:
                    continue
                if r["cohort"] == "SID":
                    _SID_COMPOUNDS.add(comp)
                elif r["cohort"] == "AS":
                    d = _AS_COMPOUNDS[r["strain"]]
                    if comp in d:
                        ong, omx, omd = d[comp]
                        d[comp] = (max(ong, ng), max(omx, mx), max(omd, mp))
                    else:
                        d[comp] = (ng, mx, mp)
    return _SID_COMPOUNDS, _AS_COMPOUNDS

# ---- helpers ------------------------------------------------------------
def coverage(roster):
    tot = 0
    cov = collections.Counter()
    for b in roster["bgcs"]:
        for g in b["genes"]:
            tot += 1
            for ch, v in g["channels"].items():
                if v:
                    cov[ch] += 1
    return tot, cov

def v3_body(strain):
    """Return the lead-ranking + per-BGC detail chunk from the v3 md, verbatim,
    with headers relabelled to the dossier's section numbering."""
    p = os.path.join(ROSTER_DIR, f"{strain}_BGC_protein_roster_v3.md")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8").read()
    idx = txt.find("## Lead ranking")
    if idx < 0:
        return None
    chunk = txt[idx:]
    chunk = chunk.replace("## Lead ranking (novelty-first)",
                          "## 3. Novelty-ranked BGC table (novelty-first)", 1)
    chunk = chunk.replace("## Per-BGC detail", "## 4. Per-BGC detail", 1)
    return chunk

def unique_here(strain):
    """(a) reference-dark cores from the board; (b) MIBiG anchors AS-only vs SID."""
    board = load_board()
    rows = board.get(strain, [])
    dark = []
    for r in rows:
        try:
            cd = int(r["core_dark_confirmed"]); ct = int(r["core_total"])
        except (ValueError, KeyError):
            cd = ct = 0
        if cd > 0:
            dark.append(r)
    dark.sort(key=lambda r: -int(r["core_dark_confirmed"]))

    sid, asc = load_clusterblast()
    mine = asc.get(strain, {})
    as_only = [(c, v) for c, v in mine.items() if c not in sid]
    # rank by anchor breadth then similarity
    as_only.sort(key=lambda x: (-x[1][0], -x[1][1]))
    return dark, as_only, len(mine)

def build_md(strain):
    roster = json.load(open(os.path.join(ROSTER_DIR, f"{strain}_roster_v2.json")))
    body = v3_body(strain)
    if body is None:
        return None, "missing v3 md"
    tot, cov = coverage(roster)
    nbgc = len(roster["bgcs"])
    present = roster.get("channels_present", [])
    absent = roster.get("channels_absent", {}) or {}
    dark, as_only, n_mine = unique_here(strain)

    L = []
    L.append(f"# {strain} — strain BGC dossier")
    L.append("")
    L.append(f"*Unified per-strain dossier · {strain} · {nbgc} BGCs · {tot} genes · "
             f"generated 2026-08-03*")
    L.append("")
    L.append("> **Homology & capacity only.** Every BLASTp / ClusterBlast %id is a "
             "class-level similarity lead — \"capacity consistent with,\" never "
             "\"produces\"; predicted ≠ measured; judgment deferred; no structure "
             "or bioactivity claims. Every count carries its denominator. A null / "
             "absent channel means **NOT RUN**, never a biological zero.")
    L.append("")

    # --- Section 1: header / coverage ---
    L.append("## 1. Overview & channel coverage")
    L.append("")
    L.append(f"- **Strain:** {strain}")
    L.append(f"- **BGCs:** {nbgc}")
    L.append(f"- **Total genes:** {tot}")
    L.append(f"- **Widget (interactive BGC map):** "
             f"`sapote_deliverables/widgets/{strain}_BGC_widget.html`")
    L.append("")
    L.append("**Four-channel homology coverage** (genes with a hit / total genes; "
             "an unhit gene is not-yet-resolved, not a biological absence):")
    L.append("")
    L.append("| channel | genes with a hit | coverage |")
    L.append("|---|--:|--:|")
    for ch in CHANNELS:
        c = cov.get(ch, 0)
        pct = f"{100.0*c/tot:.1f}%" if tot else "—"
        note = " *(channel NOT RUN)*" if ch in absent else ""
        L.append(f"| {ch}{note} | {c}/{tot} | {pct} |")
    L.append("")
    if absent:
        L.append(f"> Channels absent for this strain (NOT RUN): {', '.join(absent)}.")
        L.append("")

    # --- Section 2: what's unique here ---
    L.append("## 2. What's unique here")
    L.append("")
    L.append("Reference-dark cores are the honest novelty signal for rare-genus / "
             "fragmented genomes: core biosynthetic genes whose best NCBI-nr hit is "
             "<60% identity have no close characterized homolog. This is a *capacity / "
             "similarity* statement, not evidence of a novel product.")
    L.append("")
    L.append("### 2a. Reference-dark cores (confirmed core genes with nr %id < 60)")
    L.append("")
    if dark:
        L.append("| BGC | class | core dark (nr<60) / core total | med core nr%id | dominant MIBiG anchor |")
        L.append("|---|---|:-:|--:|---|")
        for r in dark:
            med = r.get("nr_median_pid", "") or "—"
            dom = r.get("dominant_mibig", "") or "—"
            L.append(f"| {r['bgc']} | {r['class']} | "
                     f"{r['core_dark_confirmed']}/{r['core_total']} | {med} | {dom} |")
        L.append("")
        L.append("> `core dark` counts core genes with a **confirmed** nr hit < 60% id. "
                 "Core genes not yet nr-BLASTed are a coverage gap (see the `core nr-todo` "
                 "column in section 3), not evidence either way.")
    else:
        L.append("_No BGC in this strain has a **confirmed** core reference-dark gene "
                 "(nr<60%). This may reflect either genuinely well-characterized cores "
                 "**or** core genes not yet nr-BLASTed — check `core nr-todo` in section 3 "
                 "before reading it as \"nothing novel.\"_")
    L.append("")
    L.append("### 2b. MIBiG compound anchors this strain has that no SID-panel strain has")
    L.append("")
    L.append(f"Of {n_mine} MIBiG compound anchors detected for {strain} by ClusterBlast, "
             f"the following **{len(as_only)}** are absent from every strain in the SID "
             "comparison panel. This is *AS-only vs. this SID panel only* — it is a "
             "cohort-relative distinctiveness cue (homology-level), **not** a claim of "
             "global novelty or of production.")
    L.append("")
    if as_only:
        L.append("| MIBiG compound anchor | best n_genes | best max %id | best median %id |")
        L.append("|---|--:|--:|--:|")
        for c, (ng, mx, md) in as_only:
            L.append(f"| {c} | {ng} | {mx:.0f} | {md:.0f} |")
    else:
        L.append("_Every MIBiG anchor detected for this strain is also present somewhere "
                 "in the SID panel (no AS-only-vs-panel anchors), or ClusterBlast was NOT "
                 "RUN for this strain._")
    L.append("")
    L.append("---")
    L.append("")

    # --- Sections 3 & 4 lifted from v3 ---
    L.append(body.rstrip())
    L.append("")
    return "\n".join(L), None

# ---- docx (landscape + repeating headers) -------------------------------
class OptionalDependencyMissing(RuntimeError):
    """Optional docx-export dependency absent. Message names what to install and what is skipped."""


def _md_to_docx_convert(md_path, docx_path):
    # v9.7.409 (CLAUDE_409_optional_deps_guard): the previous `from md_to_docx import convert`
    # imported a Python module that does not exist in the bundle -- the only md->docx helper is the
    # pandoc-backed shell script tools/md_to_docx.sh -- so the docx pass crashed with a bare
    # ModuleNotFoundError on every run. Call the real helper (sibling tools/ dir, resolved from
    # this file's location, not from the workspace CWD) and fail with a typed, actionable message
    # when pandoc / the helper is unavailable, so the .md deliverable still stands.
    import shutil, subprocess
    helper = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "tools", "md_to_docx.sh")
    if not os.path.isfile(helper):
        raise OptionalDependencyMissing(
            f"docx export skipped: md->docx helper not found at {helper}.")
    if shutil.which("pandoc") is None:
        raise OptionalDependencyMissing(
            "docx export skipped: 'pandoc' is not installed (the md->docx helper needs it). "
            "The markdown (.md) deliverable was still written. "
            "Install pandoc (e.g.  brew install pandoc  /  apt-get install pandoc).")
    r = subprocess.run(["bash", helper, md_path, docx_path], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(docx_path):
        raise OptionalDependencyMissing(
            f"docx export skipped: md->docx helper failed (rc={r.returncode}): "
            f"{(r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else 'no output'}")


def to_docx(md_path, docx_path):
    convert = _md_to_docx_convert
    try:
        from docx import Document
    except ImportError as e:
        raise OptionalDependencyMissing(
            "docx post-processing skipped: the 'python-docx' package is not installed. "
            "The markdown (.md) deliverable was still written. "
            "To enable docx, run:  pip install '.[documents]'  (or:  pip install python-docx)."
        ) from e
    from docx.enum.section import WD_ORIENT
    from docx.shared import Inches
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    convert(md_path, docx_path)
    d = Document(docx_path)
    for sec in d.sections:
        sec.orientation = WD_ORIENT.LANDSCAPE
        w, h = sec.page_width, sec.page_height
        sec.page_width, sec.page_height = max(w, h), min(w, h)
        sec.left_margin = sec.right_margin = Inches(0.5)
    for t in d.tables:
        tr = t.rows[0]._tr
        tp = tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        tp.append(el)
    d.save(docx_path)

def build_strain(strain):
    if strain in EXCLUDE:
        return "excluded"
    md, err = build_md(strain)
    if err:
        return f"skip: {err}"
    outdirs = [os.path.join(MASTER_DIR, strain), DOSSIER_DIR]
    for od in outdirs:
        os.makedirs(od, exist_ok=True)
        mdp = os.path.join(od, f"{strain}_strain_dossier.md")
        dxp = os.path.join(od, f"{strain}_strain_dossier.docx")
        open(mdp, "w", encoding="utf-8").write(md)
        try:
            to_docx(mdp, dxp)
        except OptionalDependencyMissing as e:
            emit(f"[build_strain_dossier] {strain}: {e}")
    return "ok"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        strains = sorted(os.path.basename(p).replace("_roster_v2.json", "")
                         for p in glob.glob(os.path.join(ROSTER_DIR, "*_roster_v2.json")))
    elif a.strain:
        strains = [a.strain]
    else:
        ap.error("need --strain or --all")
    ok = 0
    for s in strains:
        r = build_strain(s)
        emit(f"{s}: {r}")
        if r == "ok":
            ok += 1
    emit(f"\nDONE: {ok} dossiers written to both strain_data/<STRAIN>/ and dossiers/")

if __name__ == "__main__":
    main()
