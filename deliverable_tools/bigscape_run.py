#!/usr/bin/env python3
"""bigscape_run.py — run BiG-SCAPE 2.x as a first-class Sapote-Mamey post-seal step.

This is the runner behind the ``mamey bigscape`` subcommand. It takes a sealed Mamey
package (or a cohort of them, or an explicit GBK dir), gathers the antiSMASH **region**
GBKs, runs BiG-SCAPE 2 clustering on them, locates the produced SQLite cohort DB, and
(optionally) chains straight into the existing ``bigscape-widgets`` cohort widgets
(strain x GCF-family matrix + clinker within-family gene alignments).

Design: THIN integration. It REUSES the shipped tools rather than reinventing them:
  * ``tools/bigscape_prep.py``      — region-GBK discovery + strain-prefixed staging
                                      (imported: strain_from / stage_zip / stage_dir).
  * ``deliverable_tools/bigscape_matrix_widget.py`` + ``bigscape_clinker_widget.py``
                                      — the .351 widget generators it chains into.
It ADDS only the pieces those tools don't cover: the *proven* BiG-SCAPE 2.0.3 invocation
(``cluster --record-type region --classify category``), the two environment gotchas
(fasttree casing, spaces-in-paths), DB location, and the widget chain.

stdlib + subprocess only. No heavy deps. Engine-neutral: reads GBKs, runs an external
binary, reads the DB — never touches scores, tiers, boards, or the sealed package.

Claim-safety: BiG-SCAPE GCF families = sequence-similarity clustering, class-level only;
comparators are similarity anchors, not compound identity; judgment deferred.

Proven recipe (real run, 2026-08-04, Nocardia cohort, ~543 region GBKs, 4 cpus, ~500s):
    bigscape cluster -i <INPUT_GBK_DIR> -o <OUT_DIR> -p <PFAM-A.hmm> \\
        --record-type region --classify category \\
        --gcf-cutoffs 0.3,0.5,0.7 --include-singletons -c <CPUS>

Usage (standalone; the subcommand mirrors these args):
    python bigscape_run.py --package runs/AS-XXX/package --out AS-XXX/bigscape
    python bigscape_run.py --runs-dir runs_gold/ --out cohort/bigscape --cpus 4
    python bigscape_run.py --input-gbk-dir bigscape_input/ --out out/ --dry-run
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)  # deliverable_tools/ sits next to mamey/ and tools/

# ---- documented defaults (override on the CLI / subcommand) -------------------------
BIGSCAPE_BIN_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/bigscape/bin/bigscape"
PFAM_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/BigSCAPE/Pfam-A.hmm"
CUTOFFS_DEFAULT = "0.3,0.5,0.7"

REGION = re.compile(r"region\d+\.gbk$", re.I)


# ---- reuse tools/bigscape_prep.py for GBK discovery/staging -------------------------
def _load_prep():
    """Import the shipped tools/bigscape_prep.py (region-GBK collector). Returns the module,
    or None if the tools/ tree is not alongside (e.g. running from an installed wheel)."""
    import importlib.util as _ilu

    path = os.path.join(REPO_ROOT, "tools", "bigscape_prep.py")
    if not os.path.exists(path):
        return None
    spec = _ilu.spec_from_file_location("_sapote_bigscape_prep", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strain_from(name: str) -> str:
    b = os.path.basename(name)
    b = re.sub(r"\.(zip|tar\.gz|tgz)$", "", b, flags=re.I)
    b = re.sub(r"_SapoteMamey.*$", "", b)
    return b


def discover_inputs(package=None, runs_dir=None, input_gbk_dir=None):
    """Return (mode, items) describing where region GBKs come from.

    Exactly one source is honored, in priority order:
      * input_gbk_dir -> ("gbk_dir", [dir])          already-extracted region GBKs
      * package       -> ("packages", [pkg_dir])     one sealed Mamey package dir/zip
      * runs_dir      -> ("packages", [pkg, ...])     a cohort: every <ID>/package under it
    """
    if input_gbk_dir:
        return "gbk_dir", [input_gbk_dir]
    if package:
        return "packages", [package]
    if runs_dir:
        items = []
        # a cohort layout is <runs_dir>/<ID>/package/  (matches cohort-figures --runs-dir)
        for pkg in sorted(glob.glob(os.path.join(runs_dir, "*", "package"))):
            items.append(pkg)
        # also accept sealed zips / bare package dirs directly under runs_dir
        items += sorted(glob.glob(os.path.join(runs_dir, "*.zip")))
        if not items:
            items = [p for p in sorted(glob.glob(os.path.join(runs_dir, "*"))) if os.path.isdir(p)]
        return "packages", items
    raise ValueError("no input source: pass --package, --runs-dir, or --input-gbk-dir")


def stage_gbks(mode, items, out_dir):
    """Copy/extract region GBKs into a (space-free) staging dir, strain-prefixed so records
    from different strains never collide. Reuses tools/bigscape_prep.py when available.

    Returns the number of region GBKs staged."""
    os.makedirs(out_dir, exist_ok=True)
    prep = _load_prep()
    total = 0

    if mode == "gbk_dir":
        src = items[0]
        for f in glob.glob(os.path.join(src, "**", "*.gbk"), recursive=True):
            if os.path.basename(f).startswith("._"):
                continue  # macOS AppleDouble resource forks crash BiG-SCAPE
            if not REGION.search(f):
                continue
            base = os.path.basename(f)
            # only add a strain prefix if the filename isn't already prefixed
            shutil.copy(f, os.path.join(out_dir, base))
            total += 1
        return total

    # mode == "packages": one or more sealed Mamey packages / antiSMASH zips
    for it in items:
        strain = _strain_from(it)
        try:
            if prep is not None:
                if os.path.isdir(it):
                    n = prep.stage_dir(it, out_dir, strain)
                elif it.lower().endswith(".zip"):
                    n = prep.stage_zip(it, out_dir, strain)
                else:
                    continue
            else:  # fallback: same logic, no import
                n = _stage_dir_fallback(it, out_dir, strain) if os.path.isdir(it) else 0
        except Exception as e:  # never let one bad input abort the cohort
            emit(f"  {strain}: SKIP ({type(e).__name__}: {e})", file=sys.stderr)
            continue
        if n:
            emit(f"  staged {strain}: {n} region GBKs")
            total += n
    return total


def _stage_dir_fallback(d, out, strain):
    n = 0
    for f in glob.glob(os.path.join(d, "**", "*.gbk"), recursive=True):
        if os.path.basename(f).startswith("._") or not REGION.search(f):
            continue
        shutil.copy(f, os.path.join(out, f"{strain}_{os.path.basename(f)}"))
        n += 1
    return n


# ---- GOTCHA 1: fasttree casing ------------------------------------------------------
def ensure_fasttree(bigscape_bin, shim_dir):
    """BiG-SCAPE 2 shells out to `fasttree` (lowercase) to build per-GCF dendrograms for the
    HTML. conda ships the binary as `FastTree` (capital) / `FastTreeMP`, so a bare `fasttree`
    is not on PATH and the HTML build dies with FileNotFoundError (clustering + DB are fine,
    only the HTML fails). Fix defensively: if `fasttree` is already resolvable, do nothing;
    otherwise symlink a discovered FastTree/FastTreeMP to `<shim_dir>/fasttree` and return
    shim_dir (caller prepends it to PATH). Returns the shim dir used, or None if nothing was
    needed / no FastTree was found.
    """
    if shutil.which("fasttree"):
        return None  # already resolvable
    candidates = []
    env_bin = os.path.dirname(os.path.abspath(bigscape_bin)) if bigscape_bin else ""
    for name in ("FastTree", "FastTreeMP"):
        if env_bin:
            p = os.path.join(env_bin, name)
            if os.path.exists(p):
                candidates.append(p)
        w = shutil.which(name)
        if w:
            candidates.append(w)
    if not candidates:
        emit("  bigscape: WARNING: no fasttree/FastTree found; per-GCF HTML dendrograms "
              "may fail (clustering + DB unaffected).", file=sys.stderr)
        return None
    os.makedirs(shim_dir, exist_ok=True)
    link = os.path.join(shim_dir, "fasttree")
    try:
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(candidates[0], link)
    except OSError:  # fall back to a copy if symlinks are unavailable
        shutil.copy(candidates[0], link)
        os.chmod(link, 0o755)
    emit(f"  bigscape: shimmed `fasttree` -> {candidates[0]} (in {shim_dir})")
    return shim_dir


# ---- GOTCHA 2: spaces in paths ------------------------------------------------------
def _stage_no_space(path, work_root):
    """If `path` contains a space, symlink it under a space-free dir and return the link;
    else return the path unchanged. Used for the Pfam DB (the input GBK dir is always staged
    into the space-free work dir separately)."""
    if path and " " in os.path.abspath(path):
        os.makedirs(work_root, exist_ok=True)
        link = os.path.join(work_root, os.path.basename(path).replace(" ", "_"))
        if os.path.lexists(link):
            os.remove(link)
        try:
            os.symlink(os.path.abspath(path), link)
        except OSError:
            return path
        return link
    return path


# ---- command assembly ---------------------------------------------------------------
def build_command(bigscape_bin, input_dir, out_dir, pfam, cpus,
                  cutoffs=CUTOFFS_DEFAULT, record_type="region",
                  classify="category", include_singletons=True):
    """Assemble the proven BiG-SCAPE 2.0.3 cluster command as a list of str.

    Proven flags (2026-08-04 Nocardia run):
      cluster -i IN -o OUT -p PFAM --record-type region --classify category
              --gcf-cutoffs 0.3,0.5,0.7 --include-singletons -c CPUS
    """
    cmd = [bigscape_bin, "cluster",
           "-i", input_dir,
           "-o", out_dir,
           "-p", pfam,
           "--record-type", record_type,
           "--classify", classify,
           "--gcf-cutoffs", cutoffs,
           "-c", str(cpus)]
    if include_singletons:
        cmd.append("--include-singletons")
    return cmd


def locate_db(out_dir):
    """Return the BiG-SCAPE 2.x SQLite cohort DB produced under out_dir (newest *.db), or None.
    BiG-SCAPE 2 names the DB from the run/output, so we glob rather than assume a fixed name."""
    dbs = glob.glob(os.path.join(out_dir, "**", "*.db"), recursive=True)
    if not dbs:
        return None
    return max(dbs, key=os.path.getmtime)


# ---- optional widget chain (.351 deliverable) ---------------------------------------
def maybe_run_widgets(db, widgets_out, cutoff=0.3):
    """Chain into the .351 BiG-SCAPE cohort widgets (matrix + clinker) if their generators are
    present next to us in deliverable_tools/. Best-effort, non-blocking. Returns a dict of
    what was produced (possibly empty)."""
    import importlib.util as _ilu

    produced = {}

    def _imp(name):
        path = os.path.join(HERE, name + ".py")
        if not os.path.exists(path):
            return None
        if HERE not in sys.path:
            sys.path.insert(0, HERE)  # so they can import their sibling _bigscape_data
        spec = _ilu.spec_from_file_location(name, path)
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    os.makedirs(widgets_out, exist_ok=True)
    try:
        matrix_mod = _imp("bigscape_matrix_widget")
        if matrix_mod is not None:
            m = matrix_mod.render_matrix(db=db, cutoff=cutoff, outdir=widgets_out)
            produced["matrix"] = m.get("path")
            emit(f"  bigscape: widget matrix -> {m.get('path')}")
    except Exception as exc:  # non-blocking
        emit(f"  bigscape: matrix widget skipped ({type(exc).__name__}: {exc})", file=sys.stderr)
    try:
        clinker_mod = _imp("bigscape_clinker_widget")
        if clinker_mod is not None:
            c = clinker_mod.render_families(db=db, cutoff=cutoff, outdir=widgets_out)
            produced["clinker"] = c.get("index")
            emit(f"  bigscape: widget clinker -> {c.get('index')}")
    except Exception as exc:  # non-blocking
        emit(f"  bigscape: clinker widget skipped ({type(exc).__name__}: {exc})", file=sys.stderr)
    return produced


# ---- orchestration ------------------------------------------------------------------
def run_pipeline(package=None, runs_dir=None, input_gbk_dir=None,
                 out=None, bigscape_bin=BIGSCAPE_BIN_DEFAULT, pfam=PFAM_DEFAULT,
                 cpus=4, cutoffs=CUTOFFS_DEFAULT, record_type="region",
                 classify="category", work_dir=None, dry_run=False,
                 run_widgets=True, widgets_out=None):
    """Full post-seal BiG-SCAPE step. Returns a result dict:
       {"command": [...], "input_dir": ..., "n_gbks": N, "out": ..., "db": ...|None,
        "widgets": {...}, "dry_run": bool}.
    Never raises for expected failures — prints and returns with db=None instead."""
    out = out or "bigscape_run"
    os.makedirs(out, exist_ok=True)

    # GOTCHA 2: run under a space-free work root; stage input GBKs there. The out dir may have
    # spaces (proven to work), but staging keeps the *input* path space-free (which mattered).
    work_root = work_dir or tempfile.mkdtemp(prefix="bs_work_")
    os.makedirs(work_root, exist_ok=True)
    input_dir = os.path.join(work_root, "input")
    shim_dir = os.path.join(work_root, "_shim_bin")

    mode, items = discover_inputs(package=package, runs_dir=runs_dir, input_gbk_dir=input_gbk_dir)
    n = stage_gbks(mode, items, input_dir)
    emit(f"  bigscape: staged {n} region GBKs -> {input_dir}")

    pfam_use = _stage_no_space(pfam, work_root)

    cmd = build_command(bigscape_bin, input_dir, out, pfam_use, cpus,
                        cutoffs=cutoffs, record_type=record_type, classify=classify)
    result = {"command": cmd, "input_dir": input_dir, "n_gbks": n,
              "out": out, "db": None, "widgets": {}, "dry_run": dry_run}

    emit("  $ " + " ".join(str(c) for c in cmd))
    if dry_run:
        emit("  bigscape: --dry-run, not executing.")
        return result
    if n == 0:
        emit("  bigscape: no region GBKs found; nothing to run.", file=sys.stderr)
        return result

    # GOTCHA 1: make `fasttree` resolvable for the HTML dendrogram step.
    env = dict(os.environ)
    used_shim = ensure_fasttree(bigscape_bin, shim_dir)
    if used_shim:
        env["PATH"] = used_shim + os.pathsep + env.get("PATH", "")

    # Blocking subprocess. The *caller* backgrounds `mamey bigscape` if desired; a short
    # foreground timeout truncates only the HTML write, so we do NOT impose a timeout here.
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        emit(f"  bigscape: cluster exited {proc.returncode} "
              f"(DB may still be usable if only HTML failed).", file=sys.stderr)

    db = locate_db(out)
    result["db"] = db
    if db:
        emit(f"  bigscape: cohort DB -> {db}")
        if run_widgets:
            wout = widgets_out or os.path.join(out, "widgets")
            result["widgets"] = maybe_run_widgets(db, wout,
                                                  cutoff=float(cutoffs.split(",")[0]))
    else:
        emit("  bigscape: no SQLite DB found under the output dir.", file=sys.stderr)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="bigscape_run.py",
        description="Run BiG-SCAPE 2.x on a Mamey package/cohort's region GBKs and chain the "
                    "cohort widgets (post-seal, best-effort, engine-neutral).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--package", help="A single sealed Mamey Complete_Package dir/zip")
    src.add_argument("--runs-dir", help="Cohort dir containing <ID>/package/ (or sealed zips)")
    src.add_argument("--input-gbk-dir", dest="input_gbk_dir",
                     help="Explicit dir of already-extracted antiSMASH region GBKs")
    ap.add_argument("--out", default="bigscape_run", help="Output dir (default: bigscape_run)")
    ap.add_argument("--bigscape", dest="bigscape_bin", default=BIGSCAPE_BIN_DEFAULT,
                    help="BiG-SCAPE 2.x binary (default: the conda bigscape env)")
    ap.add_argument("--pfam", default=PFAM_DEFAULT, help="Pfam-A.hmm (pressed)")
    ap.add_argument("--cpus", type=int, default=4, help="CPU cores (default: 4)")
    ap.add_argument("--cutoffs", default=CUTOFFS_DEFAULT, help="GCF cutoffs (default: 0.3,0.5,0.7)")
    ap.add_argument("--record-type", default="region", dest="record_type")
    ap.add_argument("--classify", default="category")
    ap.add_argument("--work-dir", dest="work_dir", default=None,
                    help="Space-free staging dir (default: a fresh system-temp dir)")
    ap.add_argument("--no-widgets", action="store_false", dest="run_widgets", default=True,
                    help="Skip chaining into the BiG-SCAPE cohort widgets")
    ap.add_argument("--widgets-out", dest="widgets_out", default=None,
                    help="Output dir for the chained widgets (default: <out>/widgets)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the assembled command + staging plan without running BiG-SCAPE")
    a = ap.parse_args(argv)

    res = run_pipeline(package=a.package, runs_dir=a.runs_dir, input_gbk_dir=a.input_gbk_dir,
                       out=a.out, bigscape_bin=a.bigscape_bin, pfam=a.pfam, cpus=a.cpus,
                       cutoffs=a.cutoffs, record_type=a.record_type, classify=a.classify,
                       work_dir=a.work_dir, dry_run=a.dry_run, run_widgets=a.run_widgets,
                       widgets_out=a.widgets_out)
    emit("  GCF = BiG-SCAPE sequence-similarity clustering, class-level only; comparators "
          "are similarity anchors, not identity. Judgment deferred.")
    if a.dry_run:
        return 0
    return 0 if res.get("db") else 1


if __name__ == "__main__":
    sys.exit(main())
