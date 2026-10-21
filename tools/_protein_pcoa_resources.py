"""Resource admission and watched attempts for the existing protein PCoA owner.

Estimates are engineering allowances, never measured peaks or scientific filters.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import tempfile
import shutil
import stat
import sys
import uuid
from pathlib import Path

from tools._release_validation import ValidationRefused, run_watched
from mamey import native_workspace as _native_workspace

SCHEMA = "sapote-mamey.protein-pcoa-resource.v1"
DEFAULT_RSS = 3_800_000_000
DEFAULT_DISK = 2_000_000_000
DEFAULT_TIMEOUT = 900
THREAD_ENVIRONMENT_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_THREAD_LIMIT")


class ResourceRefusal(RuntimeError):
    """An input, budget, monitor or completion contract was not admitted."""


def clean_path(value, *, exists=True):
    return _native_workspace.clean_path(value, exists=exists, refusal=ResourceRefusal)


def digest(path):
    return _native_workspace.digest(path, refusal=ResourceRefusal)


def write_json(path, value):
    with clean_path(path, exists=False).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")



def read_request_json(path):
    """Bound the coordinator's completion/request metadata allocation."""
    with clean_path(path).open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ResourceRefusal("attempt metadata exceeds 1MiB")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ResourceRefusal("attempt metadata must be an object")
    return value


def budget(a):
    values = {"rss_limit_bytes": getattr(a, "rss_limit_bytes", DEFAULT_RSS),
              "min_free_disk_bytes": getattr(a, "min_free_disk_bytes", DEFAULT_DISK),
              "timeout_seconds": getattr(a, "timeout_seconds", DEFAULT_TIMEOUT),
              "threads": a.threads}
    for key, value in values.items():
        try:
            finite = math.isfinite(value)
        except (TypeError, OverflowError):
            finite = False
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite or value <= 0:
            raise ResourceRefusal("resource budgets and threads must be finite and positive")
        if key != "timeout_seconds" and int(value) != value:
            raise ResourceRefusal("byte budgets and threads must be integers")
        if key != "timeout_seconds":
            values[key] = int(value)
    # os.cpu_count is an observation, not an inferred affinity/cgroup policy.
    values["available_cpu_observation"] = os.cpu_count()
    values["cpu_constraint"] = "USER_CONFIGURED_POSITIVE_THREADS; OS_CPU_COUNT_NOT_AN_ENFORCED_ALLOCATION"
    return values


def solver_bytes(n):
    c = 52 if n <= 400 else (28 if n < 8000 else 20)
    return c * n * n + 1536 * n


def estimate(info, *, n=None):
    count = info["records"] if n is None else n
    endpoints = [min(count, 400)] if count >= 4 else []
    if count >= 401:
        endpoints.append(min(count, 7999))
    if count >= 8000:
        endpoints.append(count)
    h = (384 * 1024**2 + 8 * info["fasta_bytes"] + 8 * info["metadata_bytes"]
         + 2048 * info["records"] + 8 * info["maximum_line_bytes"])
    matrix = max((solver_bytes(x) for x in endpoints), default=0) if n is None else solver_bytes(count)
    disk = (4 * count * count * (2 * info["maximum_id_bytes"] + 128)
            + 8 * info["fasta_bytes"] + 4 * info["metadata_bytes"]
            + 2048 * info["records"] + 32 * 1024**2)
    return {"retained_n": count, "input_baseline_bytes": h,
            "estimated_rss_bytes": h + matrix, "estimated_disk_bytes": disk,
            "reachable_solver_endpoints": endpoints, "estimate_not_guarantee": True}


def admit(info, limits, *, n=None):
    e = estimate(info, n=n)
    if e["retained_n"] < 4:
        raise ResourceRefusal("fewer than four retained points")
    if n is not None and n > info["records"]:
        raise ResourceRefusal("clustered membership exceeds admitted upper bound")
    if e["estimated_rss_bytes"] > limits["rss_limit_bytes"] * 0.8:
        raise ResourceRefusal("estimated RSS exceeds 80% admission margin")
    return e


def cluster_stage_estimate(info, limits):
    """Linear clustering allowance; the dense solver is admitted only after clustering.

    Fixed per-thread buffers and input multipliers are engineering estimates.
    The same process-tree RSS cap and disk floor remain authoritative at runtime.
    """
    if info["records"] < 4:
        raise ResourceRefusal("fewer than four input points")
    baseline = estimate(info)["input_baseline_bytes"]
    rss = baseline + 128 * 1024**2 * limits["threads"] + 16 * info["fasta_bytes"] + 4096 * info["records"]
    disk = (256 * 1024**2 + 64 * info["fasta_bytes"] + 8 * info["metadata_bytes"]
            + info["records"] * (8 * info["maximum_id_bytes"] + 4096))
    if rss > limits["rss_limit_bytes"] * 0.8:
        raise ResourceRefusal("cluster-stage estimated RSS exceeds 80% admission margin")
    # Cohort members cannot be reduced by reference clustering.
    irreducible_points = info["records"] - info["reference"] - info["mibig"]
    if irreducible_points < 0:
        raise ResourceRefusal("inconsistent input membership counts")
    if irreducible_points >= 4:
        admit(info, limits, n=irreducible_points)
    return dict(stage="CLUSTER_ONLY", records=info["records"], input_baseline_bytes=baseline,
                estimated_rss_bytes=rss, estimated_disk_bytes=disk,
                estimate_not_guarantee=True, final_ordination_admission="PENDING_CLUSTERED_N")


def _lines(path, ceiling, h, metrics):
    with clean_path(path).open("rb") as stream:
        while True:
            raw = stream.readline(ceiling + 1)
            if not raw:
                break
            if len(raw) > ceiling:
                raise ResourceRefusal("input line exceeds bounded reader allowance")
            h.update(raw)
            metrics["maximum_line_bytes"] = max(metrics["maximum_line_bytes"], len(raw))
            yield raw.decode("utf-8")


def read_inputs(kit, name, limits, *, materialize=False, expected=None):
    """Preflight keeps IDs/source labels only; worker binds its parsed streams too."""
    kit = clean_path(kit)
    if not name or name in (".", "..") or any(x in name for x in "/\\\r\n"):
        raise ResourceRefusal("set must be one filename component")
    meta_path, fasta_path = kit / f"{name}_META.tsv", kit / f"{name}.faa"
    before = [digest(meta_path), digest(fasta_path)]
    info = {"records": 0, "cohort": 0, "reference": 0, "mibig": 0,
            "metadata_bytes": before[0]["bytes"], "fasta_bytes": before[1]["bytes"],
            "maximum_line_bytes": 0, "maximum_id_bytes": 0}
    ceiling = max(1, min(16 * 1024**2, int(limits["rss_limit_bytes"] // 64)))
    info["line_ceiling_bytes"] = ceiling
    if estimate(info)["estimated_rss_bytes"] > limits["rss_limit_bytes"] * 0.8:
        raise ResourceRefusal("input-byte estimate exceeds admission before parsing")
    hashes = [hashlib.sha256(), hashlib.sha256()]
    meta = {}
    for row in csv.DictReader(_lines(meta_path, ceiling, hashes[0], info), delimiter="\t"):
        identifier, source = row.get("id"), row.get("source")
        if not identifier or not source or any(c.isspace() for c in identifier) or identifier in meta:
            raise ResourceRefusal("missing/duplicate/whitespace metadata ID or missing source")
        meta[identifier] = row if materialize else source
        info["records"] += 1
        key = "cohort" if source == "isolate" else ("mibig" if source == "MIBiG" else "reference")
        info[key] += 1
        info["maximum_id_bytes"] = max(info["maximum_id_bytes"], len(identifier.encode("utf-8")))
        if estimate(info)["input_baseline_bytes"] > limits["rss_limit_bytes"] * 0.8:
            raise ResourceRefusal("streaming bookkeeping estimate exceeds admission")
    seqs, seen, current = {}, set(), None
    for line in _lines(fasta_path, ceiling, hashes[1], info):
        line = line.strip()
        if line.startswith(">"):
            tokens = line[1:].split()
            if not tokens or tokens[0] in seen or tokens[0] not in meta:
                raise ResourceRefusal("missing/duplicate/unmatched FASTA ID")
            current = tokens[0]
            seen.add(current)
            if materialize:
                seqs[current] = []
        elif line:
            if current is None:
                raise ResourceRefusal("FASTA sequence precedes its ID")
            if materialize:
                seqs[current].append(line)
    if seen != set(meta):
        raise ResourceRefusal("metadata and FASTA membership disagree")
    consumed = [dict(record, sha256=h.hexdigest()) for record, h in zip(before, hashes)]
    if consumed != before or before != [digest(meta_path), digest(fasta_path)] or (expected is not None and consumed != expected):
        raise ResourceRefusal("input consumed-byte/source binding changed")
    return info, consumed, meta, {k: "".join(v) for k, v in seqs.items()}



def shell_safe_path(path):
    return _native_workspace.shell_safe_path(path, refusal=ResourceRefusal)


def cluster_workspace_policy(a, info, limits, default_root=None):
    """Cluster scratch root. An explicit --cluster-work-root is used as given (a refused explicit root is never
    replaced). Otherwise the attempt's own receipt folder (default_root, resolved for aliases) when its path is
    shell-safe, so scratch stays beside the attempt that owns it. Otherwise (no default_root, or a receipt path with
    spaces or other refused characters) the resolved system temp root. The choice is recorded as root_source."""
    if not (info["reference"] or info["mibig"]):
        return None
    explicit = getattr(a, "cluster_work_root", None)
    root = None
    if explicit is not None:
        root, source = shell_safe_path(explicit), "EXPLICIT"
    elif default_root is not None:
        try:
            root, source = shell_safe_path(Path(default_root).resolve(strict=True)), "ATTEMPT_RECEIPT_DEFAULT"
        except ResourceRefusal:
            root, source = None, "SYSTEM_TEMP_FALLBACK_ATTEMPT_PATH_NOT_SHELL_SAFE"
    else:
        source = "SYSTEM_TEMP_DEFAULT"
    if root is None:
        root = shell_safe_path(Path(tempfile.gettempdir()).resolve(strict=True))
    if not root.is_dir():
        raise ResourceRefusal("cluster work root must be an existing directory")
    observed = root.stat()
    output_bound = info["records"] * (2 * info["maximum_id_bytes"] + 4)
    phase_estimate = (cluster_stage_estimate(info, limits) if getattr(a, "cluster_first", False)
                      else estimate(info))
    required = phase_estimate["estimated_disk_bytes"] + info["fasta_bytes"] + info["records"] + output_bound
    free = shutil.disk_usage(root).free
    if free < limits["min_free_disk_bytes"] + required:
        raise ResourceRefusal("cluster work filesystem lacks estimated growth plus free-disk floor")
    return {"root": str(root), "root_source": source, "device": observed.st_dev, "inode": observed.st_ino,
            "estimated_disk_bytes": required, "estimate_not_guarantee": True,
            "free_bytes_observed": free,
            "monitor_min_free_bytes": max(limits["min_free_disk_bytes"], free - math.ceil(required / 0.8)),
            "input_copy_ceiling_bytes": info["fasta_bytes"] + info["records"]}


def checked_cluster_root(policy, limits):
    if not isinstance(policy, dict):
        raise ResourceRefusal("cluster work root is not bound in the worker request")
    root = shell_safe_path(policy["root"])
    current = root.stat()
    if not root.is_dir() or (current.st_dev, current.st_ino) != (policy["device"], policy["inode"]):
        raise ResourceRefusal("cluster work root identity changed")
    if shutil.disk_usage(root).free < limits["min_free_disk_bytes"] + policy["estimated_disk_bytes"]:
        raise ResourceRefusal("cluster work filesystem changed below admission floor")
    return root


def bounded_copy(source, destination, ceiling):
    return _native_workspace.bounded_copy(source, destination, ceiling, refusal=ResourceRefusal)


def run_cluster_workspace(executable, source, destination, *, name, approx_id, threads,
                          member_count, maximum_id_bytes, policy, limits):
    """Only cluster runs in fresh safe cwd; outer watched worker owns its child."""
    if name not in ("refs", "mibig"):
        raise ResourceRefusal("unexpected cluster group")
    root = checked_cluster_root(policy, limits)
    binary = shell_safe_path(executable)
    destination = clean_path(destination, exists=False)
    if destination.exists() or destination.is_symlink():
        raise ResourceRefusal("cluster result already exists")
    source_binding = digest(source)
    owned = _native_workspace.OwnedWorkspace.create(root, "mamey-pcoa-cluster-", refusal=ResourceRefusal)
    scratch = owned.path
    identity = scratch.stat()
    record = {"name": name, "temporary_directory": str(scratch), "work_root": policy,
              "source": source_binding, "state": "RUNNING", "temporary_identity": {"device": identity.st_dev, "inode": identity.st_ino},
              "child_process_group": "INHERIT_WATCHED_WORKER"}
    terminal = destination.parent / f"{name}_cluster_terminal.json"
    failure = None
    try:
        shell_safe_path(scratch)
        write_json(destination.parent / f"{name}_cluster_running.json", record)
        (scratch / "tmp").mkdir(exist_ok=False)
        record["input_copy"] = bounded_copy(source, scratch / "input.faa", policy["input_copy_ceiling_bytes"])
        if record["input_copy"]["source"] != source_binding:
            raise ResourceRefusal("cluster source changed before child launch")
        argv = [str(binary), "cluster", "-d", "input.faa", "-o", "clusters.tsv", "--approx-id", str(approx_id),
                "--member-cover", "80", "--threads", str(threads), "--tmpdir", "tmp", "--quiet"]
        record["argv"] = argv
        checked_cluster_root(policy, limits)
        if shutil.disk_usage(destination.parent).free < limits["min_free_disk_bytes"] + policy["estimated_disk_bytes"]:
            raise ResourceRefusal("receipt filesystem lacks cluster growth plus free-disk floor")
        # No shell, global chdir or detached session. The original outer watcher
        # covers Python, DIAMOND, scratch filesystem, eigensolver and promotion.
        subprocess.run(argv, cwd=scratch, check=True)
        if digest(source) != source_binding or digest(scratch / "input.faa") != record["input_copy"]["copy"]:
            raise ResourceRefusal("cluster input/source changed during child execution")
        record["output_copy"] = bounded_copy(scratch / "clusters.tsv", destination,
                                               member_count * (2 * maximum_id_bytes + 4))
        record["state"] = "SUCCEEDED"
    except BaseException as exc:
        failure = exc
        record.update(state="FAILED", reason_type=type(exc).__name__, reason=str(exc))
    finally:
        try:
            record["cleanup"] = owned.cleanup()
        except OSError as exc:
            record.update(state="FAILED", cleanup="FAILED", cleanup_error=str(exc))
            failure = failure or exc
        except ResourceRefusal as exc:
            record.update(state="FAILED", cleanup="REFUSED", cleanup_error=str(exc))
            failure = failure or exc
        write_json(terminal, record)
    if failure is not None:
        raise ResourceRefusal("cluster attempt failed; inspect retained cluster diagnostics") from failure
    return {"terminal": digest(terminal), "input_copy": record["input_copy"],
            "output_copy": record["output_copy"], "cleanup": record["cleanup"]}


def source_bindings(script):
    root = Path(script).parent.parent
    return [digest(p) for p in [Path(script), Path(__file__), root / "tools/_release_validation.py", root / "mamey/native_workspace.py",
                               root / "mamey/csv_safety.py", root / "mamey/_gbk_shim.py"]]


def runtime():
    versions = {}
    for name in ("numpy", "scipy"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "executable": digest(Path(sys.executable).resolve(strict=True)), "requested_executable": sys.executable,
            "installed_distributions": versions, "loaded_module_versions": {name: getattr(sys.modules.get(name), "__version__", "NOT_IMPORTED") for name in ("numpy", "scipy")}}


def coordinate(a, script):
    limits = budget(a)
    kit = clean_path(a.kit)
    explicit_receipt = getattr(a, "resource_receipt_dir", None)
    preflight = getattr(a, "preflight", False)
    if not a.set or a.set in (".", "..") or any(c in a.set for c in "/\\\r\n"):
        raise ResourceRefusal("set must be one filename component")
    if preflight and not explicit_receipt:
        raise ResourceRefusal("--preflight requires an explicit fresh --resource-receipt-dir")
    if explicit_receipt and not preflight:
        raise ResourceRefusal("--resource-receipt-dir is for preflight; compute receipts stay in the owned attempt")
    attempt_root = clean_path(getattr(a, "attempt_root", None) or kit, exists=False)
    if not attempt_root.exists():
        if preflight:
            raise ResourceRefusal("preflight does not create an attempt root")
        clean_path(attempt_root.parent)
        attempt_root.mkdir(exist_ok=False)
    target = attempt_root / f"out_{a.set}"
    # Validate the component before any output operation.
    if not a.set or a.set in (".", "..") or any(c in a.set for c in "/\\\r\n"):
        raise ResourceRefusal("set must be one filename component")
    if target.exists() or target.is_symlink():
        raise ResourceRefusal("existing ordinate output is retained; choose a fresh --attempt-root")
    if preflight:
        receipt = clean_path(explicit_receipt, exists=False)
        clean_path(receipt.parent)
        if kit == receipt or receipt in kit.parents:
            raise ResourceRefusal("diagnostic target may not contain the source kit")
        receipt.mkdir(exist_ok=False)
    else:
        target.mkdir(exist_ok=False)
        receipt = target / "RESOURCE_ATTEMPT"
        receipt.mkdir(exist_ok=False)
    attempt = uuid.uuid4().hex
    base = {"schema": SCHEMA, "attempt_id": attempt, "limits": limits, "source_kit": str(kit),
            "mode": "METADATA_ONLY_PREFLIGHT" if preflight else "WATCHED_ORDINATION"}
    try:
        info, inputs, _, _ = read_inputs(kit, a.set, limits)
        base.update(counts=info, estimate=estimate(info))
        # Reference and MIBiG sequences are clustered before the all-vs-all in every run, so by default their set is
        # admitted at the clustering stage and the dense solver at the clustered count. A cohort-only set is never
        # clustered and keeps the upper-bound admission. An explicit --cluster-first / --no-cluster-first wins.
        requested = getattr(a, "cluster_first", None)
        cluster_first = bool(info["reference"] or info["mibig"]) if requested is None else bool(requested)
        a.cluster_first = cluster_first
        e = cluster_stage_estimate(info, limits) if cluster_first else admit(info, limits)
        base["admission_mode"] = "CLUSTER_FIRST" if cluster_first else "UPPER_BOUND_FIRST"
        base["admission_mode_source"] = "DEFAULT" if requested is None else "EXPLICIT"
        if cluster_first:
            base.update(unclustered_upper_bound_estimate=estimate(info), estimate=e)
        free = shutil.disk_usage(receipt).free
        if free < limits["min_free_disk_bytes"] + e["estimated_disk_bytes"]:
            raise ResourceRefusal("estimated scratch growth plus free-disk floor is unavailable")
        workspace = cluster_workspace_policy(a, info, limits, default_root=receipt)
        sources = source_bindings(script)
        admitted = dict(base, state="CLUSTER_STAGE_ADMITTED" if cluster_first else "ADMITTED", counts=info, estimate=e, inputs=inputs, sources=sources,
                        cluster_workspace=workspace)
        write_json(receipt / "admission.json", admitted)
        if preflight:
            state = "PREFLIGHT_CLUSTER_ADMITTED_ORDINATION_PENDING" if cluster_first else "PREFLIGHT_ADMITTED"
            write_json(receipt / "terminal.json", dict(base, state=state, compute="NOT_EXECUTED"))
            return dict(admitted, mode="METADATA_ONLY_PREFLIGHT", compute="NOT_EXECUTED", state=state)
        scratch = receipt / "scratch"
        scratch.mkdir(exist_ok=False)
        request = dict(admitted, scratch=str(scratch), set=a.set,
                       approx_id=a.approx_id, diamond=a.diamond,
                       keep_allvsall=bool(getattr(a, "keep_allvsall", False)),
                       cluster_first=cluster_first,
                       thread_environment={key: "1" for key in THREAD_ENVIRONMENT_KEYS})
        request_path = receipt / "request.json"
        write_json(request_path, request)
        request_hash = digest(request_path)["sha256"]
        env = dict(os.environ)
        env.update(request["thread_environment"])
        env["MAMEY_PCOA_REQUEST"] = request_hash
        env["PYTHONHASHSEED"] = "0"
        write_json(receipt / "running.json", dict(base, state="RUNNING", request_sha256=request_hash))
        watched = run_watched([sys.executable, str(script), "--_ordinate-worker", str(request_path), request_hash],
                              cwd=receipt, log=receipt / "worker.log", env=env,
                              rss_limit=limits["rss_limit_bytes"],
                              min_disk=(limits["min_free_disk_bytes"] if cluster_first else
                                  max(limits["min_free_disk_bytes"], free - math.ceil(e["estimated_disk_bytes"] / 0.8))),
                              timeout=limits["timeout_seconds"], poll_interval=0.2,
                              additional_disk_floors=(() if workspace is None else
                                  ((Path(workspace["root"]), workspace["monitor_min_free_bytes"]),)))
        resource_path = receipt / "monitored_resource.json"
        write_json(resource_path, dict(base, state="MONITOR_TERMINAL", watch=watched))
        if watched["exit_code"] != 0 or watched["stop_reason"] or watched.get("cleanup_error"):
            raise ResourceRefusal("watched worker failed; inspect retained worker diagnostics")
        if (digest(request_path)["sha256"] != request_hash or sources != source_bindings(script)
                or inputs != [digest(Path(x["path"])) for x in inputs]):
            raise ResourceRefusal("source/input drift before output admission")
        candidate = read_request_json(scratch / "completion.json")
        if candidate["attempt_id"] != attempt or candidate["request_sha256"] != request_hash:
            raise ResourceRefusal("worker completion does not match this attempt")
        if cluster_first:
            matrix = candidate["run"].get("matrix_admission", {})
            matrix_path = scratch / "matrix_admission.json"
            if (matrix.get("relative_path") != "RESOURCE_ATTEMPT/scratch/matrix_admission.json"
                    or matrix.get("sha256") != digest(matrix_path)["sha256"]
                    or matrix.get("retained_n") != candidate["run"].get("points")):
                raise ResourceRefusal("post-cluster matrix admission binding mismatch")
            matrix_record = read_request_json(matrix_path)
            if (matrix_record.get("state") != "ADMITTED" or matrix_record.get("limits") != limits
                    or matrix_record.get("retained_n") != matrix.get("retained_n")
                    or matrix_record.get("estimate") != matrix.get("estimate")):
                raise ResourceRefusal("post-cluster matrix admission receipt mismatch")
        expected_names = {f"PCOA_{a.set}.tsv", f"REFERENCE_CLUSTERS_{a.set}.tsv"}
        scientific_names = set(expected_names)
        if request["keep_allvsall"]:
            expected_names.add("allvsall.tsv.gz")
            retained = candidate["run"].get("retained_allvsall", {})
            if (retained.get("relative_path") != "allvsall.tsv.gz"
                    or retained.get("sha256") != candidate["outputs"].get("allvsall.tsv.gz", {}).get("sha256")):
                raise ResourceRefusal("retained all-vs-all receipt binding mismatch")
        elif "retained_allvsall" in candidate["run"]:
            raise ResourceRefusal("unrequested retained all-vs-all output")
        if set(candidate["outputs"]) != expected_names:
            raise ResourceRefusal("unexpected worker output roster")
        for name, record in candidate["outputs"].items():
            if record != digest(scratch / name):
                raise ResourceRefusal("worker output hash mismatch")
        clean_path(target)
        clean_path(receipt)
        # No blanket directory copy: admit the exact scientific/opt-in replay output roster.
        for name in sorted(expected_names):
            source = clean_path(scratch / name)
            with source.open("rb") as inp, (target / name).open("xb") as out:
                shutil.copyfileobj(inp, out, 1024 * 1024)
            if digest(target / name)["sha256"] != candidate["outputs"][name]["sha256"]:
                raise ResourceRefusal("promoted scientific output changed")
        run = dict(candidate["run"], resource_schema=SCHEMA, attempt_id=attempt,
                   request_sha256=request_hash, inputs=inputs, producer_sources=sources,
                   producer_runtime=candidate["runtime"], diamond=candidate["diamond"],
                   resource_receipt={"relative_path": "RESOURCE_ATTEMPT/monitored_resource.json",
                                     "sha256": digest(resource_path)["sha256"]},
                   outputs={name: digest(target / name) for name in sorted(scientific_names)})
        run_path = target / f"RUN_{a.set}.json"
        write_json(run_path, run)
        write_json(receipt / "terminal.json", dict(base, state="SUCCEEDED", run=digest(run_path)))
        return run
    except (ResourceRefusal, ValidationRefused, OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        write_json(receipt / "terminal.json", dict(base, state="FAILED", reason=str(exc)))
        raise ResourceRefusal(str(exc)) from exc
