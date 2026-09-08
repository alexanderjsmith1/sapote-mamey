#!/usr/bin/env python3
"""modeb_domain_phylogeny.py — gate-safe `#### Domain phylogeny` subsection (.360, P360-002).

Surfaces the .359 `_4D` two-proof / KS-clade rescue verdict INTO the Mode-B card. This closes the
delivery gap the Developer or User named ("why not a Mode B?"): `_4D` is computed by `two_proof_join` and written to
`{strain}_4D_two_proof_rescue.csv`, but NO card module read it — the verdict lived on disk and was
invisible to every reader.

Design (matches the other modeb_subsections):
  * Renders a `#### ` block with NO `§N` marker, so `modeb_structure_gate` (which keys on §N headings)
    is UNAFFECTED — same mechanism as catalytic_domain_census / blastp_channel_evidence.
  * Reader-side, NON-SCORING, deterministic. PRIMARY data is the package-internal `_4D` CSV, so the
    section is complete from the package alone — the emitter calls `domain_phylogeny(pkg, bgc_id)` with
    no extra state.
  * The KS/AT TREE artifacts (patristic distance, per-strain identity baseline, treefile) live OUTSIDE
    the package under `strain_data/<STRAIN>/PKS_KS_tree_*/`. They are read ONLY if `tree_root` is
    provided (workspace runs); otherwise the section cites the canonical tree path as provenance and
    marks distance/baseline as not co-located — a MEASUREMENT gap, never a biological negative.

Field spec: Amber (AMBER P358, 2026-08-10). Join key: the `_4D` row's contig token
(`NODE_\\d+` for AS SPAdes; WGS accession for SID) matches the tree tip PREFIX; keep the node token,
never the BGC ordinal alone (BGC node-naming rule).

Claim-safety (in the block header): `KS_CLADE_ONLY` = reference-DARK CANDIDATE to surface, never a
confirmed rescue; cis-AT KS can cluster by upstream-module SUBSTRATE (programming convergence) rather
than ancestry; two-proof (homology AND biosynthetic-logic complementarity) required before any
`RESCUE_CANDIDATE`; homology-guided linkage, NOT nucleotide joining; judgment deferred.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

# Evidence-verdict -> interpretation wording (the Developer or User-approved additive `interpretation` column, 2026-08-10).
# The `verdict` stays the EVIDENCE label (gates/tests read it); interpretation names the reading.
_INTERP = {
    "TWO_PROOF_RESCUE": "complementary two-proof candidate (RG-GMCI logic + KS-clade homology)",
    "MULTI_CHANNEL_HOLD": "two homology channels concordant, complementarity proof owed — advisory HOLD, not a rescue",
    "KS_CLADE_ONLY":    "reference-dark KS-clade link (surface for adjudication)",
    "RGGMCI_ONLY":      "logic-only rescue (no shared KS clade)",
    "WEAK":             "below both bars",
}


def _find(pkg: Path, suffix: str):
    hits = sorted(Path(pkg).glob(f"*{suffix}"))
    return hits[0] if hits else None


def _read_csv(path):
    if not path or not Path(path).exists():
        return None
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def _read_tsv(path):
    if not path or not Path(path).exists():
        return None
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _strain_of(pkg: Path) -> str:
    inv = _find(pkg, "_2_inventory.csv")
    if inv:
        m = re.match(r"(.+?)_2_inventory\.csv$", inv.name)
        if m:
            return m.group(1)
    return Path(pkg).name


def _contig_token(v: str) -> str:
    """The join token: NODE_\\d+ for AS SPAdes, else the leading accession field."""
    m = re.search(r"(NODE_\d+)", v or "")
    if m:
        return m.group(1)
    return (v or "").strip().split("_")[0]


def _rows_touching(rows, bgc_id):
    out = []
    for r in rows or []:
        if (r.get("bgc_a") or "").strip() == bgc_id or (r.get("bgc_b") or "").strip() == bgc_id:
            out.append(r)
    return out


def _strain_baseline(strain, tree_root):
    """Per-strain within-contig median %id (never pooled). None unless the baseline tsv is co-located."""
    if not tree_root:
        return None
    p = Path(tree_root) / "_IDENTITY_BASELINE_2026-08-10" / "_COHORT_identity_baseline.tsv"
    for r in _read_tsv(p) or []:
        if (r.get("strain") or "").strip() == strain:
            try:
                return float(r.get("within_contig_median_pid"))
            except (TypeError, ValueError):
                return None
    return None


def _ks_distance(strain, conta, contb, tree_root):
    """Min cross-region patristic distance between two contigs from Amber's fragment_candidates.tsv.
    Returns (formatted_str | None). Only available with a co-located tree_root."""
    if not tree_root:
        return None
    root = Path(tree_root) / strain / "PKS_KS_tree_2026-08-10"
    cands = sorted(root.glob(f"{strain}_*_fragment_candidates.tsv")) if root.exists() else []
    best = None
    for f in cands:
        for r in _read_tsv(f) or []:
            na, nb = _contig_token(r.get("node_a")), _contig_token(r.get("node_b"))
            if {na, nb} == {conta, contb} and na != nb:
                try:
                    d = float(r.get("patristic_dist"))
                except (TypeError, ValueError):
                    continue
                if best is None or d < best[0]:
                    best = (d, r.get("KS_a") or na, r.get("KS_b") or nb)
    if best is None:
        return None
    return f"{best[0]:.4f} | {best[1]} ~ {best[2]} | CROSS-REGION"


def _tree_citation(strain, contig_token) -> str:
    """Cite the rooted treefile + the tip the contig token maps to (provenance, not a data read)."""
    return f"`{strain}_KS_tree.rooted.treefile` @ `{contig_token}`"


def domain_phylogeny(pkg, bgc_id, tree_root=None) -> str:
    pkg = Path(pkg)
    strain = _strain_of(pkg)
    rows = _read_csv(_find(pkg, "_4D_two_proof_rescue.csv"))
    L = [
        "#### Domain phylogeny (KS/AT two-proof · _4D)",
        "<!-- gate-safe subsection (no §N marker; modeb_structure_gate unaffected). Surfaces the "
        "package's _4D two-proof / KS-clade rescue verdict per region. KS_CLADE_ONLY = reference-DARK "
        "CANDIDATE to surface, NOT a confirmed rescue; cis-AT KS can cluster by upstream-module "
        "substrate (programming convergence) not ancestry; two-proof (homology AND biosynthetic-logic "
        "complementarity) required before RESCUE_CANDIDATE; homology-guided linkage, NOT nucleotide "
        "joining; judgment deferred. -->",
        "",
    ]
    if rows is None:
        L.append("*No `_4D_two_proof_rescue.csv` in this package — the two-proof/KS-clade channel was "
                 "NOT produced here (package predates the .359 engine, or the scan was skipped). This "
                 "is a measurement gap, not a biological negative.*")
        return "\n".join(L)
    hits = _rows_touching(rows, bgc_id)
    if not hits:
        L.append(f"*No cross-region KS/AT two-proof signal for `{bgc_id}` — the channel ran and no "
                 f"pair touches this region.*")
        return "\n".join(L)

    # Surface CANDIDATE-grade pairs; collapse WEAK (below both bars) to a count so a fragmented
    # assembly's hundreds of WEAK pairs don't drown the card. (Signoff gate: don't render non-signal
    # as content.) Rows arrive already ordered TWO_PROOF_RESCUE > KS_CLADE_ONLY > RGGMCI_ONLY > WEAK.
    surfaced = [r for r in hits if (r.get("verdict") or "").strip() != "WEAK"]
    n_weak = len(hits) - len(surfaced)
    baseline = _strain_baseline(strain, tree_root)
    if not surfaced:
        L.append(f"*No candidate-grade cross-region pair for `{bgc_id}` — {n_weak} `WEAK` pair(s) "
                 f"present (below both bars), omitted. A measurement outcome, not a biological negative.*")
        return "\n".join(L)
    L.append("| partner | verdict | interpretation | RG-GMCI | KS clade | patristic | tree |")
    L.append("|---|---|---|---|---|---|---|")
    for r in surfaced:
        a_is_this = (r.get("bgc_a") or "").strip() == bgc_id
        partner = ((r.get("bgc_b") if a_is_this else r.get("bgc_a")) or "?").strip()
        verdict = (r.get("verdict") or "").strip()
        interp = (r.get("interpretation") or _INTERP.get(verdict, "")).strip()
        rg = (r.get("rggmci_confidence") or "").strip() or "—"
        ksid = (r.get("ks_clade_id") or "").strip() or "—"
        conta, contb = _contig_token(r.get("contig_a")), _contig_token(r.get("contig_b"))
        dist = _ks_distance(strain, conta, contb, tree_root)
        this_contig = conta if a_is_this else contb
        L.append(f"| `{partner}` | **{verdict}** | {interp} | {rg} | {ksid} | "
                 f"{dist or '—'} | {_tree_citation(strain, this_contig)} |")
    L.append("")
    if n_weak:
        L.append(f"*+ {n_weak} `WEAK` pair(s) below both bars — omitted from the table.*")
    if baseline is not None:
        thr = min(max(baseline + 20, 70), 100)
        L.append(f"*Same-locus identity threshold for **{strain}**: within-contig median %id = "
                 f"{baseline:.0f}% → cross-contig CANDIDATE when %id > {thr:.0f}% (baseline+20, floor 70). "
                 f"Baseline is PER-STRAIN — never pooled.*")
    else:
        L.append(f"*Per-strain identity baseline not co-located with this package (see "
                 f"`strain_data/{strain}/_IDENTITY_BASELINE_2026-08-10/`). The legacy ≤0.10 patristic "
                 f"cutoff is a secondary signal only (thin: ~4 candidates across ~33 trees).*")
    L.append(f"*Tree artifacts: `strain_data/{strain}/PKS_KS_tree_2026-08-10/` (rooted treefile + "
             f"PNG per domain KS/AT/C/A). Homology-guided linkage; judgment deferred.*")
    return "\n".join(L)


# ── VGP-399 card 3/3: generalized per-class domain-tree subsections ─────────────────────────────
# Consumes the `{class}_domain_tree_summary.tsv` contract written by mamey/domain_tree.py (the gated
# builder). ADDITIVE: domain_phylogeny() above is byte-unchanged; emitters opt in by also calling
# domain_tree_sections(). Same gate-safety mechanism (#### blocks, no §N marker) and the same
# "missing summary renders nothing" rule — a measurement gap is never rendered as an empty stub.

_TAILORING_NOTE = ("capacity context only — clade proximity to a characterized reference names the "
                   "chemistry CLASS its relatives perform, never a modification/identity claim")
_MODULE_CORE = {"PKS_KS", "PKS_AT", "Condensation", "AMP-binding", "PKS_KR", "PKS_DH"}


def _summaries_for(strain, tree_root):
    """All co-located {class}_domain_tree_summary.tsv files. tree_root=None -> none (workspace-only
    artifacts are read only when explicitly co-located, matching the _4D tree_root contract)."""
    if not tree_root:
        return []
    root = Path(tree_root) / strain
    if not root.exists():
        return []
    return sorted(root.glob("**/*_domain_tree_summary.tsv"))


def domain_tree_sections(pkg, bgc_id, tree_root=None) -> str:
    """Render one `#### Domain tree (<class>)` block per co-located summary whose rows touch this
    strain. Returns "" when no summaries exist — the emitter appends nothing (no empty stubs)."""
    pkg = Path(pkg)
    strain = _strain_of(pkg)
    blocks = []
    for p in _summaries_for(strain, tree_root):
        rows = _read_tsv(p) or []
        rows = [r for r in rows if (r.get("strain") or "").strip() in ("", strain)]
        if not rows:
            continue
        cls = (rows[0].get("domain_class") or p.name.split("_domain_tree_summary")[0]).strip()
        kind_note = ("strain-internal module-core tree; ITERATIVE-MODULE GUARD applies "
                     "(domain count != module count != chain length)"
                     if cls in _MODULE_CORE else _TAILORING_NOTE)
        L = [
            f"#### Domain tree ({cls})",
            f"<!-- gate-safe subsection (no section-number marker). Source: `{p.name}` (gated build via "
            f"mamey/domain_tree.py: staged/dedup'd, tree_sanity PASS required). {kind_note}; "
            f"judgment deferred. -->",
            "",
            "| tip | clade | support | nearest ref | ref family | patristic |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            L.append("| `{tip}` | {clade} | {sup} | {ref} | {fam} | {pat} |".format(
                tip=(r.get("tip") or r.get("node") or "?").strip(),
                clade=(r.get("clade_id") or "—").strip() or "—",
                sup=(r.get("clade_support") or "—").strip() or "—",
                ref=(r.get("nearest_ref") or "—").strip() or "—",
                fam=(r.get("nearest_ref_family") or "—").strip() or "—",
                pat=(r.get("patristic_to_ref") or "—").strip() or "—"))
        L.append("")
        blocks.append("\n".join(L))
    return "\n".join(blocks)
