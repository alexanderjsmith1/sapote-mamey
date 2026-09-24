#!/usr/bin/env python3
"""bigscape_pipeline.py -- one-command BiG-SCAPE GCF layer for a Mamey cohort.

Closes the full loop the workflow doc describes as prep -> run -> ingest, end to end:

  antiSMASH zips / sealed Mamey packages
        |  (1) bigscape_prep.py         -> strain-prefixed region GBKs
        v
  BiG-SCAPE 2 cluster + MIBiG anchor    -> anchored SQLite DB
        |  (2) bigscape_known_novel.py  -> known-vs-novel family table
        |  (3) bigscape_family_domains  -> per-family Pfam domains (novelty verification)
        v
  (4) bigscape_ingest_to_mamey.py       -> GCF context written back INTO the Mode B cards
                                           + GCF columns on the triage board

This driver only orchestrates the shipped adapter tools + the external BiG-SCAPE binary; it adds
no new science. It is deliberately resumable: the domain scan caches per-GBK in --db-path, so
re-runs that only add strains re-scan just the new GBKs. Steps can be skipped once done.

Usage:
  python bigscape_pipeline.py \
      --inputs pkgA.zip pkgB/ ... \
      --pfam /path/Pfam-A.hmm --mibig-dir mibig_gbks/ \
      --workdir bigscape_run/ \
      [--cutoffs 0.3,0.5,0.7] [--cores 1] [--ingest-package MameyPkg/] \
      [--bigscape /path/to/BiG-SCAPE] [--skip-cluster] [--mibig-name local_set]

Memory note: --chunk-mibig is held until multi-call reference and run identity is proven.
The MIBiG route uses the guarded bigscape_launch.sh with -m, never -r.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, contextlib, glob, os, sqlite3, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mamey.bigscape_namespace import NamespaceError, normalize_run_id  # noqa: E402


class PipelineRunError(RuntimeError):
    """Expected, path-redacted refusal for exact BiG-SCAPE run binding."""

    def __init__(self, code, message):
        self.code = code
        self.public_message = message
        super().__init__(f"BIGSCAPE_PIPELINE_ERROR[{code}]: {message}")


def interpreter_env(env=None, executable=None):
    """The launch environment for anything spawned under this interpreter: the interpreter's own
    bin directory is prepended to PATH so binaries installed beside it (BiG-SCAPE shells out to a
    BARE `fasttree` during output generation) resolve even though the conda env was never
    activated. The pipeline is documented to run under the env's python by absolute path, which is
    exactly the case where PATH does not contain that env. v9.7.441 card EB3DF1EF / 283f1f96."""
    env = dict(os.environ if env is None else env)
    bindir = os.path.dirname(executable or sys.executable)
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p]
    if bindir and (not parts or parts[0] != bindir):
        parts = [bindir] + [p for p in parts if p != bindir]
    env["PATH"] = os.pathsep.join(parts)
    return env


def run(cmd, **kw):
    emit("  $ " + " ".join(str(c) for c in cmd))
    kw["env"] = interpreter_env(kw.get("env"))
    return subprocess.run(cmd, check=True, **kw)


def tool(name):
    return os.path.join(HERE, name)


def _exact_run_id(value):
    try:
        return normalize_run_id(value)
    except NamespaceError:
        raise PipelineRunError(
            "RUN_ID_INVALID", "run_id must be a canonical positive integer"
        ) from None


def _snapshot_run_ids(db):
    """Read the exact run-ID set without creating or modifying the database."""
    if not os.path.exists(db):
        return frozenset()
    if not os.path.isfile(db):
        raise PipelineRunError(
            "RUN_DATABASE_INVALID", "BiG-SCAPE run database is unavailable or invalid"
        )
    try:
        uri = Path(db).resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as connection:
            rows = connection.execute("select id from run").fetchall()
    except (OSError, sqlite3.Error):
        raise PipelineRunError(
            "RUN_DATABASE_INVALID", "BiG-SCAPE run database is unavailable or invalid"
        ) from None
    try:
        return frozenset(_exact_run_id(row[0]) for row in rows)
    except (IndexError, TypeError):
        raise PipelineRunError(
            "RUN_DATABASE_INVALID", "BiG-SCAPE run database is unavailable or invalid"
        ) from None


def _resolve_exact_run(db, before, explicit_run_id):
    after = _snapshot_run_ids(db)
    if explicit_run_id is not None:
        if explicit_run_id not in after:
            raise PipelineRunError(
                "RUN_ID_NOT_PRESENT", "explicit run_id is not present in the BiG-SCAPE database"
            )
        return explicit_run_id
    created = after - before
    if len(created) != 1:
        raise PipelineRunError(
            "RUN_DELTA_AMBIGUOUS",
            "cluster transaction did not create exactly one provable BiG-SCAPE run",
        )
    return next(iter(created))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="antiSMASH zips and/or Mamey package dirs")
    ap.add_argument("--pfam", required=True)
    ap.add_argument("--mibig-dir", help="dir of MIBiG antiSMASH GBKs (references)")
    ap.add_argument("--mibig-name", help="explicit BiG-SCAPE -m reference slot name")
    ap.add_argument("--workdir", default="bigscape_run")
    ap.add_argument("--cutoffs", default="0.3,0.5,0.7")
    ap.add_argument("--cores", type=int, default=1)
    ap.add_argument("--bigscape", default=os.environ.get("BIGSCAPE_HOME", "BiG-SCAPE"),
                    help="BiG-SCAPE checkout dir (contains bigscape.py) or 'bigscape' if on PATH")
    ap.add_argument("--ingest-package", help="Mamey package to write GCF context back into")
    ap.add_argument("--mibig-index", help="mibig_reference_index.bacterial.json for compound names")
    ap.add_argument("--chunk-mibig", type=int, default=0, help="load MIBiG refs in batches of N (memory)")
    ap.add_argument("--mibig-index-dir", default=os.path.join(os.path.dirname(HERE), "mamey", "data", "mibig"),
                    help="MIBiG index dir (holds mibig_reference_index.*.json) used to filter refs during --chunk-mibig batching")
    ap.add_argument("--skip-prep", action="store_true")
    ap.add_argument("--skip-cluster", action="store_true")
    ap.add_argument(
        "--run-id",
        help="exact BiG-SCAPE run id; required for skip, pre-existing, shared, or multi-call databases",
    )
    a = ap.parse_args(argv)

    explicit_run_id = _exact_run_id(a.run_id) if a.run_id is not None else None
    if a.skip_cluster and explicit_run_id is None:
        raise PipelineRunError(
            "RUN_ID_REQUIRED_SKIP", "--skip-cluster requires an explicit run_id"
        )
    if a.chunk_mibig and a.mibig_dir and explicit_run_id is None:
        raise PipelineRunError(
            "RUN_ID_REQUIRED_MULTICALL",
            "multi-call clustering requires an explicit run_id or an external exact-run receipt",
        )

    if a.chunk_mibig and a.mibig_dir:
        raise PipelineRunError(
            "CHUNK_MIBIG_UNPROVEN",
            "multi-call MIBiG references are held until loaded counts and exact-run identity are proven",
        )
    if a.mibig_dir and not a.skip_cluster and not a.mibig_name:
        raise PipelineRunError("MIBIG_NAME_REQUIRED", "--mibig-dir requires --mibig-name")
    if a.mibig_dir and not a.skip_cluster and not os.environ.get("BIGSCAPE_ENV_BIN"):
        raise PipelineRunError("BIGSCAPE_ENV_REQUIRED", "set BIGSCAPE_ENV_BIN for the guarded MIBiG launcher")

    inp = os.path.join(a.workdir, "input")
    out = os.path.join(a.workdir, "out")
    db = os.path.join(out, "bigscape.db") if a.mibig_dir else os.path.join(a.workdir, "bigscape.db")
    if not a.skip_cluster and explicit_run_id is None and os.path.lexists(db):
        raise PipelineRunError(
            "RUN_ID_REQUIRED_PREEXISTING",
            "pre-existing or shared BiG-SCAPE databases require an explicit run_id",
        )
    before_run_ids = _snapshot_run_ids(db)

    os.makedirs(a.workdir, exist_ok=True)

    # (1) prep
    if not a.skip_prep:
        emit("[1/4] prep: extracting + strain-prefixing region GBKs")
        run([sys.executable, tool("bigscape_prep.py"), "--inputs", *a.inputs, "--out", inp])
    n = len(glob.glob(os.path.join(inp, "*.gbk")))
    emit(f"      input has {n} region GBKs")

    # (2) cluster + anchor
    bs = a.bigscape
    bs_entry = os.path.join(bs, "bigscape.py") if os.path.isdir(bs) else bs
    base = [sys.executable, bs_entry, "cluster", "-i", inp, "-o", out, "--db-path", db,
            "-p", a.pfam, "--cores", str(a.cores), "--include-singletons", "--gcf-cutoffs", a.cutoffs]
    if not a.skip_cluster:
        emit("[2/4] cluster + MIBiG anchor")
        if a.mibig_dir:
            # Launcher installs the explicit -m slot, checks dependencies and loaded MIBiG count.
            # The pipeline never treats -r (generic reference directory) as a MIBiG anchor.
            env = os.environ.copy()
            env["PFAM_HMM"] = a.pfam
            run(["bash", tool("bigscape_launch.sh"), inp, out, "--label", "bigscape",
                 "--cutoffs", a.cutoffs, "--cores", str(a.cores),
                 "--mibig-dir", a.mibig_dir, "--mibig-name", a.mibig_name,
                 "--include-singletons"], env=env)
        else:
            run(base)

    run_id = _resolve_exact_run(db, before_run_ids, explicit_run_id)

    # (3) tables
    emit("[3/4] known-vs-novel + per-family domains")
    kn = os.path.join(a.workdir, "known_vs_novel.tsv")
    run([sys.executable, tool("bigscape_known_novel.py"), "--db", db,
         "--run-id", str(run_id), "--out", kn])
    run([sys.executable, tool("bigscape_cross_strain.py"), "--db", db,
         "--run-id", str(run_id),
         "--out", os.path.join(a.workdir, "cross_strain_GCFs.tsv"), "--min-strains", "2"])

    # (4) ingest into Mamey
    if a.ingest_package:
        emit("[4/4] ingest GCF context into Mamey cards + triage")
        cmd = [sys.executable, tool("bigscape_ingest_to_mamey.py"), "--db", db,
               "--run-id", str(run_id), "--package", a.ingest_package]
        if a.mibig_index:
            cmd += ["--mibig-index", a.mibig_index]
        run(cmd)
    else:
        emit("[4/4] skipped ingest (no --ingest-package); TSVs written to", a.workdir)
    emit("done. anchored DB:", db)


def cli(argv=None):
    try:
        main(argv)
    except PipelineRunError as error:
        # v9.7.405: sys.stderr.write, not print() — typed-refusal diagnostic, ratchet at ceiling.
        sys.stderr.write(str(error) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
