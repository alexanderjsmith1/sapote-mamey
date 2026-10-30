"""Registry-backed Sapote-Mamey deliverables menu.

The registry is the source of truth.  Human Markdown, CLI discovery, and the
end-of-session checklist should consume the same records instead of keeping
independent hand-written menus.  Availability checks are deliberately local
and read-only; this module never contacts a network service.
"""
from __future__ import annotations
import sys

import importlib.util
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import BUNDLE_VERSION, __version__


REGISTRY_PATH = Path(__file__).with_name("data") / "deliverables_registry.json"
CANONICAL_MENU_PATH = Path(__file__).parents[1] / "docs" / "DELIVERABLE_MENU.md"
LEGACY_MENU_PATH = Path(__file__).parents[1] / "docs" / "DELIVERABLE_MENU_v97146.md"

_BGC_TOKEN = re.compile(r"\bBGC\d+\b", re.I)


class DeliverablesRegistryError(ValueError):
    """The shipped deliverables registry violates its schema or contracts."""


@dataclass(frozen=True)
class Availability:
    deliverable_id: str
    state: str
    missing: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "deliverable_id": self.deliverable_id,
            "state": self.state,
            "missing": list(self.missing),
            "notes": list(self.notes),
        }


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else REGISTRY_PATH
    data = json.loads(source.read_text(encoding="utf-8"))
    findings = validate_registry(data)
    if findings:
        raise DeliverablesRegistryError("; ".join(findings))
    return data


def validate_registry(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    required_root = {
        "schema_version", "registry_id", "title", "identity_contract",
        "global_claim_ceiling", "delivery_classes", "groups", "deliverables",
    }
    missing_root = sorted(required_root - set(data))
    if missing_root:
        findings.append(f"missing root keys: {', '.join(missing_root)}")
        return findings
    if data.get("schema_version") != 1:
        findings.append("schema_version must be 1")
    if data.get("identity_contract") != "strain / full node-or-contig / region / BGC alias":
        findings.append("identity_contract is not the permanent four-part display contract")

    groups = data.get("groups")
    items = data.get("deliverables")
    if not isinstance(groups, list) or not groups:
        findings.append("groups must be a non-empty list")
        return findings
    if not isinstance(items, list) or not items:
        findings.append("deliverables must be a non-empty list")
        return findings

    group_ids = [row.get("id") for row in groups if isinstance(row, dict)]
    if len(group_ids) != len(set(group_ids)):
        findings.append("group ids are not unique")
    allowed_classes = set(data.get("delivery_classes", {}))
    seen_ids: set[str] = set()
    seen_labels: set[str] = set()
    lookup_tokens: dict[str, str] = {}
    required_item = {
        "id", "label", "group", "name", "question", "summary",
        "delivery_class", "commands", "requirements", "optional_inputs",
        "outputs", "gates", "triggers", "claim_ceiling",
    }
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            findings.append(f"deliverable row {index} is not an object")
            continue
        missing = sorted(required_item - set(item))
        item_id = str(item.get("id", f"row-{index}"))
        if missing:
            findings.append(f"{item_id}: missing keys {', '.join(missing)}")
            continue
        if item_id in seen_ids:
            findings.append(f"duplicate deliverable id: {item_id}")
        seen_ids.add(item_id)
        label = str(item["label"])
        if label in seen_labels:
            findings.append(f"duplicate menu label: {label}")
        seen_labels.add(label)
        if item["group"] not in group_ids:
            findings.append(f"{item_id}: unknown group {item['group']}")
        if item["delivery_class"] not in allowed_classes:
            findings.append(f"{item_id}: unknown delivery_class {item['delivery_class']}")
        for key in ("commands", "requirements", "optional_inputs", "outputs", "gates", "triggers"):
            if not isinstance(item[key], list) or any(not isinstance(v, str) for v in item[key]):
                findings.append(f"{item_id}: {key} must be a list of strings")
        if "detection_globs" in item and (
            not isinstance(item["detection_globs"], list)
            or any(not isinstance(v, str) for v in item["detection_globs"])
        ):
            findings.append(f"{item_id}: detection_globs must be a list of strings")
        if not item["outputs"]:
            findings.append(f"{item_id}: outputs may not be empty")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(v, str) or not v.strip() for v in aliases):
            findings.append(f"{item_id}: aliases must be a list of non-empty strings")
            aliases = []
        for token in [item_id, label, str(item["name"]), *aliases]:
            folded = token.casefold()
            if folded in lookup_tokens and lookup_tokens[folded] != item_id:
                findings.append(f"{item_id}: ambiguous lookup token {token}")
            lookup_tokens[folded] = item_id
        for trigger in item["triggers"]:
            if _BGC_TOKEN.search(trigger) and trigger.count(" / ") < 3:
                findings.append(f"{item_id}: incomplete exact-locus trigger: {trigger}")
    return findings


def _csv(values: Iterable[str]) -> str:
    values = list(values)
    return ", ".join(f"`{value}`" for value in values) if values else "None"


def render_menu(registry: dict[str, Any] | None = None) -> str:
    registry = registry or load_registry()
    kinds = {
        "DETERMINISTIC_BUILT_IN": "Built-in output",
        "OPTIONAL_LOCAL_ADAPTER": "Needs optional local tools or data",
        "POST_SEAL_JUDGMENT": "Requires interpretation and writing",
        "OPTIONAL_EXTERNAL_WORKFLOW": "Uses an external service",
        "GOVERNANCE_AND_QA": "Checks and records",
        "HUMAN_REVIEW_PROTOCOL": "Requires a reviewer",
    }
    groups = {
        "counter": "Explore a strain", "evidence": "Inspect evidence",
        "meals": "Build an interpretation", "sides": "Add focused comparisons",
        "governance": "Check and share work",
    }
    def labels(values: Iterable[str]) -> str:
        return ", ".join(value.replace("handoff_bundle", "transfer ZIP").replace("_", " ") for value in values) or "None"
    lines = [
        "# Choose an output", "",
        "Find the result you need below. Each entry lists its inputs and whether it "
        "needs extra tools, an external service or a written interpretation.", "",
        "For the complete requirements and command names of the first entry, run "
        "from the bundle directory:", "", "```bash",
        "python mamey_run.py deliverables explain '#1'", "```", "",
        "Replace the example path with your antiSMASH ZIP, then check it for that entry:", "", "```bash",
        "python mamey_run.py deliverables availability '#1' --input-zip ~/Downloads/EXAMPLE.zip",
        "```", "",
        "Availability checks local files and tools; each output still needs its own "
        "input checks. Use another entry's label to inspect its requirements.", "",
        "For a single locus, supply its complete identity: "
        f"`{registry['identity_contract']}`.", "",
    ]
    by_group: dict[str, list[dict[str, Any]]] = {}
    for item in registry["deliverables"]:
        by_group.setdefault(item["group"], []).append(item)
    for group in registry["groups"]:
        lines.extend([f"## {groups.get(group['id'], group['title'])}", ""])
        for item in by_group.get(group["id"], []):
            lines.extend([
                f"### {item['label']} — {item.get('reader_name', item['name'])}", "",
                item.get("reader_summary", item["summary"]), "",
                f"- **You need:** {labels(item['requirements'])}.",
                f"- **You get:** {labels(item['outputs'])}.",
                f"- **Work involved:** {kinds.get(item['delivery_class'], item['delivery_class'])}.",
                "",
            ])
    lines.extend([
        "---", "",
        f"Sapote-Mamey v{BUNDLE_VERSION}; engine {__version__}. "
        "Generated from `mamey/data/deliverables_registry.json` by "
        "`tools/generate_deliverables_menu.py`.", "",
    ])
    return "\n".join(lines)


def render_legacy_pointer() -> str:
    return "\n".join([
        "# Sapote-Mamey Deliverable Menu — compatibility pointer",
        "",
        "Choose the output you need in the [current deliverable menu](DELIVERABLE_MENU.md). "
        "This older address remains available for existing links.",
        "",
        f"Current bundle: Sapote-Mamey v{BUNDLE_VERSION}; engine: Mamey {__version__}.",
        "",
        "Menu #5 distinguishes default full48, opt-in current50_v2 and source-bound expanded-locus "
        "work orders. Emitted templates are scaffolds, not finished authored cards.",
        "",
        "Do not add new offerings here. Add them to "
        "`mamey/data/deliverables_registry.json` and regenerate the menu.",
        "",
    ])


def _has_package(path: str | None) -> bool:
    return bool(path and (Path(path) / "manifest.json").is_file())


def _count_packages(path: str | None, limit: int = 2) -> int:
    if not path or not Path(path).is_dir():
        return 0
    count = 0
    for manifest in Path(path).glob("*/package/manifest.json"):
        if manifest.is_file():
            count += 1
            if count >= limit:
                break
    return count


def _complete_locus(value: str | None) -> bool:
    return bool(value and value.count(" / ") == 3 and _BGC_TOKEN.search(value))


def _requirement_available(requirement: str, *, package: str | None, runs_dir: str | None,
                           input_zip: str | None, locus: str | None) -> bool | None:
    if requirement == "antismash_zip":
        return bool(input_zip and Path(input_zip).is_file())
    if requirement == "sealed_package":
        return _has_package(package)
    if requirement == "multiple_sealed_packages":
        return _count_packages(runs_dir) >= 2
    if requirement == "exact_locus_identity":
        return _complete_locus(locus)
    if requirement == "gecco_local":
        return shutil.which("gecco") is not None
    if requirement == "biopython":
        return importlib.util.find_spec("Bio") is not None
    if requirement == "figure_stack":
        return importlib.util.find_spec("matplotlib") is not None
    if requirement == "local_literature_corpus":
        corpus = Path(__file__).with_name("data") / "literature" / "_corpus" / "literature_corpus.jsonl"
        return corpus.is_file()
    if requirement == "phylogenomics_local":
        has_tree = shutil.which("GToTree") is not None
        has_iqtree = shutil.which("iqtree3") is not None or shutil.which("iqtree") is not None
        return has_tree and has_iqtree
    # These are governed, user-supplied, or scientific states that cannot be
    # inferred safely from a generic path scan.
    return None


def availability_for(item: dict[str, Any], *, package: str | None = None,
                     runs_dir: str | None = None, input_zip: str | None = None,
                     locus: str | None = None) -> Availability:
    missing: list[str] = []
    declared: list[str] = []
    for requirement in item["requirements"]:
        present = _requirement_available(
            requirement, package=package, runs_dir=runs_dir, input_zip=input_zip, locus=locus,
        )
        if present is False:
            missing.append(requirement)
        elif present is None:
            declared.append(requirement)
    delivery_class = item["delivery_class"]
    if missing:
        state = "INPUT_OR_LOCAL_DEPENDENCY_REQUIRED"
    elif delivery_class == "POST_SEAL_JUDGMENT":
        state = "JUDGMENT_REQUIRED"
    elif delivery_class == "OPTIONAL_EXTERNAL_WORKFLOW":
        state = "EXTERNAL_CONTACT_AUTHORIZATION_REQUIRED"
    elif delivery_class == "HUMAN_REVIEW_PROTOCOL":
        state = "HUMAN_REVIEW_REQUIRED"
    elif declared:
        state = "DECLARED_INPUT_REVIEW_REQUIRED"
    else:
        state = "READY"
    notes = tuple(f"not inferred automatically: {name}" for name in declared)
    return Availability(item["id"], state, tuple(missing), notes)


def _find_item(registry: dict[str, Any], token: str) -> dict[str, Any]:
    folded = token.casefold()
    for item in registry["deliverables"]:
        tokens = [item["id"], item["label"], item["name"], *item.get("aliases", [])]
        if folded in {value.casefold() for value in tokens}:
            return item
    raise DeliverablesRegistryError(f"unknown deliverable: {token}")


def _print_table(rows: list[dict[str, Any]]) -> None:
    widths = {
        key: max(len(key), *(len(str(row[key])) for row in rows))
        for key in ("id", "label", "class", "name")
    }
    sys.stdout.write(str("  ".join(key.upper().ljust(widths[key]) for key in widths)) + "\n")
    for row in rows:
        sys.stdout.write(str("  ".join(str(row[key]).ljust(widths[key]) for key in widths)) + "\n")


def deliverables_command(args: Any) -> int:
    registry = load_registry()
    action = args.deliverables_action
    if action == "list":
        rows = [{
            "id": item["id"], "label": item["label"],
            "class": item["delivery_class"], "name": item["name"],
        } for item in registry["deliverables"]]
        if args.json:
            sys.stdout.write(str(json.dumps(rows, indent=2)) + "\n")
        else:
            _print_table(rows)
        return 0
    if action == "explain":
        item = _find_item(registry, args.item)
        sys.stdout.write(str(json.dumps(item, indent=2) if args.json else render_item_text(item)) + "\n")
        return 0
    if action == "availability":
        items = registry["deliverables"]
        if args.item:
            items = [_find_item(registry, args.item)]
        rows = [availability_for(
            item, package=args.package, runs_dir=args.runs_dir,
            input_zip=args.input_zip, locus=args.locus,
        ).as_dict() for item in items]
        if args.json:
            sys.stdout.write(str(json.dumps(rows, indent=2)) + "\n")
        else:
            for row in rows:
                detail = ", ".join(row["missing"] + row["notes"])
                sys.stdout.write(str(f"{row['deliverable_id']}: {row['state']}" + (f" — {detail}" if detail else "")) + "\n")
        return 0
    if action == "render":
        content = render_menu(registry)
        if args.out:
            Path(args.out).write_text(content, encoding="utf-8")
            sys.stdout.write(str(args.out) + "\n")
        else:
            sys.stdout.write(str(content) + "\n")  # v9.7.409 A3: was str(content, end="") -> TypeError
        return 0
    raise DeliverablesRegistryError(f"unsupported action: {action}")


def render_item_text(item: dict[str, Any]) -> str:
    return "\n".join([
        f"{item['label']} — {item['name']} ({item['id']})",
        item["summary"],
        f"Delivery class: {item['delivery_class']}",
        f"Commands: {', '.join(item['commands']) or 'None'}",
        f"Required inputs: {', '.join(item['requirements'])}",
        f"Outputs: {', '.join(item['outputs'])}",
        f"Gates: {', '.join(item['gates'])}",
        f"Claim ceiling: {item['claim_ceiling']}",
    ])


def add_deliverables_arguments(parser: Any) -> None:
    actions = parser.add_subparsers(dest="deliverables_action", required=True)
    listing = actions.add_parser("list", help="List registered user-facing outcomes")
    listing.add_argument("--json", action="store_true")
    explain = actions.add_parser("explain", help="Explain one deliverable by id, label, or name")
    explain.add_argument("item")
    explain.add_argument("--json", action="store_true")
    available = actions.add_parser("availability", help="Read-only local input/dependency preflight")
    available.add_argument("item", nargs="?", default=None)
    available.add_argument("--package", default=None)
    available.add_argument("--runs-dir", default=None, dest="runs_dir")
    available.add_argument("--input-zip", default=None, dest="input_zip")
    available.add_argument("--locus", default=None,
                           help="complete identity: strain / full node-or-contig / region / BGC alias")
    available.add_argument("--json", action="store_true")
    render = actions.add_parser("render", help="Render the current Markdown menu")
    render.add_argument("--out", default=None)
