"""Opt-in actual single-run transaction; no unbound source or early master publication."""
from contextlib import redirect_stdout, redirect_stderr
from copy import copy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import shutil
import tempfile
import uuid
import os

from .archive_snapshot import ArchiveSnapshotPolicy
from .intake_session import CapturedIntakeSession, CapturedIntakeHold, EvidenceOptions, encode
from . import source_context
from .output_transaction import preflight_output_roster, publish_payloads


class RunFrame:
    def __init__(self, session, source, stage, final, master_stage, master_final, source_aliases=None):
        self.session = session
        self.source_sha256 = session.snapshot.input_sha256
        self.source_path = source_context.lexical_locator(source)
        self.source_aliases = frozenset(source_aliases or (self.source_path, Path(source).resolve()))
        self.stage, self.final = stage, final
        self.master_stage, self.master_final = master_stage, master_final
        self.bound = self.working = None
        self.region_count = None
        self.execution_options = None
        self.governance = None
        self.pin_origin = "OPERATOR_EXPECTED" if session.expected_sha256 else "CONSUMED_UNASSERTED"

    def display(self, text):
        if self.master_stage is not None:
            text = text.replace(str(self.master_stage), str(self.master_final))
        return text.replace(str(self.stage / "runs"), str(self.final))

    def output_status(self, status):
        result = dict(status)
        locator = result.get("path")
        if result.get("state") == "PRODUCED" and locator:
            physical = str(locator)
            if self.master_final is not None and physical == str(self.master_final):
                physical = str(self.master_stage)
            elif physical.startswith(str(self.final) + "/"):
                physical = str(self.stage / "runs") + physical[len(str(self.final)):]
            path = Path(physical)
            if path.is_file():
                result["checksum_sha256_head16"] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            result["path"] = self.display(str(locator))
        return result

    def receipt(self):
        snapshot = self.session.snapshot
        return {"schema": "sapote.captured-run-source.v1", "input_sha256": snapshot.input_sha256,
                "original_version": "EXPECTED_DIGEST_MATCHED" if self.pin_origin == "OPERATOR_EXPECTED" else "ORIGINAL_VERSION_UNASSERTED",
                "pin_origin": self.pin_origin,
                "replay_version_verified": bool(self.session.expected_sha256),
                "capture_policy": asdict(self.session.policy),
                "execution_options": self.execution_options,
                "governance": self.governance.binding() if self.governance is not None else None,
                "verified_uncompressed_bytes": snapshot.verified_uncompressed_bytes,
                "genbank": self.genbank,
                "denominator": {"kind": "PARSED_BGC_RECORDS", "value": self.region_count,
                                "expected_biological_total": None, "whole_assembly_completeness": "UNKNOWN"},
                "evidence_parse_origin_sha256": self.bound.payload_sha256 if self.bound else None,
                "source_completeness": self.working.get("source_completeness") if self.working else None,
                "scope": "configured gold run; no figures/HMM/reference completion",
                "biological_absence": "NOT_ESTABLISHED", "upstream_search_completion": "NOT_ESTABLISHED"}


class StagedStream:
    """Keep progress visible, labelled staged until final publication commits."""
    def __init__(self, stream, frame):
        self.stream, self.frame, self.beginning = stream, frame, True

    def write(self, value):
        text = self.frame.display(value)
        for part in text.splitlines(keepends=True):
            if self.beginning:
                self.stream.write("[staged] ")
            self.stream.write(part)
            self.beginning = part.endswith("\n")
            if self.beginning:
                self.stream.flush()
        return len(value)

    def flush(self):
        self.stream.flush()


def load_policy(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CapturedIntakeHold("CAPTURED_RUN_POLICY_DUPLICATE_KEY")
            result[key] = value
        return result
    data = json.loads(Path(path).read_text(), object_pairs_hook=unique)
    required = {"max_archive_bytes", "max_members", "max_total_uncompressed_bytes", "max_publish_bytes"}
    optional = {"max_batch_inputs", "max_batch_archive_bytes", "max_batch_uncompressed_bytes", "max_worker_threads"}
    if (not isinstance(data, dict) or not required.issubset(data) or set(data) - required - optional
            or any(type(value) is not int or value <= 0 for value in data.values())):
        raise CapturedIntakeHold("CAPTURED_RUN_POLICY_REQUIRED_POSITIVE_LIMITS")
    return data


def normalize_staged_metadata(frame):
    """Relocate owned output provenance before scientific package checksums/sealing."""
    from openpyxl import load_workbook
    for path in frame.stage.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".xlsx":
            book = load_workbook(path)
            changed = False
            for sheet in book:
                for row in sheet:
                    for cell in row:
                        if isinstance(cell.value, str):
                            cooked = frame.display(cell.value)
                            if cooked != cell.value:
                                cell.value = cooked; changed = True
            if changed:
                book.save(path)
            book.close()
        elif path.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".csv", ".tsv", ".txt"}:
            try:
                original = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            cooked = frame.display(original)
            if cooked != original:
                path.write_text(cooked, encoding="utf-8")


def finalize_payloads(frame, maximum, protected):
    """Prepare bounded publication after actual run success; never rewrite sealed core."""
    payloads = {}
    total = 0
    for path in sorted((frame.stage / "runs").rglob("*")):
        if path.is_symlink():
            raise CapturedIntakeHold("CAPTURED_RUN_OUTPUT_SYMLINK")
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            data = stream.read(maximum - total + 1)
        if len(data) > maximum - total:
            raise CapturedIntakeHold("CAPTURED_RUN_PUBLICATION_BUDGET")
        # Late handback is outside package integrity; relocate its final locator.
        if path.name == "HANDBACK.json":
            data = frame.display(data.decode()).encode()
        total += len(data)
        if total > maximum:
            raise CapturedIntakeHold("CAPTURED_RUN_PUBLICATION_BUDGET")
        payloads[frame.final / path.relative_to(frame.stage / "runs")] = data
    replacement = None
    if frame.master_stage is not None:
        with frame.master_stage.open("rb") as stream:
            data = stream.read(maximum - total + 1)
        total += len(data)
        if total > maximum:
            raise CapturedIntakeHold("CAPTURED_RUN_PUBLICATION_BUDGET")
        replacement = (frame.master_final, data)
    preflight_output_roster(payloads, replacement=replacement[0] if replacement else None,
                            protected_paths=protected)
    return payloads, replacement


def publish_result(frame, maximum, protected):
    payloads, replacement = finalize_payloads(frame, maximum, protected)
    created = []
    try:
        for target in payloads:
            chain = []; parent = target.parent
            while not parent.exists():
                chain.append(parent); parent = parent.parent
            for directory in reversed(chain):
                directory.mkdir(); created.append((directory, directory.stat()))
        publish_payloads(payloads, replacement=replacement)
    except BaseException as primary:
        if getattr(primary, "output_transaction_commit_status", None) == "COMMITTED":
            raise
        for directory, owned in reversed(created):
            if directory.exists() and directory.stat().st_ino == owned.st_ino:
                try: directory.rmdir()
                except OSError as cleanup_error:
                    primary.add_note("Owned directory cleanup retained: " + type(cleanup_error).__name__)
        raise


def retain_failure_diagnostics(frame, maximum, error, *, destination=None):
    """Retain bounded phase logs outside disposable staging; never admit a package."""
    if destination is None:
        destination = frame.final.parent / ("." + frame.final.name + ".captured-failure-" + uuid.uuid4().hex)
        destination.mkdir()
    remaining = maximum
    rows = []
    for path in sorted(frame.stage.rglob("run_phase_receipts.jsonl")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            data = stream.read(remaining + 1)
        truncated = len(data) > remaining
        data = data[:remaining]
        target = destination / path.relative_to(frame.stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        remaining -= len(data)
        rows.append({"path": str(target), "bytes": len(data), "truncated": truncated,
                     "sha256": hashlib.sha256(data).hexdigest()})
        if not remaining:
            break
    receipt = {"schema": "sapote.captured-run-failure.v1", "admission": "UNADMITTED_DIAGNOSTIC_ONLY",
               "error_type": type(error).__name__, "error": str(error)[:2000],
               "source_sha256": frame.source_sha256,
               "diagnostic_byte_limit": maximum, "diagnostic_bytes": maximum - remaining,
               "files": rows, "package_or_master_admitted": False}
    (destination / "FAILURE.json").write_bytes(encode(receipt))
    return destination


def resolve_execution(args):
    """Resolve documented capped profile and effective timeout once per invocation."""
    result = copy(args)
    if getattr(result, "_capture_execution", None) is not None:
        return result
    requested = {key: getattr(args, key, None) for key in
                 ("brief", "locus_maps", "json_evidence", "require_workbook", "mode")}
    if getattr(args, "chatgpt_safe", False):
        result.brief = "none"
        result.json_evidence = "off"
        os.environ.setdefault("MAMEY_ZIP_COMPRESSION", "stored")
        if result.locus_maps == "auto":
            result.locus_maps = "off"
    result.require_workbook = True
    try:
        budget = int(os.environ.get("MAMEY_BOUNDED_BUDGET_S", "300"))
    except ValueError as exc:
        raise CapturedIntakeHold("CAPTURED_RUN_STATUS_BUDGET_INVALID") from exc
    if budget < 0:
        raise CapturedIntakeHold("CAPTURED_RUN_STATUS_BUDGET_INVALID")
    result._capture_execution = {"requested": requested,
        "effective": {key: getattr(result, key, None) for key in requested},
        "status_budget_seconds": budget}
    return result


def require_profile(args):
    from . import cli
    if (args.brief != "none" or args.locus_maps != "off" or getattr(args, "metadata_csv", None)
            or getattr(args, "hmm_scan", False) or cli._completion_mode(args) != "off"):
        raise CapturedIntakeHold("CAPTURED_RUN_CONSUMER_UNAVAILABLE: require brief none, locus maps off, no metadata/HMM, reference completion off")


def capture(args, policy, expected=None):
    from . import parsers
    aliases = (source_context.lexical_locator(args.input_zip), Path(args.input_zip).resolve())
    session = CapturedIntakeSession.capture(args.input_zip,
                policy=ArchiveSnapshotPolicy(policy["max_archive_bytes"], policy["max_members"], policy["max_total_uncompressed_bytes"]),
                expected_sha256=expected)
    genbank = {}
    parsers.read_genbank_records(session.snapshot, completeness_out=genbank)
    if not genbank.get("members") or any(row["state"] != "COMPLETE" for row in genbank["members"]):
        raise CapturedIntakeHold("CAPTURED_RUN_GENBANK_INCOMPLETE")
    return session, genbank, aliases


def execute_stage(args, legacy, frame):
    import sys
    private = copy(args)
    frame.execution_options = args._capture_execution
    frame.governance = args._capture_governance
    private.outdir = str(frame.stage / "runs")
    private.master = str(frame.master_stage) if frame.master_stage else None
    private.require_workbook = True
    private.capture_policy = None
    with source_context.binding(frame), redirect_stdout(StagedStream(sys.stdout, frame)), redirect_stderr(StagedStream(sys.stderr, frame)):
        code = legacy(private)
    if code != 0:
        raise CapturedIntakeHold("CAPTURED_RUN_PIPELINE_NOT_SUCCESSFUL")


def run(args, legacy):
    """Run actual configured Mamey extraction privately; publish outputs/master last."""
    from . import cli, capture_completion
    if args.strains:
        from .captured_batch import run_batch
        return run_batch(args, legacy)
    master_lock = None
    committed = False
    try:
        args = resolve_execution(args)
        require_profile(args)
        policy = load_policy(args.capture_policy)
        capture_completion.bind_governance(args, policy)
        prior = capture_completion.prior_identity(args, policy["max_publish_bytes"])
        pin = capture_completion.prior_pin(prior, args.input_zip, args.capture_expected_sha256)
        session, genbank, source_aliases = capture(args, policy, pin)
        roster = [{"path": str(source_context.lexical_locator(args.input_zip)), "input_sha256": session.snapshot.input_sha256,
                   "pin_origin": "OPERATOR_EXPECTED" if args.capture_expected_sha256 else "CONSUMED_UNASSERTED"}]
        identity = capture_completion.binding(args, policy, roster)
        final = Path(args.outdir).resolve()
        if final.exists() and not getattr(args, "capture_resume", False):
            raise CapturedIntakeHold("CAPTURED_RUN_OUTPUT_ROOT_MUST_BE_FRESH")
        if cli._refuse_outdir_inside_bundle(str(final)):
            return 2
        master = Path(args.master).resolve() if args.master else None
        original_master = None
        if master is not None:
            master_lock = cli._acquire_master_workbook_lock(master)
            if master_lock is None:
                raise CapturedIntakeHold("CAPTURED_RUN_MASTER_LOCK_UNAVAILABLE")
            if master.exists():
                if master.stat().st_size > policy["max_publish_bytes"]:
                    raise CapturedIntakeHold("CAPTURED_RUN_MASTER_BYTE_BUDGET")
                original_master = capture_completion.bounded_bytes(master, policy["max_publish_bytes"])
        if final.exists():
            capture_completion.verify(final, master, identity, policy["max_publish_bytes"])
            cli._stage("captured resume SKIP: exact source/options/policy/code/output binding verified")
            return 0
        capture_completion.check_failed_attempts(args, identity, policy["max_publish_bytes"])
        final.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".mamey-captured-run-", dir=final.parent) as temporary:
            stage = Path(temporary); staged_master = stage / "master.xlsx" if master else None
            if original_master is not None:
                staged_master.write_bytes(original_master)
            frame = RunFrame(session, args.input_zip, stage, final, staged_master, master, source_aliases)
            frame.genbank = genbank
            frame.pin_origin = roster[0]["pin_origin"]
            try:
                execute_stage(args, legacy, frame)
                if capture_completion.binding(args, policy, roster) != identity:
                    raise CapturedIntakeHold("CAPTURED_RUN_CODE_CHANGED")
                capture_completion.write(frame, identity, policy["max_publish_bytes"])
                if master is not None and ((capture_completion.bounded_bytes(master, policy["max_publish_bytes"]) if master.exists() else None) != original_master):
                    raise CapturedIntakeHold("CAPTURED_RUN_MASTER_CHANGED")
                publish_result(frame, policy["max_publish_bytes"], [args.input_zip, args.capture_policy])
                committed = True
            except BaseException as primary:
                if getattr(primary, "output_transaction_commit_status", None) != "COMMITTED":
                    try:
                        retained = retain_failure_diagnostics(frame, policy["max_publish_bytes"], primary)
                        capture_completion.retain_attempt(retained, identity, policy["max_publish_bytes"])
                        primary.add_note("Unadmitted failure diagnostics: " + str(retained))
                        cli._refuse("Unadmitted failure diagnostics: " + str(retained))
                    except Exception as diagnostic_error:
                        primary.add_note("Failure diagnostic retention failed: " + repr(diagnostic_error))
                        cli._refuse("Failure diagnostic retention failed: " + repr(diagnostic_error))
                raise

        cli._stage("captured run package/master publication committed")
        return 0
    except Exception as exc:
        if committed or getattr(exc, "output_transaction_commit_status", None) == "COMMITTED":
            error = RuntimeError("CAPTURED_RUN_COMMITTED_POSTCOMMIT_FAILURE")
            error.output_transaction_commit_status = "COMMITTED"
            raise error from exc
        cli._refuse(f"CAPTURED_RUN_HOLD: {type(exc).__name__}: {exc}")
        return 2
    finally:
        if master_lock is not None:
            cli._release_master_workbook_lock(master_lock)
