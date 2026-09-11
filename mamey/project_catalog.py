"""Portable catalog and private-handoff utilities for multi-strain projects.

The catalog records package locations as logical paths below an explicitly
selected project root.  It does not scan personal directories, infer privacy,
or turn a package into a scientific conclusion.  The optional archive helper
is intentionally a private, byte-verified handoff rather than a public export
or redaction system.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


CATALOG_SCHEMA = "mamey_portable_project_catalog_v1"
HANDOFF_SCHEMA = "mamey_private_project_handoff_v1"
CATALOG_FILENAME = "project_catalog.json"
PRIVATE_HANDOFF_CLASS = "PRIVATE_PROJECT_HANDOFF_ONLY"
_ABSOLUTE_LOCATOR = re.compile(r"^(?:/|\\\\|[A-Za-z]:[\\/]|~[\\/])")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _project_root(value: str | Path) -> Path:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("an explicit project root is required")
    root = Path(value).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError("project root is not a directory")
    return root


def _relative(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("catalog entry must remain below the explicit project root") from exc
    if not relative.parts:
        raise ValueError("project root itself cannot be a catalog package")
    return relative.as_posix()


def _safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if not name or member.is_absolute() or ".." in member.parts or member.parts[0] in {"", "."}:
        raise ValueError(f"unsafe archive member path: {name!r}")
    return member


def _read_manifest(package: Path) -> dict[str, Any]:
    manifest_path = package / "manifest.json"
    if not package.is_dir() or not manifest_path.is_file():
        raise ValueError(f"not a package directory with manifest.json: {package}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("package manifest must be a JSON object")
    return payload


def _first_absolute_locator(value: Any, field: str = "manifest") -> tuple[str, str] | None:
    """Find a legacy absolute locator without changing sealed package evidence."""
    if isinstance(value, dict):
        for key, item in value.items():
            found = _first_absolute_locator(item, f"{field}.{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _first_absolute_locator(item, f"{field}[{index}]")
            if found:
                return found
    elif isinstance(value, str) and _ABSOLUTE_LOCATOR.match(value.strip()):
        return field, value
    return None


@dataclass(frozen=True)
class CatalogEntry:
    package_relative_path: str
    manifest_sha256: str
    strain_id: str
    bundle_version: str
    workflow_version: str
    privacy_tier: str
    privacy_assignment_state: str
    # Binary release is the only safe predicate for a PUBLIC interface.  A
    # named privacy tier can be user-defined and therefore cannot be guessed to
    # mean public.  Older catalogs omit this field and remain private by
    # default when decoded.
    release: str = "PRIVATE"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class ProjectCatalog:
    """A small hash-bound, relative-path package catalog.

    Catalog membership is an availability/provenance fact only.  It is not a
    cohort denominator, scientific acceptance, release decision, or a privacy
    reclassification.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = _project_root(project_root)
        self.path = self.project_root / "lab_quest_outputs" / CATALOG_FILENAME
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"schema": CATALOG_SCHEMA, "entries": [], "claim_ceiling": self.claim_ceiling})

    @property
    def claim_ceiling(self) -> str:
        return (
            "Catalog membership is package availability and provenance only. It does not establish "
            "scientific acceptance, biological identity, activity, production, causality, release, or publication readiness."
        )

    def _read(self) -> dict[str, Any]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema") != CATALOG_SCHEMA or not isinstance(payload.get("entries"), list):
            raise ValueError("project catalog is malformed or uses an unsupported schema")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def _entry_for_package(self, package: str | Path) -> CatalogEntry:
        resolved = Path(package).expanduser().resolve()
        relative = _relative(self.project_root, resolved)
        manifest = _read_manifest(resolved)
        strain = str(manifest.get("strain_id") or manifest.get("display_name") or "").strip()
        if not strain:
            raise ValueError("package manifest has no strain identifier")
        privacy_tier = str(manifest.get("privacy_tier") or manifest.get("release") or "NOT_RECORDED")
        assignment = str(manifest.get("privacy_assignment_state") or "LEGACY_OR_NOT_RECORDED")
        release = str(manifest.get("release") or "PRIVATE").strip().upper()
        if release not in {"PUBLIC", "PRIVATE"}:
            release = "PRIVATE"
        return CatalogEntry(
            package_relative_path=relative,
            manifest_sha256=_sha256(resolved / "manifest.json"),
            strain_id=strain,
            bundle_version=str(manifest.get("bundle_version") or "NOT_RECORDED"),
            workflow_version=str(manifest.get("workflow_version") or "NOT_RECORDED"),
            privacy_tier=privacy_tier,
            privacy_assignment_state=assignment,
            release=release,
        )

    def register_package(self, package: str | Path) -> CatalogEntry:
        """Register or rebind one local package after exact manifest hashing."""
        entry = self._entry_for_package(package)
        payload = self._read()
        entries = [item for item in payload["entries"] if item.get("package_relative_path") != entry.package_relative_path]
        entries.append(entry.as_dict())
        payload["entries"] = sorted(entries, key=lambda item: str(item["package_relative_path"]))
        self._write(payload)
        return entry

    def entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(CatalogEntry(**item) for item in self._read()["entries"])

    def listed_entries(self, visibility: str = "PRIVATE_PROJECT") -> tuple[CatalogEntry, ...]:
        """Return hash-current entries for one explicitly named interface view.

        PUBLIC is deliberately an allowlist: only a manifest that explicitly
        recorded binary ``release=PUBLIC`` reaches the returned rows.  Filtering
        happens before callers build labels, tables, or widget options, so a
        private strain identifier cannot leak through presentation formatting.
        """
        view = str(visibility or "").strip().upper()
        if view not in {"PUBLIC", "PRIVATE_PROJECT"}:
            raise ValueError("catalog visibility must be PUBLIC or PRIVATE_PROJECT")
        verified: list[CatalogEntry] = []
        for entry in self.entries():
            # Privacy filtering must precede every operation that could echo a
            # private logical path in an error shown by the PUBLIC interface.
            if view == "PUBLIC" and entry.release != "PUBLIC":
                continue
            member = _safe_member(entry.package_relative_path)
            package = (self.project_root / Path(*member.parts)).resolve()
            _relative(self.project_root, package)
            _read_manifest(package)
            if _sha256(package / "manifest.json") != entry.manifest_sha256:
                raise ValueError(f"catalog manifest hash is stale for {entry.package_relative_path}")
            verified.append(entry)
        return tuple(verified)

    def listing_rows(self, visibility: str = "PRIVATE_PROJECT") -> tuple[dict[str, str], ...]:
        """Build presentation-safe rows only after privacy filtering and hash checks."""
        return tuple(entry.as_dict() for entry in self.listed_entries(visibility))

    def verified_packages(self, visibility: str = "PRIVATE_PROJECT") -> tuple[Path, ...]:
        """Return visible entries only when every locator and manifest hash is current."""
        verified: list[Path] = []
        for entry in self.listed_entries(visibility):
            member = _safe_member(entry.package_relative_path)
            package = (self.project_root / Path(*member.parts)).resolve()
            verified.append(package)
        return tuple(verified)

    def verification_report(self) -> dict[str, Any]:
        packages = self.verified_packages()
        return {
            "schema": CATALOG_SCHEMA,
            "catalog_sha256": _sha256(self.path),
            "entry_count": len(packages),
            "packages": [str(path.relative_to(self.project_root)) for path in packages],
            "claim_ceiling": self.claim_ceiling,
        }


def _iter_package_files(root: Path, packages: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for package in packages:
        for path in sorted(package.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"project handoff refuses symbolic links: {path}")
            if path.is_file():
                _relative(root, path)
                files.append(path)
    return sorted(set(files), key=lambda item: _relative(root, item))


def _portfolio_files(root: Path) -> tuple[list[Path], dict[str, Any] | None]:
    """Return an optional current portfolio binding and its source files.

    The import is local so projects that do not use an evidence portfolio keep
    the catalog lightweight. A stale binding is refused: copying it would
    detach the recipient's typed availability summary from its policy inputs.

    B8/v9.7.405 rebase note: adapted from CODEX_391_PORTFOLIO_AWARE_PRIVATE_HANDOFF_2026-08-29,
    which travelled a separate profile_sha256 + evidence_registry_sha256 pair (the superseded
    privacy_profile.py/evidence_registry.py shape). This module's mamey/portfolio_config.py
    already consolidates both into one registry_sha256 (mamey/project_registry.py), so only that
    single hash needs to travel with the handoff.
    """
    binding_path = root / "lab_quest_outputs" / "portfolio_binding.json"
    if not binding_path.is_file():
        return [], None
    from .portfolio_config import PORTFOLIO_BINDING_SCHEMA, load_portfolio_binding

    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    if payload.get("schema") != PORTFOLIO_BINDING_SCHEMA:
        raise ValueError("portfolio binding has an unsupported schema")
    current = load_portfolio_binding(root, str(payload.get("config_relative_path") or ""))
    for key in ("config_sha256", "registry_sha256"):
        if payload.get(key) != getattr(current, key):
            raise ValueError(f"portfolio binding is stale: {key}")
    config = root / Path(*_safe_member(current.config_relative_path).parts)
    registry = root / Path(*_safe_member(current.registry_relative_path).parts)
    return [binding_path, config, registry], {
        "binding_sha256": _sha256(binding_path),
        "config_sha256": current.config_sha256,
        "registry_sha256": current.registry_sha256,
    }


def export_private_project_handoff(project_root: str | Path, output_zip: str | Path) -> Path:
    """Write a deterministic, non-public archive of catalogued package files.

    This helper deliberately has no "public" mode and performs no redaction.
    A project that needs a public release must pass through its separately
    governed public-tier process.
    """
    root = _project_root(project_root)
    catalog = ProjectCatalog(root)
    packages = catalog.verified_packages()
    for package in packages:
        absolute = _first_absolute_locator(_read_manifest(package))
        if absolute:
            field, _ = absolute
            raise ValueError(
                f"private handoff refuses package {package.name}: {field} contains an absolute locator. "
                "Preserve the sealed package and create a governed relocation record before export."
            )
    output = Path(output_zip).expanduser().resolve()
    if output.exists() and output.is_dir():
        raise ValueError("handoff output must be a file path")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_relative_to(root):
        raise ValueError("handoff archive must be written outside the project root to avoid self-inclusion")
    portfolio_files, portfolio = _portfolio_files(root)
    files = [catalog.path, *portfolio_files, *_iter_package_files(root, packages)]
    records = [
        {"path": _relative(root, path), "sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in files
    ]
    manifest = {
        "schema": HANDOFF_SCHEMA,
        "handoff_class": PRIVATE_HANDOFF_CLASS,
        "catalog_sha256": _sha256(catalog.path),
        "files": records,
        "claim_ceiling": catalog.claim_ceiling,
    }
    if portfolio is not None:
        manifest["portfolio"] = portfolio
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            member = _relative(root, path)
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("handoff_manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def import_private_project_handoff(input_zip: str | Path, project_root: str | Path) -> dict[str, Any]:
    """Import a private handoff only after path and hash verification.

    Import requires an empty destination.  This prevents accidental merging of
    unrelated projects and makes the imported project root portable by design.
    """
    source = Path(input_zip).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    root = _project_root(project_root)
    if any(root.iterdir()):
        raise ValueError("private handoff import requires an empty destination project root")
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise ValueError("private handoff archive fails its CRC check")
        names = archive.namelist()
        for name in names:
            _safe_member(name)
        if "handoff_manifest.json" not in names:
            raise ValueError("private handoff lacks handoff_manifest.json")
        manifest = json.loads(archive.read("handoff_manifest.json"))
        if manifest.get("schema") != HANDOFF_SCHEMA or manifest.get("handoff_class") != PRIVATE_HANDOFF_CLASS:
            raise ValueError("archive is not a supported private project handoff")
        records = manifest.get("files")
        if not isinstance(records, list) or not records:
            raise ValueError("private handoff manifest has no file inventory")
        declared = {str(item.get("path") or ""): item for item in records}
        if set(names) != set(declared) | {"handoff_manifest.json"}:
            raise ValueError("private handoff member set does not match its manifest")
        staging = Path(tempfile.mkdtemp(prefix="mamey_project_import_", dir=root.parent))
        try:
            for name, item in sorted(declared.items()):
                member = _safe_member(name)
                data = archive.read(name)
                if len(data) != int(item.get("bytes", -1)) or hashlib.sha256(data).hexdigest() != item.get("sha256"):
                    raise ValueError(f"private handoff hash mismatch: {name}")
                target = staging.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            catalog_path = staging / "lab_quest_outputs" / CATALOG_FILENAME
            if not catalog_path.is_file() or _sha256(catalog_path) != manifest.get("catalog_sha256"):
                raise ValueError("private handoff catalog is absent or hash-mismatched")
            shutil.copytree(staging, root, dirs_exist_ok=True)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    report = ProjectCatalog(root).verification_report()
    if manifest.get("portfolio") is not None:
        from .portfolio_config import load_portfolio_binding
        binding_path = root / "lab_quest_outputs" / "portfolio_binding.json"
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        current = load_portfolio_binding(root, str(payload.get("config_relative_path") or ""))
        for key in ("config_sha256", "registry_sha256"):
            if manifest["portfolio"].get(key) != getattr(current, key):
                raise ValueError(f"imported portfolio binding hash mismatch: {key}")
    report.update({"handoff_sha256": _sha256(source), "handoff_class": PRIVATE_HANDOFF_CLASS})
    return report
