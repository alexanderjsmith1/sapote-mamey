"""mamey.cohort_context — strain-level cohort context for the strain Mode B S5 (LQ-STRAIN-03).

Turns a BiG-SCAPE cohort (all AS + Type + SID strains in one GCF space) into the cross-cluster /
private-chemistry facts the strain-level Mode B S5 needs: for this strain, which BGCs sit in
strain-**private** GCFs (private chemistry) vs **shared** GCFs (and which other strains they share
with), and which are near a known MIBiG cluster (KNOWN) vs NOVEL.

It reuses the tested cohort readers already in the bundle (`tools/bigscape_ingest_to_mamey.py`:
`gcf_context` for the sqlite DB, `tsv_context` for the portable export, `load_triage` for the
BGC→locator bridge, `load_mibig_names`) rather than re-deriving the SQL. Source priority: the
sqlite DB (richest — carries co-members + nearest-MIBiG) is preferred; the portable TSV is the
fallback (co-members unavailable there, stated explicitly); with neither, the strain card stays in
single-strain mode and S5 says so.
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
from .bigscape_namespace import validate_membership_row

_TOOLS = Path(__file__).resolve().parent.parent / "tools" / "bigscape_ingest_to_mamey.py"


def _tools_mod():
    """Import tools/bigscape_ingest_to_mamey.py as a module (it is not an installed package)."""
    spec = importlib.util.spec_from_file_location("_bigscape_ingest_to_mamey", _TOOLS)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_TOOLS}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_private(entry: dict) -> bool:
    """A GCF the strain does not share with any other strain in the cohort = private chemistry."""
    n = entry.get("n_strains")
    if isinstance(n, int):
        return n <= 1
    co = entry.get("cross_strain_members")
    return bool(co is not None and len(co) == 0)


def strain_cohort_summary(pkg_dir, strain: str, cohort_db=None, cohort_tsv=None,
                          cutoff="0.5", mibig_index=None, run_id=None) -> dict | None:
    """Return a strain-level cohort summary for S5, or None if no cohort source resolves the strain.

    Keys: source, n_with_gcf, n_private, n_shared, n_known, n_novel, neighbours (Counter of the
    other strains sharing GCFs, most-common first), shared (top shared GCFs with co-members +
    nearest MIBiG), per_bgc ({bgc_number -> ctx entry} for S3 annotation / cross-card indexing).
    """
    if not cohort_db and not cohort_tsv:
        return None
    tm = _tools_mod()
    names = tm.load_mibig_names(mibig_index) if mibig_index else {}
    if cohort_db:
        ctx = tm.gcf_context(cohort_db, cutoff, names, run_id=run_id)
        source = "bigscape_db"
    else:
        ctx = tm.tsv_context(cohort_tsv, strain, cutoff)
        source = "portable_tsv"

    prefix = f"{strain}:"
    strain_ctx = {k: v for k, v in ctx.items() if k.startswith(prefix)}
    if not strain_ctx:
        return None

    # BGC-number -> ctx entry, via the triage board bridge (Contig + region -> canon locator)
    per_bgc: dict[str, dict] = {}
    pkg = Path(pkg_dir)
    triage = pkg / f"{strain}_4_triage_board.csv"
    if triage.exists():
        try:
            bridge = tm.load_triage(str(triage))
            for (s, num), loc in bridge.items():
                if s and s != strain:
                    continue
                key = f"{strain}:{loc}"
                if key in strain_ctx:
                    per_bgc[num] = strain_ctx[key]
        except Exception:
            per_bgc = {}

    neighbours: Counter = Counter()
    shared: list[dict] = []
    n_private = n_shared = n_known = n_novel = 0
    for key, e in strain_ctx.items():
        if str(e.get("status", "")).upper() == "KNOWN":
            n_known += 1
        else:
            n_novel += 1
        co = e.get("cross_strain_members")
        if _is_private(e):
            n_private += 1
        else:
            n_shared += 1
            if co:
                neighbours.update(co)
                nm = e.get("nearest_mibig")
                shared.append({
                    "locator": key.split(":", 1)[1],
                    "co_members": list(co),
                    "n_strains": e.get("n_strains"),
                    "status": e.get("status"),
                    "nearest_mibig": (nm[0] if isinstance(nm, (list, tuple)) and nm else None),
                    "nearest_mibig_name": (nm[1] if isinstance(nm, (list, tuple)) and len(nm) > 1 else None),
                })
    shared.sort(key=lambda r: (-(r["n_strains"] or 0), r["locator"]))
    return {
        "source": source,
        "n_with_gcf": len(strain_ctx),
        "n_private": n_private,
        "n_shared": n_shared,
        "n_known": n_known,
        "n_novel": n_novel,
        "neighbours": neighbours,
        "shared": shared[:8],
        "per_bgc": per_bgc,
        "co_members_available": source == "bigscape_db",
    }


def render_s5(summary: dict | None, strain: str) -> list[str]:
    """Render the S5 body lines from a cohort summary (or the single-strain fallback)."""
    if not summary:
        return [
            "_No cohort context supplied_ — pass `--cohort-db <full_cohort.db>` (or `--cohort-tsv`) "
            "to populate cross-cluster neighbours and private chemistry from the BiG-SCAPE cohort. "
            "Without it this is a single-strain view: uniqueness/private-chemistry can't be computed.",
        ]
    L = [
        f"**Cohort placement** (source: `{summary['source']}`, {summary['n_with_gcf']} of this "
        f"strain's BGCs placed in the GCF space): **{summary['n_private']} private** "
        f"(strain-unique GCF — candidate private chemistry) · **{summary['n_shared']} shared** · "
        f"**{summary['n_known']} KNOWN** (near a MIBiG cluster) / **{summary['n_novel']} NOVEL**.",
    ]
    if summary["neighbours"]:
        top = ", ".join(f"{s} ({n})" for s, n in summary["neighbours"].most_common(6))
        L.append(f"**Nearest cohort neighbours** (strains sharing the most GCFs): {top}.")
    elif not summary["co_members_available"]:
        L.append("_Co-members unavailable in the portable TSV export_ (no per-BGC family_id); "
                 "run with `--cohort-db` for the shared-strain list.")
    if summary["shared"]:
        L.append("")
        L.append("| shared GCF (locator) | in N strains | status | nearest MIBiG | co-members |")
        L.append("|---|--:|---|---|---|")
        for r in summary["shared"]:
            co = ", ".join(r["co_members"][:5]) + (" …" if len(r["co_members"]) > 5 else "")
            nm = r.get("nearest_mibig_name") or r.get("nearest_mibig") or "—"
            L.append(f"| {r['locator']} | {r['n_strains'] or '—'} | {r.get('status') or '—'} | {nm} | {co} |")
    L.append("")
    L.append("_Private GCFs are the strain's candidate private chemistry; shared GCFs place its "
             "capacity against the cohort. KCB/MIBiG names are similarity, not identity._")
    return L


def cross_card_gcf_index(card_summaries: dict[str, dict]) -> dict[str, list[tuple[str, str]]]:
    """Given {strain -> summary}, group BGCs by GCF family across cards so a BGC in one strain's
    card links to same-GCF BGCs in others' (the 'compare BGCs across cards' view). Returns
    {qualified_family_id -> [(strain, bgc_number), ...]} for families spanning >1."""
    fam: dict[str, list[tuple[str, str]]] = {}
    for strain, summ in (card_summaries or {}).items():
        if not summ:
            continue
        for num, e in (summ.get("per_bgc") or {}).items():
            if not e.get("family_id") and not e.get("qualified_family_id"):
                continue
            identity = validate_membership_row(e)
            if identity is None:
                continue
            fam.setdefault(identity.qualified_family_id, []).append((strain, num))
    return {k: sorted(set(v)) for k, v in fam.items() if len(set(v)) > 1}
