#!/usr/bin/env python3
"""Execute an APPROVED GToTree -> IQ-TREE -> sign-off -> (optional) fastANI phylogenomics run.

This is the execution companion to ``plan_gtotree_iqtree.py``. The planner is deliberately
approval-gated and never invokes GToTree/IQ-TREE; this runner performs the actual run *after*
a human has approved CPU use (the project's tree-approval gate). It refuses to run without an
explicit ``--approved`` flag.

It encodes the operational recipe verified on 2026-08-05 (GToTree v1.8.16 + IQ-TREE 3.x) and,
since v9.7.432 (TREES_432 tree round), the GToTree **v2.0.0** recipe verified on 2026-09-15
(``gtotree -f <list> -H <hmm FILE> -j <jobs> -M <muscle threads> ...``), including the gotchas
that silently break a naive run:

  * GToTree v2 has no ``-n``; ``GToTree -n 1`` fails with "unrecognized arguments" before any
    work. The runner probes ``-v`` and builds the version-correct command.
  * v2 needs ``-H`` to be an existing HMM **file** (its own sets are GTDB r232; the project's
    138-gene Actinobacteria set lives in the phylo env). An invalid ``-H`` surfaces only as
    "GToTree_HMM_dir does not seem to be set" — so the file is asserted BEFORE launch, its
    sha256 is recorded (and checked when ``--hmm-sha256`` is given), and ``GToTree_HMM_dir``
    is exported to its directory.
  * v2 hard-refuses a ``-f`` list with a space in any entry; the runner preflights the list
    (missing files, spaces, duplicates) before spending CPU.
  * GToTree's exit code is propagated as-is (typed ``GTOTREE_EXIT rc=<n>``) and recorded in
    ``<workdir>/run_status.json``; no wrapper may mask it as success.
  * GToTree's "too few SCG hits" filter can drop a genome and exit 0. After GToTree the retained
    tips are diffed against the genome list; a dropped QUERY is a hard failure naming the
    genome and quoting its SCG-hit counts (``QUERY_TIP_DROPPED``). Drops are recorded in
    ``<workdir>/DROPPED_BY_QC.tsv``.
  * IQ-TREE is complete only when ``.contree`` exists, the treefile carries support labels and
    the log contains "Total wall-clock time" — a bare ``.treefile`` is INTERRUPTED, never DONE.
  * ``NCBI_assembly_data_dir`` / ``NCBI_ASSEMBLY_DATA_DIR`` (v1 / v2 spellings) are both set.
  * The workdir path must contain NO SPACES — GToTree/BLAST mis-parse spaces. Enforced.
  * The IQ-TREE binary may be ``iqtree`` (3.x) or ``iqtree2``; both are accepted.
  * The alignment is ``Aligned_SCGs.faa`` (1.8) or ``aligned-SCGs.faa`` (2.0); both are found.
  * Outgroup tip labels = the FASTA basename (minus extension); pass ``--outgroup`` names that
    match those, comma-separated for a multi-taxon outgroup clade.

Nothing here changes engine scoring or claim-safety; it is an operational reproducibility tool.
Class-level phylogenomics; ANI is nucleotide identity only; judgment deferred.
"""
from __future__ import annotations
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

VERIFIED = "GToTree 1.8.16 / IQ-TREE 3.x, verified 2026-08-05; GToTree 2.0.0 recipe verified 2026-09-15"
DEFAULT_HMM_SET = "Actinobacteria"
GTOTREE_BINS = ("GToTree", "gtotree")   # 1.8 installs GToTree; 2.0 installs gtotree


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


def gtotree_version(gtotree_path):
    """Probe ``<gtotree> -v``. Returns ``(major: int | None, raw: str)``. ``None`` = unparseable."""
    try:
        proc = subprocess.run([gtotree_path, "-v"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, universal_newlines=True, timeout=60)
        raw = (proc.stdout or "").strip().splitlines()
        raw = raw[0].strip() if raw else ""
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"probe failed: {exc}"
    m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", raw)
    return (int(m.group(1)) if m else None), raw


def gtotree_command(gtotree, major, genome_list, hmm, threads, parallel, out_dir):
    """Version-correct GToTree invocation. v1.8: ``-n <threads> -j <parallel>``; v2.0: no ``-n``,
    ``-M <muscle threads>``, ``-N`` (the runner makes the tree itself so seed/model stay pinned).
    Both take ``-H``; v2 needs a FILE path there (resolve_hmm handles that)."""
    if major is not None and major >= 2:
        return [gtotree, "-f", genome_list, "-H", hmm, "-j", str(parallel), "-M", str(threads),
                "-N", "-o", out_dir]
    return [gtotree, "-f", genome_list, "-H", hmm, "-n", str(threads), "-j", str(parallel), "-o", out_dir]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_hmm(hmm_arg, hmm_dir, expected_sha256=None):
    """Resolve ``--hmm`` (a set name like ``Actinobacteria`` or a path) to an EXISTING ``.hmm`` file.

    Returns ``(hmm_file, hmm_dir, sha256)``; raises ``FileNotFoundError`` (typed ``HMM_PATH_MISSING``)
    when no file exists, ``ValueError`` (``HMM_IDENTITY``) when ``expected_sha256`` does not match.
    The directory of the resolved file becomes ``GToTree_HMM_dir``.
    """
    cands = []
    if os.path.isfile(hmm_arg):
        cands.append(os.path.abspath(hmm_arg))
    if hmm_dir:
        name = os.path.basename(hmm_arg)
        cands.append(os.path.join(hmm_dir, name if name.endswith(".hmm") else name + ".hmm"))
    hit = next((c for c in cands if os.path.isfile(c)), None)
    if hit is None:
        raise FileNotFoundError(
            f"HMM_PATH_MISSING: --hmm {hmm_arg!r} is not an existing file and "
            f"{cands[-1] if cands else '<no GToTree_HMM_dir>'} does not exist. GToTree v2 reports this only "
            "as 'GToTree_HMM_dir does not seem to be set'; refusing before launch.")
    sha = _sha256(hit)
    if expected_sha256:
        exp = expected_sha256.strip().lower()
        if not sha.startswith(exp) and sha != exp:
            raise ValueError(f"HMM_IDENTITY: {hit} sha256 {sha[:16]}... != expected {exp[:16]}...")
    return hit, os.path.dirname(hit), sha


def preflight_genome_list(genome_list, base_dir=None):
    """Errors that GToTree would only report after launch (or mid-run): a missing list, an entry
    with a space (v2 hard-refuses the whole list), a missing FASTA, or a duplicate tip label.
    Returns ``(entries, errors)``; ``errors`` is a list of typed strings, empty when clean."""
    errors = []
    if not os.path.isfile(genome_list):
        return [], [f"GENOME_LIST_MISSING: {genome_list}"]
    base = base_dir or os.path.dirname(os.path.abspath(genome_list))
    with open(genome_list, encoding="utf-8") as fh:
        entries = [ln.rstrip("\n") for ln in fh if ln.strip()]
    if not entries:
        errors.append(f"GENOME_LIST_EMPTY: {genome_list}")
    seen = {}
    for e in entries:
        if " " in e:
            errors.append(f"GENOME_PATH_HAS_SPACE: {e!r} (GToTree v2 refuses the list; rename the staged file)")
        path = e if os.path.isabs(e) else os.path.join(base, e)
        if not os.path.isfile(path):
            errors.append(f"GENOME_FILE_MISSING: {e}")
        tip = _tip_of(e)
        if tip in seen:
            errors.append(f"DUPLICATE_TIP_LABEL: {tip} ({seen[tip]} and {e})")
        seen.setdefault(tip, e)
    return entries, errors


def _tip_of(path):
    name = os.path.basename(path.strip())
    if name.endswith(".gz"):
        name = name[:-3]
    stem, _d, _e = name.rpartition(".")
    return stem or name


def _log_tail(path, n=8):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
        return lines[-n:]
    except OSError:
        return []


def run(cmd, log, env=None):
    _emit("+", " ".join(cmd), file=log); log.flush()
    return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env).returncode


def _write_status(workdir, status, **fields):
    """``<workdir>/run_status.json`` — the typed outcome of this run; written on every exit path
    after the workdir exists so a wrapper can never report a masked success."""
    payload = {"status": status}
    payload.update(fields)
    try:
        with open(os.path.join(workdir, "run_status.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    except OSError as exc:
        fields["run_status_write_error"] = str(exc)  # status could not be persisted; keep it in memory
    return payload


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
    ap.add_argument("--hmm", default=DEFAULT_HMM_SET,
                    help=f"GToTree HMM set name or .hmm file path (default {DEFAULT_HMM_SET}); must resolve "
                         "to an existing file under GToTree_HMM_dir")
    ap.add_argument("--hmm-sha256", help="optional expected sha256 (or prefix) of the resolved HMM file")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--seed", type=int, default=12345,
                    help="IQ-TREE --seed for reproducible ML search + UFBoot (default 12345, "
                         "matching the planner's COMMAND.sh template and the placement path).")
    ap.add_argument("--iqtree-threads", default="1",
                    help="IQ-TREE -T value (default 1, matching the planner template; thread count "
                         "can perturb results, so AUTO is NOT used here. Pass AUTO to override).")
    ap.add_argument("--tree-spec", help="TREE_SPEC.json; its queries/query_tips list declares which tips are queries")
    ap.add_argument("--query-tips", help="comma-separated query tip labels (overrides TREE_SPEC; default: every listed genome)")
    ap.add_argument("--allow-reference-drop", action="store_true",
                    help="let GToTree's SCG filter drop a REFERENCE tip (recorded in DROPPED_BY_QC.tsv); a dropped QUERY always fails")
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

    # Genome-list preflight BEFORE any launch: v2 refuses a spaced entry after printing one line,
    # and a missing FASTA otherwise surfaces mid-run.
    entries, gl_errors = preflight_genome_list(a.genome_list)
    if gl_errors:
        _emit("REFUSED: genome list preflight failed:", file=sys.stderr)
        for e in gl_errors:
            _emit("  " + e, file=sys.stderr)
        return 2
    expected_tips = [_tip_of(e) for e in entries]

    gtotree = _resolve(GTOTREE_BINS)
    iqtree = _resolve(["iqtree", "iqtree2"])
    if not gtotree:
        _emit("ERROR: GToTree/gtotree not on PATH (activate the phylo or gtotree2 conda env).", file=sys.stderr); return 3
    if not iqtree:
        _emit("ERROR: iqtree/iqtree2 not on PATH.", file=sys.stderr); return 3
    major, ver_raw = gtotree_version(gtotree)
    if major is None:
        _emit(f"ERROR: could not parse GToTree version from '{gtotree} -v' ({ver_raw}); refusing to guess flags.",
              file=sys.stderr); return 3

    env = dict(os.environ)
    hmm_dir = env.get("GToTree_HMM_dir") or (_hmm_dir_for(gtotree) or "")
    try:
        hmm_file, hmm_dir, hmm_sha = resolve_hmm(a.hmm, hmm_dir or None, a.hmm_sha256)
    except (FileNotFoundError, ValueError) as exc:
        _emit(f"ERROR: {exc}", file=sys.stderr); return 3
    env["GToTree_HMM_dir"] = hmm_dir.rstrip("/") + "/"

    os.makedirs(a.workdir, exist_ok=True)
    ncbi_dir = os.path.join(a.workdir, "ncbi_data")
    os.makedirs(ncbi_dir, exist_ok=True)
    env["NCBI_assembly_data_dir"] = ncbi_dir            # v1 spelling
    env["NCBI_ASSEMBLY_DATA_DIR"] = ncbi_dir            # v2 spelling
    # v2 exits if Pfam_data_dir is unset; an empty dir is the correct starting state.
    env.setdefault("Pfam_data_dir", os.path.join(a.workdir, "pfam_data") + "/")
    os.makedirs(env["Pfam_data_dir"], exist_ok=True)
    env["PYTHONUNBUFFERED"] = "1"

    here = os.path.dirname(os.path.abspath(__file__))
    gate = _load_module(os.path.join(here, "gtotree_execution_gate.py"), "gtotree_execution_gate_for_runner")
    if gate is None:
        _emit("ERROR: tools/gtotree_execution_gate.py not found beside this runner; the completion and "
              "tip-retention gates cannot run, so the run is refused.", file=sys.stderr); return 3

    logp = os.path.join(a.workdir, "run_planned_tree.log")
    base_status = {"gtotree": gtotree, "gtotree_version": ver_raw, "gtotree_major": major, "iqtree": iqtree,
                   "hmm_file": hmm_file, "hmm_sha256": hmm_sha, "genome_list": os.path.abspath(a.genome_list),
                   "n_genomes": len(entries), "log": logp}
    with open(logp, "w") as log:
        _emit(f"# {VERIFIED}", file=log)
        _emit(f"# GToTree={gtotree} ({ver_raw})\n# iqtree={iqtree}\n# GToTree_HMM_dir={env['GToTree_HMM_dir']}",
              file=log)
        _emit(f"# HMM file={hmm_file} sha256={hmm_sha}", file=log)

        # 1) GToTree
        gt_out = os.path.join(a.workdir, "gtotree")
        if os.path.isdir(gt_out):
            shutil.rmtree(gt_out)
        cmd = gtotree_command(gtotree, major, a.genome_list, hmm_file if major >= 2 else a.hmm,
                              a.threads, a.parallel, gt_out)
        rc = run(cmd, log, env)
        _emit(f"GTOTREE_EXIT rc={rc}", file=log)
        if rc != 0:
            tail = _log_tail(logp)
            _write_status(a.workdir, "GTOTREE_FAILED", gtotree_rc=rc, log_tail=tail, **base_status)
            _emit(f"GTOTREE_EXIT rc={rc} — GToTree failed; see {logp}", file=sys.stderr)
            for ln in tail:
                _emit("  | " + ln, file=sys.stderr)
            return 4
        aln = gate.find_alignment(gt_out)
        if not aln:
            _write_status(a.workdir, "ALIGNMENT_MISSING", gtotree_rc=rc, **base_status)
            _emit("ERROR: ALIGNMENT_MISSING — GToTree exited 0 but produced no "
                  f"{'/'.join(gate.ALIGNMENT_NAMES)} in {gt_out} (all genomes dropped by SCG QC?).",
                  file=sys.stderr); return 4

        # 1b) Tip retention (TREES_432 query-drop card): GToTree's SCG-hit filter drops genomes
        # and still exits 0. Diff the alignment against the genome list; a dropped QUERY is fatal.
        spec = None
        if a.tree_spec and os.path.isfile(a.tree_spec):
            with open(a.tree_spec, encoding="utf-8") as fh:
                spec = json.load(fh)
        qt = [t for t in (a.query_tips or "").split(",") if t.strip()] or None
        queries = gate.declared_query_tips(expected_tips, spec, qt)
        retention = gate.tip_retention(expected_tips, gate.gtotree_retained_tips(gt_out), queries, gt_out,
                                       a.allow_reference_drop)
        _emit(f"=== tip retention: {retention['status']} (runlog says: {retention['runlog_claim']}) ===", file=log)
        for ln in gate.format_dropped(retention):
            _emit(ln, file=log)
        if retention["dropped"]:
            gate.write_dropped_by_qc(os.path.join(a.workdir, "DROPPED_BY_QC.tsv"), retention)
        if retention["status"] not in ("TIPS_RETAINED", "REFERENCE_TIP_DROPPED_ALLOWED"):
            _write_status(a.workdir, retention["status"], gtotree_rc=rc, dropped=retention["dropped"],
                          unexpected=retention["unexpected"], **base_status)
            _emit(f"REFUSED: {retention['status']} — GToTree removed a declared tip and exited 0. "
                  "NOT building a tree without it.", file=sys.stderr)
            for ln in gate.format_dropped(retention):
                _emit(ln, file=sys.stderr)
            _emit(f"  Drops recorded in {os.path.join(a.workdir, 'DROPPED_BY_QC.tsv')}. Review the assembly "
                  "(CheckM2/GUNC) or re-stage; a query cannot be silently absent from its own panel.",
                  file=sys.stderr)
            return 7

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
        _emit(f"IQTREE_EXIT rc={rc}", file=log)
        if rc != 0:
            _write_status(a.workdir, "IQTREE_FAILED", iqtree_rc=rc, log_tail=_log_tail(logp), **base_status)
            _emit(f"IQTREE_EXIT rc={rc} — IQ-TREE failed; see {logp}", file=sys.stderr); return 5
        treefile = prefix + ".treefile"

        # 2b) Completion gate (TREES_432 contree card): .contree + support labels + wall-clock line,
        # or the run is INTERRUPTED regardless of what IQ-TREE's exit code said.
        completion = gate.iqtree_completion(prefix)
        _emit(f"=== IQ-TREE completion: {completion['status']} (support nodes {completion['support_nodes']}) ===",
              file=log)
        for r in completion["reasons"]:
            _emit("  " + r, file=log)
        if completion["status"] != "COMPLETE":
            _write_status(a.workdir, "IQTREE_" + completion["status"], iqtree_rc=rc, completion=completion,
                          **base_status)
            _emit(f"REFUSED: IQ-TREE run is {completion['status']} — NOT reporting DONE.", file=sys.stderr)
            for r in completion["reasons"]:
                _emit("  " + r, file=sys.stderr)
            _emit(f"  last IQ-TREE log line: {completion['last_log_line']!r}", file=sys.stderr)
            _emit(f"  Do NOT render or copy {treefile}; re-run IQ-TREE to completion.", file=sys.stderr)
            return 5

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
            _write_status(a.workdir, "TREE_QC_FAILED", qc=qc_lines, treefile=treefile, **base_status)
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

    _write_status(a.workdir, "DONE", treefile=treefile, contree=completion["contree"], alignment=aln,
                  support_nodes=completion["support_nodes"], tip_retention=retention["status"],
                  dropped=retention["dropped"], fastani=ani_out, **base_status)
    _emit(f"DONE. treefile={treefile}")
    _emit(f"  contree={completion['contree']} (support on {completion['support_nodes']} nodes)")
    _emit(f"  alignment={aln}")
    _emit(f"  tip retention: {retention['status']}")
    if a.signoff:
        _emit("  sign-off gate run (advisory; eyeball the judgment items).")
    if ani_out:
        _emit(f"  fastANI boundary table={ani_out} (ANI>=95 ~ same species; within ~1% = boundary).")
    _emit(f"  log={logp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
