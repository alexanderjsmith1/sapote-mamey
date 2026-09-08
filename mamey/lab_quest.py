"""Portable, claim-safe support for the optional local Lab Quest interface.

Lab Quest is intentionally a thin local control surface.  It binds one explicit
portable code-tier root, invokes only supported Mamey commands, and records
workflow receipts.  It neither searches personal workspaces nor makes
independent biological decisions.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .exact_identity import exact_locus_from_mapping
from .validate import validate_package


CLAIM_CEILING = (
    "Quest navigation and receipts are not scientific evidence. Similarity is not identity; "
    "biosynthetic capacity is not production; strain-level activity is not locus-level causality; "
    "missing or unbound evidence is not biological absence."
)
HISTORICAL_PROTOTYPE_STATUS = (
    "Historical Lab Quest prose and examples are retained only as dated prototype material. "
    "They are not current scientific authority and must be regenerated from governed evidence."
)
_STRAIN_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_VERSION = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_BUNDLE = re.compile(r'^BUNDLE_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


class EngineBindingError(ValueError):
    """Raised when an explicit portable engine binding is absent or inconsistent."""


@dataclass(frozen=True)
class EngineBinding:
    """Verified identity of the only engine root Lab Quest may execute."""

    code_tier: Path
    bundle_version: str
    engine_version: str
    init_sha256: str
    runner_sha256: str
    pyproject_sha256: str
    binding_sha256: str

    def as_receipt(self) -> dict[str, str]:
        value = asdict(self)
        value["code_tier"] = str(self.code_tier)
        return value


@dataclass(frozen=True)
class PackageSnapshot:
    package: Path
    strain: str
    manifest_sha256: str
    workflow_version: str
    bundle_version: str
    mode: str
    release: str
    validator_status: str
    evidence_date_utc: str
    inventory: tuple[dict[str, Any], ...]
    triage: tuple[dict[str, Any], ...]
    # B8/v9.7.405: defaults retain read-only compatibility with historical package snapshots
    # and test fixtures that predate the landed models.py privacy_tier/privacy_assignment_state
    # fields (mamey/project_registry.py is the intended producer of these on a real package).
    privacy_tier: str = "LEGACY_OR_NOT_RECORDED"
    privacy_assignment_state: str = "LEGACY_OR_NOT_RECORDED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_display_text(value: object, label: str, max_length: int = 240) -> str:
    """Validate user text before it reaches a path, receipt, or rendered widget."""
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > max_length or _CONTROL.search(text):
        raise ValueError(f"{label} contains unsupported control characters or exceeds {max_length} characters")
    return text


def _markdown_value(value: object, label: str, max_length: int = 240) -> str:
    """Render controlled provenance text without allowing Markdown structure."""
    text = safe_display_text(value, label, max_length=max_length)
    return text.replace("\\", "\\\\").replace("`", "\\`").replace("|", "\\|")


def safe_upload_name(name: str) -> str:
    """Accept a single portable antiSMASH ZIP filename and reject traversal."""
    text = safe_display_text(name, "upload filename", max_length=180)
    if not text or text in {".", ".."}:
        raise ValueError("upload filename is empty or reserved")
    if "/" in text or "\\" in text or Path(text).name != text or ".." in text:
        raise ValueError("upload filename must not contain path traversal")
    if not text.lower().endswith(".zip"):
        raise ValueError("Lab Quest accepts antiSMASH ZIP inputs only")
    return text


def validate_strain_token(value: str) -> str:
    text = safe_display_text(value, "strain", max_length=128)
    if not _STRAIN_TOKEN.fullmatch(text) or ".." in text:
        raise ValueError("strain must use letters, digits, dot, dash, or underscore")
    return text


def release_for_strain(strain: str) -> str:
    """Derive the release class fail-closed from the strain token."""
    return "PRIVATE" if validate_strain_token(strain).upper().startswith(("AS-", "AJS-", "PENDING-")) else "PUBLIC"


def resolve_project_root(value: str | Path) -> Path:
    """Resolve an explicit local project root without a cwd fallback.

    An empty string would otherwise become ``Path('.')`` and silently make the
    launch directory a source root.  Lab Quest is portable only when an
    operator deliberately supplies a project root, so refuse that ambiguity.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("an explicit Lab Quest project root is required")
    root = Path(value).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    return root


def contained_path(root: str | Path, *parts: str) -> Path:
    resolved_root = resolve_project_root(root)
    candidate = resolved_root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path escapes the Lab Quest project root: {candidate}") from exc
    return candidate


def _one(root: Path, suffix: str) -> Path:
    matches = sorted(p for p in root.iterdir() if p.is_file() and p.name.endswith(suffix))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one *{suffix} in {root}; found {len(matches)}")
    return matches[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def resolve_engine_binding(
    code_tier: str | Path,
    *,
    expected_bundle_version: str,
    expected_engine_version: str,
) -> EngineBinding:
    """Validate a configured code tier and refuse stale or ambiguous bindings.

    There is deliberately no workspace glob or "newest" heuristic.  The caller
    must supply both the root and the versions it expects to execute.
    """
    if not expected_bundle_version.strip() or not expected_engine_version.strip():
        raise EngineBindingError("expected bundle and engine versions are required for Lab Quest")
    root = Path(code_tier).expanduser().resolve()
    required = (root / "mamey_run.py", root / "pyproject.toml", root / "mamey" / "__init__.py")
    missing = [str(path.name) for path in required if not path.is_file()]
    if missing:
        raise EngineBindingError(f"configured code tier is incomplete: missing {', '.join(missing)}")
    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise EngineBindingError(f"configured pyproject is not parseable: {exc}") from exc
    init_path = root / "mamey" / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    engine_match = _VERSION.search(init_text)
    bundle_match = _BUNDLE.search(init_text)
    project_engine = str((pyproject.get("project") or {}).get("version") or "")
    project_bundle = str((pyproject.get("tool") or {}).get("sapote", {}).get("bundle_version") or "")
    if not engine_match or not bundle_match:
        raise EngineBindingError("configured mamey/__init__.py lacks both version constants")
    engine_version = engine_match.group(1)
    bundle_version = bundle_match.group(1)
    if (engine_version, bundle_version) != (project_engine, project_bundle):
        raise EngineBindingError("configured engine and pyproject versions disagree")
    if bundle_version != expected_bundle_version or engine_version != expected_engine_version:
        raise EngineBindingError(
            "configured code tier is stale or unexpected: "
            f"found bundle {bundle_version} / engine {engine_version}; "
            f"expected {expected_bundle_version} / {expected_engine_version}"
        )
    init_sha = sha256_file(init_path)
    runner_sha = sha256_file(root / "mamey_run.py")
    pyproject_sha = sha256_file(root / "pyproject.toml")
    binding_sha = _canonical_hash(
        {
            "code_tier": str(root),
            "bundle_version": bundle_version,
            "engine_version": engine_version,
            "init_sha256": init_sha,
            "runner_sha256": runner_sha,
            "pyproject_sha256": pyproject_sha,
        }
    )
    return EngineBinding(root, bundle_version, engine_version, init_sha, runner_sha, pyproject_sha, binding_sha)


def verify_engine_binding_current(binding: EngineBinding) -> None:
    """Fail closed if a selected portable code tier drifts before execution."""
    sources = {
        "mamey/__init__.py": binding.code_tier / "mamey" / "__init__.py",
        "mamey_run.py": binding.code_tier / "mamey_run.py",
        "pyproject.toml": binding.code_tier / "pyproject.toml",
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise EngineBindingError("configured code tier changed after binding: missing " + ", ".join(missing))
    observed = {name: sha256_file(path) for name, path in sources.items()}
    expected = {
        "mamey/__init__.py": binding.init_sha256,
        "mamey_run.py": binding.runner_sha256,
        "pyproject.toml": binding.pyproject_sha256,
    }
    changed = [name for name in expected if observed[name] != expected[name]]
    if changed:
        raise EngineBindingError(
            "configured code tier changed after binding; re-bind before execution: " + ", ".join(changed)
        )


def export_private_project_handoff(
    *,
    binding: EngineBinding,
    project_root: str | Path,
    output_zip: str | Path,
) -> Path:
    """Export a private project only while the Lab Quest engine binding is current.

    Binding verification is intentionally the first operation.  A stale code
    tier therefore fails before the catalog helper can create an output parent
    or touch an archive.
    """
    verify_engine_binding_current(binding)
    from .project_catalog import export_private_project_handoff as _export_private_project_handoff

    return _export_private_project_handoff(project_root, output_zip)


def write_engine_binding_receipt(project_root: str | Path, binding: EngineBinding) -> Path:
    """Persist the verified code-tier binding as a local, additive provenance record."""
    verify_engine_binding_current(binding)
    root = resolve_project_root(project_root)
    out = contained_path(root, "lab_quest_outputs", "engine_binding.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "mamey_lab_quest_engine_binding_v1",
        "created_utc": utc_now(),
        "binding": binding.as_receipt(),
        "claim_ceiling": CLAIM_CEILING,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def discover_packages(root: str | Path, max_depth: int = 6) -> list[Path]:
    """Discover sealed-package candidates under a selected project root only."""
    project = resolve_project_root(root)
    found: list[Path] = []
    for manifest in project.rglob("manifest.json"):
        try:
            depth = len(manifest.parent.relative_to(project).parts)
        except ValueError:
            continue
        if depth <= max_depth and any(manifest.parent.glob("*_2_inventory.csv")):
            found.append(manifest.parent.resolve())
    return sorted(set(found))


def load_package_snapshot(package: str | Path) -> PackageSnapshot:
    """Read a package with current validation and complete exact-locus identities."""
    root = Path(package).expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not root.is_dir() or not manifest_path.is_file():
        raise ValueError(f"not a Mamey package directory: {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    strain = validate_strain_token(str(manifest.get("strain_id") or manifest.get("display_name") or ""))
    intake_path = _one(root, "_1_intake.json")
    inventory_path = _one(root, "_2_inventory.csv")
    triage_path = _one(root, "_4_triage_board.csv")
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    inventory_rows = _read_csv(inventory_path)
    triage_rows = _read_csv(triage_path)

    identity_by_alias: dict[str, str] = {}
    inventory: list[dict[str, Any]] = []
    for row in inventory_rows:
        exact = exact_locus_from_mapping(strain, row)
        alias = safe_display_text(row.get("BGC_ID"), "inventory BGC alias", 80)
        if not alias or alias in identity_by_alias:
            raise ValueError(f"inventory BGC alias is missing or duplicated: {alias!r}")
        identity_by_alias[alias] = exact
        inventory.append({**row, "exact_locus": exact})

    triage: list[dict[str, Any]] = []
    for row in triage_rows:
        alias = safe_display_text(row.get("BGC_ID"), "triage BGC alias", 80)
        if alias not in identity_by_alias:
            raise ValueError(f"triage row has no exact inventory identity: {alias!r}")
        triage.append({**row, "exact_locus": identity_by_alias[alias]})

    validation = validate_package(root, enrichment_check=True)
    evidence_date = datetime.fromtimestamp(manifest_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return PackageSnapshot(
        package=root,
        strain=strain,
        manifest_sha256=sha256_file(manifest_path),
        workflow_version=str(manifest.get("workflow_version") or "NOT_RECORDED"),
        bundle_version=str(manifest.get("bundle_version") or "NOT_RECORDED"),
        mode=str(manifest.get("mode") or "NOT_RECORDED"),
        release=str(intake.get("release") or release_for_strain(strain)),
        privacy_tier=str(manifest.get("privacy_tier") or "LEGACY_OR_NOT_RECORDED"),
        privacy_assignment_state=str(manifest.get("privacy_assignment_state") or "LEGACY_OR_NOT_RECORDED"),
        validator_status=str(validation.get("status") or validation.get("file_presence") or "UNKNOWN"),
        evidence_date_utc=evidence_date,
        inventory=tuple(inventory),
        triage=tuple(triage),
    )


def formal_review_markdown(
    *,
    binding: EngineBinding,
    project_root: str | Path,
    run: object | None,
    snapshot: PackageSnapshot | None,
) -> str:
    """Build a persona-free local workflow record, not a scientific report.

    The record contains only current interface provenance and typed workflow
    states. It never converts a visit, receipt, or package validation into an
    owner-review, release, or biological conclusion.
    """
    root = resolve_project_root(project_root)
    rows = [
        ("Portable code-tier root", str(binding.code_tier)),
        ("Project/source-root binding", str(root)),
        ("Bundle / engine", f"{binding.bundle_version} / {binding.engine_version}"),
        ("Code-tier binding SHA-256", binding.binding_sha256),
        ("Quest workflow state", str(getattr(getattr(run, "state", None), "value", "NOT_STARTED"))),
        ("Evidence/admission state", str(getattr(getattr(run, "evidence_state", None), "value", "NOT_ADMITTED"))),
        ("Owner review", "NOT_ADMITTED_BY_INTERFACE"),
        ("Release approval", "NOT_ADMITTED_BY_INTERFACE"),
    ]
    if run is not None:
        rows.extend([
            ("Run ID", str(getattr(run, "run_id", "NOT_RECORDED"))),
            ("Input ZIP SHA-256", str(getattr(run, "input_sha256", "NOT_RECORDED"))),
        ])
    if snapshot is not None:
        rows.extend([
            ("Package manifest SHA-256", snapshot.manifest_sha256),
            ("Package validation", snapshot.validator_status),
            ("Run mode / release class", f"{snapshot.mode} / {snapshot.release}"),
            ("Privacy tier / assignment", f"{snapshot.privacy_tier} / {snapshot.privacy_assignment_state}"),
            ("Evidence date", snapshot.evidence_date_utc),
        ])
    table = ["| Field | Current value |", "|---|---|"]
    table.extend(
        f"| {_markdown_value(field, 'formal review field')} | {_markdown_value(value, 'formal review value')} |"
        for field, value in rows
    )
    return "\n".join([
        "# Sapote-Mamey scientific review record",
        "",
        "Status: `LOCAL_WORKFLOW_RECORD_NOT_SCIENTIFIC_ACCEPTANCE`.",
        "",
        "This persona-free record reports local provenance and typed workflow states only.",
        "It is not a biological result, owner review, integration, release, or publication approval.",
        "",
        *table,
        "",
        "## Claim ceiling",
        "",
        CLAIM_CEILING,
        "",
    ])


def _require_within_project(project_root: str | Path, path: str | Path) -> Path:
    project = resolve_project_root(project_root)
    resolved = Path(path).expanduser().resolve()
    try:
        resolved.relative_to(project)
    except ValueError as exc:
        raise ValueError(f"Lab Quest only operates on paths below the selected project root: {resolved}") from exc
    return resolved


def build_engine_command(binding: EngineBinding, *args: str) -> list[str]:
    """Build the sole allowed execution path: the bound code tier's runner."""
    verify_engine_binding_current(binding)
    return [sys.executable, str(binding.code_tier / "mamey_run.py"), *args]


def build_run_command(
    *,
    binding: EngineBinding,
    project_root: str | Path,
    input_zip: str | Path,
    strain: str,
    taxonomy: str = "",
    source: str = "",
) -> list[str]:
    root = resolve_project_root(project_root)
    zip_path = _require_within_project(root, input_zip)
    command = build_engine_command(
        binding,
        "run",
        "--strain",
        validate_strain_token(strain),
        "--input-zip",
        str(zip_path),
        "--outdir",
        str(contained_path(root, "runs")),
        "--mode",
        "gold",
        "--source-provenance",
        "asserted",
    )
    if taxonomy := safe_display_text(taxonomy, "taxonomy"):
        command.extend(["--taxonomy", taxonomy])
    if source := safe_display_text(source, "source"):
        command.extend(["--source", source])
    return command


def build_station_command(
    *,
    binding: EngineBinding,
    project_root: str | Path,
    package: str | Path,
    station: str,
    run_id: str,
) -> list[str]:
    """Map a governed station to one supported Mamey command; no game logic."""
    root = resolve_project_root(project_root)
    package_path = _require_within_project(root, package)
    if station == "BLASTP":
        return build_engine_command(binding, "blastp-status", "--package", str(package_path))
    if station == "MODE_B":
        output = station_artifact_paths(project_root=root, package=package_path, station=station, run_id=run_id)[0]
        output.parent.mkdir(parents=True, exist_ok=True)
        return build_engine_command(binding, "emit-strain-modeb", "--package", str(package_path), "--out", str(output))
    if station == "FIGURES":
        # The engine defaults to non-blocking per-set figure rendering.  A
        # receipt-gated station must not advance after an exit-zero aggregate
        # that concealed an individual set error.
        return build_engine_command(binding, "render-all-figures", "--package", str(package_path), "--fail-fast")
    if station == "HANDOFF":
        output = station_artifact_paths(project_root=root, package=package_path, station=station, run_id=run_id)[0]
        output.parent.mkdir(parents=True, exist_ok=True)
        return build_engine_command(binding, "handoff", "--package", str(package_path), "--out", str(output))
    raise ValueError(f"unsupported Lab Quest station: {station}")


def station_artifact_paths(
    *,
    project_root: str | Path,
    package: str | Path,
    station: str,
    run_id: str,
) -> tuple[Path, ...]:
    """Return the output artifact that a successful post-seal station must bind.

    BLASTP status is a command/availability observation and has no mandatory
    new output artifact.  All other post-seal stations require an exact local
    artifact before a receipt may unlock the next station.
    """
    root = resolve_project_root(project_root)
    package_path = _require_within_project(root, package)
    if station == "MODE_B":
        return (contained_path(root, "lab_quest_outputs", "modeb", f"{run_id}_strain_modeb.md"),)
    if station == "FIGURES":
        return (_require_within_project(root, package_path / "render_all_figures_summary.json"),)
    if station == "HANDOFF":
        return (contained_path(root, "lab_quest_outputs", "handoffs", f"{run_id}_handoff.zip"),)
    if station == "BLASTP":
        return ()
    raise ValueError(f"unsupported Lab Quest station: {station}")


def run_bound_command(command: Iterable[str], *, timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    """Run a bound command without shell interpolation or silent error handling."""
    return subprocess.run(list(command), capture_output=True, text=True, timeout=timeout, check=False)


def validate_package_with_bound_engine(
    *,
    binding: EngineBinding,
    project_root: str | Path,
    package: str | Path,
) -> tuple[list[str], subprocess.CompletedProcess[str], PackageSnapshot | None]:
    """Execute package validation through the bound runner before admitting a snapshot.

    The second, in-process snapshot construction is deliberately a read-only
    identity/provenance guard after the bound CLI has returned success. It does
    not substitute for the receipt-producing engine command.
    """
    package_path = _require_within_project(project_root, package)
    command = build_engine_command(binding, "validate", str(package_path))
    completed = run_bound_command(command)
    if completed.returncode != 0:
        return command, completed, None
    return command, completed, load_package_snapshot(package_path)


def write_run_receipt(
    project_root: str | Path,
    command: list[str],
    input_zip: str | Path,
    returncode: int,
    stdout: str,
    stderr: str,
    binding: EngineBinding,
    *,
    run_id: str,
    station: str,
    package_snapshot: PackageSnapshot | None = None,
    artifact_paths: Iterable[str | Path] = (),
    context: dict[str, str] | None = None,
) -> Path:
    """Write a receipt with execution, provenance, and evidence-state boundaries."""
    root = resolve_project_root(project_root)
    receipts = contained_path(root, "lab_quest_outputs", "receipts")
    receipts.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = receipts / f"lab_quest_{station.lower()}_{run_id}_{stamp}.json"
    artifacts = []
    for artifact in artifact_paths:
        item = _require_within_project(root, artifact)
        artifacts.append(
            {
                "path": str(item),
                "exists": item.exists(),
                "sha256": sha256_file(item) if item.is_file() else "NOT_RECORDED",
            }
        )
    missing_artifacts = [item["path"] for item in artifacts if not item["exists"]]
    receipt_status = "PASS" if returncode == 0 and not missing_artifacts else "FAIL"
    payload: dict[str, object] = {
        "schema": "mamey_lab_quest_workflow_receipt_v2",
        "created_utc": utc_now(),
        "run_id": run_id,
        "station": station,
        "command": command,
        "input_zip": str(Path(input_zip).resolve()),
        "input_sha256": sha256_file(input_zip),
        "returncode": int(returncode),
        "status": receipt_status,
        "engine_binding": binding.as_receipt(),
        "artifacts": artifacts,
        "stdout_tail": stdout[-8000:],
        "stderr_tail": stderr[-8000:],
        "claim_ceiling": CLAIM_CEILING,
    }
    if missing_artifacts:
        payload["receipt_hold"] = "expected station artifact is missing: " + ", ".join(missing_artifacts)
    if package_snapshot is not None:
        payload["package"] = {
            "path": str(package_snapshot.package),
            "manifest_sha256": package_snapshot.manifest_sha256,
            "validator_status": package_snapshot.validator_status,
            "evidence_date_utc": package_snapshot.evidence_date_utc,
            "mode": package_snapshot.mode,
            "release": package_snapshot.release,
            "privacy_tier": package_snapshot.privacy_tier,
            "privacy_assignment_state": package_snapshot.privacy_assignment_state,
        }
    if context:
        payload["context"] = {key: safe_display_text(value, f"receipt context {key}") for key, value in context.items()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def lab_quest_launch_command(
    project_root: str | Path,
    port: int,
    headless: bool,
    *,
    binding: EngineBinding,
) -> tuple[list[str], dict[str, str]]:
    """Launch the optional local UI with an already-validated engine binding."""
    root = resolve_project_root(project_root)
    app = Path(__file__).with_name("lab_quest_app.py").resolve()
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(int(port)),
        "--server.headless",
        "true" if headless else "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    env = dict(os.environ)
    env.update(
        {
            "MAMEY_LAB_QUEST_ROOT": str(root),
            "MAMEY_LAB_QUEST_CODE_TIER": str(binding.code_tier),
            "MAMEY_LAB_QUEST_EXPECT_BUNDLE": binding.bundle_version,
            "MAMEY_LAB_QUEST_EXPECT_ENGINE": binding.engine_version,
        }
    )
    return command, env


def register_subparser(sub):
    parser = sub.add_parser(
        "lab-quest",
        help="launch the optional local Lab Quest interface bound to one verified portable Mamey code tier",
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="explicit contained project root for uploads, runs, and additive UI outputs",
    )
    parser.add_argument("--code-tier", required=True, help="explicit portable code-tier root containing mamey_run.py")
    parser.add_argument("--expect-bundle-version", required=True, help="required bundle version for the code-tier binding")
    parser.add_argument("--expect-engine-version", required=True, help="required engine version for the code-tier binding")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="validate the explicit project/code-tier binding and write its receipt without requiring Streamlit or launching the UI",
    )
    parser.set_defaults(func=run_from_args)
    return parser


def run_from_args(args) -> int:
    try:
        binding = resolve_engine_binding(
            args.code_tier,
            expected_bundle_version=args.expect_bundle_version,
            expected_engine_version=args.expect_engine_version,
        )
        write_engine_binding_receipt(args.project_root, binding)
    except (EngineBindingError, OSError, ValueError) as exc:
        sys.stderr.write(str(f"Lab Quest refused to launch: {exc}") + "\n")
        return 2
    if args.verify_only:
        sys.stdout.write(str(f"Lab Quest binding verified: {binding.code_tier}") + "\n")
        return 0
    if importlib.util.find_spec("streamlit") is None:
        sys.stderr.write(str("Lab Quest requires the optional dependency: pip install 'mamey[labquest]'") + "\n")
        return 2
    command, env = lab_quest_launch_command(args.project_root, args.port, args.headless, binding=binding)
    return subprocess.call(command, env=env)
