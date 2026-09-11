
"""Configured data roots, local database lookup and checked external tool execution."""
from __future__ import annotations

import os
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
import pathlib
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import logging
_LOG = logging.getLogger(__name__)

__all__ = [
    "blast_bin", "mafft_bin", "root", "registry_row", "rrna16s_db", "refseq_16s_blastdb",
    "has_space", "space_free_workdir", "stage_file", "stage_blastdb", "run_checked",
    "reference_definition_hold", "reference_definition_from_fasta_header",
    "explicit_type_strain_target",
    "screen_query_records", "write_query_qc_tsv",
    "UNCULTURED_DEFINITION_SQL", "PhyloToolFailure",
]

_IUPAC_DNA = frozenset("ACGTRYSWKMBDHVN-.?")


def screen_query_records(records, *, fragment_threshold: int = 1200,
                         min_length: int = 200, max_length: int = 2500) -> list[dict]:
    """Screen query 16S records without trimming or changing their identifiers.

    The result distinguishes hard admission failures from warnings and records whether the
    placement aligner should use MAFFT's fragment mode. Lengths exclude gap punctuation; ambiguous
    IUPAC bases remain part of the admitted sequence and are reported rather than silently removed.
    """
    if min_length < 1 or fragment_threshold < min_length or max_length < fragment_threshold:
        raise ValueError("QUERY_QC_THRESHOLDS_INVALID")
    seen = set()
    rows = []
    for header, sequence in records:
        query_id = (header or "").split()[0]
        seq = re.sub(r"\s+", "", sequence or "").upper()
        ungapped = seq.replace("-", "").replace(".", "")
        unsupported = "".join(sorted(set(seq) - _IUPAC_DNA))
        ambiguous = sum(base not in {"A", "C", "G", "T", "U"} for base in ungapped)
        length = len(ungapped)
        holds = []
        warnings = []
        if not query_id:
            holds.append("QUERY_ID_MISSING")
        elif query_id in seen:
            holds.append("QUERY_ID_DUPLICATE")
        seen.add(query_id)
        if unsupported:
            holds.append("QUERY_UNSUPPORTED_SYMBOLS")
        if length < min_length:
            holds.append("QUERY_TOO_SHORT")
        if length > max_length:
            warnings.append("POSSIBLE_NON_16S_OR_UNTRIMMED")
        ambiguity_fraction = ambiguous / length if length else 0.0
        if ambiguity_fraction > 0.05:
            warnings.append("HIGH_AMBIGUITY")
        terminal_n = max(len(re.match(r"^N*", ungapped).group(0)),
                         len(re.search(r"N*$", ungapped).group(0))) if ungapped else 0
        if terminal_n >= 20:
            warnings.append("LONG_TERMINAL_N_RUN")
        rows.append({
            "query_id": query_id,
            "length": length,
            "ambiguity_fraction": ambiguity_fraction,
            "terminal_n_run": terminal_n,
            "fragmentary": length < fragment_threshold,
            "admission_state": "HOLD" if holds else "ADMITTED",
            "hold_reasons": holds,
            "warnings": warnings,
        })
    if not rows:
        raise ValueError("QUERY_FASTA_EMPTY")
    return rows


def write_query_qc_tsv(rows: list[dict], path) -> None:
    """Write the stable, reviewable query-admission receipt used by the 16S autopilot."""
    with open(path, "w") as handle:
        handle.write("query_id\tlength\tambiguity_fraction\tterminal_n_run\tfragmentary\t"
                     "admission_state\thold_reasons\twarnings\n")
        for row in rows:
            handle.write(
                f"{row['query_id']}\t{row['length']}\t{row['ambiguity_fraction']:.6f}\t"
                f"{row['terminal_n_run']}\t{str(row['fragmentary']).lower()}\t"
                f"{row['admission_state']}\t{'|'.join(row['hold_reasons'])}\t"
                f"{'|'.join(row['warnings'])}\n")


# One reference-admission vocabulary for every 16S front door. The SQL form bounds the database
# candidate pool before BLAST; the Python form covers FASTA and blastdbcmd producers. "Clone1"
# remains admissible because it can be an isolate name, while the separate word "clone" denotes
# an environmental clone in the definitions at issue.
UNCULTURED_DEFINITION_SQL = (
    "LOWER(definition) NOT LIKE 'uncultured%' "
    "AND LOWER(definition) NOT LIKE '%unidentified%' "
    "AND LOWER(definition) NOT LIKE '% clone %' "
    "AND LOWER(definition) NOT LIKE '% clone,%' "
    "AND LOWER(definition) NOT LIKE '%bacterium enrichment%'"
)


def reference_definition_hold(definition: str) -> str | None:
    """Return a typed reason when deposited text describes no named isolate reference."""
    value = re.sub(r"\s+", " ", (definition or "").strip()).lower()
    if value.startswith("uncultured"):
        return "UNCULTURED_DEFINITION"
    if "unidentified" in value:
        return "UNIDENTIFIED_DEFINITION"
    if re.search(r"(?<![a-z0-9])clone(?![a-z0-9])", value):
        return "ENVIRONMENTAL_CLONE_DEFINITION"
    if "bacterium enrichment" in value:
        return "ENRICHMENT_DEFINITION"
    return None


def reference_definition_from_fasta_header(header: str) -> str:
    """Drop the FASTA record identifier and return its definition text."""
    raw = (header or "").lstrip(">").strip()
    return raw.split(None, 1)[1] if " " in raw else raw


def explicit_type_strain_target(definition: str) -> tuple[str, str]:
    """Return the named target and bounded evidence for an explicit type-strain statement.

    Deposited organism names sometimes remain ``Genus sp.`` even though another field in the
    record states ``type strain of Genus species``. Preserve those as two claims: the deposited
    taxon stays unchanged and the named type target travels as explicit evidence. A generic
    ``type strain`` or ``type material`` flag has no named target and returns empty values.
    """
    text = re.sub(r"\s+", " ", (definition or "").strip())
    match = re.search(
        r"\btype\s+strain\s+of\s+([A-Z][A-Za-z-]+\s+[a-z][a-z-]+)(?=\b|[;,.)\]])",
        text,
    )
    if not match:
        return "", ""
    return match.group(1), match.group(0)


class PhyloToolFailure(RuntimeError):
    """An external tool did not run, or ran and failed. NEVER a measurement."""


def root() -> pathlib.Path:
    """The workspace root, by the same contract as `tools/find_asset.py`.

    Env first so an operator pack or an unusual layout can be pinned; then the engine's own
    resolver. No personal-path literal — the portability guard forbids one outside its single
    sanctioned home (`mamey/workspace_root.py`).
    """
    for var in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(var)
        if v:
            return pathlib.Path(v)
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from mamey.workspace_root import workspace_root as _wr
        return pathlib.Path(_wr())
    except Exception:
        raise SystemExit(
            "_phylo16s: no workspace root configured. Set SAPOTE_WORKSPACE_ROOT (or SAPOTE_ROOT), "
            "or run from a bundle where the mamey package is importable.")


def registry_row(asset_id: str) -> dict | None:
    """One row of `OFFICIAL_DATA/ASSET_REGISTRY.tsv`, or None. Same file `find_asset.py` reads.

    Reading the registry rather than hardcoding a path is what makes a shipped tool able to find a
    267 MiB asset it does not carry: the registry is the workspace's own statement of where its big
    local data lives, and `tools/register_compute_output.py` keeps it current by construction.
    """
    reg = root() / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv"
    if not reg.is_file():
        return None
    for ln in reg.read_text(errors="replace").splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("asset_id\t"):
            continue
        f = ln.split("\t")
        if len(f) >= 5 and f[0] == asset_id:
            f += [""] * max(0, 6-len(f))
            return dict(asset_id=f[0], kind=f[1], path=f[2], size=f[3],
                        guards=[g for g in f[4].split("|") if g], note=f[5])
    return None


_DB_ENV = "SAPOTE_16S_SQLITE"
_DB_REL = "16S Database/rrna16s.sqlite"


def rrna16s_db(explicit: str | None = None, must_exist: bool = True) -> str:
    """The 16S SQLite store. Resolution order, most specific first:

        1. `explicit` — a `--db` argument, so a caller can always override.
        2. `$SAPOTE_16S_SQLITE`.
        3. `OFFICIAL_DATA/ASSET_REGISTRY.tsv` row `rrna16s_db` (its `path` is the DIRECTORY;
           `rrna16s.sqlite` is the store inside it).
        4. `<root>/16S Database/rrna16s.sqlite`.

    `must_exist=True` REFUSES when nothing resolves to a file on disk, naming the builder. This is
    load-bearing: `sqlite3.connect()` on a missing path creates an empty database, every query then
    returns zero rows, and a panel built from it reports "no records matched" — a missing asset
    rendered as a finding. `must_exist=False` is for the builder itself, which creates the file.
    """
    if explicit:
        cand = pathlib.Path(explicit)
    elif os.environ.get(_DB_ENV):
        cand = pathlib.Path(os.environ[_DB_ENV])
    else:
        r = root()
        row = registry_row("rrna16s_db")
        cand = (r / row["path"]) if row else (r / _DB_REL)
        if row and (cand.is_dir() or cand.suffix.lower() not in (".sqlite", ".db", ".sqlite3")):
            cand = cand / "rrna16s.sqlite"
    if must_exist and not cand.is_file():
        raise SystemExit(
            f"16S database not found at {cand}\n"
            f"  It is a large local asset and is NOT shipped with the bundle (registered as\n"
            f"  `rrna16s_db` in OFFICIAL_DATA/ASSET_REGISTRY.tsv).\n"
            f"  Locate it:  python3 tools/find_asset.py rrna16s_db\n"
            f"  Build it:   python3 tools/phylo_16s_build_db.py\n"
            f"  Or pin it:  {_DB_ENV}=/path/to/rrna16s.sqlite   (or --db)\n"
            f"  Refusing rather than opening an empty database: every query would then return zero "
            f"rows, which reads as a finding.")
    return str(cand)


def refseq_16s_blastdb(explicit: str | None = None) -> str:
    """The local NCBI 16S RefSeq BLAST database PREFIX (no extension).

    `$SAPOTE_16S_DB` / `$NCBI_16S_DB` (the names `tools/comparator_select.py` and
    `tools/phylo_refset.py` already use), then the two locations this project keeps it in.
    """
    if explicit:
        return explicit
    for var in ("SAPOTE_16S_DB", "NCBI_16S_DB"):
        v = os.environ.get(var)
        if v:
            return v
    r = root()
    for rel in ("Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA",
                "blast_dbs/16S_ribosomal_RNA"):
        if (r / (rel + ".nin")).exists() or (r / (rel + ".nal")).exists():
            return str(r / rel)
    return str(r / "blast_dbs/16S_ribosomal_RNA")


def _bin(name: str, env_dir: str, *extra_dirs: str) -> str:
    """An external binary: `$<env_dir>` as a DIRECTORY, then PATH, then the conda envs this
    project uses. Refuses by name rather than returning a path that does not exist, because a
    nonexistent binary raises FileNotFoundError deep inside a loop instead of at the front door."""
    d = os.environ.get(env_dir)
    if d:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
        raise SystemExit(f"{env_dir}={d} does not contain {name}")
    w = shutil.which(name)
    if w:
        return w
    r = root()
    for rel in extra_dirs:
        p = r / rel / name
        if p.exists():
            return str(p)
    raise SystemExit(
        f"{name} not found. Put it on PATH, or set {env_dir} to the directory holding it "
        f"(this project keeps BLAST+ in a conda env; see docs/PHYLOGENETICS_WORKFLOW.md).")


def blast_bin(name: str) -> str:
    """`blastn` / `makeblastdb` / `blastdbcmd`. Honours `$BLAST_BIN` (a directory)."""
    return _bin(name, "BLAST_BIN", "miniconda3/envs/blast/bin")


def mafft_bin() -> str:
    """`mafft`. Honours `$MAFFT_BIN` (a directory)."""
    return _bin("mafft", "MAFFT_BIN", "miniconda3/envs/placement/bin",
                "miniconda3/envs/phylo/bin")


def has_space(path) -> bool:
    return " " in str(path)


def space_free_workdir(prefix: str = "phylo16s_"):
    """A temp directory guaranteed not to contain a space, or a refusal saying so.

    `tempfile` honours `$TMPDIR`, and a `$TMPDIR` with a space in it defeats the whole staging
    strategy — silently, because BLAST would then fail on the staged copy too. This checks the
    directory it actually got rather than assuming.
    """
    if not re.fullmatch(r'[A-Za-z0-9_-]+', prefix):
        raise ValueError('temporary prefix must be a safe filename component')
    d = tempfile.mkdtemp(prefix=prefix)
    if has_space(d):
        shutil.rmtree(d, ignore_errors=True)
        raise SystemExit(
            f"TMPDIR contains a space ({tempfile.gettempdir()!r}); NCBI BLAST+ cannot open a path "
            f"with a space in it, so staging there would fail the same way. Set TMPDIR to a "
            f"space-free directory and re-run.")
    return d


def stage_file(path, workdir, name: str | None = None) -> str:
    """A space-free path to `path` for BLAST. Copies only when the original has a space."""
    path = str(path)
    if not pathlib.Path(path).is_file():
        raise ValueError('staging input file is missing')
    if name and (pathlib.Path(name).name != name or has_space(name)):
        raise ValueError('staging name must be a space-free filename')
    if not has_space(path):
        return path
    dest = os.path.join(workdir, name or os.path.basename(path).replace(" ", "_"))
    shutil.copyfile(path, dest)
    return dest


def stage_blastdb(db_prefix, workdir) -> str:
    """A space-free prefix for an existing BLAST database, by SYMLINKING its volume files.

    A BLAST database is many files sharing one prefix (`.nin`, `.nsq`, `.nhr`, `.nal`, volume
    suffixes). Copying can be gigabytes; symlinks cost nothing and BLAST follows them. Only the
    spaced case does any work at all. Falls back to copying where symlinks are unavailable, and
    refuses if the prefix matches no file rather than handing BLAST a path that will fail as
    "database not found" — which is indistinguishable from an empty database.
    """
    db_prefix = str(db_prefix)
    if pathlib.Path(db_prefix + '.nal').exists():
        raise ValueError('BLAST alias provenance/staging hold: supply a direct volume prefix')
    if not any(pathlib.Path(db_prefix).parent.glob(pathlib.Path(db_prefix).name + '.*')):
        raise ValueError('BLAST database prefix has no volume files')
    if not has_space(db_prefix):
        return db_prefix
    src_dir = os.path.abspath(os.path.dirname(db_prefix) or ".")
    stem = os.path.basename(db_prefix)
    members = [f for f in os.listdir(src_dir) if f.startswith(stem + ".") and os.path.isfile(os.path.join(src_dir, f))]
    if not members:
        raise SystemExit(f"no BLAST database volumes found for prefix {db_prefix!r}")
    safe_stem = stem.replace(" ", "_")
    for f in members:
        dst = os.path.join(workdir, safe_stem + f[len(stem):])
        try:
            os.symlink(os.path.join(src_dir, f), dst)
        except (OSError, NotImplementedError):
            shutil.copyfile(os.path.join(src_dir, f), dst)
    return os.path.join(workdir, safe_stem)


def run_checked(cmd, what: str, allow_empty_stdout: bool = True, **kw):
    """`subprocess.run` whose exit code is READ. Returns the CompletedProcess; never None.

    On a nonzero exit this raises `SystemExit` naming the tool, the code, and the first 400
    characters of stderr — and, when any argument still contains a space, says so, because that is
    the single most common cause in this workspace and the error BLAST prints for it
    ("BLAST Database error: Database memory map file error") does not mention paths at all.

    `allow_empty_stdout=False` additionally refuses a zero exit that produced nothing, for the
    calls whose empty output would otherwise be read as "no records".
    """
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    try:
        p = subprocess.run(list(cmd), **kw)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f'{what} failed to execute: {exc}; no measurement available') from exc
    if p.returncode != 0:
        spaced = [a for a in cmd if isinstance(a, str) and " " in a]
        hint = ""
        if spaced:
            hint = ("\n  One or more arguments contain a SPACE, which NCBI BLAST+ cannot open:\n"
                    + "\n".join(f"    {a}" for a in spaced[:4])
                    + "\n  Stage the input behind a space-free path (see _phylo16s.stage_file / "
                      "stage_blastdb).")
        raise SystemExit(
            f"{what} FAILED: exit {p.returncode}. This is a TOOL FAILURE, not a result — do not "
            f"read the empty output as 'no hits'.\n"
            f"  cmd: {' '.join(str(a) for a in cmd)[:300]}\n"
            f"  stderr: {(p.stderr or '').strip()[:400]}{hint}")
    if not allow_empty_stdout and not (p.stdout or "").strip():
        raise SystemExit(
            f"{what} exited 0 but produced NO OUTPUT. Refusing to report that as an empty result; "
            f"re-check the database and the query.\n  cmd: "
            f"{' '.join(str(a) for a in cmd)[:300]}")
    return p



def sequence(value):
    """Normalized ungapped IUPAC DNA. Invalid or absent input is not a sequence."""
    value = (value or "").upper()
    if not value or re.search(r"[^ACGTRYSWKMBDHVN]", value):
        raise ValueError("missing sequence or unsupported nucleotide symbol")
    return value


def read_fasta(path):
    """Preserve headers; reject duplicate BLAST identifiers, empty records and preamble."""
    rows, ids, header = {}, set(), None
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                header = line[1:].strip()
                key = header.split()[0] if header else ""
                if not key or key in ids:
                    raise ValueError("empty or duplicate FASTA identifier")
                ids.add(key)
                rows[header] = ""
            elif header is None:
                raise ValueError("sequence before first FASTA header")
            else:
                rows[header] += line
    if not rows:
        raise ValueError("empty FASTA input")
    return {key: sequence(value) for key, value in rows.items()}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def accession(value, version_required=False):
    """Syntactic sequence accession check, never a claim of database membership."""
    value = value or ""
    suffix = r"\.[1-9][0-9]*" if version_required else r"(?:\.[1-9][0-9]*)?"
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*[0-9]" + suffix, value):
        raise ValueError("invalid or local sequence accession")
    return value


def read_database(path):
    """Open an existing database read-only, refusing uncheckpointed sidecar state.

    Refusing WAL/journal inputs keeps the file hash bound to the rows being read.
    Ask the database owner for a closed, checkpointed snapshot if this hold fires.
    """
    path = pathlib.Path(rrna16s_db(path)).resolve()
    if any(pathlib.Path(str(path) + s).exists() for s in ("-wal", "-journal")):
        raise ValueError("database has WAL/journal state; supply a checkpointed snapshot")
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    if not con.execute("PRAGMA table_info(record)").fetchall():
        con.close()
        raise ValueError("16S record schema is missing")
    return con


def database_copy(path):
    """In-memory working copy. The selected input is never a write target."""
    con = sqlite3.connect(":memory:")
    try:
        with closing(read_database(path)) as src:
            src.backup(con)
        return con
    except BaseException:
        con.close()
        raise


def require_new_output(path):
    path = pathlib.Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError("output exists; choose a new output path")
    if not path.parent.is_dir():
        raise ValueError("output parent directory does not exist")
    return path


def save_database(con, path, operation, details):
    """Publish an additive database; operation_event carries the completion receipt."""
    path = require_new_output(path)
    con.execute("CREATE TABLE IF NOT EXISTS operation_event "
                "(event_id INTEGER PRIMARY KEY, operation TEXT, timestamp TEXT, details_json TEXT)")
    con.execute("INSERT INTO operation_event(operation,timestamp,details_json) VALUES (?,?,?)",
                (operation, datetime.now(timezone.utc).isoformat(), json.dumps(details, sort_keys=True)))
    con.commit()
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("output database failed integrity_check")
    # Serialize the completed transaction before reserving its exclusive destination.
    blob = con.serialize()
    with path.open("xb") as handle:
        handle.write(blob)


def _selftest() -> int:
    bad = 0
    if has_space("/a b/c") is not True or has_space("/ab/c") is not False:
        bad += 1; _LOG.info("  FAIL has_space")
    try:
        run_checked([sys.executable, "-c", "import sys; sys.exit(3)"], "probe")
        bad += 1; _LOG.info("  FAIL run_checked did not refuse a nonzero exit")
    except SystemExit as e:
        if "exit 3" not in str(e):
            bad += 1; _LOG.info(f"  FAIL refusal text: {e}")
    _LOG.info("PASS _phylo16s selftest" if not bad else f"{bad} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(_selftest() if "--test" in sys.argv else (_LOG.info(__doc__.split("\n\n")[0]) or 0))
