#!/usr/bin/env python3
"""Render/check assistant bootstrap docs from bootstrap_contract.yml.

This tool keeps the ChatGPT bootstrap contract from drifting across hand-edited
Markdown surfaces. Version/build values are read from pyproject.toml and
BUILD_STAMP.txt; bootstrap semantics and gotchas are read from
bootstrap_contract.yml.

Usage:
  python tools/render_bootstrap_contract.py --check
  python tools/render_bootstrap_contract.py --apply
  python tools/render_bootstrap_contract.py --print initiation_prompt
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wbio import atomic_write_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "bootstrap_contract.yml"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "PyYAML is required for tools/render_bootstrap_contract.py. "
            "Install dev tooling with `pip install pyyaml`, or vendor a stdlib parser "
            "before wiring this into release CI."
        ) from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected mapping at top level")
    return data


def _read_versions(root: Path) -> dict[str, str]:
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    stamp = (root / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    engine = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', pyproject)
    bundle = re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', pyproject)
    build = re.search(r'(?m)^build=(\S+)', stamp)
    if not engine or not bundle or not build:
        raise SystemExit("Could not read engine/bundle/build from pyproject.toml + BUILD_STAMP.txt")
    return {"engine": engine.group(1), "bundle": bundle.group(1), "build": build.group(1)}


def _active_gotchas(contract: dict) -> list[dict]:
    return [g for g in contract.get("known_gotchas", []) if g.get("status") == "active"]


def _headline_gotcha_lines(contract: dict) -> list[str]:
    lines = [g.get("initiation_text", "").strip() for g in _active_gotchas(contract) if g.get("show_in_initiation")]
    return [x for x in lines if x]


def render_initiation_prompt(contract: dict, versions: dict[str, str]) -> str:
    read_proof = contract["read_proof"]["sentence"]
    workflow_lines = contract["workflow"]["display_lines"]
    gotchas = _headline_gotcha_lines(contract) or ["see §3 Known gotchas"]
    gotcha_block = f"   known gotcha (this build) : {gotchas[0]}"
    for line in gotchas[1:]:
        gotcha_block += ";\n                               " + line
    return "\n".join([
        read_proof,
        "",
        "◆ SAPOTE–MAMEY · CHATGPT MODE ACTIVE",
        "   instruction file : CHATGPT_START_HERE.md  ✓ loaded",
        f"   bundle / engine  : v{versions['bundle']} / {versions['engine']} · build {versions['build']}",
        gotcha_block,
        f"   workflow         : {workflow_lines[0]}",
        f"                      {workflow_lines[1]}",
        "   ◆ next paths (pick one by number — exactly 8):",
        "     1. <standing path: if any BGC is un-analysed → \"Continue deeper Mode B:",
        "        run next batch (BGC[list]) to full §1–§30\"; else the highest-value deeper-analysis path>",
        "     2. <distinct path>",
        "     3. <distinct path>",
        "     4. <distinct path>",
        "     5. <distinct path>",
        "     6. <distinct path>",
        "     7. <distinct path>",
        "     8. <distinct path>",
    ])


def render_known_gotchas_section(contract: dict, versions: dict[str, str]) -> str:
    out = [
        f"## 3 · Known gotchas for THIS build (v{versions['bundle']} / {versions['engine']} · {versions['build']})",
        "",
        "These entries are generated from `bootstrap_contract.yml`; edit the registry there, then run:",
        "",
        "```bash",
        "python tools/render_bootstrap_contract.py --apply",
        "```",
        "",
        "State the relevant gotcha when it applies:",
        "",
    ]
    for g in _active_gotchas(contract):
        gid = g.get("id", "unknown")
        applies = g.get("applies_to", "general")
        severity = g.get("severity", "unspecified")
        detail = g.get("detail", "").strip()
        out.append(f"- **{gid}** ({severity}; {applies}): {detail}")
    return "\n".join(out).rstrip() + "\n"


def render_surface_table(contract: dict) -> str:
    rows = contract.get("bootstrap_surfaces", [])
    out = [
        "## 3 · Bootstrap surface contract",
        "",
        "This map is generated from `bootstrap_contract.yml`. Required canonical surfaces are hard release gates; generated mirrors are convenience surfaces; optional typo-rescue aliases are convenience shims and must not become scanner authority.",
        "",
        "| Path | Classification | Required | Scanner authority | Generation | Purpose |",
        "|---|---|---:|---:|---|---|",
    ]
    for s in rows:
        out.append("| `{path}` | {status} / {role} | {required} | {authority} | {gen} | {purpose} |".format(
            path=s.get("path", ""),
            status=s.get("status", ""),
            role=s.get("role", ""),
            required="yes" if s.get("required") else "no",
            authority="yes" if s.get("scanner_authority") else "no",
            gen=s.get("generated_from_contract", ""),
            purpose=str(s.get("purpose", "")).replace("|", "/"),
        ))
    return "\n".join(out) + "\n"


def render_bootstrap_audit(contract: dict, versions: dict[str, str]) -> str:
    body = [
        "# Bootstrap file audit — generated from bootstrap_contract.yml",
        "",
        f"Bundle / engine / build: v{versions['bundle']} / {versions['engine']} · {versions['build']}",
        "",
        "## Classification map",
        "",
        "| Path | Classification | Required | Scanner authority | Severity | Generated |",
        "|---|---|---:|---:|---|---|",
    ]
    for s in contract.get("bootstrap_surfaces", []):
        body.append("| `{path}` | {status} / {role} | {required} | {authority} | {severity} | {gen} |".format(
            path=s.get("path", ""),
            status=s.get("status", ""),
            role=s.get("role", ""),
            required="yes" if s.get("required") else "no",
            authority="yes" if s.get("scanner_authority") else "no",
            severity=s.get("scanner_severity", ""),
            gen=s.get("generated_from_contract", ""),
        ))
    body.extend([
        "",
        "## Policy conclusions",
        "",
        "- `CHATGPT_START_HERE.md` is the authoritative ChatGPT operating contract.",
        "- `CHATGTP_READ_ME_FIRST.md` is an optional accidental-typo rescue alias. It may be shipped to catch ChatGPT→ChatGTP transposition, including ATP/GTP-context slips, but missing it should not block canonical ChatGPT discovery.",
        "- New scanner/test logic should target canonical surfaces and treat aliases as compatibility checks only.",
        "- Known gotcha text should be edited in `bootstrap_contract.yml`, not independently in the initiation prompt and §3.",
    ])
    return "\n".join(body) + "\n"


def _workflow_snippet(contract: dict) -> str:
    cmd = contract["workflow"]["first_run_default"]["command"]
    return f"""```bash
python -m mamey doctor
python -m mamey inspect <antiSMASH.zip>
{cmd}
python -m mamey validate <package>
```"""


def _read_proof(contract: dict) -> str:
    rp = contract.get("read_proof") or {}
    return str(rp.get("sentence") or "The sky is not red, it is blue, just like the ocean.")


def render_chatgpt_readme_alias(contract: dict, versions: dict[str, str]) -> str:
    return f"""# CHATGPT_READ_ME_FIRST.md — redirect stub (generated from `bootstrap_contract.yml`)

**One door: run `python mamey_run.py start`, then read `AGENTS.md`.** `start` prints this bundle's
real version and the ordered happy path; `AGENTS.md` is the canonical contract for every assistant.

For assistant-specific rules only, read `CHATGPT_START_HERE.md` (the authoritative ChatGPT contract)
or `CLAUDE_START_HERE.md` (Claude). For a timeout-safe first run, add `--capped-session` to `run`.

Read-proof sentence required by the ChatGPT contract (echo it before your first action):

```text
{_read_proof(contract)}
```

This correctly spelled alias adds nothing beyond that redirect; `CHATGTP_READ_ME_FIRST.md` is the
optional accidental typo-rescue alias, non-authoritative.

Current bundle: v{versions['bundle']} / engine {versions['engine']} · build {versions['build']}.
"""


def render_chatgtp_typo_rescue_alias(contract: dict, versions: dict[str, str]) -> str:
    return f"""# CHATGTP_READ_ME_FIRST.md — accidental-typo rescue stub (generated from `bootstrap_contract.yml`)

You probably meant **ChatGPT**. This filename is a common accidental `CHATGTP` transposition (kept for
scientific users for whom GTP is a familiar acronym); it is **not** the authoritative entry point, and
scanner logic must target `CHATGPT_START_HERE.md` instead.

**One door: run `python mamey_run.py start`, then read `AGENTS.md`.** `start` prints this bundle's real
version and the ordered happy path; `AGENTS.md` is the canonical contract for every assistant.

For assistant-specific rules only, read `CHATGPT_START_HERE.md` (ChatGPT) or `CLAUDE_START_HERE.md`
(Claude, only if this ZIP is operated in Claude). For a timeout-safe first run, add `--capped-session`
to `run`. (Current bundle: v{versions['bundle']} / engine {versions['engine']} · build {versions['build']}.)

Read-proof sentence required by the ChatGPT contract (echo it before your first action):

```text
{_read_proof(contract)}
```
"""


def _replace_marker(text: str, marker: str, replacement: str) -> str:
    start = f"<!-- BEGIN GENERATED: {marker} from bootstrap_contract.yml -->"
    end = f"<!-- END GENERATED: {marker} from bootstrap_contract.yml -->"
    block = f"{start}\n{replacement.rstrip()}\n{end}"
    if start in text and end in text:
        return re.sub(re.escape(start) + r"[\s\S]*?" + re.escape(end), lambda _m: block, text)
    raise ValueError(f"missing generated marker {marker}")


def _install_initial_markers_chatgpt(text: str, initiation: str, gotchas: str) -> str:
    init_block = "<!-- BEGIN GENERATED: initiation_prompt from bootstrap_contract.yml -->\n```text\n" + initiation + "\n```\n<!-- END GENERATED: initiation_prompt from bootstrap_contract.yml -->"
    if "<!-- BEGIN GENERATED: initiation_prompt" not in text:
        text = re.sub(
            r"(### The Initiation Prompt \(emit this on trigger, and once before your first run of a session\)\n\n)```[\s\S]*?```",
            lambda m: m.group(1) + init_block,
            text,
            count=1,
        )
    else:
        text = _replace_marker(text, "initiation_prompt", "```text\n" + initiation + "\n```")

    gotcha_block = "<!-- BEGIN GENERATED: known_gotchas_section from bootstrap_contract.yml -->\n" + gotchas.rstrip() + "\n<!-- END GENERATED: known_gotchas_section from bootstrap_contract.yml -->"
    if "<!-- BEGIN GENERATED: known_gotchas_section" not in text:
        text = re.sub(
            r"## 3 · Known gotchas for THIS build[\s\S]*?(?=\n## 4 · What to read next)",
            gotcha_block + "\n",
            text,
            count=1,
        )
    else:
        text = _replace_marker(text, "known_gotchas_section", gotchas)
    text = re.sub(
        r"> \*\*Cross-assistant bootstrap:\*\* .*?\n\n",
        "> **Cross-assistant bootstrap:** this file is the authoritative ChatGPT contract. "
        "`000_READ_ME_FIRST_CHATGPT_CLAUDE.md` is the cross-assistant router. "
        "Bootstrap mirrors and aliases are described in `bootstrap_contract.yml`; "
        "the `CHATGTP_READ_ME_FIRST.md` file is optional typo rescue only, "
        "not scanner authority. If this ZIP is in Claude, use `CLAUDE_START_HERE.md`.\n\n",
        text,
        count=1,
        flags=re.S,
    )
    return text


def _install_initial_markers_router(text: str, surface_section: str) -> str:
    block = "<!-- BEGIN GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->\n" + surface_section.rstrip() + "\n<!-- END GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->"
    if "<!-- BEGIN GENERATED: bootstrap_surface_map" not in text:
        text = re.sub(
            r"## 3 · Six-place discoverability contract[\s\S]*?(?=\n## 4 · Current gotchas)",
            block + "\n",
            text,
            count=1,
        )
    else:
        text = _replace_marker(text, "bootstrap_surface_map", surface_section)
    text = text.replace(
        "- **Typo rescue:** if you searched for `CHATGTP`, `CHAT GTP`, `ChatGTP read me first`, or similar, open `CHATGTP_READ_ME_FIRST.md`; it points back here and then to `CHATGPT_START_HERE.md`.",
        "- **Typo rescue:** if you accidentally typed `CHATGTP`, `CHAT GTP`, `ChatGTP read me first`, or similar, `CHATGTP_READ_ME_FIRST.md` exists only to redirect you back here and then to the canonical `CHATGPT_START_HERE.md`; it is optional and not scanner authority.",
    )
    text = text.replace(
        "- The root bootstrap files are deliberate duplicates, not stale clutter; they prevent instruction drift when a ZIP is uploaded to a new assistant.",
        "- Bootstrap surfaces are mapped in `bootstrap_contract.yml`; canonical ChatGPT discovery is `CHATGPT_START_HERE.md`, while `CHATGTP_READ_ME_FIRST.md` is optional accidental-typo rescue only.",
    )
    return text


def render_all(contract: dict, versions: dict[str, str]) -> dict[str, str]:
    return {
        "initiation_prompt": render_initiation_prompt(contract, versions),
        "known_gotchas_section": render_known_gotchas_section(contract, versions),
        "bootstrap_surface_map": render_surface_table(contract),
        "BOOTSTRAP_FILE_AUDIT.md": render_bootstrap_audit(contract, versions),
        "CHATGPT_READ_ME_FIRST.md": render_chatgpt_readme_alias(contract, versions),
        "CHATGTP_READ_ME_FIRST.md": render_chatgtp_typo_rescue_alias(contract, versions),
    }


def apply(root: Path = ROOT) -> list[Path]:
    contract = _load_yaml(root / "bootstrap_contract.yml")
    versions = _read_versions(root)
    rendered = render_all(contract, versions)
    changed: list[Path] = []

    # v9.7.374 (audit lane): these are the root-level bootstrap gateway files a fresh
    # ChatGPT/Claude session reads first. A crash/kill mid-write here — same failure mode
    # already found and fixed repeatedly elsewhere this session — would leave the actual
    # bootstrap contract truncated on disk. Write via the shared atomic .tmp+os.replace
    # helper, not a bare write_text().
    start = root / "CHATGPT_START_HERE.md"
    new_start = _install_initial_markers_chatgpt(start.read_text(encoding="utf-8"), rendered["initiation_prompt"], rendered["known_gotchas_section"])
    if start.read_text(encoding="utf-8") != new_start:
        atomic_write_text(start, new_start)
        changed.append(start)

    router = root / "000_READ_ME_FIRST_CHATGPT_CLAUDE.md"
    new_router = _install_initial_markers_router(router.read_text(encoding="utf-8"), rendered["bootstrap_surface_map"])
    if router.read_text(encoding="utf-8") != new_router:
        atomic_write_text(router, new_router)
        changed.append(router)

    for rel in ["BOOTSTRAP_FILE_AUDIT.md", "CHATGPT_READ_ME_FIRST.md", "CHATGTP_READ_ME_FIRST.md"]:
        p = root / rel
        if not p.exists() or p.read_text(encoding="utf-8") != rendered[rel]:
            atomic_write_text(p, rendered[rel])
            changed.append(p)

    # Keep top-level reader banners truthful without generating entire README files.
    replacements = {
        "README.md": [
            ("A typo-rescue alias is also shipped as `CHATGTP_READ_ME_FIRST.md`.",
             "A correctly spelled ChatGPT alias is shipped as `CHATGPT_READ_ME_FIRST.md`; `CHATGTP_READ_ME_FIRST.md` is optional accidental-typo rescue only."),
        ],
        "README_START_HERE.md": [
            ("`CHATGTP_READ_ME_FIRST.md` is included as a typo-rescue alias.",
             "`CHATGPT_READ_ME_FIRST.md` is the correctly spelled alias; `CHATGTP_READ_ME_FIRST.md` is optional accidental-typo rescue only."),
        ],
    }
    for rel, reps in replacements.items():
        p = root / rel
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        new = txt
        for old, rep in reps:
            new = new.replace(old, rep)
        if new != txt:
            atomic_write_text(p, new)
            changed.append(p)
    return changed


def check(root: Path = ROOT) -> list[str]:
    # Re-render in a temp-like in-memory comparison by checking the generated outputs and markers.
    contract = _load_yaml(root / "bootstrap_contract.yml")
    versions = _read_versions(root)
    rendered = render_all(contract, versions)
    errors: list[str] = []
    start_text = (root / "CHATGPT_START_HERE.md").read_text(encoding="utf-8")
    for marker, expected in [("initiation_prompt", "```text\n" + rendered["initiation_prompt"] + "\n```"), ("known_gotchas_section", rendered["known_gotchas_section"].rstrip())]:
        begin = f"<!-- BEGIN GENERATED: {marker} from bootstrap_contract.yml -->"
        end = f"<!-- END GENERATED: {marker} from bootstrap_contract.yml -->"
        m = re.search(re.escape(begin) + r"\n([\s\S]*?)\n" + re.escape(end), start_text)
        if not m:
            errors.append(f"CHATGPT_START_HERE.md: missing generated marker {marker}")
        elif m.group(1).strip() != expected.strip():
            errors.append(f"CHATGPT_START_HERE.md: generated block {marker} is stale")
    router_text = (root / "000_READ_ME_FIRST_CHATGPT_CLAUDE.md").read_text(encoding="utf-8")
    begin = "<!-- BEGIN GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->"
    end = "<!-- END GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->"
    m = re.search(re.escape(begin) + r"\n([\s\S]*?)\n" + re.escape(end), router_text)
    if not m:
        errors.append("000_READ_ME_FIRST_CHATGPT_CLAUDE.md: missing generated bootstrap_surface_map")
    elif m.group(1).strip() != rendered["bootstrap_surface_map"].strip():
        errors.append("000_READ_ME_FIRST_CHATGPT_CLAUDE.md: generated bootstrap_surface_map is stale")
    for rel in ["BOOTSTRAP_FILE_AUDIT.md", "CHATGPT_READ_ME_FIRST.md", "CHATGTP_READ_ME_FIRST.md"]:
        p = root / rel
        if not p.exists():
            errors.append(f"{rel}: missing generated file")
        elif p.read_text(encoding="utf-8").strip() != rendered[rel].strip():
            errors.append(f"{rel}: generated file is stale")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--print", choices=["initiation_prompt", "known_gotchas_section", "bootstrap_surface_map", "audit"])
    ap.add_argument("--root", default=str(ROOT))
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    if ns.apply:
        changed = apply(root)
        for p in changed:
            emit(f"updated {p.relative_to(root)}")
        return 0
    if ns.check:
        errors = check(root)
        if errors:
            emit(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
            return 1
        contract = _load_yaml(root / "bootstrap_contract.yml")
        payload = {
            "status": "PASS",
            "contract_sha256": hashlib.sha256((root / "bootstrap_contract.yml").read_bytes()).hexdigest(),
            "surfaces": len(contract.get("bootstrap_surfaces", [])),
            "gotchas": len(_active_gotchas(contract)),
        }
        emit(json.dumps(payload, indent=2))
        return 0
    contract = _load_yaml(root / "bootstrap_contract.yml")
    versions = _read_versions(root)
    if ns.print == "initiation_prompt":
        emit(render_initiation_prompt(contract, versions))
    elif ns.print == "known_gotchas_section":
        emit(render_known_gotchas_section(contract, versions))
    elif ns.print == "bootstrap_surface_map":
        emit(render_surface_table(contract))
    elif ns.print == "audit":
        emit(render_bootstrap_audit(contract, versions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
