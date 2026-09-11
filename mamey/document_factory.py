"""Token-light batch authoring for governed Sapote documents.

The factory moves repeated metadata into one YAML project manifest and allows
multiple documents to reuse small Markdown body templates.  It materializes
fully governed Markdown, validates every document before rendering any output,
then delegates to :mod:`mamey.document_export`.  Substitution is deliberately
non-programmable: ``{{name}}`` placeholders map only to explicit scalar values.
"""
from __future__ import annotations

import sys

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

import yaml

from .document_export import export_document
from .sapote_markdown import parse_path, validate_model


PROJECT_SCHEMA_VERSION = "sapote-document-project-1.0"
DOCUMENT_SCHEMA_VERSION = "sapote-markdown-1.0"
DOCUMENT_TYPES = {"human_guide", "analysis_report", "mode_b_card"}
OUTPUT_FORMATS = {"docx", "pdf", "both"}
DEFAULT_PROFILES = {
    "human_guide": "human_guide",
    "analysis_report": "scientific_report",
    "mode_b_card": "mode_b_card",
}
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_PLACEHOLDER = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_IMAGE = re.compile(r"!\[[^]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


class DocumentFactoryError(ValueError):
    """Raised when a project cannot be normalized safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(base: Path, relative: str, *, kind: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise DocumentFactoryError(f"{kind}_PATH_MUST_BE_PORTABLE_RELATIVE:{relative}")
    resolved = (base / candidate).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise DocumentFactoryError(f"{kind}_PATH_ESCAPES_PROJECT:{relative}")
    return resolved


def _load_mapping(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise DocumentFactoryError("PROJECT_ROOT_MAPPING_REQUIRED")
    return raw


def _scalar_mapping(raw: Any, *, field: str) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise DocumentFactoryError(f"{field.upper()}_MAPPING_REQUIRED")
    values: dict[str, str] = {}
    for key, value in raw.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(key)):
            raise DocumentFactoryError(f"VARIABLE_NAME_INVALID:{key}")
        if isinstance(value, (dict, list)) or value is None:
            raise DocumentFactoryError(f"VARIABLE_SCALAR_REQUIRED:{key}")
        values[str(key)] = str(value)
    return values


def _render_placeholders(text: str, values: dict[str, str], *, source: str) -> str:
    required = set(_PLACEHOLDER.findall(text))
    missing = sorted(required - set(values))
    if missing:
        raise DocumentFactoryError(f"TEMPLATE_VARIABLES_MISSING:{source}:{','.join(missing)}")
    rendered = _PLACEHOLDER.sub(lambda match: values[match.group(1)], text)
    if "{{" in rendered or "}}" in rendered:
        raise DocumentFactoryError(f"TEMPLATE_MARKUP_UNRESOLVED:{source}")
    return rendered


def _exact_locus(raw: Any, *, document_id: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise DocumentFactoryError(f"EXACT_LOCUS_REQUIRED:{document_id}")
    fields = {
        "strain": str(raw.get("strain", "")).strip(),
        "node_or_contig": str(raw.get("node_or_contig", "")).strip(),
        "region": str(raw.get("region", "")).strip(),
        "bgc_alias": str(raw.get("bgc_alias", "")).strip(),
    }
    if not all(fields.values()):
        raise DocumentFactoryError(f"EXACT_LOCUS_INCOMPLETE:{document_id}")
    return fields


def _merge(defaults: dict[str, Any], entry: dict[str, Any], field: str, fallback: str = "") -> str:
    value = entry.get(field, defaults.get(field, fallback))
    return str(value).strip()


def _document_plan(
    *, project_root: Path, defaults: dict[str, Any], entry: dict[str, Any], seen: set[str]
) -> dict[str, Any]:
    document_id = str(entry.get("id", "")).strip()
    if not _IDENTIFIER.fullmatch(document_id) or document_id in seen:
        raise DocumentFactoryError(f"DOCUMENT_ID_MISSING_INVALID_OR_DUPLICATE:{document_id}")
    seen.add(document_id)
    document_type = _merge(defaults, entry, "document_type")
    if document_type not in DOCUMENT_TYPES:
        raise DocumentFactoryError(f"DOCUMENT_TYPE_INVALID:{document_id}:{document_type}")
    source_value = str(entry.get("source", "")).strip()
    source = _contained(project_root, source_value, kind="SOURCE")
    if not source.is_file():
        raise DocumentFactoryError(f"SOURCE_MISSING:{document_id}:{source_value}")
    output_format = _merge(defaults, entry, "output_format", "both")
    if output_format not in OUTPUT_FORMATS:
        raise DocumentFactoryError(f"OUTPUT_FORMAT_INVALID:{document_id}:{output_format}")

    required_meta = {
        "title": _merge(defaults, entry, "title"),
        "audience": _merge(defaults, entry, "audience"),
        "authority": _merge(defaults, entry, "authority"),
        "claim_safety_footer": _merge(defaults, entry, "claim_safety_footer"),
    }
    missing = [key for key, value in required_meta.items() if not value]
    if missing:
        raise DocumentFactoryError(f"DOCUMENT_METADATA_MISSING:{document_id}:{','.join(missing)}")
    exact = _exact_locus(entry.get("exact_locus"), document_id=document_id) if document_type == "mode_b_card" else None
    variables = _scalar_mapping(defaults.get("variables"), field="default_variables")
    variables.update(_scalar_mapping(entry.get("variables"), field="variables"))
    variables.update({"document_id": document_id, **required_meta})
    if exact:
        exact_display = " / ".join(exact[field] for field in ("strain", "node_or_contig", "region", "bgc_alias"))
        variables.update(exact)
        variables["exact_locus"] = exact_display
    return {
        "id": document_id,
        "document_type": document_type,
        "source": source,
        "source_locator": source_value,
        "title": required_meta["title"],
        "subtitle": _merge(defaults, entry, "subtitle"),
        "audience": required_meta["audience"],
        "authority": required_meta["authority"],
        "claim_safety_footer": required_meta["claim_safety_footer"],
        "render_profile": _merge(defaults, entry, "render_profile", DEFAULT_PROFILES[document_type]),
        "source_manifest": _merge(defaults, entry, "source_manifest"),
        "output_format": output_format,
        "exact_locus": exact,
        "variables": variables,
    }


def _front_matter(plan: dict[str, Any]) -> str:
    meta: dict[str, Any] = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "document_type": plan["document_type"],
        "title": plan["title"],
        "subtitle": plan["subtitle"],
        "audience": plan["audience"],
        "authority": plan["authority"],
        "render_profile": plan["render_profile"],
        "claim_safety_footer": plan["claim_safety_footer"],
    }
    if plan["source_manifest"]:
        meta["source_manifest"] = plan["source_manifest"]
    if plan["exact_locus"]:
        meta["exact_locus"] = plan["exact_locus"]
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).rstrip() + "\n---\n\n"


def _copy_assets(*, body: str, source: Path, normalized_dir: Path) -> None:
    for asset_locator in sorted(set(_IMAGE.findall(body))):
        asset = _contained(source.parent, asset_locator, kind="ASSET")
        if not asset.is_file():
            raise DocumentFactoryError(f"ASSET_MISSING:{source}:{asset_locator}")
        target = normalized_dir / asset_locator
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)


def _normalize(plan: dict[str, Any], normalized_root: Path) -> Path:
    raw_body = plan["source"].read_text(encoding="utf-8")
    body = _render_placeholders(raw_body, plan["variables"], source=plan["source_locator"]).strip() + "\n"
    if body.startswith("---\n"):
        raise DocumentFactoryError(f"BODY_FRONT_MATTER_FORBIDDEN:{plan['id']}")
    h1s = _H1.findall(body)
    if plan["document_type"] == "mode_b_card":
        exact_display = plan["variables"]["exact_locus"]
        if not h1s:
            body = f"# {exact_display} — {plan['title']}\n\n" + body
        elif len(h1s) != 1 or exact_display not in h1s[0]:
            raise DocumentFactoryError(f"MODEB_H1_EXACT_LOCUS_MISMATCH:{plan['id']}")
    normalized_dir = normalized_root / plan["id"]
    normalized_dir.mkdir(parents=True, exist_ok=False)
    _copy_assets(body=body, source=plan["source"], normalized_dir=normalized_dir)
    normalized = normalized_dir / f"{plan['id']}.md"
    normalized.write_text(_front_matter(plan) + body, encoding="utf-8")
    model = parse_path(normalized)
    validation = validate_model(model, require_assets=True)
    validation.raise_for_errors()
    return normalized


def _project_plans(project_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    project = _load_mapping(project_path)
    if str(project.get("schema_version", "")).strip() != PROJECT_SCHEMA_VERSION:
        raise DocumentFactoryError("PROJECT_SCHEMA_VERSION_UNSUPPORTED")
    defaults = project.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise DocumentFactoryError("DEFAULTS_MAPPING_REQUIRED")
    entries = project.get("documents")
    if not isinstance(entries, list) or not entries:
        raise DocumentFactoryError("DOCUMENTS_NONEMPTY_LIST_REQUIRED")
    seen: set[str] = set()
    plans = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise DocumentFactoryError("DOCUMENT_ENTRY_MAPPING_REQUIRED")
        plans.append(_document_plan(project_root=project_path.parent, defaults=defaults, entry=entry, seen=seen))
    return project, plans


def _replace_prefix(value: Any, old: str, new: str) -> Any:
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [_replace_prefix(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: _replace_prefix(item, old, new) for key, item in value.items()}
    return value


def _repair_render_receipts(output_root: Path, old_root: Path) -> None:
    old = str(old_root.resolve())
    new = str(output_root.resolve())
    for receipt in output_root.rglob("*.render_receipt.json"):
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        payload = _replace_prefix(payload, old, new)
        receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_project(project_file: str | Path) -> dict[str, Any]:
    project_path = Path(project_file).resolve()
    _, plans = _project_plans(project_path)
    with tempfile.TemporaryDirectory(prefix="sapote-doc-check-") as temporary:
        normalized_root = Path(temporary) / "normalized"
        normalized_root.mkdir()
        normalized = [_normalize(plan, normalized_root) for plan in plans]
        return {
            "status": "PASS",
            "schema_version": PROJECT_SCHEMA_VERSION,
            "project": str(project_path),
            "document_count": len(plans),
            "documents": [plan["id"] for plan in plans],
            "normalized_sha256": {path.stem: _sha256(path) for path in normalized},
        }


def build_project(
    project_file: str | Path,
    *,
    outdir: str | Path | None = None,
) -> dict[str, Any]:
    project_path = Path(project_file).resolve()
    project, plans = _project_plans(project_path)
    output_root = Path(outdir).resolve() if outdir else (project_path.parent / "rendered_documents").resolve()
    if output_root.exists():
        raise DocumentFactoryError(f"OUTPUT_ROOT_ALREADY_EXISTS:{output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".sapote-doc-build-", dir=output_root.parent)).resolve()
    try:
        normalized_root = staging / "normalized"
        render_root = staging / "documents"
        normalized_root.mkdir()
        render_root.mkdir()
        prepared: list[tuple[dict[str, Any], Path]] = []
        for plan in plans:
            prepared.append((plan, _normalize(plan, normalized_root)))
        for plan, normalized in prepared:
            export_document(normalized, outdir=render_root / plan["id"], output_format=plan["output_format"])
        staging.replace(output_root)
        _repair_render_receipts(output_root, staging)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    outputs: list[dict[str, Any]] = []
    for plan in plans:
        folder = output_root / "documents" / plan["id"]
        for extension in (["docx", "pdf"] if plan["output_format"] == "both" else [plan["output_format"]]):
            artifact = folder / f"{plan['id']}.{extension}"
            outputs.append({
                "document_id": plan["id"], "format": extension,
                "path": str(artifact), "sha256": _sha256(artifact), "bytes": artifact.stat().st_size,
            })

    unique_templates = sorted({plan["source"] for plan in plans})
    authored_bytes = project_path.stat().st_size + sum(path.stat().st_size for path in unique_templates)
    normalized_files = sorted((output_root / "normalized").glob("*/*.md"))
    normalized_bytes = sum(path.stat().st_size for path in normalized_files)
    receipt = {
        "status": "PASS",
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_path": str(project_path),
        "project_sha256": _sha256(project_path),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "document_count": len(plans),
        "template_count": len(unique_templates),
        "documents": [plan["id"] for plan in plans],
        "templates": [
            {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in unique_templates
        ],
        "outputs": outputs,
        "token_light_metrics": {
            "project_plus_unique_template_bytes": authored_bytes,
            "materialized_governed_markdown_bytes": normalized_bytes,
            "reuse_multiple": round(normalized_bytes / authored_bytes, 3) if authored_bytes else None,
            "approx_authored_tokens": round(authored_bytes / 4),
            "approx_materialized_tokens": round(normalized_bytes / 4),
            "note": "Approximation uses four UTF-8 bytes per token; it is a workflow comparison, not a tokenizer measurement.",
        },
        "authority": str(project.get("authority", "PROJECT_RENDER_ONLY_NOT_SCIENTIFIC_VALIDATION")),
    }
    receipt_path = output_root / "DOCUMENT_FACTORY_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def init_project(directory: str | Path) -> list[str]:
    root = Path(directory).resolve()
    if root.exists() and any(root.iterdir()):
        raise DocumentFactoryError(f"INIT_DIRECTORY_NOT_EMPTY:{root}")
    (root / "templates").mkdir(parents=True, exist_ok=True)
    manifest = root / "sapote-documents.yml"
    guide = root / "templates" / "guide.md"
    manifest.write_text(
        """schema_version: sapote-document-project-1.0
authority: PROJECT_RENDER_ONLY_NOT_SCIENTIFIC_VALIDATION
defaults:
  audience: New users
  authority: User documentation; not a biological result
  claim_safety_footer: Software guidance only; scientific conclusions require source review.
  output_format: both
documents:
  - id: quickstart
    source: templates/guide.md
    document_type: human_guide
    title: Five-Minute Quickstart
    subtitle: A governed document starter
""",
        encoding="utf-8",
    )
    guide.write_text(
        """# Start here

> [LEAD] The short version
> Replace this sentence with the reader's most important takeaway.

## First steps

1. Add the source-derived facts.
2. State the decision or next action.
3. Preserve the relevant claim ceiling.
""",
        encoding="utf-8",
    )
    return [str(manifest), str(guide)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Token-light Sapote document project factory")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Normalize and validate every document without rendering")
    check.add_argument("project")
    build = sub.add_parser("build", help="Validate all documents, then render the complete batch")
    build.add_argument("project")
    build.add_argument("--outdir", default=None)
    init = sub.add_parser("init", help="Create a minimal manifest and reusable guide body")
    init.add_argument("directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            result = check_project(args.project)
        elif args.command == "build":
            result = build_project(args.project, outdir=args.outdir)
        else:
            result = {"status": "PASS", "created": init_project(args.directory)}
    except Exception as exc:
        sys.stdout.write(str(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2)) + "\n")
        return 1
    sys.stdout.write(str(json.dumps(result, indent=2)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
