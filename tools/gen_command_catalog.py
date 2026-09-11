#!/usr/bin/env python3
"""gen_command_catalog.py — generate the task-oriented CLI command catalog (v9.7.405).

WAC-01375 items 12/13/15/16/29 ("argument conventions and command discovery"): the CLI has ~90
subcommands and no grouped, current index of them. This generator introspects the live argparse
tree in mamey.cli, groups every subcommand by task family, and writes
docs/COMMAND_CATALOG.generated.md — so the catalog cannot drift from the code. `--check` fails
when the committed file is stale (same contract as gen_tools_inventory.py).

Grouping is by a small, explicit table below (a command not in it lands in "Other"), so a new
subcommand is still listed the moment it is added. Deterministic; no network; no package I/O.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "COMMAND_CATALOG.generated.md"

GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    ("Run and seal a strain", "Deterministic extraction — the only step that creates a package.",
     ("run", "validate", "seal-package", "inspect", "start", "doctor", "capabilities", "resume", "fingerprint", "handoff", "explain", "release-qa", "tab-reconcile")),
    ("Post-seal figures", "Start with `render-all-figures` for one sealed package. Use `figure-factory` "
     "for a receipt-bound custom configuration; the remaining commands are specialized builders.",
     ("render-figures", "figure-factory", "figures", "interactive-figures", "cohort-figures", "diagram", "atlas",
      "overmerge-widgets", "rggmci-widget", "assembly-line-widget", "assembly-line-pdf", "bgc-gene-map", "kcb-locusmap", "lead-pages", "render-all-figures",
      "render-widgets", "attach-bgc-overlays")),
    ("Mode B judgment support", "Scaffolds and gates for LLM judgment; the triage table is NOT a finished card.",
     ("mode-b", "modeb-compile", "modeb-export", "modeb-round", "verify-modeb", "write-narrative",
      "compile-report", "report-card", "guide", "verify-guide", "verify-citations", "dualpass", "surface-leads",
      # v9.7.407: the layperson guide renders plain-language prose from package-owned fields only.
      # Grouped here rather than with the figure builders because it is narrative output that
      # carries the claim-safety footer, not a plot.
      "layperson",
      "emit-modeb-cards", "emit-modeb-template", "emit-strain-modeb", "modeb-availability", "modeb-blastp",
      "modeb-gene-first", "build-bgc-drafts", "claim-safety", "class-believability")),
    ("Evidence channels (BLASTp / MIBiG / BiG-SCAPE)", "Optional deeper evidence; every channel stays a separate lane.",
     ("tool-database-inspect", "ingest-blastp", "ingest-blastp-trove", "blastp-status", "blastp-online", "blastp-ebi", "blastp-round",
      "auto-blastp", "blastp-availability", "bigscape", "gcf-network", "clinker", "hmm-adjudicate",
      "domain-reference", "domain-level", "reference-dark", "kcb-frontpage", "comparator-coverage",
      "bgc-blastp-panel", "blastp-followup", "cohort-proteins", "resistance-dossier")),
    ("Cohort and cross-strain", "Aggregation across sealed packages.",
     ("cohort", "cohort-leads", "cohort-assemble", "cohort-precompute", "majority-read", "novelty-shortlist",
      "realistic-count", "af-leadboard", "af-dossier", "genus-appendix", "good-guesses", "clade-deepdive",
      "split-overmerge-cards", "compound-families", "p450-tailoring", "assembly-line", "discover", "explore",
      "compare", "activity-leads", "activity-lead-genes", "cddr-pks", "directed-pks-study",
      "wise-fragmented-pks")),
    ("Phylogeny", "Use `phylo-autopilot` for 16S routing and EPA-ng placement; use `phylo-run` for an "
     "approved GToTree/IQ-TREE genome workflow.", ("phylo-run", "phylo-autopilot", "ani", "signoff")),
    ("Workflow, receipts, catalogs", "Non-destructive status and lookups.",
     ("workflow", "deliverables", "deliverable-queue", "ingest-receipts", "validate-finished-review-request", "list-bgcs", "literature", "lookup", "search",
      "lab-quest",
      "triage-raw", "wheelhouse", "list", "clean", "add-strain")),
    ("Compatibility and maintainer commands", "Retained for existing scripts and specialized maintenance. "
     "They are not additional onboarding paths.",
     ("chatgpt-init", "codex-figure-catalog", "codex-figure-sets", "codex-figure-sources",
      "codex-bigscape-figure-sets", "codex-heatmaps")),
]


def _md_cell(value: str) -> str:
    """Escape prose for a Markdown table cell.

    Argparse help may legitimately contain ``|`` (for example, a list of figure
    kinds).  An unescaped pipe creates extra table columns and makes GitHub hide
    the rest of the description.
    """
    return " ".join(value.split()).replace("\\", "\\\\").replace("|", "\\|")


def _subparsers():
    from mamey import cli  # local import: the CLI module is heavy
    parser = cli.build_parser() if hasattr(cli, "build_parser") else None
    if parser is None:  # fall back: find the parser-building function by convention
        for name in ("make_parser", "_build_parser", "get_parser"):
            if hasattr(cli, name):
                parser = getattr(cli, name)(); break
    if parser is None:
        raise SystemExit("gen_command_catalog: mamey.cli exposes no parser builder")
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # help= text lives on the pseudo-actions, not on the sub-parser (whose .description
            # is usually None); prefer help, fall back to description.
            helps = {ca.dest: (ca.help or "") for ca in action._choices_actions}
            result = {}
            owner_by_parser = {}
            for name, parser in action.choices.items():
                key = id(parser)
                if key in owner_by_parser:
                    result[owner_by_parser[key]]["aliases"].append(name)
                    continue
                owner_by_parser[key] = name
                result[name] = {
                    "help": helps.get(name) or (parser.description or ""),
                    "aliases": [],
                }
            return result
    return {}


def render() -> str:
    from mamey import BUNDLE_VERSION, __version__
    subs = _subparsers()
    seen: set[str] = set()
    lines = ["# Command catalog (generated)", "",
             f"*Generated from the live argparse tree of `mamey.cli` by `tools/gen_command_catalog.py` — "
             f"bundle v{BUNDLE_VERSION} · engine {__version__}. Do not edit by hand; `--check` fails the build when stale.*", "",
             "Every command is invoked as `python mamey_run.py <command> …` from the extracted bundle root "
             "(the bundle-local launcher, so an older installed copy cannot shadow it). Most post-seal commands take "
             "`--package <sealed package dir>`; `run` is the only command that creates a package. "
             "Claim-safety: every output is a class-level hypothesis with judgment deferred.", "",
             "## Recommended front doors", "",
             "Most users can stay on this path: `start` for orientation, `inspect` then `run` for extraction, "
             "`validate` for the package gate, `discover` and `explore` for review, `render-all-figures` for "
             "the applicable figure suite, `phylo-autopilot` or `phylo-run` for tree workflows, `mode-b` for "
             "the interpretation scaffold, and `workflow` for status. The catalog below includes specialist "
             "commands so they remain discoverable; aliases are folded into their canonical command row.", ""]
    for title, blurb, names in GROUPS:
        lines += [f"## {title}", "", f"_{blurb}_", "", "| command | what it does |", "|---|---|"]
        for n in names:
            if n in subs:
                seen.add(n)
                meta = subs[n]
                help_ = _md_cell(meta["help"])
                aliases = "" if not meta["aliases"] else " (alias: " + ", ".join(f"`{x}`" for x in meta["aliases"]) + ")"
                lines.append(f"| `{n}`{aliases} | {help_ or '(no description)'} |")
        lines.append("")
    other = sorted(set(subs) - seen)
    if other:
        lines += ["## Other", "", "_Commands not yet assigned to a task family — add them to GROUPS in the generator._", "",
                  "| command | what it does |", "|---|---|"]
        for n in other:
            help_ = _md_cell(subs[n]["help"])
            lines.append(f"| `{n}` | {help_ or '(no description)'} |")
        lines.append("")
    alias_count = sum(len(meta["aliases"]) for meta in subs.values())
    lines += [f"_{len(subs)} canonical commands catalogued; {alias_count} aliases folded into those rows._", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if the committed catalog is stale")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.stderr.write(f"STALE: {OUT.relative_to(ROOT)} — run tools/gen_command_catalog.py\n")
            return 1
        sys.stdout.write("command catalog current\n")
        return 0
    OUT.write_text(text, encoding="utf-8")
    sys.stdout.write(f"wrote {OUT.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
