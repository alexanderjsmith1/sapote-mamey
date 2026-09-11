#!/usr/bin/env python3
"""build_modeb_compilation.py — per-strain Mode B compilation (report + cards + majority-read + figures).

Binds, for one strain, into a single claim-safe dossier:
  §1  the strain report (July 20 thesis strain_reports/<strain>_report.md)
  §2  a whole-BGC MAJORITY-READ overview (from whole_bgc_majority_read_cohort.csv) — the honest
      per-BGC characterization table, so the compilation is claim-safe by construction
  §3  every Mode B v9.7.339 card, each PREFACED with its majority-read verdict banner (a FLAGGED
      family call is labelled class-level right where the card sits)
  §4  a figures / widgets index for the strain (paths; images not embedded by md_to_docx)

Card set = mode_b_v9.7.339 (engine-graded, full coverage) + majority-read overlay (the Developer or User, 2026-08-05).
Output = one md + one docx per strain (per-strain format), written to strain_data/<strain>/ and a
shared compilation dir.

Claim-safety: class-level capacity only; similarity != identity; a per-gene hit != product identity;
predicted != measured; judgment deferred. The majority-read banner never asserts a product.

Usage:
  build_modeb_compilation.py --strain AS-XXX         # pilot one strain
  build_modeb_compilation.py --strains AS-XXX AS-XXX ...
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, re, sys, os
from pathlib import Path
try:
    from mamey.canonical_write_guard import guard_canonical_write
except ImportError:  # bare-script run: bundle root is one level up
    import os as _g_os, sys as _g_sys
    _g_sys.path.insert(0, _g_os.path.dirname(_g_os.path.dirname(_g_os.path.abspath(__file__))))
    from mamey.canonical_write_guard import guard_canonical_write

ROOT = Path(os.environ.get("MAMEY_DATA_ROOT", os.getcwd()))
MASTER = ROOT / "strain_data"
REPORTS = ROOT / "July 20 thesis claude" / "strain_reports"
MAJORITY = MASTER / "whole_bgc_majority_read_2026-08-05" / "whole_bgc_majority_read_cohort.csv"
OUTDIR = MASTER / "modeb_compilation_2026-08-05"

VERDICT_ICON = {"STRONG_FAMILY_ANCHOR": "◆", "PARTIAL_ANCHOR": "◐",
                "FLAGGED_MINORITY": "⚠", "NO_MIBIG_ANCHOR": "○"}


def majority_map(strain: str) -> dict[str, dict]:
    out = {}
    if not MAJORITY.is_file():
        return out
    with MAJORITY.open() as fh:
        for r in csv.DictReader(fh):
            if r["strain"] == strain:
                out[r["bgc_id"]] = r
    return out


def bgc_of(card_path: Path) -> str:
    m = re.search(r"(BGC\d+)", card_path.name)
    return m.group(1) if m else card_path.stem


def banner(rec: dict | None) -> str:
    if not rec:
        return "> 🔎 **Whole-BGC majority read:** not available for this BGC.\n"
    icon = VERDICT_ICON.get(rec["verdict"], "•")
    return (f"> {icon} **Whole-BGC majority read: {rec['verdict']}** — {rec['honest_line']}\n"
            f"> *(genes hitting MIBiG: {rec['hit_genes']}/{rec['total_genes']}, share "
            f"{rec['query_gene_share']}, median id {rec['median_pct_identity']}%, boundary "
            f"{rec.get('boundary','?')}, flags: {rec['flags'] or 'none'})*\n")


def demote_headers(md: str) -> str:
    """Push a card's own #/## headers one level deeper so they nest under the §3 card heading."""
    return re.sub(r"(?m)^(#{1,5})\s", lambda m: "#" + m.group(1) + " ", md)


def build(strain: str) -> str:
    mm = majority_map(strain)
    cards = sorted((MASTER / strain / "mode_b_v9.7.339").glob(f"{strain}_BGC*_ModeB.md"),
                   key=lambda p: bgc_of(p))
    L: list[str] = []
    L.append(f"# {strain} — Mode B compilation")
    L.append("")
    L.append(f"*Strain report + {len(cards)} Mode B v9.7.339 cards (each with its whole-BGC "
             f"majority-read verdict) + figures index · generated 2026-08-05*")
    L.append("")
    L.append("> **Claim-safety.** Class-level capacity only. Every MIBiG/BLASTp %id is a similarity "
             "lead — \"capacity consistent with,\" never \"produces.\" A per-gene hit is a class-level "
             "anchor, not a product identity; similarity ≠ identity; predicted ≠ measured; judgment "
             "deferred. The majority-read banner labels each family call by how much of the BGC "
             "actually supports it.")
    L.append("")

    # §1 strain report
    L.append("## 1. Strain report")
    L.append("")
    rp = REPORTS / f"{strain}_report.md"
    if rp.is_file():
        rt = rp.read_text(encoding="utf-8", errors="replace")
        rt = re.sub(r"(?m)^(#{1,5})\s", lambda m: "#" + m.group(1) + " ", rt)  # demote
        L.append(rt.rstrip())
    else:
        L.append(f"_No strain report found at {rp}._")
    L.append("")

    # §2 majority-read overview
    L.append("## 2. Whole-BGC majority-read overview (honest characterization)")
    L.append("")
    L.append("Each BGC's MIBiG family call, graded by how many of its genes actually support it "
             "(◆ strong family anchor · ◐ partial · ⚠ flagged minority/promiscuous · ○ no MIBiG hit). "
             "A ⚠ row must be read as class-level similarity, never a product identity.")
    L.append("")
    L.append("| BGC | products | boundary | genes hit / total | share | id | verdict |")
    L.append("|---|---|---|--:|--:|--:|---|")
    for bgc in sorted(mm, key=lambda b: int(re.sub(r"\D", "", b) or 0)):
        r = mm[bgc]
        icon = VERDICT_ICON.get(r["verdict"], "•")
        L.append(f"| {bgc} | {r['products'][:20]} | {r.get('boundary','')} | "
                 f"{r['hit_genes']}/{r['total_genes']} | {r['query_gene_share']} | "
                 f"{r['median_pct_identity']}% | {icon} {r['verdict']} |")
    L.append("")
    # a small honest tally
    from collections import Counter
    tally = Counter(r["verdict"] for r in mm.values())
    L.append(f"> Verdict tally: " + ", ".join(f"{v}={n}" for v, n in tally.most_common()) + ".")
    L.append("")

    # §3 the cards
    L.append("## 3. Mode B cards (v9.7.339) with majority-read verdicts")
    L.append("")
    for i, cp in enumerate(cards, 1):
        bgc = bgc_of(cp)
        L.append(f"### 3.{i}  {bgc}")
        L.append("")
        L.append(banner(mm.get(bgc)))
        L.append("")
        L.append(demote_headers(cp.read_text(encoding="utf-8", errors="replace")).rstrip())
        L.append("")
        L.append("---")
        L.append("")

    # §4 figures / widgets index
    L.append("## 4. Figures & widgets index")
    L.append("")
    figs = sorted((MASTER / strain / "figures").rglob("*.*")) if (MASTER / strain / "figures").exists() else []
    wids = sorted((MASTER / strain / "widgets").glob("*.html")) if (MASTER / strain / "widgets").exists() else []
    if figs:
        L.append("**Figures:**")
        for f in figs[:40]:
            L.append(f"- `{f.relative_to(ROOT)}`")
    else:
        L.append("_No per-strain figures directory populated; Figure Factory outputs live under the "
                 "dated Figure Factory folders (link at compile time when the canonical set is chosen)._")
    L.append("")
    if wids:
        L.append("**Interactive widgets:**")
        for w in wids[:40]:
            L.append(f"- `{w.relative_to(ROOT)}`")
    L.append("")
    return "\n".join(L)


class OptionalDependencyMissing(RuntimeError):
    """Optional docx-export dependency absent. Message names what to install and what is skipped."""


def _md_to_docx_convert(md_path: str, docx_path: str) -> None:
    # v9.7.409 (CLAUDE_409_optional_deps_guard): `from md_to_docx import convert` imported a Python
    # module that does not exist -- the only md->docx helper in the bundle is the pandoc-backed
    # shell script tools/md_to_docx.sh -- so the docx pass never produced output. Call the real
    # helper (resolved from this file's location) and raise a typed, actionable message when
    # pandoc / the helper is unavailable, leaving the .md deliverable intact.
    import shutil, subprocess
    helper = Path(__file__).resolve().parent.parent / "tools" / "md_to_docx.sh"
    if not helper.is_file():
        raise OptionalDependencyMissing(
            f"docx export skipped: md->docx helper not found at {helper}.")
    if shutil.which("pandoc") is None:
        raise OptionalDependencyMissing(
            "docx export skipped: 'pandoc' is not installed (the md->docx helper needs it). "
            "The markdown (.md) deliverable was still written. "
            "Install pandoc (e.g.  brew install pandoc  /  apt-get install pandoc).")
    r = subprocess.run(["bash", str(helper), str(md_path), str(docx_path)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(docx_path):
        raise OptionalDependencyMissing(
            f"docx export skipped: md->docx helper failed (rc={r.returncode}): "
            f"{(r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else 'no output'}")


def to_docx(md_path: Path, docx_path: Path) -> None:
    """Landscape docx with repeating table headers (reuses the dossier pattern)."""
    convert = _md_to_docx_convert
    try:
        from docx import Document
        from docx.enum.section import WD_ORIENT
        from docx.shared import Inches
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError as e:
        raise OptionalDependencyMissing(
            "docx post-processing skipped: the 'python-docx' package is not installed. "
            "The markdown (.md) deliverable was still written. "
            "To enable docx, run:  pip install '.[documents]'  (or:  pip install python-docx)."
        ) from e
    convert(str(md_path), str(docx_path))
    d = Document(str(docx_path))
    for sec in d.sections:
        sec.orientation = WD_ORIENT.LANDSCAPE
        w, h = sec.page_width, sec.page_height
        sec.page_width, sec.page_height = max(w, h), min(w, h)
        sec.left_margin = sec.right_margin = Inches(0.5)
    for t in d.tables:
        tp = t.rows[0]._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader"); el.set(qn("w:val"), "true"); tp.append(el)
    d.save(str(docx_path))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain")
    ap.add_argument("--strains", nargs="+")
    ap.add_argument("--no-docx", action="store_true")
    # v9.7.413 (BC2): --out, mirroring `majority-read` and `surface-leads` (the latter landed at
    # .412). Without it this command had no way NOT to write into the canonical home: it writes
    # BOTH `<MAMEY_DATA_ROOT>/strain_data/<STRAIN>/` and the dated
    # `strain_data/modeb_compilation_2026-08-05/` on every run, and `strain_data` is a symlink to
    # the canonical evidence root. Unlike surface-leads, `build()` reads live per-strain state, so a re-run
    # REPLACES rather than reproduces — and the canonical folder also holds .pdf files this tool
    # does not regenerate, so an unguarded run leaves a stale PDF beside a rewritten MD/DOCX.
    # With --out, both copies collapse to the one given directory. Default is unchanged.
    ap.add_argument("--out", help="write to this directory INSTEAD of the two canonical targets "
                                  "(default: <root>/strain_data/<STRAIN>/ AND the dated "
                                  "modeb_compilation folder, both overwritten in place)")
    ap.add_argument("--force", "--in-place", dest="force", action="store_true",
                    help="allow overwriting an existing canonical dated deliverable")
    a = ap.parse_args()
    strains = a.strains or ([a.strain] if a.strain else None)
    if not strains:
        ap.error("give --strain or --strains")
    targets = [Path(a.out)] if a.out else None
    if targets is None:
        OUTDIR.mkdir(parents=True, exist_ok=True)
    for s in strains:
        md = build(s)
        for od in (targets if targets is not None else (MASTER / s, OUTDIR)):
            od.mkdir(parents=True, exist_ok=True)
            mdp = od / f"{s}_ModeB_compilation.md"
            # v9.7.413 (BC2): refuse to silently replace an existing canonical dated deliverable.
            guard_canonical_write(mdp, force=a.force)
            mdp.write_text(md, encoding="utf-8")
            if not a.no_docx:
                try:
                    to_docx(mdp, od / f"{s}_ModeB_compilation.docx")
                except OptionalDependencyMissing as e:
                    emit(f"  {s}: {e}")
                except Exception as e:
                    emit(f"  {s}: docx failed ({type(e).__name__}: {str(e)[:80]}); md written")
        _where = targets[0] if targets is not None else (MASTER / s)
        emit(f"{s}: compiled ({md.count(chr(10))} lines) -> {_where}/{s}_ModeB_compilation.(md|docx)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
