"""Exact local completion bindings; receipts are evidence, never snapshot capabilities."""
from pathlib import Path
import hashlib
import importlib.util
import json
import marshal
import sys
import os
import uuid

from .intake_session import CapturedIntakeHold, encode

NAME = "captured_completion.json"
CORE = ("cli", "captured_run", "captured_batch", "capture_completion", "captured_harness", "source_context",
        "intake_session", "archive_snapshot", "parsers", "antismash_evidence", "antismash_input",
        "strain_identity", "rggmci", "output_transaction", "nrps_predictions", "clusterblast_genes",
        "pks_ks_scan", "structured_domain_motif_extension", "residue_tiling", "gene_by_gene",
        "ref_completion", "mibig_per_gene", "captured_intake_cli", "session_resume", "capture_governance", "exclusions")


def code_binding():
    """Bind source tree plus actual loader code, including explicit development overlays."""
    root = Path(__file__).parent
    files = sorted(root.rglob("*.py"))
    if any(p.is_symlink() for p in files):
        raise CapturedIntakeHold("CAPTURED_ENGINE_SOURCE_SYMLINK")
    rows = [(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    for name in CORE:
        spec = importlib.util.find_spec("mamey." + name)
        code = spec.loader.get_code(spec.name)
        rows.append(("loaded:" + name, hashlib.sha256(marshal.dumps(code)).hexdigest()))
    return hashlib.sha256(encode(rows)).hexdigest()


def options_binding(args):
    # argparse callbacks are dispatch code, bound by code_binding instead.
    ignored = {"func", "capture_resume", "capture_policy", "input_zip", "strains", "outdir", "master"}
    return {k: v for k, v in vars(args).items() if k not in ignored and not k.startswith("_capture_")}


def binding(args, policy, roster):
    from .captured_run import resolve_execution
    args = resolve_execution(args)
    if getattr(args, "_capture_governance", None) is None:
        from .capture_governance import capture
        args._capture_governance = capture(policy["max_archive_bytes"])
    referenced = {}
    for key in ("privacy_profile", "project_registry"):
        locator = getattr(args, key, None)
        if locator:
            data = bounded_bytes(Path(locator), policy["max_archive_bytes"])
            referenced[key] = {"path": str(Path(locator).resolve()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    result = {"schema": "sapote.captured-completion-binding.v1", "policy": policy,
            "referenced_option_files": referenced,
            "execution_options": args._capture_execution,
            "governance": args._capture_governance.binding(),
            "environment": {key: os.environ.get(key) for key in ("MAMEY_OFFICIAL_DATA", "MAMEY_DATA_ROOT", "MAMEY_ZIP_COMPRESSION")},
            "options": options_binding(args), "code_sha256": code_binding(), "inputs": roster,
            "python": {"version": sys.version, "executable": str(Path(sys.executable).resolve())},
            "outdir": str(Path(args.outdir).resolve()),
            "master": str(Path(args.master).resolve()) if args.master else None}
    return json.loads(encode(result))


def bounded_bytes(path, maximum):
    if path.is_symlink():
        raise CapturedIntakeHold("CAPTURED_COMPLETION_SYMLINK")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise CapturedIntakeHold("CAPTURED_COMPLETION_BYTE_BUDGET")
    return data


def tree(root, maximum):
    consumed = 0
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise CapturedIntakeHold("CAPTURED_COMPLETION_SYMLINK")
        if not p.is_file() or p == root / NAME:
            continue
        data = bounded_bytes(p, maximum - consumed)
        consumed += len(data)
        rows.append({"path": p.relative_to(root).as_posix(), "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest()})
    return rows, consumed


def write(frame, identity, maximum):
    from .captured_run import normalize_staged_metadata
    normalize_staged_metadata(frame)
    rows, consumed = tree(frame.stage / "runs", maximum)
    master = None
    if frame.master_stage is not None:
        data = bounded_bytes(frame.master_stage, maximum - consumed)
        master = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    receipt = {"schema": "sapote.captured-completion.v1", "status": "COMPLETE",
               "binding": identity, "outputs": rows, "master": master,
               "source_binding_scope": "consumed archive versions and configured options; biological completeness not established"}
    (frame.stage / "runs" / NAME).write_bytes(encode(receipt))


def verify(root, master_path, identity, maximum):
    raw = bounded_bytes(root / NAME, maximum)
    receipt = json.loads(raw)
    if (receipt.get("schema") != "sapote.captured-completion.v1" or receipt.get("status") != "COMPLETE"
            or receipt.get("binding") != identity):
        raise CapturedIntakeHold("CAPTURED_RESUME_BINDING_CHANGED")
    rows, consumed = tree(root, maximum - len(raw))
    consumed += len(raw)
    master = None
    if master_path is not None:
        data = bounded_bytes(master_path, maximum - consumed)
        master = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if receipt.get("outputs") != rows or receipt.get("master") != master:
        raise CapturedIntakeHold("CAPTURED_RESUME_OUTPUT_CHANGED")
    return receipt


def retain_attempt(destination, identity, maximum):
    data = encode(identity)
    if len(data) > maximum:
        raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_BYTE_BUDGET")
    (destination / "BINDING.json").write_bytes(data)


def check_failed_attempts(args, identity, maximum):
    """Resume a failed attempt only under its saved source/options/policy/code binding."""
    if not getattr(args, "capture_resume", False):
        return
    final = Path(args.outdir).resolve()
    for directory in sorted(final.parent.glob("." + final.name + ".captured-failure-*")):
        if directory.is_symlink() or not directory.is_dir():
            raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_DIAGNOSTIC_PATH_REFUSED")
        saved = directory / "BINDING.json"
        if not saved.is_file():
            raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_UNAVAILABLE")
        if json.loads(bounded_bytes(saved, maximum)) != identity:
            raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_CHANGED")


def prior_identity(args, maximum):
    """Read only durable pins/bindings; capture factories recreate all trusted objects."""
    if not getattr(args, "capture_resume", False):
        return None
    final = Path(args.outdir).resolve()
    if final.exists():
        receipt = json.loads(bounded_bytes(final / NAME, maximum))
        if receipt.get("schema") != "sapote.captured-completion.v1" or receipt.get("status") != "COMPLETE":
            raise CapturedIntakeHold("CAPTURED_RESUME_RECEIPT_INVALID")
        return receipt["binding"]
    identities = []
    for directory in sorted(final.parent.glob("." + final.name + ".captured-failure-*")):
        if directory.is_symlink() or not directory.is_dir():
            raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_DIAGNOSTIC_PATH_REFUSED")
        saved = directory / "BINDING.json"
        if not saved.is_file():
            raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_UNAVAILABLE")
        identities.append(json.loads(bounded_bytes(saved, maximum)))
    if identities and any(row != identities[0] for row in identities):
        raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_AMBIGUOUS")
    return identities[0] if identities else None


def prior_pin(identity, locator, operator_pin=None):
    if identity is None:
        return operator_pin
    from .source_context import lexical_locator
    rows = [row for row in identity["inputs"] if row["path"] == str(lexical_locator(locator))]
    if len(rows) != 1:
        raise CapturedIntakeHold("CAPTURED_RESUME_SOURCE_LOCATOR_CHANGED")
    pin = rows[0]["input_sha256"]
    if operator_pin is not None and operator_pin != pin:
        raise CapturedIntakeHold("CAPTURED_RESUME_EXPECTED_VERSION_CONFLICT")
    return pin


def bind_governance(args, policy):
    from .capture_governance import capture
    args._capture_governance = capture(policy["max_archive_bytes"])


def begin_attempt(final, identity, maximum):
    """Persist the complete admitted plan before replay, independent of any item frame."""
    data = encode(identity)
    if len(data) > maximum:
        raise CapturedIntakeHold("CAPTURED_FAILED_ATTEMPT_BINDING_BYTE_BUDGET")
    directory = final.parent / ("." + final.name + ".captured-failure-" + uuid.uuid4().hex)
    directory.mkdir()
    (directory / "BINDING.json").write_bytes(data)
    attempt_state(directory, "IN_PROGRESS")
    return directory


def attempt_state(directory, state):
    (directory / "ATTEMPT.json").write_bytes(encode({
        "schema": "sapote.captured-attempt.v1", "state": state,
        "purpose": "retained transaction binding; directory naming is historical",
        "scientific_publication": "COMMITTED" if state.startswith("COMMITTED") else "NOT_ESTABLISHED"}))
