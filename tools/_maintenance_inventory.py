"""Build deterministic maintenance navigation from explicit owners and scoped rosters.

This helper reads declarations and files. It never probes optional installations,
runs an owning generator, imports a scientific pipeline, or retires evidence.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit


POLICY = "docs/maintenance_inventory.policy.json"
JSON_OUT = "docs/MAINTENANCE_INVENTORY.generated.json"
MD_OUT = "docs/MAINTENANCE_INVENTORY.generated.md"
OUTPUTS = (JSON_OUT, MD_OUT)


def checked_path(root: Path, relative: str, *, missing=False) -> Path:
    """Admit only a normalized file inside this root, without symlink traversal."""
    rel = PurePosixPath(relative)
    if (not relative or rel.is_absolute() or ".." in rel.parts
            or rel.as_posix() != relative or "\\" in relative):
        raise ValueError(f"unsafe maintenance path: {relative!r}")
    path = root.joinpath(*rel.parts)
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
        raise ValueError(f"symlink maintenance path: {relative}")
    if not path.is_file() and not (missing and not path.exists()):
        raise ValueError(f"missing maintenance input: {relative}")
    return path


def file_binding(root: Path, relative: str) -> dict:
    data = checked_path(root, relative).read_bytes()
    return {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def literal_assignment(root: Path, relative: str, name: str):
    """Read a literal declaration without executing its owner."""
    tree = ast.parse(checked_path(root, relative).read_text(encoding="utf-8"))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    if len(values) != 1:
        raise ValueError(f"expected one literal {name} in {relative}")
    return ast.literal_eval(values[0])


def documentation_paths(root: Path) -> list[str]:
    """Root Markdown plus docs/ and wiki/ Markdown; other packaging trees excluded."""
    paths = set(root.glob("*.md"))
    for directory in ("docs", "wiki"):
        base = root / directory
        if base.is_symlink():
            raise ValueError(f"symlink documentation directory: {directory}")
        paths.update(base.rglob("*.md"))
    names = {path.relative_to(root).as_posix() for path in paths}
    names.add(MD_OUT)  # Declared before creation: generation has a fixed point.
    for name in names:
        checked_path(root, name, missing=name == MD_OUT)
    return sorted(names)


def linked_docs(root: Path, names: set[str]) -> set[str]:
    """Current navigation membership; links do not prove semantic currentness."""
    text = checked_path(root, "CURRENT_DOCS_INDEX.md").read_text(encoding="utf-8")
    paths = {"CURRENT_DOCS_INDEX.md"}
    for target in re.findall(r"\]\(\s*<?([^\s)>]+)>?(?:\s+[^)]*)?\)", text):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        name = posixpath.normpath(unquote(parsed.path))
        if name in names:
            paths.add(name)
    return paths


def build_inventory(root: Path, commands: list[dict], tool_paths: list[str], companions: list) -> dict:
    """Join parser/catalog rows with declarations; caller binds the owning parser."""
    root = root.resolve()
    policy = json.loads(checked_path(root, POLICY).read_text(encoding="utf-8"))
    if policy.get("schema") != "sapote-mamey.maintenance-policy.v1":
        raise ValueError("unsupported maintenance policy schema")
    surfaces = literal_assignment(root, "tools/generated_surface_ownership.py", "SURFACES")
    mirrors = literal_assignment(root, "tools/sync_wiki_mirrors.py", "MIRRORS")
    generated = []
    for key, value in surfaces.items():
        generated.append({"id": key, "outputs": list(value["outputs"]),
                          "owner_paths": list(value["owner_paths"]), "regeneration_rule": value["owner"],
                          "check_rule": value["validator"], "trigger": value["trigger"],
                          "scope": "existing-phase-planner-contract"})
    generated.extend(policy["generated_surfaces"])
    for output, source in sorted(mirrors.items()):
        generated.append({"id": "wiki:" + output, "outputs": [output],
                          "owner_paths": ["tools/sync_wiki_mirrors.py", source],
                          "regeneration_rule": "python tools/sync_wiki_mirrors.py --apply",
                          "check_rule": "python tools/sync_wiki_mirrors.py --check",
                          "trigger": "maintained mirror source changes", "scope": "complete-mirror"})
    records, output_owners, input_names = [], {}, {POLICY, "CURRENT_DOCS_INDEX.md", "mamey/cli.py",
        "tools/gen_tools_inventory.py", "tools/_maintenance_inventory.py", "tools/gen_command_catalog.py",
        "tools/generated_surface_ownership.py", "tools/sync_wiki_mirrors.py",
        "mamey/companion_tools.py", "mamey/data/companion_tools.json"}

    def add(kind, identifier, lifecycle, owners, rule, **fields):
        if not owners or not rule.strip():
            raise ValueError(f"missing owner or regeneration rule: {identifier}")
        for owner in owners:
            checked_path(root, owner)
        records.append(dict(id=kind + ":" + identifier, kind=kind, lifecycle=lifecycle,
                            owner_paths=owners, regeneration_rule=rule, **fields))

    for surface in generated:
        owners = surface["owner_paths"]
        input_names.update(owners)
        for output in surface["outputs"]:
            checked_path(root, output, missing=output in OUTPUTS)
            if output in output_owners:
                raise ValueError(f"conflicting generated owners: {output}")
            output_owners[output] = surface["id"]
        add("generated", surface["id"], "OWNER_DECLARED", owners,
            surface["regeneration_rule"], outputs=surface["outputs"], check_rule=surface["check_rule"],
            trigger=surface["trigger"], scope=surface["scope"])

    for command in commands:
        optional = command["requirement"] == "optional-addon"
        owners = ["mamey/cli.py", "tools/gen_command_catalog.py"]
        if optional:
            owners += policy["optional_commands"][command["name"]]["owner_paths"]
        add("command", command["name"], "OPTIONAL_DECLARED" if optional else "PARSER_DECLARED", owners,
            "Edit the parser/catalog owner, then regenerate command and maintenance catalogs; preserve aliases.",
            name=command["name"], aliases=command["aliases"], group=command["group"],
            description=command["help"], requirement=command["requirement"], availability="NOT_PROBED")
        input_names.update(owners)

    if len(tool_paths) != len(set(tool_paths)):
        raise ValueError("duplicate discovered tool path")
    for name in sorted(tool_paths):
        add("tool", name, "SOURCE_DISCOVERED_REVIEW_HOLD", [name],
            "Edit this source; regenerate tools and maintenance inventories. Discovery does not establish a supported entry point.",
            source=file_binding(root, name))

    for tool in companions:
        add("companion", tool.id, "REGISTRY_DECLARED", ["mamey/data/companion_tools.json", "mamey/companion_tools.py"],
            "Edit and validate the canonical companion registry; regenerate maintenance navigation. Provisioning is a separate explicit action.",
            name=tool.name, requirement=tool.requirement, availability="NOT_PROBED")

    for hook in policy["optional_hooks"]:
        add("optional-hook", hook, "OPTIONAL_DECLARED", [hook, "docs/OPTIONAL_HOOKS.md"],
            "Edit this source and its optional-hook guide. Explicit installation is separate; shipping does not activate it.",
            availability="NOT_PROBED", source=file_binding(root, hook))

    names = documentation_paths(root)
    current = linked_docs(root, set(names))
    for name in names:
        if name in output_owners:
            lifecycle = "GENERATED_OR_MANAGED_SURFACE"
        elif name in policy["retained_history"] or any(name.startswith(prefix) for prefix in policy["history_prefixes"]):
            lifecycle = "RETAINED_HISTORY"
        elif any(name.startswith(prefix) for prefix in policy["engineering_prefixes"]):
            lifecycle = "ENGINEERING_RECORD"
        elif name in policy["optional_documents"]:
            lifecycle = "OPTIONAL_GUIDE"
        elif name in current:
            lifecycle = "CURRENT_NAVIGATION_DECLARED"
        else:
            lifecycle = "UNCLASSIFIED_REVIEW_HOLD"
        fields = {"path": name, "linked_from_current_index": name in current}
        if name in output_owners:
            fields["generated_owner_id"] = "generated:" + output_owners[name]
            rule = "Use the linked generated owner; edit only its maintained inputs or explicitly maintained prose."
        else:
            fields["source"] = file_binding(root, name)
            rule = ("Retain in place; preserve links. Changes or migration need review. No automatic retirement."
                    if lifecycle in {"RETAINED_HISTORY", "ENGINEERING_RECORD"}
                    else "Edit this maintained document; regenerate maintenance navigation. Semantic currentness needs content review.")
        add("document", name, lifecycle, [name] if name not in OUTPUTS else ["tools/gen_tools_inventory.py"], rule, **fields)

    for name in policy["retained_history"] + policy["optional_documents"]:
        checked_path(root, name)
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate maintenance record id")
    # Generated bytes are bound by their own checks and final source checksums.
    # Exclude them here to prevent self/manifest/managed-prose checksum cycles.
    inputs = [file_binding(root, name) for name in sorted(input_names - set(output_owners))]
    return {"schema": "sapote-mamey.maintenance-inventory.v1", "status": "ROSTERED_WITH_EXPLICIT_REVIEW_HOLDS",
            "scope": {"documents": "root *.md plus docs/**/*.md and wiki/**/*.md",
                      "tools": "existing tools inventory discovery plus bootstrap.sh",
                      "commands": "owning canonical parser plus fixed optional catalog rows",
                      "availability": "NOT_PROBED", "semantic_currentness": "NOT_INFERRED_FROM_NAVIGATION_OR_VERSION",
                      "generated_hashes": "OWNING_CHECKS_AND_FINAL_SOURCE_CHECKSUMS"},
            "inputs": inputs, "counts": dict(sorted(Counter(record["kind"] for record in records).items())),
            "document_lifecycles": dict(sorted(Counter(record["lifecycle"] for record in records if record["kind"] == "document").items())),
            "records": sorted(records, key=lambda record: record["id"])}


def _link(path: str) -> str:
    return posixpath.relpath(path, "docs").replace(" ", "%20")


def render_navigation(payload: dict) -> str:
    """Compact navigation from the same machine records; no parallel catalog prose."""
    lines = ["# Maintenance inventory (generated)", "",
             "Generated by `python tools/gen_tools_inventory.py --maintenance`; verify both files with `--maintenance --check`.", "",
             "[Machine-readable records](MAINTENANCE_INVENTORY.generated.json) contain every scoped row, source owner and regeneration rule. "
             "[Catalog maintenance](CATALOG_MAINTENANCE.md) explains owner checks and write boundaries. "
             "Navigation membership and file/version names do not establish semantic currentness or capability acceptance. "
             "Optional installations are not probed; retained history stays in place.", "",
             "| Scope | Records |", "|---|---:|"]
    lines += [f"| {kind} | {count} |" for kind, count in payload["counts"].items()]
    lines += ["", "| Document lifecycle | Records |", "|---|---:|"]
    lines += [f"| {kind} | {count} |" for kind, count in payload["document_lifecycles"].items()]
    lines += ["", "## Generated owners", "", "| Surface | Regeneration | Check |", "|---|---|---|"]
    for record in payload["records"]:
        if record["kind"] == "generated":
            escape = lambda text: text.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {escape(record['id'].removeprefix('generated:'))} | `{escape(record['regeneration_rule'])}` | `{escape(record['check_rule'])}` |")
    lines += ["", "## Declared current navigation", "",
              "Generated surfaces, optional guides and retained records keep their own lifecycle even when linked from the current index.", ""]
    for record in payload["records"]:
        if record["kind"] == "document" and record["linked_from_current_index"]:
            path = record["path"]
            lines.append(f"- [{path}]({_link(path)}) — {record['lifecycle']}")
    lines += ["", "## Retained historical documents", "", "Preserved records; no migration or deletion is performed.", ""]
    for record in payload["records"]:
        if record["kind"] == "document" and record["lifecycle"] == "RETAINED_HISTORY":
            path = record["path"]
            lines.append(f"- [{path}]({_link(path)})")
    return "\n".join(lines) + "\n"


def maintain(root: Path, commands: list[dict], tool_paths: list[str], companions: list,
             *, check: bool, write_text) -> tuple[str, int]:
    """Validate all inputs first; each output is atomic, then check the complete pair."""
    payload = build_inventory(root, commands, tool_paths, companions)
    contents = {JSON_OUT: json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                MD_OUT: render_navigation(payload)}
    stale = [name for name, content in contents.items() if not (root / name).is_file()
             or (root / name).read_text(encoding="utf-8") != content
             or (os.name == "posix" and (root / name).stat().st_mode & 0o777 != 0o644)]
    if check:
        return (("MAINTENANCE INVENTORY STALE: " + ", ".join(stale) + "\n", 1) if stale
                else ("maintenance inventory OK — complete scoped rosters; review holds retained\n", 0))
    for name, content in contents.items():
        target = checked_path(root, name, missing=True)
        write_text(target, content)
        if os.name == "posix":
            target.chmod(0o644)  # Public bundle metadata, including first-time atomic creation.
    return "wrote maintenance inventory JSON and navigation; review holds retained\n", 0
