"""Opt-in direct-archive intake harness using captured all-or-nothing transactions."""
from pathlib import Path
import glob
import io
import json

from .intake_session import CapturedIntakeHold


def run(args, *, engine, taxonomy_map, taxonomy_binding):
    from . import cli
    if args.bench or args.batch_report:
        raise CapturedIntakeHold("CAPTURED_HARNESS_BENCH_REPORT_UNAVAILABLE")
    if args.capture_batch_policy != "all-or-nothing" or args.capture_threads != 1:
        raise CapturedIntakeHold("CAPTURED_HARNESS_EXPLICIT_BATCH_POLICY_ONE_THREAD_REQUIRED")
    inputs = []
    for item in args.inputs:
        path = Path(item)
        if path.is_dir():
            inputs.extend(sorted(glob.glob(str(path / "*.zip"))))
        elif path.suffix.lower() == ".zip":
            inputs.append(str(path))
        else:
            raise CapturedIntakeHold("CAPTURED_HARNESS_INPUT_MUST_BE_ARCHIVE_OR_DIRECTORY")
    if not inputs:
        raise CapturedIntakeHold("CAPTURED_HARNESS_NO_ARCHIVES")
    root = Path(args.outdir).resolve()
    relative = []
    for locator in (args.registry, args.metrics):
        path = Path(locator).resolve()
        if root not in path.parents or path == root:
            raise CapturedIntakeHold("CAPTURED_HARNESS_CSV_MUST_BE_INSIDE_TRANSACTION_ROOT")
        relative.append(path.relative_to(root).as_posix())
    if relative[0].casefold() == relative[1].casefold():
        raise CapturedIntakeHold("CAPTURED_HARNESS_CSV_COLLISION")
    command = ["run", "--strains", *inputs, "--outdir", str(root), "--brief", "none",
               "--locus-maps", "off", "--reference-completion", "off", "--json-evidence", "bounded",
               "--rggmci-threads", "1", "--source", args.source, "--release", args.release,
               "--mode", args.mode, "--capture-policy", args.capture_policy,
               "--capture-batch-policy", args.capture_batch_policy]
    if args.capture_master:
        command += ["--master", args.capture_master]
    if args.resume:
        command += ["--capture-resume"]
    parsed = cli.build_parser().parse_args(command)
    parsed.capture_harness_context = {"engine": engine, "taxonomy_map_binding": taxonomy_binding,
        "taxonomy_map": taxonomy_map, "registry": relative[0], "metrics": relative[1],
        "batch_label": args.batch_label, "input_profile": "direct captured antiSMASH archives; no extraction/repacking"}
    return cli.run_command(parsed)


def summaries(frame, context, roster, maximum):
    """Write fresh registry/metrics inside the same transaction; unknown counts stay blank."""
    from .capture_completion import bounded_bytes
    from .csv_safety import SafeDictWriter
    registry = []
    metrics = []
    for row in roster:
        sid = row.get("strain")
        if not sid:
            raise CapturedIntakeHold("CAPTURED_HARNESS_ROSTER_STRAIN_REQUIRED")
        package = frame.stage / "runs" / sid / "package"
        manifest = json.loads(bounded_bytes(package / "manifest.json", maximum))
        counts = manifest.get("bgc_counts") or {}
        registry.append({"strain": sid, "organism": row.get("taxonomy"), "release": manifest.get("release"),
            "assembly_tier": counts.get("assembly_tier"), "raw_bgcs": counts.get("raw"),
            "diagnostic_cores_present": None, "rescue_leads": None, "rescue_HIGH": None,
            "rescue_MODERATE": None, "IDC_split_HIGH": None})
        metrics.append({"strain": sid, "batch": context["batch_label"], "status": "OK",
            "engine_wall_s": None, "engine_peak_mb": None, "rescue_wall_s": None,
            "n_regions": (manifest.get("captured_source") or {}).get("denominator", {}).get("value")})
    for key, rows in (("registry", registry), ("metrics", metrics)):
        path = frame.stage / "runs" / context[key]
        if path.exists() or path.is_symlink():
            raise CapturedIntakeHold("CAPTURED_HARNESS_SUMMARY_OUTPUT_OCCUPIED")
        stream = io.StringIO(newline="")
        writer = SafeDictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        data = stream.getvalue().encode()
        if len(data) > maximum:
            raise CapturedIntakeHold("CAPTURED_HARNESS_SUMMARY_BYTE_BUDGET")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
