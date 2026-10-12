"""Source-bound serial stage records with explicit retries and generated navigation.

STAGES_COMPLETE means the declared commands completed. Release-specific identity,
privacy, artifact verification and owner gates remain separate requirements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import stat
import shutil
import uuid

import _release_partition_runner as partition
import _release_partitions as contract
import _release_validation as support


SCHEMA = "sapote-mamey.release-stages.v1"
RESERVED = {"workflow.json", "STATUS.md", "00_START_HERE.md", "HANDOFF.md", "LOCK"}


@dataclass(frozen=True)
class Stage:
    """Declare the command, permitted source mutations and immutable output paths."""

    name: str
    argv: tuple[str, ...]
    source_changes: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    output_trees: tuple[str, ...] = ()
    retry_argv: tuple[str, ...] | None = None


def relative_path(value: str) -> Path:
    """Admit only explicit relative paths, never parent traversal or root aliases."""
    path = Path(value)
    contract.require(isinstance(value, str) and bool(value) and not path.is_absolute()
                     and ".." not in path.parts and path.parts and "." != value,
                     "stage path must be a nonempty safe relative path")
    return path


def source_snapshot(source: Path) -> dict:
    """Use the existing source digest's exclusions for a compact mutation ledger."""
    import verify_external_validation_receipt as existing
    partition.source_digest(source)  # The shared contract rejects source symlinks.
    result = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if (any(part in existing._SKIP_DIRS or part.endswith(".egg-info") for part in relative.parts)
                or path.name in existing._SKIP_NAMES or path.suffix in existing._SKIP_SUFFIXES
                or not path.is_file()):
            continue
        result[relative.as_posix()] = {"sha256": support.sha256_file(path), "bytes": path.stat().st_size,
                                       "mode": stat.S_IMODE(path.stat().st_mode)}
    return result


def mutation_rows(before: dict, after: dict) -> list[dict]:
    """Retain exact changed-file identities without copying whole source packages."""
    return [{"path": name, "before": before.get(name), "after": after.get(name)}
            for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)]


def output_inventory(output: Path, stage: Stage) -> list[dict]:
    """Bind explicit files and complete output trees, including their own child logs."""
    paths = set()
    for value in stage.outputs:
        path = output / relative_path(value)
        contract.require(path.is_file() and not path.is_symlink(), "declared stage output is missing or a symlink: " + value)
        paths.add(path)
    for value in stage.output_trees:
        tree = output / relative_path(value)
        contract.require(tree.is_dir() and not tree.is_symlink(), "declared output tree is missing or a symlink: " + value)
        for path in tree.rglob("*"):
            contract.require(not path.is_symlink(), "output tree contains a symlink")
            if path.is_file():
                paths.add(path)
    contract.require(all(path.resolve().is_relative_to(output.resolve()) for path in paths), "output escaped its root")
    return [{"path": path.relative_to(output).as_posix(), "sha256": support.sha256_file(path),
             "bytes": path.stat().st_size, "mode": stat.S_IMODE(path.stat().st_mode)} for path in sorted(paths)]


class Workflow:
    """Run one declared serial workflow and resume only its exact verified lineage."""

    def __init__(self, source: Path, output: Path, stages: tuple[Stage, ...], python: str, *,
                 inputs: tuple[dict, ...] = (), env: dict[str, str] | None = None,
                 rss_limit: int = support.DEFAULT_RSS_LIMIT, min_disk: int = support.DEFAULT_MIN_DISK,
                 timeout: float = 3600, context: dict | None = None, progress=None):
        self.source = source.resolve(strict=True); self.output = output.resolve()
        contract.require(self.source.is_dir() and not self.output.is_relative_to(self.source)
                         and not self.source.is_relative_to(self.output), "workflow source and output must be separate")
        contract.require(stages and len({s.name for s in stages}) == len(stages), "stage names must be nonempty and unique")
        declared_outputs = []
        for stage in stages:
            contract.require(stage.name and stage.argv and all(isinstance(a, str) and a for a in stage.argv), "empty stage declaration")
            for value in (*stage.source_changes, *stage.outputs, *stage.output_trees):
                relative_path(value)
            for value in (*stage.outputs, *stage.output_trees):
                contract.require(Path(value).parts[0] not in RESERVED | {"attempts", "admissions"}, "output uses a reserved workflow path")
                declared_outputs.append(value)
        contract.require(len(declared_outputs) == len(set(declared_outputs)), "stage outputs must not be overwritten by another stage")
        self.stages = stages; self.python = python; self.inputs = inputs
        self.context = json.loads(json.dumps(context or {})); self.progress = progress
        self.env = partition.test_environment(self.source, env)
        self.policy = {"rss_limit": rss_limit, "min_disk": min_disk, "timeout": timeout}
        contract.require(rss_limit > 0 and min_disk >= 0 and timeout > 0, "invalid workflow resource policy")
        definition = {"stages": [asdict(stage) for stage in stages], "inputs": list(inputs),
                      "context": self.context, "engine_sha256": support.sha256_file(Path(__file__)),
                      "machinery_sha256": partition.machinery_digest(), "resource_policy": self.policy}
        self.definition_sha256 = hashlib.sha256(support.canonical_json(definition)).hexdigest()
        self.data = None

    def expand(self, arguments: tuple[str, ...], reason: str | None = None) -> list[str]:
        """Expand declared path tokens without evaluating shell text or Python format code."""
        tokens = {"{SOURCE}": str(self.source), "{OUT}": str(self.output),
                  "{PYTHON}": self.environment["resolved_executable"], "{RETRY_REASON}": reason or ""}
        result = []
        for argument in arguments:
            for token, value in tokens.items():
                argument = argument.replace(token, value)
            result.append(argument)
        return result

    def check_inputs(self):
        """Reference external evidence in place and refuse any changed binding."""
        for reference in self.inputs:
            path = Path(reference["path"])
            contract.require(path.is_file() and support.sha256_file(path) == reference["sha256"], "external workflow input changed")

    def record_refusal(self, reason: str):
        """Preserve the prior root record and make a refused resume visible now."""
        directory = self.output / "refusals" / uuid.uuid4().hex
        directory.mkdir(parents=True)
        before = directory / "workflow_before.json"
        before.write_bytes((self.output / "workflow.json").read_bytes())
        event = {"schema": "sapote-mamey.workflow-resume-refusal.v1", "reason": reason,
                 "checked_utc": support.utc_now(), "prior_record": partition.artifact(self.output, before)}
        support.atomic_json(directory / "refusal.json", event)
        self.data.setdefault("resume_refusals", []).append(partition.artifact(self.output, directory / "refusal.json"))
        self.data.update(status="REFUSED_RESUME", reason=reason)
        self.save()

    def save(self):
        """Update the one authoritative record, then render all operational pages."""
        support.atomic_json(self.output / "workflow.json", self.data)
        lines = ["# Release stage record", "", "state: " + self.data["status"], "",
                 "Authority: [workflow.json](workflow.json). These pages are generated from that record.", "",
                 "STAGES_COMPLETE describes command execution, not a seal, publication or scientific acceptance.", "",
                 "| Stage | State | Attempts |", "| --- | --- | --- |"]
        lines.extend(f"| {stage['name']} | {stage['status']} | {len(stage['attempts'])} |" for stage in self.data["stages"])
        if self.data.get("context"):
            lines.extend(["", "Declared context: `" + json.dumps(self.data["context"], sort_keys=True) + "`."])
        if self.data.get("reason"):
            lines.extend(["", "Current reason: " + self.data["reason"] + "."])
        lines.extend(["", "Source digest: `" + self.data["committed_source_sha256"] + "`.",
                      "", "linux_py312_ci: NOT_RUN_LOCALLY unless an independent measured receipt establishes it.", "",
                      "No seal, tag, push or publication is performed by this stage engine.", ""])
        text = "\n".join(lines)
        for name in ("STATUS.md", "00_START_HERE.md", "HANDOFF.md"):
            path = self.output / name
            temporary = path.with_suffix(".md.tmp")
            temporary.write_text(text)
            temporary.replace(path)

    def check_history(self):
        """Verify immutable attempts, complete output trees and the committed source chain."""
        contract.require(self.data.get("context", {}) == self.context, "workflow context changed")
        contract.require(isinstance(self.data.get("stages"), list) and len(self.data["stages"]) == len(self.stages),
                         "workflow stage list is incomplete")
        _, environment = partition.read_artifact(self.output, self.data.get("environment"))
        contract.require(environment.get("status") == "READY"
                         and environment.get("identity_sha256") == self.data["environment_identity_sha256"],
                         "recorded workflow environment is inconsistent")
        measured_identity = hashlib.sha256(support.canonical_json({
            "executable_sha256": environment.get("executable_sha256"), "identity": environment.get("identity"),
            "test_environment_sha256": environment.get("test_environment_sha256")})).hexdigest()
        contract.require(measured_identity == self.data["environment_identity_sha256"], "workflow environment identity payload changed")
        parent = Path(self.data["environment"]["path"]).parent
        contract.require(len(environment.get("steps", [])) == 3, "workflow admission evidence is incomplete")
        for step in environment["steps"]:
            log = self.output / parent / Path(step.get("log", "")).name
            contract.require(log.is_file() and support.sha256_file(log) == step.get("log_sha256")
                             and step.get("exit_code") == 0 and step.get("stop_reason") is None,
                             "workflow admission log changed")
            contract.validate_age(step)
        chain = self.data["initial_source_sha256"]
        for declared, state in zip(self.stages, self.data["stages"]):
            contract.require(state["name"] == declared.name, "stage order changed")
            for index, entry in enumerate(state["attempts"]):
                _, started = partition.read_artifact(self.output, entry["started"])
                contract.require(started.get("source_before") == chain, "attempt source lineage changed")
                logical = declared.retry_argv if entry.get("retry_reason") and declared.retry_argv else declared.argv
                contract.require(started.get("logical_command") == list(logical)
                    and started.get("definition_sha256") == self.definition_sha256
                    and started.get("stage") == declared.name and started.get("retry_reason") == entry.get("retry_reason"),
                    "attempt declared command or binding changed")
                if index:
                    contract.require(isinstance(entry.get("retry_reason"), str) and bool(entry["retry_reason"].strip()), "retry disposition is missing")
                else:
                    contract.require(entry.get("retry_reason") is None, "initial attempt is mislabeled as retry")
                if entry.get("receipt"):
                    _, final = partition.read_artifact(self.output, entry["receipt"])
                    contract.require(final.get("definition_sha256") == self.definition_sha256
                                     and final.get("retry_reason") == entry.get("retry_reason")
                                     and final.get("command") == started.get("command")
                                     and final.get("logical_command") == started.get("logical_command")
                                     and final.get("source_before") == chain
                                     and final.get("stage") == declared.name, "attempt definition or disposition changed")
                    log = (self.output / final["log"]["path"]).resolve() if final.get("log") else None
                    if log is not None:
                        contract.require(log.is_relative_to(self.output) and log.is_file()
                                         and support.sha256_file(log) == final["log"]["sha256"], "attempt log changed")
                    contract.require(index == len(state["attempts"]) - 1 or final["status"] != "PASS", "a completed stage was retried")
            if state["status"] != "PASS":
                break
            contract.require(state["attempts"] and state["active"] == state["attempts"][-1]["receipt"], "stage active evidence is not its final attempt")
            _, receipt = partition.read_artifact(self.output, state["active"])
            contract.require(receipt["status"] == "PASS" and receipt["watch"]["exit_code"] == 0
                             and receipt["watch"]["stop_reason"] is None, "stage process is not green")
            watch = receipt["watch"]
            nice = shutil.which("nice")
            expected_argv = [nice, "-n", "15", *receipt["command"]] if nice else receipt["command"]
            contract.require(watch.get("argv") == expected_argv
                and watch.get("rss_stop_bytes") == self.policy["rss_limit"]
                and watch.get("minimum_free_disk_bytes") == self.policy["min_disk"]
                and watch.get("timeout_seconds") == self.policy["timeout"]
                and 0 <= watch.get("peak_process_tree_rss", -1) < self.policy["rss_limit"], "stage command or resource observation changed")
            contract.validate_age(receipt)
            contract.require(receipt["outputs"] == output_inventory(self.output, declared), "stage output inventory changed")
            contract.require(all(row["path"] in declared.source_changes for row in receipt["source_changes"]), "undeclared source mutation")
            chain = receipt["source_after"]
        contract.require(chain == self.data["committed_source_sha256"], "committed source lineage is inconsistent")
        contract.require(partition.source_digest(self.source) == chain, "source differs from the last committed stage; preserve diagnostics and rebuild before resume")

    def verify(self, expected_sha256: str, admission: Path) -> dict:
        """Independently check a completed root without executing stages or editing it."""
        path = self.output / "workflow.json"
        contract.require(support.sha256_file(path) == expected_sha256, "workflow root SHA-256 mismatch")
        self.data = json.loads(path.read_text())
        contract.require(self.data.get("schema") == SCHEMA
            and self.data.get("definition_sha256") == self.definition_sha256
            and self.data.get("status") == "STAGES_COMPLETE", "workflow is incomplete or its definition changed")
        self.check_inputs(); self.check_history()
        contract.require(not admission.resolve().is_relative_to(self.source), "verification evidence is inside source")
        if admission.resolve().is_relative_to(self.output):
            contract.require(not any(admission.resolve().is_relative_to(self.output / value)
                for stage in self.stages for value in (*stage.outputs, *stage.output_trees)),
                "verification evidence would modify a bound stage output")
        environment = support.admit_environment(self.python, output=admission, env=self.env,
            rss_limit=self.policy["rss_limit"], min_disk=self.policy["min_disk"])
        contract.require(environment["status"] == "READY"
            and environment["identity_sha256"] == self.data["environment_identity_sha256"], "current workflow environment differs")
        self.check_inputs(); self.check_history()
        contract.require(support.sha256_file(path) == expected_sha256, "workflow root changed during verification")
        receipt = {"schema": "sapote-mamey.release-stages-verification.v1", "status": "VERIFIED_STAGES",
            "root_sha256": expected_sha256, "source_sha256": self.data["committed_source_sha256"],
            "environment_identity_sha256": environment["identity_sha256"], "context": self.context,
            "owner_adoption": "NOT_AUTHORIZED", "checked_utc": support.utc_now()}
        support.atomic_json(admission / "workflow-verification.json", receipt)
        return receipt

    def run(self, *, resume: bool = False, retry: dict[str, str] | None = None) -> dict:
        """Execute remaining declared stages after binding and verifying all reusable work."""
        events = self.iter_run(resume=resume, retry=retry)
        try:
            while True:
                try:
                    message = next(events)
                except StopIteration as completed:
                    return completed.value
                if self.progress:
                    self.progress(message)
        finally:
            events.close()

    def iter_run(self, *, resume: bool = False, retry: dict[str, str] | None = None):
        """Yield each stage announcement before execution; return the completed record.

        Consumers must exhaust or close the iterator. Closing at an announcement
        records failure and releases the workflow lock without executing that stage.
        """
        retry = retry or {}
        contract.require(set(retry) <= {stage.name for stage in self.stages}, "retry names an unknown stage")
        if not resume:
            self.check_inputs()
            self.output.mkdir(parents=True, exist_ok=False)
        contract.require(self.output.is_dir(), "resume workflow root is missing")
        with partition.exclusive(self.output):
            path = self.output / "workflow.json"
            if resume:
                self.data = json.loads(path.read_text())
                try:
                    contract.require(self.data.get("schema") == SCHEMA and self.data.get("definition_sha256") == self.definition_sha256,
                                     "workflow definition or schema changed")
                    self.check_inputs(); self.check_history()
                except (OSError, ValueError) as exc:
                    if isinstance(self.data, dict) and self.data.get("schema") == SCHEMA:
                        self.record_refusal(str(exc))
                    raise
            if not resume:
                digest = partition.source_digest(self.source)
                self.data = {"schema": SCHEMA, "status": "ADMITTING", "definition_sha256": self.definition_sha256,
                             "context": self.context, "initial_source_sha256": digest, "committed_source_sha256": digest,
                             "environment_identity_sha256": None, "environment": None,
                             "started_utc": support.utc_now(),
                             "stages": [{"name": stage.name, "status": "PENDING", "attempts": []} for stage in self.stages]}
                self.save()
            directory = self.output / "admissions" / uuid.uuid4().hex
            self.environment = support.admit_environment(self.python, output=directory, env=self.env,
                rss_limit=self.policy["rss_limit"], min_disk=self.policy["min_disk"])
            if self.environment["status"] != "READY":
                self.data.update(status="REFUSED_ENVIRONMENT", reason="workflow environment refused; inspect admission evidence",
                    latest_environment=partition.artifact(self.output, directory / "environment.json"))
                self.save()
                raise support.ValidationRefused(self.data["reason"])
            if resume:
                if self.data["environment_identity_sha256"] != self.environment["identity_sha256"]:
                    self.record_refusal("workflow environment changed")
                    raise support.ValidationRefused("workflow environment changed")
            else:
                self.data.update(status="WORKING", environment_identity_sha256=self.environment["identity_sha256"],
                    environment=partition.artifact(self.output, directory / "environment.json"))
                self.save()
            try:
                for declared, state in zip(self.stages, self.data["stages"]):
                    if state["status"] == "PASS":
                        contract.require(declared.name not in retry, "cannot retry an already green stage")
                        continue
                    reason = retry.get(declared.name)
                    if state["status"] != "PENDING":
                        contract.require(isinstance(reason, str) and reason.strip(), "failed or interrupted workflow stage requires a retry reason: " + declared.name)
                    else:
                        contract.require(reason is None, "pending stage is not a retry")
                    yield "Release stage: " + declared.name + (" (explicit retry)" if reason else "")
                    self.execute(declared, state, reason)
                self.data.pop("reason", None)
                self.data.update(status="STAGES_COMPLETE", completed_utc=support.utc_now())
                self.save(); self.check_history()
            except BaseException as exc:
                self.data.update(status="FAILED", reason=str(exc), completed_utc=support.utc_now())
                self.save()
                raise
        return self.data

    def execute(self, declared: Stage, state: dict, reason: str | None):
        """Write one immutable attempt; a failure never advances the committed source."""
        self.check_inputs()
        before_digest = partition.source_digest(self.source)
        contract.require(before_digest == self.data["committed_source_sha256"], "source drift between workflow stages")
        before = source_snapshot(self.source)
        directory = self.output / "attempts" / uuid.uuid4().hex
        directory.mkdir(parents=True)
        argv = self.expand(declared.retry_argv if reason and declared.retry_argv else declared.argv, reason)
        record = {"schema": "sapote-mamey.release-stage-attempt.v1", "status": "RUNNING", "stage": declared.name,
                  "definition_sha256": self.definition_sha256, "command": argv,
                  "logical_command": list(declared.retry_argv if reason and declared.retry_argv else declared.argv),
                  "source_before": before_digest,
                  "retry_reason": reason, "started_utc": support.utc_now()}
        support.atomic_json(directory / "started.json", record)
        entry = {"started": partition.artifact(self.output, directory / "started.json"), "retry_reason": reason}
        state["attempts"].append(entry); state["status"] = "RUNNING"; self.data["status"] = "WORKING"; self.save()
        try:
            watch = support.run_watched(argv, cwd=self.source, log=directory / "command.log", env=self.env,
                rss_limit=self.policy["rss_limit"], min_disk=self.policy["min_disk"], timeout=self.policy["timeout"])
            record["watch"] = watch
            contract.require(watch["exit_code"] == 0 and watch["stop_reason"] is None, "workflow stage failed or was stopped: " + declared.name)
            record["outputs"] = output_inventory(self.output, declared)
            record["status"] = "PASS"
        except BaseException as exc:
            record["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "FAILED"
            record["reason"] = str(exc)
            raise
        finally:
            record["source_after"] = partition.source_digest(self.source)
            record["source_changes"] = mutation_rows(before, source_snapshot(self.source))
            if any(row["path"] not in declared.source_changes for row in record["source_changes"]):
                record["status"] = "FAILED"; record["reason"] = "undeclared source mutation"
            log = directory / "command.log"
            if log.is_file():
                record["log"] = partition.artifact(self.output, log)
            record["completed_utc"] = support.utc_now()
            support.atomic_json(directory / "attempt.json", record)
            entry["receipt"] = partition.artifact(self.output, directory / "attempt.json")
            state["status"] = record["status"]
            if record["status"] == "PASS":
                state["active"] = entry["receipt"]
                self.data["committed_source_sha256"] = record["source_after"]
            self.save()
        contract.require(record["status"] == "PASS", record.get("reason", "stage did not pass"))
