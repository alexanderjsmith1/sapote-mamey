"""Explicit all-or-nothing captured batch; sequential captures, cumulative private master."""
from copy import copy
from pathlib import Path
from types import SimpleNamespace
import tempfile

from . import capture_completion, captured_run, source_context
from .intake_session import CapturedIntakeHold, encode


def _per_item(value, count, fallback):
    fields = (value or "").split("|")
    if len(fields) not in (1, count):
        raise CapturedIntakeHold("CAPTURED_BATCH_METADATA_CARDINALITY")
    if len(fields) == 1:
        fields *= count
    return [field or fallback for field in fields]


def plan(args, policy):
    """Bind consumed plan versions and scientific identities, without retaining all captures."""
    from .strain_identity import resolve_strain_id
    required = {"max_batch_inputs", "max_batch_archive_bytes", "max_batch_uncompressed_bytes", "max_worker_threads"}
    if (not required.issubset(policy) or policy["max_worker_threads"] != 1
            or getattr(args, "rggmci_threads", None) != 1):
        raise CapturedIntakeHold("CAPTURED_BATCH_EXPLICIT_AGGREGATE_LIMITS_AND_ONE_THREAD_REQUIRED")
    if len(args.strains) > policy["max_batch_inputs"]:
        raise CapturedIntakeHold("CAPTURED_BATCH_INPUT_COUNT_BUDGET")
    if getattr(args, "capture_expected_sha256", None):
        raise CapturedIntakeHold("CAPTURED_BATCH_SINGLE_PIN_AMBIGUOUS")
    count = len(args.strains)
    if count != 1 and getattr(args, "rggmci_label", None) is not None:
        raise CapturedIntakeHold("CAPTURED_BATCH_RG_LABEL_REQUIRES_SINGLE_INPUT")
    taxonomies = _per_item(args.taxonomy, count, "not verified")
    sources = _per_item(args.source, count, "not supplied")
    provenance = _per_item(getattr(args, "source_provenance", None), count, "asserted")
    prior = capture_completion.prior_identity(args, policy["max_publish_bytes"])
    roster = []
    locators, identities = set(), set()
    byte_total = expansion_total = 0
    for index, locator in enumerate(args.strains):
        lexical = str(source_context.lexical_locator(locator))
        if lexical in locators:
            raise CapturedIntakeHold("CAPTURED_BATCH_DUPLICATE_LOCATOR")
        locators.add(lexical)
        selected = copy(args)
        selected.input_zip = locator
        session, genbank, aliases = captured_run.capture(selected, policy,
            capture_completion.prior_pin(prior, locator))
        byte_total += len(session.snapshot._payload)
        expansion_total += session.snapshot.verified_uncompressed_bytes
        if (byte_total > policy["max_batch_archive_bytes"]
                or expansion_total > policy["max_batch_uncompressed_bytes"]):
            raise CapturedIntakeHold("CAPTURED_BATCH_AGGREGATE_SOURCE_BUDGET")
        resolved = resolve_strain_id("auto", session.snapshot,
                     allow_accession=getattr(args, "allow_accession_strain_id", False))
        if resolved.refused or not resolved.strain_id:
            raise CapturedIntakeHold("CAPTURED_BATCH_STRAIN_ID_UNRESOLVED")
        # Distinct archives with the same scientific identity require explicit upstream resolution.
        sid = resolved.strain_id
        if sid.casefold() in identities:
            raise CapturedIntakeHold("CAPTURED_BATCH_CONFLICTING_STRAIN_IDENTITY")
        identities.add(sid.casefold())
        context = getattr(args, "capture_harness_context", None)
        if context is not None and sid in context["taxonomy_map"]:
            taxonomies[index] = context["taxonomy_map"][sid]
        roster.append({"path": lexical, "input_sha256": session.snapshot.input_sha256,
                       "pin_origin": "PLANNED_CONSUMED_VERSION", "strain": sid,
                       "taxonomy": taxonomies[index], "source": sources[index],
                       "source_provenance": provenance[index]})
        # Drop the only live capture before admitting the next input.
        del session
    return roster


def run_batch(args, legacy):
    from . import cli
    lock = None
    committed = False
    frame = None
    try:
        args = captured_run.resolve_execution(args)
        captured_run.require_profile(args)
        if getattr(args, "capture_batch_policy", None) != "all-or-nothing":
            raise CapturedIntakeHold("CAPTURED_BATCH_EXPLICIT_PUBLICATION_POLICY_REQUIRED")
        policy = captured_run.load_policy(args.capture_policy)
        capture_completion.bind_governance(args, policy)
        roster = plan(args, policy)
        identity = capture_completion.binding(args, policy, roster)
        final = Path(args.outdir).resolve()
        if final.exists() and not getattr(args, "capture_resume", False):
            raise CapturedIntakeHold("CAPTURED_RUN_OUTPUT_ROOT_MUST_BE_FRESH")
        if cli._refuse_outdir_inside_bundle(str(final)):
            return 2
        master = Path(args.master).resolve() if args.master else None
        original_master = None
        if master is not None:
            lock = cli._acquire_master_workbook_lock(master)
            if lock is None:
                raise CapturedIntakeHold("CAPTURED_RUN_MASTER_LOCK_UNAVAILABLE")
            if master.exists():
                original_master = capture_completion.bounded_bytes(master, policy["max_publish_bytes"])
        if final.exists():
            capture_completion.verify(final, master, identity, policy["max_publish_bytes"])
            cli._stage("captured batch resume SKIP: complete transaction binding verified")
            return 0
        capture_completion.check_failed_attempts(args, identity, policy["max_publish_bytes"])
        final.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".mamey-captured-batch-", dir=final.parent) as temporary:
            stage = Path(temporary)
            staged_master = stage / "master.xlsx" if master else None
            if original_master is not None:
                staged_master.write_bytes(original_master)
            receipts = []
            attempt = None
            try:
                attempt = capture_completion.begin_attempt(final, identity, policy["max_publish_bytes"])
                for row in roster:
                    item = copy(args)
                    item.strains = None
                    item.input_zip = row["path"]
                    item.strain = row["strain"]
                    item.taxonomy, item.source = row["taxonomy"], row["source"]
                    item.source_provenance = row["source_provenance"]
                    session, genbank, aliases = captured_run.capture(item, policy, row["input_sha256"])
                    frame = captured_run.RunFrame(session, item.input_zip, stage, final,
                                                   staged_master, master, aliases)
                    frame.pin_origin = "PLANNED_CONSUMED_VERSION"
                    frame.genbank = genbank
                    captured_run.execute_stage(item, legacy, frame)
                    # Bound retained outputs after each item; never accumulate payload dictionaries.
                    _, used = capture_completion.tree(stage / "runs", policy["max_publish_bytes"])
                    if staged_master is not None:
                        capture_completion.bounded_bytes(staged_master, policy["max_publish_bytes"] - used)
                    receipts.append({"strain": row["strain"], "source": frame.receipt(),
                                     "package": str(final / row["strain"] / "package")})
                    frame.session = None
                    del session
                if capture_completion.binding(args, policy, roster) != identity:
                    raise CapturedIntakeHold("CAPTURED_RUN_CODE_CHANGED")
                (stage / "runs" / "CAPTURED_BATCH.json").write_bytes(encode({
                    "schema": "sapote.captured-batch.v1", "publication_policy": "all-or-nothing",
                    "inputs": roster, "items": receipts, "biological_completeness": "NOT_ESTABLISHED"}))
                if getattr(args, "capture_harness_context", None) is not None:
                    from .captured_harness import summaries
                    summaries(frame, args.capture_harness_context, roster, policy["max_publish_bytes"])
                capture_completion.write(frame, identity, policy["max_publish_bytes"])
                if master is not None and ((capture_completion.bounded_bytes(master, policy["max_publish_bytes"])
                        if master.exists() else None) != original_master):
                    raise CapturedIntakeHold("CAPTURED_RUN_MASTER_CHANGED")
                captured_run.publish_result(frame, policy["max_publish_bytes"], [*args.strains, args.capture_policy])
                committed = True
                capture_completion.attempt_state(attempt, "COMMITTED")
            except BaseException as primary:
                if committed or getattr(primary, "output_transaction_commit_status", None) == "COMMITTED":
                    if attempt is not None:
                        try:
                            capture_completion.attempt_state(attempt, "COMMITTED_WITH_ERROR")
                        except Exception as state_error:
                            primary.add_note("Committed attempt state update failed: " + repr(state_error))
                else:
                    try:
                        context = frame if frame is not None else SimpleNamespace(
                            stage=stage, final=final, source_sha256=None)
                        retained = captured_run.retain_failure_diagnostics(context, policy["max_publish_bytes"], primary,
                                                                         destination=attempt)
                        capture_completion.retain_attempt(retained, identity, policy["max_publish_bytes"])
                        capture_completion.attempt_state(retained, "FAILED")
                        (retained / "BATCH_PLAN.json").write_bytes(encode(roster))
                        cli._refuse("Unadmitted batch diagnostics: " + str(retained))
                    except Exception as diagnostic_error:
                        primary.add_note("Batch diagnostic retention failed: " + repr(diagnostic_error))
                        cli._refuse("Batch diagnostic retention failed: " + repr(diagnostic_error))
                raise
        cli._stage("captured batch package/master publication committed")
        return 0
    except Exception as exc:
        if committed or getattr(exc, "output_transaction_commit_status", None) == "COMMITTED":
            error = RuntimeError("CAPTURED_RUN_COMMITTED_POSTCOMMIT_FAILURE")
            error.output_transaction_commit_status = "COMMITTED"
            raise error from exc
        cli._refuse(f"CAPTURED_BATCH_HOLD: {type(exc).__name__}: {exc}")
        return 2
    finally:
        if lock is not None:
            cli._release_master_workbook_lock(lock)
