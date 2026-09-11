"""blastp_ebi.py — formal EBI BLASTp transport (folded from the AS-XXX EBI patch, v9.7.215).

Fallback for when NCBI nr is unreachable from the run host (the "Temporarily unavailable" failure).
EBI is one-query-per-job, so a 30-seq FASTA = 30 jobs; job ids persist to disk so a killed process
resumes. This retrieves the **XML** result (not TSV) because the XML carries a real, source-
reported query length (the TSV drops it) — see mamey.ebi_xml_to_outfmt10, which turns the XML
into the SAME 13-column -outfmt 10 that blastp_ingest already accepts. `to_outfmt10()` below
persists that per-query length into the `.provenance.json` sidecar (AUDIT_378 wave 17: it
was previously parsed and then silently dropped, despite this file claiming coverage "survives")
so query coverage can be computed downstream without ever deriving it from alignment length. The
parse/score/reconcile layer is untouched.

DB caveat (stamped into provenance on every run): EBI offers no nr. Default here is
uniprotkb_bacteria (actinomycete-relevant subset); uniprotkb_trembl / uniref90 are the broad options.
EBI hits/%identities are NOT interchangeable with an nr panel — any card built on this transport must
carry database + transport=EBI in its §28 provenance and a named nr-confirmation next step. EBI is a
fallback, never the default; nr remains the reference DB when reachable.
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
import re
import json, os, sys, time, urllib.request, urllib.parse

BASE = "https://www.ebi.ac.uk/Tools/services/rest/ncbiblast"
# EBI's alignments/scores param is an ENUM, not a free int — posting an off-enum value (e.g. 6) is a
# hard 400 "Invalid parameters" (bug in v215-v217). Snap the requested hit count up to the nearest valid.
_EBI_ALIGN_ENUM = (0, 5, 10, 20, 50, 100, 150, 200, 250, 500, 750, 1000)


def _snap_alignments(n: int) -> str:
    for v in _EBI_ALIGN_ENUM:
        if v >= n:
            return str(v)
    return "1000"


def _post(path, params):
    req = urllib.request.Request(f"{BASE}/{path}", data=urllib.parse.urlencode(params).encode(),
                                 headers={"User-Agent": "mamey-blastp-ebi"})
    return urllib.request.urlopen(req, timeout=60).read().decode()


def _get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "mamey-blastp-ebi"})
    return urllib.request.urlopen(req, timeout=90).read().decode()


def read_fasta(path):
    seqs = []; lt = None; buf = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(">"):
                if lt:
                    seqs.append((lt, "".join(buf)))
                lt = line[1:].split()[0]; buf = []
            else:
                buf.append(line.strip())
    if lt:
        seqs.append((lt, "".join(buf)))
    return seqs


def _load(state):
    if os.path.exists(state):
        with open(state, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save(state, d):
    with open(state + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2)
    os.replace(state + ".tmp", state)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_EBI_BATCH = 30  # EMBL-EBI Job Dispatcher asks programmatic users to cap active jobs at 30.

def _validate_ebi_email(email):
    """EMBL-EBI requires a real contact email; reject empty/placeholder/invalid BEFORE any network call."""
    e = "" if email is None else str(email).strip()
    if not e:
        raise ValueError("blastp-ebi --submit requires a valid contact email (EMBL-EBI service identity). "
                         "Pass --email you@institution.edu")
    low = e.lower()
    if "example.org" in low or "example.com" in low or low == "sapote-mamey@example.org":
        raise ValueError(f"blastp-ebi --submit refuses the placeholder email {e!r}; pass your real --email")
    if not _EMAIL_RE.match(e):
        raise ValueError(f"blastp-ebi --submit: {e!r} is not a valid email address")
    return e


def submit_ebi(fasta, state, database="uniprotkb_bacteria", email=None,
               submit_gap=6.0, hits=6, throttle_sleep=time.sleep):
    """Submit every sequence in `fasta` (one EBI job each), persisting job ids after each submit.

    Fail-closed on EMBL-EBI fair-use: a valid --email is required, a transaction is capped at 30
    records, and a new transaction is refused while earlier submitted jobs are unharvested.
    """
    email = _validate_ebi_email(email)
    seqs = read_fasta(fasta)
    if len(seqs) > _MAX_EBI_BATCH:
        raise ValueError(f"blastp-ebi --submit: EMBL-EBI asks for <= {_MAX_EBI_BATCH} jobs per transaction; "
                         f"this FASTA has {len(seqs)} records. Split it into <= {_MAX_EBI_BATCH}-record batches.")
    d = _load(state)
    if d:
        pending = [lt for lt, j in d.get("jobs", {}).items()
                   if j and not str(j).startswith("ERR") and not (d.get("results") or {}).get(lt)]
        if pending:
            raise ValueError(f"blastp-ebi --submit refused: {len(pending)} job(s) already submitted and not yet "
                             "harvested. Run --harvest first, then resubmit any failures.")
    if not d:
        d = {"fasta": fasta, "database": database, "transport": "EBI",
             "jobs": {lt: None for lt, _ in seqs}, "results": {lt: None for lt, _ in seqs}}
        _save(state, d)
    # Fair-use budget across runs (EBI Job Dispatcher): refuse up front if the durable ledger says the
    # rolling 24 h window is exhausted; record each accepted job so a later run sees it. Inert inside
    # pytest unless a test sets MAMEY_BLAST_LEDGER. See mamey/blast_ledger.py.
    from .blast_ledger import refuse_if_exhausted, record
    _to_submit = sum(1 for lt, _ in seqs if d["jobs"].get(lt) is None)
    refuse_if_exhausted("ebi", need=max(1, _to_submit))
    for lt, seq in seqs:
        if d["jobs"].get(lt) is None:
            try:
                jid = _post("run", {"email": email, "program": "blastp", "stype": "protein",
                                    "database": database, "sequence": f">{lt}\n{seq}",
                                    "alignments": _snap_alignments(hits), "scores": _snap_alignments(hits)}).strip()
                d["jobs"][lt] = jid if jid and "-" in jid else f"ERR:no-jobid"
                if d["jobs"][lt] and not str(d["jobs"][lt]).startswith("ERR"):
                    record("ebi")
            except Exception as e:
                d["jobs"][lt] = f"ERR:{type(e).__name__}"
            _save(state, d)
            throttle_sleep(submit_gap)   # EBI fair-use throttle
    return d


def harvest_ebi(state, poll_budget=600, poll_gap=8.0, save_xml=True, sleep=time.sleep):
    """Poll pending jobs; retrieve XML (coverage-bearing) for finished ones. Resumable."""
    d = _load(state)
    # BLAST-P06: harvest before submit (or a missing/empty state file) means no jobs — return
    # gracefully instead of a KeyError on d["jobs"], per the resumable-phases contract.
    if not d.get("jobs"):
        emit(f"harvest_ebi: no submitted jobs in {state} (run submit first)", file=sys.stderr)
        return d
    stem = state[:-5] if state.endswith(".json") else state
    deadline = time.time() + poll_budget
    _results = d.get("results", {})
    pending = [lt for lt, j in d["jobs"].items()
               if j and not j.startswith("ERR") and _results.get(lt) is None]
    while pending and time.time() < deadline:
        for lt in list(pending):
            jid = d["jobs"][lt]
            try:
                st = _get(f"status/{jid}").strip()
            except Exception:
                continue
            if st == "FINISHED":
                try:
                    xml = _get(f"result/{jid}/xml")
                    if save_xml:
                        with open(f"{stem}_{lt}.xml", "w", encoding="utf-8") as fh:
                            fh.write(xml)
                    d["results"][lt] = "OK"; _save(state, d); pending.remove(lt)
                except Exception:
                    pass
            elif st in ("NOT_FOUND", "FAILURE", "ERROR"):
                d["results"][lt] = st; _save(state, d); pending.remove(lt)
        if pending:
            sleep(poll_gap)
    done = sum(1 for v in d["results"].values() if v == "OK")
    return d, done


def to_outfmt10(state, out_csv):
    """Convert all harvested per-locus XMLs into one -outfmt 10 CSV + a provenance sidecar carrying
    real per-query length (source-reported by EBI, not derived from alignment length) so query
    coverage can be computed downstream -- the CSV's 13 columns alone cannot carry coverage.

    A single malformed/partial XML (EBI rate-limit page, truncated download — the same failure class
    documented for the NCBI channel in blastp_online.py) is skipped and reported, not fatal to the batch:
    this is the fallback transport, so it should degrade gracefully, not crash harder than the primary."""
    import csv
    from mamey.ebi_xml_to_outfmt10 import convert
    d = _load(state)
    stem = state[:-5] if state.endswith(".json") else state
    n = 0
    failed = []
    # AUDIT_378 (wave 17): convert() parses a real, source-reported query length straight
    # off the EBI XML's <sequence length=...> attribute — the entire reason this module retrieves
    # XML instead of TSV in the first place (module docstring: "so query-coverage survives"; this
    # function's own docstring claimed "(coverage intact)"; the CLI print below claimed the same).
    # But qlen was captured into a local and never used again — dropped, not persisted anywhere —
    # so every claim of "coverage intact" was false: the 13-column -outfmt10 CSV has no coverage
    # column (by design, to stay byte-identical to the NCBI format blastp_ingest.py expects), and
    # nothing else recorded qlen either. Fixed by collecting per-query qlen here and writing it
    # into the provenance sidecar this function already produces, so a downstream reader can
    # compute real query_coverage = (q_end-q_start+1)/qlen without re-deriving qlen from anything
    # else (never from align_len/subject stats — this qlen is EBI-source-reported, exactly what
    # the house rule "never derive query coverage from alignment length" asks for).
    query_lengths = {}
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for lt, res in d.get("results", {}).items():
            if res != "OK":
                continue
            xmlp = f"{stem}_{lt}.xml"
            if not os.path.exists(xmlp):
                continue
            try:
                rows, qid, qlen = convert(xmlp)
            except Exception as exc:
                failed.append((lt, repr(exc)))
                continue
            for r in rows:
                w.writerow(r)
            if qid and qlen:
                query_lengths[qid] = qlen
            n += 1
    if failed:
        shown = ", ".join(f"{lt} ({err})" for lt, err in failed[:5])
        more = f" … +{len(failed) - 5} more" if len(failed) > 5 else ""
        emit(f"[blastp_ebi] WARN: {len(failed)} locus XML(s) failed to convert (malformed/partial "
              f"EBI response) and were skipped, not silently dropped: {shown}{more}", file=sys.stderr)
    # provenance sidecar so no card can silently mix nr and EBI
    with open(out_csv + ".provenance.json", "w", encoding="utf-8") as fh:
        json.dump({"transport": "EBI", "database": d.get("database", "?"),
                   "n_queries": n, "n_failed": len(failed),
                   "query_lengths": query_lengths,
                   "note": "EBI is not nr; flag DB-sensitive calls for nr re-run. query_lengths is "
                           "the EBI-XML-source-reported query length per query id -- the field the "
                           "13-column outfmt10 CSV cannot carry -- so a consumer can compute real "
                           "query coverage without deriving it from alignment length."},
                  fh, indent=2)
    return n


def blastp_ebi_command(a):
    """CLI: mamey blastp-ebi --fasta F --state S [--database D] [--submit|--harvest|--to-outfmt10 OUT].

    Fallback transport when NCBI nr is unreachable. Phases are resumable and can be run separately.
    """
    ran = False
    if getattr(a, "submit", False):
        d = submit_ebi(a.fasta, a.state, database=a.database, email=getattr(a, 'email', None), submit_gap=a.submit_gap, hits=a.hits)
        ok = sum(1 for j in d["jobs"].values() if j and not str(j).startswith("ERR"))
        emit(f"blastp-ebi submit [{a.database}]: {ok}/{len(d['jobs'])} jobs submitted -> {a.state}")
        ran = True
    if getattr(a, "harvest", False):
        d, done = harvest_ebi(a.state, poll_budget=a.poll_budget)
        emit(f"blastp-ebi harvest: {done}/{len(d['jobs'])} XML retrieved "
              f"({'re-run --harvest to continue' if done < len(d['jobs']) else 'COMPLETE'})")
        ran = True
    if getattr(a, "to_outfmt10", None):
        n = to_outfmt10(a.state, a.to_outfmt10)
        _db = _load(a.state).get("database", "?")
        emit(f"blastp-ebi to-outfmt10: {n} queries -> {a.to_outfmt10} "
              f"(real per-query length for coverage in {a.to_outfmt10}.provenance.json['query_lengths']). "
              f"Feed to `mamey ingest-blastp` WITH --source \"EBI ({_db})\" — this HitTable is "
              f"EBI transport, not NCBI, and ingest-blastp stamps 'NCBI web-BLASTp' by default.")
        ran = True
    if not ran:
        emit("blastp-ebi: choose at least one phase: --submit, --harvest, or --to-outfmt10 OUT.csv")
    return 0
