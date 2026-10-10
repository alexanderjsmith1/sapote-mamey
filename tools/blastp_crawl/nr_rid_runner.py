#!/usr/bin/env python3
"""
nr_rid_runner.py — polite, RID-based remote NCBI nr BLASTp for the AS cohort.

Uses NCBI's qblast URL API the way it's meant to be used: SUBMIT a query (CMD=Put) → get an RID →
poll status → retrieve by RID (RIDs live ~24 h). This DECOUPLES submit from fetch, so we never hold
a long blocking call, and it survives restarts. blastp -remote does NOT bypass NCBI limits, and it
returned empty here — this is the robust replacement.

Politeness (why it won't overload NCBI): serial submits spaced by --sleep (default 50 s; NCBI asks
<=1 request/~10 s); each RID polled at most once/60 s; a small cap on concurrent in-flight searches.

NON-DESTRUCTIVE: results are written under `Blastp RESULTS/_NR_RID/` (ledger + raw XML2 + staging
curated CSVs). It NEVER edits the curated `Blastp RESULTS/<STRAIN>/<BGC>/` files. Merge is a
separate, deliberate step.

Output per BGC (staging): `_NR_RID/results/<STRAIN>/<BGC>/<BGC>_blastp_top10.csv` (+ _top_hit_per_gene.csv)
in the SAME 16-column schema as the curated results. Raw XML2 kept at `_NR_RID/xml/<RID>-Alignment.xml`
(also consumable by Yellow's enrich_xml.py).

Workspace: set SAPOTE_WORKSPACE_ROOT to the folder that holds `Blastp RESULTS/` (default: the
current directory). Lane: RID_DATABASE, RID_QUERIES, RID_BASE, as before.

Held RIDs (bundle v9.7.443): a RID older than --hold-after no longer occupies a submit slot, its
status is checked less often as it ages (1 min, then 5 min after 10 min, then 15 min after 1 h),
and at --max-wait it becomes `unsure` for the operator. A waiting RID is never retired and
resubmitted automatically: ClusteredNR RIDs have returned full results after 7-27 h.

Usage (gap crawl, one protein per query file):
  RID_DATABASE=nr_cluster_seq RID_BASE=_STRAINGAP_SINGLE_CLNR_GAP_<ASn> RID_QUERIES=_QUERIES_GAP_<AS-n>_K \
    python3 tools/blastp_crawl/nr_rid_runner.py run --hours 24 --sleep 300 --max-inflight 2
  python3 tools/blastp_crawl/nr_rid_runner.py status
"""
from __future__ import annotations
import argparse, base64, contextlib, csv, hashlib, io, json, os, re, subprocess, sys, tempfile, time, urllib.parse, uuid
import xml.etree.ElementTree as ET
import math
import html
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter, SafeWriter
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # run as a bare script: the bundle root is two levels above this file
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from mamey.csv_safety import SafeDictWriter, SafeWriter
    from mamey.path_safety import assert_output_outside_bundle

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()))
BR = ROOT / "Blastp RESULTS"
# env-overridable so the SAME runner can drive a second remote channel (e.g. clustered nr)
# with its OWN query subset, ledger and staging — never mixing channels:
#   RID_DATABASE (default nr) · RID_QUERIES (default _QUERIES) · RID_BASE (default _NR_RID)
DATABASE = os.environ.get("RID_DATABASE", "nr")
# CHANNEL-SAFETY (2026-08-10): the staged CSV suffix decides the channel in
# BLASTp Database/build_blastp_db.py (CHANNEL_BY_SUFFIX). `_NR_CLUSTER_RID` lives UNDER
# "Blastp RESULTS", which is a SEARCH_ROOT, so a clustered result written as the plain
# `_blastp_top10.csv` gets ingested as ncbi_nr — mixing cluster-representative identities
# into full-nr. The suffix must therefore follow the database, never the default.
TOP10_SUFFIX = "_blastp_top10_clustered.csv" if DATABASE == "nr_cluster_seq" else "_blastp_top10.csv"
QUERIES = BR / os.environ.get("RID_QUERIES", "_QUERIES")
BASE = BR / os.environ.get("RID_BASE", "_NR_RID")
XMLDIR = BASE / "xml"
RESDIR = BASE / "results"
LEDGER = BASE / "_ledger.csv"
LOG = BASE / "_run.log"
URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
UA = "SapoteMamey-LabQuest-nr-runner/1.0 (polite serial cohort BLASTp)"

# ── crawl_manifest heartbeat (v9.7.428) ──────────────────────────────────
# Derive the manifest lane name from RID_BASE (e.g. "_NR_CLNR_GAP_A" → "A").
# Non-GAP lanes (legacy _NR_RID etc.) don't have a manifest entry; heartbeat is a no-op for them.
_MANIFEST_LANE: str | None = None
_base_name = os.environ.get("RID_BASE", "_NR_RID")
if "_GAP_" in _base_name:
    _MANIFEST_LANE = _base_name.rsplit("_", 1)[-1]  # "A", "B", etc.
_LAST_HEARTBEAT = 0.0
_HEARTBEAT_INTERVAL = 60.0  # seconds between manifest heartbeats
_cm_heartbeat = None
_HEARTBEAT_WARNED = False
if _MANIFEST_LANE:
    _cm_path = HERE / "crawl_manifest.py"
    if not _cm_path.is_file():
        # v9.7.443: say so. Every run_lane.sh lane is a GAP lane, and crawl_manifest.py is not
        # shipped beside this runner, so the heartbeat used to be off with no word to anyone.
        sys.stderr.write(f"[nr_rid_runner] heartbeat disabled for lane {_MANIFEST_LANE}: "
                         f"{_cm_path} not found\n")
    else:
        try:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location("crawl_manifest", _cm_path)
            _cm_mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_cm_mod)
            _cm_heartbeat = _cm_mod.heartbeat
        except Exception as exc:  # present but unusable: a real failure, not an absent add-on
            sys.stderr.write(f"[nr_rid_runner] heartbeat disabled for lane {_MANIFEST_LANE}: "
                             f"could not load {_cm_path} ({type(exc).__name__}: {exc})\n")


def _heartbeat_failed(exc: Exception) -> None:
    """The manifest is advisory and never blocks the crawl; report its first failure once."""
    global _HEARTBEAT_WARNED
    if not _HEARTBEAT_WARNED:
        _HEARTBEAT_WARNED = True
        sys.stderr.write(f"[nr_rid_runner] manifest heartbeat failed for lane {_MANIFEST_LANE} "
                         f"({type(exc).__name__}: {exc}); further heartbeat errors are not repeated\n")

# Optional strain submit order for multi-strain query roots, e.g. RID_PRIORITY="AS-1,AS-2".
FLAGSHIP = [s.strip() for s in os.environ.get("RID_PRIORITY", "").split(",") if s.strip()]

# ── held RIDs, pacing and query checks (v9.7.443) ────────────────────────────────
def poll_interval(age_s: float, errors: int = 0) -> float:
    """Seconds between status checks for a RID of this age. Normal RIDs return in about a
    minute and are checked every 60 s as before; a RID that has waited longer is checked less
    often, and consecutive poll errors stretch the gap further (capped at 30 min)."""
    base = 60.0 if age_s < 600 else 300.0 if age_s < 3600 else 900.0
    return min(1800.0, base * (2 ** min(errors, 5)))

# Fleet pacing: the gap between this lane's submissions grows with the number of runners alive on
# this machine, so adding lanes does not multiply the load on NCBI. 1-4 runners: --sleep as given;
# 5-8: at least 12 min; 9-16: at least 20 min; 17 or more: at least 30 min. The count is refreshed
# once a minute and includes runners of any version.
_PACE = {"t": 0.0, "n": 1, "gap": None}
_RUNNER_CMD = re.compile(r"^\S*python[\d.]*\s+\S*nr_rid_runner\.py\s+run\b", re.IGNORECASE)

def live_runner_count() -> int:
    try:
        out = subprocess.run(["ps", "-Ao", "command="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return _PACE["n"]
    return max(1, sum(1 for line in out.splitlines() if _RUNNER_CMD.match(line.strip())))

def paced_sleep(base: float) -> float:
    if time.time() - _PACE["t"] >= 60:
        _PACE["t"] = time.time(); _PACE["n"] = live_runner_count()
    n = _PACE["n"]
    gap = (base if n <= 4 else max(base, 720.0) if n <= 8 else max(base, 1200.0) if n <= 16
           else max(base, 1800.0))
    if gap != _PACE["gap"]:
        _PACE["gap"] = gap
        log(f"  PACE {n} runner(s) live: one new submission per {gap / 60:.0f} min on this lane")
    return gap

def read_fasta(text: str) -> list[tuple[str, str]]:
    recs, head, seq = [], None, []
    for line in text.splitlines():
        if line.startswith(">"):
            if head is not None: recs.append((head, "".join(seq)))
            head, seq = line[1:].strip(), []
        elif head is not None:
            seq.append(line.strip())
    if head is not None: recs.append((head, "".join(seq)))
    return recs

def unsearchable_reason(fasta_text: str, min_aa: int, max_aa: int, max_one_residue: float) -> str:
    """Why a single-protein query should be parked instead of submitted, or "" if it is fine.
    Multi-record panels are left alone; the checks describe one protein."""
    recs = read_fasta(fasta_text)
    if len(recs) != 1: return ""
    seq = recs[0][1].upper().rstrip("*")
    if not seq: return "empty sequence"
    if max_aa and len(seq) >= max_aa: return f">={max_aa}aa ({len(seq)} aa); run manually"
    if len(seq) < min_aa: return f"<{min_aa}aa ({len(seq)} aa)"
    top = max(seq.count(c) for c in set(seq)) / len(seq)
    if top > max_one_residue: return f"low complexity ({top:.0%} one residue)"
    return ""

def check_query_tree(files: list[Path]) -> list[str]:
    """Problems that make a query tree unsafe to crawl: files with different record counts
    (single-protein and multi-protein panels mixed), or one sequence ID staged in two files."""
    problems, kinds, seen = [], set(), {}
    for f in files:
        recs = read_fasta(f.read_text(errors="replace"))
        kinds.add("single" if len(recs) == 1 else "multi")
        for head, _ in recs:
            ident = head.split()[0] if head else ""
            if ident in seen and seen[ident] != f:
                problems.append(f"sequence {ident} is staged in both {seen[ident].name} and {f.name}")
            seen.setdefault(ident, f)
    if kinds == {"single", "multi"}:
        problems.insert(0, "query tree mixes single-protein and multi-protein files")
    return problems
OUT_COLS = ["strain","bgc_id","gene","aa_length","role","domains","hit_rank","subject_acc",
            "subject_organism","subject_def","pct_identity","align_length","query_coverage",
            "evalue","bitscore","pct_positives"]
LEDGER_COLS = ["strain","bgc","file","rid","rtoe","submit_iso","status","fetch_iso","note", "query_sha256", "query_roster", "database"]

# XML2 parsers (regex, matching enrich_xml.py's approach)
R_SEARCH = re.compile(r"<Search>(.*?)</Search>", re.DOTALL)
R_QTITLE = re.compile(r"<query-title>([^<]*)</query-title>")
R_QID    = re.compile(r"<query-id>([^<]*)</query-id>")
R_HIT    = re.compile(r"<Hit>(.*?)</Hit>", re.DOTALL)
R_ACC    = re.compile(r"<accession>([^<]+)</accession>")
R_SCI    = re.compile(r"<sciname>([^<]*)</sciname>")
R_TITLE  = re.compile(r"<title>([^<]*)</title>")
R_BITS   = re.compile(r"<bit-score>([\d.eE+-]+)</bit-score>")
R_EVAL   = re.compile(r"<evalue>([\d.eE+-]+)</evalue>")
R_IDENT  = re.compile(r"<identity>(\d+)</identity>")
R_POS    = re.compile(r"<positive>(\d+)</positive>")
R_ALEN   = re.compile(r"<align-len>(\d+)</align-len>")


class TransportUnverified(RuntimeError):
    def __init__(self, message, response=""):
        super().__init__(message)
        self.response = response


class RetrievalUnverified(ValueError):
    """A response cannot certify the complete submitted query roster."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink(): raise ValueError(f"checkpoint symlink refused: {path}")
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _recover_results():
    journal = BASE / "_result_transaction.json"
    if not journal.exists(): return
    record = json.loads(journal.read_text())
    items = record["items"]
    for item in items:
        target = BASE / item["relative"]
        if target.is_symlink() or not target.resolve().is_relative_to(BASE.resolve()):
            raise ValueError(f"unsafe result recovery target: {target}")
    # A fully published generation is committed even if cleanup was interrupted.
    complete = all((BASE / i["relative"]).is_file() and
                   _sha((BASE / i["relative"]).read_bytes()) == i["new_sha256"] for i in items)
    if not complete:
        for item in items:
            target = BASE / item["relative"]
            previous = item["previous"]
            if previous is None: target.unlink(missing_ok=True)
            else:
                payload = base64.b64decode(previous, validate=True)
                if _sha(payload) != item["previous_sha256"]:
                    raise ValueError("result recovery backup digest mismatch")
                _atomic_bytes(target, payload)
    journal.unlink()


def _publish_results(payloads: dict[Path, bytes]):
    journal = BASE / "_result_transaction.json"
    if journal.exists(): raise ValueError("pending result transaction requires lane recovery")
    items = []
    for target, data in payloads.items():
        if target.is_symlink() or not target.resolve().is_relative_to(BASE.resolve()):
            raise ValueError(f"unsafe result target: {target}")
        previous = target.read_bytes() if target.exists() else None
        items.append(dict(relative=str(target.relative_to(BASE)), new_sha256=_sha(data),
                          previous=None if previous is None else base64.b64encode(previous).decode(),
                          previous_sha256=None if previous is None else _sha(previous)))
    _atomic_bytes(journal, json.dumps(dict(schema=1, items=items), sort_keys=True).encode())
    try:
        for target, data in payloads.items(): _atomic_bytes(target, data)
    except BaseException:
        _recover_results()
        raise
    journal.unlink()


@contextlib.contextmanager
def lane_owner():
    """OS-held lane ownership is released on process exit; the PID is advisory only."""
    try: import fcntl
    except ImportError as exc: raise ValueError("exclusive lane ownership requires POSIX flock; runner held on this platform") from exc
    BASE.mkdir(parents=True, exist_ok=True)
    lockpath = BASE / "_runner.lock"
    if lockpath.is_symlink(): raise ValueError("lane lock symlink refused")
    with lockpath.open("a+") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise ValueError("lane already owned by another runner") from exc
        try:
            _recover_results()
            yield
        finally: fcntl.flock(lock, fcntl.LOCK_UN)


def now_iso(): return time.strftime("%Y-%m-%d %H:%M:%S")

def iso_to_epoch(s: str) -> float:
    try: return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
    except Exception: return time.time()

def log(msg):
    BASE.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {msg}"; print(line, flush=True)
    with LOG.open("a") as fh: fh.write(line + "\n")

def _curl(args: list[str], timeout: int) -> str:
    # route through curl: this Python's urllib has no CA bundle (CERTIFICATE_VERIFY_FAILED),
    # but curl uses the system trust store and reaches NCBI fine.
    # --http1.1: force HTTP/1.1. curl negotiates HTTP/2 to blast.ncbi.nlm.nih.gov by default and a
    # framing error (curl rc=16 / CURLE_HTTP2) can wedge a single RID's polls indefinitely. HTTP/1.1
    # avoids that failure mode; NCBI serves the URL API fine over 1.1.
    p = subprocess.run(["curl", "-s", "--fail-with-body", "--http1.1", "--max-time", str(timeout), "-A", UA] + args,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise TransportUnverified(f"curl rc={p.returncode}: {p.stderr.strip()[:150]}", p.stdout)
    return p.stdout

def submit(fasta_text: str) -> tuple[str, int]:
    with tempfile.NamedTemporaryFile("w", suffix=".faa", delete=False) as tf:
        tf.write(fasta_text); qf = tf.name
    try:
        out = _curl(["-X", "POST", URL,
                     "--data-urlencode", "CMD=Put",
                     "--data-urlencode", "PROGRAM=blastp",
                     "--data-urlencode", f"DATABASE={DATABASE}",
                     "--data-urlencode", "HITLIST_SIZE=10",
                     "--data-urlencode", f"QUERY@{qf}"], 90)
    finally:
        os.unlink(qf)
    rid = re.search(r"RID = (\S+)", out); rtoe = re.search(r"RTOE = (\d+)", out)
    return (rid.group(1) if rid else ""), (int(rtoe.group(1)) if rtoe else 0)

def status(rid: str) -> str:
    q = urllib.parse.urlencode({"CMD": "Get", "FORMAT_OBJECT": "SearchInfo", "RID": rid})
    m = re.search(r"Status=(\w+)", _curl([f"{URL}?{q}"], 30))
    return m.group(1) if m else "UNKNOWN"

def fetch_xml2(rid: str) -> str:
    q = urllib.parse.urlencode({"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML2_S"})
    return _curl([f"{URL}?{q}"], 180)


def defline_meta(faa: Path) -> dict:
    meta = {}
    if not faa.exists():
        # 2026-09-10: an orphaned RID (see the RESUME comment below) has no local query file
        # to read defline metadata from -- that's cosmetic (role/aa annotations on the result rows),
        # not fatal. Degrade to no metadata instead of letting FileNotFoundError abort the fetch.
        return meta
    for line in faa.read_text(errors="replace").splitlines():
        if line.startswith(">"):
            d = {k.split("=",1)[0].strip(): k.split("=",1)[1].strip()
                 for k in line[1:].split("|") if "=" in k}
            if d.get("gene"):
                value = {"aa": d.get("aa",""), "role": d.get("role","")}
                meta[line[1:].strip()] = value
                meta.setdefault(d["gene"], value)
    return meta

def gene_of(defline: str) -> str:
    m = re.search(r"gene=([^|]+)", defline)
    if m: return m.group(1)
    parts = defline.split("|")
    return parts[2] if len(parts) > 2 else defline


# (2026-07-31) A panel may hold proteins from MORE THAN ONE BGC — the self-resistance set is
# 1-2 genes across hundreds of BGCs, so per-BGC panels would mean ~226 submissions instead of ~27.
# Results are filed per (strain, BGC), so the pair must come from the DEFLINE, not the file path,
# or every hit in a mixed panel lands under the wrong BGC. Every defline this project emits starts
# `<strain>|<BGC>|...`, so read it there and fall back to the path when it doesn't match.
R_SB = re.compile(r"^((?:AS|AJS|SID)-?\d+)\|(BGC\d+)\|")

def strain_bgc_of(defline: str, strain: str, bgc: str) -> tuple:
    m = R_SB.match(defline.lstrip(">").strip())
    return (m.group(1), m.group(2)) if m else (strain, bgc)

def parse_xml2(xml: str, strain: str, bgc: str, meta: dict, *, expected_queries=None) -> list[list]:
    try: root = ET.fromstring(xml)
    except ET.ParseError as exc: raise RetrievalUnverified(f"malformed XML: {exc}") from exc
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
        if node.text: node.text = node.text.strip()
    if root.tag not in ("BlastXML2", "BlastOutput2", "Search"):
        raise RetrievalUnverified(f"unsupported XML root {root.tag}")
    if any(n.tag in ("error", "Error", "errors", "Err") for n in root.iter()):
        raise RetrievalUnverified("XML error response")
    searches = list(root.iter("Search"))
    titles = []
    for search in searches:
        qt = search.find("query-title")
        if qt is None or not qt.text or not qt.text.strip():
            raise RetrievalUnverified("Search missing query-title")
        titles.append(qt.text.strip())
        qlen = search.find("query-len")
        hits_node = search.find("hits")
        if qlen is None or not (qlen.text or "").isdigit() or int(qlen.text) <= 0 or hits_node is None:
            raise RetrievalUnverified("Search missing complete query-length/hits structure")
        if any(len(search.findall(tag)) != 1 for tag in ("query-title", "query-len", "hits")):
            raise RetrievalUnverified("Search has repeated required structure")
        if any(child.tag != "Hit" for child in hits_node) or (hits_node.text or "").strip():
            raise RetrievalUnverified("unsupported hits structure")
        if list(search.iter("Hit")) != list(hits_node):
            raise RetrievalUnverified("Hit outside direct hits roster")
        for hit in search.iter("Hit"):
            if hit.find("hsps") is None or not list(hit.iter("Hsp")):
                raise RetrievalUnverified("Hit missing HSP structure")
            required = ("accession", "bit-score", "evalue", "identity", "align-len")
            if any(not any(n.tag == tag and n.text for n in hit.iter()) for tag in required):
                raise RetrievalUnverified("Hit missing required result field")
            for hsp in hit.iter("Hsp"):
                try:
                    fields = {n.tag: n.text for n in hsp}
                    alen = int(fields["align-len"])
                    identity = int(fields["identity"])
                    bits = float(fields["bit-score"]); evalue = float(fields["evalue"])
                    if alen <= 0 or identity < 0 or identity > alen or bits < 0 or evalue < 0 or not all(map(math.isfinite, (bits, evalue))):
                        raise ValueError("invalid alignment field")
                except (KeyError, TypeError, ValueError) as exc:
                    raise RetrievalUnverified("HSP incomplete or invalid numeric fields") from exc
    if not titles or len(set(titles)) != len(titles):
        raise RetrievalUnverified("missing or repeated Search query identity")
    if expected_queries is not None:
        expected_queries = list(expected_queries)
        if not expected_queries or len(set(expected_queries)) != len(expected_queries):
            raise RetrievalUnverified("submitted query roster empty or ambiguous")
        if set(titles) != set(expected_queries):
            raise RetrievalUnverified("returned query roster differs from submitted query roster")
    # Normalize namespaces for the existing rank/metric implementation.
    xml = ET.tostring(root, encoding="unicode")
    rows = []
    for sb in R_SEARCH.finditer(xml):
        block = sb.group(1)
        qt = R_QTITLE.search(block) or R_QID.search(block)
        if not qt: continue
        title = html.unescape(qt.group(1))
        gene = gene_of(title)
        r_strain, r_bgc = strain_bgc_of(title, strain, bgc)
        m = meta.get(title, meta.get(gene, {"aa": "", "role": ""}))
        hits = []
        for hb in R_HIT.finditer(block):
            h = hb.group(1)
            acc = R_ACC.search(h); sci = R_SCI.search(h); ti = R_TITLE.search(h)
            bits = R_BITS.search(h); ev = R_EVAL.search(h)
            idn = R_IDENT.search(h); pos = R_POS.search(h); al = R_ALEN.search(h)
            if not (acc and bits and al): continue
            alen = int(al.group(1)) or 1
            pident = round(int(idn.group(1))/alen*100, 3) if idn else ""
            ppos = round(int(pos.group(1))/alen*100, 2) if pos else ""
            hits.append((float(bits.group(1)), acc.group(1),
                         sci.group(1).strip() if sci else "",
                         ti.group(1).strip() if ti else "",
                         pident, alen, ev.group(1) if ev else "", ppos))
        hits.sort(key=lambda x: x[0], reverse=True)
        for rank, (bits, acc, org, sdef, pident, alen, ev, ppos) in enumerate(hits[:10], 1):
            rows.append([r_strain, r_bgc, gene, m["aa"], m["role"], "", rank, acc,
                         org, sdef, pident, alen, "", ev, bits, ppos])
    return rows


def write_results_grouped(rows: list[list]):
    """Split rows by their OWN (strain, bgc) columns and file each group. Required for mixed-BGC
    panels; for a single-BGC panel this is exactly one write_results call, so behaviour is
    unchanged."""
    if not rows: return
    groups: dict = {}
    for r in rows:
        groups.setdefault((r[0], r[1]), []).append(r)
    for (s, b), g in groups.items():
        write_results(s, b, g)

def write_results(strain: str, bgc: str, rows: list[list], *, replace_genes=None, fresh=False):
    # MERGE by gene, don't clobber. A BGC can span several batch FASTAs (b01,b02,...),
    # each returning its own RID. Writing the per-BGC CSV per-batch with "w" would let the
    # last-fetched batch overwrite earlier ones, dropping genes. Instead: keep every gene
    # already in the file, replace only the genes present in this batch (idempotent re-run),
    # and append this batch's genes. gene locus (col index 2) is the stable key.
    if not rows and replace_genes is None: return
    d = RESDIR / strain / bgc; d.mkdir(parents=True, exist_ok=True)
    path = d / f"{bgc}{TOP10_SUFFIX}"
    existing = []
    if path.exists() and not fresh:
        with path.open(newline="") as fh:
            rd = csv.reader(fh); next(rd, None)          # drop header
            existing = [row for row in rd if row]
    new_genes = set(replace_genes) if replace_genes is not None else {r[2] for r in rows}
    merged = [row for row in existing if row[2] not in new_genes] + rows
    top1 = [r for r in merged if str(r[6]) == "1"]
    payloads = {}
    for target, selected in ((path, merged), (d / f"{bgc}_top_hit_per_gene.csv", top1)):
        stream = io.StringIO(newline="")
        writer = SafeWriter(stream); writer.writerow(OUT_COLS); writer.writerows(selected)
        payloads[target] = stream.getvalue().encode()
    receipt = dict(schema=1, generation=uuid.uuid4().hex,
                   files={str(p.relative_to(BASE)): _sha(data) for p, data in payloads.items()})
    payloads[d / "_result_generation.json"] = json.dumps(receipt, sort_keys=True).encode()
    _publish_results(payloads)


# ---------- ledger ----------
def load_ledger() -> dict:
    if not LEDGER.exists(): return {}
    out = {}
    for r in csv.DictReader(LEDGER.open()):
        out[r["file"]] = r
    return out

def save_ledger(led: dict):
    BASE.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline="")
    w = SafeDictWriter(stream, fieldnames=LEDGER_COLS); w.writeheader()
    for r in led.values(): w.writerow({k: r.get(k, "") for k in LEDGER_COLS})
    _atomic_bytes(LEDGER, stream.getvalue().encode())


def all_query_files() -> list[Path]:
    strains = sorted([p.name for p in QUERIES.iterdir()
                      if p.is_dir() and re.match(r"^(AS|SID)-?\d", p.name)])
    counts = {s: sum(1 for _ in (QUERIES / s).rglob("*.faa")) for s in strains}
    order = [s for s in FLAGSHIP if s in strains] + \
            sorted([s for s in strains if s not in FLAGSHIP], key=lambda s: counts[s], reverse=True)
    files = []
    for s in order: files.extend(sorted((QUERIES / s).rglob("*.faa")))
    # PRIORITY TIERS (stable partition — flagship/count ordering preserved within each tier):
    #   pri0 = the owner's curated Mode-B card set (PRIORITY_BLASTP_nr.fasta, 2026-07-31). These gate
    #          Mode-B card authoring + his analysis, so they run FIRST, ahead of everything.
    #   pri  = Mode-B High/Exceptional lead panels (antifungal-first) built earlier.
    #   rest = the bulk sweep.
    # All priority panels are 8 proteins/query.
    # NB: "_pri_p" is NOT a substring of "_pri0_p" (the digit breaks it), so each tier must be
    # tested explicitly — otherwise pri0 panels fall through into `rest` and get submitted twice.
    #   _srz_p = self-resistance gene set (Claude July 31 2026/SELF_RESISTANCE_*), 10 proteins
    #            per panel, TOP100-flagged BGCs first. Runs after the card set, before the
    #            AF-lead panels.
    def tier(f):
        if "_srzTOP_" in f.name: return 0   # self-resistance batches — TOP priority (the owner 07-31)
        if "_pri0_p" in f.name: return 1    # Mode-B card set
        if "_srz_p" in f.name: return 2     # (superseded per-BGC srz panels, if any remain)
        if "_pri_p" in f.name: return 3     # antifungal-first lead panels
        return 4
    return sorted(files, key=lambda f: (tier(f), files.index(f)))

def relkey(faa: Path) -> str: return str(faa.relative_to(QUERIES))


def record_response(rid, xml, ledger_row):
    """Preserve every returned body before result admission, including HTTP-error bodies."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", rid): raise RetrievalUnverified("unsafe RID filename identity")
    raw = xml.encode("utf-8")
    attempt = XMLDIR / f"{rid}-{uuid.uuid4().hex}.xml"
    _atomic_bytes(attempt, raw)
    _atomic_bytes(XMLDIR / f"{rid}-Alignment.xml", raw)
    try:
        roster = json.loads(ledger_row.get("query_roster") or "[]")
        if not isinstance(roster, list) or any(not isinstance(title, str) for title in roster): roster = []
    except ValueError: roster = []
    evidence = dict(schema=1, rid=rid, database=ledger_row.get("database", ""),
                    query_sha256=ledger_row.get("query_sha256", ""), raw_sha256=_sha(raw),
                    raw_file=attempt.name, queries=roster, status="UNVERIFIED", rows=None,
                    query_states=[dict(title=title, status="UNVERIFIED") for title in roster])
    _atomic_bytes(attempt.with_suffix(".admission.json"), json.dumps(evidence, sort_keys=True).encode())
    _atomic_bytes(XMLDIR / f"{rid}-admission.json", json.dumps(evidence, sort_keys=True).encode())
    return attempt, evidence


def retrieval_admitted(key, row):
    """Legacy/mismatched retrieved statuses are not certified completion."""
    try:
        faa = QUERIES / key
        receipt = json.loads((XMLDIR / f"{row['rid']}-admission.json").read_text())
        raw_file = XMLDIR / receipt["raw_file"]
        if not raw_file.resolve().is_relative_to(XMLDIR.resolve()): return False
        bound = (receipt.get("database") == row.get("database") == DATABASE and
                 receipt["status"] in ("COMPLETE_HITS", "COMPLETE_NO_HITS") and
                 receipt["query_sha256"] == row.get("query_sha256") == _sha(faa.read_bytes()) and
                 receipt["raw_sha256"] == _sha(raw_file.read_bytes()) and
                 receipt["queries"] == [h for h, _ in read_fasta(faa.read_text())])
        if not bound or not receipt.get("result_groups"): return False
        for group in receipt["result_groups"]:
            directory = RESDIR / group["strain"] / group["bgc"]
            if not directory.resolve().is_relative_to(RESDIR.resolve()): return False
            generation = json.loads((directory / "_result_generation.json").read_text())
            expected = {str((directory / f"{group['bgc']}{TOP10_SUFFIX}").relative_to(BASE)),
                        str((directory / f"{group['bgc']}_top_hit_per_gene.csv").relative_to(BASE))}
            if set(generation["files"]) != expected: return False
            if any(_sha((BASE / name).read_bytes()) != digest
                   for name, digest in generation["files"].items()): return False
        return True
    except (KeyError, TypeError, ValueError, OSError): return False


def cmd_status():
    led = load_ledger()
    from collections import Counter
    c = Counter(r["status"] for r in led.values())
    print(f"ledger: {len(led)} entries — " + ", ".join(f"{k}={v}" for k,v in sorted(c.items())))
    staged = sum(1 for _ in RESDIR.rglob(f"*{TOP10_SUFFIX}")) if RESDIR.exists() else 0
    print(f"staged BGC result files: {staged}")


def cmd_run(args):
    try:
        with lane_owner(): return _owned_cmd_run(args)
    except (ValueError, OSError) as exc:
        print(f"RUN refused: {exc}", file=sys.stderr)
        return 3


def _owned_cmd_run(args):
    marker = BASE / "_HANDOFF_OUT.txt"
    if marker.exists() and not args.ignore_handoff:
        print(f"RUN refused: this lane is handed off to another machine ({marker}):\n"
              f"{marker.read_text().strip()}\nMerge its return zip first (crawl_handoff.py merge), "
              f"or pass --ignore-handoff.", file=sys.stderr)
        return 3
    for d in (BASE, XMLDIR, RESDIR): d.mkdir(parents=True, exist_ok=True)
    # _runner.pid marks the lane live for blastp_health.py, whatever launched it.
    pidfile = BASE / "_runner.pid"
    _atomic_bytes(pidfile, f"{os.getpid()}\n".encode())
    try:
        return _run_lane(args)
    finally:
        try:
            if pidfile.read_text().strip() == str(os.getpid()):
                pidfile.unlink()
        except OSError as exc:
            if not isinstance(exc, FileNotFoundError):  # already gone is fine; anything else is not
                sys.stderr.write(f"[nr_rid_runner] could not remove {pidfile} ({exc}); "
                                 f"blastp_health may report this lane as live\n")


def _run_lane(args):
    global _LAST_HEARTBEAT
    led = load_ledger()
    files = all_query_files()
    for key, row in led.items():
        if row.get("status") == "fetched" and not retrieval_admitted(key, row):
            row["status"] = "query_unbound"
            row["note"] = "completed retrieval receipt missing, changed, or unbound; operator hold"
    save_ledger(led)
    # todo excludes already-fetched AND still-in-flight (submitted); expired/error get retried.
    # 2026-09-10: also exclude "submit_failed_parked" — the poison-pill park (30-fail cap,
    # see MAX_SUBMIT_RETRIES below) previously only held for the REST of that same process's run;
    # a fresh launch re-scanned `files`, saw no "fetched"/"submitted" exclusion, and re-burned the
    # full ~30-fail/~2.5h cycle on the same already-known-bad panel before re-parking it. Confirmed
    # across two consecutive session restarts (four panels across three strains all
    # re-appeared in fresh run.logs after having already parked in a prior process). A parked file
    # stays parked until someone deliberately retries it (moving it back, or a ledger edit) — see
    # `Blastp RESULTS/_QUARANTINE_CLNR_GAP/` for the manual-quarantine workaround used meanwhile.
    if not args.allow_mixed_tree:
        problems = check_query_tree(files)
        if problems:
            for msg in problems[:20]: log(f"  REFUSED: {msg}")
            log(f"RUN refused: {len(problems)} query-tree problem(s) under {QUERIES}. "
                f"Fix the staging, or pass --allow-mixed-tree.")
            return 2
    todo = [f for f in files
            if led.get(relkey(f), {}).get("status") not in ("fetched", "submitted", "submit_failed_parked", "unsure", "retrieval_unverified", "query_unbound")]

    deadline = time.time() + args.hours*3600
    inflight = {}          # rid -> [faa, last_poll, submit_epoch]
    poll_errs = {}         # rid -> consecutive status-poll error count (reset on any success)
    requests = []          # epoch of every submit and status check, for the hourly rate line
    last_rate_log = time.time()
    # Failed retrieval retries the same RID; only a bound complete XML roster is admitted.
    # RESUME: re-poll live RIDs from a previous/other run instead of resubmitting them.
    # Carry each RID's original submit time so the WAITING age-out (below) can retire zombies.
    #
    # 2026-09-10: this loop used to require faa.exists() to resume a RID at all -- silently
    # dropping any RID whose query file no longer sits under THIS lane's QUERIES root. A lane
    # rebalance (e.g. the 4->8 split) moves query files between lane roots without touching any
    # other lane's ledger, so the SOURCE lane's ledger keeps a "submitted" row for a RID it will
    # never poll again, while the DESTINATION lane doesn't know the RID exists and eventually
    # resubmits the same query from scratch. Confirmed 16 such orphans across lanes A-D after this
    # session's split, one submitted 2026-09-09 09:12 and still READY-but-unclaimed >28h later --
    # a genuinely completed result sitting at NCBI, going unfetched, until manually reaped.
    # Resume bookkeeping remains visible when a query moved. Retrieval now holds unbound
    # or missing local query material rather than certifying results from an unknown roster.
    orphaned_resumed = 0
    for key, r in led.items():
        if r.get("status") in ("submitted", "retrieval_unverified") and r.get("rid"):
            faa = QUERIES / key
            if not faa.exists():
                orphaned_resumed += 1
            inflight[r["rid"]] = [faa, 0.0, iso_to_epoch(r.get("submit_iso", ""))]
    if orphaned_resumed:
        log(f"  WARNING: {orphaned_resumed} resumed RID(s) have no local query file under "
            f"{QUERIES} (likely moved by a lane rebalance) -- still polling them; retrieval "
            f"is held until the original query binding can be reconciled.")
    log(f"RUN start: {len(files)} query files, {len(todo)} to submit, "
        f"{len(inflight)} live RIDs resumed. hours={args.hours} sleep={args.sleep}s "
        f"max_inflight={args.max_inflight} hold_after={args.hold_after:.0f}s max_held={args.max_held} "
        f"max_wait={args.max_wait:.0f}s min_aa={args.min_aa} max_aa={args.max_aa}")
    last_submit = 0.0
    idx = 0
    submitted = fetched = failed = 0
    consec_err = 0         # consecutive submit failures -> exponential backoff (network-outage safe)
    MAX_SUBMIT_RETRIES = 30  # per-FILE submit-fail cap: a poison-pill query (e.g. one NCBI persistently
    # refuses) is PARKED after this many fails so it can't stall a lane indefinitely (the 2026-09-01
    # two-strain incident: one file failed 240x/211x over ~20h). At ~300s max backoff, 30 fails ≈ 2.5h
    # of trying — long enough that a genuine network outage self-heals first, short enough that a true
    # poison pill is skipped instead of parking the whole lane.
    submit_fails = {}      # key -> consecutive submit failures for THAT file (distinct from global consec_err)
    next_submit_ok = 0.0   # don't attempt a submit before this time (backoff gate)
    pending = None         # the file we're currently trying to submit (retried, never skipped)

    while time.time() < deadline and (idx < len(todo) or pending or inflight):
        if args.limit and submitted >= args.limit and not inflight:
            break
        nowt = time.time()
        # pick the next file to (re)try; keep it 'pending' until it actually submits
        if pending is None and idx < len(todo) and not (args.limit and submitted >= args.limit):
            pending = todo[idx]; idx += 1
        # SUBMIT (only when paced AND not inside a backoff window)
        held = sum(1 for v in inflight.values() if nowt - v[2] >= args.hold_after)
        active = len(inflight) - held
        if (pending is not None and nowt - last_submit >= paced_sleep(args.sleep) and nowt >= next_submit_ok
                and active < args.max_inflight and held < args.max_held):
            faa = pending
            key = relkey(faa); strain, bgc = Path(key).parts[0], Path(key).parts[1]
            last_submit = nowt          # respect pace whether or not this one succeeds
            text = faa.read_text(errors="replace")
            why = unsearchable_reason(text, args.min_aa, args.max_aa, args.max_one_residue)
            if why:
                led[key] = {"strain": strain, "bgc": bgc, "file": key, "rid": "", "rtoe": 0,
                            "submit_iso": now_iso(), "status": "submit_failed_parked",
                            "fetch_iso": "", "note": f"not submitted: {why}"}
                save_ledger(led); pending = None; last_submit = 0.0
                log(f"  PARKED {key} before submit: {why}")
                continue
            requests.append(nowt)
            try:
                rid, rtoe = submit(text)
            except Exception as e:
                rid, rtoe = "", 0; log(f"  submit ERROR {key}: {str(e)[:150]}")
            if rid:
                inflight[rid] = [faa, 0.0, nowt]; submitted += 1; consec_err = 0; pending = None
                led[key] = {"strain": strain, "bgc": bgc, "file": key, "rid": rid,
                            "rtoe": rtoe, "submit_iso": now_iso(), "status": "submitted",
                            "query_sha256": _sha(faa.read_bytes()),
                            "query_roster": json.dumps([h for h, _ in read_fasta(text)]), "database": DATABASE,
                            "fetch_iso": "",
                            "note": ""}
                save_ledger(led)
                log(f"  submitted {key} -> RID {rid} (rtoe~{rtoe}s) [{submitted} sent, {len(inflight)} in-flight]")
            else:
                # submit failure (usually network). Back off and retry the SAME file — a transient
                # outage self-heals (backoff caps at 5 min). BUT cap per-file retries so a poison-pill
                # query that NCBI persistently refuses is PARKED instead of stalling the lane forever.
                consec_err += 1
                submit_fails[key] = submit_fails.get(key, 0) + 1
                if submit_fails[key] >= MAX_SUBMIT_RETRIES:
                    led[key] = {"strain": strain, "bgc": bgc, "file": key, "rid": "",
                                "rtoe": 0, "submit_iso": now_iso(), "status": "submit_failed_parked",
                                "fetch_iso": "", "note": f"parked after {submit_fails[key]} submit fails"}
                    save_ledger(led)
                    log(f"  PARKED {key} after {submit_fails[key]} submit failures (poison pill — NCBI "
                        f"persistently refused it); skipping so the lane advances. Re-try it manually.")
                    pending = None; consec_err = 0; next_submit_ok = 0.0   # advance to the next file
                else:
                    backoff = min(300, 20 * (2 ** min(consec_err, 4)))   # 40,80,160,300,300...
                    next_submit_ok = nowt + backoff
                    log(f"  submit failed x{submit_fails[key]} for {key}; backing off {backoff:.0f}s "
                        f"(retry the SAME file, job stays alive; parks at {MAX_SUBMIT_RETRIES}).")
        # POLL / FETCH
        for rid in list(inflight):
            faa, last_poll, sub_epoch = inflight[rid]
            key = relkey(faa)
            strain, bgc = Path(key).parts[0], Path(key).parts[1]
            age = time.time() - sub_epoch
            if age > args.max_wait:
                # Past the window: stop checking, and leave it for the operator. Never resubmit
                # automatically; resubmitting is what makes a slow service slower.
                led[key]["status"] = "unsure"
                led[key]["note"] = f"no result after {age/3600:.1f} h; operator to check or resubmit"
                save_ledger(led); del inflight[rid]; poll_errs.pop(rid, None); failed += 1
                log(f"  UNSURE {key} RID {rid}: no result after {age/3600:.1f} h — left for the operator")
                continue
            if time.time() - last_poll < poll_interval(age, poll_errs.get(rid, 0)): continue
            inflight[rid][1] = time.time()
            requests.append(time.time())
            try:
                st = status(rid)
                poll_errs.pop(rid, None)          # any success clears the counter
            except Exception as e:
                poll_errs[rid] = poll_errs.get(rid, 0) + 1
                log(f"  poll ERROR x{poll_errs[rid]} {rid}: {str(e)[:120]} "
                    f"(next check in {poll_interval(age, poll_errs[rid])/60:.0f} min)")
                # Keep the RID. Each consecutive error stretches the gap to the next check
                # (poll_interval), so a bad network costs a few requests an hour, not one a minute.
                continue
            # A WAITING RID stays in flight. Once older than --hold-after it no longer blocks a
            # submit slot (see the submit gate), and --max-wait above ends the wait.
            if st == "READY":
                attempt = evidence = None
                try:
                    requests.append(time.time())
                    try:
                        xml = fetch_xml2(rid)
                    except TransportUnverified as exc:
                        attempt, evidence = record_response(rid, exc.response, led[key])
                        raise
                    attempt, evidence = record_response(rid, xml, led[key])
                    raw = xml.encode("utf-8")
                    roster = evidence["queries"]
                    if led[key].get("database") != DATABASE or not roster or not faa.is_file() or not led[key].get("query_sha256") or _sha(faa.read_bytes()) != led[key]["query_sha256"]:
                        led[key]["status"] = "query_unbound"
                        led[key]["note"] = "retrieval held: local submitted query digest unavailable or changed"
                        save_ledger(led); del inflight[rid]
                        continue
                    if roster != [head for head, _ in read_fasta(faa.read_text())]:
                        raise RetrievalUnverified("submitted roster differs from bound local query")
                    rows = parse_xml2(xml, strain, bgc, defline_meta(faa), expected_queries=roster)
                    evidence = dict(schema=1, rid=rid, database=DATABASE, query_sha256=led[key]["query_sha256"],
                                    raw_sha256=_sha(raw), raw_file=attempt.name, queries=roster,
                                    status="COMPLETE_HITS" if rows else "COMPLETE_NO_HITS", rows=len(rows))
                    queried = {}
                    for title in roster:
                        sb = strain_bgc_of(title, strain, bgc)
                        queried.setdefault(sb, set()).add(gene_of(title))
                    for (rs, rb), genes in queried.items():
                        write_results(rs, rb, [r for r in rows if (r[0], r[1]) == (rs, rb)], replace_genes=genes)
                    evidence["result_groups"] = [dict(strain=rs, bgc=rb) for rs, rb in queried]
                    evidence["query_states"] = [dict(title=title, status="HITS" if any(
                        (r[0], r[1]) == strain_bgc_of(title, strain, bgc) and r[2] == gene_of(title)
                        for r in rows) else "NO_HITS") for title in roster]
                    _atomic_bytes(attempt.with_suffix(".admission.json"), json.dumps(evidence, sort_keys=True).encode())
                    _atomic_bytes(XMLDIR / f"{rid}-admission.json", json.dumps(evidence, sort_keys=True).encode())
                    led[key]["status"] = "fetched"; led[key]["fetch_iso"] = now_iso()
                    led[key]["note"] = f"{len(rows)} rows; " + evidence["status"]
                    save_ledger(led); fetched += 1; del inflight[rid]
                    log(f"  READY  {key} RID {rid}: {len(rows)} rows staged [{fetched} fetched]")
                except Exception as e:
                    if evidence is not None and attempt is not None:
                        evidence["status"] = "UNVERIFIED"
                        for state in evidence.get("query_states", []):
                            state["status"] = "UNVERIFIED"
                        evidence["error"] = f"{type(e).__name__}: {str(e)[:120]}"
                        _atomic_bytes(attempt.with_suffix(".admission.json"), json.dumps(evidence, sort_keys=True).encode())
                        _atomic_bytes(XMLDIR / f"{rid}-admission.json", json.dumps(evidence, sort_keys=True).encode())
                    led[key]["status"] = "retrieval_unverified"
                    led[key]["note"] = f"retrieval unverified: {type(e).__name__}: {str(e)[:120]}"
                    save_ledger(led)
                    log(f"  fetch ERROR {rid} {key}: {str(e)[:150]}")
            elif st in ("UNKNOWN",):
                # expired or failed RID; mark for resubmit next run
                led[key]["status"] = "expired"; led[key]["note"] = "RID UNKNOWN"; save_ledger(led)
                del inflight[rid]; failed += 1
                log(f"  UNKNOWN {key} RID {rid} — will retry on a later run")
            # else WAITING: leave in flight
        # ── manifest heartbeat (throttled to once per _HEARTBEAT_INTERVAL) ────────
        if _cm_heartbeat and time.time() - _LAST_HEARTBEAT >= _HEARTBEAT_INTERVAL:
            try:
                _cm_heartbeat(_MANIFEST_LANE, pid=os.getpid(),
                              inflight=len(inflight), fetched_this_run=fetched,
                              submitted_this_run=submitted,
                              status="polling" if inflight else "idle")
            except Exception as exc:
                _heartbeat_failed(exc)  # manifest is advisory — never block the crawl
            _LAST_HEARTBEAT = time.time()
        if time.time() - last_rate_log >= 3600:
            cutoff = time.time() - 3600
            requests = [r for r in requests if r >= cutoff]
            held_now = sum(1 for v in inflight.values() if time.time() - v[2] >= args.hold_after)
            log(f"  RATE last hour: {len(requests)} NCBI requests ({len(requests)/60:.1f}/min); "
                f"{len(inflight)} in flight, {held_now} held")
            last_rate_log = time.time()
        time.sleep(5)

    # Final heartbeat: mark lane as stopped
    if _cm_heartbeat:
        try:
            _cm_heartbeat(_MANIFEST_LANE, pid=os.getpid(),
                          inflight=len(inflight), fetched_this_run=fetched,
                          submitted_this_run=submitted, status="stopped")
        except Exception as exc:
            _heartbeat_failed(exc)
    log(f"RUN end: {submitted} submitted, {fetched} fetched, {failed} failed/expired, "
        f"{len(inflight)} still in-flight (RIDs saved in ledger; rerun to fetch).")
    return 0


def cmd_rebuild():
    try:
        with lane_owner(): return _owned_rebuild()
    except (ValueError, OSError) as exc:
        print(f"REBUILD refused: {exc}", file=sys.stderr); return 3


def _owned_rebuild():
    # Validate every admitted query before changing any result generation.
    led = load_ledger()
    groups, replacements, batches = {}, {}, 0
    for key, record in led.items():
        if record.get("status") != "fetched": continue
        if not retrieval_admitted(key, record):
            raise RetrievalUnverified(f"unbound fetched ledger: {key}")
        xmlf = XMLDIR / f"{record['rid']}-Alignment.xml"
        faa = QUERIES / key
        roster = [h for h, _ in read_fasta(faa.read_text())]
        rows = parse_xml2(xmlf.read_text(), record["strain"], record["bgc"], defline_meta(faa),
                          expected_queries=roster)
        for title in roster:
            sb = strain_bgc_of(title, record["strain"], record["bgc"])
            groups.setdefault(sb, [])
            replacements.setdefault(sb, set()).add(gene_of(title))
        for row in rows: groups.setdefault((row[0], row[1]), []).append(row)
        batches += 1
    for (strain, bgc), rows in sorted(groups.items()):
        write_results(strain, bgc, rows, replace_genes=replacements[(strain, bgc)], fresh=True)
    print(f"rebuilt {len(groups)} BGC result files from {batches} fetched batches")
    return 0


def cmd_coverage():
    # Per-BGC Mode-B readiness. A gene is RESOLVED once its batch FASTA is fetched — whether or
    # not it produced an nr hit ("no significant similarity" is itself a valid, card-worthy result
    # for an orphan/novel gene). So we gate on batch-fetched, and report hit-rate separately.
    led = load_ledger()
    want: dict[tuple[str, str], set] = {}          # all queried genes per BGC
    resolved: dict[tuple[str, str], set] = {}      # genes whose batch was fetched
    for f in all_query_files():
        strain, bgc = f.relative_to(QUERIES).parts[0], f.relative_to(QUERIES).parts[1]
        genes = {gene_of(h) for h, _ in read_fasta(f.read_text())}
        want.setdefault((strain, bgc), set()).update(genes)
        if led.get(relkey(f), {}).get("status") == "fetched" and retrieval_admitted(relkey(f), led[relkey(f)]):
            resolved.setdefault((strain, bgc), set()).update(genes)
    ready = partial = empty = 0
    partial_list = []
    for (strain, bgc), genes in sorted(want.items()):
        got = resolved.get((strain, bgc), set())
        hit = set()
        csvf = RESDIR / strain / bgc / f"{bgc}_top_hit_per_gene.csv"
        if csvf.exists():
            with csvf.open() as fh:
                rd = csv.reader(fh); next(rd, None)
                hit = {row[2] for row in rd if row}
        if not got: empty += 1
        elif genes - got: partial += 1; partial_list.append((strain, bgc, len(got), len(genes), len(hit)))
        else: ready += 1
    print(f"BGCs queried: {len(want)}  |  CARD-READY (every gene's batch fetched): {ready}  "
          f"|  partial: {partial}  |  not-yet-started: {empty}")
    if partial_list:
        print("partial BGCs (genes resolved / queried  [with-nr-hit]):")
        for s, b, r, t, h in partial_list[:40]:
            print(f"  {s}/{b}: {r}/{t}  [{h} hit]")
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--hours", type=float, default=24.0)
    r.add_argument("--sleep", type=float, default=50.0)
    r.add_argument("--limit", type=int, default=0, help="max submissions this run (0=all)")
    r.add_argument("--max-inflight", dest="max_inflight", type=int, default=2,
                   help="RIDs younger than --hold-after that may be in flight at once (default 2)")
    r.add_argument("--hold-after", dest="hold_after", type=float, default=3600.0,
                   help="seconds after which a waiting RID stops occupying a submit slot (default 1 h)")
    r.add_argument("--max-held", dest="max_held", type=int, default=4,
                   help="held RIDs a lane may carry before it stops submitting (default 4)")
    r.add_argument("--min-aa", dest="min_aa", type=int, default=20,
                   help="park single-protein queries shorter than this (default 20)")
    r.add_argument("--max-aa", dest="max_aa", type=int, default=1000,
                   help="park single-protein queries at least this long, to run by hand (0 = off; default 1000)")
    r.add_argument("--max-one-residue", dest="max_one_residue", type=float, default=0.6,
                   help="park single-protein queries where one residue exceeds this fraction (default 0.6)")
    r.add_argument("--ignore-handoff", dest="ignore_handoff", action="store_true",
                   help="run a lane even though _HANDOFF_OUT.txt says another machine has it")
    r.add_argument("--allow-mixed-tree", dest="allow_mixed_tree", action="store_true",
                   help="run even if the query tree mixes panel sizes or stages a sequence twice")
    r.add_argument("--max-wait", dest="max_wait", type=float, default=129600.0,
                   help="seconds a RID is waited for before it is marked `unsure` for the operator "
                        "(default 36 h). It is never resubmitted automatically. "
                        "Must exceed NCBI's real compute time, else slow-but-valid jobs get retired before "
                        "they finish and the pool churns without progress. This ONLY ever kills jobs NCBI "
                        "still reports as WAITING -- an expired or failed RID reports UNKNOWN and is reaped "
                        "immediately regardless of this value -- so a long window cannot strand a dead RID. "
                        "History: 2026-08-05 measured submit->fetch p95 ~173min on nr, and 45min retired "
                        "~94%% of jobs prematurely, livelocking the runner ~9h. That measurement no longer "
                        "describes ClusteredNR: on 2026-09-16/17 the 6h default livelocked five "
                        "_STRAINGAP_CLNR_* lanes outright, and RID ANGKV9CW014 was still WAITING at 21h43m "
                        "and returned 53 rows at 27h08m -- past the ~24h retention this text used to cite. "
                        "2026-09-25: RID B85Y1283016 answered UNKNOWN about 44 h after submission.")
    sub.add_parser("status")
    sub.add_parser("rebuild", help="re-derive staged CSVs from saved XML (merges multi-batch BGCs)")
    sub.add_parser("coverage", help="per-BGC gene completeness vs the query FASTAs")
    args = ap.parse_args()
    if args.cmd in ("run", "rebuild"):
        # The lane folder is ROOT-relative and ROOT falls back to the current directory; refuse
        # before the first write if that lands inside the code bundle.
        assert_output_outside_bundle(BASE, __file__, kind="BLASTp lane folder")
    if args.cmd == "status": cmd_status(); return 0
    if args.cmd == "rebuild": return cmd_rebuild()
    if args.cmd == "coverage": return cmd_coverage()
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
