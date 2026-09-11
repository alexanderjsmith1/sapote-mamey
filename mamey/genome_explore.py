#!/usr/bin/env python3
"""
mamey.genome_explore — efficient, question-driven genome exploration mode.

`explain` narrates a package and `list-bgcs` inventories it; neither answers the
question a user actually explores with: *what here is distinctive vs. genus-common,
and where should I look first?* This module adds that layer with lightweight
scanners that run over a sealed package (no re-extraction):

  scan_divergence(pkg)   per-BGC conservation median (nr-preferred, ClusterBlast
                         fallback) -> ranks the genuinely DIVERGENT loci above the
                         genus-conserved accessory clusters. Operationalises the
                         readiness-gate conservation signal as an exploration axis:
                         the fix for "everything got called novel."
  scan_co_capture(pkg)   flags BGCs whose antiSMASH region likely swept in
                         non-biosynthetic passengers (toxin-antitoxin, ribonucleotide
                         reductase, glycoside hydrolase, bare transport operons) so
                         exploration focuses on the real cluster, not the region call.
  exploration_board(pkg) reconciles score + divergence + boundary quality + resistance
                         coupling into an honest "look here first" ranking (a conserved
                         high-AB cluster ranks below a divergent one for discovery).

Consumed by `mamey explore <package>` (CLI wiring in cli.py — see the patch diff).
All read-only; deterministic; capacity-language only in any emitted prose.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
    from .exact_identity import (
        ExactLocusIdentityError,
        exact_locus_from_mapping,
        exact_locus_from_native_manifest_bgc,
    )
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
    from mamey.exact_identity import (
        ExactLocusIdentityError,
        exact_locus_from_mapping,
        exact_locus_from_native_manifest_bgc,
    )
import statistics
import csv
import json
import math
import stat
from pathlib import Path
from statistics import median
from typing import Any

# passenger (non-biosynthetic) domain/product signatures for the co-capture scan
_PASSENGER_HINTS = (
    "toxin", "antitoxin", "yoeb", "pare", "phdyefm", "relbe",        # TA systems
    "ribonucleotide reductase", "ribonuc_red", "atp-cone",           # RNR
    "glyco_hydro", "glycoside hydrolase", "trehalase",               # GH housekeeping
    "pentapeptide", "lsr2", "parbc", "transposase", "integrase",     # mobile / nucleoid
)


def _load_manifest(pkg: Path) -> dict:
    p = pkg / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _bgc_records(man: dict) -> dict[str, dict]:
    return {b.get("bgc_id"): b for b in man.get("bgcs", []) if b.get("bgc_id")}


def _presentation_identity_index(man: dict) -> dict[str, str]:
    """Validate every raw manifest BGC before public presentation indexing.

    Low-level conservation scans intentionally remain keyed by their source lookup
    tokens. Human and JSON presentation is stricter: current manifest producer rows
    must carry one complete, conflict-free identity whose ``bgc_id`` is the admitted
    secondary alias. Validation happens before ``_bgc_records`` can drop a missing key
    or collapse duplicate keys.
    """
    records = man.get("bgcs", [])
    if not isinstance(records, list):
        raise ExactLocusIdentityError(
            "manifest bgcs must be a list; exploration presentation identity is fail-closed"
        )
    identities: dict[str, str] = {}
    physical_identities: set[str] = set()
    for position, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ExactLocusIdentityError(
                f"manifest BGC record {position} must be an object; "
                "exploration presentation identity is fail-closed"
            )
        if "node_id" in record:
            exact_locus = exact_locus_from_native_manifest_bgc(
                man.get("strain_id"), record
            ).exact_locus
        else:
            exact_locus = exact_locus_from_mapping(man.get("strain_id"), record)
        raw_alias = record.get("bgc_id")
        if not isinstance(raw_alias, str) or not raw_alias.strip():
            raise ExactLocusIdentityError(
                f"manifest BGC record {position} is missing producer bgc_id; "
                "exploration presentation identity is fail-closed"
            )
        alias = raw_alias.strip()
        if exact_locus.rsplit(" / ", 1)[-1] != alias:
            raise ExactLocusIdentityError(
                f"manifest BGC record {position} has conflicting BGC alias values"
            )
        if alias in identities:
            raise ExactLocusIdentityError(
                f"duplicate producer BGC alias at manifest record {position}; "
                "exploration presentation identity is fail-closed"
            )
        physical_identity = exact_locus.rsplit(" / ", 1)[0]
        if physical_identity in physical_identities:
            raise ExactLocusIdentityError(
                f"duplicate physical strain/node-or-contig/region identity at manifest "
                f"record {position}; exploration presentation identity is fail-closed"
            )
        identities[alias] = exact_locus
        physical_identities.add(physical_identity)
    return identities


def _presentation_rows(rows: list[dict], identities: dict[str, str]) -> list[dict]:
    """Attach the owner-admitted display without altering low-level row contracts."""
    presented = []
    for position, row in enumerate(rows, 1):
        alias = row.get("bgc_id")
        if alias not in identities:
            raise ExactLocusIdentityError(
                f"no admitted exact-locus identity for exploration row {position}"
            )
        presented.append({**row, "exact_locus": identities[alias]})
    return presented


def _exploration_presentation(package: str | Path, top: int = 8) -> dict[str, list[dict]]:
    """Build all public explore views after validating the raw manifest identity set."""
    pkg = Path(package)
    identities = _presentation_identity_index(_load_manifest(pkg))
    return {
        "exploration_board": _presentation_rows(exploration_board(pkg)[:top], identities),
        "divergence": _presentation_rows(scan_divergence(pkg), identities),
        "co_capture": _presentation_rows(scan_co_capture(pkg), identities),
    }


def _gene_context(pkg: Path) -> dict[str, list]:
    out: dict[str, list] = {}
    gc = next(pkg.glob("*gene_context.jsonl"), None)
    if not gc:
        return out
    for line in gc.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("bgc_id"):
            out[r["bgc_id"]] = r.get("cds", [])
    return out


def _conservation_background_observation(pkg: Path) -> dict:
    """Return the admitted genome-wide nr background and its evidence status."""
    ids: list[float] = []
    d = pkg / "blastp_online"
    try:
        mode = d.stat().st_mode
    except FileNotFoundError:
        return {"median_id": None, "n_genes": 0, "source": "none",
                "status": "UNAVAILABLE", "invalid_source": None}
    except OSError:
        return {"median_id": None, "n_genes": 0, "source": "none",
                "status": "INVALID", "invalid_source": "nr"}
    if not stat.S_ISDIR(mode):
        return {"median_id": None, "n_genes": 0, "source": "none",
                "status": "INVALID", "invalid_source": "nr"}
    try:
        overlay_files = sorted(
            entry for entry in d.iterdir() if entry.name.endswith("_online_blastp.csv")
        )
    except OSError:
        return {"median_id": None, "n_genes": 0, "source": "none",
                "status": "INVALID", "invalid_source": "nr"}
    for f in overlay_files:
        observation = _nr_observation_from_file(f)
        if observation["status"] == "INVALID":
            return {"median_id": None, "n_genes": 0, "source": "none",
                    "status": "INVALID", "invalid_source": "nr"}
        ids.extend(observation["identities"])
    if not ids:
        return {"median_id": None, "n_genes": 0, "source": "none",
                "status": "UNAVAILABLE", "invalid_source": None}
    return {"median_id": statistics.median(ids), "n_genes": len(ids), "source": "nr",
            "status": "ADMITTED", "invalid_source": None}


def conservation_background(pkg: Path) -> tuple[float | None, int]:
    """Genome-wide median of per-gene closest-hit %identity across every BGC overlay in the package.

    v9.7.240. Why this exists: `_conservation_median` reports the median rank-1 identity for one BGC, and
    `NOVELTY_CONTRADICTION` fires when that median >= 90%. But rank-1 identity against nr measures *"has a
    close relative been sequenced"*, not *"is this cluster distinctive"*. On AS-XXX, whose sister species
    (Streptosporangium saharense) is deposited in nr, all 36 BGC overlays land at 92.1-98.6% median — the
    guard fires 36/36 and discriminates nothing. The background median is the reference the per-BGC value
    must be read against: a BGC is distinctive when it sits well BELOW its own genome's background, not
    below an absolute constant. Returns (background_median, n_genes). The tuple API is retained
    for callers that only need the admitted value. Consumers that distinguish unavailable from
    invalid evidence use `_conservation_background_observation`.
    """
    observation = _conservation_background_observation(pkg)
    return observation["median_id"], observation["n_genes"]


def conservation_saturated(pkg: Path, floor: float = 90.0) -> bool:
    """True when the genome-wide background itself clears the novelty floor — i.e. a near-relative is in
    the reference DB, so per-BGC medians carry no novelty signal and NOVELTY_CONTRADICTION is uninformative.
    Callers should report the background alongside any novelty verdict rather than suppress the finding."""
    bg, n = conservation_background(pkg)
    return bg is not None and n > 0 and bg >= floor


def _admit_identity_percentage(value) -> tuple[float | None, str]:
    """Classify one identity field without turning corrupt input into evidence."""
    if value is None:
        return None, "UNAVAILABLE"
    if isinstance(value, str):
        value = value.strip()
        if not value or value.upper() == "NO_HIT":
            return None, "UNAVAILABLE"
    if isinstance(value, bool):
        return None, "INVALID"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, "INVALID"
    if not math.isfinite(number) or not 0.0 <= number <= 100.0:
        return None, "INVALID"
    return number, "ADMITTED"


def _observation_from_rows(rows, source: str, organism_keys=()) -> dict:
    """Admit one source as a whole; any invalid row invalidates the observation."""
    identities: list[float] = []
    multispecies_hits = 0
    invalid = False
    for row in rows:
        if not isinstance(row, dict):
            invalid = True
            continue
        identity, status = _admit_identity_percentage(row.get("pct_identity"))
        if status == "INVALID":
            invalid = True
            continue
        if status != "ADMITTED":
            continue
        identities.append(identity)
        if any(row.get(key) and any(
                marker in str(row[key]) for marker in ("MULTISPECIES", "unclassified"))
                for key in organism_keys):
            multispecies_hits += 1
    if invalid:
        return {"median_id": None, "n_genes": 0, "multispecies_hits": 0,
                "source": "none", "status": "INVALID", "invalid_source": source,
                "identities": []}
    if not identities:
        return {"median_id": None, "n_genes": 0, "multispecies_hits": 0,
                "source": "none", "status": "UNAVAILABLE", "invalid_source": None,
                "identities": []}
    return {"median_id": round(median(identities), 1), "n_genes": len(identities),
            "multispecies_hits": multispecies_hits, "source": source,
            "status": "ADMITTED", "invalid_source": None, "identities": identities}


def _nr_observation_from_file(path: Path) -> dict:
    """Strictly stream one full-nr CSV into the shared observation admission policy."""
    invalid = {"median_id": None, "n_genes": 0, "multispecies_hits": 0,
               "source": "none", "status": "INVALID", "invalid_source": "nr",
               "identities": []}
    try:
        if path.stat().st_size == 0:
            return _observation_from_rows((), "nr", ("blastp_organism",))
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames
            if (headers is None or headers.count("pct_identity") != 1
                    or len(headers) != len(set(headers))):
                return invalid

            def admitted_nr_rows():
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise csv.Error("inconsistent CSV row width")
                    channel = str(row.get("channel") or "").strip().lower()
                    source_channel = str(row.get("source_channel") or "").strip().lower()
                    if channel and source_channel and channel != source_channel:
                        raise csv.Error("conflicting channel declarations")
                    declared = channel or source_channel
                    if not declared:
                        raise csv.Error("legacy channel provenance is unbound")
                    if declared != "nr":
                        raise csv.Error("non-nr row in full-nr observation")
                    yield row

            return _observation_from_rows(admitted_nr_rows(), "nr", ("blastp_organism",))
    except (OSError, UnicodeError, csv.Error):
        return invalid


def _conservation_observation(pkg: Path, man: dict, bgc: str) -> dict:
    """Return the one admitted conservation observation and its actual source."""
    nr_csv = pkg / "blastp_online" / f"{bgc}_online_blastp.csv"
    if nr_csv.exists():
        observation = _nr_observation_from_file(nr_csv)
        if observation["status"] != "UNAVAILABLE":
            return observation

    from .scan_channel_alias import resolve_scan_channel  # v9.7.400 channel-alias stubs
    cbg = resolve_scan_channel(man.get("source_scans", {}) or {}, "clusterblast_genes", pkg) or {}
    rows = (cbg.get("per_gene_best_hit", {}) or {}).get(bgc, []) or []
    return _observation_from_rows(
        rows, "clusterblast", ("reference_organism", "organism", "reference"))


def _conservation_median(pkg: Path, man: dict, bgc: str) -> tuple[float | None, int, int]:
    """Per-gene closest-hit %identity median for a BGC. nr (blastp_online) preferred over
    ClusterBlast (its narrow reference set understates conservation). Returns
    (median_id, n_genes, multispecies_hits)."""
    observation = _conservation_observation(pkg, man, bgc)
    return (observation["median_id"], observation["n_genes"],
            observation["multispecies_hits"])


def scan_divergence(package: str | Path) -> list[dict]:
    """Rank BGCs by how divergent they are from their closest database relatives.
    Low median identity = genuinely distinctive (discovery-relevant); high = genus-conserved."""
    pkg = Path(package)
    man = _load_manifest(pkg)
    out = []
    for bgc, rec in _bgc_records(man).items():
        observation = _conservation_observation(pkg, man, bgc)
        med = observation["median_id"]
        n = observation["n_genes"]
        ms = observation["multispecies_hits"]
        src = observation["source"]
        # Divergence is only trustworthy from nr (all-GenBank). ClusterBlast LOW identity is
        # NOT trustworthy divergence — its narrow reference set made genus-conserved BGC043
        # look 62% when nr says 100%. ClusterBlast HIGH identity IS trustworthy conservation.
        if med is None:
            tier = "NO_EVIDENCE"
        elif src == "nr":
            tier = "DIVERGENT" if med < 70 else "VARIABLE" if med < 90 else "GENUS_CONSERVED"
        else:  # clusterblast
            tier = "GENUS_CONSERVED" if med >= 90 else "UNCONFIRMED_CHECK_NR"
        out.append({
            "bgc_id": bgc,
            "node_region": f"{rec.get('contig','?')} · r{rec.get('region_number','?')}",
            "products": rec.get("products"),
            "median_id": med,
            "n_genes": n,
            "multispecies_hits": ms,
            "divergence_tier": tier,
            "source": src,
            "source_status": observation["status"],
            "invalid_source": observation["invalid_source"],
        })
    out.sort(key=lambda r: (r["median_id"] if r["median_id"] is not None else 999))
    return out


def scan_co_capture(package: str | Path) -> list[dict]:
    """Flag BGCs likely carrying non-biosynthetic passengers swept into the antiSMASH region."""
    pkg = Path(package)
    gc = _gene_context(pkg)
    man = _load_manifest(pkg)
    recs = _bgc_records(man)
    out = []
    for bgc, cds in gc.items():
        passengers = []
        for g in cds:
            blob = (" ".join(g.get("sec_met_domains") or []) + " "
                    + (g.get("product") or "") + " " + (g.get("gene_functions") or "")).lower()
            for hint in _PASSENGER_HINTS:
                if hint in blob:
                    passengers.append((g.get("locus_tag"), hint))
                    break
        if passengers:
            rec = recs.get(bgc, {})
            out.append({
                "bgc_id": bgc,
                "node_region": f"{rec.get('contig','?')} · r{rec.get('region_number','?')}",
                "n_passengers": len(passengers),
                "passenger_genes": [p[0] for p in passengers][:8],
                "passenger_kinds": sorted({p[1] for p in passengers}),
                "note": "region likely wider than the true cluster; exclude these from the pathway read",
            })
    out.sort(key=lambda r: -r["n_passengers"])
    return out


def exploration_board(package: str | Path) -> list[dict]:
    """Honest 'look here first' ranking: divergence + capacity score + boundary quality +
    resistance coupling. A conserved high-score cluster ranks below a divergent one for
    discovery; a resistance-coupled or divergent lead is promoted."""
    pkg = Path(package)
    man = _load_manifest(pkg)
    recs = _bgc_records(man)
    div = {d["bgc_id"]: d for d in scan_divergence(pkg)}
    rescoup = (man.get("resistance_gene_summary", {}) or {}).get("bgc_coupling", {}) or {}
    rows = []
    for bgc, rec in recs.items():
        d = div.get(bgc, {})
        med = d.get("median_id")
        tier = d.get("divergence_tier")
        ab = rec.get("ab_score") or 0
        af = rec.get("af_score") or 0
        # reward only nr-CONFIRMED divergence; unconfirmed (ClusterBlast-only) gets a smaller,
        # provisional bump so it surfaces for an nr check without being over-promoted.
        if tier == "DIVERGENT":
            div_bonus = 40
        elif tier == "UNCONFIRMED_CHECK_NR":
            div_bonus = 10
        elif tier == "VARIABLE":
            div_bonus = 15
        else:
            div_bonus = 0
        res_bonus = 15 if rescoup.get(bgc) else 0
        interest = round(max(ab, af) * 0.5 + div_bonus + res_bonus, 1)
        rows.append({
            "bgc_id": bgc,
            "node_region": f"{rec.get('contig','?')} · r{rec.get('region_number','?')}",
            "products": rec.get("products"),
            "exploration_interest": interest,
            "divergence_tier": d.get("divergence_tier"),
            "median_id": med,
            "source_status": d.get("source_status"),
            "invalid_source": d.get("invalid_source"),
            "ab": ab, "af": af,
            "resistance_coupled": bool(rescoup.get(bgc)),
            "boundary": rec.get("edge_status"),
            "why": _why(d.get("divergence_tier"), max(ab, af), bool(rescoup.get(bgc)),
                        source_status=d.get("source_status"),
                        invalid_source=d.get("invalid_source")),
        })
    rows.sort(key=lambda r: -r["exploration_interest"])
    return rows


def _why(tier: str | None, score: float, res: bool, *,
         source_status: str | None = None, invalid_source: str | None = None) -> str:
    bits = []
    status = str(source_status or "").strip().upper()
    if status == "INVALID":
        source = str(invalid_source or "conservation source").strip()
        bits.append(f"{source} conservation evidence INVALID (no divergence conclusion)")
    elif tier == "NO_EVIDENCE":
        bits.append("conservation evidence UNAVAILABLE (no divergence conclusion)")
    elif tier == "DIVERGENT":
        bits.append("genuinely divergent from database relatives (discovery lead)")
    elif tier == "GENUS_CONSERVED":
        bits.append("genus-conserved (capacity, not novelty)")
    if score >= 60:
        bits.append("high capacity score")
    if res:
        bits.append("resistance-coupled (bioactivity hypothesis)")
    return "; ".join(bits) or "baseline"


def render_explore(package: str | Path, top: int = 8) -> str:
    """Plain-text exploration summary for `mamey explore`."""
    presentation = _exploration_presentation(package, top=top)
    board = presentation["exploration_board"]
    alldiv = presentation["divergence"]
    conf = [d for d in alldiv if d["divergence_tier"] == "DIVERGENT"]
    unconf = [d for d in alldiv if d["divergence_tier"] == "UNCONFIRMED_CHECK_NR"]
    cc = presentation["co_capture"]
    lines = ["# Genome exploration — look here first\n"]
    lines.append("## Top exploration leads (nr-confirmed divergence + capacity + resistance)")
    for i, r in enumerate(board, 1):
        lines.append(f"{i}. {r['exact_locus']} — {r['products']} · "
                     f"interest {r['exploration_interest']} · median-id {r['median_id']} · {r['why']}")
    lines.append(f"\n## nr-confirmed divergent loci ({len(conf)}) — the real distinctiveness axis")
    lines += [f"- {d['exact_locus']}: median-id {d['median_id']}% (nr, {d['n_genes']} genes)" for d in conf] or ["- none"]
    lines.append(f"\n## Unconfirmed divergence ({len(unconf)}) — ClusterBlast-only, RUN nr before trusting")
    lines.append("  (ClusterBlast's narrow reference set makes genus-conserved loci look divergent — "
                 "the documented false-divergence case compared 62% ClusterBlast with 100% nr. "
                 "These need nr to confirm or refute.)")
    lines += [f"- {d['exact_locus']}: ClusterBlast median-id {d['median_id']}%" for d in unconf[:12]] or ["- none"]
    lines.append(f"\n## Co-capture flags ({len(cc)}) — regions wider than the true cluster")
    lines += [f"- {c['exact_locus']}: {c['n_passengers']} passenger(s) {c['passenger_kinds']}" for c in cc[:8]] or ["- none"]
    lines.append("\n_Capacity-level only; median-id is similarity, not identity; bioactivity is extract-level._")
    return "\n".join(lines)


def explore_command(args) -> int:
    """CLI entry: mamey explore <package_dir> [--top N] [--json]."""
    pkg = Path(args.package)
    top = getattr(args, "top", 8)
    try:
        if args.json:
            output = json.dumps(_exploration_presentation(pkg, top=top), indent=1)
        else:
            output = render_explore(pkg, top=top)
    except ExactLocusIdentityError as exc:
        raise SystemExit(f"EXACT_LOCUS_IDENTITY_REQUIRED: {exc}") from None
    emit(output)
    return 0
