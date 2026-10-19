"""Explicit captured intake CLI slice; publishes intake JSON, never a full package."""
from pathlib import Path
import hashlib

from .archive_snapshot import ArchiveSnapshotPolicy
from .intake_session import CapturedIntakeSession, EvidenceOptions, encode
from .output_transaction import fresh_output_set


def manifest_payload(intake, payload):
    """Finalize with the consumed-source digest; do not reopen its original locator."""
    return {"schema": "sapote.captured-intake-manifest.v1", "scope": intake["scope"],
            "input_sha256": intake["input_sha256"], "original_version": intake["original_version"],
            "strain_id": intake["strain_id"], "genbank_complete": intake["genbank_complete"],
            "denominator": intake["denominator"], "source_completeness": intake["evidence"].get("source_completeness"),
            "outputs": [{"path": "intake.json", "bytes": len(payload),
                         "sha256": hashlib.sha256(payload).hexdigest()}],
            "full_package_published": False, "workbook_updated": False,
            "biological_absence": "NOT_ESTABLISHED", "upstream_search_completion": "NOT_ESTABLISHED"}


def command(args):
    """Run one supported captured intake; failure leaves no admitted output set."""
    from .cli import _refuse, _refuse_outdir_inside_bundle
    if _refuse_outdir_inside_bundle(args.outdir):
        return 2
    try:
        session = CapturedIntakeSession.capture(
            args.input_zip, policy=ArchiveSnapshotPolicy(args.max_archive_bytes, args.max_members,
                                                        args.max_total_uncompressed_bytes),
            expected_sha256=args.expected_sha256, require_complete_genbank=not args.allow_incomplete_genbank,
            consumer=args.consumer)
        options = EvidenceOptions(args.json_evidence, not args.no_tigrfam, args.include_structured,
                                  args.json_budget_seconds)
        intake = session.prepare(args.strain, options=options)
        payload = encode(intake)
        with fresh_output_set(args.outdir, ["intake.json", "manifest.json"]) as stage:
            (stage / "intake.json").write_bytes(payload)
            (stage / "manifest.json").write_bytes(encode(manifest_payload(intake, payload)))
    except Exception as exc:
        _refuse(f"CAPTURED_INTAKE_HOLD: {type(exc).__name__}: {exc}")
        return 2
    return 0


def register(subparsers):
    """Register an opt-in supported slice with required caller resource policy."""
    parser = subparsers.add_parser("intake-captured", help="Opt-in intake-only capture; writes intake.json and manifest.json")
    parser.add_argument("--input-zip", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--strain", default="auto")
    parser.add_argument("--max-archive-bytes", required=True, type=int)
    parser.add_argument("--max-members", required=True, type=int)
    parser.add_argument("--max-total-uncompressed-bytes", required=True, type=int)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--consumer", default="intake", help="Only intake is migrated; other consumers HOLD before capture")
    parser.add_argument("--json-evidence", choices=["off", "bounded", "full"], default="off")
    parser.add_argument("--json-budget-seconds", type=int, default=300)
    parser.add_argument("--no-tigrfam", action="store_true")
    parser.add_argument("--include-structured", action="store_true")
    parser.add_argument("--allow-incomplete-genbank", action="store_true", help="Explicit partial GBK admission; duplicate namespaces still HOLD")
    parser.set_defaults(func=command)
