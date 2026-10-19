"""Opt-in captured intake session; source binding is separate from scientific certainty.

This route covers intake only. It does not run gold analysis, Mode B, RG-GMCI,
resume or batch processing. Unsupported consumers hold before capture/publication.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import weakref

from .archive_snapshot import ArchiveSnapshot, ArchiveSnapshotPolicy, snapshot_zip, validate_captured, parse_captured, ArchiveSnapshotRefused
from .ziputil import duplicate_member_names, nonregular_file_names, is_macos_metadata_name


class CapturedIntakeHold(ValueError):
    """Typed admission hold; no sealed package or workbook is implied."""


def encode(value):
    """Deterministic finite JSON; preserve nulls/errors instead of inventing values."""
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


@dataclass(frozen=True)
class EvidenceOptions:
    json_mode: str = "off"
    want_tigrfam: bool = True
    include_structured: bool = False
    budget_seconds: int = 300

    def validate(self):
        if (self.json_mode not in {"off", "bounded", "full"}
                or type(self.want_tigrfam) is not bool or type(self.include_structured) is not bool
                or type(self.budget_seconds) is not int or self.budget_seconds < 0):
            raise CapturedIntakeHold("CAPTURED_EVIDENCE_OPTIONS_INVALID")


@dataclass(frozen=True, eq=False)
class BoundEvidence:
    _session_token: object
    input_sha256: str
    _payload: bytes
    payload_sha256: str
    options: EvidenceOptions


class CapturedIntakeSession:
    """Reuse exactly one08capture across identification, evidence and intake products."""

    def __init__(self, snapshot, *, policy, expected_sha256=None, require_complete_genbank=True):
        if not isinstance(snapshot, ArchiveSnapshot) or not isinstance(policy, ArchiveSnapshotPolicy):
            raise CapturedIntakeHold("CAPTURED_INTAKE_CAPABILITY_REQUIRED")
        try:
            self.capture_admission = validate_captured(snapshot, policy=policy, expected_sha256=expected_sha256)
        except ArchiveSnapshotRefused as exc:
            if str(exc) == "ARCHIVE_SNAPSHOT_POLICY_MISMATCH":
                raise CapturedIntakeHold("CAPTURED_INTAKE_POLICY_MISMATCH") from exc
            raise
        if type(require_complete_genbank) is not bool:
            raise CapturedIntakeHold("CAPTURED_INTAKE_COMPLETENESS_POLICY_INVALID")
        self.snapshot, self.policy = snapshot, policy
        self.expected_sha256 = expected_sha256 if expected_sha256 is not None else snapshot.expected_sha256
        self.require_complete_genbank = require_complete_genbank
        self._token = object()
        self._minted_evidence = weakref.WeakSet()
        with snapshot_zip(snapshot) as archive:
            # Partial member admission never resolves ambiguous duplicate namespaces.
            duplicates = [n for n in duplicate_member_names(archive) if not is_macos_metadata_name(n)]
            special = [n for n in nonregular_file_names(archive) if not is_macos_metadata_name(n)]
            if duplicates or special:
                raise CapturedIntakeHold("CAPTURED_INTAKE_NAMESPACE_AMBIGUOUS_OR_SPECIAL")

    @classmethod
    def capture(cls, source, *, policy, expected_sha256=None,
                require_complete_genbank=True, consumer="intake"):
        if consumer != "intake":
            raise CapturedIntakeHold("CAPTURED_CONSUMER_UNAVAILABLE: " + str(consumer))
        snapshot = ArchiveSnapshot.capture(source, policy=policy, expected_sha256=expected_sha256)
        return cls(snapshot, policy=policy, expected_sha256=expected_sha256,
                   require_complete_genbank=require_complete_genbank)

    def parse_evidence(self, options=EvidenceOptions()):
        """Keep status-pass options and bounded fallback on the same captured bytes."""
        if not isinstance(options, EvidenceOptions):
            raise CapturedIntakeHold("CAPTURED_EVIDENCE_OPTIONS_INVALID")
        options.validate()
        from . import antismash_evidence as ev
        from . import cli
        mode = options.json_mode
        state = "DISABLED" if options.budget_seconds == 0 else "NOT_APPLICABLE"
        kwargs = dict(want_tigrfam=options.want_tigrfam, include_structured=options.include_structured)
        if mode == "bounded" and options.budget_seconds:
            try:
                data = cli._with_timeout(options.budget_seconds, ev.parse_antismash_evidence,
                                         self.snapshot, json_mode=mode, **kwargs)
                state = ("RETURNED_GUARD_ARMED" if hasattr(cli._signal, "SIGALRM")
                         else "RETURNED_GUARD_UNAVAILABLE")
            except cli._BoundedTimeout:
                mode = "off"
                data = ev.parse_antismash_evidence(self.snapshot, json_mode=mode, **kwargs)
                state = "EXCEEDED_FALLBACK_OFF"
        else:
            data = ev.parse_antismash_evidence(self.snapshot, json_mode=mode, **kwargs)
        data["json_mode_requested"] = options.json_mode
        data["json_parse_budget"] = {"seconds": options.budget_seconds, "state": state,
                                    "scope": "requested status paths; fallback outside budget"}
        payload = encode({"evidence": data, "options": asdict(options),
                          "input_sha256": self.snapshot.input_sha256})
        bound = BoundEvidence(self._token, self.snapshot.input_sha256, payload,
                              hashlib.sha256(payload).hexdigest(), options)
        self._minted_evidence.add(bound)
        return bound

    def working_evidence(self, bound):
        """Return a fresh working copy while retaining immutable parse-origin binding."""
        if (not isinstance(bound, BoundEvidence) or bound not in self._minted_evidence
                or not isinstance(bound.options, EvidenceOptions)
                or type(bound._payload) is not bytes or bound._session_token is not self._token
                or bound.input_sha256 != self.snapshot.input_sha256
                or hashlib.sha256(bound._payload).hexdigest() != bound.payload_sha256):
            raise CapturedIntakeHold("CAPTURED_EVIDENCE_BINDING_REFUSED")
        envelope = json.loads(bound._payload)
        if (envelope.get("options") != asdict(bound.options)
                or envelope.get("input_sha256") != bound.input_sha256):
            raise CapturedIntakeHold("CAPTURED_EVIDENCE_BINDING_REFUSED")
        return envelope["evidence"]

    def prepare(self, strain="auto", *, options=EvidenceOptions(), bound_evidence=None):
        """Compute the complete supported intake slice before any output publication."""
        from . import parsers
        from .antismash_input import identify
        from .strain_identity import resolve_strain_id, validate_strain_id
        info = identify(self.snapshot)
        if not info.is_antismash:
            raise CapturedIntakeHold("CAPTURED_INPUT_NOT_ANTISMASH")
        resolved = resolve_strain_id(strain, self.snapshot)
        if resolved.refused or resolved.strain_id is None:
            raise CapturedIntakeHold("CAPTURED_STRAIN_IDENTITY_REFUSED")
        strain_id = validate_strain_id(resolved.strain_id)
        completeness = {}
        parsers.read_genbank_records(self.snapshot, completeness_out=completeness)
        members = completeness.get("members", [])
        complete = bool(members) and all(row["state"] == "COMPLETE" for row in members)
        if self.require_complete_genbank and not complete:
            raise CapturedIntakeHold("CAPTURED_GENBANK_COMPLETENESS_REFUSED")
        metrics = parsers.assembly_metrics_from_zip(self.snapshot)
        bound = self.parse_evidence(options) if bound_evidence is None else bound_evidence
        evidence = self.working_evidence(bound)
        if bound.options != options:
            raise CapturedIntakeHold("CAPTURED_EVIDENCE_OPTIONS_MISMATCH")
        core = {}
        def parse_bound(source, *, json_mode, core_snapshot_out):
            if source is not self.snapshot:
                raise CapturedIntakeHold("CAPTURED_EVIDENCE_SOURCE_OBJECT_MISMATCH")
            return parsers.parse_bgcs_from_zip(source, evidence=evidence, json_mode=json_mode,
                                              core_snapshot_out=core_snapshot_out)
        bgcs, transaction = parse_captured(self.snapshot, policy=self.policy,
                    expected_sha256=self.expected_sha256, json_mode=evidence["json_mode"],
                    core_snapshot_out=core, require_complete_genbank=self.require_complete_genbank,
                    parse_operation=parse_bound)
        cds = parsers.extract_cds_features(self.snapshot)
        domains = parsers.extract_domain_features(self.snapshot)
        contigs = parsers.extract_contig_sequences(self.snapshot)
        roster = [{"contig": name, "length": len(sequence),
                   "sha256_uppercase": hashlib.sha256(sequence.upper().encode()).hexdigest()}
                  for name, sequence in sorted(contigs.items())]
        # Return all working observations/errors/audits, not a selected-field projection.
        return {"schema": "sapote.captured-intake.v1", "scope": "INTAKE_ONLY_NOT_FULL_RUN",
                "input_sha256": self.snapshot.input_sha256, "source_label": self.snapshot.label,
                "capture_receipt": {"policy": asdict(self.policy), "archive_bytes": len(self.snapshot._payload),
                                    "member_count": self.snapshot.member_count,
                                    "declared_uncompressed_bytes": self.snapshot.declared_uncompressed_bytes,
                                    "verified_uncompressed_bytes": self.snapshot.verified_uncompressed_bytes},
                "original_version": self.capture_admission["original_version"],
                "transaction": transaction,
                "strain_id": strain_id, "strain_resolution": asdict(resolved),
                "identification": asdict(info), "assembly": asdict(metrics),
                "genbank": completeness, "genbank_complete": complete,
                "denominator": {"kind": "PARSED_BGC_RECORDS", "value": len(bgcs),
                                "source_complete": complete, "expected_biological_total": None},
                "bgcs": [asdict(row) for row in bgcs], "cds": [asdict(row) for row in cds],
                "domains": [asdict(row) for row in domains], "sequence_roster": roster,
                "sequence_context_state": "AVAILABLE_BOUND" if contigs else "UNAVAILABLE",
                "evidence": evidence, "evidence_parse_origin_sha256": bound.payload_sha256,
                "working_evidence_sha256": hashlib.sha256(encode(evidence)).hexdigest(),
                "core_records_sha256": core["records_sha256"],
                "biological_absence": "NOT_ESTABLISHED", "upstream_search_completion": "NOT_ESTABLISHED",
                "unsupported_consumers": ["gold", "mode_b", "rggmci", "resume", "batch"]}
