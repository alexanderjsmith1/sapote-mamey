"""blastp_autoharness.py — the resumable automation layer over the NCBI web-BLASTp channel.

Why this exists: the pipeline already has every *piece* of the per-gene BLASTp workflow — the
batch emitter, the fail-closed online transport (`blastp_online`), the ingest + ledger path
(`blastp_ingest`), and the completeness gate (`blastp_gate`). What it did NOT have is the thing
that runs them unattended over a whole strain while respecting NCBI's public-server etiquette:
build a PRIORITY worklist of the BGCs that still need BLASTp, submit **one** query roughly every
8 minutes (the courteous public-URLAPI cadence), poll the outstanding RIDs, and on an hourly
(adjustable) cadence fold the retrieved results into the package's unmixed channel stores. This
module is that scheduler.

Design constraints (non-negotiable, inherited from the project rules):
  * NETWORK IS INJECTABLE + FAIL-CLOSED. The scheduler NEVER talks to NCBI directly: it calls a
    `submit_fn` / `poll_fn` / `ingest_fn` handed to it. Real runs pass the NCBI-backed defaults
    (which reuse `blastp_online._submit_batch` and the poll recipe); tests pass mocks. Nothing is
    ever fabricated — a failed submit/poll is recorded, never invented.
  * NO EMAIL / NO PERSONAL IDENTIFIER on any outbound request. `build_submit_payload` constructs
    the NCBI Put payload with the anonymous common-pool `tool` tag ONLY. There is a test that
    asserts no email key and no user id ever appears in the payload.
  * CHANNELS STAY UNMIXED. Ingestion goes through `blastp_ingest.install_channel_top10`, which
    writes the four separate stores (blastp_nr / blastp_cluster_nr / blastp_swissprot /
    blastp_ebi) and keeps pct_identity AND pct_positives distinct. A BLASTp hit is SIMILARITY,
    never product identity.
  * RESUMABLE + IDEMPOTENT. State persists to <package>/blastp_online/_autoharness_state.json.
    Re-running resumes from that state: a unit already submitted/retrieved/ingested is never
    re-submitted. Provenance (channel, RID, timestamps) is recorded per unit.
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

try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import time
from pathlib import Path

from . import blastp_online as _bo
from . import blastp_gate as _gate

# One submission unit = one NCBI Put (respects "1 query per 8 min"). A BGC gene panel that exceeds
# the batch/residue budget is split into several units by `chunk_proteins`; the worklist itself is
# reported at BGC granularity.
DEFAULT_SUBMIT_INTERVAL_S = 480      # 8 minutes between Puts — courteous public-server cadence
DEFAULT_INGEST_INTERVAL_S = 3600     # fold retrieved results in hourly (adjustable)
STATE_FILENAME = "_autoharness_state.json"
CLAIM_SAFETY = _bo.CLAIM_SAFETY

# the online NCBI channel this harness drives writes to the `nr` store by default.
DEFAULT_CHANNEL = "nr"
_CHANNEL_DB = {"nr": "nr", "clustered_nr": "nr_cluster_seq", "swissprot": "swissprot"}


# --------------------------------------------------------------------------------------------
# request payload — the ONLY place an outbound NCBI request is shaped. No email, ever.
# --------------------------------------------------------------------------------------------
def build_submit_payload(fasta: str, *, database: str = "nr", evalue: str = "1e-5",
                         hitlist_size: int = 10) -> dict:
    """Build the NCBI BLAST URLAPI ``Put`` payload for one batch.

    Anonymous common pool ONLY: the sole identifier is the static ``tool`` tag ``SapoteMamey``.
    NO ``email`` key, NO user id, NO personal identifier is ever attached (project rule
    'no-email-in-api-requests'). Tests assert this invariant against the returned dict.
    """
    return {
        "CMD": "Put",
        "PROGRAM": "blastp",
        "DATABASE": database,
        "QUERY": fasta,
        "HITLIST_SIZE": str(hitlist_size),
        "EXPECT": evalue,
        "tool": "SapoteMamey",   # anonymous common-pool tag; deliberately no `email`
    }


# --------------------------------------------------------------------------------------------
# worklist — which BGCs still need BLASTp, ordered by lead priority
# --------------------------------------------------------------------------------------------
def _f(v, default=0.0) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


_LEAD_RANK = {
    "EXCEPTIONAL": 5, "PRIORITY ISO": 4, "PRIORITY_ISO": 4, "HIGH": 3, "HIGH SEQ": 3,
    "HIGH_SEQ": 3, "MEDIUM": 2, "MED": 2, "LOW": 1, "": 0,
}


def _load_faa(pkg: Path) -> dict:
    """locus_tag -> protein sequence, from <strain>_proteins.faa (the sealed translations)."""
    cache: dict[str, str] = {}
    for fp in sorted(pkg.glob("*_proteins.faa")):
        tag, buf = None, []
        try:
            with fp.open(encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith(">"):
                        if tag and buf:
                            cache.setdefault(tag, "".join(buf))
                        tag = line[1:].split()[0].split("|")[0].strip()
                        buf = []
                    elif tag:
                        buf.append(line.strip())
            if tag and buf:
                cache.setdefault(tag, "".join(buf))
        except OSError:
            continue
    return cache


def _proteins_for_bgc(pkg: Path, bgc_id: str, faa: dict) -> list:
    """[(locus_tag, seq)] for one BGC, in genomic order. Sequences come from the sealed FAA;
    loci/order come from gene_context. Honest-empty on any absence — never raises."""
    from . import modeb_template_emitter as _emit
    out: list = []
    for r in _emit._gene_rows_for_bgc(pkg, bgc_id):
        lt = (r.get("locus_tag") or r.get("lt") or "").strip()
        seq = (r.get("translation") or r.get("seq") or "").strip()
        if not seq and lt:
            seq = faa.get(lt, "")
        if lt and seq:
            out.append((lt, seq))
    return out


def build_worklist(package, strain: str, priority: str = "af_first",
                   channel: str = DEFAULT_CHANNEL, batch_size: int = _bo.DEFAULT_BATCH) -> list:
    """The priority worklist of BGCs that still need BLASTp on `channel`.

    A BGC needs BLASTp when it is NOT already recorded in the package's ingest ledger for this
    channel (the authoritative 'internal to the package' record the gate reads) AND it has loadable
    proteins. Ordering by `priority`:
      * 'af_first'  — antifungal-forward: AF_auto desc, then lead tier, then corrected rank
                      (the AF-first-for-Candida rule).
      * 'ab_first'  — antibacterial-forward: AB_auto desc, then lead tier, then corrected rank.
      * 'rank'      — the engine's corrected rank order.

    One work item = one BGC's gene panel:
      {bgc_id, channel, priority_score, af, ab, novelty, lead_tier, corrected_rank, products,
       n_proteins, proteins:[(locus,seq)], batches:[[(locus,seq)…], …]}
    Never raises; a BGC with no loadable proteins is dropped with nothing fabricated.
    """
    from . import modeb_template_emitter as _emit
    pkg = Path(package)
    triage = _emit._read_triage(pkg)
    already = set(_gate.read_ingest_ledger(pkg).get(channel, {}).keys())
    faa = _load_faa(pkg)

    items: list = []
    for r in triage:
        bgc = (r.get("BGC_ID") or r.get("bgc_id") or "").strip()
        if not bgc or bgc in already:
            continue
        proteins = _proteins_for_bgc(pkg, bgc, faa)
        if not proteins:
            continue
        af = _f(r.get("AF_auto"))
        ab = _f(r.get("AB_auto"))
        lead = (r.get("Lead_tier_auto") or "").strip().upper()
        lead_rank = _LEAD_RANK.get(lead, 0)
        crank = _f(r.get("Corrected_rank") or r.get("Rank"), default=1e9)
        batches = _bo.chunk_proteins(proteins, batch_size)
        items.append({
            "bgc_id": bgc,
            "channel": channel,
            "af": af, "ab": ab,
            "novelty": _f(r.get("Novelty_auto")),
            "lead_tier": lead,
            "_lead_rank": lead_rank,
            "corrected_rank": crank,
            "products": (r.get("Products") or "").strip(),
            "n_proteins": len(proteins),
            "proteins": proteins,
            "batches": batches,
            "n_batches": len(batches),
        })

    if priority == "af_first":
        keyf = lambda it: (-it["af"], -it["_lead_rank"], it["corrected_rank"])
    elif priority == "ab_first":
        keyf = lambda it: (-it["ab"], -it["_lead_rank"], it["corrected_rank"])
    else:  # 'rank'
        keyf = lambda it: (it["corrected_rank"], -it["_lead_rank"])
    items.sort(key=keyf)
    for i, it in enumerate(items, 1):
        it["priority_order"] = i
    return items


def plan_units(worklist: list) -> list:
    """Flatten the BGC-level worklist into ordered SUBMISSION UNITS (one NCBI Put each).

    A BGC whose panel exceeds the batch/residue budget yields several units, kept in worklist
    order so priority is preserved across the flattening. Each unit carries its own FASTA batch.
    """
    units: list = []
    for it in worklist:
        for bi, batch in enumerate(it["batches"]):
            uid = f"{it['bgc_id']}#{bi}"
            units.append({
                "unit_id": uid,
                "bgc_id": it["bgc_id"],
                "channel": it["channel"],
                "batch_index": bi,
                "n_proteins": len(batch),
                "batch": [list(p) for p in batch],   # [[locus, seq], …] (JSON-serializable)
            })
    return units


# --------------------------------------------------------------------------------------------
# scheduler state
# --------------------------------------------------------------------------------------------
def state_path(package) -> Path:
    return Path(package) / "blastp_online" / STATE_FILENAME


def load_state(package) -> dict | None:
    p = state_path(package)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_state(package, state: dict) -> None:
    p = state_path(package)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(p)


def new_state(package, strain: str, worklist: list, *, channel: str = DEFAULT_CHANNEL,
              submit_interval_s: int = DEFAULT_SUBMIT_INTERVAL_S,
              ingest_interval_s: int = DEFAULT_INGEST_INTERVAL_S) -> dict:
    return {
        "version": 1,
        "strain": strain,
        "package": str(package),
        "channel": channel,
        "submit_interval_s": submit_interval_s,
        "ingest_interval_s": ingest_interval_s,
        "last_submit_ts": None,
        "last_ingest_ts": None,
        "n_submits": 0,
        "queue": plan_units(worklist),      # not-yet-submitted units, in priority order
        "submitted": {},                    # unit_id -> {rid, bgc_id, ts, status, n_proteins, batch}
        "retrieved": {},                    # unit_id -> {rid, bgc_id, retrieve_ts, result_ref, batch}
        "ingested": [],                     # unit_ids folded into the channel store
        "failures": [],                     # {unit_id, phase, reason, ts}
        "provenance": [],                   # {unit_id, bgc_id, channel, rid, submit_ts, retrieve_ts, ingest_ts}
    }


def init_state(package, strain: str, *, priority: str = "af_first", channel: str = DEFAULT_CHANNEL,
               submit_interval_s: int = DEFAULT_SUBMIT_INTERVAL_S,
               ingest_interval_s: int = DEFAULT_INGEST_INTERVAL_S,
               resume: bool = True) -> dict:
    """Load existing state (resume) or build fresh from the worklist. Interval overrides are
    applied on resume too, so an operator can change the cadence without losing progress."""
    if resume:
        st = load_state(package)
        if st is not None:
            st["submit_interval_s"] = submit_interval_s
            st["ingest_interval_s"] = ingest_interval_s
            return st
    wl = build_worklist(package, strain, priority=priority, channel=channel)
    return new_state(package, strain, wl, channel=channel,
                     submit_interval_s=submit_interval_s, ingest_interval_s=ingest_interval_s)


def is_done(state: dict) -> bool:
    return not state["queue"] and not state["submitted"] and not state["retrieved"]


def status_line(state: dict) -> str:
    return (f"[auto-blastp] {state.get('strain','?')} ch={state.get('channel','?')}: "
            f"queued={len(state['queue'])} submitted={len(state['submitted'])} "
            f"retrieved={len(state['retrieved'])} ingested={len(state['ingested'])} "
            f"puts={state['n_submits']} failures={len(state['failures'])}")


# --------------------------------------------------------------------------------------------
# the scheduler step — pure/testable with injected fns + injected clock
# --------------------------------------------------------------------------------------------
def tick(now: float, state: dict, submit_fn, poll_fn, ingest_fn,
         *, max_submits: int | None = None) -> dict:
    """One scheduler step. Mutates and returns `state`. No I/O of its own — every side effect goes
    through an injected fn, so the whole thing is deterministic under a fake clock.

    Order within a tick:
      1. SUBMIT — if the queue is non-empty and >= submit_interval_s has elapsed since the last
         Put (and max_submits not reached), submit the next unit via `submit_fn(unit)`.
      2. POLL — for every outstanding submitted RID, call `poll_fn(entry)`; READY -> retrieved,
         FAILED -> failure.
      3. INGEST — if there are retrieved units and >= ingest_interval_s has elapsed since the last
         ingest, fold ALL retrieved units into the channel store via `ingest_fn(entries, state)`.

    Contracts:
      submit_fn(unit)            -> {"ok": bool, "rid": str, "reason": str}
      poll_fn(entry)             -> {"status": "READY"|"WAITING"|"FAILED", "result_ref": <json>,
                                     "reason": str}
      ingest_fn(entries, state)  -> {"ingested": [unit_id, …], "reason": str}
    """
    _tick_submit(now, state, submit_fn, max_submits)
    _tick_poll(now, state, poll_fn)
    _tick_ingest(now, state, ingest_fn)
    return state


def _due(now: float, last: float | None, interval: float) -> bool:
    return last is None or (now - last) >= interval


def _tick_submit(now, state, submit_fn, max_submits):
    if not state["queue"]:
        return
    if max_submits is not None and state["n_submits"] >= max_submits:
        return
    if not _due(now, state["last_submit_ts"], state["submit_interval_s"]):
        return
    unit = state["queue"][0]
    res = submit_fn(unit) or {}
    # every submit consumes the rate-limit window, success or fail, so we never hammer NCBI
    state["last_submit_ts"] = now
    state["n_submits"] += 1
    if res.get("ok") and res.get("rid"):
        state["queue"].pop(0)
        state["submitted"][unit["unit_id"]] = {
            "rid": res["rid"], "bgc_id": unit["bgc_id"], "channel": unit["channel"],
            "batch_index": unit["batch_index"], "n_proteins": unit["n_proteins"],
            "batch": unit["batch"], "submit_ts": now, "status": "submitted",
        }
    else:
        # leave it at the head? no — rotate to the tail so a poison unit can't wedge the queue.
        state["queue"].pop(0)
        state["queue"].append(unit)
        state["failures"].append({"unit_id": unit["unit_id"], "phase": "submit",
                                   "reason": res.get("reason", "submit failed"), "ts": now})


def _tick_poll(now, state, poll_fn):
    for uid in list(state["submitted"].keys()):
        entry = state["submitted"][uid]
        res = poll_fn({**entry, "unit_id": uid}) or {}
        status = res.get("status", "WAITING")
        if status == "READY":
            del state["submitted"][uid]
            state["retrieved"][uid] = {
                "rid": entry["rid"], "bgc_id": entry["bgc_id"], "channel": entry["channel"],
                "batch": entry["batch"], "submit_ts": entry["submit_ts"],
                "retrieve_ts": now, "result_ref": res.get("result_ref"),
            }
        elif status == "FAILED":
            del state["submitted"][uid]
            state["failures"].append({"unit_id": uid, "phase": "poll",
                                      "reason": res.get("reason", "poll FAILED"), "ts": now})
        # WAITING / anything else: leave it submitted for the next tick


def _tick_ingest(now, state, ingest_fn):
    if not state["retrieved"]:
        return
    if not _due(now, state["last_ingest_ts"], state["ingest_interval_s"]):
        return
    entries = [{"unit_id": uid, **v} for uid, v in state["retrieved"].items()]
    res = ingest_fn(entries, state) or {}
    done = set(res.get("ingested", []))
    for uid in list(state["retrieved"].keys()):
        if uid not in done:
            continue
        v = state["retrieved"].pop(uid)
        state["ingested"].append(uid)
        state["provenance"].append({
            "unit_id": uid, "bgc_id": v["bgc_id"], "channel": v["channel"], "rid": v["rid"],
            "submit_ts": v["submit_ts"], "retrieve_ts": v["retrieve_ts"], "ingest_ts": now,
        })
    state["last_ingest_ts"] = now


# --------------------------------------------------------------------------------------------
# default (real-network) injected fns — reuse blastp_online transport + blastp_ingest store
# --------------------------------------------------------------------------------------------
def _live_bo():
    """Resolve blastp_online from sys.modules AT CALL TIME, not via the module-level `_bo`.

    The transport must always be the live module object: this honours any monkeypatch of
    `_post`/`_submit_batch`, and stays correct if another test forks `mamey.blastp_online` in
    `sys.modules` (e.g. a registry-parity test that deletes+re-imports mamey modules) — otherwise
    the harness would call a stale copy whose `_post` was never patched. Same call-time-resolve
    pattern the default ingest fn already uses for `install_channel_top10`.
    """
    import importlib
    return importlib.import_module("mamey.blastp_online")


def default_submit_fn(*, channel: str = DEFAULT_CHANNEL, evalue: str = "1e-5"):
    """Real NCBI submit. Reuses blastp_online._submit_batch (which itself uses the anonymous
    `tool=SapoteMamey` Put — no email). Returns {ok, rid, reason}."""
    database = _CHANNEL_DB.get(channel, "nr")

    def _submit(unit):
        batch = [tuple(p) for p in unit["batch"]]
        r = _live_bo()._submit_batch(batch, database=database, evalue=evalue)
        return {"ok": bool(r.ok and r.rid), "rid": r.rid or "", "reason": r.reason}
    return _submit


def default_poll_fn(package, *, top_n: int = 10):
    """Real NCBI poll for one RID. Reuses blastp_online._post + parse_blast_xml. On READY, caches
    the parsed hits to <store>/_autoharness_cache/<unit_id>.json and returns that path as
    result_ref (JSON-serializable, so state stays clean). FAIL-CLOSED: transport errors -> WAITING
    (retry next tick), never fabricates."""
    import re
    cache_dir = Path(package) / "blastp_online" / "_autoharness_cache"

    def _poll(entry):
        rid = entry.get("rid")
        if not rid:
            return {"status": "FAILED", "reason": "no RID"}
        try:
            bo = _live_bo()
            info = bo._post({"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"})
            st = re.search(r"Status=(\w+)", info)
            status = st.group(1) if st else "UNKNOWN"
            if status == "FAILED":
                return {"status": "FAILED", "reason": "NCBI status FAILED"}
            if status != "READY":
                return {"status": "WAITING"}
            xml = bo._post({"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML",
                             "ALIGNMENTS": "3", "DESCRIPTIONS": "3"})
            batch = [tuple(p) for p in entry["batch"]]
            hits = bo.parse_blast_xml(xml, batch, top_n=top_n)
            if bo._zero_alignment_batch(hits):
                return {"status": "FAILED",
                        "reason": f"zero alignments for all {len(hits)} queries (v9.7.250 guard)"}
            cache_dir.mkdir(parents=True, exist_ok=True)
            rows = _hits_to_top10_rows(entry["bgc_id"], hits, strain="")
            ref = cache_dir / f"{entry['unit_id'].replace('#','_')}.json"
            ref.write_text(json.dumps({"bgc_id": entry["bgc_id"], "rows": rows}), encoding="utf-8")
            return {"status": "READY", "result_ref": str(ref)}
        except Exception as exc:   # network-restricted or NCBI down — retry, never fabricate
            return {"status": "WAITING", "reason": f"{type(exc).__name__}: {exc}"}
    return _poll


def _hits_to_top10_rows(bgc_id: str, hits, strain: str = "") -> list:
    """Flatten parsed BlastpHit objects into the channel-store top-10 schema
    (`blastp_ingest._TOP10_COLS`), keeping pct_identity AND pct_positives separate."""
    rows: list = []
    for h in hits:
        top = h.top_hits or [{
            "hit_def": h.blastp_top_def, "accession": h.blastp_accession,
            "organism": h.blastp_organism, "pct_identity": h.pct_identity,
            "pct_positive": h.pct_positive, "query_coverage": h.query_coverage,
            "evalue": h.evalue, "bitscore": h.bitscore,
        }]
        for rank, row in enumerate(top, 1):
            rows.append({
                "strain": strain, "bgc_id": bgc_id, "gene": h.locus_tag,
                "aa_length": h.aa_length, "role": h.antismash_domains, "hit_rank": rank,
                "subject_acc": row.get("accession", ""),
                "subject_organism": row.get("organism", ""),
                "subject_def": row.get("hit_def", ""),
                "pct_identity": row.get("pct_identity", ""),
                "pct_positives": row.get("pct_positive", ""),
                "query_coverage": row.get("query_coverage", ""),
                "evalue": row.get("evalue", ""), "bitscore": row.get("bitscore", ""),
            })
    return rows


def default_ingest_fn(package, strain: str, *, channel: str = DEFAULT_CHANNEL):
    """Real ingest: materialize retrieved units as a temporary per-BGC top-10 trove, then hand it
    to blastp_ingest.install_channel_top10 — the SAME unmixed-channel store + ledger path the
    manual workflow uses. Returns {ingested:[unit_id…]}. Reuses, never reimplements, the store."""
    import csv
    from .blastp_ingest import install_channel_top10, _TOP10_COLS, CHANNEL_STORE

    def _ingest(entries, state):
        pkg = Path(package)
        trove = pkg / "blastp_online" / "_autoharness_trove"
        sdir = trove / strain
        # group rows by BGC across all retrieved units so a multi-batch BGC lands as one table
        by_bgc: dict[str, list] = {}
        unit_by_bgc: dict[str, list] = {}
        for e in entries:
            ref = e.get("result_ref")
            rows = []
            if ref and Path(ref).exists():
                try:
                    rows = json.loads(Path(ref).read_text(encoding="utf-8")).get("rows", [])
                except (OSError, json.JSONDecodeError):
                    rows = []
            for r in rows:
                r["strain"] = r.get("strain") or strain
            by_bgc.setdefault(e["bgc_id"], []).extend(rows)
            unit_by_bgc.setdefault(e["bgc_id"], []).append(e["unit_id"])
        if not by_bgc:
            return {"ingested": []}
        # per-channel filename the store's glob expects (blastp_ingest._TOP10_GLOBS)
        fname = {"nr": "{b}_blastp_top10.csv", "clustered_nr": "{b}_blastp_top10_clustered.csv",
                 "swissprot": "{b}_blastp_top10_local.csv",
                 "ebi": "{b}_blastp_top10_ebi.csv"}.get(channel, "{b}_blastp_top10.csv")
        for bgc, rows in by_bgc.items():
            bdir = sdir / bgc
            bdir.mkdir(parents=True, exist_ok=True)
            with (bdir / fname.format(b=bgc)).open("w", newline="", encoding="utf-8") as fh:
                w = _SafeDictWriter(fh, fieldnames=_TOP10_COLS, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    w.writerow({k: r.get(k, "") for k in _TOP10_COLS})
        install_channel_top10(pkg, trove, channel, strain)  # writes CHANNEL_STORE[channel] + ledger
        ingested = [uid for uids in unit_by_bgc.values() for uid in uids]
        return {"ingested": ingested, "store": str(pkg / CHANNEL_STORE[channel])}
    return _ingest


# --------------------------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------------------------
def dry_run_report(package, strain: str, *, priority: str = "af_first",
                   channel: str = DEFAULT_CHANNEL,
                   submit_interval_s: int = DEFAULT_SUBMIT_INTERVAL_S,
                   ingest_interval_s: int = DEFAULT_INGEST_INTERVAL_S) -> dict:
    """Plan the worklist + schedule WITHOUT touching the network. Returns a summary dict and is
    the body of `--dry-run`."""
    wl = build_worklist(package, strain, priority=priority, channel=channel)
    units = plan_units(wl)
    n_proteins = sum(it["n_proteins"] for it in wl)
    span_min = max(0, len(units) - 1) * (submit_interval_s / 60.0)
    return {
        "strain": strain, "channel": channel, "priority": priority,
        "n_bgcs": len(wl), "n_units": len(units), "n_proteins": n_proteins,
        "submit_interval_s": submit_interval_s, "ingest_interval_s": ingest_interval_s,
        "est_submit_span_min": round(span_min, 1),
        "worklist": [{"order": it["priority_order"], "bgc_id": it["bgc_id"], "af": it["af"],
                      "ab": it["ab"], "lead_tier": it["lead_tier"],
                      "corrected_rank": it["corrected_rank"], "n_proteins": it["n_proteins"],
                      "n_batches": it["n_batches"], "products": it["products"]} for it in wl],
    }


def run(package, strain: str, *, priority: str = "af_first", channel: str = DEFAULT_CHANNEL,
        submit_interval_s: int = DEFAULT_SUBMIT_INTERVAL_S,
        ingest_interval_s: int = DEFAULT_INGEST_INTERVAL_S, max_submits: int | None = None,
        submit_fn=None, poll_fn=None, ingest_fn=None, clock=time.time, sleep_fn=time.sleep,
        poll_gap_s: float = 30.0, resume: bool = True, on_tick=None) -> dict:
    """Drive the scheduler to completion (or until max_submits Puts have been made).

    Real runs leave submit_fn/poll_fn/ingest_fn None -> the NCBI-backed defaults are used. Tests
    pass mocks + a fake `clock`/`sleep_fn`. State is persisted after every tick, so the process can
    be killed and resumed at any point. Returns the final state.
    """
    state = init_state(package, strain, priority=priority, channel=channel,
                       submit_interval_s=submit_interval_s, ingest_interval_s=ingest_interval_s,
                       resume=resume)
    save_state(package, state)
    submit_fn = submit_fn or default_submit_fn(channel=channel)
    poll_fn = poll_fn or default_poll_fn(package)
    ingest_fn = ingest_fn or default_ingest_fn(package, strain, channel=channel)

    while not is_done(state):
        if max_submits is not None and state["n_submits"] >= max_submits \
                and not state["submitted"] and not state["retrieved"]:
            break
        tick(clock(), state, submit_fn, poll_fn, ingest_fn, max_submits=max_submits)
        save_state(package, state)
        if on_tick:
            on_tick(state)
        if is_done(state):
            break
        sleep_fn(poll_gap_s)
    # final ingest sweep for anything retrieved after the last cadence boundary
    if state["retrieved"]:
        state["last_ingest_ts"] = None
        _tick_ingest(clock(), state, ingest_fn)
        save_state(package, state)
    return state


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def auto_blastp_command(args) -> int:
    """CLI: mamey auto-blastp — resumable priority BLASTp scheduler over the NCBI channel.

    --dry-run plans the worklist + schedule with NO network. A live run submits ~1 query / 8 min
    (adjustable), polls, and ingests hourly into the package's unmixed channel store. Fail-closed:
    nothing is ever fabricated; state persists to <package>/blastp_online/_autoharness_state.json.
    """
    package = args.package
    strain = args.strain
    channel = getattr(args, "channel", DEFAULT_CHANNEL)
    priority = getattr(args, "priority", "af_first")
    si = int(getattr(args, "submit_interval", DEFAULT_SUBMIT_INTERVAL_S) or DEFAULT_SUBMIT_INTERVAL_S)
    ii = int(getattr(args, "ingest_interval", DEFAULT_INGEST_INTERVAL_S) or DEFAULT_INGEST_INTERVAL_S)
    max_submits = getattr(args, "max_submits", None)

    if getattr(args, "dry_run", False):
        rep = dry_run_report(package, strain, priority=priority, channel=channel,
                             submit_interval_s=si, ingest_interval_s=ii)
        emit(f"[auto-blastp] DRY RUN — {rep['strain']} · channel {rep['channel']} · priority {rep['priority']}", f"[auto-blastp] worklist: {rep['n_bgcs']} BGC(s) need BLASTp ({rep['n_proteins']} proteins -> {rep['n_units']} submission unit(s))", f"[auto-blastp] schedule: 1 Put / {si}s (~{si / 60:.0f} min), ingest every {ii}s (~{ii / 60:.0f} min); est. submit span ~{rep['est_submit_span_min']:.0f} min", f'[auto-blastp] NO network contacted (dry run). NO email/personal id on any request. {CLAIM_SAFETY}', sep="\n")
        for row in rep["worklist"][:20]:
            emit(f"    {row['order']:>3}. {row['bgc_id']:<8} AF={row['af']:>5} AB={row['ab']:>5} "
                  f"tier={row['lead_tier'] or '-':<12} rank={row['corrected_rank']:.0f} "
                  f"genes={row['n_proteins']:>3} batches={row['n_batches']} · {row['products'][:48]}")
        if rep["n_bgcs"] > 20:
            emit(f"    … and {rep['n_bgcs'] - 20} more")
        return 0

    state = run(package, strain, priority=priority, channel=channel,
                submit_interval_s=si, ingest_interval_s=ii, max_submits=max_submits)
    emit(status_line(state), f"[auto-blastp] done. state -> {state_path(package)}. {CLAIM_SAFETY}", sep="\n")
    return 0
