"""roster_v2 — package-native per-BGC, multi-channel gene roster model.

Builds the data contract consumed by the widget deliverable's per-gene "gene" view and
by the static v2/v3 rosters. Reader-side, offline, non-scoring: it only re-projects
package-native artifacts (never re-runs antiSMASH, never re-scores, never authors judgment).

Sources, all inside the sealed package:
  - genomic map + role + domains : locus_maps/<BGC>_*_locus_data.csv
  - channel hits (best per gene)  : the engine's own channel stores, each row already
      channel-tagged by blastp_ingest — nr/clustered_nr -> blastp_online/,
      swissprot -> blastp_swissprot/, ebi -> blastp_ebi/  (schema = HIT_FIELDS + channel)
  - MIBiG (KnownClusterBlast) + general ClusterBlast, per gene, with compound/annotation:
      parsed from the bundled antiSMASH JSON if present (records[].modules
      ["antismash.modules.clusterblast"].{knowncluster,general}); absent -> channel stays null.

Claim ceiling: every %id is homology — "capacity consistent with," never "produces";
a null channel means NOT RUN, never a biological zero.

Engine target: Mamey >= v1.9.119 / bundle v9.7.349. Author: Claude session 2026-08-03.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
from pathlib import Path
from typing import Any

# role -> (functional group, colour) for the arrow map / legend
_ROLE_GROUPS = (
    (("glycosyl",), ("glycosyltransferase", "#5b8def")),
    (("sugar pathway", "pepm", "ppd"), ("sugar pathway", "#e08a3c")),
    (("tailoring", "redox", "methyltransferase", "aminotransferase", "halogenase", "plp", "dehydrogenase"),
     ("tailoring/redox", "#6fbf73")),
    (("regulat",), ("regulator", "#e86fa0")),
    (("activation", "adenylation", "ntp transferase"), ("activation", "#a06fd0")),
    (("pks module", "nrps module", "ripp"), ("biosynthetic core", "#c9a227")),
    (("transport",), ("transport", "#4fb3b3")),
)
# engine channel store directories. Two on-disk schemas exist for the same channel today:
# the mixed per-BGC overlay `ingest_blastp_trove()` writes to blastp_online/<BGC>_online_
# blastp.csv for EVERY channel (nr/clustered_nr/swissprot/ebi alike, distinguished only by a
# "channel" column; schema = blastp_top_def/blastp_organism/blastp_accession), and the unmixed
# per-channel TOP10 store `install_channel_top10()` writes to blastp_nr/ blastp_clustered_nr/
# blastp_swissprot/ blastp_ebi/ as <BGC>_top10.csv (schema = subject_def/subject_organism/
# subject_acc) — see blastp_ingest.CHANNEL_STORE and widget_deliverable._BLASTP_CHANNEL_DIRS,
# which already read both. `_read_channel_store` below reads both for every channel; this dict
# only names the per-channel TOP10 directory (the overlay directory is fixed: blastp_online/).
_CHANNEL_STORES = {
    "nr": ("blastp_nr",),
    # ``blastp_cluster_nr`` was the pre-v9.7.383 writer spelling.  Prefer the
    # canonical explicit channel name, but continue to read legacy packages.
    "clustered_nr": ("blastp_clustered_nr", "blastp_cluster_nr"),
    "swissprot": ("blastp_swissprot",),
    "ebi": ("blastp_ebi",),
}
_OVERLAY_DIR = "blastp_online"


def _role_group(role: str) -> tuple[str, str]:
    r = (role or "").lower()
    for needles, out in _ROLE_GROUPS:
        if any(n in r for n in needles):
            return out
    return ("other", "#5aa9a0")


def _domains(gene_functions: str) -> tuple[list[str], str]:
    if not gene_functions:
        return [], ""
    doms = re.findall(r"([A-Za-z0-9_\-]+)\s*\(E-value", gene_functions)
    m = re.search(r"SMCOG\d+:\s*([^(]+?)(?:\s{2,}|\(E-value|$)", gene_functions)
    smcog = m.group(1).strip() if m else ""
    seen: set[str] = set()
    out: list[str] = []
    for d in doms:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out, smcog


def _fpct(x: Any) -> float | None:
    try:
        return round(float(x), 1)
    except (TypeError, ValueError):
        return None


def _gene_key(g: str) -> tuple[int, int]:
    m = re.match(r"ctg(\d+)_(\d+)", g or "")
    return (int(m.group(1)), int(m.group(2))) if m else (10 ** 9, 0)


def _locus_from_cb_query(q: str) -> str | None:
    for p in (q or "").split("|"):
        if re.match(r"ctg\d+_\d+$", p):
            return p
    return None


def _read_channel_store(pkg: Path, channel: str) -> dict[tuple[str, str], dict]:
    """Best (rank-1) hit per (bgc, locus) from one engine channel store.

    Reads both on-disk schemas for `channel` (see the `_CHANNEL_STORE` note above) and merges
    them; a TOP10-store row only fills a (bgc, locus) key the overlay store didn't already
    cover, so a package carrying both never lets a lower-precedence duplicate win.
    """
    out: dict[tuple[str, str], dict] = {}

    # overlay store: blastp_online/<BGC>_online_blastp.csv — every channel lands here, rows
    # distinguished by a "channel" column (nr/clustered_nr treated as interchangeable, matching
    # this module's existing nr call sites).
    od = pkg / _OVERLAY_DIR
    if od.is_dir():
        accept = ("", channel, "nr", "clustered_nr") if channel in ("nr", "clustered_nr") else ("", channel)
        for f in sorted(od.glob("*_online_blastp.csv")):
            try:
                for r in csv.DictReader(f.open(newline="", encoding="utf-8")):
                    if r.get("channel") not in accept:
                        continue
                    bgc = r.get("query_bgc") or _bgc_from_name(f.name)
                    locus = r.get("locus_tag") or r.get("query_locus")
                    if not locus:
                        continue
                    key = (bgc, locus)
                    if key in out:
                        continue  # store is already rank-1 per gene
                    out[key] = r
            except OSError:
                continue

    # unmixed TOP10 store: blastp_<channel>/<BGC>_top10.csv, sorted (gene, hit_rank) at write
    # time so the first row seen per gene is rank-1.
    for directory in _CHANNEL_STORES.get(channel, ()):
        td = pkg / directory
        if not td.is_dir():
            continue
        for f in sorted(td.glob("*_top10.csv")):
            try:
                for r in csv.DictReader(f.open(newline="", encoding="utf-8")):
                    bgc = r.get("bgc_id") or r.get("query_bgc") or _bgc_from_name(f.name)
                    locus = r.get("gene") or r.get("locus_tag") or r.get("query_locus")
                    if not locus:
                        continue
                    key = (bgc, locus)
                    if key in out:
                        continue  # canonical/overlay evidence keeps precedence
                    out[key] = r
            except OSError:
                continue
    return out


def _bgc_from_name(name: str) -> str:
    m = re.match(r"(BGC[0-9A-Za-z]+)", name)
    return m.group(1) if m else ""


def _rank_int(x: Any) -> int | None:
    try:
        v = int(str(x).strip())
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _clusterblast_from_per_gene_csvs(pkg: Path) -> tuple[dict, dict]:
    """(mibig_by_gene, general_by_gene) best-rank hit per (bgc, locus), read from the
    package's own already-parsed per-gene sidecars (_3_mibig_per_gene.csv /
    _4A2_ClusterBlast_per_gene.csv) — the same real, always-shipped files
    widget_deliverable._gene_evidence_rows() (the "genes" flat-table model) already reads
    successfully. Keyed by (bgc_id, locus), not locus alone, matching that reader and
    avoiding a same-locus-different-BGC collision the old locus-only keying risked."""
    mibig: dict[tuple[str, str], dict] = {}
    general: dict[tuple[str, str], dict] = {}
    mibig_csv = next(pkg.glob("*_3_mibig_per_gene.csv"), None)
    if mibig_csv and mibig_csv.is_file():
        try:
            for r in csv.DictReader(mibig_csv.open(newline="", encoding="utf-8")):
                key = (r.get("bgc_id", ""), r.get("query_gene", ""))
                pid = _fpct(r.get("pct_identity"))
                rank = _rank_int(r.get("reference_rank")) or 10**9
                if not key[1] or pid is None:
                    continue
                cur = mibig.get(key)
                if cur is None or rank < cur["_rank"]:
                    mibig[key] = {"pid": pid, "coverage": _fpct(r.get("pct_coverage")),
                                  "subject_gene": r.get("subject_gene", ""),
                                  "compound": r.get("mibig_compound", ""),
                                  "annotation": r.get("reference_type", "") or "",
                                  "genecluster": r.get("mibig_accession", ""), "_rank": rank}
        except OSError:
            pass
    cb_csv = next(pkg.glob("*_4A2_ClusterBlast_per_gene.csv"), None)
    if cb_csv and cb_csv.is_file():
        try:
            for r in csv.DictReader(cb_csv.open(newline="", encoding="utf-8")):
                key = (r.get("bgc_id", ""), r.get("query_gene", ""))
                pid = _fpct(r.get("pct_identity"))
                rank = _rank_int(r.get("reference_rank")) or 10**9
                if not key[1] or pid is None:
                    continue
                cur = general.get(key)
                if cur is None or rank < cur["_rank"]:
                    general[key] = {"pid": pid, "coverage": _fpct(r.get("pct_coverage")),
                                    "subject_gene": r.get("subject_gene", ""),
                                    "compound": "", "annotation": r.get("reference_source", "") or "",
                                    "genecluster": r.get("reference", ""), "_rank": rank}
        except OSError:
            pass
    for bucket in (mibig, general):
        for v in bucket.values():
            v.pop("_rank", None)
    return mibig, general


def _clusterblast_from_json(pkg: Path) -> tuple[dict, dict]:
    """Legacy fallback: (mibig_by_locus, general_by_locus) parsed straight from a bundled raw
    antiSMASH JSON, if a package variant genuinely ships one (records[].modules[...]). Real
    gold packages under the default --json-evidence bounded mode do not carry this file (only
    Mamey's own derived per-gene CSVs, read by _clusterblast_from_per_gene_csvs() above, which
    build_gene_roster() now prefers) — kept only so a package that does embed the raw JSON
    still benefits from it."""
    js = None
    for cand in list(pkg.glob("*.json")) + list(pkg.glob("**/*.json")):
        if cand.name in ("manifest.json", "gate_validation.json"):
            continue
        try:
            head = cand.open(encoding="utf-8", errors="ignore").read(200)
        except OSError:
            continue
        if '"records"' in head or "antismash" in head.lower():
            js = cand
            break
    mibig: dict[str, dict] = {}
    general: dict[str, dict] = {}
    if not js:
        return mibig, general
    try:
        data = json.load(js.open(encoding="utf-8"))
    except (OSError, ValueError):
        return mibig, general
    for rec in data.get("records", []):
        cb = rec.get("modules", {}).get("antismash.modules.clusterblast")
        if not cb:
            continue
        for kind, bucket in (("knowncluster", mibig), ("general", general)):
            for res in cb.get(kind, {}).get("results", []):
                for ref, score in res.get("ranking", []):
                    compound = (ref.get("description") or "").strip()
                    for pr in score.get("pairings", []):
                        if not (isinstance(pr, list) and len(pr) >= 3):
                            continue
                        lt = _locus_from_cb_query(pr[0])
                        hit = pr[2]
                        pid = _fpct(hit.get("perc_ident"))
                        if lt is None or pid is None:
                            continue
                        cur = bucket.get(lt)
                        if cur is None or pid > cur["pid"]:
                            bucket[lt] = {"pid": pid, "coverage": _fpct(hit.get("perc_coverage")),
                                          "subject_gene": hit.get("name", ""),
                                          "compound": compound if kind == "knowncluster" else "",
                                          "annotation": hit.get("annotation", "") or "",
                                          "genecluster": hit.get("genecluster", "")}
    return mibig, general


def build_gene_roster(package: str | os.PathLike, strain_id: str | None = None) -> dict:
    """Return the per-gene multi-channel roster model for a sealed package directory."""
    pkg = Path(package)
    # BGC metadata from the inventory CSV
    inv_rows: list[dict] = []
    for cand in list(pkg.glob("*_2_inventory.csv")) + list(pkg.glob("*inventory*.csv")):
        inv_rows = list(csv.DictReader(cand.open(newline="", encoding="utf-8")))
        break
    meta = {r["BGC_ID"]: r for r in inv_rows if r.get("BGC_ID")}
    strain = strain_id or (inv_rows[0].get("User_Label") if inv_rows else None) or pkg.name

    nr = _read_channel_store(pkg, "nr")
    cnr = _read_channel_store(pkg, "clustered_nr")
    sp = _read_channel_store(pkg, "swissprot")
    ebi = _read_channel_store(pkg, "ebi")
    mibig, general = _clusterblast_from_per_gene_csvs(pkg)
    mibig_by_locus_fallback: dict[str, dict] = {}
    general_by_locus_fallback: dict[str, dict] = {}
    if not mibig and not general:
        # legacy fallback only if a package genuinely ships no per-gene CSV sidecars at all
        # (real gold packages always do); locus-only keying preserves this path's prior,
        # already-existing same-locus-across-BGCs collision risk rather than changing it.
        mibig_by_locus_fallback, general_by_locus_fallback = _clusterblast_from_json(pkg)

    def locus_rows(bgc: str) -> dict[str, dict]:
        fs = glob.glob(str(pkg / "locus_maps" / f"{bgc}_*_locus_data.csv"))
        return {r["locus_tag"]: r for r in csv.DictReader(open(fs[0], newline="", encoding="utf-8"))} if fs else {}

    bgc_ids = sorted(set(meta) | {b for (b, _l) in list(nr) + list(cnr) + list(sp) + list(ebi)},
                     key=lambda b: int(re.sub(r"\D", "", b) or 0))
    present: set[str] = set()
    out_bgcs = []
    for bgc in bgc_ids:
        m = meta.get(bgc, {})
        ld = locus_rows(bgc)
        genes = sorted(set(ld) | {l for (b, l) in nr if b == bgc} | {l for (b, l) in cnr if b == bgc}
                       | {l for (b, l) in sp if b == bgc} | {l for (b, l) in ebi if b == bgc},
                       key=_gene_key)
        if not genes:
            continue
        gene_objs = []
        for g in genes:
            L = ld.get(g, {})
            doms, smcog = _domains(L.get("gene_functions", ""))
            grp, color = _role_group(L.get("role", ""))
            def hit(store, key, extra=None):
                r = store.get((bgc, g))
                if not r:
                    return None
                # overlay-schema (blastp_top_def/...) and TOP10-schema (subject_def/...) fields are
                # both possible per-row; prefer overlay, fall back to TOP10 so neither store's rows
                # render with a blank def/organism/acc.
                base = {"pid": _fpct(r.get("pct_identity")),
                        "def": r.get("blastp_top_def") or r.get("subject_def", ""),
                        "organism": r.get("blastp_organism") or r.get("subject_organism", ""),
                        "acc": r.get("blastp_accession") or r.get("subject_acc", "")}
                return base
            nr_h = hit(nr, "nr")
            cnr_h = hit(cnr, "clustered_nr")
            sp_h = hit(sp, "swissprot")
            ebi_h = hit(ebi, "ebi")
            mi = mibig.get((bgc, g)) or mibig_by_locus_fallback.get(g)
            cb = general.get((bgc, g)) or general_by_locus_fallback.get(g)
            for k, v in (("nr", nr_h), ("clustered_nr", cnr_h), ("swissprot", sp_h), ("ebi", ebi_h),
                         ("mibig", mi), ("clusterblast", cb)):
                if v:
                    present.add(k)
            gene_objs.append({
                "locus_tag": g,
                "order": int(L["order"]) if str(L.get("order", "")).isdigit() else None,
                "start": int(L["start"]) if str(L.get("start", "")).isdigit() else None,
                "end": int(L["end"]) if str(L.get("end", "")).isdigit() else None,
                "strand": L.get("strand", ""),
                "aa": int(L["length_aa"]) if str(L.get("length_aa", "")).isdigit() else None,
                "role": L.get("role", ""), "role_group": grp, "role_color": color,
                "domains": doms, "smcog": smcog,
                "channels": {"nr": nr_h, "clustered_nr": cnr_h, "swissprot": sp_h, "ebi": ebi_h,
                             "mibig": mi, "clusterblast": cb},
            })
        out_bgcs.append({
            "bgc_id": bgc, "node": m.get("Contig", "") or m.get("Node_ID", ""),
            "region": m.get("antiSMASH_Region", "") or m.get("Region", ""),
            "products": m.get("Products", ""), "boundary": m.get("Boundary", ""),
            "length_kb": m.get("Length_kb", ""), "kcb_top": m.get("KCB_top", ""),
            "kcb_score": m.get("KCB_score", ""), "genes": gene_objs,
        })
    return {"strain": strain, "channels_present": sorted(present), "bgcs": out_bgcs}
