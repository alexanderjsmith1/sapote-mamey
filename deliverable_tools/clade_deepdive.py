#!/usr/bin/env python3
"""clade_deepdive.py — genus/clade deep-dive ORCHESTRATOR (Sapote-Mamey deliverable tool).

Formalizes the multi-track workflow first run ad-hoc for the bee Nocardia clade
(strain_data/_NOCARDIA_CLADE) and now repeated per genus. Given a clade name, a directory of
the clade's genome FASTAs, a BiG-SCAPE cohort DB + the clade's strain ids, and (optional) a
comparator-genome dir, it drives SIX tracks by CALLING the existing + new deliverable tools, then
writes a `<CLADE>_SYNTHESIS.md` skeleton with the section headers, the numbers filled where
computable, and mandatory claim-safety. It DEGRADES GRACEFULLY: a track whose input or external
tool is missing is skipped with a logged note; no track failure aborts the run.

The six tracks (four REUSED from v9.7.352, two NEW here + this orchestrator):
  1. ANI & species boundaries         -> clade_ani.py                (NEW)
  2. BiG-SCAPE GCF sharing matrix      -> bigscape_matrix_widget.py   (REUSED, .352)
  3. Conserved reference-dark proteins -> conserved_dark_proteins.py  (REUSED, .352)
  4. Nucleotide core-BGC clock         -> clade_nt_core_bgc.py        (NEW)
  5. Decontamination (per-contig bins) -> clade_decontam.py           (NEW, only if flagged)
  6. Clinker within-family alignments  -> bigscape_clinker_widget.py  (REUSED, .352)
(The BiG-SCAPE cohort DB itself is produced by the REUSED bigscape_run.py / `mamey bigscape`.)

Post-seal / reader-side. Every track is class-level CAPACITY / RELATEDNESS: ANI<95% = candidate
distinct species (94-96% boundary/indeterminate), never AAI-as-ANI; BiG-SCAPE GCFs = sequence-
similarity clustering, not compound identity; conserved-dark = conserved protein of unknown
function; comparators are similarity anchors. Sign-off gate applies (genuine sister-group outgroup,
label integrity, assembly-quality flags). Judgment deferred.

Usage:
    clade_deepdive.py --clade Nocardia --genomes genomes/ --db full_cohort.db \\
        --strains AS-XXX,AS-XXX,AS-XXX,AS-XXX,AS-XXX [--comparators refs/] \\
        [--proteomes proteomes/] [--gbk-dir region_gbks/] \\
        [--decontam-assembly AS-XXX.fna --ref-target AS-XXX.fna --ref-contaminant AS-XXX.fna] \\
        --out OUTDIR
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import glob
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

CLAIM_SAFETY = (
    "All tracks are class-level CAPACITY / RELATEDNESS. ANI is nucleotide relatedness, not a species "
    "call (94-96% = boundary/indeterminate; never quote AAI as ANI). BiG-SCAPE GCFs = sequence-"
    "similarity clustering, NOT compound identity. Conserved-dark = conserved protein of UNKNOWN "
    "function. Comparators are similarity anchors. Sign-off gate: genuine sister-group outgroup, "
    "label integrity, assembly-quality flags. Judgment deferred."
)

# (key, section header, one-line description) — canonical order of the six tracks
SECTIONS = [
    ("ani",             "1. ANI & species boundaries (fastANI)",
     "genome-wide nucleotide ANI all-vs-all + sign-off species-boundary calls"),
    ("bigscape_matrix", "2. BiG-SCAPE GCF sharing matrix",
     "strain x gene-cluster-family sharing (sequence-similarity clustering)"),
    ("conserved_dark",  "3. Conserved reference-dark proteins",
     "conserved proteins of unknown function (no Pfam), by conservation scope"),
    ("nt_core_bgc",     "4. Nucleotide core-BGC clock",
     "RBH nt identity + syn/nonsyn over shared core biosynthetic CDS (recency)"),
    ("decontam",        "5. Decontamination (per-contig binning)",
     "per-contig GC/coverage + blastn-vs-two-refs binning (only if flagged)"),
    ("clinker",         "6. Clinker within-family gene alignments",
     "within-GCF synteny / orthogroup alignment across the clade's strains"),
]


# ---- sibling-module loader ---------------------------------------------------------------------

def _import_local(module_name, filename):
    """Import a sibling deliverable_tools/<filename> by path. Returns the module or None."""
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as exc:  # pragma: no cover - defensive
        emit(f"clade_deepdive: could not import {filename} ({type(exc).__name__}: {exc})",
              file=sys.stderr)
        return None


def _has_fastas(d):
    return d and os.path.isdir(d) and any(
        p.lower().endswith((".fna", ".fa", ".fasta"))
        for p in glob.glob(os.path.join(d, "*")))


# ---- track runners (each returns {"status","note",...}; never raises) --------------------------

def track_ani(clade, genomes, out, comparators=None, fastani_bin=None):
    if not _has_fastas(genomes):
        return {"status": "skipped", "note": "no genome FASTAs in --genomes"}
    mod = _import_local("clade_ani", "clade_ani.py")
    if mod is None:
        return {"status": "skipped", "note": "clade_ani.py not found"}
    # If comparators supplied, point fastANI at a merged view is out of scope here; the tool globs
    # one dir. We run over --genomes (which the caller may pre-populate with comparators).
    try:
        kw = {}
        if fastani_bin:
            kw["fastani_bin"] = fastani_bin
        return mod.run(genomes, os.path.join(out, "ani"), clade=clade, **kw)
    except Exception as exc:
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


def track_bigscape_matrix(clade, db, out, cutoff=0.3):
    if not (db and os.path.exists(db)):
        return {"status": "skipped", "note": "no BiG-SCAPE cohort DB (--db)"}
    mod = _import_local("bigscape_matrix_widget", "bigscape_matrix_widget.py")
    if mod is None:
        return {"status": "skipped", "note": "bigscape_matrix_widget.py not found (needs .352 tree)"}
    try:
        res = mod.render_matrix(db=db, cutoff=cutoff, outdir=os.path.join(out, "bigscape_matrix"))
        res["status"] = "ok"
        return res
    except Exception as exc:
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


def track_conserved_dark(clade, proteomes, out):
    if not (proteomes and os.path.isdir(proteomes) and
            glob.glob(os.path.join(proteomes, "*.faa"))):
        return {"status": "skipped", "note": "no proteomes dir of <strain>.faa (--proteomes)"}
    mod = _import_local("conserved_dark_proteins", "conserved_dark_proteins.py")
    if mod is None:
        return {"status": "skipped", "note": "conserved_dark_proteins.py not found (needs .352 tree)"}
    try:
        # run() needs a Pfam source; without one it cannot separate dark from annotated -> skip.
        return {"status": "skipped",
                "note": "conserved-dark needs a Pfam --pfam-tbl/--pfam-hmm; run "
                        "conserved_dark_proteins.py directly with a Pfam source"}
    except Exception as exc:  # pragma: no cover
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


def track_nt_core_bgc(clade, gbk_dir, out):
    if not (gbk_dir and os.path.isdir(gbk_dir) and glob.glob(os.path.join(gbk_dir, "*.gbk"))):
        return {"status": "skipped", "note": "no region GBK dir (--gbk-dir)"}
    mod = _import_local("clade_nt_core_bgc", "clade_nt_core_bgc.py")
    if mod is None:
        return {"status": "skipped", "note": "clade_nt_core_bgc.py not found"}
    try:
        return mod.run(gbk_dir, os.path.join(out, "nt_core_bgc"), clade=clade)
    except Exception as exc:
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


def track_decontam(clade, decontam, out):
    if not decontam:
        return {"status": "skipped", "note": "not flagged (no --decontam-assembly / refs)"}
    assembly, ref_target, ref_contam = decontam
    mod = _import_local("clade_decontam", "clade_decontam.py")
    if mod is None:
        return {"status": "skipped", "note": "clade_decontam.py not found"}
    try:
        return mod.run(assembly, ref_target, ref_contam, os.path.join(out, "decontam"), clade=clade)
    except Exception as exc:
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


def track_clinker(clade, db, out, cutoff=0.3):
    if not (db and os.path.exists(db)):
        return {"status": "skipped", "note": "no BiG-SCAPE cohort DB (--db)"}
    mod = _import_local("bigscape_clinker_widget", "bigscape_clinker_widget.py")
    if mod is None:
        return {"status": "skipped", "note": "bigscape_clinker_widget.py not found (needs .352 tree)"}
    try:
        res = mod.render_families(db=db, cutoff=cutoff, outdir=os.path.join(out, "clinker"))
        return {"status": "ok", "detail": str(res)[:200]}
    except Exception as exc:
        return {"status": "error", "note": f"{type(exc).__name__}: {exc}"}


# ---- synthesis writer --------------------------------------------------------------------------

def _fmt_metrics(res):
    """Render a track result's metric fields as markdown bullets (everything but status/note)."""
    lines = []
    for k, v in res.items():
        if k in ("status", "note", "seq"):
            continue
        if isinstance(v, dict):
            v = ", ".join(f"{a}={b}" for a, b in list(v.items())[:12])
        lines.append(f"  - `{k}`: {v}")
    return lines


def write_synthesis(clade, results, out_path, strains=None, genomes=None, db=None):
    """Write <CLADE>_SYNTHESIS.md with all six section headers, numbers where computable, and a
    skip-with-note where a track's input/tool was absent. `results` = dict track_key -> result."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    n_ok = sum(1 for k, _h, _d in SECTIONS if results.get(k, {}).get("status") == "ok")
    with open(out_path, "w") as fh:
        fh.write(f"# {clade} clade deep-dive — synthesis\n\n")
        fh.write(f"**Tracks completed:** {n_ok}/6. ")
        if strains:
            fh.write(f"**Strains:** {', '.join(strains)}. ")
        if db:
            fh.write(f"**BiG-SCAPE DB:** `{db}`. ")
        fh.write("\n\n")
        fh.write("> **Claim-safety.** " + CLAIM_SAFETY + "\n\n")
        fh.write("---\n\n")
        for key, header, desc in SECTIONS:
            res = results.get(key, {"status": "skipped", "note": "not run"})
            status = res.get("status", "skipped")
            badge = {"ok": "DONE", "skipped": "SKIPPED", "error": "ERROR"}.get(status, status)
            fh.write(f"## {header}\n\n")
            fh.write(f"*{desc}.* **[{badge}]**\n\n")
            if status == "ok":
                metrics = _fmt_metrics(res)
                if metrics:
                    fh.write("\n".join(metrics) + "\n\n")
                else:
                    fh.write("  - (completed; see output dir)\n\n")
            else:
                fh.write(f"  - _skipped:_ {res.get('note', 'no input')} — re-run this track's tool "
                         f"directly when the input is available.\n\n")
        fh.write("---\n\n")
        fh.write("## Sign-off checklist (fill before presenting)\n\n")
        fh.write("- [ ] Outgroup is a genuine sister group (e.g. Rhodococcus, not Gordonia, for Nocardia)\n")
        fh.write("- [ ] ANI boundary honesty (94-96% = indeterminate; no AAI quoted as ANI)\n")
        fh.write("- [ ] Assembly-quality flags noted (fragmented/inflated genomes)\n")
        fh.write("- [ ] Label integrity (Genus species strain; current taxonomy)\n")
        fh.write("- [ ] Every metric carries its denominator\n")
        fh.write("- [ ] Claim-safety restated (class-level hypotheses; judgment deferred)\n")
    return out_path


# ---- orchestration -----------------------------------------------------------------------------

def run(clade, genomes, db, strains, comparators=None, out=None, proteomes=None,
        gbk_dir=None, decontam=None, fastani_bin=None, cutoff=0.3):
    """Run the six tracks and write the synthesis skeleton. Returns (results_dict, synthesis_path)."""
    out = out or f"{clade}_deepdive"
    os.makedirs(out, exist_ok=True)
    strains = ([s.strip() for s in strains.split(",")] if isinstance(strains, str)
               else (strains or []))
    results = {}
    results["ani"] = track_ani(clade, genomes, out, comparators=comparators, fastani_bin=fastani_bin)
    results["bigscape_matrix"] = track_bigscape_matrix(clade, db, out, cutoff=cutoff)
    results["conserved_dark"] = track_conserved_dark(clade, proteomes, out)
    results["nt_core_bgc"] = track_nt_core_bgc(clade, gbk_dir, out)
    results["decontam"] = track_decontam(clade, decontam, out)
    results["clinker"] = track_clinker(clade, db, out, cutoff=cutoff)
    for key, _h, _d in SECTIONS:
        r = results.get(key, {})
        emit(f"  [{r.get('status','skipped'):7}] {key}"
              + (f" — {r['note']}" if r.get("note") else ""))
    synth = write_synthesis(clade, results, os.path.join(out, f"{clade}_SYNTHESIS.md"),
                            strains=strains, genomes=genomes, db=db)
    emit(f"  synthesis -> {synth}")
    return results, synth


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genus/clade deep-dive orchestrator (six tracks)")
    ap.add_argument("--clade", required=True, help="clade name (output prefix)")
    ap.add_argument("--genomes", required=True, help="dir of the clade's genome FASTAs")
    ap.add_argument("--db", default=None, help="BiG-SCAPE cohort SQLite DB (full_cohort.db)")
    ap.add_argument("--strains", default="", help="comma list of the clade's strain ids")
    ap.add_argument("--comparators", default=None, help="optional dir of comparator/type genome FASTAs")
    ap.add_argument("--proteomes", default=None, help="optional dir of <strain>.faa (conserved-dark)")
    ap.add_argument("--gbk-dir", default=None, help="optional dir of region GBKs (nt core-BGC clock)")
    ap.add_argument("--decontam-assembly", default=None, help="assembly to decontaminate (if flagged)")
    ap.add_argument("--ref-target", default=None, help="clean same-genus ref (decontam)")
    ap.add_argument("--ref-contaminant", default=None, help="clean contaminant ref (decontam)")
    ap.add_argument("--fastani", default=None, help="fastANI binary override")
    ap.add_argument("--cutoff", type=float, default=0.3, help="BiG-SCAPE GCF cutoff (default 0.3)")
    ap.add_argument("--out", default=None, help="output dir (default <clade>_deepdive)")
    a = ap.parse_args(argv)
    decontam = None
    if a.decontam_assembly and a.ref_target and a.ref_contaminant:
        decontam = (a.decontam_assembly, a.ref_target, a.ref_contaminant)
    run(a.clade, a.genomes, a.db, a.strains, comparators=a.comparators, out=a.out,
        proteomes=a.proteomes, gbk_dir=a.gbk_dir, decontam=decontam, fastani_bin=a.fastani,
        cutoff=a.cutoff)
    emit("  " + CLAIM_SAFETY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
