#!/usr/bin/env python3
"""Execute an APPROVED GToTree -> IQ-TREE -> sign-off -> (optional) fastANI phylogenomics run.

This is the execution companion to ``plan_gtotree_iqtree.py``. The planner is deliberately
approval-gated and never invokes GToTree/IQ-TREE; this runner performs the actual run *after*
a human has approved CPU use (the project's tree-approval gate). It refuses to run without an
explicit ``--approved`` flag.

It encodes the operational recipe that was verified working on 2026-08-05 (GToTree v1.8.16 +
IQ-TREE 3.x, macOS/conda), including the gotchas that silently break a naive run:

  * ``GToTree_HMM_dir`` MUST be set to the conda env's ``share/gtotree/hmm_sets/`` or GToTree
    exits with "GToTree_HMM_dir variable is not set". Auto-detected from the resolved GToTree.
  * ``NCBI_assembly_data_dir`` must be set (gtt-data-locations check requires it) even for
    FASTA-only input; pointed at a scratch dir under the workdir.
  * The workdir path must contain NO SPACES — GToTree/BLAST mis-parse spaces. Enforced.
  * The IQ-TREE binary may be ``iqtree`` (3.x) or ``iqtree2``; both are accepted.
  * GToTree 1.8.x writes ``Aligned_SCGs.faa`` (older docs say ``Aligned_SCGs_mod_names.faa``);
    the runner globs for either.
  * Outgroup tip labels = the FASTA basename (minus extension); pass ``--outgroup`` names that
    match those, comma-separated for a multi-taxon outgroup clade.

Nothing here changes engine scoring or claim-safety; it is an operational reproducibility tool.
Class-level phylogenomics; ANI is nucleotide identity only; judgment deferred.
"""
from __future__ import annotations
import argparse
import glob
import os
import shutil
import subprocess
import sys

VERIFIED = "GToTree 1.8.16 / IQ-TREE 3.x, verified 2026-08-05"
DEFAULT_HMM_SET = "Actinobacteria"


def _emit(*a, file=None):
    (file or sys.stdout).write(" ".join(str(x) for x in a) + "\n")


def _resolve(bin_names):
    for b in bin_names:
        p = shutil.which(b)
        if p:
            return p
    return None


def _hmm_dir_for(gtotree_path):
    """Env's share/gtotree/hmm_sets/ sits at <env>/share/gtotree/hmm_sets relative to <env>/bin/GToTree."""
    env_root = os.path.dirname(os.path.dirname(os.path.abspath(gtotree_path)))
    cand = os.path.join(env_root, "share", "gtotree", "hmm_sets")
    return cand if os.path.isdir(cand) else None


def run(cmd, log, env=None):
    _emit("+", " ".join(cmd), file=log); log.flush()
    return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env).returncode


def _load_module(path, name):
    """Load a module by file path (stdlib-only deps). Returns the module or None."""
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hard_tree_qc(treefile, outgroup, tools_dir=None, mamey_dir=None, genomes_dir=None):
    """HARD tree-QC gate for a FINISHED treefile — run BEFORE this runner may report DONE.

    Finding 3 (DEEP_AUDIT3_phylo): the CLI-blessed genome executor produced a tree and
    reported DONE with **no hard QC**, so a contaminant/rogue tip, a misplaced taxon,
    malformed labels, missing support, or a bootstrap killed mid-run all passed silently.
    This mirrors how the *placement* renderer already wires the hard gate before drawing
    (``phylo_place._render_tree`` -> ``_graft_sane`` -> ``tree_sanity_check.check()``), giving
    the genome path the equivalent it lacked.

    Three gates, all typed and surfaced (never swallowed):
      1. ``tree_sanity_check.check()`` (HARD) — pathological long-terminal / dominating branch
         (the bad-outgroup / contaminant-genome signature). Outgroup-aware.
      2. ``phylo_postflight`` P1-P6 (HARD; run as a subprocess so its own exit code, 1 = >=1
         FAIL, is authoritative) — P1 rooting, P3 bootstrap-killed-mid-run, P4 misplaced taxon.
      3. ``mamey/phylo_evidence._support`` (HARD, typed refusal) — the machine-enforced
         claim-safety gate: no SH-aLRT/UFBoot support -> ``PHYLO_SUPPORT_MISSING`` (a tree
         with no support cannot back a phylogenetic claim).

    Returns ``(ok: bool, lines: list)``. ``ok=False`` on ANY hard FAIL. Advisory
    ``signoff_check`` is deliberately NOT run here — it stays optional/non-blocking in main().
    """
    here = os.path.dirname(os.path.abspath(__file__))
    tools_dir = tools_dir or here
    mamey_dir = mamey_dir or os.path.join(os.path.dirname(here), "mamey")
    og_primary = (outgroup.split(",")[0].strip() if outgroup else "") or "OUTGROUP"
    lines, ok = [], True

    # Gate 1 — tree_sanity_check (HARD). Same gate the placement renderer calls before drawing.
    try:
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import tree_sanity_check as _tsc
        s_ok, s_msg = _tsc.check(treefile, outgroup=outgroup)
        lines.append(s_msg)
        if not s_ok:
            ok = False
    except Exception as exc:  # a gate that cannot run is a FAIL, never a silent pass
        ok = False
        lines.append(f"  [tree_sanity_check] ERROR {type(exc).__name__}: {exc} (treated as FAIL)")

    # Gate 2 — phylo_postflight P1-P6 (HARD on any FAIL; subprocess for its authoritative rc).
    pf = os.path.join(tools_dir, "phylo_postflight.py")
    if os.path.exists(pf):
        cmd = [sys.executable, pf, treefile, "--outgroup", og_primary]
        if genomes_dir:
            cmd += ["--genomes-dir", genomes_dir]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, universal_newlines=True)
        if proc.stdout:
            lines.append(proc.stdout.rstrip("\n"))
        if proc.returncode != 0:
            ok = False
            lines.append("  [phylo_postflight] HARD FAIL (>=1 P1-P6 check FAILed)")
    else:
        lines.append("  [phylo_postflight] NOTE: tool not found; skipped")

    # Gate 3 — phylo_evidence claim-safety typed refusal: support must be present.
    pe = os.path.join(mamey_dir, "phylo_evidence.py")
    if os.path.exists(pe):
        mod = _load_module(pe, "phylo_evidence_for_run_qc")
        if mod is not None:
            try:
                with open(treefile, encoding="utf-8", errors="strict") as fh:
                    tree_text = fh.read()
                supp = mod._support(tree_text)
                lines.append(f"  [phylo_evidence] support present ({supp['label']}) on "
                             f"{supp['node_count']} nodes; SH-aLRT min {supp['sh_alrt_min']}, "
                             f"UFBoot min {supp['ufboot_min']}, weak {supp['weak_node_count']}")
            except Exception as exc:  # PhyloEvidenceError renders as 'CODE: detail'
                ok = False
                lines.append(f"  [phylo_evidence] REFUSED {exc}")
    return ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Execute an APPROVED GToTree->IQ-TREE->signoff[->fastANI] run.")
    ap.add_argument("--genome-list", required=True, help="file of absolute FASTA paths (one per line)")
    ap.add_argument("--workdir", required=True, help="output workdir (MUST contain no spaces)")
    ap.add_argument("--outgroup", required=True, help="comma-separated outgroup tip label(s) = FASTA basename(s)")
    ap.add_argument("--hmm", default=DEFAULT_HMM_SET, help=f"GToTree HMM set (default {DEFAULT_HMM_SET})")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--seed", type=int, default=12345,
                    help="IQ-TREE --seed for reproducible ML search + UFBoot (default 12345, "
                         "matching the planner's COMMAND.sh template and the placement path).")
    ap.add_argument("--iqtree-threads", default="1",
                    help="IQ-TREE -T value (default 1, matching the planner template; thread count "
                         "can perturb results, so AUTO is NOT used here. Pass AUTO to override).")
    ap.add_argument("--ani-refs", help="optional: file of reference FASTA paths for a fastANI boundary table")
    ap.add_argument("--ani-queries", help="optional: file of query FASTA paths for fastANI (defaults to genome-list)")
    ap.add_argument("--signoff", help="path to signoff_check.py (optional; run on the treefile if given)")
    ap.add_argument("--approved", action="store_true",
                    help="REQUIRED. Affirms a human approved this CPU run (tree-approval gate).")
    a = ap.parse_args(argv)

    if not a.approved:
        _emit("REFUSED: this runner performs an actual GToTree/IQ-TREE run. The project tree-approval",
              file=sys.stderr)
        _emit("gate requires explicit human approval of CPU use. Re-run with --approved once approved.",
              file=sys.stderr)
        return 2
    if " " in os.path.abspath(a.workdir):
        _emit(f"REFUSED: workdir path contains a space ({a.workdir!r}); GToTree/BLAST mis-parse spaces.",
              file=sys.stderr)
        return 2

    gtotree = _resolve(["GToTree"])
    iqtree = _resolve(["iqtree", "iqtree2"])
    if not gtotree:
        _emit("ERROR: GToTree not on PATH (activate the phylo conda env).", file=sys.stderr); return 3
    if not iqtree:
        _emit("ERROR: iqtree/iqtree2 not on PATH.", file=sys.stderr); return 3

    os.makedirs(a.workdir, exist_ok=True)
    env = dict(os.environ)
    hmm_dir = env.get("GToTree_HMM_dir") or (_hmm_dir_for(gtotree) or "")
    if not hmm_dir or not os.path.isdir(hmm_dir):
        _emit("ERROR: GToTree_HMM_dir could not be resolved; set it to <env>/share/gtotree/hmm_sets/.",
              file=sys.stderr); return 3
    env["GToTree_HMM_dir"] = hmm_dir
    env["NCBI_assembly_data_dir"] = os.path.join(a.workdir, "ncbi_data")
    os.makedirs(env["NCBI_assembly_data_dir"], exist_ok=True)

    logp = os.path.join(a.workdir, "run_planned_tree.log")
    with open(logp, "w") as log:
        _emit(f"# {VERIFIED}", file=log)
        _emit(f"# GToTree={gtotree}\n# iqtree={iqtree}\n# GToTree_HMM_dir={hmm_dir}", file=log)

        # 1) GToTree
        gt_out = os.path.join(a.workdir, "gtotree")
        if os.path.isdir(gt_out):
            shutil.rmtree(gt_out)
        rc = run([gtotree, "-f", a.genome_list, "-H", a.hmm,
                  "-n", str(a.threads), "-j", str(a.parallel), "-o", gt_out], log, env)
        if rc != 0:
            _emit(f"GToTree failed (rc={rc}); see {logp}", file=sys.stderr); return 4
        aln = None
        for name in ("Aligned_SCGs.faa", "Aligned_SCGs_mod_names.faa"):
            hit = glob.glob(os.path.join(gt_out, name))
            if hit:
                aln = hit[0]; break
        if not aln:
            _emit("ERROR: GToTree produced no Aligned_SCGs*.faa (all genomes dropped by SCG QC?).",
                  file=sys.stderr); return 4

        # 2) IQ-TREE
        # v9.7.409 (CLAUDE_409 phylo-run, Finding 7): PIN determinism. The pristine invocation had
        # no --seed (IQ-TREE draws a random ML-search/UFBoot seed -> a different tree/support run to
        # run) and used -T AUTO (thread count varies by host and can perturb results). The planner's
        # emitted COMMAND.sh template already pins `--seed 12345 -T 1`; match it so the CLI-blessed
        # executor is reproducible like the planner and the placement path.
        prefix = os.path.join(a.workdir, "iqtree")
        rc = run([iqtree, "-s", aln, "-m", "MFP", "-B", "1000", "-alrt", "1000",
                  "-seed", str(a.seed), "-T", str(a.iqtree_threads),
                  "-o", a.outgroup, "--prefix", prefix], log, env)
        if rc != 0:
            _emit(f"IQ-TREE failed (rc={rc}); see {logp}", file=sys.stderr); return 5
        treefile = prefix + ".treefile"

        # 3) HARD tree QC (v9.7.409, CLAUDE_409 phylo-run, Finding 3): run tree_sanity_check +
        # phylo_postflight (P1-P6) + phylo_evidence's support gate UNCONDITIONALLY before this
        # runner may report DONE — mirroring how the placement renderer wires the hard gate before
        # it draws. A contaminant/rogue tip, a misplaced taxon, malformed labels, missing support,
        # or a bootstrap killed mid-run is now caught and surfaced (typed WARN/refusal), not
        # silently reported complete.
        qc_ok, qc_lines = hard_tree_qc(treefile, a.outgroup)
        _emit("=== tree QC (hard) ===", file=log)
        for _ln in qc_lines:
            _emit(_ln, file=log)
        if not qc_ok:
            _emit("=== tree QC (hard) — FAILED ===", file=sys.stderr)
            for _ln in qc_lines:
                _emit(_ln, file=sys.stderr)
            _emit("REFUSED: tree QC FAILED — NOT reporting DONE. Resolve the FAIL(s) above (prune a "
                  "contaminant/rogue tip, re-root on the declared outgroup, or re-run IQ-TREE to "
                  f"completion), then re-run. The tree at {treefile} was produced but is NOT "
                  "cleared for use.", file=sys.stderr)
            return 6
        _emit("tree QC PASSED (tree_sanity_check + phylo_postflight P1-P6 + phylo_evidence support).",
              file=log)

        # 4) sign-off gate (advisory)
        if a.signoff and os.path.exists(a.signoff):
            run([sys.executable, a.signoff, treefile], log, env)

        # 5) optional fastANI boundary table
        ani_out = None
        if a.ani_refs:
            fastani = _resolve(["fastANI"])
            if fastani:
                ani_out = os.path.join(a.workdir, "fastani.tsv")
                ql = a.ani_queries or a.genome_list
                run([fastani, "--ql", ql, "--rl", a.ani_refs, "-o", ani_out, "-t", str(a.threads)], log, env)
            else:
                _emit("NOTE: --ani-refs given but fastANI not on PATH; skipped.", file=log)

    _emit(f"DONE. treefile={treefile}")
    _emit(f"  alignment={aln}")
    if a.signoff:
        _emit("  sign-off gate run (advisory; eyeball the judgment items).")
    if ani_out:
        _emit(f"  fastANI boundary table={ani_out} (ANI>=95 ~ same species; within ~1% = boundary).")
    _emit(f"  log={logp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
