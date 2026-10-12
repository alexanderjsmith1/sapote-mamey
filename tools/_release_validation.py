"""Internal bounded-process and existing-interpreter support for release tests.

Importing this module performs no probes, starts no processes and writes no files.
The runner admits POSIX process-tree monitoring explicitly; it never installs a runtime.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Callable


ENVIRONMENT_SCHEMA = "sapote-mamey.release-environment.v1"
DEFAULT_RSS_LIMIT = 3_800_000_000
DEFAULT_MIN_DISK = 2_000_000_000


class ValidationRefused(ValueError):
    """A measured admission or evidence requirement was not satisfied."""


def utc_now() -> str:
    """Return an aware UTC timestamp in the receipt's canonical form."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: object) -> bytes:
    """Encode a deterministic JSON value for digesting."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_file(path: Path) -> str:
    """Hash a file without loading large executables or logs into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    """Replace an operational state file atomically, not immutable attempt evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as out:
        temporary = Path(out.name)
        try:
            json.dump(value, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)


def resolve_interpreter(requested: str | Path) -> Path:
    """Validate an available target, preserving its invocation path and venv context."""
    locator = os.fspath(requested)
    found = shutil.which(locator)
    if found is None:
        raise ValidationRefused(f"Python executable is unavailable: {locator}")
    try:
        executable = Path(os.path.abspath(found))
        target = executable.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationRefused(f"Cannot resolve Python executable: {locator}") from exc
    if not target.is_file() or not os.access(target, os.X_OK):
        raise ValidationRefused(f"Python is not an executable file: {executable}")
    return executable


def _process_snapshot() -> dict[int, tuple[int, int, int, str]]:
    """Read PID, parent, group, RSS and birth identity for scoped cleanup."""
    ps = shutil.which("ps")
    if os.name != "posix" or ps is None:
        raise ValidationRefused("POSIX ps process-tree monitoring is unavailable")
    try:
        result = subprocess.run([ps, "-axo", "pid=,ppid=,pgid=,rss=,lstart="],
                                capture_output=True, text=True, check=True, timeout=5)
        rows = [line.split(maxsplit=4) for line in result.stdout.splitlines() if line.strip()]
        if not rows or any(len(row) != 5 for row in rows):
            raise ValueError("empty or malformed process snapshot")
        return {int(pid): (int(parent), int(group), int(rss) * 1024, birth)
                for pid, parent, group, rss, birth in rows}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise ValidationRefused(f"Process-tree monitoring failed: {exc}") from exc


class _OwnedProcessTree:
    """Remember observed descendants even after their parent exits or they detach.

    PID reuse cannot transfer ownership: the process-group and birth identity must
    still match. Periodic observation is not a kernel sandbox; an unobserved child
    that detaches and exits its ancestry between snapshots is outside this proof.
    """

    def __init__(self, root: int):
        self.root = root
        self.known: dict[int, tuple[int, str]] = {}
        self.cleanup_events: list[dict] = []

    def refresh(self) -> dict[int, tuple[int, int, int, str]]:
        rows = _process_snapshot()
        members = {self.root} | {pid for pid, (_, group, _, _) in rows.items() if group == self.root}
        members |= {pid for pid, identity in self.known.items()
                    if pid in rows and (rows[pid][1], rows[pid][3]) == identity}
        while True:
            expanded = members | {pid for pid, (parent, _, _, _) in rows.items() if parent in members}
            if expanded == members:
                break
            members = expanded
        owned = {pid: row for pid, row in rows.items() if pid in members}
        self.known.update({pid: (row[1], row[3]) for pid, row in owned.items()})
        return owned

    def stop(self, process: subprocess.Popen) -> str | None:
        """Stop the owned group and each observed detached descendant, retaining failures."""
        error = None
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                owned = self.refresh()
                for pid in sorted(owned, reverse=True):
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        self.cleanup_events.append({'target':'pid', 'pid':pid,
                                                    'signal':sig.name, 'status':'ALREADY_EXITED'})
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                error = "PROCESS_CLEANUP_MONITOR_ERROR: " + str(exc)
            # The owned root group can still be stopped if the snapshot disappears.
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                self.cleanup_events.append({'target':'group', 'pid':process.pid,
                                            'signal':sig.name, 'status':'ALREADY_EXITED'})
            if sig == signal.SIGTERM:
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.cleanup_events.append({'target':'root', 'pid':process.pid,
                                                'status':'TERM_WAIT_EXPIRED_ESCALATING_TO_KILL'})
        process.wait()
        return error


def process_tree_rss(pid: int) -> int:
    """Measure a POSIX process group plus children; a failed probe is a refusal."""
    return sum(row[2] for row in _OwnedProcessTree(pid).refresh().values())


def run_watched(
    command: list[str], *, cwd: Path, log: Path, env: dict[str, str],
    rss_limit: int = DEFAULT_RSS_LIMIT, min_disk: int = DEFAULT_MIN_DISK,
    timeout: float = 3600, poll_interval: float = 0.2,
    sampler: Callable[[int], int] = process_tree_rss,
    additional_disk_floors: tuple[tuple[Path, int], ...] = (),
) -> dict:
    """Run one command with fail-closed resource checks and an exclusive durable log.

    Sampling is best-effort periodic observation, not a kernel-enforced memory limit.
    A stop reason invalidates the command even if it happens to return zero.
    """
    if os.name != "posix":
        raise ValidationRefused("Watched release validation currently requires POSIX process groups")
    if not command or rss_limit <= 0 or min_disk < 0 or timeout <= 0 or poll_interval <= 0:
        raise ValidationRefused("Invalid watched-command resource policy")
    cwd = cwd.resolve(strict=True)
    if not cwd.is_dir():
        raise ValidationRefused(f"Working directory is not a directory: {cwd}")
    disk_floors = {cwd: min_disk}
    for path, floor in additional_disk_floors:
        if isinstance(floor, bool) or not isinstance(floor, int) or floor < 0:
            raise ValidationRefused("Invalid additional disk floor")
        path = Path(path).resolve(strict=True)
        if not path.is_dir():
            raise ValidationRefused("Additional disk root must be a directory")
        disk_floors[path] = max(disk_floors.get(path, 0), floor)
    def low_disk_root():
        return next((str(path) for path, floor in disk_floors.items()
                     if shutil.disk_usage(path).free < floor), None)
    sampler(os.getpid())  # Admit the monitor before any test process starts.
    if low_disk_root() is not None:
        raise ValidationRefused("Insufficient free disk before command start")
    disk_stop_root = None
    log.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now(); clock_start = time.monotonic(); peak = 0; stop = None
    nice = shutil.which("nice")
    argv = [nice, "-n", "15", *command] if nice else list(command)
    with log.open("x", encoding="utf-8") as output:
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            raise ValidationRefused(f"Command could not start: {exc}") from exc
        tree = _OwnedProcessTree(process.pid)
        cleanup_error = None
        try:
            while True:
                try:
                    owned = tree.refresh()
                    observed = (sum(row[2] for row in owned.values())
                                if sampler is process_tree_rss else sampler(process.pid))
                    if observed < 0:
                        raise ValidationRefused("Negative process-tree memory observation")
                    peak = max(peak, observed)
                    if observed >= rss_limit:
                        stop = "MEMORY_LIMIT"
                    elif (disk_stop_root := low_disk_root()) is not None:
                        stop = "DISK_LIMIT"
                    elif time.monotonic() - clock_start >= timeout:
                        stop = "TIME_LIMIT"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    stop = "MONITOR_ERROR: " + str(exc)
                if stop:
                    cleanup_error = tree.stop(process)
                    break
                if process.poll() is not None:
                    break
                time.sleep(poll_interval)
        except BaseException:
            tree.stop(process)
            raise
        finally:
            if process.poll() is None:
                cleanup_error = tree.stop(process)
        code = process.wait()
        # Also stop observed descendants that opened a separate process session.
        cleanup_error = tree.stop(process) or cleanup_error
        if cleanup_error and stop is None:
            stop = cleanup_error
    return {"argv": argv, "cwd": str(cwd), "started_utc": started, "completed_utc": utc_now(),
            "exit_code": code, "stop_reason": stop, "cleanup_error": cleanup_error,
            "cleanup_events": tree.cleanup_events,
            "observed_owned_processes": len(tree.known), "peak_process_tree_rss": peak,
            "rss_stop_bytes": rss_limit, "minimum_free_disk_bytes": min_disk,
            "disk_floors": [{"path": str(path), "min_free_bytes": floor} for path, floor in disk_floors.items()],
            "disk_stop_root": disk_stop_root,
            "timeout_seconds": timeout, "monitor_interval_seconds": poll_interval,
            "elapsed_seconds": time.monotonic() - clock_start,
            "log": str(log.resolve()), "log_sha256": sha256_file(log)}


_IDENTITY_PROBE = r'''
import hashlib, importlib.metadata, json, platform, sys
from pathlib import Path
import pytest
distributions = []
for distribution in importlib.metadata.distributions():
    metadata = distribution.read_text("METADATA") or ""
    record = distribution.read_text("RECORD") or ""
    distributions.append({"name": distribution.metadata.get("Name", ""),
        "version": distribution.version,
        "location": str(Path(distribution.locate_file("")).resolve()),
        "metadata_sha256": hashlib.sha256(metadata.encode()).hexdigest(),
        "record_sha256": hashlib.sha256(record.encode()).hexdigest()})
sys.stdout.write(json.dumps({"executable": str(Path(sys.executable).absolute()),
    "executable_target": str(Path(sys.executable).resolve()),
    "version": sys.version, "version_info": list(sys.version_info[:3]),
    "implementation": platform.python_implementation(), "platform": platform.platform(),
    "prefix": sys.prefix, "base_prefix": sys.base_prefix, "pytest_version": pytest.__version__,
    "distribution_binding": "installed metadata and RECORD hashes; not a recursive installed-code hash",
    "distributions": sorted(distributions, key=lambda row: (row["name"].casefold(), row["version"]))}))
'''

_VENV_PROBE = r'''
import encodings, json, sys
from pathlib import Path
import pip
prefix = Path(sys.prefix).resolve()
expected = Path(sys.argv[1]).resolve()
assert prefix == expected and sys.prefix != sys.base_prefix, (prefix, expected)
assert Path(pip.__file__).resolve().is_relative_to(prefix), pip.__file__
sys.stdout.write(json.dumps({"prefix": str(prefix), "base_prefix": sys.base_prefix,
    "encodings": encodings.__file__, "pip_version": pip.__version__, "isolated": True}))
'''


def admit_environment(
    requested: str | Path, *, output: Path, env: dict[str, str] | None = None,
    rss_limit: int = DEFAULT_RSS_LIMIT, min_disk: int = DEFAULT_MIN_DISK,
    probe_timeout: float = 120,
) -> dict:
    """Measure existing Python/pytest, dependencies and an offline temporary venv.

    Output must be a fresh external evidence directory. Failed logs and the disposable
    venv remain for diagnosis; a successful venv is removed after its evidence is saved.
    """
    executable = resolve_interpreter(requested)
    output = output.absolute()
    if output.exists():
        raise ValidationRefused(f"Environment evidence destination is occupied: {output}")
    output.mkdir(parents=True)
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Default TMPDIR is preserved. Runtime imports should not see an unrelated PYTHONPATH.
    probe_env = dict(child_env)
    probe_env.pop("PYTHONPATH", None)
    steps = []
    report = {"schema": ENVIRONMENT_SCHEMA, "status": "WORKING", "started_utc": utc_now(),
              "requested_executable": os.fspath(requested), "resolved_executable": str(executable),
              "executable_sha256": sha256_file(executable),
              "executable_target": str(executable.resolve(strict=True)), "steps": steps,
              "test_environment_sha256": hashlib.sha256(canonical_json(child_env)).hexdigest(),
              "visible_environment": {key: child_env.get(key) for key in [
                  "PATH", "PYTHONPATH", "TMPDIR", "PYTHONHASHSEED", "PYTHONOPTIMIZE",
                  "PYTEST_ADDOPTS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_PLUGINS"]}}
    scratch = output / "venv probe"
    try:
        if child_env.get("PYTHONOPTIMIZE") not in (None, "", "0"):
            raise ValidationRefused("Optimized Python execution is not admitted for release tests")
        if child_env.get("PYTEST_ADDOPTS"):
            raise ValidationRefused("Ambient PYTEST_ADDOPTS is not admitted; use the fixed release profile")
        identity = run_watched([str(executable), "-c", _IDENTITY_PROBE], cwd=output,
                               log=output / "identity.log", env=probe_env, rss_limit=rss_limit,
                               min_disk=min_disk, timeout=probe_timeout)
        steps.append(identity)
        if identity["exit_code"] or identity["stop_reason"]:
            raise ValidationRefused("Python/pytest identity probe failed; see identity.log")
        try:
            report["identity"] = json.loads((output / "identity.log").read_text())
        except (OSError, ValueError) as exc:
            raise ValidationRefused("Python identity probe did not produce valid JSON") from exc
        # Bind the invocation locator as well as the separately validated binary target.
        # This remains within the identity payload consumed by receipt verification.
        report["identity"]["invocation_executable"] = str(executable)
        report["identity"]["invocation_target"] = report["executable_target"]
        if executable.resolve(strict=True) != Path(report["executable_target"]) or sha256_file(executable) != report["executable_sha256"]:
            raise ValidationRefused("Python executable target changed during identity admission")
        if report["identity"]["version_info"] < [3, 12, 0]:
            raise ValidationRefused("Release validation requires Python 3.12 or newer")
        creation = run_watched([str(executable), "-m", "venv", str(scratch)], cwd=output,
                               log=output / "venv-create.log", env=probe_env,
                               rss_limit=rss_limit, min_disk=min_disk, timeout=probe_timeout)
        steps.append(creation)
        if creation["exit_code"] or creation["stop_reason"]:
            raise ValidationRefused("Offline temporary venv creation failed; see venv-create.log")
        probe = run_watched([str(scratch / "bin/python"), "-I", "-c", _VENV_PROBE, str(scratch)],
                            cwd=output, log=output / "venv-import.log", env=probe_env,
                            rss_limit=rss_limit, min_disk=min_disk, timeout=probe_timeout)
        steps.append(probe)
        if probe["exit_code"] or probe["stop_reason"]:
            raise ValidationRefused("Temporary venv cannot import stdlib and its own pip")
        report["venv_probe"] = json.loads((output / "venv-import.log").read_text())
        report["pyvenv_cfg"] = (scratch / "pyvenv.cfg").read_text()
        report["status"] = "READY"
        report["identity_sha256"] = hashlib.sha256(canonical_json({
            "executable_sha256": report["executable_sha256"], "identity": report["identity"],
            "test_environment_sha256": report["test_environment_sha256"],
        })).hexdigest()
        shutil.rmtree(scratch)
        report["successful_venv_scratch_removed"] = True
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report["status"] = "REFUSED"
        report["reason"] = str(exc)
    report["completed_utc"] = utc_now()
    atomic_json(output / "environment.json", report)
    return report
