"""Internal bounded-process and existing-interpreter support for release tests.

Importing this module performs no probes, starts no processes and writes no files.
The runner admits POSIX process-tree monitoring explicitly; it never installs a runtime.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from typing import Callable


ENVIRONMENT_SCHEMA = "sapote-mamey.release-environment.v1"
DEFAULT_RSS_LIMIT = 3_800_000_000
DEFAULT_MIN_DISK = 2_000_000_000


class ValidationRefused(ValueError):
    """A measured admission or evidence requirement was not satisfied."""


class WatchedTermination(SystemExit):
    """A main-thread SIGTERM that must unwind owned-child cleanup before exit."""

    def __init__(self, signum: int):
        super().__init__(128 + signum)
        self.signum = signum

    def __str__(self):
        return "watched command interrupted by " + signal.Signals(self.signum).name


def _cleanup_on_sigterm(function):
    """Let Python unwind watcher cleanup on main-thread termination; restore policy.

    SIGKILL cannot be caught. Worker-thread callers retain their host's signal
    policy because only the main thread may install Python signal handlers.
    """
    @wraps(function)
    def watched(*args, **kwargs):
        if threading.current_thread() is not threading.main_thread():
            return function(*args, **kwargs)
        previous = signal.getsignal(signal.SIGTERM)
        def interrupt(signum, frame):
            # A second TERM must not interrupt the first TERM's child cleanup.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise WatchedTermination(signum)
        signal.signal(signal.SIGTERM, interrupt)
        try:
            return function(*args, **kwargs)
        finally:
            signal.signal(signal.SIGTERM, previous)
    return watched


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
        # Collapsing symlink-directory/.. can select a different executable.
        executable = Path(found)
        if not executable.is_absolute():
            executable = Path.cwd() / executable
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
        result = subprocess.run([ps, "-axo", "pid=,ppid=,pgid=,rss=,stat=,lstart="],
                                capture_output=True, text=True, check=True, timeout=5)
        rows = [line.split(maxsplit=5) for line in result.stdout.splitlines() if line.strip()]
        if not rows or any(len(row) != 6 for row in rows):
            raise ValueError("empty or malformed process snapshot")
        return {int(pid): (int(parent), int(group), int(rss) * 1024, birth)
                for pid, parent, group, rss, state, birth in rows if not state.startswith("Z")}
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
        self.root_finished = False
        self.scope_uncertain = False
        self.last_owned: dict = {}

    def refresh(self) -> dict[int, tuple[int, int, int, str]]:
        rows = _process_snapshot()
        root_row = rows.get(self.root)
        identity = self.known.get(self.root)
        root_valid = bool(root_row and not self.root_finished and
                          (identity is None or (root_row[1], root_row[3]) == identity))
        retained = {pid for pid, old in self.known.items()
                    if pid in rows and (rows[pid][1], rows[pid][3]) == old
                    and not (pid == self.root and self.root_finished)}
        anchor = root_valid or any(rows[pid][1] == self.root for pid in retained)
        group = {pid for pid, row in rows.items() if row[1] == self.root}
        self.scope_uncertain = bool(group and not anchor)
        members = retained | (group if anchor else set())
        if root_valid:
            members.add(self.root)
        elif root_row:
            members.discard(self.root)
        while True:
            expanded = members | {pid for pid, row in rows.items() if row[0] in members}
            if expanded == members:
                break
            members = expanded
        owned = {pid: rows[pid] for pid in members}
        self.known.update({pid: (row[1], row[3]) for pid, row in owned.items()})
        self.last_owned = owned
        return owned

    def stop(self, process: subprocess.Popen) -> str | None:
        """Signal a live owned group first; verify exits and retain denied/unknown cleanup."""
        error = None
        def observe():
            nonlocal error
            self.root_finished = process.poll() is not None
            try:
                owned = self.refresh()
                if self.scope_uncertain:
                    error = "PROCESS_CLEANUP_IDENTITY_UNCONFIRMED"
                return owned
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                error = "PROCESS_CLEANUP_MONITOR_ERROR: " + str(exc)
                return None
        for sig in (signal.SIGTERM, signal.SIGKILL):
            owned = observe()
            group_live = bool(owned and any(row[1] == self.root for row in owned.values()))
            # Direct-child lifetime also permits an emergency group stop when the
            # monitor fails, but absence of verification still remains an error.
            fallback = owned is None and process.poll() is None
            if (group_live and not self.scope_uncertain) or fallback:
                try:
                    os.killpg(process.pid, sig)
                    self.cleanup_events.append({'target':'group','pid':process.pid,
                                                'signal':sig.name,'status':'SENT'})
                except ProcessLookupError:
                    self.cleanup_events.append({'target':'group','pid':process.pid,
                                                'signal':sig.name,'status':'ALREADY_EXITED'})
                except OSError as exc:
                    after = observe()
                    exited = (process.poll() is not None and after is not None
                              and not self.scope_uncertain
                              and not any(row[1] == self.root for row in after.values()))
                    self.cleanup_events.append({'target':'group','pid':process.pid,'signal':sig.name,
                        'status':'ERROR_AFTER_VERIFIED_EXIT' if exited else 'SIGNAL_FAILED',
                        'errno':exc.errno,'error':str(exc)})
                    if not exited:
                        error = "PROCESS_CLEANUP_SIGNAL_FAILED: " + str(exc)
            # Detached, observed descendants retain their own birth-bound stop.
            for pid in sorted(owned or {}, reverse=True):
                current = observe()
                if current is None or pid not in current:
                    continue
                try:
                    os.kill(pid, sig)
                    self.cleanup_events.append({'target':'pid','pid':pid,'signal':sig.name,'status':'SENT'})
                except ProcessLookupError:
                    self.cleanup_events.append({'target':'pid','pid':pid,'signal':sig.name,'status':'ALREADY_EXITED'})
                except OSError as exc:
                    after = observe()
                    exited = after is not None and pid not in after
                    self.cleanup_events.append({'target':'pid','pid':pid,'signal':sig.name,
                        'status':'ERROR_AFTER_VERIFIED_EXIT' if exited else 'SIGNAL_FAILED','errno':exc.errno,'error':str(exc)})
                    if not exited:
                        error = "PROCESS_CLEANUP_SIGNAL_FAILED: " + str(exc)
            if process.poll() is None:
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.cleanup_events.append({'target':'root','pid':process.pid,
                        'status':'TERM_WAIT_EXPIRED_ESCALATING_TO_KILL' if sig == signal.SIGTERM else 'KILL_WAIT_EXPIRED'})
            deadline = time.monotonic() + 2.0
            while True:
                pending = observe()
                if process.poll() is not None and pending is not None and not pending:
                    break
                if time.monotonic() >= deadline:
                    self.cleanup_events.append({'target':'tree','pid':process.pid,
                        'status':'TERM_TREE_WAIT_EXPIRED' if sig == signal.SIGTERM else 'KILL_TREE_WAIT_EXPIRED'})
                    break
                time.sleep(0.02)
        remaining = observe()
        if process.poll() is None or remaining:
            error = error or "PROCESS_CLEANUP_LIVE_OWNED_MEMBERS_REMAIN"
        return error


def process_tree_rss(pid: int) -> int:
    """Measure a POSIX process group plus children; a failed probe is a refusal."""
    return sum(row[2] for row in _OwnedProcessTree(pid).refresh().values())


NICE_INCREMENT = 15


def _priority_not_applied(record: dict, message: str, strict: bool) -> dict:
    """Ruling 16: record and warn by default; refuse only under an explicit strict-priority request."""
    record["status"] = "NOT_APPLIED"
    record["message"] = message
    if strict:
        raise ValidationRefused("RESOURCE_POLICY_HOLD: " + message)
    # A direct stderr write: a warning, not a counted print/emit site.
    sys.stderr.write("WARNING: priority policy not applied: " + message + "\n")
    sys.stderr.flush()
    return record


PRIORITY_PROBE_TIMEOUT = 10.0
_PROBE_CAPTURE_BYTES = 65536  # per stream; anything beyond is read and discarded


def _wait_bounded(pid: int, deadline: float) -> int | None:
    """Reap ``pid`` by ``deadline``; return its wait status, or None if it is still running."""
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            return status
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.01)


def _kill_probe(pid: int, notes: list[str]) -> int:
    """SIGKILL the probe's own session and reap it. A probe that already exited is noted."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError as exc:
        notes.append(f"probe group already gone: {exc}")
    _, status = os.waitpid(pid, 0)
    return status


def verify_nice(nice: str | None, *, strict: bool = False,
                timeout: float = PRIORITY_PROBE_TIMEOUT) -> dict:
    """Check that `nice -n 15` really lowers a child's priority here, before relying on it.

    `nice` prints a warning and still runs the command when it cannot change priority (seen in
    a sandbox), so the argv alone does not show the policy took effect. A tiny probe child reports
    its own niceness. The result is returned as the receipt's `priority` record either way, with
    `status` APPLIED or NOT_APPLIED. NOT_APPLIED warns on stderr by default and is a
    RESOURCE_POLICY_HOLD refusal only when `strict` is true (ruling 16; the `strict_priority`
    keyword of `run_watched`). A probe that cannot start, exits nonzero, or does not finish within
    `timeout` seconds is NOT_APPLIED: it is killed and reaped, never waited on without a bound.
    Both probe pipes are drained together, so a probe that floods stderr cannot deadlock."""
    if not nice:
        record = {"requested_increment": NICE_INCREMENT, "expected_niceness": None,
                  "probe_niceness": None, "probe_stderr": "", "probe_pipe_close_errors": [],
                  "probe_timed_out": False}
        return _priority_not_applied(record, "no `nice` executable; the nice -n 15 policy cannot be applied",
                                     strict)
    expected = min(19, os.getpriority(os.PRIO_PROCESS, 0) + NICE_INCREMENT)  # lowest priority that counts
    probe = [nice, "-n", str(NICE_INCREMENT), sys.executable, "-I", "-c",
             "import os; print(os.getpriority(os.PRIO_PROCESS, 0))"]
    # posix_spawn, not subprocess: the probe must not depend on (or disturb) a caller's
    # subprocess.Popen, and it is a few milliseconds of work with no input.
    out_r, out_w = os.pipe(); err_r, err_w = os.pipe()
    close_errors: list[str] = []
    notes: list[str] = []
    chunks: dict[int, list[bytes]] = {out_r: [], err_r: []}
    kept = {out_r: 0, err_r: 0}
    spawn_error: OSError | None = None
    timed_out = False
    status: int | None = None
    try:
        try:
            pid = os.posix_spawn(nice, probe, dict(os.environ), setsid=True, file_actions=[
                (os.POSIX_SPAWN_DUP2, out_w, 1), (os.POSIX_SPAWN_DUP2, err_w, 2),
                (os.POSIX_SPAWN_CLOSE, out_r), (os.POSIX_SPAWN_CLOSE, err_r)])
        except OSError as exc:
            spawn_error = exc
            pid = None
        if pid is not None:
            os.close(out_w); out_w = -1; os.close(err_w); err_w = -1
            deadline = time.monotonic() + timeout
            with selectors.DefaultSelector() as selector:
                for fd in (out_r, err_r):
                    selector.register(fd, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        break
                    for key, _events in selector.select(remaining):
                        block = os.read(key.fd, 65536)
                        if not block:
                            selector.unregister(key.fd)
                        elif kept[key.fd] < _PROBE_CAPTURE_BYTES:
                            chunks[key.fd].append(block)
                            kept[key.fd] += len(block)
            if not timed_out:
                status = _wait_bounded(pid, deadline)
                timed_out = status is None
            if timed_out:
                status = _kill_probe(pid, notes)
    finally:
        for fd in (out_r, out_w, err_r, err_w):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError as exc:
                    # A failed close of a probe pipe does not change the measured niceness, but it
                    # is recorded in the receipt rather than dropped.
                    close_errors.append(f"fd {fd}: {type(exc).__name__}: {exc}")
    stdout = b"".join(chunks[out_r]).decode("utf-8", "replace").strip()
    stderr = b"".join(chunks[err_r]).decode("utf-8", "replace").strip()
    record = {"requested_increment": NICE_INCREMENT, "expected_niceness": expected,
              "probe_niceness": None, "probe_stderr": stderr[:500],
              "probe_pipe_close_errors": close_errors, "probe_timed_out": timed_out}
    if notes:
        record["probe_notes"] = notes
    if spawn_error is not None:
        return _priority_not_applied(
            record, f"priority probe could not start ({type(spawn_error).__name__}: {spawn_error})", strict)
    if timed_out:
        return _priority_not_applied(
            record, f"priority probe did not finish within {timeout:g} s; it was killed", strict)
    try:
        observed = int(stdout) if os.waitstatus_to_exitcode(status) == 0 else None
    except ValueError:
        observed = None
    record["probe_niceness"] = observed
    # The ceiling is 19 on Linux and 20 on macOS, so "at least the expected value" is the check.
    if observed is None or observed < expected:
        return _priority_not_applied(
            record, f"nice -n 15 did not take effect (expected niceness {expected}, probe saw {observed}; "
                    f"{record['probe_stderr'] or 'no message'})", strict)
    record["status"] = "APPLIED"
    return record


def _check_child_niceness(priority: dict, pid: int, strict: bool) -> str | None:
    """Read the launched child's own niceness; return a stop reason only under strict."""
    try:
        child = os.getpriority(os.PRIO_PROCESS, pid)
    except (ProcessLookupError, PermissionError) as exc:
        priority["child_check"] = f"not read: {type(exc).__name__}"
        return None
    priority["child_niceness"] = child
    expected = priority.get("expected_niceness")
    if expected is None or child >= expected:
        priority["child_check"] = "AT_EXPECTED_NICENESS"
        return None
    priority["child_check"] = "BELOW_EXPECTED_NICENESS"
    message = (f"the launched child runs at niceness {child}, not the expected {expected}, "
               "although the probe was reniced")
    try:
        _priority_not_applied(priority, message, strict)
    except ValidationRefused as exc:
        return str(exc)
    return None


@_cleanup_on_sigterm
def run_watched(
    command: list[str], *, cwd: Path, log: Path, env: dict[str, str],
    rss_limit: int = DEFAULT_RSS_LIMIT, min_disk: int = DEFAULT_MIN_DISK,
    timeout: float = 3600, poll_interval: float = 0.2,
    sampler: Callable[[int], int] = process_tree_rss,
    additional_disk_floors: tuple[tuple[Path, int], ...] = (),
    log_header: dict | None = None,
    strict_priority: bool = False,
) -> dict:
    """Run one command with fail-closed resource checks and an exclusive durable log.

    `strict_priority=True` refuses when `nice -n 15` cannot lower the child's priority; by default
    that is recorded in the receipt's `priority` field and warned. It is a keyword of this function
    only: no command-line front end passes it yet. When the probe shows the policy did not take
    effect, the command runs without the `nice` wrapper (`priority["wrapper"]` is "none"), never
    through a wrapper that was just seen to fail. When the wrapper is used, the launched child's own
    niceness is read once it starts (`priority["child_niceness"]`); a child that is not at the
    expected niceness downgrades the record to NOT_APPLIED (a RESOURCE_POLICY_HOLD stop under strict).

    Sampling is best-effort periodic observation, not a kernel-enforced memory limit.
    A stop reason invalidates the command even if it happens to return zero.
    """
    if os.name != "posix":
        raise ValidationRefused("Watched release validation currently requires POSIX process groups")
    nonfinite = any(isinstance(value, float) and not math.isfinite(value)
                    for value in (rss_limit, min_disk, timeout, poll_interval))
    if nonfinite or not command or rss_limit <= 0 or min_disk < 0 or timeout <= 0 or poll_interval <= 0:
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
    priority = verify_nice(nice, strict=strict_priority)  # warns, or refuses under strict_priority
    use_nice = bool(nice) and priority.get("status") == "APPLIED"
    argv = [nice, "-n", "15", *command] if use_nice else list(command)
    priority["wrapper"] = "nice -n 15" if use_nice else "none"
    priority["child_niceness"] = None
    child_checked = not use_nice
    with log.open("x", encoding="utf-8") as output:
        if log_header is not None:
            output.write("# sapote-suite-environment " + json.dumps(log_header, sort_keys=True) + "\n")
            output.flush()
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            raise ValidationRefused(f"Command could not start: {exc}") from exc
        tree = _OwnedProcessTree(process.pid)
        cleanup_error = None
        cleanup_attempted = False
        cleanup_report = None
        def cleanup(original=None):
            nonlocal cleanup_error, cleanup_attempted, cleanup_report
            cleanup_attempted = True
            cleanup_error = tree.stop(process) or cleanup_error
            if cleanup_error:
                cleanup_report = log.with_name(log.name + '.cleanup-' + uuid.uuid4().hex + '.json')
                atomic_json(cleanup_report, {'status':'CLEANUP_UNCONFIRMED', 'error':cleanup_error,
                    'original_interruption':str(original) if original is not None else None,
                    'root_returncode':process.poll(), 'remaining_observed_pids':sorted(tree.last_owned),
                    'scope_uncertain':tree.scope_uncertain, 'events':tree.cleanup_events,
                    'checked_utc':utc_now()})
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
                if not stop and not child_checked and time.monotonic() - clock_start >= poll_interval:
                    child_checked = True
                    stop = _check_child_niceness(priority, process.pid, strict_priority)
                if stop:
                    cleanup()
                    break
                if process.poll() is not None:
                    break
                time.sleep(poll_interval)
        except BaseException as original:
            cleanup(original)
            if cleanup_error:
                raise ValidationRefused("Interrupted command cleanup is unconfirmed; retain " + str(cleanup_report)) from original
            raise
        finally:
            if process.poll() is None and not cleanup_attempted:
                cleanup()
        if not cleanup_attempted:
            cleanup()
        code = process.poll()
        if code is None:
            raise ValidationRefused("Owned command remains live after bounded cleanup; retain " + str(cleanup_report))
        if cleanup_error and stop is None:
            stop = cleanup_error
    return {"argv": argv, "priority": priority, "cwd": str(cwd), "started_utc": started, "completed_utc": utc_now(),
            "exit_code": code, "stop_reason": stop, "cleanup_error": cleanup_error,
            "cleanup_events": tree.cleanup_events, "cleanup_report": str(cleanup_report) if cleanup_report else None,
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
