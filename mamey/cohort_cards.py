"""cohort_cards.py — Gap 1: cohort-scale Mode B card orchestrator.

THE GAP THIS FILLS
------------------
Carding N strains has been N hand-runs of `mamey mode-b` plus manual stitching, and the cards
come out cross-strain-blind. This orchestrator does it in one pass:
  1. discover all sealed packages under a directory (manifest.json present)
  2. resolve each to its strain id, reusing the engine's own per-strain mode-b card path
  3. inject the Gap-2 §X Cross-strain context block into every card, read from the cohort master

It does NOT reimplement card generation — it drives the existing `mode_b_command` per strain and
post-processes the emitted markdown. No scoring change; deterministic; PRIVATE by construction
(cohort spans AS strains; public render redacts to AS-XXX).

DEPENDENCY: a populated cohort master with Cross_Strain_Class_Prevalence recomputed for the
current cohort (denominator invariant must hold). If the master is stale/empty, the §X blocks are
skipped (each card still generates) and a warning is emitted — the cards are never wrong, just
un-annotated.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

from mamey.cross_strain_card_context import (
    load_prevalence, registry_size, card_context_block,
)

_RANK_RE = re.compile(r"## Rank \d+: .+?\((BGC\d+)\)")


def discover_packages(packages_dir: str | Path) -> list[Path]:
    """Return every package dir (manifest.json present) under packages_dir, sorted by name."""
    root = Path(packages_dir)
    found = []
    for mf in root.rglob("manifest.json"):
        found.append(mf.parent)
    # also accept a flat dir of <SID>/package/manifest.json or <SID>/manifest.json
    return sorted(set(found), key=lambda p: p.name)


def _strain_id(pkg: Path) -> str:
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    return (m.get("strain", {}).get("strain_id")
            or m.get("strain_id")
            or pkg.parent.name)


def _products_for(pkg: Path) -> dict:
    """Map bgc_id -> list of product classes from the manifest."""
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    out = {}
    for b in m.get("bgcs", []):
        bid = b.get("bgc_id")
        if not bid:
            continue  # v9.7.117 (Bug Hunt): skip malformed BGC entries without an id, don't KeyError
        prods = b.get("products", [])
        if isinstance(prods, str):
            try:
                prods = json.loads(prods.replace("'", '"'))
            except Exception:
                prods = [prods]
        out[bid] = list(prods)
    return out


def inject_cross_strain(card_md: str, strain_id: str, products_by_bgc: dict,
                        prevalence: dict, N: int) -> str:
    """Append the §X Cross-strain context block to each Rank card in the markdown."""
    if not prevalence:
        return card_md  # stale/empty master -> leave cards un-annotated
    # split before each "## Rank" header (at string start or after a newline)
    parts = re.split(r"(?=(?:^|\n)## Rank \d+:)", card_md)
    out = [parts[0]] if parts and not parts[0].startswith("## Rank") else []
    for part in parts[1:]:
        m = _RANK_RE.search(part)
        bid = m.group(1) if m else ""
        if bid and "§X. Cross-strain context" not in part:
            blk = card_context_block(strain_id, bid, products_by_bgc.get(bid, []),
                                     prevalence, N)
            if blk:
                part = part.rstrip("\n") + "\n\n" + blk
        out.append(part)
    return "\n".join(out)


def run_cohort_cards(packages_dir: str | Path, master_path: str | Path,
                     outdir: str | Path, top_n: int = 15,
                     mode_b_runner=None) -> dict:
    """Orchestrate: generate + cross-strain-annotate Mode B cards for every package.

    mode_b_runner(pkg, outdir, top_n) -> path to the emitted *_Mode_B_Top_Leads.md
    is injected so this module stays testable without the full CLI. In production the CLI
    passes a thin wrapper around mamey.chatgpt_commands.mode_b_command.

    Returns a summary dict: {strains, cards, annotated, master_used, warnings}.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prevalence = load_prevalence(master_path)
    N = registry_size(master_path)
    warnings = []
    if not prevalence:
        warnings.append(f"master {master_path} has no usable Cross_Strain_Class_Prevalence "
                        f"-> cards generated WITHOUT §X cross-strain context")

    pkgs = discover_packages(packages_dir)
    total_cards = total_annotated = 0
    per_strain = {}
    for pkg in pkgs:
        sid = _strain_id(pkg)
        md_path = mode_b_runner(pkg, outdir, top_n)
        if md_path is None or not Path(md_path).exists():
            warnings.append(f"{sid}: card generation produced no markdown")
            continue
        card_md = Path(md_path).read_text(encoding="utf-8")
        products = _products_for(pkg)
        annotated_md = inject_cross_strain(card_md, sid, products, prevalence, N)
        n_cards = annotated_md.count("## Rank ")
        n_annot = annotated_md.count("§X. Cross-strain context")
        final = outdir / f"{sid}_Mode_B_cohort.md"
        # AUDIT_374: atomic write (tmp-sibling + os.replace) — this is the cohort-annotated
        # Mode B card a reviewer opens directly; a process killed mid-write previously left a
        # truncated *_Mode_B_cohort.md on disk with no error surfaced, matching the atomic-write
        # gap already fixed this session elsewhere in the codebase.
        _tmp = final.with_name(final.name + ".tmp")
        _tmp.write_text(annotated_md, encoding="utf-8")
        _tmp.replace(final)
        per_strain[sid] = {"cards": n_cards, "annotated": n_annot, "path": str(final)}
        total_cards += n_cards
        total_annotated += n_annot

    return {
        "strains": len(per_strain),
        "cards": total_cards,
        "annotated": total_annotated,
        "master_used": str(master_path),
        "N": N,
        "warnings": warnings,
        "per_strain": per_strain,
    }
