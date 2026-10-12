#!/usr/bin/env python3
"""Execute an APPROVED GToTree -> IQ-TREE -> sign-off -> (optional) fastANI phylogenomics run.

This is the execution companion to ``plan_gtotree_iqtree.py``. The planner is deliberately
approval-gated and never invokes GToTree/IQ-TREE; this runner performs the actual run *after*
a human has approved CPU use (the project's tree-approval gate). It refuses to run without an
explicit ``--approved`` flag.

Historical operational recipes included GToTree v1.8.16, now refused by shared policy, and,
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
import tempfile
from pathlib import Path

VERIFIED = "GToTree interface policy: 1.8.19 or 2.0.x; installed version/help and exact HMM bound per run"
DEFAULT_HMM_SET = "Actinobacteria"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gtotree_versions as _gtotree_policy  # noqa: E402
from _gtotree_versions import (  # noqa: E402
    GTOTREE_BINS, accepted as _gtotree_accepted, command as _gtotree_command,
    probe as gtotree_probe,
)


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
    """Compatibility tuple from the complete admitted version/help probe."""
    result = gtotree_probe(gtotree_path)
    return (result.get("major") if result["verified_interface"] == "PASS" else None,
            result.get("version") or result.get("error") or "probe failed")


def gtotree_command(gtotree, version_text, genome_list, hmm, threads, parallel, out_dir):
    """Delegate exact admitted version and explicit resources to the shared owner."""
    return _gtotree_command(gtotree, version_text, genome_list, hmm, threads, parallel, out_dir)


# v9.7.444: docs/GTOTREE_WORKFLOW.md section 5 prescribes this restricted ModelFinder search for the protein
# supermatrix ("bare -m MFP never finishes on ~30k cols"). The runner used bare -m MFP: on the 87-genome insect-set
# v5 alignment (20,910 columns) ModelFinder tested 24 of up to 1,232 models in about 2 hours.
DOCUMENTED_MODEL_SEARCH = ["-m", "MFP", "-mset", "LG,WAG,JTT,Q.pfam", "-mrate", "G,I,I+G"]


def iqtree_command(iqtree, aln, prefix, seed, threads, outgroup, model=""):
    """IQ-TREE invocation. ``model`` empty = the documented restricted search; 'MFP' = unrestricted
    ModelFinder; anything else = that fixed model (e.g. LG+F+G4)."""
    model_args = DOCUMENTED_MODEL_SEARCH if not model else ["-m", model]
    return [iqtree, "-s", aln, *model_args, "-B", "1000", "-alrt", "1000",
            "-seed", str(seed), "-T", str(threads), "-o", outgroup, "--prefix", prefix]


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


def preflight_fresh_workdir(workdir, input_paths):
    """Admit a new output root without mutating any path; this is not a resume API."""
    lexical = Path(os.path.abspath(workdir))
    for parent in (lexical, *lexical.parents):
        if parent.is_symlink():
            raise ValueError("WORKDIR_SYMLINK: output root or ancestor is a symlink")
        if parent.exists() and not parent.is_dir():
            raise ValueError("WORKDIR_PARENT_NOT_DIRECTORY: " + str(parent))
    resolved = lexical.resolve()
    if lexical.exists():
        raise ValueError("WORKDIR_OCCUPIED: use a fresh output directory; existing evidence is preserved")
    for supplied in input_paths:
        selected = Path(supplied).resolve(strict=True)
        if not selected.is_file():
            raise ValueError("INPUT_NOT_REGULAR_FILE: " + str(supplied))
        if selected == resolved or resolved in selected.parents or selected in resolved.parents:
            raise ValueError("WORKDIR_INPUT_OVERLAP: " + str(supplied))
    return str(resolved)


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
        with open(os.path.join(workdir, "run_status.json"), "x", encoding="utf-8") as fh:
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


def hard_tree_qc(treefile, outgroup, tools_dir=None, mamey_dir=None, genomes_dir=None, *, launch=None, log=None, env=None):
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

    # Gate 1 — require the gate from this tree, not a cached module from another copy.
    try:
        sanity_path = os.path.join(tools_dir, "tree_sanity_check.py")
        if not os.path.isfile(sanity_path):
            raise FileNotFoundError("mandatory gate module missing: " + sanity_path)
        _tsc = _load_module(sanity_path, "tree_sanity_check_for_run_qc")
        if _tsc is None:
            raise RuntimeError("mandatory gate module loader returned None")
        s_ok, s_msg = _tsc.check(treefile, outgroup=outgroup)
        lines.append(s_msg)
        if not s_ok:
            ok = False
    except Exception as exc:
        ok = False
        lines.append(f"  [tree_sanity_check] ERROR {type(exc).__name__}: {exc} (treated as FAIL)")

    # Gate 2 — absent/unlaunchable postflight is a hard failure, like a nonzero exit.
    pf = os.path.join(tools_dir, "phylo_postflight.py")
    try:
        if not os.path.isfile(pf):
            raise FileNotFoundError("mandatory gate module missing: " + pf)
        cmd = [sys.executable, pf, treefile, "--outgroup", og_primary]
        if genomes_dir:
            cmd += ["--genomes-dir", genomes_dir]
        if launch is None:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, universal_newlines=True)
        else:
            from types import SimpleNamespace
            rc = launch(cmd, log, env)
            watched_log = launch.root / ("watch_%03d.log" % launch.count)
            with watched_log.open(encoding="utf-8", errors="replace") as f:
                diagnostic = f.read(65536)
            proc = SimpleNamespace(returncode=rc, stdout=diagnostic)
        if proc.stdout:
            lines.append(proc.stdout.rstrip("\n"))
        if proc.returncode != 0:
            ok = False
            lines.append(f"  [phylo_postflight] HARD FAIL rc={proc.returncode} (>=1 P1-P6 check FAILed)")
    except Exception as exc:
        ok = False
        lines.append(f"  [phylo_postflight] ERROR {type(exc).__name__}: {exc} (treated as FAIL)")

    # Gate 3 — absence, import/loader failure and support refusal all fail explicitly.
    pe = os.path.join(mamey_dir, "phylo_evidence.py")
    try:
        if not os.path.isfile(pe):
            raise FileNotFoundError("mandatory gate module missing: " + pe)
        mod = _load_module(pe, "phylo_evidence_for_run_qc")
        if mod is None:
            raise RuntimeError("mandatory gate module loader returned None")
        with open(treefile, encoding="utf-8", errors="strict") as fh:
            tree_text = fh.read()
        supp = mod._support(tree_text)
        lines.append(f"  [phylo_evidence] support present ({supp['label']}) on "
                     f"{supp['node_count']} nodes; SH-aLRT min {supp['sh_alrt_min']}, "
                     f"UFBoot min {supp['ufboot_min']}, weak {supp['weak_node_count']}")
    except Exception as exc:
        ok = False
        lines.append(f"  [phylo_evidence] REFUSED {type(exc).__name__}: {exc}")
    return ok, lines


def _run_requested_fastani(refs, queries, workdir, threads, log, env, *, launch=None, executable=None):
    """Operational stage receipt; no ANI threshold/content interpretation is added."""
    stage = {"requested": True, "status": "FASTANI_LAUNCH_FAILED", "returncode": None,
             "references": refs, "queries": queries, "output": None}
    failure_status = "FASTANI_LAUNCH_FAILED"
    try:
        fastani = executable or _resolve(["fastANI"])
        stage["executable"] = fastani
        if not fastani:
            stage.update(status="FASTANI_UNAVAILABLE", detail="requested fastANI executable is not on PATH")
            return stage
        # A fresh attempt path cannot mistake a prior fastani.tsv for this run's output.
        # Keep prior ANI/core-tree files until a current output is ready to publish.
        attempt_dir = tempfile.mkdtemp(prefix=".fastani_attempt_", dir=workdir)
        attempt = os.path.join(attempt_dir, "fastani.tsv")
        stage["attempted_output"] = attempt
        cmd = [fastani, "--ql", queries, "--rl", refs, "-o", attempt, "-t", str(threads)]
        stage["command"] = cmd
        rc = (launch or run)(cmd, log, env)
        stage["returncode"] = rc
        _emit(f"FASTANI_EXIT rc={rc}", file=log)
        if rc != 0:
            stage.update(status="FASTANI_FAILED", detail="requested fastANI exited nonzero")
            return stage
        if not os.path.isfile(attempt):
            stage.update(status="FASTANI_OUTPUT_MISSING", detail="fastANI exited zero without a current output file")
            return stage
        failure_status = "FASTANI_OUTPUT_VALIDATION_FAILED"
        output_sha = _sha256(attempt)
        output = os.path.join(workdir, "fastani.tsv")
        failure_status = "FASTANI_OUTPUT_PUBLISH_FAILED"
        os.replace(attempt, output)
        stage.update(status="DONE", output=output, output_sha256=output_sha)
        return stage
    except Exception as exc:
        stage.update(status=failure_status, detail=f"{type(exc).__name__}: {exc}")
        return stage


def validate_plan_binding(args, entries, tips, runtime, gtotree, iqtree):
    from _gtotree_runtime import APPROVED_MANIFEST_SHA256, require_verified
    require_verified(runtime, gtotree)
    root = Path(args.plan_dir).resolve(strict=True)
    manifest = json.loads((root / "RUN_MANIFEST.json").read_text())
    state = json.loads((root / "RUN_STATE.json").read_text())
    if state.get("approved") is not True or state.get("run_id") != manifest.get("run_id"):
        raise ValueError("PLAN_APPROVAL_REQUIRED")
    binding = manifest["runtime_binding"]
    if (binding["manifest_sha256"] != APPROVED_MANIFEST_SHA256 or
            Path(binding["manifest"]).resolve() != Path(args.gtotree_runtime_manifest).resolve() or
            Path(binding["environment"]).resolve() != Path(args.gtotree_runtime_environment).resolve() or
            Path(binding["editable_source"]).resolve() != Path(args.gtotree_runtime_source).resolve()):
        raise ValueError("PLAN_RUNTIME_BINDING")
    rows = manifest["assemblies"]
    planned = _gtotree_policy.plan_mapping_rows(rows, manifest["toolchain"]["gtotree"]["version"])
    layout = _gtotree_policy.governed_paths(root, manifest.get("execution_layout"))
    if (Path(args.workdir).resolve() != layout["workdir_relative"] or
            Path(args.genome_list).resolve() != root / "input_view/genomes_absolute.txt"):
        raise ValueError("PLAN_OUTPUT_BINDING")
    if [str(Path(e).resolve()) for e in entries] != [str(Path(r["object_path"]).resolve()) for r in rows]:
        raise ValueError("PLAN_INPUT_ROSTER")
    for row in rows:
        if _sha256(row["object_path"]) != row["object_sha256"]:
            raise ValueError("PLAN_INPUT_IDENTITY")
    mapping = [line.split("\t") for line in (root / "input_view/labels.tsv").read_text().splitlines()]
    if mapping != [[name, label] for name, label, role in planned]:
        raise ValueError("PLAN_MAPPING_BINDING")
    bound_tips = [label for name, label, role in planned]
    if (tips != bound_tips or Path(args.mapping_file).resolve() != root / "input_view/labels.tsv" or
            (args.query_tips or "").split(",") != [t for t,r in zip(tips,rows) if r["role"] == "QUERY"] or
            args.outgroup.split(",") != [t for t,r in zip(tips,rows) if r["role"] == "OUTGROUP"]):
        raise ValueError("PLAN_TIP_ROLE_BINDING")
    resources = manifest["resource_policy"]
    if (args.threads != resources["muscle_threads"] or args.parallel != resources["gtotree_jobs"] or
            int(args.iqtree_threads) != resources["iqtree_threads_per_tree"] or
            args.gtotree_cpu_budget != resources["maximum_concurrent_cores"] or
            Path(gtotree).resolve() != Path(manifest["toolchain"]["gtotree"]["path"]).resolve() or
            Path(iqtree).resolve() != Path(manifest["toolchain"]["iqtree"]["path"]).resolve() or
            _sha256(args.hmm) != manifest["hmm"]["sha256"]):
        raise ValueError("PLAN_TOOL_OR_RESOURCE_BINDING")
    return {"schema": "GTOTREE_GOVERNED_PLAN_BINDING_V1", "plan_directory": str(root),
            "manifest_sha256": _sha256(root / "RUN_MANIFEST.json"),
            "state_sha256": _sha256(root / "RUN_STATE.json"),
            "genome_list": str(Path(args.genome_list).resolve()),
            "genome_list_sha256": _sha256(args.genome_list),
            "mapping": str(Path(args.mapping_file).resolve()),
            "mapping_sha256": _sha256(args.mapping_file),
            "workdir": str(layout["workdir_relative"])}


def completed_artifact(path, workdir):
    """Bind a current producer output; this is not a cross-file transaction."""
    root = Path(workdir).resolve(strict=True)
    p = Path(path).absolute()
    if (not p.is_file() or root not in p.resolve().parents or
            any(q.is_symlink() for q in (p, *p.parents))):
        raise ValueError("EXECUTION_OUTPUT_IDENTITY")
    return {"path": str(p), "sha256": _sha256(p), "bytes": p.stat().st_size}


def mapped_tips(entries, mapping_file=None, *, version_text="1.8.19"):
    """Retain default tips; explicit version-specific mapping must cover every input."""
    if not mapping_file:
        return [_tip_of(e) for e in entries]
    mapping = {}
    with open(mapping_file, encoding="utf-8") as f:
        for line in f:
            cells = line.rstrip("\n").split("\t")
            if len(cells) != 2 or not all(cells) or cells[0] in mapping or cells[1] in mapping.values():
                raise ValueError("GTOTREE_MAPPING_IDENTITY")
            # GToTree labels become Newick/FASTA tips; whitespace and grammar chars are unsafe.
            if any(ch.isspace() or ch in "():,;[]'\"" for ch in cells[1]):
                raise ValueError("GTOTREE_MAPPING_UNSAFE_TIP")
            mapping[cells[0]] = cells[1]
    keys = _gtotree_policy.mapping_input_keys(entries, version_text)
    if set(mapping) != set(keys):
        raise ValueError("GTOTREE_MAPPING_ROSTER")
    return [mapping[key] for key in keys]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Execute an APPROVED GToTree->IQ-TREE->signoff[->fastANI] run.")
    ap.add_argument("--genome-list", required=True, help="file of absolute FASTA paths (one per line)")
    ap.add_argument("--workdir", required=True, help="fresh, absent output workdir (MUST contain no spaces); existing directories are refused")
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
    ap.add_argument("--iqtree-model", default="",
                    help="IQ-TREE model. Default: the documented restricted ModelFinder search "
                         "(-m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G; docs/GTOTREE_WORKFLOW.md section 5). "
                         "'MFP' = unrestricted search (slow on large alignments); anything else = that fixed model.")
    ap.add_argument("--tree-spec", help="TREE_SPEC.json; its queries/query_tips list declares which tips are queries")
    ap.add_argument("--query-tips", help="comma-separated query tip labels (overrides TREE_SPEC; default: every listed genome)")
    ap.add_argument("--allow-reference-drop", action="store_true",
                    help="let GToTree's SCG filter drop a REFERENCE tip (recorded in DROPPED_BY_QC.tsv); a dropped QUERY always fails")
    ap.add_argument("--ani-refs", help="optional: file of reference FASTA paths for a fastANI boundary table")
    ap.add_argument("--ani-queries", help="optional: file of query FASTA paths for fastANI (defaults to genome-list)")
    ap.add_argument("--signoff", help="path to signoff_check.py (optional; run on the treefile if given)")
    ap.add_argument("--approved", action="store_true",
                    help="REQUIRED. Affirms a human approved this CPU run (tree-approval gate).")
    from _gtotree_runtime import (add_runtime_arguments, runtime_from_arguments,
        verified_interface, resource_pass, RuntimeRefused, WatchedLaunch)
    add_runtime_arguments(ap)
    ap.add_argument("--gtotree-bin", help="explicit selected GToTree launcher")
    ap.add_argument("--iqtree-bin", help="explicit selected IQ-TREE executable")
    ap.add_argument("--mapping-file", help="exact headerless two-column TSV: v1 basename or v2 exact supplied input path to tip")
    ap.add_argument("--plan-dir", help="frozen planner directory; requires its recorded approval and exact roster")
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
    # Admit the complete selected input roster before any output creation.
    input_roster = [a.genome_list] + [
        e if os.path.isabs(e) else os.path.join(os.path.dirname(os.path.abspath(a.genome_list)), e)
        for e in entries]
    for selected in (a.tree_spec, a.signoff, a.mapping_file):
        if selected:
            input_roster.append(selected)
    for selected in (a.ani_refs, a.ani_queries):
        if selected:
            ani_entries, ani_errors = preflight_genome_list(selected)
            if ani_errors:
                for detail in ani_errors:
                    _emit("REFUSED: ANI_INPUT_" + detail, file=sys.stderr)
                return 2
            input_roster += [selected] + [
                e if os.path.isabs(e) else os.path.join(os.path.dirname(os.path.abspath(selected)), e)
                for e in ani_entries]
    try:
        a.workdir = preflight_fresh_workdir(a.workdir, input_roster)
    except (OSError, ValueError) as exc:
        _emit("REFUSED: " + str(exc), file=sys.stderr)
        return 2

    spec = None
    if a.tree_spec:
        try:
            with open(a.tree_spec, encoding="utf-8") as fh:
                spec = json.load(fh)
            if not isinstance(spec, dict):
                raise ValueError("TREE_SPEC_INVALID: JSON object required")
        except (OSError, ValueError) as exc:
            _emit("REFUSED: TREE_SPEC_INVALID: " + str(exc), file=sys.stderr)
            return 2
    gtotree = os.path.abspath(a.gtotree_bin) if a.gtotree_bin else _resolve(GTOTREE_BINS)
    iqtree = os.path.abspath(a.iqtree_bin) if a.iqtree_bin else _resolve(["iqtree", "iqtree2"])
    if not gtotree:
        _emit("ERROR: GToTree/gtotree not on PATH (activate the phylo or gtotree2 conda env).", file=sys.stderr); return 3
    if not iqtree:
        _emit("ERROR: iqtree/iqtree2 not on PATH.", file=sys.stderr); return 3
    try:
        runtime = runtime_from_arguments(a, gtotree)
        gt_probe = verified_interface(runtime, gtotree) if runtime else gtotree_probe(gtotree)
    except (OSError, ValueError) as exc:
        _emit("REFUSED: " + str(exc), file=sys.stderr)
        return 3
    ver_raw = str(gt_probe.get("version") or "")
    if gt_probe.get("verified_interface") != "PASS" or not _gtotree_accepted(ver_raw):
        _emit("REFUSED: GTOTREE_INTERFACE: " + json.dumps(gt_probe, sort_keys=True),
              file=sys.stderr)
        return 3
    # Mapping keys depend on the successfully admitted native interface. This is
    # still before output creation or any genome/model child (software probe only).
    try:
        expected_tips = mapped_tips(entries, a.mapping_file, version_text=ver_raw)
    except (OSError, ValueError) as exc:
        _emit("REFUSED: " + str(exc), file=sys.stderr)
        return 2
    plan_binding = None
    if a.plan_dir:
        try:
            plan_binding = validate_plan_binding(a, entries, expected_tips, runtime, gtotree, iqtree)
            input_roster += [os.path.join(a.plan_dir, name) for name in
                             ("RUN_MANIFEST.json", "RUN_STATE.json")]
        except (OSError, ValueError, KeyError) as exc:
            _emit("REFUSED: PLAN_BINDING: " + str(exc), file=sys.stderr)
            return 3
    major = gt_probe["major"]
    try:
        gt_resources = (_gtotree_policy.resource_contract(ver_raw, a.threads, a.parallel,
            verified_runtime=runtime, cpu_budget=a.gtotree_cpu_budget) if runtime else
            _gtotree_policy.resource_contract(ver_raw, a.threads, a.parallel))
        if runtime:
            iq_threads = int(a.iqtree_threads)
            if (iq_threads < 1 or iq_threads > a.gtotree_cpu_budget or
                    iq_threads > gt_resources["cpu_count_observed"]):
                raise RuntimeRefused("GTOTREE_IQTREE_CPU_BUDGET")
    except ValueError as exc:
        _emit("REFUSED: " + str(exc), file=sys.stderr)
        return 3
    if not resource_pass(gt_resources):
        _emit("REFUSED: GTOTREE_RESOURCE_PROFILE: " + json.dumps(gt_resources, sort_keys=True),
              file=sys.stderr)
        return 3

    env = runtime.native_environment() if runtime else dict(os.environ)
    hmm_dir = env.get("GToTree_HMM_dir") or (_hmm_dir_for(gtotree) or "")
    try:
        hmm_file, hmm_dir, hmm_sha = resolve_hmm(a.hmm, hmm_dir or None, a.hmm_sha256)
    except (FileNotFoundError, ValueError) as exc:
        _emit(f"ERROR: {exc}", file=sys.stderr); return 3
    env["GToTree_HMM_dir"] = hmm_dir.rstrip("/") + "/"

    inherited_pfam = env.get("Pfam_data_dir")
    if inherited_pfam and not os.path.isdir(inherited_pfam):
        _emit("REFUSED: PFAM_INPUT_DIRECTORY_MISSING: selected Pfam_data_dir must already exist", file=sys.stderr)
        return 2
    # Recheck the full roster, including the resolved HMM, before making parents.
    try:
        a.workdir = preflight_fresh_workdir(a.workdir, input_roster + [hmm_file])
    except (OSError, ValueError) as exc:
        _emit("REFUSED: " + str(exc), file=sys.stderr)
        return 2
    env["PYTHONUNBUFFERED"] = "1"

    here = os.path.dirname(os.path.abspath(__file__))
    gate = _load_module(os.path.join(here, "gtotree_execution_gate.py"), "gtotree_execution_gate_for_runner")
    if gate is None:
        _emit("ERROR: tools/gtotree_execution_gate.py not found beside this runner; the completion and "
              "tip-retention gates cannot run, so the run is refused.", file=sys.stderr); return 3

    qt = [t for t in (a.query_tips or "").split(",") if t.strip()] or None
    try:
        if a.mapping_file and qt is not None:
            # These are exact admitted labels, not genome filenames. A dot or
            # accession version is part of identity and must not be stemmed.
            queries = set(qt)
            if len(queries) != len(qt) or not queries.issubset(set(expected_tips)):
                raise ValueError("MAPPED_QUERY_TIP_IDENTITY")
        else:
            queries = gate.declared_query_tips(expected_tips, spec, qt)
    except (TypeError, ValueError) as exc:
        _emit("REFUSED: QUERY_DECLARATION_INVALID: " + str(exc), file=sys.stderr)
        return 2
    # Exclusive root creation preserves occupied destinations, including a late race.
    try:
        os.makedirs(a.workdir, exist_ok=False)
    except OSError as exc:
        _emit("REFUSED: WORKDIR_CREATE_FAILED: " + str(exc), file=sys.stderr)
        return 2
    ncbi_dir = os.path.join(a.workdir, "ncbi_data")
    os.mkdir(ncbi_dir)
    env["NCBI_assembly_data_dir"] = ncbi_dir
    env["NCBI_ASSEMBLY_DATA_DIR"] = ncbi_dir
    if not inherited_pfam:
        env["Pfam_data_dir"] = os.path.join(a.workdir, "pfam_data") + "/"
        os.mkdir(env["Pfam_data_dir"])
    # Existing external Pfam input is reused, never mkdir'ed by this owner.
    logp = os.path.join(a.workdir, "run_planned_tree.log")
    launch = run
    fastani_executable = None
    if runtime:
        fastani_executable = _resolve(["fastANI"]) if a.ani_refs else None
        if a.ani_refs and not fastani_executable:
            _write_status(a.workdir, "FASTANI_UNAVAILABLE")
            _emit("REFUSED: requested fastANI executable is unavailable", file=sys.stderr)
            return 8
        executables = [gtotree, iqtree, sys.executable]
        if fastani_executable:
            executables.append(fastani_executable)
        bound_sources = [__file__, os.path.join(here, "gtotree_execution_gate.py"),
            os.path.join(here, "_gtotree_runtime.py"), os.path.join(here, "_gtotree_versions.py"),
            os.path.join(here, "_release_validation.py"), os.path.join(here, "phylo_postflight.py"),
            os.path.join(here, "tree_sanity_check.py"),
            os.path.join(here, "_wbio.py"), os.path.join(here, "phylo_preflight.py"),
            os.path.join(here, "_console.py"),
            os.path.join(os.path.dirname(here), "mamey", "__init__.py"),
            os.path.join(os.path.dirname(here), "mamey", "outgroup_registry_path.py"),
            os.path.join(os.path.dirname(here), "mamey", "phylo_evidence.py")]
        try:
            launch = WatchedLaunch(runtime, a.workdir, input_roster + [hmm_file] + bound_sources,
                executables, rss_limit=a.gtotree_rss_limit, min_disk=a.gtotree_min_disk,
                timeout=a.gtotree_timeout)
        except (OSError, ValueError) as exc:
            _write_status(a.workdir, "EXECUTION_BINDING_FAILED", detail=str(exc))
            return 3
    base_status = {"gtotree": gtotree, "gtotree_version": ver_raw, "gtotree_major": major,
                   "gtotree_probe": gt_probe, "gtotree_resource_contract": gt_resources, "iqtree": iqtree,
                   "hmm_file": hmm_file, "hmm_sha256": hmm_sha, "genome_list": os.path.abspath(a.genome_list),
                   "n_genomes": len(entries), "log": logp}
    if runtime:
        base_status["execution_phases"] = launch.receipts
        base_status["execution_bindings_sha256"] = _sha256(os.path.join(a.workdir, "EXECUTION_BINDINGS.json"))
        base_status["plan_binding"] = plan_binding
    with open(logp, "x") as log:
        _emit(f"# {VERIFIED}", file=log)
        _emit(f"# GToTree={gtotree} ({ver_raw})\n# iqtree={iqtree}\n# GToTree_HMM_dir={env['GToTree_HMM_dir']}",
              file=log)
        _emit(f"# HMM file={hmm_file} sha256={hmm_sha}", file=log)

        # 1) GToTree
        gt_out = os.path.join(a.workdir, "gtotree")
        cmd = gtotree_command(gtotree, ver_raw, a.genome_list, hmm_file,
                              a.threads, a.parallel, gt_out)
        if a.mapping_file:
            cmd.extend(["-m", os.path.abspath(a.mapping_file)])
        # Version/executable observations are watched and bound independently of the source profile.
        if runtime:
            tool_versions = []
            for software_cmd in ([iqtree, "--version"],
                                 *([[fastani_executable, "--version"]] if fastani_executable else [])):
                if launch(software_cmd, log, env):
                    _write_status(a.workdir, "EXECUTION_TOOL_PROBE_FAILED", **base_status)
                    return 3
                phase_log = launch.root / ("watch_%03d.log" % launch.count)
                if phase_log.stat().st_size > 65536:
                    _write_status(a.workdir, "EXECUTION_VERSION_TEXT_LIMIT", **base_status)
                    return 3
                tool_versions.append({"executable": software_cmd[0],
                    "executable_sha256": _sha256(software_cmd[0]), "argv": software_cmd,
                    "observed_stdout_stderr": phase_log.read_text(encoding="utf-8", errors="replace"),
                    "log_sha256": _sha256(phase_log), "phase_receipt": launch.receipts[-1]})
            version_path = os.path.join(a.workdir, "TOOL_VERSIONS.json")
            with open(version_path, "x", encoding="utf-8") as f:
                json.dump(tool_versions, f, indent=2)
            base_status["tool_versions_sha256"] = _sha256(version_path)
        rc = launch(cmd, log, env)
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
        retained_tips = gate.gtotree_retained_tips(gt_out)
        retention = gate.tip_retention(expected_tips, retained_tips, queries, gt_out,
                                       a.allow_reference_drop)
        if retention["status"] in ("TIPS_RETAINED", "REFERENCE_TIP_DROPPED_ALLOWED"):
            if retention["unexpected"]:
                retention["status"] = "UNEXPECTED_ALIGNMENT_TIP"
            elif retained_tips is not None and len(retained_tips) != len(set(retained_tips)):
                retention["status"] = "DUPLICATE_ALIGNMENT_TIP"
                retention["duplicates"] = sorted({tip for tip in retained_tips if retained_tips.count(tip) > 1})
        _emit(f"=== tip retention: {retention['status']} (runlog says: {retention['runlog_claim']}) ===", file=log)
        for ln in gate.format_dropped(retention):
            _emit(ln, file=log)
        if retention["dropped"]:
            gate.write_dropped_by_qc(os.path.join(a.workdir, "DROPPED_BY_QC.tsv"), retention)
        if retention["status"] not in ("TIPS_RETAINED", "REFERENCE_TIP_DROPPED_ALLOWED"):
            _write_status(a.workdir, retention["status"], gtotree_rc=rc, dropped=retention["dropped"],
                          unexpected=retention["unexpected"], duplicates=retention.get("duplicates", []), **base_status)
            if retention["status"] in ("UNEXPECTED_ALIGNMENT_TIP", "DUPLICATE_ALIGNMENT_TIP"):
                _emit(f"REFUSED: {retention['status']} — current alignment does not preserve the declared "
                      "unique tip roster. NOT building a tree from this alignment.", file=sys.stderr)
            else:
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
        rc = launch(iqtree_command(iqtree, aln, prefix, a.seed, a.iqtree_threads, a.outgroup,
                                getattr(a, "iqtree_model", "")), log, env)
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
        qc_ok, qc_lines = (hard_tree_qc(treefile, a.outgroup, launch=launch, log=log, env=env)
                           if runtime else hard_tree_qc(treefile, a.outgroup))
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
            launch([sys.executable, a.signoff, treefile], log, env)

        # 5) Optional until requested; a requested incomplete stage fails the overall run.
        ani_out = None
        ani_fields = {}
        if a.ani_refs:
            stage = (_run_requested_fastani(a.ani_refs, a.ani_queries or a.genome_list,
                                          a.workdir, a.threads, log, env,
                                          launch=launch, executable=fastani_executable) if runtime else
                     _run_requested_fastani(a.ani_refs, a.ani_queries or a.genome_list,
                                          a.workdir, a.threads, log, env))
            ani_fields["fastani_stage"] = stage
            _emit(f"FASTANI_STAGE status={stage['status']} rc={stage['returncode']} "
                  f"detail={stage.get('detail', '')}", file=log)
            if stage["status"] != "DONE":
                _write_status(a.workdir, stage["status"], treefile=treefile,
                              contree=completion["contree"], alignment=aln,
                              support_nodes=completion["support_nodes"],
                              tip_retention=retention["status"], dropped=retention["dropped"],
                              core_tree_status="TREE_QC_PASSED", qc=qc_lines,
                              fastani=None, **ani_fields, **base_status)
                _emit(f"REFUSED: {stage['status']} — requested fastANI stage did not complete. "
                      f"Core-tree artifacts retained; see {logp} and run_status.json.", file=sys.stderr)
                return 8
            ani_out = stage["output"]

    if runtime:
        try:
            launch.revalidate()
            if launch.resource_failed:
                raise RuntimeRefused("GTOTREE_EXECUTION_RESOURCE_FAILURE")
            artifacts = {name: completed_artifact(path, a.workdir) for name, path in
                         (("alignment", aln), ("treefile", treefile),
                          ("contree", completion["contree"]), ("iqtree_log", completion["log"]))}
            summary = os.path.join(gt_out, gate.V2_GENOME_SUMMARY)
            # Missing native summary does not change the existing runner's hard-QC semantics.
            # Discovery requires it and will HOLD rather than invent its denominator.
            artifacts["genome_summary"] = (completed_artifact(summary, a.workdir)
                                            if os.path.lexists(summary) else None)
            if ani_out:
                artifacts["fastani"] = completed_artifact(ani_out, a.workdir)
            base_status["completed_artifacts"] = artifacts
        except (OSError, ValueError) as exc:
            _write_status(a.workdir, "EXECUTION_BINDING_DRIFT", detail=str(exc), **base_status)
            return 3
    _write_status(a.workdir, "DONE", treefile=treefile, contree=completion["contree"], alignment=aln,
                  support_nodes=completion["support_nodes"], tip_retention=retention["status"],
                  dropped=retention["dropped"], fastani=ani_out, **ani_fields, **base_status)
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
