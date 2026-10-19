"""Explicit BLASTp physical assertions, bound through existing exact-identity owners.

No sequence identity, cross-version region bridge, filename or prefix inference is
performed. A row without physical assertions retains its caller's legacy depth.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from .exact_identity import (
    ExactLocusIdentityError,
    exact_locus_from_mapping,
    exact_locus_from_native_inventory_row,
    exact_locus_from_native_manifest_bgc,
)

POLICY = "explicit_blastp_physical_assertions_v1"
QUERY_FIELDS = ("query_locus", "query_id", "query_gene", "gene", "locus_tag", "query_title",
                "query_source_id")
FULL_FIELDS = ("query_contig", "full_contig", "full_node", "full_node_or_contig",
               "Full_Node_ID", "contig", "Contig")
NODE_FIELDS = ("query_node", "node", "node_id", "Node_ID")
REGION_FIELDS = ("query_region", "region", "Region", "antismash_region", "antiSMASH_Region")
_FIELD_ROLE = {**dict.fromkeys(FULL_FIELDS, "full_contig"),
               **dict.fromkeys(NODE_FIELDS, "node"),
               **dict.fromkeys(REGION_FIELDS, "region")}
_TOKEN = re.compile(r"(?:^|[|\s])(?P<key>[A-Za-z_]+)=(?P<value>[^|\s]*)")
_REGION = re.compile(r"region[0-9]{3,}\Z")


class PhysicalBindingHold(ValueError):
    """The asserted physical identity cannot safely enter this output generation."""


def refuse_source_aliases(sources, targets) -> None:
    """Refuse overlapping raw inputs/destinations before the first write."""
    targets = tuple(Path(target) for target in targets)
    for source in sources:
        source = Path(source)
        for target in targets:
            try:
                aliases = source.resolve() == target.resolve()
                if not aliases and source.exists() and target.exists():
                    aliases = source.samefile(target)
            except (OSError, RuntimeError) as exc:
                raise PhysicalBindingHold("BLASTP_SOURCE_ALIAS_HOLD: cannot establish source/destination separation") from exc
            if aliases:
                raise PhysicalBindingHold("BLASTP_SOURCE_ALIAS_HOLD: raw input aliases a publication destination")


def physical_assertions(row: dict) -> list[dict[str, str]]:
    """Retain every explicit original field/token, including repeated tokens.

    A derived B5 contig is not a source claim: manual callers must pass the raw
    query columns/XML title instead of their enriched B5 display fields.
    """
    claims = []
    for field, role in _FIELD_ROLE.items():
        value = row.get(field)
        if value is not None and str(value).strip():
            claims.append({"source": field, "role": role, "value": str(value).strip()})
    for field in QUERY_FIELDS:
        raw = str(row.get(field) or "")
        for match in _TOKEN.finditer(raw):
            key = match.group("key")
            if key in _FIELD_ROLE:
                claims.append({"source": f"{field}:{key}", "role": _FIELD_ROLE[key],
                               "value": match.group("value")})
        # The existing query parser also accepts bare NODE/region tokens.
        # Inspect every occurrence, rather than its first-wins projection, so
        # a repeated contradictory anchor cannot disappear during parsing.
        tokens = raw.lstrip(">").split("|") if "|" in raw else raw.split()
        # Only the declared strain|BGC (or strain BGC) grammar has two leading
        # role tokens. BGC-leading titles may put a bare anchor in slot one.
        start = (2 if len(tokens) >= 2 and re.fullmatch(r"BGC\d+", tokens[1].strip())
                 else 1 if tokens and re.match(r"^BGC\d+(?:_|$)", tokens[0].strip()) else 0)
        for ordinal, token in enumerate(tokens[start:], start):
            value = token.strip()
            if "=" in value:
                continue
            role = ("node" if value.startswith("NODE") else
                    "region" if value.startswith("region") else "")
            if role:
                claims.append({"source": f"{field}:bare:{ordinal}",
                               "role": role, "value": value})
    return claims


def physical_csv_rows(path: Path):
    """Read source rows without allowing duplicate headers to hide assertions."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers = reader.fieldnames
        if headers is None or len(headers) != len(set(headers)):
            raise PhysicalBindingHold("BLASTP_SOURCE_SCHEMA_HOLD: absent or duplicate CSV columns")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise PhysicalBindingHold("BLASTP_SOURCE_SCHEMA_HOLD: inconsistent CSV row width")
            yield row


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(row: dict, *fields: str) -> str:
    values = {str(row[field]).strip() for field in fields
              if row.get(field) is not None and str(row[field]).strip()}
    if len(values) > 1:
        raise ExactLocusIdentityError("conflicting authority aliases: " + ", ".join(fields))
    return next(iter(values), "")


def _identity(strain: str, row: dict) -> dict[str, str]:
    """Select a declared producer adapter; never collapse full and join roles."""
    if all(field in row for field in ("Contig", "Node_ID", "BGC_ID", "antiSMASH_Region")):
        native = exact_locus_from_native_inventory_row(strain, row)
    elif all(field in row for field in ("contig", "node_id", "bgc_id", "antismash_region")):
        native = exact_locus_from_native_manifest_bgc(strain, row)
    else:
        # Generic legacy authority requires literal synonym agreement and a full
        # physical identifier. It grants no shortened native-node mapping.
        display = exact_locus_from_mapping(strain, row)
        fields = display.split(" / ")
        if len(fields) != 4:
            raise ExactLocusIdentityError("unsafe physical display separator")
        return {"strain": fields[0], "full_contig": fields[1], "node": fields[1],
                "node_role": "full_only",
                "region": fields[2], "bgc": fields[3], "exact_locus": display}
    if row.get("region_number") not in (None, ""):
        ordinal = str(row["region_number"]).strip()
        if not ordinal.isdigit() or int(ordinal) != int(native.region[6:]):
            raise ExactLocusIdentityError("native crosswalk region_number contradicts region label")
    return {"strain": native.strain, "full_contig": native.full_contig,
            "node": native.normalized_node_id, "node_role": "native",
            "region": native.region,
            "bgc": native.bgc_alias, "exact_locus": native.exact_locus}


class PhysicalAuthority:
    """One read-only selected-package snapshot, loaded only for asserted rows."""

    def __init__(self, package: Path, strain: str):
        self.package = Path(package)
        self.strain = strain
        self.sources: list[dict] = []
        self.identities: dict[str, list[dict]] = {}
        self.errors: dict[str, str] = {}
        self.members: dict[tuple[str, str], list[dict]] = {}
        self.node_contigs: dict[str, set[str]] = {}
        self.global_error = ""
        self.loaded = False

    def _read(self, path: Path) -> bytes:
        data = path.read_bytes()
        rel = path.relative_to(self.package).as_posix()
        self.sources.append({"path": rel, "sha256": _digest(data)})
        return data

    def _add_identity(self, row: dict, owner: str) -> None:
        bgc = str(row.get("bgc_id") or row.get("BGC_ID") or "").strip()
        try:
            identity = _identity(self.strain, row)
        except (ExactLocusIdentityError, ValueError, TypeError) as exc:
            if bgc:
                self.errors[bgc] = "PHYSICAL_AUTHORITY_MALFORMED"
            else:
                self.global_error = "PHYSICAL_AUTHORITY_MALFORMED"
            return
        bucket = self.identities.setdefault(identity["bgc"], [])
        if owner == "crosswalk" and any(x["owner"] == "crosswalk" for x in bucket):
            self.errors[identity["bgc"]] = "PHYSICAL_AUTHORITY_AMBIGUOUS"
        bucket.append({**identity, "owner": owner})
        self.node_contigs.setdefault(identity["node"], set()).add(identity["full_contig"])

    def _add_member(self, bgc: str, row: dict, owner: str) -> None:
        locus = _text(row, "locus_tag")
        if not bgc or not locus:
            return
        full = _text(row, "contig", "Contig", "full_contig", "Full_Node_ID")
        region = _text(row, "region", "antismash_region", "antiSMASH_Region")
        member_strain = _text(row, "strain", "strain_id", "Strain", "Strain_ID")
        bucket = self.members.setdefault((bgc, locus), [])
        if any(member["owner"] == owner for member in bucket):
            self.errors[bgc] = "PHYSICAL_GENE_MEMBERSHIP_AMBIGUOUS"
        bucket.append(
            {"full_contig": full, "region": region, "strain": member_strain, "owner": owner})

    def load(self) -> None:
        if self.loaded:
            return
        self.loaded = True
        try:
            crosswalks = sorted(self.package.rglob("*2b_bgc_crosswalk.csv"))
            if len(crosswalks) != 1:
                self.global_error = ("PHYSICAL_AUTHORITY_UNAVAILABLE" if not crosswalks
                                     else "PHYSICAL_AUTHORITY_AMBIGUOUS")
            else:
                import io
                reader = csv.DictReader(io.StringIO(self._read(crosswalks[0]).decode("utf-8")), strict=True)
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    self.global_error = "PHYSICAL_AUTHORITY_MALFORMED"
                else:
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            self.global_error = "PHYSICAL_AUTHORITY_MALFORMED"
                            continue
                        self._add_identity(row, "crosswalk")
            manifest_path = self.package / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(self._read(manifest_path))
                if not isinstance(manifest, dict):
                    raise ValueError("manifest is not an object")
                supplied_strain = manifest.get("strain_id") or manifest.get("strain")
                if supplied_strain and str(supplied_strain).strip() != self.strain:
                    self.global_error = "PHYSICAL_AUTHORITY_CONFLICT"
                for name in ("bgcs", "bgc_crosswalk"):
                    records = manifest.get(name) or []
                    if not isinstance(records, list):
                        raise ValueError("physical manifest collection is not a list")
                    seen = set()
                    for record in records:
                        if not isinstance(record, dict):
                            raise ValueError("physical manifest record is not an object")
                        bgc = str(record.get("bgc_id") or record.get("BGC_ID") or "")
                        if bgc in seen:
                            self.errors[bgc] = "PHYSICAL_AUTHORITY_AMBIGUOUS"
                        seen.add(bgc)
                        self._add_identity(record, "manifest:" + name)
            import io
            for pattern, owner in (("*cds_table.csv", "cds_table"),
                                   ("*gene_by_gene_all_bgcs.csv", "all_bgc_genes")):
                matches = sorted(self.package.rglob(pattern))
                if len(matches) > 1:
                    self.global_error = "PHYSICAL_AUTHORITY_AMBIGUOUS"
                for path in matches:
                    reader = csv.DictReader(io.StringIO(self._read(path).decode("utf-8")), strict=True)
                    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                        raise ValueError("duplicate/absent membership columns")
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            raise ValueError("malformed membership row")
                        self._add_member(_text(row, "bgc_id", "BGC_ID"), row, owner)
            contexts = sorted(self.package.rglob("*gene_context.jsonl"))
            if len(contexts) > 1:
                self.global_error = "PHYSICAL_AUTHORITY_AMBIGUOUS"
            for path in contexts:
                for line in self._read(path).decode("utf-8").splitlines():
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    bgc = _text(record, "bgc_id", "BGC_ID")
                    for cds in record.get("cds", []) or []:
                        self._add_member(bgc, cds, "gene_context")
        except (OSError, UnicodeError, csv.Error, json.JSONDecodeError, ValueError, TypeError, AttributeError):
            self.global_error = "PHYSICAL_AUTHORITY_MALFORMED"
        self.sources.sort(key=lambda source: source["path"])

    def check(self, row: dict, bgc: str, locus: str) -> tuple[dict, str]:
        claims = physical_assertions(row)
        result = {"binding_depth": "LEGACY_TAG_LENGTH_ONLY", "assertions": claims}
        if not claims:
            return result, ""
        self.load()
        result["binding_depth"] = "PHYSICAL_ASSERTIONS_HELD"
        if self.global_error or bgc in self.errors:
            return result, self.global_error or self.errors[bgc]
        records = self.identities.get(bgc, [])
        crosswalk = [record for record in records if record["owner"] == "crosswalk"]
        if len(crosswalk) != 1:
            return result, "PHYSICAL_AUTHORITY_UNAVAILABLE"
        canonical = crosswalk[0]
        if any(any(record[key] != canonical[key] for key in
                   ("strain", "full_contig", "region", "bgc")) for record in records):
            return result, "PHYSICAL_AUTHORITY_CONFLICT"
        # A literal full-only authority does not assert a normalized node key.
        # Admit that key only when an existing typed producer validates it.
        native_nodes = {record["node"] for record in records
                        if record["node_role"] == "native"}
        if len(native_nodes) > 1:
            return result, "PHYSICAL_AUTHORITY_CONFLICT"
        canonical = {**canonical, "node": next(iter(native_nodes), canonical["full_contig"])}
        members = self.members.get((bgc, locus), [])
        if not members:
            return result, "PHYSICAL_GENE_MEMBERSHIP_UNAVAILABLE"
        for member in members:
            if ((member["full_contig"] and member["full_contig"] != canonical["full_contig"])
                    or (member["region"] and member["region"] != canonical["region"])
                    or (member["strain"] and member["strain"] != self.strain)):
                return result, "PHYSICAL_GENE_MEMBERSHIP_CONFLICT"
        if not any(member["full_contig"] for member in members):
            return result, "PHYSICAL_GENE_MEMBERSHIP_UNAVAILABLE"
        for claim in claims:
            value, role = claim["value"], claim["role"]
            if not value or value.lower() in {"unknown", "none", "null", "na", "n/a", "?", "-"}:
                return result, "QUERY_PHYSICAL_UNVERIFIABLE"
            if role == "region":
                if not _REGION.fullmatch(value) or int(value[6:]) <= 0:
                    return result, "QUERY_REGION_UNVERIFIABLE"
                if value != canonical["region"]:
                    return result, "QUERY_REGION_CONFLICT"
            elif role == "full_contig":
                if value != canonical["full_contig"]:
                    return result, "QUERY_NODE_CONFLICT"
            elif re.fullmatch(r"NODE_[0-9]+", value, flags=re.IGNORECASE):
                return result, "QUERY_NODE_UNVERIFIABLE"
            elif value not in (canonical["full_contig"], canonical["node"]):
                return result, "QUERY_NODE_CONFLICT"
            elif (value != canonical["full_contig"]
                  and len(self.node_contigs.get(value, set())) != 1):
                return result, "QUERY_NODE_UNVERIFIABLE"
        result.update(binding_depth=("FULL_PHYSICAL_ASSERTIONS_BOUND" if any(
            claim["role"] == "full_contig" or claim["role"] == "node"
            and claim["value"] == canonical["full_contig"] for claim in claims)
            else "NORMALIZED_PHYSICAL_ASSERTIONS_BOUND" if any(
                claim["role"] == "node" for claim in claims)
            else "REGION_ASSERTIONS_BOUND"),
            current_identity={key: canonical[key] for key in
                              ("strain", "full_contig", "node", "region", "bgc", "exact_locus")})
        return result, ""

    def verify_unchanged(self) -> None:
        for source in self.sources:
            path = self.package / source["path"]
            if _digest(path.read_bytes()) != source["sha256"]:
                raise PhysicalBindingHold("PHYSICAL_AUTHORITY_DRIFT: selected source changed before publication")


def validate_receipt_authorities(package: Path, binding: dict) -> str:
    """Check material physical inputs without promoting an old admission receipt."""
    if not isinstance(binding, dict) or binding.get("policy") != POLICY:
        return "PHYSICAL_RECEIPT_POLICY_HOLD"
    sources = binding.get("authority_sources")
    if not isinstance(sources, list) or not sources:
        return "PHYSICAL_RECEIPT_AUTHORITY_HOLD"
    for source in sources:
        if not isinstance(source, dict):
            return "PHYSICAL_RECEIPT_AUTHORITY_HOLD"
        rel = source.get("path")
        expected = source.get("sha256")
        if (not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts
                or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)):
            return "PHYSICAL_RECEIPT_AUTHORITY_HOLD"
        try:
            if _digest((Path(package) / rel).read_bytes()) != expected:
                return "PHYSICAL_AUTHORITY_DRIFT"
        except OSError:
            return "PHYSICAL_AUTHORITY_DRIFT"
    return ""


def generation_marker(record: dict, bgc: str) -> dict | None:
    """Validate the optional current-policy marker without reading legacy receipts."""
    if "physical_generations" not in record and "physical_binding_policy" not in record:
        return None
    generations = record.get("physical_generations")
    if (record.get("physical_binding_policy") != POLICY
            or not isinstance(generations, dict) or not generations):
        raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: malformed current-policy marker")
    for rel, reference in generations.items():
        if (not isinstance(rel, str) or "\x00" in rel or Path(rel).is_absolute()
                or ".." in Path(rel).parts or len(Path(rel).parts) != 2
                or Path(rel).as_posix() != rel
                or Path(rel).parts[0] not in {"blastp_online", "blastp_nr",
                    "blastp_clustered_nr", "blastp_swissprot", "blastp_ebi"}
                or Path(rel).name.split("_", 1)[0] != bgc):
            raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: unsafe output locator")
        if not isinstance(reference, dict):
            raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: malformed output reference")
        name = reference.get("receipt")
        if (not isinstance(name, str) or name in {"", ".", ".."}
                or "\x00" in name or Path(name).name != name
                or any(not isinstance(reference.get(key), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", reference[key])
                    for key in ("sha256", "receipt_sha256"))):
            raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: unsafe receipt/hash reference")
    return generations


class PhysicalAdmission:
    """Use existing receipts for a conditional, evidence-preserving generation.

    Legacy operations remain on their original receipt namespace. A historical
    normalized output is never retroactively certified from a new raw header.
    """

    def __init__(self, package: Path, strain: str, *,
                 legacy_depth: str = "LEGACY_TAG_LENGTH_ONLY"):
        self.package = Path(package)
        self.authority = PhysicalAuthority(package, strain)
        self.legacy_depth = legacy_depth
        self.asserted_rows: list[dict] = []
        self.legacy_rows: dict[str, int] = {}
        self.legacy_rows_by_depth: dict[str, dict[str, int]] = {}
        self.raw_sources: dict[Path, str] = {}
        self.previous_bindings: list[dict] = []

    def source(self, path: Path, expected_sha256: str) -> None:
        previous = self.raw_sources.get(Path(path))
        if previous is not None and previous != expected_sha256:
            raise PhysicalBindingHold("BLASTP_SOURCE_DRIFT: source changed during admission")
        self.raw_sources[Path(path)] = expected_sha256

    def check(self, row: dict, bgc: str, locus: str, source_file: str,
              source_sha256: str, row_number: int, prior_reason: str = "", *,
              legacy_depth: str | None = None) -> tuple[dict, str]:
        result, reason = self.authority.check(row, bgc, locus)
        if result["assertions"]:
            self.asserted_rows.append({"bgc": bgc, "locus": locus,
                "source_file": source_file, "source_file_sha256": source_sha256,
                "source_row_number": row_number, "reason": prior_reason or reason, **result})
        else:
            depth = ("LEGACY_ROW_HELD_BY_EXISTING_GUARD" if prior_reason
                     else legacy_depth or self.legacy_depth)
            result["binding_depth"] = depth
            self.legacy_rows[bgc] = self.legacy_rows.get(bgc, 0) + 1
            bucket = self.legacy_rows_by_depth.setdefault(depth, {})
            bucket[bgc] = bucket.get(bgc, 0) + 1
        return result, reason

    def _referenced_generations(self, path: Path) -> tuple[list[dict], bool]:
        ledger_path = self.package / "blastp_online" / "_ingest_ledger.json"
        if not ledger_path.exists():
            return [], False
        try:
            ledger_bytes = ledger_path.read_bytes()
            ledger_sha = _digest(ledger_bytes)
            prior_sha = self.raw_sources.get(ledger_path)
            if prior_sha is not None and prior_sha != ledger_sha:
                raise ValueError("physical generation ledger changed during evaluation")
            self.raw_sources[ledger_path] = ledger_sha
            ledger = json.loads(ledger_bytes)
            if not isinstance(ledger, dict):
                raise ValueError("ledger is not an object")
            names: dict[str, set[tuple[str, str]]] = {}
            affected_bgc = path.name.split("_", 1)[0]
            rel = path.relative_to(self.package).as_posix()
            managed = False
            for bgcs in ledger.values():
                if not isinstance(bgcs, dict):
                    raise ValueError("ledger channel is not an object")
                # All channels can own a generation of a shared overlay, but
                # another BGC's receipt cannot own this output.
                for bgc, record in bgcs.items():
                    if bgc != affected_bgc:
                        continue
                    marker = generation_marker(record, bgc) if isinstance(record, dict) else None
                    if marker is not None:
                        if rel not in marker:
                            continue  # this entry owns a different channel store
                        generation = marker[rel]
                        if not isinstance(generation, dict):
                            raise ValueError("malformed physical generation reference")
                        expected = generation.get("sha256")
                        receipt_sha = generation.get("receipt_sha256")
                        name = generation.get("receipt")
                        if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                               for value in (expected, receipt_sha)):
                            raise ValueError("malformed physical output ledger hash")
                        if not isinstance(name, str) or not name or Path(name).name != name:
                            raise ValueError("unsafe physical generation receipt locator")
                        managed = True
                        names.setdefault(name, set()).add((expected, receipt_sha))
                        continue
                    # Unmarked legacy entries assert no physical generation.
                    # Their source-admission receipt is not a new dependency.
            matching = []
            for name in sorted(names):
                receipt_path = self.package / "blastp_ingest_receipts" / name
                try:
                    receipt_bytes = receipt_path.read_bytes()
                    if {pair[1] for pair in names[name]} != {_digest(receipt_bytes)}:
                        raise ValueError("marked physical generation receipt changed")
                    receipt = json.loads(receipt_bytes)
                except (OSError, json.JSONDecodeError):
                    raise ValueError("marked physical generation receipt unavailable")
                if not isinstance(receipt, dict):
                    raise ValueError("marked physical generation receipt is not an object")
                binding = receipt.get("physical_binding")
                if binding is None:
                    raise ValueError("marked generation receipt lacks physical binding")
                if not isinstance(binding, dict) or not isinstance(binding.get("output_sha256"), dict):
                    raise ValueError("physical generation is malformed")
                if rel not in binding["output_sha256"]:
                    raise ValueError("marked generation receipt lacks its output")
                managed = True
                if {pair[0] for pair in names[name]} != {binding["output_sha256"][rel]}:
                    raise ValueError("physical ledger and receipt generation disagree")
                if binding["output_sha256"][rel] != _digest(path.read_bytes()):
                    continue  # another channel's immutable generation can be older
                reason = validate_receipt_authorities(self.package, binding)
                if reason:
                    continue
                self.previous_bindings.append(binding)
                self.raw_sources[receipt_path] = _digest(receipt_bytes)
                matching.append({"receipt": name, "receipt_sha256": _digest(receipt_bytes),
                                 "output": rel, "output_sha256": binding["output_sha256"][rel]})
            return matching, managed
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            raise PhysicalBindingHold("PHYSICAL_MIGRATION_HOLD: current generation references unreadable or malformed")

    def prepare(self, payloads: dict[Path, str], deletions: set[Path],
                affected_outputs: set[Path]) -> dict | None:
        """Refuse uncertain historical migration before any output is modified."""
        asserted_bgcs = {row["bgc"] for row in self.asserted_rows}
        conflicting_bgcs = {row["bgc"] for row in self.asserted_rows if row["reason"]}
        existing = sorted(path for path in affected_outputs if path.exists())
        retained, managed_any = [], False
        for path in existing:
            matches, managed = self._referenced_generations(path)
            managed_any = managed_any or managed
            bgc = path.name.split("_")[0]
            if bgc in conflicting_bgcs:
                raise PhysicalBindingHold(
                    "PHYSICAL_MIGRATION_HOLD: contradictory source cannot rewrite retained output")
            if bgc in asserted_bgcs or managed:
                if not matches:
                    raise PhysicalBindingHold(
                        "PHYSICAL_MIGRATION_HOLD: retained output has no current authority-bound generation")
                retained.extend(matches)
        if not self.asserted_rows and not managed_any:
            return None
        self.authority.load()
        if managed_any and self.authority.global_error:
            raise PhysicalBindingHold(self.authority.global_error + ": physical generation cannot be downgraded")
        self.verify_unchanged()
        outputs = {path.relative_to(self.package).as_posix(): _digest(text.encode("utf-8"))
                   for path, text in sorted(payloads.items())}
        # Empty/no-op targets still bind retained bytes in this generation.
        for path in existing:
            if path not in payloads and path not in deletions:
                outputs[path.relative_to(self.package).as_posix()] = _digest(path.read_bytes())
        depths = sorted(self.legacy_rows_by_depth)
        binding = {"policy": POLICY, "authority_sources": self.authority.sources,
                "asserted_rows": self.asserted_rows,
                "legacy_rows_by_bgc": dict(sorted(self.legacy_rows.items())),
                "legacy_binding_depth": depths[0] if len(depths) == 1 else
                    "MIXED_SEE_ROW_DEPTH_COUNTS" if depths else self.legacy_depth,
                "legacy_rows_by_binding_depth": {depth: dict(sorted(bgcs.items()))
                    for depth, bgcs in sorted(self.legacy_rows_by_depth.items())},
                "retained_generations": retained, "output_sha256": outputs,
                "deleted_outputs": sorted(path.relative_to(self.package).as_posix() for path in deletions),
                "binding_scope": "Incoming physical assertions checked; unasserted rows retain "
                    + "their recorded per-depth counts; retained hashes do not invent original query identity"}
        # A byte-identical reevaluation reuses its prior physical receipt instead
        # of creating an unbounded chain of identical generations.
        material = set(binding) - {"retained_generations"}
        for previous in self.previous_bindings:
            if all(previous.get(key) == binding[key] for key in material):
                return previous
        return binding

    def verify_unchanged(self) -> None:
        self.authority.verify_unchanged()
        for path, expected in self.raw_sources.items():
            if _digest(path.read_bytes()) != expected:
                raise PhysicalBindingHold("BLASTP_SOURCE_DRIFT: source changed before publication")


def validate_managed_generations(package: Path, ledger: dict) -> None:
    """Verify opt-in physical outputs before the gate uses ledger/fallback rows.

    Source-admission status remains the gate's existing policy. Only an explicit
    current-policy generation marker introduces these stronger dependencies.
    Multiple channels may retain different historical proofs for one overlay;
    at least one referenced generation must bind its current bytes and authority.
    """
    package = Path(package)
    paths: set[Path] = set()
    for bgcs in ledger.values():
        if not isinstance(bgcs, dict):
            continue  # retain the owning ledger reader's legacy policy
        for bgc, record in bgcs.items():
            if not isinstance(record, dict):
                continue
            generations = generation_marker(record, bgc)
            if generations is None:
                continue
            for rel in generations:
                paths.add(package / rel)
    if not paths:
        return
    manager = PhysicalAdmission(package, "")
    ledger_path = package / "blastp_online" / "_ingest_ledger.json"
    try:
        ledger_bytes = ledger_path.read_bytes()
        if json.loads(ledger_bytes) != ledger:
            raise ValueError("ledger changed since the gate's admission read")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: ledger changed during gate evaluation") from exc
    manager.source(ledger_path, _digest(ledger_bytes))
    for path in sorted(paths):
        if not path.is_file():
            raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: bound output unavailable")
        matches, managed = manager._referenced_generations(path)
        if not managed or not matches:
            raise PhysicalBindingHold("PHYSICAL_GENERATION_HOLD: no current authority-bound output generation")
    manager.verify_unchanged()
