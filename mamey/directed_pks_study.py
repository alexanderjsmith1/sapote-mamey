"""Directed PKS Study scaffold.

This conservative scaffold validates directed PKS study specifications, enforces
claim-safety language, enforces full-20 Mode B headings, and can emit a minimal
summary from a spec alone.

It does not run BLASTP/HMMER/DIAMOND, render figures, alter scoring, or claim
product identity.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib import resources
from pathlib import Path
from typing import Any
import json
import re


REQUIRED_SPEC_KEYS = {"study_id", "strain_id", "focus", "groups", "claim_policy", "figure_policy"}

from mamey.validators.modeb_full20 import REQUIRED_MODEB_FULL20_SECTIONS


DEFAULT_FULL20_SECTIONS = list(REQUIRED_MODEB_FULL20_SECTIONS)

DEFAULT_FORBIDDEN_CLAIMS = [
    "makes desertomycin",
    "makes conglobatin",
    "makes nystatin",
    "Set A is one BGC",
    "SetA is one BGC",
]

FORBIDDEN_TERMS = {"claim_scope", "product_identity_without_evidence"}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    path: str = ""


def _data_path(name: str) -> Path:
    try:
        return Path(resources.files("mamey") / "data" / "directed_pks_study" / name)
    except Exception:
        return Path(__file__).resolve().parent / "data" / "directed_pks_study" / name


def load_rules(path: str | Path | None = None) -> dict[str, Any]:
    rules_path = Path(path) if path else _data_path("directed_pks_study_rules.json")
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    return payload.get("directed_pks_study_mode", payload)


def load_study_spec(path: str | Path) -> dict[str, Any]:
    """Load a directed PKS study spec from JSON or YAML.

    JSON is dependency-free. YAML uses PyYAML only if installed.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        obj = json.loads(text)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise RuntimeError("YAML directed PKS specs require PyYAML; use JSON spec otherwise") from exc
        obj = yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported directed PKS study spec extension: {path.suffix}")
    if not isinstance(obj, dict):
        raise ValueError("directed PKS study spec did not parse to an object")
    return obj


def _walk_values(obj: Any, path: str = "") -> list[tuple[str, Any]]:
    vals: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            vals.append((p, v))
            vals.extend(_walk_values(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            vals.extend(_walk_values(v, f"{path}[{i}]"))
    return vals


def _as_text_blob(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, sort_keys=True)
    except Exception:
        return str(obj)


def private_identifier_hits(obj: Any, rules: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return literal private strain IDs that should not ship in public scaffold data."""
    rules = rules or load_rules()
    policy = rules.get("private_identifier_policy") or {}
    # SCHEMA-P02: the old default AS-\d{3} caught only 3-digit AS ids — it MISSED the real 2-digit
    # (AS-XXX/AS-XXX) and 4-digit AS strains, and AJS-/PENDING- entirely, which are unconditionally
    # private everywhere else (cli.py release-tag logic, redact_public_tier). Broadened to the
    # canonical private prefixes: AS-\d{2,4} (matching redact_public_tier; AS-1 prose excluded),
    # plus AJS-/PENDING-\d{1,4}. The (?<![A-Za-z]) lookbehind keeps CAS-/MCAS-/LAS- and the AS-XXX
    # placeholder from matching. A rules-registry override still wins.
    pattern = policy.get("private_strain_regex") or r"(?<![A-Za-z])(?:AJS-\d{1,4}|PENDING-\d{1,4}|AS-\d{2,4})"
    hits: list[tuple[str, str]] = []
    regex = re.compile(pattern)
    for path, val in _walk_values(obj):
        if isinstance(val, str):
            for hit in regex.findall(val):
                hits.append((path, hit))
    return hits


def forbidden_claim_hits(obj: Any, rules: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    rules = rules or load_rules()
    forbidden = list(rules.get("forbidden_claims") or DEFAULT_FORBIDDEN_CLAIMS)
    hits: list[tuple[str, str]] = []
    for path, val in _walk_values(obj):
        if not isinstance(val, str):
            continue
        lower = val.lower()
        for phrase in forbidden:
            if phrase.lower() in lower:
                hits.append((path, phrase))
    return hits


def forbidden_term_hits(obj: Any, rules: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    rules = rules or load_rules()
    forbidden = set(rules.get("forbidden_terms") or FORBIDDEN_TERMS)
    hits: list[tuple[str, str]] = []
    for path, val in _walk_values(obj):
        for term in forbidden:
            if term in path:
                hits.append((path, term))
            if isinstance(val, str) and term in val:
                hits.append((path, term))
    return hits


def required_full20_sections(rules: dict[str, Any] | None = None) -> list[str]:
    rules = rules or load_rules()
    sections = list(rules.get("required_sections_full20") or DEFAULT_FULL20_SECTIONS)
    if len(sections) != 20:
        raise ValueError(f"directed PKS full20 requires exactly 20 sections; found {len(sections)}")
    return sections


def validate_full20_card_text(text: str, rules: dict[str, Any] | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sections = required_full20_sections(rules)
    for section in sections:
        if section not in text:
            issues.append(ValidationIssue("ERROR", "MISSING_FULL20_SECTION", f"missing section: {section}"))
    for path, claim in forbidden_claim_hits({"card_text": text}, rules):
        issues.append(ValidationIssue("ERROR", "FORBIDDEN_CLAIM", f"forbidden claim: {claim}", path))
    for path, term in forbidden_term_hits({"card_text": text}, rules):
        issues.append(ValidationIssue("ERROR", "FORBIDDEN_TERM", f"forbidden term: {term}", path))
    return issues


def validate_study_spec(spec: dict[str, Any], rules: dict[str, Any] | None = None, *, public_tier: bool = True) -> list[ValidationIssue]:
    rules = rules or load_rules()
    issues: list[ValidationIssue] = []

    missing = REQUIRED_SPEC_KEYS - set(spec)
    for key in sorted(missing):
        issues.append(ValidationIssue("ERROR", "MISSING_REQUIRED_KEY", f"missing required key: {key}", key))

    if public_tier:
        for path, hit in private_identifier_hits(spec, rules):
            # Allow the redacted placeholder AS-XXX, but not literal AS-###.
            if hit != "AS-XXX":
                issues.append(ValidationIssue("ERROR", "PRIVATE_STRAIN_ID_IN_PUBLIC_SPEC", f"literal private strain identifier in public scaffold: {hit}", path))

    groups = spec.get("groups")
    if not isinstance(groups, dict) or not groups:
        issues.append(ValidationIssue("ERROR", "NO_GROUPS", "directed PKS study must define at least one group", "groups"))
    else:
        for gid, group in groups.items():
            if not isinstance(group, dict):
                issues.append(ValidationIssue("ERROR", "INVALID_GROUP", f"group {gid} is not an object", f"groups.{gid}"))
                continue
            nodes = group.get("nodes")
            if not isinstance(nodes, list) or not nodes:
                issues.append(ValidationIssue("ERROR", "GROUP_WITHOUT_NODES", f"group {gid} has no nodes", f"groups.{gid}.nodes"))
            scope = str(group.get("interpretation_scope", ""))
            if not scope:
                issues.append(ValidationIssue("ERROR", "GROUP_WITHOUT_INTERPRETATION_SCOPE", f"group {gid} lacks interpretation_scope", f"groups.{gid}.interpretation_scope"))
            if re.search(r"\bphysical\s+cluster\b|\bone\s+BGC\b|\bmerged\s+cluster\b", scope, re.I):
                issues.append(ValidationIssue("ERROR", "UNSUPPORTED_PHYSICAL_LINKAGE_CLAIM", f"group {gid} claims physical linkage in scaffold mode", f"groups.{gid}.interpretation_scope"))
            if "functional_grouping" not in scope:
                issues.append(ValidationIssue("WARN", "GROUP_SCOPE_SHOULD_SAY_FUNCTIONAL_GROUPING", f"group {gid} should state functional_grouping", f"groups.{gid}.interpretation_scope"))

    focus = spec.get("focus") if isinstance(spec.get("focus"), dict) else {}
    exclusions = focus.get("exclude_bgcs") or []
    reasons = focus.get("exclude_reason") or {}
    if exclusions and not isinstance(reasons, dict):
        issues.append(ValidationIssue("ERROR", "EXCLUSION_REASON_NOT_OBJECT", "exclude_reason must map BGC IDs to reasons", "focus.exclude_reason"))
    for bgc in exclusions:
        if not isinstance(reasons, dict) or not reasons.get(bgc):
            issues.append(ValidationIssue("ERROR", "EXCLUSION_WITHOUT_REASON", f"excluded BGC lacks reason: {bgc}", f"focus.exclude_reason.{bgc}"))

    claim_policy = spec.get("claim_policy") if isinstance(spec.get("claim_policy"), dict) else {}
    if claim_policy.get("named_product_claims") is not False:
        issues.append(ValidationIssue("ERROR", "NAMED_PRODUCT_CLAIMS_NOT_DISABLED", "named_product_claims must be false", "claim_policy.named_product_claims"))
    if claim_policy.get("use_interpretation_scope") is not True:
        issues.append(ValidationIssue("ERROR", "INTERPRETATION_SCOPE_NOT_REQUIRED", "use_interpretation_scope must be true", "claim_policy.use_interpretation_scope"))

    figure_policy = spec.get("figure_policy") if isinstance(spec.get("figure_policy"), dict) else {}
    if int(figure_policy.get("quality_gate", 0) or 0) < 9:
        issues.append(ValidationIssue("ERROR", "FIGURE_GATE_TOO_LOW", "figure quality gate must be >= 9", "figure_policy.quality_gate"))
    for key in ("require_preflight", "require_self_rating"):
        if figure_policy.get(key) is not True:
            issues.append(ValidationIssue("ERROR", "FIGURE_GATE_MISSING_REQUIREMENT", f"{key} must be true", f"figure_policy.{key}"))

    for path, claim in forbidden_claim_hits(spec, rules):
        issues.append(ValidationIssue("ERROR", "FORBIDDEN_CLAIM", f"forbidden claim: {claim}", path))
    for path, term in forbidden_term_hits(spec, rules):
        issues.append(ValidationIssue("ERROR", "FORBIDDEN_TERM", f"forbidden term: {term}", path))

    return issues


def issue_dicts(issues: list[ValidationIssue]) -> list[dict[str, str]]:
    return [asdict(i) for i in issues]


def build_full20_skeleton(rules: dict[str, Any] | None = None) -> str:
    sections = required_full20_sections(rules)
    return "\n\n".join(f"## {i}. {section}\n\nPENDING_EVIDENCE." for i, section in enumerate(sections, 1)) + "\n"


def build_minimal_summary(spec: dict[str, Any], rules: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    rules = rules or load_rules()
    groups = spec.get("groups") or {}
    focus = spec.get("focus") or {}
    excluded = focus.get("exclude_bgcs") or []
    reasons = focus.get("exclude_reason") or {}
    comparators = spec.get("comparators") or []

    lines = [
        f"# Directed PKS Study Scaffold — {spec.get('study_id', 'unnamed')}",
        "",
        f"**Strain:** {spec.get('strain_id', '')}",
        f"**Title:** {spec.get('title', '')}",
        "",
        "## Claim policy",
        "",
        "- Named product claims: disabled",
        "- Required wording: `interpretation_scope`, `functional_grouping`, `comparator_context`",
        "- Comparator context must not be treated as product identity.",
        "",
        "## Groups",
        "",
    ]
    for gid, group in groups.items():
        lines.extend([
            f"### {gid}",
            "",
            f"- Label: {group.get('label', '')}",
            f"- Nodes: {', '.join(group.get('nodes', []))}",
            f"- interpretation_scope: {group.get('interpretation_scope', '')}",
            "",
        ])
    lines.extend(["## Excluded/background BGCs", ""])
    if excluded:
        for bgc in excluded:
            lines.append(f"- {bgc}: {reasons.get(bgc, 'reason required')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Comparator tracks", ""])
    if comparators:
        for comp in comparators:
            lines.append(f"- {comp.get('accession', '')}: {comp.get('label', '')} — comparator_context: {comp.get('role', '')}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Full20 Mode B skeleton",
        "",
        "The required 20-section skeleton is available from `build_full20_skeleton()`.",
        "",
    ])
    summary = "\n".join(lines)

    payload = {
        "schema_version": "directed_pks_study_scaffold_v1",
        "study_id": spec.get("study_id", ""),
        "strain_id": spec.get("strain_id", ""),
        "group_count": len(groups),
        "excluded_bgcs": excluded,
        "comparator_count": len(comparators),
        "required_full20_sections": required_full20_sections(rules),
        "interpretation_scope_required": True,
        "named_product_claims": False,
    }
    return summary, payload


def write_minimal_summary(spec: dict[str, Any], out_dir: str | Path, rules: dict[str, Any] | None = None) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md, payload = build_minimal_summary(spec, rules)
    md_path = out / "DIRECTED_PKS_STUDY_SUMMARY.md"
    json_path = out / "DIRECTED_PKS_STUDY_SUMMARY.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"markdown": str(md_path), "json": str(json_path)}
