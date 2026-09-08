#!/usr/bin/env python3
"""evidence_bundle.py — per-BGC evidence bundle assembled from a SEALED Mamey package (P360-001 / Idea D).

Reader-side, NON-SCORING, deterministic. For each BGC in a sealed package it assembles every evidence
channel the package already emits — MIBiG convergence, MIBiG novelty profile, per-gene ClusterBlast, RG-GMCI
split-pathway pairs, and the .359 `_4D` two-proof rescue verdict — into one JSON + a Markdown
`## Evidence Summary` block. This is the machine-readable spine four chats asked for independently
(a contributor lane PATCH 2, the patch lane Idea D, the integration lane CARD_2 renderer, a contributor lane Mode-B integration-evidence).

It changes NO score and emits NO new package artifact into the sealed package — it is a post-seal consumer,
run against an already-sealed `package/` directory. External BLASTp channels (nr / SwissProt) are intentionally
NOT read here: this bundle is deterministic and package-internal; the BLASTp Repository overlay is a separate,
non-deterministic layer (see the P358-002 registry rule) and would break reproducibility if folded in.

DEFICIT SEMANTICS (the "unmeasured flag != finding" rule — flag-vs-finding, do not confuse absence with negation):
  * PRESENT          — the channel file exists AND carries a row for this BGC.
  * ABSENT_NO_ROWS   — the channel file exists but has no row for this BGC (scanned, none matched).
  * ABSENT_NO_FILE   — the channel file was not produced in this package (NOT measured — never "no evidence exists").

CLAIM-SAFETY (carried on every bundle): KCB/MIBiG names are class-level similarity, NOT identity; RG-GMCI /
`_4D` are homology-guided CANDIDATES, not merges or nucleotide joins; novelty tiers are priors, judgment deferred.

CLI:
  python -m tools.evidence_bundle <package_dir> [--strain AS-XXX] --out <dir>
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text  # noqa: E402 -- AUDIT_374 atomic-write fix


# ── schema-tolerant helpers ─────────────────────────────────────────────────────────────────
def _read_csv(path: Path) -> list[dict] | None:
    """Return rows as dicts, or None if the file does not exist (ABSENT_NO_FILE)."""
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def _col(fieldnames: Iterable[str], *patterns: str) -> str | None:
    """First fieldname matching any regex (case-insensitive). Lets the reader survive header drift."""
    fields = list(fieldnames or [])
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for f in fields:
            if rx.search(f or ""):
                return f
    return None


def _short_contig(v: str) -> str:
    m = re.search(r"(NODE_\d+)", v or "")
    return m.group(1) if m else (v or "")


def _find_package_csv(package_dir: Path, suffix: str) -> Path:
    """Locate `*{suffix}` in the package (strain prefix varies). Returns a (maybe non-existent) Path."""
    hits = sorted(package_dir.glob(f"*{suffix}"))
    return hits[0] if hits else (package_dir / f"UNKNOWN{suffix}")


def _strain_from_package(package_dir: Path) -> str:
    inv = sorted(package_dir.glob("*_2_inventory.csv"))
    if inv:
        m = re.match(r"(.+?)_2_inventory\.csv$", inv[0].name)
        if m:
            return m.group(1)
    return package_dir.name


# ── channel assembly ────────────────────────────────────────────────────────────────────────
def _index_by_bgc(rows: list[dict] | None, *bgc_patterns: str) -> tuple[dict[str, list[dict]], str | None]:
    """Group rows by their BGC-id column. Returns ({bgc_id: [rows]}, column_used)."""
    if rows is None:
        return {}, None
    col = _col(rows[0].keys(), *bgc_patterns) if rows else None
    out: dict[str, list[dict]] = {}
    if col:
        for r in rows:
            out.setdefault((r.get(col) or "").strip(), []).append(r)
    return out, col


def _pairs_touching(rows: list[dict] | None, bgc_id: str) -> list[dict]:
    """RG-GMCI / _4D rows where either partner is this BGC."""
    if rows is None:
        return []
    a = _col(rows[0].keys(), r"^bgc_a$", r"bgc_a", r"^a$") if rows else None
    b = _col(rows[0].keys(), r"^bgc_b$", r"bgc_b", r"^b$") if rows else None
    if not (a and b):
        return []
    return [r for r in rows if (r.get(a) or "").strip() == bgc_id or (r.get(b) or "").strip() == bgc_id]


def _deficit(file_rows: list[dict] | None, has_rows: bool) -> str:
    if file_rows is None:
        return "ABSENT_NO_FILE"
    return "PRESENT" if has_rows else "ABSENT_NO_ROWS"


# ── BB360 evidence-join extensions (a contributor lane BB16, folded 2026-08-11) ───────────────────
def _top_family(rows: list[dict] | None) -> str | None:
    """Most-frequent compound/family name across rows (the dominant per-gene read)."""
    if not rows:
        return None
    col = _col(rows[0].keys(), r"compound", r"family", r"mibig.*name", r"^name$")
    if not col:
        return None
    from collections import Counter
    c = Counter((r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip())
    return c.most_common(1)[0][0] if c else None


def _channels_agree(dominant_rows: list[dict] | None, graded_rows: list[dict] | None) -> str:
    """Compare the dominant per-gene MIBiG family against the graded anchor.
    AGREE / DISAGREE / ONE_CHANNEL_ONLY — never asserts either is correct (two-channels rule)."""
    a = _top_family(dominant_rows)
    b = _top_family(graded_rows)
    if a and b:
        return "AGREE" if a.lower() == b.lower() else "DISAGREE"
    return "ONE_CHANNEL_ONLY"


def _unmeasured_fields(row_lists: dict[str, list[dict]]) -> list[str]:
    """`channel.column` names that are empty in an EXISTING row — a row-level gap the file-level
    ABSENT_NO_FILE deficit cannot see ('scanned, nothing found' vs 'not scanned')."""
    out = []
    for ch, rows in row_lists.items():
        for r in rows or []:
            for k, v in r.items():
                if k and (v is None or str(v).strip() == ""):
                    tag = f"{ch}.{k}"
                    if tag not in out:
                        out.append(tag)
    return sorted(out)


def _antismash_strictness(package_dir: Path) -> str:
    """RELAXED/STRICT/loose provenance from the package manifest; UNKNOWN if not recorded."""
    mf = _find_package_csv(package_dir, "manifest.json")
    if not mf.exists():
        hits = sorted(package_dir.glob("*manifest*.json"))
        mf = hits[0] if hits else mf
    if mf.exists():
        try:
            blob = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
            for key in ("antismash_strictness", "strictness", "antismash_mode", "run_mode", "mode"):
                v = blob.get(key) if isinstance(blob, dict) else None
                if v:
                    return str(v)
        except (json.JSONDecodeError, OSError):
            pass
    return "UNKNOWN"


def build_evidence_bundle(package_dir: Path | str, strain: str | None = None) -> dict:
    package_dir = Path(package_dir)
    strain = strain or _strain_from_package(package_dir)

    inventory = _read_csv(_find_package_csv(package_dir, "_2_inventory.csv"))
    convergence = _read_csv(_find_package_csv(package_dir, "_3_mibig_convergence.csv"))
    profile = _read_csv(_find_package_csv(package_dir, "_3_mibig_profile.csv"))
    per_gene_cb = _read_csv(_find_package_csv(package_dir, "_4A2_ClusterBlast_per_gene.csv"))
    rggmci = _read_csv(_find_package_csv(package_dir, "_4A_RGGMCI_ranked_pairs.csv"))
    two_proof = _read_csv(_find_package_csv(package_dir, "_4D_two_proof_rescue.csv"))
    graded = _read_csv(_find_package_csv(package_dir, "nr_vs_MIBiG_per_bgc.csv"))  # BB16 graded anchor
    strictness = _antismash_strictness(package_dir)                                # BB16 provenance

    conv_by, _ = _index_by_bgc(convergence, r"bgc_id", r"^bgc$", r"query.*bgc")
    prof_by, _ = _index_by_bgc(profile, r"bgc_id", r"^bgc$")
    cb_by, _ = _index_by_bgc(per_gene_cb, r"bgc_id", r"^bgc$")
    graded_by, _ = _index_by_bgc(graded, r"bgc_id", r"^bgc$", r"query.*bgc")

    if inventory is None:
        raise ValueError(f"no *_2_inventory.csv in {package_dir} — not a sealed Mamey package")
    inv_bgc = _col(inventory[0].keys(), r"bgc_id", r"^bgc$") if inventory else None

    bgcs: dict[str, dict] = {}
    for row in inventory:
        bid = (row.get(inv_bgc) or "").strip() if inv_bgc else ""
        if not bid:
            continue
        conv = conv_by.get(bid, [])
        prof = prof_by.get(bid, [])
        cb = cb_by.get(bid, [])
        rg = _pairs_touching(rggmci, bid)
        tp = _pairs_touching(two_proof, bid)
        gr = graded_by.get(bid, [])
        # two-proof verdict summary (advisory)
        tp_verdicts = sorted({(r.get("verdict") or "").strip() for r in tp if (r.get("verdict") or "").strip()})
        bgcs[bid] = {
            "bgc_id": bid,
            "identity": {k: row.get(k) for k in row if k},  # the full inventory row, verbatim
            # BB16 extensions: two-channel MIBiG reconciliation + row-level gap list (do NOT change deficit semantics)
            "channels_agree": _channels_agree(conv, gr),
            "unmeasured_fields": _unmeasured_fields(
                {"mibig_convergence": conv, "mibig_novelty_profile": prof, "per_gene_clusterblast": cb}),
            "channels": {
                "mibig_convergence": {"deficit": _deficit(convergence, bool(conv)), "n_rows": len(conv), "rows": conv},
                "mibig_novelty_profile": {"deficit": _deficit(profile, bool(prof)), "rows": prof},
                "per_gene_clusterblast": {"deficit": _deficit(per_gene_cb, bool(cb)), "n_gene_hits": len(cb)},
                "rggmci_pairs": {"deficit": _deficit(rggmci, bool(rg)), "n_pairs": len(rg), "pairs": rg},
                "two_proof_rescue": {"deficit": _deficit(two_proof, bool(tp)), "verdicts": tp_verdicts, "rows": tp},
                "mibig_graded_anchor": {"deficit": _deficit(graded, bool(gr)), "n_rows": len(gr), "rows": gr},
            },
        }

    present = {ch for b in bgcs.values() for ch, v in b["channels"].items() if v["deficit"] == "PRESENT"}
    return {
        "schema": "sapote-evidence-bundle-v1",
        "strain": strain,
        "package_dir": str(package_dir),
        "bgc_count": len(bgcs),
        "channels_present_somewhere": sorted(present),
        "antismash_strictness": strictness,   # BB16: which run generated the package (RELAXED adds regions)
        "bgcs": bgcs,
        "claim_safety": [
            "Deficit ABSENT_NO_FILE means a channel was NOT MEASURED in this package — never 'no evidence exists'.",
            "MIBiG/KCB names are class-level SIMILARITY, not identity; novelty tiers are priors — judgment deferred.",
            "RG-GMCI and _4D two-proof rows are homology-guided CANDIDATES, not merges or nucleotide joins.",
            "This bundle assigns no score and promotes no tier; it re-presents the package's own evidence.",
            "channels_agree=DISAGREE means two MIBiG channels named different families — a flag to adjudicate, "
            "not a correction; unmeasured_fields lists SCANNED-BUT-EMPTY columns (row-level gaps), distinct from "
            "ABSENT_NO_FILE (channel not produced).",
        ],
    }


# ── output ──────────────────────────────────────────────────────────────────────────────────
def _md_for_bgc(b: dict) -> str:
    ch = b["channels"]
    lines = [f"## Evidence Summary — {b['bgc_id']}", ""]

    def stat(name: str, key: str) -> str:
        return f"- **{name}:** {ch[key]['deficit']}"

    conv = ch["mibig_convergence"]
    lines.append(f"- **MIBiG convergence:** {conv['deficit']}"
                 + (f" ({conv['n_rows']} rows)" if conv["deficit"] == "PRESENT" else ""))
    lines.append(stat("MIBiG novelty profile", "mibig_novelty_profile"))
    cb = ch["per_gene_clusterblast"]
    lines.append(f"- **Per-gene ClusterBlast:** {cb['deficit']}"
                 + (f" ({cb['n_gene_hits']} gene hits)" if cb["deficit"] == "PRESENT" else ""))
    rg = ch["rggmci_pairs"]
    lines.append(f"- **RG-GMCI split pairs:** {rg['deficit']}"
                 + (f" ({rg['n_pairs']} pairs)" if rg["deficit"] == "PRESENT" else ""))
    tp = ch["two_proof_rescue"]
    lines.append(f"- **Two-proof rescue (_4D):** {tp['deficit']}"
                 + (f" — {', '.join(tp['verdicts'])}" if tp["verdicts"] else ""))
    lines.append("")
    lines.append("_Class-level similarity, not identity; candidates for adjudication; judgment deferred._")
    return "\n".join(lines)


def write_evidence_bundle(bundle: dict, out_dir: Path | str) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # AUDIT_374: was a plain .write_text() -- a killed process mid-write left a
    # truncated/unparseable JSON or MD deliverable on disk with no signal it was incomplete.
    # atomic_write_text writes to a sibling .tmp and os.replace()s it into place.
    atomic_write_text(out_dir / f"{bundle['strain']}_evidence_bundle.json",
                       json.dumps(bundle, indent=2, sort_keys=True))
    md_parts = [f"# Evidence bundle — {bundle['strain']} ({bundle['bgc_count']} BGCs)", "",
                "> Reader-side, non-scoring. Deficit `ABSENT_NO_FILE` = not measured, not absence of biology.", ""]
    for bid in sorted(bundle["bgcs"]):
        md_parts.append(_md_for_bgc(bundle["bgcs"][bid]))
        md_parts.append("")
    atomic_write_text(out_dir / f"{bundle['strain']}_evidence_bundle.md", "\n".join(md_parts))
    return {"json": f"{bundle['strain']}_evidence_bundle.json",
            "md": f"{bundle['strain']}_evidence_bundle.md", "bgc_count": bundle["bgc_count"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("package_dir", type=Path)
    ap.add_argument("--strain", default=None)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    bundle = build_evidence_bundle(args.package_dir, args.strain)
    summary = write_evidence_bundle(bundle, args.out)
    emit(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
