"""Sequential, resumable pytest stages with immutable per-attempt evidence.

This runner implements an explicit partition profile. It does not cut archives,
replace monolithic receipts, install dependencies or authorize a seal.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

import _release_partitions as contract
import _release_validation as support


def source_digest(source: Path) -> str:
    """Reuse the bundle's exact existing path/mode/content digest contract."""
    from verify_external_validation_receipt import source_tree_sha256
    return source_tree_sha256(source)


def machinery_digest() -> str:
    """Bind the actual runner, recorder, support and reused source verifier."""
    import verify_external_validation_receipt as existing
    files = [Path(__file__), Path(contract.__file__), Path(support.__file__),
             Path(__file__).with_name("_release_pytest_evidence.py"), Path(existing.__file__)]
    return hashlib.sha256(support.canonical_json([
        {"name": path.name, "sha256": support.sha256_file(path)} for path in files])).hexdigest()


def test_environment(source: Path, supplied: dict[str, str] | None = None) -> dict[str, str]:
    """Set the declared serial thread policy while preserving the default TMPDIR."""
    import verify_external_validation_receipt as existing
    env = dict(os.environ if supplied is None else supplied)
    env.pop("PYTEST_CURRENT_TEST", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    # Pytest runs from source. Keep its package lookup relative, as the default
    # cut does, so children changing CWD do not inherit an importable bundle.
    # Recorder machinery stays explicit for plugin discovery in synthetic suites.
    env["PYTHONPATH"] = os.pathsep.join([str(Path(__file__).parent.resolve()),
                                       ".", str(Path(existing.__file__).parent.resolve())])
    return env


def binding(source: Path, environment: dict, size: int, policy: dict, *, baseline: bool = False) -> dict:
    """Bind test content, dependencies, fixed flags, machinery and resource policy."""
    value = contract.input_binding(source_sha256=source_digest(source),
        environment_sha256=environment["identity_sha256"], machinery_sha256=machinery_digest(),
        files_per_partition=size, purpose="baseline" if baseline else "final")
    value.pop("sha256")
    value["resource_policy"] = policy
    value["sha256"] = hashlib.sha256(support.canonical_json(value)).hexdigest()
    return value


def artifact(output: Path, path: Path) -> dict:
    """Reference durable evidence relative to its root, allowing folder relocation."""
    return {"path": path.relative_to(output).as_posix(), "sha256": support.sha256_file(path)}


def read_artifact(output: Path, reference: object) -> tuple[Path, dict]:
    """Refuse missing, changed or escaping evidence before loading a receipt."""
    contract.require(isinstance(reference, dict), "artifact reference is missing")
    locator = reference.get("path")
    contract.require(isinstance(locator, str) and locator and not Path(locator).is_absolute(),
                     "artifact path must be relative")
    path = (output / locator).resolve()
    contract.require(path.is_relative_to(output.resolve()) and path.is_file(), "artifact escapes or is missing")
    contract.require(support.sha256_file(path) == reference.get("sha256"), "artifact SHA-256 mismatch: " + locator)
    return path, json.loads(path.read_text())


@contextmanager
def exclusive(output: Path):
    """Use a kernel lock; a dead process cannot leave a permanent busy flag."""
    with (output / "LOCK").open("a") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise support.ValidationRefused("Another process owns this partition stage") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _check_attempt(output: Path, ref: dict, expected: dict, source: Path,
                   scheduled: list[str] | None, collect_only: bool) -> tuple[dict, dict]:
    """Independently verify one active attempt, its process log and actual node reports."""
    attempt_path, attempt = read_artifact(output, ref)
    contract.require(attempt.get("schema") == "sapote-mamey.pytest-partition-attempt.v1"
                     and attempt.get("collect_only") is collect_only, "attempt schema or mode mismatch")
    measured = expected.get("purpose") == "baseline" and not collect_only
    required_status = "MEASURED" if measured else "PASS"
    contract.require(attempt.get("status") == required_status, "active attempt is not " + required_status)
    contract.require(attempt.get("binding") == expected, "attempt input binding mismatch")
    contract.require(attempt.get("source_before") == attempt.get("source_after") == expected["source_tree_sha256"],
                     "source changed during an attempt")
    watch = attempt.get("watch", {})
    contract.require(watch.get("exit_code") in ({0, 1} if measured else {0}) and watch.get("stop_reason") is None,
                     "attempt process failed or was stopped")
    log_ref = attempt.get("log")
    contract.require(isinstance(log_ref, dict), "attempt log reference is missing")
    log = (output / log_ref.get("path", "")).resolve()
    contract.require(log.is_relative_to(output.resolve()) and log.is_file(), "attempt log escapes or is missing")
    contract.require(support.sha256_file(log) == log_ref.get("sha256") == watch.get("log_sha256"),
                     "attempt log SHA-256 mismatch")
    _, capture = read_artifact(output, attempt.get("capture"))
    contract.require(capture.get("rootpath") == str(source), "pytest root differs from source")
    command = attempt.get("command")
    contract.require(isinstance(command, list) and command[1:1 + len(contract.FLAGS)] == contract.FLAGS,
                     "attempt does not use the fixed full-suite profile")
    tail = command[1 + len(contract.FLAGS):]
    selected_files = list(dict.fromkeys(node.split("::", 1)[0] for node in (scheduled or [])))
    suffix = ["--collect-only"] if collect_only else selected_files
    token = attempt_path.parent.name
    contract.require(len(tail) == 8 + len(suffix)
                     and tail[:5] == ["--rootdir", str(source), "-p", "_release_pytest_evidence", "--release-evidence"]
                     and Path(tail[5]).is_absolute()
                     and Path(tail[5]).parts[-3:] == ("attempts", token, "capture.json")
                     and tail[6:8] == ["--basetemp", "/tmp/sapote-release-" + token]
                     and tail[8:] == suffix, "attempt command selection or evidence arguments changed")
    contract.require(capture.get("invocation_args") == command[3:], "pytest invocation differs from measured command")
    policy = expected["resource_policy"]
    contract.require(watch.get("rss_stop_bytes") == policy["rss_limit"]
                     and watch.get("minimum_free_disk_bytes") == policy["min_disk"]
                     and watch.get("timeout_seconds") == policy["timeout"]
                     and 0 <= watch.get("peak_process_tree_rss", -1) < policy["rss_limit"],
                     "attempt resource policy or observation differs from its binding")
    nice = shutil.which("nice")
    actual = [nice, "-n", "15", *command] if nice else command
    contract.require(watch.get("argv") == actual, "watched argv differs from the declared command")
    return capture, contract.validate_capture(capture, scheduled, collect_only=collect_only,
                                              measure_assertion_failures=measured)


def _check_history(output: Path, stage: dict, expected: dict) -> None:
    """Keep failures and interrupted attempts in the verified retry chain."""
    attempts = stage.get("attempts")
    admitted = {"PASS", "MEASURED"} if expected.get("purpose") == "baseline" else {"PASS"}
    contract.require(stage.get("status") in admitted and isinstance(attempts, list) and attempts,
                     "stage has no complete attempt history")
    prior = None
    for index, entry in enumerate(attempts):
        _, start = read_artifact(output, entry.get("started"))
        contract.require(start.get("binding") == expected and start.get("retry_of") == prior,
                         "attempt start or predecessor binding differs")
        reason = entry.get("retry_reason")
        contract.require(reason is None if index == 0 else isinstance(reason, str) and bool(reason.strip()),
                         "retry history has no explicit disposition")
        contract.require(start.get("retry_reason") == reason, "retry disposition differs from started evidence")
        final = entry.get("receipt")
        if final is not None:
            _, receipt = read_artifact(output, final)
            contract.require(receipt.get("binding") == expected and receipt.get("retry_reason") == reason
                             and receipt.get("retry_of") == prior, "attempt receipt history binding differs")
            contract.require(index == len(attempts) - 1 or receipt.get("status") not in admitted,
                             "green evidence was retried without a new stage")
        else:
            contract.require(index < len(attempts) - 1, "active attempt is interrupted")
        prior = (final or entry["started"])["sha256"]
    contract.require(attempts[-1].get("receipt") == stage.get("active"),
                     "active evidence is not the final documented attempt")


def verify_partition_receipt(receipt: Path, source: Path, expected_sha256: str,
                             expected_environment_sha256: str, *, baseline: bool = False) -> dict:
    """Verify explicit partition coverage and immutable evidence against current inputs."""
    source = source.resolve(strict=True)
    receipt = receipt.resolve(strict=True)
    output = receipt.parent
    contract.require(not receipt.is_relative_to(source), "receipt is inside the source tree")
    contract.require(support.sha256_file(receipt) == expected_sha256, "partition receipt SHA-256 mismatch")
    data = json.loads(receipt.read_text())
    contract.require(data.get("schema") == (contract.BASELINE_SCHEMA if baseline else contract.SCHEMA)
                     and data.get("status") == ("MEASURED" if baseline else "PASS"),
                     "partition receipt is not a PASS of the explicit partition schema")
    declared = data.get("binding", {})
    _, environment = read_artifact(output, data.get("environment"))
    contract.require(environment.get("status") == "READY", "environment is not admitted")
    contract.require(environment.get("identity_sha256") == expected_environment_sha256,
                     "environment differs from the current admitted identity")
    measured_identity = hashlib.sha256(support.canonical_json({
        "executable_sha256": environment.get("executable_sha256"), "identity": environment.get("identity"),
        "test_environment_sha256": environment.get("test_environment_sha256")})).hexdigest()
    contract.require(measured_identity == expected_environment_sha256, "environment identity payload differs")
    env_parent = Path(data["environment"]["path"]).parent
    contract.require(len(environment.get("steps", [])) == 3, "environment admission steps are incomplete")
    for step in environment["steps"]:
        env_log = (output / env_parent / Path(step.get("log", "")).name).resolve()
        contract.require(env_log.is_relative_to(output) and env_log.is_file()
                         and support.sha256_file(env_log) == step.get("log_sha256")
                         and step.get("exit_code") == 0 and step.get("stop_reason") is None,
                         "environment probe log or result differs")
        contract.validate_age(step)
    computed = binding(source, environment, declared.get("files_per_partition"), declared.get("resource_policy"), baseline=baseline)
    contract.require(computed == declared, "current source, environment, flags or machinery binding differs")
    _check_history(output, data.get("collection", {}), declared)
    collection, _ = _check_attempt(output, data.get("collection", {}).get("active"), declared, source, None, True)
    plan = contract.partition_plan(collection["collected"], declared["files_per_partition"])
    stages = data.get("partitions")
    contract.require(isinstance(stages, list) and len(stages) == len(plan), "partition plan is incomplete")
    union = []; counts = Counter(); subcounts = Counter()
    for stage, scheduled in zip(stages, plan):
        _check_history(output, stage, declared)
        contract.require(stage.get("plan") == scheduled, "partition plan differs from full collection")
        capture, summary = _check_attempt(output, stage.get("active"), declared, source,
                                           scheduled["expected_nodes"], False)
        contract.require(capture["collection_skips"] == [], "partition introduced collection skips")
        union.extend(capture["collected"])
        counts.update(summary["main_counts"]); subcounts.update(summary["subtest_counts"])
    contract.require(Counter(union) == Counter(collection["collected"]), "partition outcome union is incomplete or duplicated")
    totals = {"main_counts": dict(counts), "main_nodes": len(union),
              "collection_skips": len(collection["collection_skips"]), "subtest_counts": dict(subcounts)}
    contract.require(data.get("totals") == totals, "root summary differs from verified partition outcomes")
    contract.require(counts["passed"] > 0, "partition stage has no measured passing tests")
    contract.validate_age(data)
    return totals


def verified_counts(source: Path, receipt: Path, expected_sha256: str, *,
                    admission_output: Path, python: str, baseline: bool = False) -> tuple[dict, dict]:
    """Re-admit the current environment before a manifest consumes structured counts."""
    source = source.resolve(strict=True)
    contract.require(not admission_output.resolve().is_relative_to(source), "admission evidence is inside source")
    environment = support.admit_environment(python, output=admission_output, env=test_environment(source))
    contract.require(environment["status"] == "READY", "current manifest-consumer environment refused")
    totals = verify_partition_receipt(receipt, source, expected_sha256, environment["identity_sha256"], baseline=baseline)
    counts = {"passed": totals["main_counts"].get("passed", 0),
              "skipped": totals["main_counts"].get("skipped", 0) + totals["collection_skips"],
              "failed": totals["main_counts"].get("failed", 0),
              "subtest_counts": totals["subtest_counts"]}
    return counts, environment


def measure_manifest_subset(files: list[Path], source: Path, *, evidence: Path,
                            environment: dict) -> tuple[int, int, int, str]:
    """Measure a configured consumer subset; retain red calls, refuse execution errors.

This is explicitly a subset receipt, never eligible as full-suite validation.
Every invocation is watched and source-bound, including the pre-apply red run.
"""
    source = source.resolve(strict=True)
    contract.require(files and len(files) == len(set(files)), "manifest consumer subset is empty or duplicated")
    selected = [str(path.resolve(strict=True).relative_to(source)) for path in files]
    token = uuid.uuid4().hex
    directory = evidence / token
    directory.mkdir(parents=True, exist_ok=False)
    contract.require(not directory.resolve().is_relative_to(source), "manifest subset evidence is inside source")
    before = source_digest(source)
    command = [environment["resolved_executable"], *contract.FLAGS,
               "--rootdir", str(source), "-p", "_release_pytest_evidence", "--release-evidence", str(directory / "capture.json"),
               "--basetemp", "/tmp/sapote-release-" + token, *selected]
    record = {"schema": "sapote-mamey.manifest-consumer-subset.v1", "status": "WORKING",
              "started_utc": support.utc_now(), "source_before": before,
              "environment_identity_sha256": environment["identity_sha256"], "command": command,
              "selected_files": selected, "machinery_sha256": machinery_digest()}
    try:
        watch = support.run_watched(command, cwd=source, log=directory / "pytest.log", env=test_environment(source))
        record["watch"] = watch
        record["source_after"] = source_digest(source)
        contract.require(record["source_after"] == before, "manifest subset changed source")
        contract.require(watch["exit_code"] in {0, 1} and watch["stop_reason"] is None,
                         "manifest consumer subset failed to execute completely")
        capture = json.loads((directory / "capture.json").read_text())
        summary = contract.validate_capture(capture, measure_assertion_failures=True)
        actual_files = {node.split("::", 1)[0] for node in capture["collected"]}
        actual_files.update(row["nodeid"] for row in capture["collection_skips"])
        contract.require(actual_files == set(selected), "manifest subset selection differs from collected files")
        record["summary"] = summary
        record["status"] = "MEASURED"
        counts = summary["main_counts"]
        failures = counts.get("failed", 0) + summary["subtest_counts"].get("failed", 0)
        if watch["exit_code"] == 0:
            scratch = Path("/tmp/sapote-release-" + token)
            if scratch.exists():
                contract.require(scratch.is_dir() and not scratch.is_symlink(), "subset scratch is unsafe")
                shutil.rmtree(scratch)
                record["successful_scratch_removed"] = True
        return counts.get("passed", 0), counts.get("skipped", 0) + summary["collection_skips"], failures, (directory / "pytest.log").read_text()
    except BaseException as exc:
        record["status"] = "FAILED"; record["reason"] = str(exc)
        raise
    finally:
        for name in ("capture.json", "pytest.log"):
            path = directory / name
            if path.is_file():
                record[name] = artifact(evidence, path)
        record["completed_utc"] = support.utc_now()
        support.atomic_json(directory / "subset.json", record)


class PartitionRunner:
    """Execute and resume distinct attempts without silently replacing failures."""

    def __init__(self, source: Path, output: Path, python: str, *, files_per_partition: int = 20,
                 rss_limit: int = support.DEFAULT_RSS_LIMIT, min_disk: int = support.DEFAULT_MIN_DISK,
                 timeout: float = 3600, env: dict[str, str] | None = None, baseline: bool = False):
        self.source = source.resolve(strict=True)
        self.output = output.resolve()
        contract.require(self.source.is_dir(), "source is not a directory")
        contract.require(not self.output.is_relative_to(self.source) and not self.source.is_relative_to(self.output),
                         "source and evidence directories must be separate")
        contract.require(rss_limit > 0 and min_disk >= 0 and timeout > 0, "invalid resource policy")
        self.python = python; self.size = files_per_partition
        self.baseline = baseline
        self.policy = {"rss_limit": rss_limit, "min_disk": min_disk, "timeout": timeout}
        self.env = test_environment(self.source, env)
        self.record = None

    def save(self):
        """Atomically update the single resumable stage index."""
        support.atomic_json(self.output / "partition.json", self.record)

    def execute(self, stage: dict, *, collect_only: bool, retry_reason: str | None) -> dict:
        """Measure one attempt and save failures as well as successes."""
        token = uuid.uuid4().hex
        directory = self.output / "attempts" / token
        directory.mkdir(parents=True)
        expected = None if collect_only else stage["plan"]["expected_nodes"]
        args = ["--rootdir", str(self.source), "-p", "_release_pytest_evidence",
                "--release-evidence", str(directory / "capture.json"),
                "--basetemp", "/tmp/sapote-release-" + token]
        args.extend(["--collect-only"] if collect_only else stage["plan"]["files"])
        command = [self.resolved_python, *contract.FLAGS, *args]
        previous = stage["attempts"][-1] if stage["attempts"] else None
        retry_of = ((previous.get("receipt") or previous["started"])["sha256"] if previous else None)
        attempt = {"schema": "sapote-mamey.pytest-partition-attempt.v1", "status": "RUNNING",
                   "binding": self.record["binding"], "started_utc": support.utc_now(),
                   "command": command, "collect_only": collect_only, "retry_reason": retry_reason, "retry_of": retry_of,
                   "source_before": source_digest(self.source)}
        support.atomic_json(directory / "started.json", attempt)
        entry = {"started": artifact(self.output, directory / "started.json"),
                 "retry_reason": retry_reason}
        stage["attempts"].append(entry); stage["status"] = "RUNNING"; self.save()
        try:
            contract.require(attempt["source_before"] == self.record["binding"]["source_tree_sha256"],
                             "source drift before attempt")
            watch = support.run_watched(command, cwd=self.source, log=directory / "pytest.log",
                env=self.env, rss_limit=self.policy["rss_limit"], min_disk=self.policy["min_disk"],
                timeout=self.policy["timeout"])
            attempt["watch"] = watch
            attempt["log"] = artifact(self.output, directory / "pytest.log")
            attempt["source_after"] = source_digest(self.source)
            contract.require(attempt["source_after"] == attempt["source_before"], "source drift during attempt")
            measuring = self.baseline and not collect_only
            contract.require(watch["exit_code"] in ({0, 1} if measuring else {0}) and watch["stop_reason"] is None,
                             "pytest failed or watcher stopped the attempt")
            attempt["summary"] = contract.validate_capture(json.loads((directory / "capture.json").read_text()),
                                                           expected, collect_only=collect_only,
                                                           measure_assertion_failures=measuring)
            attempt["status"] = "MEASURED" if measuring else "PASS"
        except (OSError, ValueError) as exc:
            attempt["status"] = "FAILED"; attempt["reason"] = str(exc)
        except BaseException as exc:
            attempt["status"] = "INTERRUPTED"; attempt["reason"] = type(exc).__name__
            raise
        finally:
            capture_path = directory / "capture.json"
            if capture_path.is_file():
                attempt["capture"] = artifact(self.output, capture_path)
                try:
                    observed = json.loads(capture_path.read_text())
                except (OSError, ValueError):
                    observed = {}
                    attempt["status"] = "FAILED"
                    attempt["reason"] = "capture is missing or invalid JSON"
                completed = {r["nodeid"] for r in observed.get("outcomes", []) if r.get("outcome") != "incomplete"}
            else:
                completed = set()
            log_path = directory / "pytest.log"
            if log_path.is_file():
                attempt["log"] = artifact(self.output, log_path)
            attempt["missing_nodes"] = [node for node in (expected or []) if node not in completed]
            scratch = Path("/tmp/sapote-release-" + token)
            clean_green_scratch = (attempt["status"] == "PASS" or
                                  (attempt["status"] == "MEASURED" and attempt["watch"]["exit_code"] == 0))
            if clean_green_scratch and scratch.exists():
                # Only this UUID's known successful scratch, after durable capture/logs.
                try:
                    contract.require(scratch.is_dir() and not scratch.is_symlink(), "successful scratch is not a real directory")
                    shutil.rmtree(scratch)
                    attempt["successful_scratch_removed"] = True
                except (OSError, ValueError) as exc:
                    attempt["status"] = "FAILED"
                    attempt["reason"] = "successful scratch cleanup refused: " + str(exc)
            attempt["completed_utc"] = support.utc_now()
            support.atomic_json(directory / "attempt.json", attempt)
            entry["receipt"] = artifact(self.output, directory / "attempt.json")
            stage["status"] = attempt["status"]
            if attempt["status"] in {"PASS", "MEASURED"}:
                stage["active"] = entry["receipt"]
            self.save()
        return attempt

    def run(self, *, resume: bool = False, retry: dict[str, str] | None = None) -> dict:
        """Resume only bound green stages; require a stated reason for each red retry."""
        retry = retry or {}
        if not resume:
            self.output.mkdir(parents=True, exist_ok=False)
        contract.require(self.output.is_dir(), "resume evidence directory is missing")
        with exclusive(self.output):
            path = self.output / "partition.json"
            if resume:
                contract.require(path.is_file(), "resume index is missing")
                self.record = json.loads(path.read_text())
                contract.require(self.record.get("schema") == (contract.BASELINE_SCHEMA if self.baseline else contract.SCHEMA),
                                 "resume schema mismatch")
                old = self.record["binding"]
                contract.require(source_digest(self.source) == old["source_tree_sha256"]
                                 and machinery_digest() == old["machinery_sha256"], "source or machinery changed; start a new evidence root")
            environment_dir = self.output / "environments" / uuid.uuid4().hex
            environment = support.admit_environment(self.python, output=environment_dir, env=self.env,
                rss_limit=self.policy["rss_limit"], min_disk=self.policy["min_disk"])
            contract.require(environment["status"] == "READY", "environment preflight refused; see " + str(environment_dir))
            self.resolved_python = environment["resolved_executable"]
            current = binding(self.source, environment, self.size, self.policy, baseline=self.baseline)
            if resume:
                contract.require(self.record["binding"] == current, "resume environment, flags, grouping or resource policy changed")
            else:
                self.record = {"schema": contract.BASELINE_SCHEMA if self.baseline else contract.SCHEMA,
                               "status": "WORKING", "binding": current,
                               "started_utc": support.utc_now(), "environment": artifact(self.output, environment_dir / "environment.json"),
                               "collection": {"status": "PENDING", "attempts": []}, "partitions": []}
                self.save()
            try:
                collection = self.record["collection"]
                self._stage(collection, "collection", True, retry)
                collected, _ = _check_attempt(self.output, collection["active"], current, self.source, None, True)
                plan = contract.partition_plan(collected["collected"], self.size)
                if not self.record["partitions"]:
                    self.record["partitions"] = [{"plan": group, "status": "PENDING", "attempts": []} for group in plan]
                    self.save()
                contract.require([s["plan"] for s in self.record["partitions"]] == plan, "resume collection or plan changed")
                known = {"collection", *(s["plan"]["id"] for s in self.record["partitions"])}
                contract.require(set(retry) <= known, "retry names an unknown stage")
                counts = Counter(); subcounts = Counter()
                for stage in self.record["partitions"]:
                    self._stage(stage, stage["plan"]["id"], False, retry)
                    _, summary = _check_attempt(self.output, stage["active"], current, self.source,
                                                stage["plan"]["expected_nodes"], False)
                    counts.update(summary["main_counts"]); subcounts.update(summary["subtest_counts"])
                self.record.update(status="MEASURED" if self.baseline else "PASS", completed_utc=support.utc_now(),
                    totals={"main_counts": dict(counts), "main_nodes": len(collected["collected"]),
                            "collection_skips": len(collected["collection_skips"]), "subtest_counts": dict(subcounts)})
                self.save()
                verify_partition_receipt(path, self.source, support.sha256_file(path), environment["identity_sha256"],
                                         baseline=self.baseline)
            except BaseException as exc:
                self.record.update(status="FAILED", reason=str(exc), completed_utc=support.utc_now())
                self.save()
                raise
        return self.record

    def _stage(self, stage: dict, identifier: str, collect_only: bool, retry: dict[str, str]) -> None:
        """Keep verified green evidence, or execute one explicitly admitted attempt."""
        required_status = "MEASURED" if self.baseline and not collect_only else "PASS"
        if stage["status"] == required_status:
            _check_history(self.output, stage, self.record["binding"])
            _check_attempt(self.output, stage["active"], self.record["binding"], self.source,
                           None if collect_only else stage["plan"]["expected_nodes"], collect_only)
            contract.require(identifier not in retry, "a green stage must not be silently rerun")
            return
        reason = retry.get(identifier)
        if stage["status"] != "PENDING":
            contract.require(isinstance(reason, str) and bool(reason.strip()),
                             "failed or interrupted stage requires an explicit retry reason: " + identifier)
        else:
            contract.require(reason is None, "pending stage does not require a retry disposition")
        result = self.execute(stage, collect_only=collect_only, retry_reason=reason)
        contract.require(result["status"] == required_status,
                         "stage failed: " + identifier + ": " + result.get("reason", "incomplete"))
