"""antismash_input.py — recognise an antiSMASH result archive regardless of how it was named.

Motivation
----------
Sapote-Mamey is used by students who name their downloads whatever they like:
``CP025018.1.zip``, ``my results (1).zip``, ``Streptomyces_stuff_FINAL_v2.zip``. Until now the engine
took the user's word for the two facts that matter most and could not check either:

* **Is this actually an antiSMASH result archive?** — a mis-picked file failed late, deep in parsing,
  with an unhelpful error.
* **Which detection strictness produced it?** — ``--antismash-profile`` defaulted to ``"unknown"`` and
  was never verified, so packages were sealed with an unknown (or, worse, a *wrong*) profile. Regions
  called under ``loose`` are not comparable to regions called under ``relaxed``; pooling them silently
  corrupts cross-strain work such as BiG-SCAPE GCF clustering.

Both facts are recoverable from *inside* the archive, so nothing needs to be trusted to a filename.
This module reads them, cheaply, and reports the evidence it used.

Design notes
------------
* **Streaming, not slurping.** The antiSMASH JSON can exceed 80 MB, and the ``"strictness"`` token
  typically sits ~15 MB in. We stream in 4 MB chunks and stop at the first hit (~0.03 s in practice),
  carrying a small tail across chunk boundaries so a token split across two reads is still found.
* **Only the first region GBK header is read** (6 KB) for organism, lineage and antiSMASH version.
* **The ``ORGANISM  .`` placeholder is not an organism.** antiSMASH run over a bare GCA assembly emits
  a literal ``.``; treating that as a name yields nonsense. When it appears, the filename is the only
  organism source — and conversely, an accession-only filename has no organism, so the GBK is the only
  source. Neither source alone is sufficient, so both are consulted in a defined order.
* **Nothing raises on a bad archive.** ``identify()`` always returns a result; ``is_antismash`` is
  False and ``warnings`` explains why. Callers decide policy.

Claim-safety: this module reports provenance only. It makes no biological claim, and a resolved
organism name is a record label, not a taxonomic assertion.
"""

from __future__ import annotations

import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional
from .parsers import GbkSizeGuardRefusal, _gbk_size_guard, _guarded_read_bytes
from .ziputil import duplicate_member_names, nonregular_file_names, regular_file_names

__all__ = ["AntismashInput", "identify", "is_antismash_archive", "detect_strictness"]

# v9.7.409 (DEEP_AUDIT2_antismash_parse, fix seed 1): the parse path is antiSMASH-version-ASSUMING
# and fails SILENT — a renamed/moved key on an out-of-range antiSMASH version reads as "no hits",
# indistinguishable from a genome that genuinely has none. The version is recovered here but nothing
# acts on it. Convert that silent drop into a LOUD, typed signal: when the recorded antiSMASH major
# version is outside the tested range (or is present-but-unparseable), emit an
# ANTISMASH_SCHEMA_UNRECOGNIZED warning (into result.warnings AND stderr). This is a WARN, never a
# refusal — a valid genome with no BGCs, and a genome from an untested-but-compatible version, must
# both still pass. Range is env-overridable so a new antiSMASH major can be blessed without a code
# change. The GBK region-file schema this parser reads has been stable across antiSMASH 5-8.
_AS_TESTED_MIN_MAJOR = 5
_AS_TESTED_MAX_MAJOR = 8
_AS_SCHEMA_WARN = "ANTISMASH_SCHEMA_UNRECOGNIZED"


def _as_tested_major_range() -> tuple[int, int]:
    """Tested antiSMASH major-version range (env-overridable, read at call time)."""
    def _read(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name, str(default)))
        except (TypeError, ValueError):
            return default
    lo = _read("MAMEY_ANTISMASH_MIN_MAJOR", _AS_TESTED_MIN_MAJOR)
    hi = _read("MAMEY_ANTISMASH_MAX_MAJOR", _AS_TESTED_MAX_MAJOR)
    return lo, hi


def _antismash_major(version: Optional[str]) -> Optional[int]:
    """Leading integer of an antiSMASH version string ('8.0.4' -> 8), or None if unreadable."""
    if not version:
        return None
    m = re.match(r"\s*(\d+)", str(version))
    return int(m.group(1)) if m else None


def antismash_schema_warning(version: Optional[str], *, has_regions: bool) -> Optional[str]:
    """Return an ANTISMASH_SCHEMA_UNRECOGNIZED warning line, or None when the version is trusted.

    - Version present and major inside the tested range  -> None (trusted).
    - Version present but major OUTSIDE the tested range  -> warn (keys may be renamed/moved; a
      silent empty parse is possible and would be indistinguishable from a true "no hits").
    - Version present but unparseable, OR absent while region GBKs exist -> warn (cannot confirm the
      output was produced by a tested antiSMASH schema).
    """
    lo, hi = _as_tested_major_range()
    major = _antismash_major(version)
    if major is not None:
        if lo <= major <= hi:
            return None
        return (f"{_AS_SCHEMA_WARN}: antiSMASH major version {major} (reported {version!r}) is "
                f"outside the tested range {lo}-{hi}. Renamed or relocated schema keys would be read "
                f"as absent, so an empty parse may be silent mis-reading rather than a true 'no "
                f"hits'. Results still emitted; verify substrate/TIGRFAM/module evidence by hand or "
                f"set MAMEY_ANTISMASH_MIN_MAJOR/MAX_MAJOR to bless this version.")
    if version:
        return (f"{_AS_SCHEMA_WARN}: antiSMASH version {version!r} could not be parsed to a major "
                f"number; cannot confirm the output matches a tested schema. Verify evidence by hand.")
    if has_regions:
        return (f"{_AS_SCHEMA_WARN}: antiSMASH version could not be recovered from the archive, so "
                f"the output cannot be confirmed to match a tested schema ({lo}-{hi}). An empty "
                f"parse of a renamed schema would be silent. Verify evidence by hand.")
    return None

_REGION_GBK = re.compile(r"\.region\d+\.gbk$", re.IGNORECASE)
_STRICTNESS = re.compile(rb'"strictness"\s*:\s*"(\w+)"')
_STRICTNESS_CLI = re.compile(rb'--hmmdetection-strictness["\s:,]+(\w+)')
_SACCHARIDE_PRODUCT = re.compile(rb'product="saccharide"')
_ORGANISM = re.compile(r"^\s*ORGANISM\s+(.+)$", re.MULTILINE)
_AS_VERSION = re.compile(r"Version\s*::\s*([0-9][0-9A-Za-z.\-]*)")
_GENUS_SPECIES = re.compile(r"^([A-Z][a-z]{3,})[ _](sp\.?|[a-z]{3,})")
_ACCESSION_ONLY = re.compile(r"^(NZ_)?[A-Z]{2,6}\d{5,}(\.\d+)?([ _(]|$)", re.IGNORECASE)

#: Markers that identify an antiSMASH HTML/JSON output bundle even when region GBKs are absent.
_AS_MARKERS = ("regions.js", "index.html", "knownclusterblast/", "clusterblast/")

#: Strictness values antiSMASH can report. ``unknown`` is ours, meaning "not recoverable".
VALID_STRICTNESS = ("strict", "relaxed", "loose")

_CHUNK = 4 * 1024 * 1024
_TAIL = 64
_HEADER_BYTES = 6144


@dataclass
class AntismashInput:
    """What we could establish about an archive, plus the evidence for it."""

    path: str
    is_antismash: bool = False
    strictness: str = "unknown"
    strictness_evidence: str = ""
    n_regions: int = 0
    organism: Optional[str] = None
    organism_source: str = ""
    lineage: str = ""
    phylum: str = ""
    is_actinomycete: Optional[bool] = None
    antismash_version: Optional[str] = None
    suggested_strain_id: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def comparable_key(self) -> str:
        """Two inputs may be pooled in one analysis only if this key matches."""
        return f"antismash:{self.strictness}"

    def summary(self) -> str:
        if not self.is_antismash:
            return f"{os.path.basename(self.path)}: not an antiSMASH archive"
        org = self.organism or "organism unresolved"
        return (f"{os.path.basename(self.path)}: antiSMASH "
                f"{self.antismash_version or '?'}, strictness={self.strictness}, "
                f"{self.n_regions} regions, {org}")


def _stream_find(zf: zipfile.ZipFile, member: str, *patterns) -> Optional[re.Match]:
    """Scan a member in chunks, returning the first match of any pattern.

    Carries a short tail between chunks so a token straddling a boundary is still found.
    """
    tail = b""
    try:
        with zf.open(member) as fh:
            while True:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    return None
                blob = tail + chunk
                for pat in patterns:
                    m = pat.search(blob)
                    if m:
                        return m
                tail = chunk[-_TAIL:]
    except Exception:
        return None


def detect_strictness(zf: zipfile.ZipFile) -> tuple[str, str]:
    """Return ``(strictness, evidence)`` read from the archive's antiSMASH JSON.

    Falls back to a recorded command line if the structured field is absent. Returns
    ``("unknown", reason)`` rather than guessing — an unknown profile is recoverable later, a wrong
    one silently corrupts comparisons.
    """
    jsons = [n for n in regular_file_names(zf) if n.lower().endswith(".json")]
    if not jsons:
        return "unknown", "no JSON member in archive"
    # Largest JSON first: the run record lives in the main results file.
    jsons.sort(key=lambda n: -(zf.getinfo(n).file_size))
    for name in jsons[:3]:
        m = _stream_find(zf, name, _STRICTNESS, _STRICTNESS_CLI)
        if m:
            value = m.group(1).decode("ascii", "ignore").lower()
            if value in VALID_STRICTNESS:
                return value, f"{name}:\"strictness\""
            return "unknown", f"{name}: unrecognised strictness {value!r}"
    # v9.7.398 (review lane): the structured `strictness` token was unreadable. Fall back to a
    # STRUCTURAL discriminator verified on paired loose/relaxed cohort inputs — the loose profile
    # emits a `saccharide` detection layer that relaxed/strict do not (measured on a paired cohort strain: loose = 26
    # saccharide regions, relaxed = 0). Presence of >=1 saccharide region product ⇒ loose. This
    # separates loose from not-loose ONLY (it cannot split relaxed from strict), so absence stays
    # "unknown" rather than guessing — never assert a flavor the evidence does not support.
    # v9.7.410 (CLAUDE_410_gbk_size_guard_all_reads): the fallback used an unbounded `zf.read` per
    # region GBK. Now: getinfo() size/ratio preflight (over-cap member skipped, never loaded) and a
    # chunked stream scan for the token — no whole-member load even on normal-size members.
    refused = 0
    unreadable = 0
    # v9.7.413 (BLIZZARD_BLUE_413_silent_swallow_triage, F_BROAD_UNCLASSIFIED): this used to be one
    # `try` around the whole loop below. Split into two layers with two different jobs, rather than
    # narrowing the exception type (which would not help — the failure modes here are heterogeneous,
    # not one guessable type):
    #  - LISTING the archive's members (regular_file_names -> ZipFile.infolist()) can raise on a
    #    truly corrupt central directory; that failure is archive-wide and "unknown" is still the
    #    right, honest answer -- kept as a coarse catch, unchanged in effect from .412.
    #  - Evaluating ONE member (per-member try below) must not abort the scan of every OTHER member:
    #    pre-.413, a single corrupt/truncated region GBK silently discarded saccharide evidence
    #    sitting in every other region GBK of the same archive -- a genuinely loose cohort strain
    #    could read back as "unknown" because of one unrelated bad member elsewhere in the zip.
    try:
        names = regular_file_names(zf)
    except Exception:
        names = []
    for name in names:
        if not _REGION_GBK.search(name):
            continue
        try:
            if _gbk_size_guard(zf.getinfo(name)):
                refused += 1
                continue
            found = _stream_find(zf, name, _SACCHARIDE_PRODUCT)
        except Exception:
            unreadable += 1
            continue
        if found:
            return "loose", f"{name}: saccharide-layer heuristic (no strictness token)"
    if refused or unreadable:
        bits = []
        if refused:
            bits.append(f"{refused} region GBK(s) GBK_SIZE_GUARD_REFUSED")
        if unreadable:
            bits.append(f"{unreadable} region GBK(s) unreadable")
        return "unknown", ("no strictness field found in JSON; " + "; ".join(bits) +
                           " (not read for the saccharide heuristic)")
    return "unknown", "no strictness field found in JSON"


def _first_region_header(zf: zipfile.ZipFile, warnings: Optional[List[str]] = None) -> tuple[str, int]:
    """Return ``(header_text, n_region_gbks)``; header is the first region GBK's leading bytes.

    v9.7.410 (CLAUDE_410_gbk_size_guard_all_reads): the read is preflighted through the GBK size /
    compression-ratio guard and bounded to ``_HEADER_BYTES`` — the whole member is never loaded
    (the .409 form was ``zf.read(member)[:6144]``, a full decompression on the read-only
    ``inspect`` path). An over-cap member yields an empty header; when ``warnings`` is given the
    typed ``GBK_SIZE_GUARD_REFUSED`` reason is appended to it.
    """
    regions = sorted(n for n in regular_file_names(zf) if _REGION_GBK.search(n))
    if not regions:
        return "", 0
    try:
        head = _guarded_read_bytes(zf, regions[0], limit=_HEADER_BYTES)
        return head.decode("utf-8", "ignore"), len(regions)
    except GbkSizeGuardRefusal as exc:
        if warnings is not None:
            warnings.append(str(exc))
        return "", len(regions)
    except Exception:
        return "", len(regions)


def _parse_header(header: str) -> tuple[Optional[str], str, Optional[str]]:
    """Extract ``(organism, lineage, antismash_version)`` from a GenBank header block."""
    organism = None
    match = _ORGANISM.search(header)
    if match:
        candidate = match.group(1).strip()
        # antiSMASH over a bare assembly writes a literal "." — that is absence, not a name.
        if candidate not in (".", ""):
            organism = candidate
    lineage = ""
    if organism:
        after = header.split("ORGANISM", 1)[1]
        indented = [ln.strip() for ln in after.splitlines()[1:12] if ln.startswith("  ")]
        lineage = " ".join(indented).split("##")[0]
        lineage = lineage.split("Version")[0].strip()
    version = None
    vmatch = _AS_VERSION.search(header)
    if vmatch:
        version = vmatch.group(1)
    return organism, lineage, version


def _organism_from_filename(path: str) -> Optional[str]:
    """A curated filename often carries the organism when the GBK does not."""
    stem = os.path.splitext(os.path.basename(path))[0]
    if _ACCESSION_ONLY.match(stem):
        return None
    if not _GENUS_SPECIES.match(stem):
        return None
    trimmed = re.split(r"GC[AF]_\d+|(?:NZ_)?[A-Z]{2,6}\d{5,}", stem)[0]
    name = trimmed.replace("_", " ").strip(" -_")
    return name or None


def _suggest_strain_id(organism: Optional[str], path: str) -> Optional[str]:
    """A readable, filesystem-safe id. Never a bare accession — that is not an identity.

    The accession is appended for traceability, but only when it is not already part of the
    organism/strain designation. Without that check, an organism whose strain token IS the accession
    (``Actinophytocola sp. NPDC049390``) yields the doubled ``..._NPDC049390_NPDC049390``.
    """
    if not organism:
        return None
    text = re.sub(r"\b(subsp\.?|strain|str\.|sp\.)\b", " ", organism, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    stem = os.path.splitext(os.path.basename(path))[0]
    acc = re.search(r"((?:NZ_)?[A-Z]{2,6}\d{5,}(?:\.\d+)?|GC[AF]_\d+\.?\d*)", stem)
    if acc:
        token = re.sub(r"[^A-Za-z0-9]+", "_", acc.group(1)).strip("_")
        have = {t.lower() for t in text.split("_") if t}
        # skip when the token, or its accession-number core, is already present in the name
        core = re.sub(r"^(NZ_|GC[AF]_)", "", token, flags=re.IGNORECASE).lower()
        if token.lower() not in have and core not in have:
            text = f"{text}_{token}"
    return re.sub(r"_+", "_", text)[:70].strip("_") or None


def is_antismash_archive(path: str) -> bool:
    """True when the archive looks like antiSMASH output, whatever it is called."""
    return identify(path).is_antismash


def identify(path: str) -> AntismashInput:
    """Inspect an archive and report what it is. Never raises; check ``.warnings``."""
    result = AntismashInput(path=path)
    if not os.path.isfile(path):
        result.warnings.append("file does not exist")
        return result
    if not zipfile.is_zipfile(path):
        result.warnings.append("not a ZIP archive")
        return result
    try:
        with zipfile.ZipFile(path) as zf:
            names = regular_file_names(zf)
            nonregular = nonregular_file_names(zf)
            duplicates = duplicate_member_names(zf)
            if nonregular:
                result.warnings.append(
                    "NONREGULAR_ZIP_MEMBERS_IGNORED: "
                    + ", ".join(nonregular[:5])
                    + (" ..." if len(nonregular) > 5 else ""))
            if duplicates:
                result.warnings.append(
                    "DUPLICATE_ZIP_MEMBER_NAMES_RESOLVED_TO_LAST_ENTRY: "
                    + ", ".join(duplicates[:5])
                    + (" ..." if len(duplicates) > 5 else ""))
            header, n_regions = _first_region_header(zf, result.warnings)
            result.n_regions = n_regions
            has_marker = any(any(mark in n for mark in _AS_MARKERS) for n in names)
            result.is_antismash = bool(n_regions) or has_marker
            if not result.is_antismash:
                result.warnings.append(
                    "no region GBKs and no antiSMASH markers — is this an antiSMASH results ZIP?")
                return result
            if n_regions == 0:
                result.warnings.append(
                    "antiSMASH markers present but zero region GBKs — nothing to analyse "
                    "(a genome with no detected BGCs, or an incomplete download)")
            result.strictness, result.strictness_evidence = detect_strictness(zf)
            if result.strictness == "unknown":
                result.warnings.append(
                    "detection strictness could not be read; results must NOT be pooled with "
                    "another strictness until it is established")
            organism, lineage, version = _parse_header(header)
            result.antismash_version = version
            # v9.7.409 (DEEP_AUDIT2_antismash_parse, fix seed 1): loud, typed signal when the
            # antiSMASH version is outside the tested schema range (or unrecoverable), so a silent
            # "no hits" from a renamed key is distinguishable from a genome that truly has none.
            schema_warn = antismash_schema_warning(version, has_regions=bool(n_regions))
            if schema_warn:
                result.warnings.append(schema_warn)
                print(schema_warn, file=sys.stderr)
            if organism:
                result.organism, result.organism_source = organism, "gbk_organism"
                result.lineage = lineage
            else:
                from_name = _organism_from_filename(path)
                if from_name:
                    result.organism, result.organism_source = from_name, "filename"
                else:
                    result.warnings.append(
                        "organism could not be resolved from the archive or its filename")
            if lineage:
                parts = [p.strip() for p in lineage.split(";") if p.strip()]
                result.phylum = parts[2] if len(parts) > 2 else (parts[-1] if parts else "")
                result.is_actinomycete = ("Actinomycetota" in lineage) or ("Actinobacteria" in lineage)
            result.suggested_strain_id = _suggest_strain_id(result.organism, path)
    except zipfile.BadZipFile:
        result.warnings.append("corrupt ZIP archive")
    except Exception as exc:  # never let intake crash on a user's file
        result.warnings.append(f"unreadable archive: {type(exc).__name__}")
    return result
