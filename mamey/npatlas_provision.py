"""mamey/npatlas_provision.py — user-provisioned NP Atlas ingestion (v9.7.405, punch-card B7).

Implements steps 1-3 of the NP Atlas provisioning/structure-display audit
(CODEX_390_NPATLAS_PROVISIONING_AND_STRUCTURE_DISPLAY_AUDIT.md, NPA-01..NPA-04). Steps 4/5
(Tanimoto similarity, ChemSpider link-out) are explicitly OUT of scope here — owner-gated.

What this module does
----------------------
- Streams a user-supplied NP Atlas source file (official full JSON, ~475 MB; or a plain SDF) with
  the vendored `ijson` -- never `json.loads`-es the whole file into memory.
- Applies a DECLARATIVE filter (origin type / taxon-substring / genus allowlist / an operator
  predicate-clause file) -- never arbitrary executed code. A "portable LLM may help author or
  inspect a filter specification, but deterministic code performs the actual row selection"
  (audit doc, recommended data contract).
- Writes a content-addressed filtered output plus a receipt: source path/SHA-256/bytes, dataset
  version, licence id (sourced from `mamey.external_data.DATASETS["npatlas"].licence` -- one
  place, corrected under NPA-02), the exact filter rule, included/excluded counts, output SHA-256,
  and this module's tool version.
- NEVER reads, copies, or redistributes the source file's content beyond the operator's own
  filtered-subset output on their own disk. No network access. No personal/default directory is
  assumed anywhere in this module.

Claim ceiling
-------------
This module provisions and counts records. It makes no taxonomic-distribution, bioactivity,
structure-similarity, or BGC-identity claim. See `mamey/npatlas_structure.py::render_structure_svg`
for the separate, explicitly-capped chemical-structure rendering path.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .external_data import DATASETS as _EXTERNAL_DATASETS

TOOL_VERSION = "9.7.405-b7"

_READ_CHUNK = 1 << 20  # 1 MiB streaming chunk for hashing -- never loads the whole file


class NpatlasProvisionError(Exception):
    """Typed refusal for anything this module cannot honestly do (bad source, bad filter, bad
    predicate file). Never a bare Exception/AssertionError so a caller can catch this exactly."""


# --------------------------------------------------------------------------------------------
# Optional streaming JSON parser -- same dual-name/vendored-fallback shape as
# mamey/antismash_evidence.py, so the NP Atlas full JSON (~475 MB) is never fully materialised.
# --------------------------------------------------------------------------------------------
try:
    import ijson  # system install, if present
    _ijson = ijson
    _HAVE_IJSON = True
    _IJSON_SOURCE = "system"
except Exception:  # pragma: no cover - exercised only when system ijson is absent
    _vd = os.path.join(os.path.dirname(__file__), "_vendor")
    if os.path.isdir(os.path.join(_vd, "ijson")) and _vd not in sys.path:
        sys.path.append(_vd)
    try:
        import ijson  # vendored pure-Python fallback, imported as top-level `ijson`
        _ijson = ijson
        _HAVE_IJSON = True
        _IJSON_SOURCE = "vendored"
    except Exception:
        ijson = None
        _ijson = None
        _HAVE_IJSON = False
        _IJSON_SOURCE = "absent"


def ijson_status() -> dict[str, Any]:
    """{'available': bool, 'source': 'system'|'vendored'|'absent'} for `doctor`."""
    return {"available": _HAVE_IJSON, "source": _IJSON_SOURCE}


def rdkit_status() -> dict[str, Any]:
    """{'available': bool, 'version': str|None} for `doctor` -- never imports at module load."""
    try:
        import rdkit  # noqa: F401
        version = getattr(rdkit, "__version__", None)
        return {"available": True, "version": version}
    except Exception:
        return {"available": False, "version": None}


# --------------------------------------------------------------------------------------------
# Content addressing
# --------------------------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    """Streamed SHA-256 of a file -- never reads it whole into memory (correct even at 475 MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_READ_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------------------------
# Source format detection + streaming record iteration
# --------------------------------------------------------------------------------------------
def _peek_first_nonspace_byte(path: str) -> bytes:
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(4096), b""):
            stripped = chunk.lstrip()
            if stripped:
                return stripped[:1]
    return b""


def detect_json_root_prefix(path: str, override: str | None = None) -> str:
    """The ijson `.items()` prefix to iterate compound records at.

    A bare top-level array (the shape of the official NP Atlas download) needs prefix "item"; a
    top-level object holding the records under a "compounds" key (the shape of this bundle's own
    filtered add-on files, see mamey/npatlas_resolver.py::_REF_FILES) needs "compounds.item".
    `override` (e.g. an operator-supplied --json-root) always wins."""
    if override:
        return override
    first = _peek_first_nonspace_byte(path)
    return "item" if first == b"[" else "compounds.item"


def iter_json_records(path: str, *, root_prefix: str | None = None) -> Iterator[dict]:
    """Stream compound records from a (potentially huge) NP Atlas JSON file. Never json.loads()s
    the whole document -- required for the official 475 MB download."""
    if not _HAVE_IJSON:
        raise NpatlasProvisionError(
            "NPATLAS_PROVISION_REFUSAL: no ijson available (neither system nor the vendored copy "
            "at mamey/_vendor/ijson) -- cannot stream a large NP Atlas JSON without it.")
    prefix = detect_json_root_prefix(path, root_prefix)
    with open(path, "rb") as fh:
        for rec in _ijson.items(fh, prefix, use_float=True):
            if isinstance(rec, dict):
                yield rec


def iter_sdf_records(path: str) -> Iterator[dict]:
    """Stream property-tag blocks from a plain-text SDF without any chemistry toolkit.

    Only the record's declared SDF properties (">  <FieldName>" blocks) are surfaced as a flat
    dict -- enough to apply the same declarative origin/taxon/genus filter used for JSON, without
    depending on RDKit for provisioning (RDKit stays optional and is only used for the separate
    structure-rendering path in mamey/npatlas_structure.py). The MOL block itself is not parsed.
    """
    prop_header_prefix = ">"
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        rec: dict[str, str] = {}
        current_field: str | None = None
        buf: list[str] = []
        saw_any = False
        for line in fh:
            stripped = line.rstrip("\n")
            if stripped == "$$$$":
                if saw_any:
                    if current_field is not None:
                        rec[current_field] = "\n".join(buf).strip()
                    yield rec
                rec, current_field, buf, saw_any = {}, None, [], False
                continue
            if stripped.startswith(prop_header_prefix) and "<" in stripped and ">" in stripped[1:]:
                if current_field is not None:
                    rec[current_field] = "\n".join(buf).strip()
                start = stripped.find("<") + 1
                end = stripped.find(">", start)
                current_field = stripped[start:end] if end > start else None
                buf = []
                saw_any = True
                continue
            if current_field is not None:
                buf.append(stripped)
        if current_field is not None and saw_any:
            rec[current_field] = "\n".join(buf).strip()
        if saw_any and rec:
            yield rec


def iter_records(path: str, *, root_prefix: str | None = None) -> Iterator[dict]:
    """Dispatch on file extension. Refuses (typed) any format this module does not stream."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        yield from iter_json_records(path, root_prefix=root_prefix)
    elif suffix == ".sdf":
        yield from iter_sdf_records(path)
    else:
        raise NpatlasProvisionError(
            f"NPATLAS_PROVISION_REFUSAL: unsupported source extension {suffix!r} -- this cut "
            f"streams .json (official NP Atlas download) or .sdf only.")


# --------------------------------------------------------------------------------------------
# Declarative filter (never executed code -- a flat list of ANDed clauses)
# --------------------------------------------------------------------------------------------
_VALID_OPS = ("eq", "in", "contains", "icontains")


@dataclass(frozen=True)
class FilterClause:
    field: str        # dotted path, e.g. "origin_type" or "reference.year"
    op: str            # one of _VALID_OPS
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "op": self.op, "value": self.value}


def _get_path(record: dict, dotted: str) -> Any:
    cur: Any = record
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def clause_from_dict(d: dict) -> FilterClause:
    field_name = d.get("field")
    op = d.get("op")
    if not field_name or not isinstance(field_name, str):
        raise NpatlasProvisionError("NPATLAS_PROVISION_REFUSAL: filter clause missing a 'field' string")
    if op not in _VALID_OPS:
        raise NpatlasProvisionError(
            f"NPATLAS_PROVISION_REFUSAL: filter clause op {op!r} not in {_VALID_OPS}")
    return FilterClause(field=field_name, op=op, value=d.get("value"))


def load_predicate_file(path: str) -> list[FilterClause]:
    """A predicate file is a plain JSON list of {"field", "op", "value"} clauses -- declarative
    data, never executed code (deliberate: the audit's own recommended contract keeps row
    selection in deterministic code, not an LLM- or operator-authored script)."""
    if not os.path.isfile(path):
        raise NpatlasProvisionError(f"NPATLAS_PROVISION_REFUSAL: --predicate-file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise NpatlasProvisionError(f"NPATLAS_PROVISION_REFUSAL: unreadable --predicate-file: {exc}")
    if not isinstance(data, list):
        raise NpatlasProvisionError(
            "NPATLAS_PROVISION_REFUSAL: --predicate-file must be a JSON list of filter clauses")
    return [clause_from_dict(c) for c in data]


def evaluate_clause(record: dict, clause: FilterClause) -> bool:
    actual = _get_path(record, clause.field)
    if clause.op == "eq":
        return actual == clause.value
    if clause.op == "in":
        allowed = clause.value if isinstance(clause.value, (list, tuple, set)) else [clause.value]
        if isinstance(actual, list):
            return any(a in allowed for a in actual)
        return actual in allowed
    if clause.op == "contains":
        return isinstance(actual, str) and isinstance(clause.value, str) and clause.value in actual
    if clause.op == "icontains":
        return (isinstance(actual, str) and isinstance(clause.value, str)
                and clause.value.lower() in actual.lower())
    return False  # unreachable given clause_from_dict's validation


def record_matches(record: dict, clauses: list[FilterClause]) -> bool:
    """All clauses AND together. An empty clause list matches everything (no filter narrowing)."""
    return all(evaluate_clause(record, c) for c in clauses)


# --------------------------------------------------------------------------------------------
# Schema normalization -- raw NP Atlas v2024_09 record -> the schema mamey/npatlas_resolver.py
# reads (CLAUDE_409 / npatlas_provision_keymap).
#
# The official download stores each record with keys that DIFFER from what the consumer reads:
#   raw `original_name`                       -> resolver reads `name`   (_load_index: c.get("name"))
#   raw `origin_reference` {doi,pmid,year,..} -> resolver reads `reference` {doi,pmid,year}
#   raw `npclassifier.class_results`          -> resolver reads `npclassifier.class`      (list)
#   raw `npclassifier.pathway_results`        -> resolver reads `npclassifier.pathway`    (list)
#   raw `npclassifier.superclass_results`     -> resolver reads `npclassifier.superclass` (list)
#   raw `npclassifier.isglycoside`            -> resolver reads `npclassifier.is_glycoside`
# `mol_formula`/`exact_mass`/`m_plus_h`/`m_plus_na`/`inchikey`/`npaid` already share the name.
# Provisioning wrote records VERBATIM, so a "successful" provision built an EMPTY resolver index
# (`c.get("name")` was None for every record -> every record skipped -> B6 stayed empty). This pass
# closes that gap: it is deterministic, offline, and pure (no I/O, no mutation of the input dict).
# --------------------------------------------------------------------------------------------
_ACTINO_PHYLA = ("actinobacteria", "actinomycetota")  # 2024_09 dump labels the phylum Actinobacteria


def _taxon_phylum(record: dict) -> str | None:
    """The phylum name for a record, read from the nested taxonomy the 2024_09 schema actually uses:
    `origin_organism.taxon.ancestors[]` is a LIST of {rank,name,...} rungs -- the phylum rung is the
    one with rank == 'phylum'. (The flat `origin_taxon` the shipped recipe named does not exist, and
    the declarative `_get_path` clause grammar cannot descend a list, so this derivation lives here.)
    Falls back to the taxon node itself when it is already a phylum. Returns None when absent."""
    org = record.get("origin_organism")
    if not isinstance(org, dict):
        return None
    taxon = org.get("taxon")
    if not isinstance(taxon, dict):
        return None
    if str(taxon.get("rank", "")).lower() == "phylum" and taxon.get("name"):
        return str(taxon.get("name"))
    ancestors = taxon.get("ancestors")
    if isinstance(ancestors, list):
        for anc in ancestors:
            if isinstance(anc, dict) and str(anc.get("rank", "")).lower() == "phylum" and anc.get("name"):
                return str(anc.get("name"))
    return None


def _first_present(record: dict, *keys: str) -> Any:
    """Return the first key's value that exists (idempotency: read raw OR already-normalized keys)."""
    for k in keys:
        if k in record and record[k] is not None:
            return record[k]
    return None


def _norm_npclassifier(raw: Any) -> dict[str, Any]:
    """Remap a raw npclassifier block to the resolver's field names; idempotent if already remapped."""
    npc = raw if isinstance(raw, dict) else {}
    def _pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in npc and npc[k] is not None:
                return npc[k]
        return default
    return {
        "class": _pick("class_results", "class", default=[]) or [],
        "pathway": _pick("pathway_results", "pathway", default=[]) or [],
        "superclass": _pick("superclass_results", "superclass", default=[]) or [],
        "is_glycoside": _pick("isglycoside", "is_glycoside"),
    }


def normalize_record(record: dict) -> dict[str, Any]:
    """Map ONE raw NP Atlas v2024_09 record onto the schema `mamey/npatlas_resolver.py` reads.

    Pure and deterministic: builds a new dict, never mutates the input. Idempotent -- a record that
    is already in resolver schema (has `name`/`reference`/`npclassifier.class`) passes through
    unchanged in meaning. A synthetic top-level `phylum` (from `_taxon_phylum`) is injected so the
    actinobacterial-vs-non-actino split is expressible as a plain declarative clause on a scalar
    field (`{"field":"phylum","op":"in","value":["Actinobacteria","Actinomycetota"]}`), which the
    list-nested ancestor taxonomy otherwise could not support."""
    ref_raw = _first_present(record, "reference", "origin_reference")
    ref = ref_raw if isinstance(ref_raw, dict) else {}
    out: dict[str, Any] = {
        "name": _first_present(record, "name", "original_name"),
        "npaid": _first_present(record, "npaid"),
        "mol_formula": _first_present(record, "mol_formula"),
        "mol_weight": _first_present(record, "mol_weight"),
        "exact_mass": _first_present(record, "exact_mass"),
        "m_plus_h": _first_present(record, "m_plus_h"),
        "m_plus_na": _first_present(record, "m_plus_na"),
        "inchikey": _first_present(record, "inchikey"),
        "inchi": _first_present(record, "inchi"),
        "smiles": _first_present(record, "smiles"),
        "synonyms": _first_present(record, "synonyms"),
        "npclassifier": _norm_npclassifier(record.get("npclassifier")),
        "reference": {
            "doi": ref.get("doi"),
            "pmid": ref.get("pmid"),
            "year": ref.get("year"),
            "journal": ref.get("journal"),
            "title": ref.get("title"),
        },
        # prefer an already-derived top-level phylum (idempotency: a second normalize pass no longer
        # sees the nested ancestor list, which the first pass flattened away).
        "phylum": record.get("phylum") or _taxon_phylum(record),
    }
    # preserve isolation provenance (genus/species/taxon name) without the huge ancestor list
    org = record.get("origin_organism")
    if isinstance(org, dict):
        taxon = org.get("taxon") if isinstance(org.get("taxon"), dict) else {}
        out["origin_organism"] = {
            "genus": org.get("genus"),
            "species": org.get("species"),
            "type": org.get("type"),
            "taxon_name": taxon.get("name"),
        }
    return out


# --------------------------------------------------------------------------------------------
# Receipt + provisioning
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ProvisionReceipt:
    source_path: str
    source_sha256: str
    source_bytes: int
    dataset_version: str
    licence_id: str
    licence_text: str
    filter_rule: list[dict[str, Any]]
    included_count: int
    excluded_count: int
    output_path: str
    output_sha256: str
    normalized: bool = False
    tool_version: str = TOOL_VERSION
    claim_ceiling: str = (
        "provisioning receipt only -- record counts and hashes, not a taxonomic-distribution, "
        "bioactivity, or BGC-identity claim")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "source_bytes": self.source_bytes,
            "dataset_version": self.dataset_version,
            "licence_id": self.licence_id,
            "licence_text": self.licence_text,
            "filter_rule": self.filter_rule,
            "included_count": self.included_count,
            "excluded_count": self.excluded_count,
            "output_path": self.output_path,
            "output_sha256": self.output_sha256,
            "normalized": self.normalized,
            "tool_version": self.tool_version,
            "claim_ceiling": self.claim_ceiling,
        }


def _npatlas_licence() -> tuple[str, str]:
    """(licence_id, licence_text) sourced from the single corrected registry entry (NPA-02) --
    never a second hardcoded copy of the licence string."""
    ds = _EXTERNAL_DATASETS["npatlas"]
    return "CC-BY-NC-4.0", ds.licence


def provision(
    source_path: str,
    out_path: str,
    clauses: list[FilterClause],
    *,
    root_prefix: str | None = None,
    dataset_version: str = "unknown",
    normalize: bool = False,
) -> ProvisionReceipt:
    """Stream `source_path`, keep records matching all `clauses`, write the filtered subset to
    `out_path` as {"compounds": [...]}, and return the content-addressed receipt. Never touches
    the source beyond a streamed read; never writes anything except the one declared output.

    When `normalize` is True (CLAUDE_409), each raw NP Atlas v2024_09 record is remapped via
    `normalize_record` onto the schema `mamey/npatlas_resolver.py` reads BEFORE the filter is
    evaluated and before it is written -- so the filter can select on the synthetic scalar `phylum`
    field (actino split) and, critically, the output the resolver loads carries a populated `name`
    (verbatim output built an EMPTY resolver index). Off by default: an operator provisioning
    already-normalized or non-NP-Atlas JSON keeps the historical verbatim behaviour."""
    if not os.path.isfile(source_path):
        raise NpatlasProvisionError(f"NPATLAS_PROVISION_REFUSAL: --source not found: {source_path}")
    source_sha256 = sha256_file(source_path)
    source_bytes = os.path.getsize(source_path)

    kept: list[dict] = []
    included = 0
    excluded = 0
    for rec in iter_records(source_path, root_prefix=root_prefix):
        if normalize:
            rec = normalize_record(rec)
        if record_matches(rec, clauses):
            kept.append(rec)
            included += 1
        else:
            excluded += 1

    payload = json.dumps({"compounds": kept}, indent=2, sort_keys=True) + "\n"
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    os.replace(tmp_path, out_path)
    output_sha256 = sha256_file(out_path)

    licence_id, licence_text = _npatlas_licence()
    return ProvisionReceipt(
        source_path=os.path.abspath(source_path),
        source_sha256=source_sha256,
        source_bytes=source_bytes,
        dataset_version=dataset_version,
        licence_id=licence_id,
        licence_text=licence_text,
        filter_rule=[c.to_dict() for c in clauses],
        included_count=included,
        excluded_count=excluded,
        output_path=os.path.abspath(out_path),
        output_sha256=output_sha256,
        normalized=normalize,
    )


def inspect_source(source_path: str, *, root_prefix: str | None = None,
                    sample_limit: int = 5) -> dict[str, Any]:
    """A streamed, read-only preview: source hash/bytes, total record count, a small sample of
    the first records' top-level keys, and (for JSON) which root prefix was used. Never writes
    anything. Full-count is a full streamed pass (bounded memory, not bounded time) -- same cost
    class as `provision`'s own single pass."""
    if not os.path.isfile(source_path):
        raise NpatlasProvisionError(f"NPATLAS_PROVISION_REFUSAL: --source not found: {source_path}")
    suffix = Path(source_path).suffix.lower()
    prefix_used = detect_json_root_prefix(source_path, root_prefix) if suffix == ".json" else None
    total = 0
    sample: list[dict] = []
    field_union: set[str] = set()
    for rec in iter_records(source_path, root_prefix=root_prefix):
        if len(sample) < sample_limit:
            sample.append(rec)
        field_union |= set(rec.keys())
        total += 1
    return {
        "source_path": os.path.abspath(source_path),
        "source_sha256": sha256_file(source_path),
        "source_bytes": os.path.getsize(source_path),
        "format": suffix.lstrip("."),
        "json_root_prefix": prefix_used,
        "total_records": total,
        "field_union_sample": sorted(field_union),
        "sample_records": sample,
        "tool_version": TOOL_VERSION,
    }


def doctor_report() -> dict[str, Any]:
    """Environment readiness for `npatlas provision` -- ijson backend, RDKit, and the dataset's
    own provisioning status (mamey.external_data), never a personal-directory assumption."""
    from . import external_data
    return {
        "tool_version": TOOL_VERSION,
        "ijson": ijson_status(),
        "rdkit": rdkit_status(),
        "npatlas_dataset": external_data.status().get("npatlas"),
    }
