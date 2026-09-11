"""bgc_alias_history.py — legacy-id history for BGC ids across re-runs (v9.7.405).

Revives the one idea from the pre-Sapote-Mamey `mamey_identity.py` (June 2026) that the four-part
identity contract never carried: when a strain is RE-RUN (new antiSMASH version, new assembly
cut, changed merge settings) the locked `bgc_id` numbering can shift — the region a reader knew as
`BGC013` may now be `BGC034`. Nothing in the package records that, so cross-run citations rot
silently and a Mode B card written against the old id points at the wrong locus.

This module reconciles a CURRENT package against a PRIOR package of the SAME strain by physical
locus (contig / node + coordinate overlap), and emits `bgc_alias_history.json`:

    {"schema": "bgc_alias_history_v1", "strain": ..., "prior_package": ..., "current_package": ...,
     "aliases": {"BGC034": {"legacy_ids": ["BGC013"], "match": "OVERLAP", "overlap_fraction": 0.98}, ...},
     "unmatched_prior": ["BGC022"], "unmatched_current": ["BGC041"]}

It never renames anything, never touches `bgc_id` (locked at parse time, by contract), and makes
no scientific statement — it records which physical locus carried which id, so a citation can be
resolved. Library: no prints. Front door: tools/bgc_alias_history.py.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

__all__ = ["load_inventory", "reconcile", "write_history"]

_COORD_RX = re.compile(r"(\d+)\s*[-–:]\s*(\d+)")


def _int(v) -> int | None:
    try:
        return int(float(str(v).replace(",", "").strip()))
    except Exception:
        return None


def load_inventory(package_dir: str | Path) -> tuple[str, list[dict]]:
    """Read `<strain>_2_inventory.csv`; return (strain, rows with normalised locus fields).

    Locus = (contig-or-node key, start, end). Column names vary across engine generations, so
    several spellings are accepted; a row without a resolvable locus is kept with `locus=None`
    and can only be matched by identical id.
    """
    pkg = Path(package_dir)
    hits = sorted(pkg.glob("*_2_inventory.csv"))
    if not hits:
        raise FileNotFoundError(f"no *_2_inventory.csv in {pkg}")
    inv = hits[0]
    strain = inv.name.split("_2_inventory.csv")[0]
    with inv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        bid = (r.get("BGC_ID") or r.get("bgc_id") or "").strip()
        if not bid:
            continue
        key = (r.get("Node_ID") or r.get("node_id") or r.get("Contig") or r.get("contig") or "").strip()
        start = _int(r.get("Start") or r.get("start") or r.get("Region_start") or r.get("region_start"))
        end = _int(r.get("End") or r.get("end") or r.get("Region_end") or r.get("region_end"))
        if (start is None or end is None) and (r.get("Coordinates") or r.get("coordinates")):
            m = _COORD_RX.search(str(r.get("Coordinates") or r.get("coordinates")))
            if m:
                start, end = int(m.group(1)), int(m.group(2))
        locus = (key, min(start, end), max(start, end)) if key and start is not None and end is not None else None
        out.append({"bgc_id": bid, "locus": locus, "products": (r.get("Products") or r.get("products") or "").strip()})
    return strain, out


def _overlap_fraction(a: tuple, b: tuple) -> float:
    if a[0] != b[0]:
        return 0.0
    inter = max(0, min(a[2], b[2]) - max(a[1], b[1]))
    shorter = max(1, min(a[2] - a[1], b[2] - b[1]))
    return inter / shorter


def reconcile(prior_rows: list[dict], current_rows: list[dict], *, min_overlap: float = 0.5) -> dict:
    """Match current ids to prior ids by physical locus overlap (fraction of the shorter region).

    A prior id maps to at most one current id (best overlap wins, deterministic tie-break by id);
    identical ids on identical loci are recorded as `SAME`. Ids that cannot be placed are listed,
    never guessed.
    """
    aliases: dict[str, dict] = {}
    used_prior: set[str] = set()
    for cur in sorted(current_rows, key=lambda r: r["bgc_id"]):
        best, best_f = None, 0.0
        if cur["locus"] is not None:
            for pr in prior_rows:
                if pr["bgc_id"] in used_prior or pr["locus"] is None:
                    continue
                f = _overlap_fraction(cur["locus"], pr["locus"])
                if f > best_f or (f == best_f and best is not None and f > 0 and pr["bgc_id"] < best["bgc_id"]):
                    best, best_f = pr, f
        if best is not None and best_f >= min_overlap:
            used_prior.add(best["bgc_id"])
            kind = "SAME" if best["bgc_id"] == cur["bgc_id"] else "RENUMBERED"
            aliases[cur["bgc_id"]] = {"legacy_ids": [] if kind == "SAME" else [best["bgc_id"]],
                                      "match": kind, "overlap_fraction": round(best_f, 3),
                                      "prior_products": best["products"], "current_products": cur["products"]}
        else:
            aliases[cur["bgc_id"]] = {"legacy_ids": [], "match": "NEW_OR_UNPLACED", "overlap_fraction": 0.0,
                                      "prior_products": "", "current_products": cur["products"]}
    unmatched_prior = sorted(r["bgc_id"] for r in prior_rows if r["bgc_id"] not in used_prior)
    unmatched_current = sorted(k for k, v in aliases.items() if v["match"] == "NEW_OR_UNPLACED")
    renumbered = sorted(k for k, v in aliases.items() if v["match"] == "RENUMBERED")
    return {"schema": "bgc_alias_history_v1", "min_overlap": min_overlap, "aliases": aliases,
            "renumbered": renumbered, "unmatched_prior": unmatched_prior,
            "unmatched_current": unmatched_current,
            "note": ("Physical-locus reconciliation only: which locus carried which id across two runs of the "
                     "same strain. Ids are never renamed; no product, class, novelty, or activity claim.")}


def write_history(current_package: str | Path, history: dict, name: str = "bgc_alias_history.json") -> Path:
    out = Path(current_package) / name
    out.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
    return out
