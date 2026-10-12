"""Whole-worker admission for build_mlsa; no nested native watcher or science changes.

Budgets are portable finite defaults, not biological filters or execution authority.
Persistent diagnostics stay in the requested output; disposable native scratch is
allocated and cleaned by the coordinator after the whole-worker watcher returns.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import uuid

from mamey import native_workspace as workspace
from tools._release_validation import ValidationRefused, run_watched

SCHEMA = "sapote-mamey.mlsa-resource.v1"
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_THREAD_LIMIT")
DEFAULT_RSS = 3_800_000_000
DEFAULT_DISK = 2_000_000_000
DEFAULT_TIMEOUT = 900.0
DEFAULT_COPY = 536_870_912
META_LIMIT = 1_048_576


class MlsaRefused(RuntimeError):
    """A path, byte, resource, monitor or completion contract was not admitted."""


def clean(value, *, exists=True):
    return workspace.clean_path(value, exists=exists, refusal=MlsaRefused)


def bind(value):
    return workspace.digest(value, refusal=MlsaRefused)


def save(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    if len(raw) > META_LIMIT:
        raise MlsaRefused("attempt metadata exceeds 1MiB")
    with clean(path, exists=False).open("xb") as out:
        out.write(raw)


def load(path):
    with clean(path).open("rb") as stream:
        raw = stream.read(META_LIMIT + 1)
    if len(raw) > META_LIMIT:
        raise MlsaRefused("attempt metadata exceeds 1MiB")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise MlsaRefused("attempt metadata must be an object")
    return value


def tool_binding(value):
    # Executable symlinks and spaced argv locators are supported. Bind both the
    # selected lexical locator and actual regular executable target, not a banner.
    locator = Path(os.path.abspath(value))
    target = locator.resolve(strict=True)
    if not target.is_file() or not os.access(locator, os.X_OK):
        raise MlsaRefused("selected companion is not an executable regular file")
    return {"locator": str(locator), "target": bind(target)}


def code_bindings():
    root = Path(__file__).resolve().parents[1]
    return [bind(root / name) for name in (
        "tools/build_mlsa.py", "tools/_mlsa_resources.py",
        "mamey/native_workspace.py", "tools/_release_validation.py", "mamey/csv_safety.py")]


def input_metadata(genomes, seeds, per_file_limit):
    gdir, sdir = clean(genomes), clean(seeds)
    if not gdir.is_dir() or not sdir.is_dir():
        raise MlsaRefused("genome and seed inputs must be directories")
    from tools.build_mlsa import LOCI
    paths = sorted(gdir.glob("*.fna"))
    if not paths:
        raise MlsaRefused("no *.fna genomes in selected input directory")
    paths += [sdir / (locus + ".faa") for locus in LOCI]
    if len(paths) > 10_005:
        raise MlsaRefused("input roster exceeds bounded metadata allowance")
    rows = []
    for path in paths:
        path = clean(path)
        if not path.is_file() or path.stat().st_size > per_file_limit:
            raise MlsaRefused("input file exceeds admitted per-file byte ceiling")
        rows.append({"path": str(path), "bytes": path.stat().st_size})
    return rows


def input_bindings(genomes, seeds, per_file_limit):
    metadata = input_metadata(genomes, seeds, per_file_limit)
    rows = [workspace.digest(row["path"], ceiling=per_file_limit, refusal=MlsaRefused) for row in metadata]
    if [{"path": row["path"], "bytes": row["bytes"]} for row in rows] != metadata:
        raise MlsaRefused("input size changed during streamed binding")
    return rows


def limits(args):
    result = {"rss_limit_bytes": args.rss_limit_bytes,
              "min_free_disk_bytes": args.min_free_disk_bytes,
              "timeout_seconds": args.timeout_seconds,
              "native_copy_limit_bytes": args.native_copy_limit_bytes,
              "threads": args.threads}
    for key, value in result.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise MlsaRefused("resource budgets and threads must be finite and positive")
        if key != "timeout_seconds" and type(value) is not int:
            raise MlsaRefused("byte budgets and threads must be integers")
    result["available_cpu_observation"] = os.cpu_count()
    result["cpu_constraint"] = "POSITIVE_USER_THREADS; OS_CPU_COUNT_IS_AN_OBSERVATION_NOT_AN_ALLOCATION"
    return result


def estimate(rows):
    # Conservative engineering allowances for proteome/CDS, BLAST databases and
    # duplicate staged/original products, alignments, and Python input strings.
    # They are not universal native-tool peak bounds; watcher remains authoritative.
    size = sum(row["bytes"] for row in rows)
    return {"source_bytes": size, "estimated_rss_bytes": 64 * 1024**2 + 20 * size,
            "output_disk_bytes": 64 * 1024**2 + 40 * size,
            "scratch_disk_bytes": 16 * 1024**2 + 12 * size,
            "estimate_not_guarantee": True}


def disk_policy(out_parent, native_root, e, policy):
    roots = [(out_parent, e["output_disk_bytes"]), (native_root, e["scratch_disk_bytes"])]
    same_filesystem = out_parent.stat().st_dev == native_root.stat().st_dev
    reservation = sum(size for _, size in roots)
    observations = []
    for path, size in roots:
        requested = reservation if same_filesystem else size
        free = shutil.disk_usage(path).free
        if free < policy["min_free_disk_bytes"] + requested:
            raise MlsaRefused("insufficient disk for output and native scratch before child launch")
        observations.append({"path": str(path), "free_bytes_before": free,
                             "estimated_reserved_bytes": requested,
                             "watch_floor_bytes": max(policy["min_free_disk_bytes"], free - requested)})
    return {"same_filesystem": same_filesystem, "roots": observations}


def _closure(root, byte_limit, file_limit):
    rows = []; total = 0
    for path in sorted(root.rglob("*")):
        clean(path)
        if path.is_dir():
            continue
        if path.stat().st_size > byte_limit - total or len(rows) >= file_limit:
            raise MlsaRefused("worker output exceeds admitted bounded closure")
        row = bind(path)
        total += row["bytes"]
        if total > byte_limit:
            raise MlsaRefused("worker output grew beyond admitted bounded closure")
        rows.append({"relative_path": path.relative_to(root).as_posix(),
                     "bytes": row["bytes"], "sha256": row["sha256"]})
    return rows


def _recheck(request):
    if request["sources"] != code_bindings():
        raise MlsaRefused("source bindings changed")
    if request["inputs"] != input_bindings(request["genomes"], request["seeds"],
                                           request["policy"]["native_copy_limit_bytes"]):
        raise MlsaRefused("input bytes or exact selected roster changed")
    if request["tools"] != {name: tool_binding(row["locator"]) for name, row in request["tools"].items()}:
        raise MlsaRefused("selected companion target or bytes changed")
    if request["python"] != tool_binding(sys.executable):
        raise MlsaRefused("worker interpreter target or bytes changed")


def _attach(request):
    descriptor = request["scratch"]
    return workspace.OwnedWorkspace(descriptor["path"], descriptor["device"], descriptor["inode"],
                                    refusal=MlsaRefused)


def worker(path, expected_sha):
    request_path = clean(path)
    if bind(request_path)["sha256"] != expected_sha:
        raise MlsaRefused("worker request digest mismatch")
    request = load(request_path)
    if request.get("schema") != SCHEMA or request.get("attempt_id") != request_path.parent.name:
        raise MlsaRefused("worker request schema/attempt mismatch")
    output = clean(request["worker_output"], exists=False)
    if output != request_path.parent / "worker_output" or output.exists():
        raise MlsaRefused("worker output must be its fresh request-owned directory")
    if any(os.environ.get(key) != "1" for key in THREAD_KEYS):
        raise MlsaRefused("worker six-key thread environment mismatch")
    _recheck(request)
    _attach(request).validate()
    from tools.build_mlsa import _compute_main
    argv = [request["genomes"], str(output), "--threads", str(request["policy"]["threads"]),
            "--seeds-dir", request["seeds"]]
    code = _compute_main(argv, native_workdir=request["scratch"]["path"],
                         native_copy_limit=request["policy"]["native_copy_limit_bytes"],
                         bound_bins={name: row["locator"] for name, row in request["tools"].items()})
    _recheck(request)
    _attach(request).validate()
    closure = _closure(output, request["estimate"]["output_disk_bytes"], request["file_limit"])
    if code == 0 and load(output / "run_status.json").get("status") != "COMPLETE":
        raise MlsaRefused("worker completion lacks mechanical COMPLETE status")
    save(request_path.parent / "WORKER_COMPLETION.json", {
        "schema": SCHEMA, "attempt_id": request["attempt_id"], "request_sha256": expected_sha,
        "exit_code": code, "outputs": closure,
        "thread_environment": {key: os.environ[key] for key in THREAD_KEYS}})
    return code


def _promote(output, destination, closure, byte_limit, owned_status, min_disk):
    # Copy this exact bounded closure into fresh exclusive names. Retaining the
    # worker bytes preserves historical copy provenance; no rename may clobber a
    # file that appeared after an earlier check. COMPLETE is created last.
    allowed_dirs = {"proteomes", "cds", "blastdb", "loci", "aln"}
    allowed_files = {"taxon_map.tsv", "mlsa.log", "run_status.json", "native_blast_identity.json", "loci_report.tsv"}
    names = {Path(row["relative_path"]).parts[0] for row in closure}
    for name in names:
        if name not in allowed_dirs | allowed_files and not name.startswith("tree."):
            raise MlsaRefused("unexpected worker output namespace")
        source = clean(output / name)
        target = clean(destination / name, exists=False)
        if target.exists():
            raise MlsaRefused("output promotion would clobber existing evidence")
        if source.is_dir() != (name in allowed_dirs):
            raise MlsaRefused("worker output namespace type mismatch")
    status_row = next((row for row in closure if row["relative_path"] == "run_status.json"), None)
    if status_row is None:
        raise MlsaRefused("completion status absent from bound closure")
    with clean(output / "run_status.json").open("rb") as stream:
        status_bytes = stream.read(META_LIMIT + 1)
    if (len(status_bytes) > META_LIMIT or len(status_bytes) != status_row["bytes"] or
            hashlib.sha256(status_bytes).hexdigest() != status_row["sha256"]):
        raise MlsaRefused("completion status bytes changed before promotion")
    created_dirs = {destination}
    remaining = byte_limit
    uncopied = sum(row["bytes"] for row in closure)
    for row in closure:
        relative = Path(row["relative_path"])
        if relative.as_posix() == "run_status.json":
            continue
        source, target = clean(output / relative), clean(destination / relative, exists=False)
        for directory in reversed(target.parent.parents):
            if directory == destination or directory.is_relative_to(destination):
                if directory not in created_dirs:
                    directory.mkdir(); created_dirs.add(directory)
        if target.parent not in created_dirs:
            target.parent.mkdir(); created_dirs.add(target.parent)
        if shutil.disk_usage(destination).free < min_disk + uncopied:
            raise MlsaRefused("output disk floor refused bounded promotion")
        copied = workspace.bounded_copy(source, target, remaining, refusal=MlsaRefused)
        if (copied["copy"]["bytes"], copied["copy"]["sha256"]) != (row["bytes"], row["sha256"]):
            raise MlsaRefused("promotion bytes differ from worker closure")
        remaining -= row["bytes"]
        uncopied -= row["bytes"]
    for row in closure:
        if row["relative_path"] != "run_status.json":
            final = bind(destination / row["relative_path"])
            if (final["bytes"], final["sha256"]) != (row["bytes"], row["sha256"]):
                raise MlsaRefused("promoted output readback differs from worker closure")
    if shutil.disk_usage(destination).free < min_disk + len(status_bytes):
        raise MlsaRefused("output disk floor refused completion status")
    # The opened status inode is recorded before writing. A late I/O failure can
    # invalidate only this owned status; replacement/unowned evidence is refused.
    with clean(destination / "run_status.json", exists=False).open("xb") as stream:
        observed = os.fstat(stream.fileno())
        owned_status.update(device=observed.st_dev, inode=observed.st_ino)
        stream.write(status_bytes)


def _failed_diagnostics(output, destination, owned_status=None):
    # Keep partial products in the attempt; expose only historical diagnostic
    # surfaces at the requested output. Never promote a tree or COMPLETE status.
    detail = "RESOURCE_OR_BUILD_REFUSED; inspect RESOURCE_ATTEMPT diagnostics"
    status = output / "run_status.json"
    if status.is_file() and not status.is_symlink():
        original = load(status)
        if original.get("status") == "FAILED":
            detail = original.get("detail", detail)
    failed = {"status": "FAILED", "detail": detail,
              "scope": "mechanical MLSA build only; judgment deferred"}
    public_status = destination / "run_status.json"
    if public_status.exists():
        clean(public_status)
        observed = public_status.stat()
        if not owned_status or (observed.st_dev, observed.st_ino) != (owned_status["device"], owned_status["inode"]):
            raise MlsaRefused("failed status would overwrite unowned evidence")
        pending = destination / ("run_status.failed-" + uuid.uuid4().hex + ".json")
        save(pending, failed)
        pending.replace(public_status)
    else:
        save(public_status, failed)
    for name in ("mlsa.log", "loci_report.tsv", "native_blast_identity.json"):
        source = output / name
        if source.is_file() and not source.is_symlink():
            workspace.bounded_copy(source, destination / name, META_LIMIT, refusal=MlsaRefused)


def parser():
    from tools.build_mlsa import DEFAULT_SEEDS_DIR
    p = argparse.ArgumentParser(description="Bounded watched MLSA build; no scientific approval")
    p.add_argument("genomes_dir"); p.add_argument("out_dir")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--bin-dir"); p.add_argument("--seeds-dir", default=DEFAULT_SEEDS_DIR)
    p.add_argument("--native-work-root")
    p.add_argument("--rss-limit-bytes", type=int, default=DEFAULT_RSS)
    p.add_argument("--min-free-disk-bytes", type=int, default=DEFAULT_DISK)
    p.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--native-copy-limit-bytes", type=int, default=DEFAULT_COPY)
    return p


def coordinate(args):
    from tools import build_mlsa
    policy = limits(args)
    genomes, seeds = clean(args.genomes_dir), clean(args.seeds_dir)
    output = clean(args.out_dir, exists=False)
    parent = clean(output.parent)
    if not parent.is_dir() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise MlsaRefused("output must be new or empty with an existing parent")
    for source in (genomes, seeds, Path(__file__).resolve().parents[1]):
        if output.is_relative_to(source) or source.is_relative_to(output):
            raise MlsaRefused("output/source overlap is not admitted")
    native_root = workspace.work_root(args.native_work_root, refusal=MlsaRefused)
    if any(native_root.is_relative_to(source) for source in (genomes, seeds, output)):
        raise MlsaRefused("native work root overlaps protected input or output")
    metadata = input_metadata(genomes, seeds, policy["native_copy_limit_bytes"])
    e = estimate(metadata)
    if e["estimated_rss_bytes"] > 0.8 * policy["rss_limit_bytes"]:
        raise MlsaRefused("estimated RSS exceeds 80% admission margin")
    disk = disk_policy(parent, native_root, e, policy)
    # Reject resource estimates from stat metadata before hashing source payloads.
    rows = input_bindings(genomes, seeds, policy["native_copy_limit_bytes"])
    if [{"path": row["path"], "bytes": row["bytes"]} for row in rows] != metadata:
        raise MlsaRefused("source metadata changed after resource preflight")
    selected = {name: build_mlsa.resolve_bin(name, args.bin_dir) for name in build_mlsa._BIN_ALIASES}
    if any(value is None for value in selected.values()):
        raise MlsaRefused("missing companion tool(s); see mamey doctor --companions")
    tools = {name: tool_binding(value) for name, value in selected.items()}
    sources = code_bindings()
    interpreter = tool_binding(sys.executable)
    # All preflights above happen before any output/scratch allocation or child.
    if not output.exists():
        output.mkdir()
    attempts = output / "RESOURCE_ATTEMPT"
    attempts.mkdir()
    attempt = attempts / uuid.uuid4().hex
    attempt.mkdir()
    owned = None; watched = None; request = None; failure = None; cleanup = None
    watch_invoked = False; owned_status = {}
    try:
        owned = workspace.OwnedWorkspace.create(native_root, "mamey-mlsa-", refusal=MlsaRefused)
        if any(owned.path.is_relative_to(source) or source.is_relative_to(owned.path)
               for source in (genomes, seeds, output)):
            raise MlsaRefused("owned scratch/protected source overlap")
        request = {"schema": SCHEMA, "attempt_id": attempt.name, "genomes": str(genomes),
                   "seeds": str(seeds), "worker_output": str(attempt / "worker_output"),
                   "scratch": owned.descriptor(), "inputs": rows, "tools": tools,
                   "python": interpreter, "sources": sources, "policy": policy,
                   "estimate": e, "disk_policy": disk, "file_limit": 1000 + 32 * (len(rows) - 5)}
        request_path = attempt / "REQUEST.json"
        save(request_path, request)
        request_sha = bind(request_path)["sha256"]
        env = dict(os.environ)
        env.update({key: "1" for key in THREAD_KEYS})
        root = Path(__file__).resolve().parents[1]
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", PYTHONPATH=str(root))
        watch_invoked = True
        watched = run_watched([sys.executable, "-B", str(root / "tools/build_mlsa.py"),
                               "--_mlsa-worker", str(request_path), request_sha],
            cwd=attempt, log=attempt / "worker.log", env=env,
            rss_limit=policy["rss_limit_bytes"], min_disk=disk["roots"][0]["watch_floor_bytes"],
            timeout=policy["timeout_seconds"],
            additional_disk_floors=((native_root, disk["roots"][1]["watch_floor_bytes"]),))
        # Freeze resource evidence first; final terminal binds its digest, avoiding
        # RUN/resource/SUCCEEDED cyclic hashes. Stop/cleanup invalidate exit zero.
        save(attempt / "RESOURCE.json", watched)
        if watched["exit_code"] != 0 or watched["stop_reason"] or watched.get("cleanup_error"):
            raise MlsaRefused("whole-worker watcher refused completion")
        if bind(request_path)["sha256"] != request_sha:
            raise MlsaRefused("frozen request changed")
        _recheck(request)
        completion = load(attempt / "WORKER_COMPLETION.json")
        closure = _closure(Path(request["worker_output"]), e["output_disk_bytes"], request["file_limit"])
        if (completion.get("attempt_id") != attempt.name or completion.get("request_sha256") != request_sha or
                completion.get("exit_code") != 0 or completion.get("outputs") != closure or
                completion.get("thread_environment") != {key: "1" for key in THREAD_KEYS}):
            raise MlsaRefused("worker completion/closure binding mismatch")
        if load(Path(request["worker_output"]) / "run_status.json").get("status") != "COMPLETE":
            raise MlsaRefused("worker completion lacks COMPLETE status")
        cleanup = owned.cleanup(); owned = None
        _promote(Path(request["worker_output"]), output, closure, e["output_disk_bytes"], owned_status,
                 policy["min_free_disk_bytes"])
        if _closure(Path(request["worker_output"]), e["output_disk_bytes"], request["file_limit"]) != closure:
            raise MlsaRefused("worker output closure changed during promotion")
        sys.stdout.write("build_mlsa: outputs -> " + str(output / "tree.treefile") + "\n")
        save(attempt / "SUCCEEDED.json", {"schema": SCHEMA, "attempt_id": attempt.name,
             "request": bind(request_path), "resource": bind(attempt / "RESOURCE.json"),
             "completion": bind(attempt / "WORKER_COMPLETION.json"), "outputs": closure,
             "worker_output_root": request["worker_output"], "promoted_output_root": str(output),
             "scratch_cleanup": cleanup, "scope": "mechanical MLSA only; no scientific approval"})
        return 0
    except (MlsaRefused, workspace.NativeWorkspaceRefused, ValidationRefused, OSError, ValueError, KeyboardInterrupt) as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if owned is not None:
            # run_watched ordinarily reaps all observed descendants before return.
            # If cleanup failed, leave scratch untouched for explicit diagnosis.
            if (watch_invoked and watched is None) or (watched is not None and watched.get("cleanup_error")):
                cleanup = "RETAINED_MONITOR_CLEANUP_UNCONFIRMED"
            else:
                try:
                    cleanup = owned.cleanup()
                except (OSError, workspace.NativeWorkspaceRefused, MlsaRefused) as exc:
                    cleanup = "REFUSED: " + str(exc)
    if failure is not None:
        save(attempt / "FAILED.json", {"schema": SCHEMA, "attempt_id": attempt.name,
             "detail": failure, "scratch_cleanup": cleanup, "scratch": request.get("scratch") if request else None,
             "request": bind(attempt / "REQUEST.json") if (attempt / "REQUEST.json").exists() else None,
             "resource": bind(attempt / "RESOURCE.json") if (attempt / "RESOURCE.json").exists() else None})
        worker_output = attempt / "worker_output"
        try:
            _failed_diagnostics(worker_output, output, owned_status)
        except (OSError, ValueError, MlsaRefused) as exc:
            save(attempt / "DIAGNOSTIC_COPY_REFUSED.json", {"detail": str(exc)})
        sys.stderr.write("build_mlsa: REFUSED " + failure + "\n")
    return 6


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--_mlsa-worker":
        if len(argv) != 3:
            raise MlsaRefused("internal worker requires exact request/hash arguments")
        try:
            return worker(argv[1], argv[2])
        except (MlsaRefused, workspace.NativeWorkspaceRefused, OSError, ValueError) as exc:
            sys.stderr.write("build_mlsa worker: REFUSED " + str(exc) + "\n")
            return 6
    if not argv or argv[0] in ("-h", "--help"):
        parser().print_help(file=sys.stderr)
        return 2
    try:
        return coordinate(parser().parse_args(argv))
    except (MlsaRefused, workspace.NativeWorkspaceRefused, ValidationRefused, OSError, ValueError) as exc:
        # No diagnostic sibling is invented outside the caller's allowed output.
        sys.stderr.write("build_mlsa: REFUSED " + str(exc) + "\n")
        return 4
