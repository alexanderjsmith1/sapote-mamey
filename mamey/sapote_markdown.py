"""Constrained Sapote Markdown parser and validator.

This module deliberately implements a small, governed Markdown profile instead
of trying to accept every Markdown dialect.  It produces one canonical block
model consumed by both the DOCX and PDF renderers in ``mamey.document_export``.
No scientific calculation or authored prose is changed by this layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "sapote-markdown-1.0"
DOCUMENT_TYPES = {"human_guide", "analysis_report", "mode_b_card"}
RENDER_PROFILES = {"human_guide", "scientific_report", "mode_b_card"}
CALLOUT_TYPES = {"LEAD", "NOTE", "CAUTION", "HOLD", "CLAIM CEILING", "DECISION"}
TABLE_LAYOUTS = {"auto", "portrait", "landscape", "companion"}
FIGURE_LAYOUTS = {"full", "column", "landscape"}


class SapoteMarkdownError(ValueError):
    """Raised when governed Markdown cannot be parsed or validated."""


@dataclass(frozen=True)
class ExactLocus:
    strain: str
    node_or_contig: str
    region: str
    bgc_alias: str

    @property
    def display(self) -> str:
        return f"{self.strain} / {self.node_or_contig} / {self.region} / {self.bgc_alias}"


@dataclass(frozen=True)
class DocumentMeta:
    schema_version: str
    document_type: str
    title: str
    subtitle: str
    audience: str
    authority: str
    render_profile: str
    claim_safety_footer: str
    exact_locus: ExactLocus | None = None
    source_manifest: str = ""


@dataclass(frozen=True)
class Block:
    kind: str
    data: dict[str, Any]


@dataclass
class DocumentModel:
    meta: DocumentMeta
    blocks: list[Block]
    source_path: str
    source_sha256: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": asdict(self.meta),
            "blocks": [asdict(block) for block in self.blocks],
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "warnings": list(self.warnings),
        }

    def canonical_sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    line: int | None = None


@dataclass
class ValidationResult:
    issues: list[ValidationIssue]
    warnings: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not self.issues

    def raise_for_errors(self) -> None:
        if not self.ok:
            rendered = "; ".join(
                f"{issue.code}{f' at line {issue.line}' if issue.line else ''}: {issue.message}"
                for issue in self.issues
            )
            raise SapoteMarkdownError(rendered)


_DIRECTIVE = re.compile(r"^<!--\s*sapote:(?P<kind>[a-z-]+)(?P<args>.*?)-->\s*$", re.I)
_IMAGE = re.compile(r"^!\[(?P<alt>[^]]*)\]\((?P<src>[^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$")
_HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
_NUMBERED = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
_MODEB_HEADING = re.compile(r"^§(\d+)\s+(.+?)\s*$")
_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SapoteMarkdownError("FRONT_MATTER_REQUIRED: document must begin with YAML front matter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise SapoteMarkdownError("FRONT_MATTER_UNCLOSED: closing --- not found") from exc
    raw = "\n".join(lines[1:end])
    parsed = yaml.safe_load(raw) or {}
    if not isinstance(parsed, dict):
        raise SapoteMarkdownError("FRONT_MATTER_OBJECT_REQUIRED: YAML root must be a mapping")
    return parsed, "\n".join(lines[end + 1 :]), end + 2


def _meta_from_mapping(raw: dict[str, Any]) -> DocumentMeta:
    exact_raw = raw.get("exact_locus")
    exact = None
    if exact_raw is not None:
        if not isinstance(exact_raw, dict):
            raise SapoteMarkdownError("EXACT_LOCUS_OBJECT_REQUIRED")
        exact = ExactLocus(
            strain=str(exact_raw.get("strain", "")).strip(),
            node_or_contig=str(exact_raw.get("node_or_contig", "")).strip(),
            region=str(exact_raw.get("region", "")).strip(),
            bgc_alias=str(exact_raw.get("bgc_alias", "")).strip(),
        )
    return DocumentMeta(
        schema_version=str(raw.get("schema_version", "")).strip(),
        document_type=str(raw.get("document_type", "")).strip(),
        title=str(raw.get("title", "")).strip(),
        subtitle=str(raw.get("subtitle", "")).strip(),
        audience=str(raw.get("audience", "")).strip(),
        authority=str(raw.get("authority", "")).strip(),
        render_profile=str(raw.get("render_profile", "")).strip(),
        claim_safety_footer=str(raw.get("claim_safety_footer", "")).strip(),
        exact_locus=exact,
        source_manifest=str(raw.get("source_manifest", "")).strip(),
    )


def _directive_args(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in shlex.split(raw.strip()):
        if "=" not in token:
            raise SapoteMarkdownError(f"DIRECTIVE_ARGUMENT_INVALID:{token}")
        key, value = token.split("=", 1)
        values[key.strip().lower().replace("-", "_")] = value.strip()
    return values


def _bool(value: str, *, key: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise SapoteMarkdownError(f"DIRECTIVE_BOOLEAN_INVALID:{key}={value}")


def _table_rows(lines: list[str], line_number: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for offset, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if offset == 1:
            if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                raise SapoteMarkdownError(f"TABLE_SEPARATOR_INVALID at line {line_number + offset}")
            continue
        rows.append(cells)
    if len(rows) < 2:
        raise SapoteMarkdownError(f"TABLE_BODY_REQUIRED at line {line_number}")
    width = len(rows[0])
    if width < 1 or any(len(row) != width for row in rows):
        raise SapoteMarkdownError(f"TABLE_RECTANGULAR_REQUIRED at line {line_number}")
    return rows


def _caption_field(line: str, field_name: str, line_number: int) -> str:
    match = re.match(rf"^\*\*{re.escape(field_name)}:\*\*\s+(.+?)\s*$", line, re.I)
    if not match:
        raise SapoteMarkdownError(f"FIGURE_{field_name.upper()}_REQUIRED at line {line_number}")
    return match.group(1).strip()


def parse_text(text: str, *, source_path: str = "<memory>") -> DocumentModel:
    raw_meta, body, body_start = _parse_front_matter(text)
    meta = _meta_from_mapping(raw_meta)
    lines = body.splitlines()
    blocks: list[Block] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    index = 0

    def line_no(offset: int = 0) -> int:
        return body_start + index + offset

    def skip_blank(pos: int) -> int:
        while pos < len(lines) and not lines[pos].strip():
            pos += 1
        return pos

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        directive = _DIRECTIVE.match(stripped)
        if directive:
            kind = directive.group("kind").lower()
            args = _directive_args(directive.group("args"))
            if kind == "page-break":
                if args:
                    raise SapoteMarkdownError(f"PAGE_BREAK_ARGUMENTS_FORBIDDEN at line {line_no()}")
                blocks.append(Block("page_break", {}))
                index += 1
                continue
            if kind == "table":
                identifier = args.get("id", "")
                if not identifier or identifier in seen_ids:
                    raise SapoteMarkdownError(f"TABLE_ID_MISSING_OR_DUPLICATE at line {line_no()}")
                seen_ids.add(identifier)
                layout = args.get("layout", "auto")
                repeat_header = _bool(args.get("repeat_header", "true"), key="repeat_header")
                widths = [float(value) for value in args.get("widths", "").split(",") if value]
                start = skip_blank(index + 1)
                table_lines: list[str] = []
                while start + len(table_lines) < len(lines) and lines[start + len(table_lines)].lstrip().startswith("|"):
                    table_lines.append(lines[start + len(table_lines)])
                if len(table_lines) < 3:
                    raise SapoteMarkdownError(f"TABLE_MARKDOWN_REQUIRED at line {line_no()}")
                rows = _table_rows(table_lines, body_start + start)
                blocks.append(Block("table", {
                    "id": identifier,
                    "layout": layout,
                    "repeat_header": repeat_header,
                    "widths": widths,
                    "rows": rows,
                }))
                index = start + len(table_lines)
                continue
            if kind == "figure":
                identifier = args.get("id", "")
                if not identifier or identifier in seen_ids:
                    raise SapoteMarkdownError(f"FIGURE_ID_MISSING_OR_DUPLICATE at line {line_no()}")
                seen_ids.add(identifier)
                layout = args.get("layout", "full")
                start = skip_blank(index + 1)
                if start >= len(lines):
                    raise SapoteMarkdownError(f"FIGURE_IMAGE_REQUIRED at line {line_no()}")
                image = _IMAGE.match(lines[start].strip())
                if not image:
                    raise SapoteMarkdownError(f"FIGURE_IMAGE_REQUIRED at line {body_start + start}")
                cursor = skip_blank(start + 1)
                if cursor + 2 >= len(lines):
                    raise SapoteMarkdownError(f"FIGURE_METADATA_INCOMPLETE at line {body_start + cursor}")
                caption = _caption_field(lines[cursor], "Caption", body_start + cursor)
                methods = _caption_field(lines[cursor + 1], "Methods", body_start + cursor + 1)
                source = _caption_field(lines[cursor + 2], "Source", body_start + cursor + 2)
                blocks.append(Block("figure", {
                    "id": identifier,
                    "layout": layout,
                    "src": image.group("src"),
                    "alt": image.group("alt").strip(),
                    "caption": caption,
                    "methods": methods,
                    "source": source,
                }))
                index = cursor + 3
                continue
            raise SapoteMarkdownError(f"DIRECTIVE_UNKNOWN:{kind} at line {line_no()}")

        if _HTML_TAG.search(stripped):
            raise SapoteMarkdownError(f"RAW_HTML_FORBIDDEN at line {line_no()}")
        heading = _HEADING.match(line)
        if heading:
            blocks.append(Block("heading", {"level": len(heading.group(1)), "text": heading.group(2).strip()}))
            index += 1
            continue
        if line.lstrip().startswith("|"):
            raise SapoteMarkdownError(f"TABLE_DIRECTIVE_REQUIRED at line {line_no()}")
        if line.lstrip().startswith(">"):
            quote_lines: list[str] = []
            start_line = line_no()
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quote_lines.append(lines[index].lstrip()[1:].strip())
                index += 1
            callout_type = "NOTE"
            title = "Note"
            if quote_lines:
                tagged = re.match(r"^\[([^]]+)\]\s*(.*)$", quote_lines[0])
                if tagged:
                    callout_type = tagged.group(1).strip().upper()
                    title = tagged.group(2).strip() or callout_type.title()
                    quote_lines = quote_lines[1:]
            blocks.append(Block("callout", {
                "type": callout_type,
                "title": title,
                "text": " ".join(quote_lines).strip(),
                "source_line": start_line,
            }))
            continue
        bullet = _BULLET.match(line)
        if bullet:
            items: list[str] = []
            while index < len(lines):
                match = _BULLET.match(lines[index])
                if not match:
                    break
                items.append(match.group(1).strip())
                index += 1
            blocks.append(Block("list", {"ordered": False, "items": items}))
            continue
        numbered = _NUMBERED.match(line)
        if numbered:
            items = []
            expected = 1
            while index < len(lines):
                match = _NUMBERED.match(lines[index])
                if not match:
                    break
                observed = int(match.group(1))
                if observed != expected:
                    warnings.append(f"NUMBERED_LIST_RENUMBERED at line {line_no()}: observed {observed}, expected {expected}")
                items.append(match.group(2).strip())
                expected += 1
                index += 1
            blocks.append(Block("list", {"ordered": True, "items": items}))
            continue
        if stripped in {"---", "***", "___"}:
            blocks.append(Block("rule", {}))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            cstrip = candidate.strip()
            if not cstrip or _DIRECTIVE.match(cstrip) or _HEADING.match(candidate) or _BULLET.match(candidate) or _NUMBERED.match(candidate) or candidate.lstrip().startswith((">", "|")) or cstrip in {"---", "***", "___"}:
                break
            if _HTML_TAG.search(cstrip):
                raise SapoteMarkdownError(f"RAW_HTML_FORBIDDEN at line {line_no()}")
            paragraph_lines.append(cstrip)
            index += 1
        blocks.append(Block("paragraph", {"text": " ".join(paragraph_lines)}))

    source_bytes = text.encode("utf-8")
    model = DocumentModel(meta, blocks, source_path, _sha256_bytes(source_bytes), warnings)
    result = validate_model(model)
    result.raise_for_errors()
    model.warnings.extend(issue.message for issue in result.warnings)
    return model


def parse_path(path: str | Path) -> DocumentModel:
    source = Path(path)
    return parse_text(source.read_text(encoding="utf-8"), source_path=str(source.resolve()))


def _validate_exact_locus(exact: ExactLocus | None) -> list[ValidationIssue]:
    if exact is None:
        return [ValidationIssue("EXACT_LOCUS_REQUIRED", "Mode B documents require exact_locus front matter")]
    issues = []
    if not all((exact.strain, exact.node_or_contig, exact.region, exact.bgc_alias)):
        issues.append(ValidationIssue("EXACT_LOCUS_INCOMPLETE", "all four identity components are mandatory"))
    if exact.region and not re.fullmatch(r"region\d+", exact.region, re.I):
        issues.append(ValidationIssue("REGION_INVALID", exact.region))
    if exact.bgc_alias and not re.fullmatch(r"BGC\d+", exact.bgc_alias, re.I):
        issues.append(ValidationIssue("BGC_ALIAS_INVALID", exact.bgc_alias))
    if exact.node_or_contig and exact.node_or_contig.upper() in {"NODE", "CONTIG", "CTG", "UNKNOWN"}:
        issues.append(ValidationIssue("FULL_NODE_REQUIRED", exact.node_or_contig))
    return issues


def validate_model(model: DocumentModel, *, require_assets: bool = False) -> ValidationResult:
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    meta = model.meta
    if meta.schema_version != SCHEMA_VERSION:
        issues.append(ValidationIssue("SCHEMA_VERSION_UNSUPPORTED", meta.schema_version or "missing"))
    if meta.document_type not in DOCUMENT_TYPES:
        issues.append(ValidationIssue("DOCUMENT_TYPE_INVALID", meta.document_type or "missing"))
    if meta.render_profile not in RENDER_PROFILES:
        issues.append(ValidationIssue("RENDER_PROFILE_INVALID", meta.render_profile or "missing"))
    for key, value in (("title", meta.title), ("audience", meta.audience), ("authority", meta.authority), ("claim_safety_footer", meta.claim_safety_footer)):
        if not value:
            issues.append(ValidationIssue(f"META_{key.upper()}_REQUIRED", key))
    if len(meta.claim_safety_footer) > 190:
        issues.append(ValidationIssue("FOOTER_TOO_LONG", "claim_safety_footer must be <=190 characters"))
    if "judgment deferred" in meta.claim_safety_footer.lower():
        issues.append(ValidationIssue("DECORATIVE_JUDGMENT_DEFERRED_FORBIDDEN", "use a specific claim ceiling instead"))
    if meta.document_type == "mode_b_card":
        issues.extend(_validate_exact_locus(meta.exact_locus))
        section_numbers: list[int] = []
        for block in model.blocks:
            if block.kind != "heading" or block.data["level"] != 2:
                continue
            match = _MODEB_HEADING.match(block.data["text"])
            if match:
                section_numbers.append(int(match.group(1)))
        if section_numbers != list(range(1, 49)):
            issues.append(ValidationIssue("MODEB_SECTIONS_1_48_REQUIRED", f"observed={section_numbers}"))
        h1s = [block.data["text"] for block in model.blocks if block.kind == "heading" and block.data["level"] == 1]
        if len(h1s) != 1:
            issues.append(ValidationIssue("MODEB_SINGLE_H1_REQUIRED", f"observed={len(h1s)}"))
        elif meta.exact_locus and meta.exact_locus.display not in h1s[0]:
            issues.append(ValidationIssue("MODEB_H1_EXACT_LOCUS_REQUIRED", meta.exact_locus.display))
    for block in model.blocks:
        if block.kind == "callout" and block.data["type"] not in CALLOUT_TYPES:
            issues.append(ValidationIssue("CALLOUT_TYPE_INVALID", block.data["type"], block.data.get("source_line")))
        if block.kind == "table":
            layout = block.data["layout"]
            if layout not in TABLE_LAYOUTS:
                issues.append(ValidationIssue("TABLE_LAYOUT_INVALID", layout))
            widths = block.data.get("widths") or []
            columns = len(block.data["rows"][0])
            if widths and len(widths) != columns:
                issues.append(ValidationIssue("TABLE_WIDTH_COUNT_MISMATCH", f"{len(widths)} widths for {columns} columns"))
            if columns > 6 and layout not in {"landscape", "companion"}:
                issues.append(ValidationIssue("WIDE_TABLE_LAYOUT_REQUIRED", f"{columns} columns require landscape or companion"))
        if block.kind == "figure":
            if block.data["layout"] not in FIGURE_LAYOUTS:
                issues.append(ValidationIssue("FIGURE_LAYOUT_INVALID", block.data["layout"]))
            src = Path(block.data["src"])
            if src.is_absolute() or ".." in src.parts:
                issues.append(ValidationIssue("FIGURE_PATH_MUST_BE_PORTABLE_RELATIVE", block.data["src"]))
            if not block.data["alt"]:
                issues.append(ValidationIssue("FIGURE_ALT_REQUIRED", block.data["id"]))
            if require_assets and model.source_path != "<memory>":
                base = Path(model.source_path).resolve().parent
                target = (base / src).resolve()
                if not target.is_relative_to(base) or not target.is_file():
                    issues.append(ValidationIssue("FIGURE_ASSET_MISSING", block.data["src"]))
    return ValidationResult(issues, warnings)


def validate_path(path: str | Path, *, require_assets: bool = True) -> ValidationResult:
    try:
        model = parse_path(path)
    except SapoteMarkdownError as exc:
        return ValidationResult([ValidationIssue("PARSE_FAILED", str(exc))], [])
    return validate_model(model, require_assets=require_assets)


def block_counts(model: DocumentModel) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in model.blocks:
        counts[block.kind] = counts.get(block.kind, 0) + 1
    return counts


def iter_modeb_sections(model: DocumentModel) -> Iterable[tuple[int, str]]:
    for block in model.blocks:
        if block.kind == "heading" and block.data["level"] == 2:
            match = _MODEB_HEADING.match(block.data["text"])
            if match:
                yield int(match.group(1)), match.group(2)
