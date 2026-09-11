#!/usr/bin/env python3
"""Render/check assistant bootstrap docs from bootstrap_contract.yml.

Shared blocks belong to the contract; AGENTS.md owns operating prose. The discovery
alias is generated from the complete canonical document, never edited independently.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit
from _wbio import atomic_write_text

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "bootstrap_contract.yml"


def _load_yaml(path: Path) -> dict:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Bootstrap contract must be a mapping")
    return data


def _read_versions(root: Path) -> dict[str, str]:
    import tomllib
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    stamp = (root / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    build = re.search(r"(?m)^build=(\S+)", stamp)
    if not build:
        raise ValueError("Build stamp is missing")
    return {"bundle": data["tool"]["sapote"]["bundle_version"],
            "engine": data["project"]["version"], "build": build.group(1)}


def _path(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"Invalid bootstrap path: {rel!r}")
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or not (root / path).resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Bootstrap path escapes bundle: {rel!r}")
    return root / path


def _active_gotchas(contract: dict) -> list[dict]:
    return [g for g in contract.get("known_gotchas", []) if g.get("status") == "active"]


def render_initiation_prompt(contract: dict, versions: dict[str, str]) -> str:
    gotchas = [g["initiation_text"] for g in _active_gotchas(contract) if g.get("show_in_initiation")]
    workflow = contract["workflow"]["display_lines"]
    return "\n".join([
        contract["read_proof"]["sentence"], "",
        "◆ SAPOTE–MAMEY · SHARED ASSISTANT CONTRACT",
        f"   instruction file : {contract['challenge_response']['canonical_instruction_file']}",
        f"   bundle / engine  : v{versions['bundle']} / {versions['engine']} · build {versions['build']}",
        "   known gotcha (this build) : " + "; ".join(gotchas),
        "   workflow         : " + " ".join(workflow),
    ])


def render_known_gotchas_section(contract: dict, versions: dict[str, str]) -> str:
    out = [f"## 3 · Known gotchas for THIS build (v{versions['bundle']} / {versions['engine']} · {versions['build']})",
           "", "Generated from `bootstrap_contract.yml`; update with `python tools/render_bootstrap_contract.py --apply`.", ""]
    for g in _active_gotchas(contract):
        out.append(f"- **{g['id']}** ({g['severity']}; {g['applies_to']}): {g['detail']}")
    return "\n".join(out) + "\n"


def render_surface_table(contract: dict) -> str:
    out = ["## Bootstrap surface contract", "",
           "Two audiences: `README.md` for people; `AGENTS.md` is the canonical portable contract intended for every coding assistant.",
           "Automatic instruction-file discovery varies by product. `CLAUDE.md` is a byte-identical Claude discovery copy; other assistants must be directed to `AGENTS.md` or receive it through their supported instruction mechanism.", "",
           "| Path | Role | Required | Scanner authority | Purpose |",
           "|---|---|---|---|---|"]
    for s in contract["bootstrap_surfaces"]:
        out.append(f"| `{s['path']}` | {s['role']} | {'yes' if s['required'] else 'no'} | "
                   f"{'yes' if s['scanner_authority'] else 'no'} | {s['purpose']} |")
    return "\n".join(out) + "\n"


def render_bootstrap_audit(contract: dict, versions: dict[str, str]) -> str:
    return ("# Bootstrap file audit — generated from bootstrap_contract.yml\n\n"
            f"Bundle / engine / build: v{versions['bundle']} / {versions['engine']} · {versions['build']}\n\n"
            + render_surface_table(contract))


def _replace_marker(text: str, marker: str, content: str) -> str:
    begin = f"<!-- BEGIN GENERATED: {marker} from bootstrap_contract.yml -->"
    end = f"<!-- END GENERATED: {marker} from bootstrap_contract.yml -->"
    pattern = re.compile(re.escape(begin) + r"\n[\s\S]*?" + re.escape(end))
    if len(pattern.findall(text)) != 1:
        raise ValueError(f"Expected exactly one generated block: {marker}")
    return pattern.sub(lambda _: begin + "\n" + content.rstrip() + "\n" + end, text)


def _expected(root: Path) -> tuple[dict, dict[str, str]]:
    contract = _load_yaml(root / "bootstrap_contract.yml")
    versions = _read_versions(root)
    rendered = {
        "initiation_prompt": "```text\n" + render_initiation_prompt(contract, versions) + "\n```",
        "known_gotchas_section": render_known_gotchas_section(contract, versions),
        "bootstrap_surface_map": render_surface_table(contract),
        "bootstrap_audit_report": render_bootstrap_audit(contract, versions),
    }
    outputs: dict[str, str] = {}
    specs = contract["generated_markdown"]
    for key, spec in specs.items():
        if "source" in spec:
            continue
        rel = spec["target"]
        path = _path(root, rel)
        content = rendered[key]
        if spec["replacement_marker"] == "full_file":
            outputs[rel] = content
        else:
            current = outputs[rel] if rel in outputs else path.read_text(encoding="utf-8")
            outputs[rel] = _replace_marker(current, spec["replacement_marker"], content)
    # Mirrors use the fully rendered canonical source, independent of YAML entry order.
    for spec in specs.values():
        if "source" not in spec:
            continue
        rel, source = spec["target"], spec["source"]
        _path(root, rel)
        path = _path(root, source)
        outputs[rel] = outputs[source] if source in outputs else path.read_text(encoding="utf-8")
    return contract, outputs


def apply(root: Path = ROOT) -> list[Path]:
    _, outputs = _expected(root)
    changed = []
    for rel, text in outputs.items():
        path = _path(root, rel)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, text)
            changed.append(path)
    return changed


def check(root: Path = ROOT) -> list[str]:
    try:
        contract, outputs = _expected(root)
        errors = []
        for surface in contract["bootstrap_surfaces"]:
            if surface.get("required") and not _path(root, surface["path"]).is_file():
                errors.append(f"{surface['path']}: missing required bootstrap surface")
        for rel, text in outputs.items():
            path = _path(root, rel)
            if not path.is_file():
                errors.append(f"{rel}: missing generated output")
            elif path.read_text(encoding="utf-8") != text:
                errors.append(f"{rel}: generated content is stale or divergent")
        return errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [str(exc)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--print", choices=["initiation_prompt", "known_gotchas_section", "bootstrap_surface_map", "audit"])
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.apply:
        for path in apply(root):
            emit(f"updated {path.relative_to(root)}")
        return 0
    if args.check:
        errors = check(root)
        emit(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors,
                         "contract_sha256": hashlib.sha256((root / "bootstrap_contract.yml").read_bytes()).hexdigest()}, indent=2))
        return int(bool(errors))
    contract = _load_yaml(root / "bootstrap_contract.yml")
    versions = _read_versions(root)
    renderers = {"initiation_prompt": lambda: render_initiation_prompt(contract, versions),
                 "known_gotchas_section": lambda: render_known_gotchas_section(contract, versions),
                 "bootstrap_surface_map": lambda: render_surface_table(contract),
                 "audit": lambda: render_bootstrap_audit(contract, versions)}
    emit(renderers[args.print]())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
