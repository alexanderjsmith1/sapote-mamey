from __future__ import annotations
import json, os, re, zipfile, io, warnings
from pathlib import Path
from .assembly import metrics_from_sequences
from .models import BGCRecord, AssemblyMetrics, CDSFeature, DomainFeature
from .crosswalk import enrich_bgc_crosswalk, region_label, infer_node_id
from .antismash_evidence import parse_antismash_evidence, apply_evidence_to_bgcs
from .ziputil import regular_file_names

FASTA_EXTS = (".fasta", ".fa", ".fna", ".ffn")
GBK_EXTS = (".gbk", ".gbff", ".gb")

# v9.7.409 (DEEP_AUDIT2_resource_dos #3): the per-region GBK read (`zf.read(name)` / streaming
# SeqIO.parse) pulls the whole uncompressed GBK into memory with NO size cap — the 5 MB guard at
# extract_antismash_version() only covers the version-JSON fallback. A single crafted GBK (one huge
# /translation, or a highly repetitive decompression bomb) expands unbounded in RAM here. Refuse a
# GBK whose UNCOMPRESSED size exceeds the cap, or whose compression ratio looks like a zip bomb,
# BEFORE reading it. Both env-overridable.
_GBK_MAX_UNCOMPRESSED_BYTES = 100_000_000       # 100 MB: far above any real region/full-assembly GBK
_GBK_MAX_COMPRESSION_RATIO = 200                # uncompressed/compressed ratio above this = bomb-like


def _gbk_guard_limits() -> tuple[int, int]:
    """``(max_bytes, max_ratio)`` for the GBK size guard, read from the environment at call time."""
    try:
        max_bytes = int(os.environ.get("MAMEY_GBK_MAX_BYTES", str(_GBK_MAX_UNCOMPRESSED_BYTES)))
    except (TypeError, ValueError):
        max_bytes = _GBK_MAX_UNCOMPRESSED_BYTES
    try:
        max_ratio = int(os.environ.get("MAMEY_GBK_MAX_RATIO", str(_GBK_MAX_COMPRESSION_RATIO)))
    except (TypeError, ValueError):
        max_ratio = _GBK_MAX_COMPRESSION_RATIO
    return max_bytes, max_ratio


def _gbk_size_guard(info: "zipfile.ZipInfo") -> str | None:
    """Return a refusal reason if this zip member is too large / bomb-like to read, else None."""
    max_bytes, max_ratio = _gbk_guard_limits()
    size = getattr(info, "file_size", 0) or 0
    comp = getattr(info, "compress_size", 0) or 0
    if size > max_bytes:
        return f"uncompressed size {size} exceeds MAMEY_GBK_MAX_BYTES={max_bytes}"
    if comp > 0 and size / comp > max_ratio:
        return f"compression ratio {size // max(comp, 1)}x exceeds MAMEY_GBK_MAX_RATIO={max_ratio} (decompression-bomb guard)"
    return None


class GbkSizeGuardRefusal(ValueError):
    """Typed refusal: a zip member failed the GBK size / compression-ratio guard and was NOT loaded.

    v9.7.410 (CLAUDE_410_gbk_size_guard_all_reads): the .409 guard was wired to only the SeqIO
    read in read_genbank_records(); every other member read (_safe_read_text → FASTA / region
    bounds / version JSON; antismash_input._first_region_header; detect_strictness saccharide
    fallback) still pulled the full uncompressed member into RAM. All of them now go through
    _guarded_read_bytes() and surface this one typed error (message prefix
    ``GBK_SIZE_GUARD_REFUSED:``) instead of a silent full load.
    """

    def __init__(self, member: str, reason: str):
        super().__init__(f"GBK_SIZE_GUARD_REFUSED: {member}: {reason}")
        self.member = member
        self.reason = reason


def _guarded_read_bytes(zf: zipfile.ZipFile, name: str, limit: int | None = None) -> bytes:
    """Read a zip member with the GBK size guard applied BEFORE and DURING the read.

    1. ``getinfo()`` preflight through :func:`_gbk_size_guard` (declared size / ratio).
    2. Bounded streaming read: at most ``limit`` bytes when given (header peeks), otherwise
       ``cap + 1`` bytes so a member whose central-directory size lies about its real size is
       still refused rather than decompressed in full.
    Raises :class:`GbkSizeGuardRefusal`; never returns more than the cap.
    """
    info = zf.getinfo(name)
    reason = _gbk_size_guard(info)
    if reason:
        raise GbkSizeGuardRefusal(name, reason)
    max_bytes, _ = _gbk_guard_limits()
    with zf.open(name) as fh:
        if limit is not None:
            return fh.read(max(0, min(limit, max_bytes)))
        data = fh.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise GbkSizeGuardRefusal(
            name,
            f"streamed size exceeds MAMEY_GBK_MAX_BYTES={max_bytes} "
            f"(central directory declared {info.file_size} bytes)")
    return data


def _safe_read_text(zf: zipfile.ZipFile, name: str) -> str:
    """Decode a zip member as UTF-8 text. Raises GbkSizeGuardRefusal for an over-cap / bomb-like
    member instead of loading it (v9.7.410; previously an unbounded ``zf.read``)."""
    return _guarded_read_bytes(zf, name).decode("utf-8", errors="replace")


def is_macos_cruft(name: str) -> bool:
    """True for macOS archive artifacts that are not real package files.

    Covers ``__MACOSX/`` resource-fork trees, AppleDouble ``._`` sidecars, and
    ``.DS_Store``. These satisfy naive extension/substring filters (e.g. a
    ``._NODE_x.region001.gbk`` shadow ends in ``.gbk`` and contains 'region'),
    so any consumer that counts or parses ZIP entries by a bare
    ``endswith()`` + substring predicate would otherwise double-count them or
    pollute empty/errored-record diagnostics. Strip at the point names first
    enter the system so no downstream counter has to know about AppleDouble.
    (v9.7.152 / engine 1.9.101 — see AUDIT_AS-XXX_macosx_appledouble.)
    """
    base = name.rsplit("/", 1)[-1]
    return (
        name.startswith("__MACOSX/")
        or "/__MACOSX/" in name
        or base.startswith("._")
        or base == ".DS_Store"
    )

def extract_antismash_version(
    zip_path: str | Path,
    *,
    refused_members: set[str] | None = None,
) -> str | None:
    """Extract antiSMASH version without loading the full JSON.

    The version is always within the first few KB of the antiSMASH JSON, so we
    read only a bounded prefix and regex it out. This avoids json.loads on a
    159 MB document just to read a version string.
    """
    refused = refused_members if refused_members is not None else set()
    with zipfile.ZipFile(zip_path) as zf:
        # Prefer small JSON files; for any JSON, read only a bounded prefix.
        json_names = [n for n in regular_file_names(zf) if n.lower().endswith(".json") and not is_macos_cruft(n)]
        for name in json_names:
            if name in refused:
                continue
            try:
                prefix = _guarded_read_bytes(zf, name, limit=8192).decode(
                    "utf-8", errors="replace"
                )
            except GbkSizeGuardRefusal as exc:
                refused.add(name)
                warnings.warn(
                    f"extract_antismash_version: {exc}; member skipped",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            except Exception:
                continue
            m = re.search(r'"(?:antismash_)?version"\s*:\s*"([^"]+)"', prefix)
            if m:
                _v = m.group(1)
                if "dev" in _v.lower() and "-" not in _v:
                    _g = _antismash_version_from_gbk(
                        zip_path, refused_members=refused
                    )
                    if _g and len(_g) > len(_v):
                        return _g
                return _v
        # Fallback: small JSON files can be safely parsed in full.
        for name in json_names:
            if name in refused:
                continue
            if zf.getinfo(name).file_size > 5_000_000:
                continue
            try:
                data = json.loads(_safe_read_text(zf, name))
            except GbkSizeGuardRefusal as exc:
                refused.add(name)
                warnings.warn(
                    f"extract_antismash_version: {exc}; member skipped",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            except Exception:
                continue
            if isinstance(data, dict):
                for key in ("version", "antismash_version"):
                    if key in data:
                        return str(data[key])
                meta = data.get("metadata") or {}
                if isinstance(meta, dict):
                    for key in ("version", "antismash_version"):
                        if key in meta:
                            return str(meta[key])
    # v9.7.185 P8: JSON often records a bare dev label ("8.dev"); the region GBK structured comment
    # carries the full build string with git hash ("8.dev-cf2fc5ee(changed)"). Prefer the richer one.
    _gbk_ver = _antismash_version_from_gbk(
        zip_path, refused_members=refused
    )
    if _gbk_ver:
        return _gbk_ver
    return None


def _antismash_version_from_gbk(
    zip_path: str | Path,
    *,
    refused_members: set[str] | None = None,
) -> str | None:
    """Read the antiSMASH version from a region GBK's ##antiSMASH-Data## structured comment."""
    refused = refused_members if refused_members is not None else set()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            gbks = [n for n in regular_file_names(zf)
                    if n.lower().endswith(GBK_EXTS) and not is_macos_cruft(n)]
            for name in sorted(gbks):
                if name in refused:
                    continue
                try:
                    head = _guarded_read_bytes(zf, name, limit=8192).decode(
                        "utf-8", errors="replace"
                    )
                except GbkSizeGuardRefusal as exc:
                    refused.add(name)
                    warnings.warn(
                        f"_antismash_version_from_gbk: {exc}; member skipped",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    continue
                m = re.search(r"##antiSMASH-Data-START##.*?Version\s*::\s*([^\n]+)", head, re.S)
                if m:
                    return m.group(1).strip()
    except Exception:
        return None
    return None

def _record_contig_id(rec) -> str:
    """Return the physical contig identifier from a GenBank record.

    Biopython uses the VERSION line as ``rec.id``. For SPAdes-style antiSMASH
    region GBKs, a contig such as ``NODE_1_length_457136_cov_55.054054`` can
    become ``NODE_1_length_457136_cov_55.54054`` because ACCESSION/VERSION
    treats the coverage decimal as a sequence version. The LOCUS token survives
    as ``rec.name``. Prefer it for NODE_*_length_*_cov_* records so FASTA/GBK
    joins and true contig-length lookup remain exact. For normal accession
    records, keep Biopython's ``rec.id`` behavior.
    """
    rec_id = str(getattr(rec, "id", "") or "").strip()
    rec_name = str(getattr(rec, "name", "") or "").strip()
    if rec_name and rec_name not in {".", "<unknown name>", "<unknown>"}:
        if re.match(r"^NODE_\d+_length_\d+_cov_", rec_name, flags=re.I):
            return rec_name
    return rec_id or rec_name


def _replicon_intake_key(item) -> tuple[int, str]:
    """Order chromosome records before plasmids without rereading the archive.

    antiSMASH exports do not provide one universal replicon field, so this uses
    only explicit text already present on the parsed record and source member.
    Unknown or contradictory labels retain deterministic lexical order after
    the recognized chromosome and plasmid groups.
    """
    source_name, rec = item
    annotations = getattr(rec, "annotations", {}) or {}
    text = " ".join(
        str(value or "")
        for value in (
            source_name,
            getattr(rec, "id", ""),
            getattr(rec, "name", ""),
            getattr(rec, "description", ""),
            annotations.get("replicon", ""),
            annotations.get("chromosome", ""),
        )
    ).lower()
    has_chromosome = bool(re.search(r"\bchromosome\b", text))
    has_plasmid = bool(re.search(r"\bplasmid\b", text))
    priority = 0 if has_chromosome and not has_plasmid else 1 if has_plasmid and not has_chromosome else 2
    return priority, str(source_name).casefold()


def read_fasta_sequences_from_zip(zip_path: str | Path) -> dict[str, str]:
    """Return the complete admitted FASTA sequence set from an archive.

    A member-level size/refusal guard cannot safely degrade to a partial return:
    every production caller treats a non-empty mapping as the complete assembly
    and suppresses its GenBank fallback.  Propagate the typed refusal so callers
    cannot publish subset-derived assembly metrics, boundary lengths, or scans.
    """
    seqs = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in regular_file_names(zf):
            if name.lower().endswith(FASTA_EXTS) and not is_macos_cruft(name):
                # v9.7.410 correction: _safe_read_text propagates
                # GbkSizeGuardRefusal. Returning the other members would make a
                # partial assembly indistinguishable from a complete one.
                text = _safe_read_text(zf, name)
                cur, parts = None, []
                for line in text.splitlines():
                    if line.startswith(">"):
                        if cur:
                            seqs[cur] = "".join(parts)
                        # PARSE-02: tolerate a bare ">" header (no id token) rather than
                        # raising IndexError on split()[0]; synthesize a stable placeholder id.
                        _tok = line[1:].split()
                        cur = _tok[0] if _tok else f"unnamed_{len(seqs)+1}"
                        parts = []
                    elif cur:
                        parts.append(line.strip())
                if cur:
                    seqs[cur] = "".join(parts)
    return seqs

def _require_seqio():
    """Import Biopython lazily.

    This keeps `python -m mamey validate ...` and JSON/TXT-only utilities usable
    in restricted sandboxes that do not have Biopython installed. GenBank-backed
    run paths still require Biopython and fail with a clear message.
    """
    try:
        from Bio import SeqIO  # type: ignore
        return SeqIO
    except ImportError:
        return None


def region_gbk_count(zip_path: str | Path) -> int:
    """How many antiSMASH REGION GBKs a ZIP actually offers the parser.

    Selection is deliberately identical to ``read_genbank_records(region_only=True)``:
    a GBK extension, not macOS cruft, and "region" in the BASENAME (not anywhere in the
    path, which would also match a directory called ``regions/``). Counting by a bare
    ``name.endswith(".gbk") and "region" in name`` substring test double-counts every
    AppleDouble shadow in a Finder-made ZIP — exactly the hazard ``is_macos_cruft``
    documents — so this is the single place that count should come from.

    Returns 0 for an unreadable ZIP: callers treat 0 as "no expectation to check against"
    rather than as evidence of emptiness.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return sum(1 for n in regular_file_names(zf)
                       if n.lower().endswith(GBK_EXTS) and not is_macos_cruft(n)
                       and "region" in Path(n).name.lower())
    except Exception:
        return 0


def read_genbank_records(zip_path: str | Path, region_only: bool = False,
                         exclude_regions: bool = False):
    SeqIO = _require_seqio()
    records = []
    errored: list[str] = []        # GBKs that raised during parse
    empty: list[str] = []          # GBKs that parsed without error but yielded 0 records
    # v9.7.173: fail clearly on a directory input. A sealed Mamey package dir has no GBKs and
    # stores parsed JSON (not translations), so `mamey compare <package_dir>` used to crash with
    # a raw IsADirectoryError from zipfile.ZipFile below. Give an actionable message instead.
    if Path(zip_path).is_dir():
        raise ValueError(
            f"read_genbank_records expects an antiSMASH output ZIP, got a directory: {zip_path}. "
            f"A sealed Mamey package stores parsed JSON (no GenBank records / protein "
            f"translations); pass the strain's antiSMASH output ZIP instead.")
    # v9.7.184 P1: accept a single .gbk/.gb/.gbff file directly. The blastp-online --package help
    # advertises "antiSMASH region GBK/ZIP", but a bare GBK fell straight into ZipFile below and
    # raised BadZipFile. Parse the file in place instead, mirroring the zip path's record shape.
    _p = Path(zip_path)
    if _p.is_file() and _p.suffix.lower() in GBK_EXTS:
        name = _p.name
        if region_only and "region" not in name.lower():
            return []
        try:
            if SeqIO is not None:
                with open(_p, encoding="utf-8", errors="replace") as handle:
                    for rec in SeqIO.parse(handle, "genbank"):
                        records.append((name, rec))
            else:
                from ._gbk_shim import parse_genbank_text
                for rec in parse_genbank_text(_p.read_text(encoding="utf-8", errors="replace")):
                    records.append((name, rec))
        except Exception as exc:
            raise ValueError(f"could not parse GenBank file {name}: {exc}") from exc
        return records
    with zipfile.ZipFile(zip_path) as zf:
        gbks = [n for n in regular_file_names(zf) if n.lower().endswith(GBK_EXTS) and not is_macos_cruft(n)]
        if region_only:
            gbks = [n for n in gbks if "region" in Path(n).name.lower()]
        elif exclude_regions:
            # v9.7.105 fix: the genome-wide CDS inventory must come from the full-assembly
            # GBK(s) only. Per-region GBKs carry REGION-LOCAL coordinates; mixing them in
            # duplicates every CDS at a shifted frame, which piles low-coordinate copies into
            # the first region (closed-genome scoping bug). Every region CDS is already present
            # in the full assembly, so excluding region files loses nothing.
            _full = [n for n in gbks if "region" not in Path(n).name.lower()]
            if _full:                      # only exclude when a full-assembly GBK exists
                gbks = _full
        total_gbks = len(gbks)
        for name in sorted(gbks):
            n_before = len(records)
            # v9.7.409 (DEEP_AUDIT2_resource_dos #3): refuse an over-large / bomb-like GBK BEFORE
            # loading it into RAM. Treated as a skipped (errored) member so the existing skip
            # diagnostic surfaces it — one refused file must not abort the rest of the package.
            try:
                _too_big = _gbk_size_guard(zf.getinfo(name))
            except Exception:
                _too_big = None
            if _too_big:
                errored.append(name)
                continue
            try:
                if SeqIO is not None:
                    with zf.open(name) as raw:
                        handle = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                        for rec in SeqIO.parse(handle, "genbank"):
                            records.append((name, rec))
                else:
                    from ._gbk_shim import parse_genbank_text
                    text = zf.read(name).decode("utf-8", errors="replace")
                    for rec in parse_genbank_text(text):
                        records.append((name, rec))
            except Exception:
                # Resilient by design: one malformed GBK must not abort the others.
                errored.append(name)
                continue
            # A GBK that parses cleanly but produces zero records is *also* a silent
            # drop — and the more insidious one, because no exception is raised. This
            # is exactly what produces downstream BGC-count mismatches the receipt
            # audit then has to diagnose from a distance, so surface it too.
            if len(records) == n_before:
                empty.append(name)
    skipped = errored + empty
    if skipped:
        def _names(lst):
            return ", ".join(Path(f).name for f in lst[:8]) + (" …" if len(lst) > 8 else "")
        detail = []
        if errored:
            detail.append(f"{len(errored)} errored [{_names(errored)}]")
        if empty:
            detail.append(f"{len(empty)} parsed-empty [{_names(empty)}]")
        warnings.warn(
            f"read_genbank_records: {len(skipped)}/{total_gbks} GBK file(s) yielded no "
            f"records in {zip_path}: " + "; ".join(detail),
            stacklevel=2,
        )
    return records

def assembly_metrics_from_zip(zip_path: str | Path) -> AssemblyMetrics:
    seqs = read_fasta_sequences_from_zip(zip_path)
    if seqs:
        return metrics_from_sequences(seqs)
    seqs = {}
    # PARSE-04: exclude clipped antiSMASH region GBKs from the contig set. They are region
    # spans, not source contigs, and multiple regions collapse onto one contig id — fabricating
    # genome_bp/contigs/n50 from clipped sequence. Same region-record test used in
    # _contig_length_map_from_zip / parse_bgcs_from_zip.
    for name, rec in read_genbank_records(zip_path, region_only=False):
        if "region" in Path(name).name.lower():
            continue
        _cid = _record_contig_id(rec)
        if _cid not in seqs or len(rec.seq) > len(seqs[_cid]):
            seqs[_cid] = str(rec.seq)
    # TODO PARSE-04: when every source record is a region GBK, seqs is empty and
    # metrics_from_sequences returns zeros/None (no fabrication) — the intended outcome. The
    # requested assembly_metrics_unavailable_region_only_input flag cannot be attached here
    # without changing the AssemblyMetrics dataclass schema (fixed positional fields used
    # project-wide); deferred rather than risk a wider refactor.
    return metrics_from_sequences(seqs)

def count_single_cand_clusters(features) -> int:
    """Number of /kind="single" cand_cluster features in a region record. >=3 marks a composite region:
    antiSMASH merged that many neighbouring protoclusters into one region, so its product string is a merge
    (not one hybrid cluster) and a single lead score aggregates them — flagged to avoid over-reading it."""
    n = 0
    for f in features:
        if getattr(f, "type", None) == "cand_cluster":
            kind = (f.qualifiers.get("kind") or [""])[0]
            if kind == "single":
                n += 1
    return n


def count_hybrid_cand_clusters(features) -> int:
    """FA3 / R1: number of cand_cluster features whose /kind="chemical_hybrid".

    antiSMASH assigns kind="chemical_hybrid" when protoclusters share cross-class biosynthetic
    module wiring (a genuinely FUSED pathway, e.g. an NRPS+T1PKS+polyhalogenated-pyrrole hybrid),
    distinct from kind="neighbouring"/"interleaved" (merely adjacent) and kind="single" (one class).
    This is the inverse of the composite_region merge-inflation flag (count_single_cand_clusters):
    it marks coherent multi-module architecture, not an over-merged product string.

    Claim-safe reading: a positive count means "multiple biosynthetic classes are fused in one
    candidate cluster" — a CAPACITY/architecture descriptor only, never a product or novelty claim."""
    n = 0
    for f in features:
        if getattr(f, "type", None) == "cand_cluster":
            kind = (f.qualifiers.get("kind") or [""])[0]
            if kind == "chemical_hybrid":
                n += 1
    return n


def cand_cluster_kinds(features) -> list[str]:
    """Return normalized antiSMASH cand_cluster ``/kind`` values.

    The list is structural parser evidence only. Unknown or blank values are
    retained as ``unknown`` rather than silently treated as a coherent region.
    """
    kinds: list[str] = []
    for feature in features:
        if getattr(feature, "type", None) != "cand_cluster":
            continue
        raw = (getattr(feature, "qualifiers", {}).get("kind") or [""])[0]
        kind = str(raw).strip().lower() or "unknown"
        kinds.append(kind)
    return kinds


def overmerge_state(kinds: list[str]) -> str:
    """Classify candidate-cluster structure without renaming or splitting a BGC."""
    normalized = [str(kind).strip().lower() for kind in kinds]
    if "chemical_hybrid" in normalized:
        return "COHERENT_CHEMICAL_HYBRID"
    if ({"neighbouring", "interleaved"} & set(normalized)) or normalized.count("single") >= 2:
        return "OVERMERGE_SUSPECT"
    if not normalized or "unknown" in normalized:
        return "NOT_VERIFIABLE"
    return "NO_OVERMERGE_SIGNAL"


def count_enediyne_ks_domains(features) -> int:
    """Count antiSMASH PKS_KS(Enediyne-KS) subtype domains in a region = the enediyne warhead PKS. A genuine
    enediyne carries >=1; a calicheamicin/neocarzinostatin/sporolide KCB similarity hit WITHOUT this domain is
    a mis-anchor (KCB = similarity, not identity), not a real enediyne."""
    n = 0
    for f in features:
        if any("enediyne" in s.lower() for s in f.qualifiers.get("domain_subtypes", [])):
            n += 1
            continue
        # fallback: the CDS NRPS_PKS domain description string "Domain: PKS_KS(Enediyne-KS) ..."
        if any("enediyne-ks" in v.lower() for v in f.qualifiers.get("NRPS_PKS", [])):
            n += 1
    return n


def count_pks_ks_domains(features) -> int:
    """Number of antiSMASH PKS_KS aSDomain features in a region record = its modular-PKS module count.
    Authoritative (the KS active-site motif under-counts real KS domains). A genuine polyene macrolide
    backbone has many (>=4); an NRPS/saccharide/RiPP/DUF692 locus has ~0."""
    n = 0
    for f in features:
        if getattr(f, "type", None) == "aSDomain" and (f.qualifiers.get("aSDomain") or [""])[0] == "PKS_KS":
            n += 1
    return n


def protocluster_breakdown(features) -> list:
    """Per-protocluster (product + region-local span) for a region record, sorted by start. De-inflates a
    composite region's merged product string into its constituent single-class protoclusters. Coordinates
    are region-local; protoclusters routinely overlap, which is why single-owner KCB/CCTT attribution is not
    forced (the region-level aggregate spans all of these)."""
    out = []
    for f in features:
        if getattr(f, "type", None) == "protocluster":
            try:
                rs, re_ = int(f.location.start), int(f.location.end)
            except Exception:
                rs, re_ = 0, 0
            out.append({
                "protocluster_number": int((f.qualifiers.get("protocluster_number") or [len(out) + 1])[0]),
                "product": _cap_qual((f.qualifiers.get("product") or ["?"])[0]),
                "rel_start": rs, "rel_end": re_,
            })
    out.sort(key=lambda p: p["rel_start"])
    return out


def _feature_products(feature) -> list[str]:
    vals = []
    for key in ("product", "products", "category", "aSDomain", "domain"):
        if key in feature.qualifiers:
            q = feature.qualifiers[key]
            vals.extend(q if isinstance(q, list) else [str(q)])
    out = []
    for v in vals:
        for part in re.split(r"[,;/]+", _cap_qual(str(v))):
            part = _cap_qual(part.strip())   # H12: a product token is a class label; never a 300 KB figure label
            if part and part not in out:
                out.append(part)
    return out

def _edge_status(start: int, end: int, contig_len: int, flank_bp: int = 5000,
                 is_circular: bool = False) -> str:
    if contig_len <= 0:
        return "Unknown"
    length = end - start + 1
    if length >= 0.95 * contig_len:
        return "Full-contig"
    # v9.7.87 P0-a: on a closed/circular replicon the origin is not a truncation point — a BGC
    # adjacent to the origin wraps, it is not Edge. Only call Edge near a contig boundary when the
    # topology is linear (or unknown). This fixes closed genomes getting a false Edge at the origin
    # (parsing-control FAIL, corrected < raw); e.g. N. nova NZ_CP006850, Solwaraspora_WMMA2065.
    if is_circular:
        return "Interior"
    if start <= flank_bp or (contig_len - end) <= flank_bp:
        return "Edge"
    return "Interior"

def architecture_grade(edge_status: str, products: list[str], length_bp: int, kcb_score=None,
                       has_chemical_hybrid: bool = False) -> tuple[str, str]:
    """Assign source-derived architecture confidence.

    A/B/C/D/E is a structural reliability grade, not a lead-priority score.
    KCB can support coherence when source-derived product labels are sparse,
    but it does not prove production or novelty.

    FA3 / R1: ``has_chemical_hybrid`` = antiSMASH flagged this region's cand_cluster
    /kind="chemical_hybrid" (a genuinely FUSED cross-class pathway; see
    count_hybrid_cand_clusters). When True on a region that also carries >=2 core-class
    labels, that is claim-safe evidence of a COHERENT multi-module architecture. It is fed
    in two claim-safe ways, both capacity-level (never a product/novelty/activity claim):
      1. A rationale note is appended so the fused-architecture capacity is visible on the
         lead board / Mode-B card (architecture_rationale is already surfaced downstream).
      2. A conservative, guarded grade promotion: a would-be "B" Interior region (core present
         but compact/limited) is lifted to "A", because the fused hybrid supplies the missing
         coherence evidence. Truncation grades (C/D/E) are NEVER promoted — the hybrid flag is
         orthogonal to edge/length truncation and must not paper over it.
    Because the promotion can move a published letter grade, it is CAT-01 (sign-off) class;
    on the current cohort it does not fire (Interior core regions are already "A"). See FA3_HOOK.
    """
    prod_text = " ".join(products).lower()
    core_terms = [
        "nrps", "pks", "ripp", "lanthipeptide", "terpene", "saccharide",
        "phosphonate", "siderophore", "metallophore", "lassopeptide",
        "thioamide", "tomm", "azole",
    ]
    has_core = any(x in prod_text for x in core_terms)
    distinct_core = sum(1 for x in core_terms if x in prod_text)
    high_kcb = kcb_score is not None and kcb_score >= 10000
    # A chemical_hybrid signal is only meaningful with >=2 distinct core classes fused (R1).
    hybrid_coherent = bool(has_chemical_hybrid) and distinct_core >= 2
    hybrid_note = (
        " Multiple biosynthetic classes are fused in one candidate cluster "
        "(antiSMASH chemical_hybrid): capacity-level coherent multi-module architecture, "
        "not a product/novelty/activity claim."
    ) if hybrid_coherent else ""

    if edge_status == "Interior" and has_core and length_bp >= 10000:
        return "A", "Interior BGC with coherent biosynthetic product annotation." + hybrid_note
    if edge_status == "Interior" and (has_core or high_kcb):
        if high_kcb and not has_core:
            return "B", "Interior BGC with strong KCB support but limited source-derived product/core annotation." + hybrid_note
        if hybrid_coherent:
            # CAT-01 promotion: fused multi-class architecture supplies the coherence a compact
            # Interior region otherwise lacks. Only Interior/core B is promoted; never truncation.
            return "A", "Interior BGC; compact but coherent." + hybrid_note
        return "B", "Interior BGC but product/core evidence is limited or compact."
    if edge_status == "Edge" and has_core:
        return "C", "Edge-truncated BGC with coherent product annotation; partial interpretation only." + hybrid_note
    if edge_status == "Edge":
        return "D", "Edge-truncated BGC with limited product annotation." + hybrid_note
    if edge_status == "Full-contig" and has_core:
        return "D", "Full-contig BGC; likely truncated on both ends and requires linkage/long-read confirmation." + hybrid_note
    return "E", "Weak/ambiguous architecture; inventory-level interpretation only." + hybrid_note


def _region_orig_bounds_from_zip(zip_path: str | Path) -> dict[str, tuple[int, int]]:
    """Return absolute antiSMASH region bounds keyed by GBK filename.

    antiSMASH region GBKs are clipped records whose feature coordinates restart
    at 1.  The absolute source-record coordinates are stored in the comment as
    ``Orig. start`` / ``Orig. end``.  Boundary classification must use these
    absolute coordinates plus the true contig length; otherwise a closed
    chromosome with many clipped region GBKs is falsely labeled Edge/Full-contig.
    """
    out: dict[str, tuple[int, int]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in regular_file_names(zf):
            if is_macos_cruft(name):
                continue
            if not name.lower().endswith(GBK_EXTS) or "region" not in Path(name).name.lower():
                continue
            try:
                text = _safe_read_text(zf, name)
            except GbkSizeGuardRefusal as exc:
                # v9.7.410: refused before any load (the same member is refused again, and
                # counted as errored, by read_genbank_records). Warn so the skip is not silent.
                warnings.warn(f"_region_orig_bounds_from_zip: {exc}; member skipped", stacklevel=2)
                continue
            except Exception:
                continue
            sm = re.search(r"Orig\.\s*start\s*::\s*(\d+)", text, flags=re.I)
            em = re.search(r"Orig\.\s*end\s*::\s*(\d+)", text, flags=re.I)
            if sm and em:
                out[name] = (int(sm.group(1)), int(em.group(1)))
    return out


def _contig_length_map_from_zip(zip_path: str | Path) -> dict[str, int]:
    """True source-record contig lengths from FASTA/full GenBank records."""
    seqs = read_fasta_sequences_from_zip(zip_path)
    if seqs:
        return {k: len(v) for k, v in seqs.items()}
    lengths: dict[str, int] = {}
    for name, rec in read_genbank_records(zip_path, region_only=False):
        # Skip clipped antiSMASH region GBKs; they are not contig-length records.
        if "region" in Path(name).name.lower():
            continue
        _cid = _record_contig_id(rec)
        lengths[_cid] = max(lengths.get(_cid, 0), len(rec.seq))
    return lengths

def _zip_has_record_json(zip_path: str | Path) -> bool:
    """True if the antiSMASH ZIP carries a record JSON.

    The record JSON is the source of KnownClusterBlast / RiQ evidence in
    bounded/full mode and the ONLY source of TIGRFAM diagnostics. A partial or
    web-exported ZIP of just region GBKs has none, in which case bounded/full
    silently degrade to TXT-only KCB with no TIGRFAM — see the preflight warning
    in parse_bgcs_from_zip.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return any(n.lower().endswith(".json") and not is_macos_cruft(n)
                       for n in regular_file_names(zf))
    except Exception:
        return False


def parse_bgcs_from_zip(zip_path: str | Path, json_mode: str = "off",
                         evidence: dict | None = None) -> list[BGCRecord]:
    # evidence: if a caller already parsed antiSMASH evidence (the run path parses it once for the
    # status dict), pass it in to avoid a second full record parse. Standalone callers leave it None
    # and the evidence is parsed here as before. Either way the result is identical: apply_evidence_to_bgcs
    # reads only by_region, which does not depend on want_tigrfam.
    bgcs = []
    seen = set()
    # PREFLIGHT: bounded/full ask for JSON evidence (KCB / RiQ / TIGRFAM), but a
    # partial or web-exported ZIP of only region GBKs carries no record JSON —
    # bounded then silently degrades to TXT-only KCB with NO TIGRFAM diagnostics.
    # Warn loudly instead of degrading in silence. (off never opens JSON, so the
    # absence is expected there and no warning fires.)
    if json_mode in ("bounded", "full") and not _zip_has_record_json(zip_path):
        warnings.warn(
            f"no antiSMASH record JSON in {Path(zip_path).name}: KCB will come "
            "from TXT clusterblast files (if present) and TIGRFAM diagnostics are "
            "UNAVAILABLE. Provide the full antiSMASH output (not just region GBKs) "
            "for complete evidence.",
            stacklevel=2,
        )
    records = read_genbank_records(zip_path, region_only=True) or read_genbank_records(zip_path, region_only=False)
    # E3: the records are already in memory; order this one read before assigning
    # locked BGC aliases so an explicitly labelled chromosome precedes plasmids.
    # Unknown or contradictory replicons follow without being guessed.
    records.sort(key=_replicon_intake_key)
    orig_bounds = _region_orig_bounds_from_zip(zip_path)
    contig_lengths = _contig_length_map_from_zip(zip_path)
    for name, rec in records:
        is_region_record = "region" in Path(name).name.lower()
        contig_id = _record_contig_id(rec)
        # PARSE-03: a clipped region GBK has no true contig length; len(rec.seq) is only the
        # region span, so falling back to it forced every region-only BGC to "Full-contig".
        # When this is a region record with no true contig length in the map, use 0 so
        # _edge_status returns "Unknown"; the non-region path is unchanged.
        if is_region_record and contig_id not in contig_lengths and rec.id not in contig_lengths:
            contig_len = 0
        else:
            contig_len = contig_lengths.get(contig_id, contig_lengths.get(rec.id, len(rec.seq)))
        # v9.7.87 P0-a: read the GenBank LOCUS topology token (biopython surfaces it as
        # annotations["topology"] == "circular"|"linear"). A closed/circular replicon has no
        # truncation point at the origin, so an origin-adjacent BGC must not be called Edge.
        _topo = str((rec.annotations or {}).get("topology", "")).lower()
        is_circular = (_topo == "circular")
        region_num = None
        m = re.search(r"region(\d+)", Path(name).name, flags=re.I)
        if m:
            region_num = int(m.group(1))
        products, start, end = [], 1, contig_len
        single_cc = count_single_cand_clusters(rec.features)
        _cand_kinds = cand_cluster_kinds(rec.features)
        _overmerge = overmerge_state(_cand_kinds)
        # FA3 / R1: does antiSMASH mark a fused cross-class pathway here? (cand_cluster
        # /kind="chemical_hybrid"). Capacity descriptor only; feeds the architecture grade note.
        hybrid_cc = count_hybrid_cand_clusters(rec.features)
        # v9.7.240 (P2): resolve the true protocluster list once; its length is the
        # protocluster count. One extra pass over features, needed unconditionally so
        # downstream gates never substitute single_cc for it.
        _pcb = protocluster_breakdown(rec.features)
        # Use antiSMASH absolute source bounds when parsing clipped region GBKs.
        # The region/cand_cluster feature coordinates inside these files are local
        # to the clipped record and almost always start at 1.
        if is_region_record and name in orig_bounds:
            start, end = orig_bounds[name]
        for f in rec.features:
            if f.type in {"region", "protocluster", "cand_cluster"}:
                products.extend(_feature_products(f))
                if not (is_region_record and name in orig_bounds):
                    try:
                        start = int(f.location.start) + 1
                        end = int(f.location.end)
                    except Exception as _deg_exc:
                        from . import degradation as _degradation
                        _degradation.record("parsers.parse_bgcs_from_zip.region_coords_fallback",
                                            _deg_exc, record=str(name))
        products = sorted(set(products))
        if not products:
            for f in rec.features:
                if f.type == "CDS":
                    products.extend(_feature_products(f)[:1])
                    if len(products) >= 3:
                        break
            products = sorted(set(products))
        key = (contig_id, region_num, start, end, tuple(products))
        if key in seen:
            continue
        seen.add(key)
        edge = _edge_status(start, end, contig_len, is_circular=is_circular)
        # Pre-evidence grade: provides initial values for BGCRecord construction.
        # Overwritten post-evidence (line ~392) once kcb_cumulative is available.
        grade, rationale = architecture_grade(edge, products, end - start + 1,
                                              has_chemical_hybrid=(hybrid_cc > 0))
        notes=[f"source_gbk={name}"]
        if is_region_record and name in orig_bounds:
            notes.append("absolute_coordinates_from_antismash_orig_start_end")
        elif is_region_record:
            notes.append("WARNING_region_gbk_lacks_orig_bounds_boundary_may_be_local")
        if single_cc >= 3:
            notes.append(f"COMPOSITE_REGION_{single_cc}_single_protoclusters_merged_product_string_and_lead_score_inflated")
        bgc = BGCRecord(
            bgc_id=f"BGC{len(bgcs)+1:03d}",
            contig=contig_id,
            region_number=region_num or (len(bgcs) + 1),
            start=start,
            end=end,
            contig_length=contig_len,
            antismash_region=region_label(region_num or (len(bgcs) + 1)),
            source_gbk=name,
            node_id=infer_node_id(contig_id, name),
            products=products,
            mibig_hits=[],
            edge_status=edge,
            architecture_confidence=grade,
            architecture_rationale=rationale,
            composite_region=(single_cc >= 3),
            single_protocluster_count=single_cc,
            has_chemical_hybrid=(hybrid_cc > 0),
            cand_cluster_kinds=_cand_kinds,
            overmerge_state=_overmerge,
            protocluster_count=len(_pcb),
            protocluster_breakdown=_pcb,  # AUG3_07: always retain so the scorer can de-inflate 2-protocluster merges
            ks_domain_count=count_pks_ks_domains(rec.features),
            ene_ks_count=count_enediyne_ks_domains(rec.features),
            notes=notes,
        )
        enrich_bgc_crosswalk(bgc, name)
        bgcs.append(bgc)
    if evidence is None:
        evidence = parse_antismash_evidence(zip_path, json_mode=json_mode)
    apply_evidence_to_bgcs(bgcs, evidence)
    for b in bgcs:
        grade, rationale = architecture_grade(b.edge_status, b.products, (b.end - b.start + 1),
                                              b.kcb_cumulative, has_chemical_hybrid=b.has_chemical_hybrid)
        b.architecture_confidence = grade
        b.architecture_rationale = rationale
    return bgcs

def extract_cds_features(zip_path: str | Path) -> list[CDSFeature]:
    cds = []
    seen = set()
    for name, rec in read_genbank_records(zip_path, region_only=False,
                                          exclude_regions=True):
        contig_id = _record_contig_id(rec)
        for f in rec.features:
            if f.type != "CDS":
                continue
            try:
                _loc = f.location
                _parts = list(getattr(_loc, "parts", []) or [])
                if len(_parts) > 1:
                    # v9.7.105 fix: origin-spanning / compound location (circular genome).
                    # The naive min..max span brackets the whole contig and false-overlaps
                    # every region; use the dominant (longest) part as representative coords.
                    _p = max(_parts, key=lambda p: int(p.end) - int(p.start))
                    start = int(_p.start) + 1
                    end = int(_p.end)
                    strand = int(_p.strand or 0)
                else:
                    start = int(_loc.start) + 1
                    end = int(_loc.end)
                    strand = int(_loc.strand or 0)
            except Exception:
                continue
            q = {k: [str(x) for x in v] for k, v in f.qualifiers.items()}
            locus = (q.get("locus_tag") or q.get("protein_id") or [None])[0]
            product = _cap_qual((q.get("product") or [None])[0])
            # v1.9.111: fold functional qualifiers into the product string so tailoring-enzyme
            # detection (glycosyltransferase, halogenase, P450, etc.) sees genes whose identity
            # lives in gene_functions/sec_met_domain/SMCOG, not the /product class label. This is
            # what lets the glycopeptide pre-check fire on machinery-bearing regions.
            _func_bits = []
            for _qk in ("gene_functions", "sec_met_domain", "gene_kind", "note"):
                for _v in q.get(_qk, []) or []:
                    _func_bits.append(_cap_qual(str(_v)))
            if _func_bits:
                product = ((product or "") + " " + " ".join(_func_bits)).strip()
            translation = (q.get("translation") or [None])[0]
            try:
                nucleotide_seq = str(f.extract(rec.seq)).upper()
            except Exception:
                nucleotide_seq = None
            key = (contig_id, start, end, strand, locus)
            if key in seen:
                continue
            seen.add(key)
            cds.append(CDSFeature(contig_id, start, end, strand, locus, product, translation, nucleotide_seq, q))
    return cds

def extract_contig_sequences(zip_path: str | Path) -> dict[str, str]:
    seqs = read_fasta_sequences_from_zip(zip_path)
    if seqs:
        return seqs
    out = {}
    for _, rec in read_genbank_records(zip_path, region_only=False):
        contig_id = _record_contig_id(rec)
        if contig_id not in out or len(rec.seq) > len(out[contig_id]):
            out[contig_id] = str(rec.seq)
    return out

def parse_antismash_evidence_status(zip_path: str | Path, json_mode: str = "off", include_structured: bool = False) -> dict:
    # want_tigrfam=True: this is the cli status path whose evidence feeds the tigrfam->gbk_pfam merge.
    return parse_antismash_evidence(zip_path, json_mode=json_mode, want_tigrfam=True, include_structured=include_structured)


# v9.7.409 (BC hostile audit H12): a region GBK with a 5 MB `/product` qualifier reached package CSVs
# (crashing csv read-back at the 128 KB default field limit) and figure labels (the render process was
# killed). Annotation text is attacker-controlled input; nothing scientific lives past a few thousand
# characters of a qualifier. Cap here, once, and say so in the value itself.
QUALIFIER_MAX_CHARS = 4000


def _cap_qual(value):
    """Truncate an over-long qualifier string; leaves non-strings and normal strings untouched."""
    if isinstance(value, str) and len(value) > QUALIFIER_MAX_CHARS:
        return value[:QUALIFIER_MAX_CHARS] + f" …[truncated {len(value) - QUALIFIER_MAX_CHARS} chars]"
    return value


def _qual_first(q: dict, keys: list[str]) -> str | None:
    for key in keys:
        if key in q and q[key]:
            return _cap_qual(str(q[key][0]))
    return None

def _parse_float_maybe(x):
    if x is None:
        return None
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None

def extract_domain_features(zip_path: str | Path) -> list[DomainFeature]:
    """Extract antiSMASH-specific domain/module features from GBKs.

    Prefer whole-record GBKs when they are present.  Region GBKs contain the
    same biological annotations in a clipped coordinate frame; mixing both
    sources duplicates domains and can assign region-local coordinates to the
    wrong BGC.  ``read_genbank_records(..., exclude_regions=True)`` retains
    region files only for archives that contain no whole-record GBK.
    """
    domains = []
    seen = set()
    wanted = {"aSDomain", "PFAM_domain", "CDS_motif", "aSModule"}   # antiSMASH type is aSModule, not "module" (Patch F Bug 1)
    for name, rec in read_genbank_records(
        zip_path, region_only=False, exclude_regions=True
    ):
        contig_id = _record_contig_id(rec)
        for f in rec.features:
            if f.type not in wanted:
                continue
            try:
                start = int(f.location.start) + 1
                end = int(f.location.end)
                strand = int(f.location.strand or 0)
            except Exception:
                continue
            q = {k: [str(x) for x in v] for k, v in f.qualifiers.items()}
            locus = _qual_first(q, ["locus_tag", "protein_id", "gene"])
            domain = _qual_first(q, ["aSDomain", "domain", "label", "description", "product", "tool", "database"])
            db = _qual_first(q, ["database", "db_xref", "tool"])
            bitscore = _parse_float_maybe(_qual_first(q, ["bitscore", "score", "domain_score"]))
            evalue = _qual_first(q, ["evalue", "E-value"])
            # Patch F Bug 2: A-domain substrate prediction lives in /specificity as
            # "substrate consensus: <aa>" (and C/E active-site motifs). Surface the monomer.
            substrate = ""
            for spec in q.get("specificity", []):
                s = str(spec)
                if "substrate consensus:" in s.lower():
                    substrate = s.split(":", 1)[1].strip()
                    break
            key = (contig_id, start, end, strand, f.type, domain, locus)
            if key in seen:
                continue
            seen.add(key)
            domains.append(DomainFeature(
                contig_id, start, end, strand, f.type, locus, domain, db,
                bitscore, evalue, substrate, q, source_file=name,
            ))
    return domains


def antismash_record_limit_truncation(input_zip) -> dict:
    """v9.7.187: detect an antiSMASH ``--limit`` record cap from the archived .log.

    antiSMASH analyses only the largest N ``--limit`` records (default 1000); any BGC on a
    skipped record is silently absent from the region set. The GC/contamination check reads the
    FULL FASTA, so a truncated run reports whole-assembly stats beside a BGC set that stops at
    the cap — an incomplete scan presented as MAMEY_COMPLETE. Returns
    {truncated, analysed, first_skipped, skipped_count} so the caller can surface it.
    """
    import zipfile, re
    out = {"truncated": False, "analysed": None, "first_skipped": None}
    try:
        zf = zipfile.ZipFile(input_zip)
    except Exception:
        return out
    for n in [x for x in regular_file_names(zf) if x.lower().endswith(".log")]:
        try:
            txt = zf.read(n).decode("utf-8", "replace")
        except Exception:
            continue
        m = re.search(r"[Oo]nly analysing the first (\d+) records", txt)
        if m:
            out["truncated"] = True
            out["analysed"] = int(m.group(1))
            # a genuinely skipped record: the "Not annotating skipped record X: skipping all but
            # largest N meaningful records" line is the authoritative skip signal.
            sk = re.search(
                r"Not annotating skipped record (\S+?):\s*skipping all but largest", txt)
            if sk:
                out["first_skipped"] = sk.group(1).rstrip(":")
            out["skipped_count"] = len(re.findall(
                r"skipping all but largest \d+ meaningful records", txt))
            break
    return out
