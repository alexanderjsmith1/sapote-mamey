"""FA3 / ADD-03 — First-class Reference-Dark novelty prior (per-BGC, NON-RANKING).

Reference-dark = the discovery frontier: a BGC whose genes do NOT recognizably map to any
characterized MIBiG family. Today that determination is re-derived ad hoc in several places
(cohort_synthesis `_is_fully_dark` / `_is_dark_or_unresolved`, and inline KCB-text parsing),
with two legitimate-but-conflated definitions. This module promotes it to ONE authoritative,
basis-tagged per-BGC field, computed once from evidence already sealed in the package:

  * per-gene MIBiG recognizability  — `*_3_mibig_profile.csv`
      (recognizable_gene_count / query_gene_count, dominant MIBiG accession, convergence tier)
  * region-level KCB coverage       — `*_4_triage_board.csv` (KCB_top)

Each BGC is tagged one of:
  REFERENCE_DARK          — no per-gene MIBiG protein hits AND no KCB MIBiG anchor.
  PARTIALLY_CHARACTERIZED — a MIBiG/KCB anchor exists but the family match is sparse
                            (recognizable fraction < WELL_FRACTION) or class-mismatched, OR
                            a region-level KCB anchor with zero per-gene recognizability.
  WELL_CHARACTERIZED      — a MIBiG anchor with a dense per-gene family match
                            (recognizable fraction >= WELL_FRACTION), not class-mismatched.

CLAIM-SAFETY / NON-RANKING CONTRACT
-----------------------------------
This is a DESCRIPTIVE novelty PRIOR, not a score. "Absence of a family match is a novelty
PRIOR, not proof of a new compound." It does NOT read or write AB/AF/novelty/lead_tier and is
computed post-seal from an already-sealed package, so it cannot move any published tier
(un-gated). Every basis string carries its own denominator (N/M genes) so the two historical
definitions can never be silently mixed. Wiring this into scoring would be a CAT-01-class
change (sign-off gated) — see FA3_HOOK.md; it is deliberately NOT done here.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import os
import re
from pathlib import Path

REFERENCE_DARK = "REFERENCE_DARK"
PARTIALLY_CHARACTERIZED = "PARTIALLY_CHARACTERIZED"
WELL_CHARACTERIZED = "WELL_CHARACTERIZED"

# Recognizable-gene fraction at/above which a MIBiG-anchored BGC is called well-characterized.
WELL_FRACTION = 0.5

# antiSMASH MIBiG cluster accession, e.g. BGC0001211. A "bare genome-reference" KCB hit that is
# NOT a MIBiG accession is treated as no anchor (mirrors cohort_synthesis `_is_dark_or_unresolved`).
_MIBIG_RE = re.compile(r"BGC\d{7}")

NOVELTY_PRIOR_NOTE = (
    "Absence of a family match is a novelty PRIOR, not proof of a new compound; "
    "product identity requires isolation."
)
CHARACTERIZED_NOTE = (
    "Recognizable MIBiG family match is a capacity/relatedness signal, not proof of exact "
    "product identity, expression, production, activity, or novelty."
)

REPORT_ONLY_CONTRACT = "NON_RANKING_DESCRIPTIVE_PRIOR_DOES_NOT_ENTER_AB_AF_TIER"

CSV_HEADERS = [
    "bgc_id",
    "reference_dark_class",
    "reference_dark_basis",
    "query_gene_count",
    "recognizable_gene_count",
    "recognizable_gene_fraction",
    "dominant_mibig_accession",
    "kcb_anchor",
    "novelty_prior_note",
    "report_only_contract",
]


def _has_mibig(text) -> bool:
    return bool(_MIBIG_RE.search(str(text or "")))


def _to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int(v, default=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def classify_reference_dark(
    query_gene_count,
    recognizable_gene_count,
    recognizable_gene_fraction,
    dominant_mibig_accession="",
    dominant_convergence_tier="",
    interpretation_class="",
    kcb_top=None,
) -> tuple[str, str]:
    """Return (reference_dark_class, reference_dark_basis) for one BGC.

    Pure function of already-computed evidence fields; no I/O, no scoring. The basis always
    quotes its denominator (recognizable/total genes) so the metric is never denominator-free.
    """
    import math
    try:
        total = float(query_gene_count)
        recognized = float(recognizable_gene_count)
        frac = float(recognizable_gene_fraction)
    except (TypeError, ValueError) as exc:
        raise ValueError("REFERENCE_DARK_EVIDENCE_INVALID: counts and fraction must be numeric") from exc
    if (not all(math.isfinite(value) for value in (total, recognized, frac))
            or not total.is_integer() or not recognized.is_integer()
            or total <= 0 or recognized < 0 or recognized > total
            or not 0 <= frac <= 1):
        raise ValueError("REFERENCE_DARK_EVIDENCE_INVALID: invalid counts, denominator, or fraction")
    qc, rc = int(total), int(recognized)
    # Native producer rounds fractions to four decimal places.
    if abs(frac - rc / qc) > 0.000050000001:
        raise ValueError("REFERENCE_DARK_EVIDENCE_INVALID: fraction disagrees with counts")
    denom = f"({rc}/{qc} genes)"
    per_gene_anchor = _has_mibig(dominant_mibig_accession)
    kcb_anchor = _has_mibig(kcb_top)
    class_mismatch = str(dominant_convergence_tier or "").strip().upper() == "CAUTION_CLASS_MISMATCH"
    no_per_gene = (
        rc <= 0
        or frac <= 0.0
        or str(interpretation_class or "").strip().upper() == "NO_MIBIG_PROTEIN_HITS"
    )

    if no_per_gene:
        if kcb_anchor:
            return (
                PARTIALLY_CHARACTERIZED,
                f"kcb_region_anchor_only; no per-gene MIBiG-recognizable genes "
                f"recognizable_gene_fraction=0.00 {denom}; region-level KCB anchor "
                f"{_MIBIG_RE.search(str(kcb_top)).group(0)}",
            )
        return (
            REFERENCE_DARK,
            f"no_per_gene_mibig_hits_and_no_kcb_mibig_anchor; "
            f"recognizable_gene_fraction=0.00 {denom}",
        )

    if frac >= WELL_FRACTION and per_gene_anchor and not class_mismatch:
        return (
            WELL_CHARACTERIZED,
            f"mibig_anchored_dense_family_match; recognizable_gene_fraction={frac:.2f} "
            f"(>={WELL_FRACTION:.2f}) {denom}; dominant {dominant_mibig_accession}",
        )

    # Some recognizability, but sparse / class-mismatched / anchor-less.
    if class_mismatch:
        reason = "class_mismatch_anchor"
    elif not per_gene_anchor:
        reason = "partial_recognizability_no_dominant_mibig_accession"
    else:
        reason = "mibig_anchored_sparse_family_match"
    anchor_txt = f"; dominant {dominant_mibig_accession}" if per_gene_anchor else ""
    return (
        PARTIALLY_CHARACTERIZED,
        f"{reason}; recognizable_gene_fraction={frac:.2f} "
        f"(<{WELL_FRACTION:.2f}) {denom}{anchor_txt}",
    )


def _note_for(cls: str) -> str:
    return CHARACTERIZED_NOTE if cls == WELL_CHARACTERIZED else NOVELTY_PRIOR_NOTE


def _read_kcb_map(triage_board_csv: str | Path | None) -> dict[str, str]:
    """bgc_id -> KCB_top string from a triage board, if present. Robust to missing column."""
    out: dict[str, str] = {}
    if not triage_board_csv or not Path(triage_board_csv).exists():
        return out
    with open(triage_board_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bgc = (row.get("BGC_ID") or row.get("bgc_id") or "").strip()
            if bgc:
                out[bgc] = row.get("KCB_top") or row.get("kcb_top") or ""
    return out


def rows_from_profile(mibig_profile_csv: str | Path,
                      triage_board_csv: str | Path | None = None) -> list[dict]:
    """Compute one reference-dark row per BGC from a sealed package's mibig_profile (+ triage board)."""
    kcb_map = _read_kcb_map(triage_board_csv)
    rows: list[dict] = []
    with open(mibig_profile_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            bgc = (r.get("bgc_id") or "").strip()
            if not bgc:
                continue
            kcb_top = kcb_map.get(bgc, "")
            cls, basis = classify_reference_dark(
                query_gene_count=r.get("query_gene_count"),
                recognizable_gene_count=r.get("recognizable_gene_count"),
                recognizable_gene_fraction=r.get("recognizable_gene_fraction"),
                dominant_mibig_accession=r.get("dominant_mibig_accession", ""),
                dominant_convergence_tier=r.get("dominant_convergence_tier", ""),
                interpretation_class=r.get("interpretation_class", ""),
                kcb_top=kcb_top,
            )
            rows.append({
                "bgc_id": bgc,
                "reference_dark_class": cls,
                "reference_dark_basis": basis,
                "query_gene_count": r.get("query_gene_count", ""),
                "recognizable_gene_count": r.get("recognizable_gene_count", ""),
                "recognizable_gene_fraction": r.get("recognizable_gene_fraction", ""),
                "dominant_mibig_accession": r.get("dominant_mibig_accession", ""),
                "kcb_anchor": _MIBIG_RE.search(str(kcb_top)).group(0) if _has_mibig(kcb_top) else "",
                "novelty_prior_note": _note_for(cls),
                "report_only_contract": REPORT_ONLY_CONTRACT,
            })
    return rows


def _find_one(package_dir: Path, suffix: str) -> Path | None:
    hits = sorted(glob.glob(str(package_dir / f"*{suffix}")))
    return Path(hits[0]) if hits else None


def compute_for_package(package_dir: str | Path, write: bool = True) -> tuple[list[dict], Path | None]:
    """Compute reference-dark priors for a sealed package directory.

    Returns (rows, output_csv_path). Locates `*_3_mibig_profile.csv` (required) and
    `*_4_triage_board.csv` (optional KCB channel) by glob. Writes
    `<strain>_3b_reference_dark_prior.csv` next to them when write=True.
    """
    package_dir = Path(package_dir)
    profile = _find_one(package_dir, "_3_mibig_profile.csv")
    if profile is None:
        raise FileNotFoundError(f"no *_3_mibig_profile.csv under {package_dir}")
    board = _find_one(package_dir, "_4_triage_board.csv")
    rows = rows_from_profile(profile, board)
    out_path = None
    if write:
        stem = profile.name.split("_3_mibig_profile.csv")[0]
        out_path = package_dir / f"{stem}_3b_reference_dark_prior.csv"
        write_csv(rows, out_path)
    return rows, out_path


def write_csv(rows: list[dict], out_path: str | Path) -> Path:
    # v9.7.374 fix: was a direct-to-final-path write. This is the sole write path for
    # `mamey reference-dark` (mamey/cli.py's registered subcommand) and is invoked automatically
    # by the autonomous `deliverable-queue` driver (mamey/deliverable_queue.py:73) for every
    # strain it processes. A crash/interrupt mid-write left a truncated
    # `<strain>_3b_reference_dark_prior.csv` under its real filename with no crash-safety, same
    # class of bug already fixed in `resistance_dossier.py`/`timing.py`/etc. this session.
    out_path = Path(out_path)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=CSV_HEADERS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_HEADERS})
    tmp_path.replace(out_path)
    return out_path


def summarize(rows: list[dict]) -> dict[str, int]:
    counts = {REFERENCE_DARK: 0, PARTIALLY_CHARACTERIZED: 0, WELL_CHARACTERIZED: 0}
    for r in rows:
        counts[r["reference_dark_class"]] = counts.get(r["reference_dark_class"], 0) + 1
    return counts


def _find_profiles(root: Path, depth: int) -> list[Path]:
    """All *_3_mibig_profile.csv under root, up to `depth` directory levels."""
    out: list[Path] = []
    root = Path(root)
    for d in range(depth + 1):
        pattern = os.path.join(str(root), *(["*"] * d), "*_3_mibig_profile.csv")
        out.extend(Path(p) for p in glob.glob(pattern))
    # dedupe, stable order
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in sorted(out):
        if str(p) not in seen:
            seen.add(str(p)); uniq.append(p)
    return uniq


def reference_dark_command(args) -> int:
    """Post-seal `reference-dark` subcommand: wire the previously-orphaned reference-dark
    novelty prior into a real deliverable. Non-blocking, report-only, non-ranking. Writes
    `<strain>_3b_reference_dark_prior.csv` into each package (or into --out DIR). NEW file
    only — pre-existing sealed files are left byte-identical (novelty PRIOR, not proof)."""
    root = Path(getattr(args, "root", ".") or ".")
    depth = int(getattr(args, "depth", 3) or 3)
    out_dir = getattr(args, "out", None)
    # If root itself is a package dir, use it directly; else recurse for profiles.
    direct = _find_one(root, "_3_mibig_profile.csv")
    profiles = [direct] if direct else _find_profiles(root, depth)
    if not profiles:
        emit(f"reference-dark: no *_3_mibig_profile.csv found under {root} (depth {depth})")
        return 0
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    npkg = 0
    total = 0
    for prof in profiles:
        pkg_dir = prof.parent
        board = _find_one(pkg_dir, "_4_triage_board.csv")
        try:
            rows = rows_from_profile(prof, board)
        except (ValueError, OSError) as exc:
            emit(f"reference-dark: {exc}")
            return 2
        stem = prof.name.split("_3_mibig_profile.csv")[0]
        target = (Path(out_dir) if out_dir else pkg_dir) / f"{stem}_3b_reference_dark_prior.csv"
        write_csv(rows, target)
        counts = summarize(rows)
        emit(f"reference-dark: {stem}: {counts} (n={len(rows)}) -> {target}")
        npkg += 1
        total += len(rows)
    emit(f"reference-dark: {npkg} package(s), {total} BGC row(s).")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Compute the non-ranking reference-dark novelty prior for a sealed package.")
    ap.add_argument("package_dir", help="path to a sealed package/ directory")
    ap.add_argument("--no-write", action="store_true", help="print summary only, do not write the CSV")
    args = ap.parse_args(argv)
    rows, out = compute_for_package(args.package_dir, write=not args.no_write)
    counts = summarize(rows)
    lines = [f"reference-dark prior for {args.package_dir}: {counts}  (n={len(rows)})"]
    if out:
        lines.append(f"wrote {out}")
    emit(*lines, sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
