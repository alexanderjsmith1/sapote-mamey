"""Mamey data models.

Extraction layer only. No WL scoring, no claim confidence, no prose.
Those live in the Mamey v1.2 prompt (judgment layer).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

from .bioactivity_metadata import normalize_bioactivity, not_supplied


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

@dataclass
class AssemblyMetrics:
    genome_bp: int
    contigs: int
    n50: int | None
    gc_pct: float | None
    largest_contig: int | None


# ---------------------------------------------------------------------------
# Per-feature records (parsed from antiSMASH GBK)
# ---------------------------------------------------------------------------

@dataclass
class CDSFeature:
    contig: str
    start: int
    end: int
    strand: int
    locus_tag: str
    product: str
    translation: str = ""
    nucleotide_seq: str = ""
    qualifiers: dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainFeature:
    contig: str
    start: int
    end: int
    strand: int
    feature_type: str       # aSDomain | PFAM_domain | CDS_motif | module
    locus_tag: str
    domain: str
    database: str
    bitscore: float | None = None
    evalue: float | None = None
    substrate_consensus: str = ""   # A-domain '/specificity=substrate consensus: <aa>' (Patch F)
    qualifiers: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""           # archive member; retained for coordinate-frame provenance


# ---------------------------------------------------------------------------
# BGC record — one per antiSMASH region
# ---------------------------------------------------------------------------

@dataclass
class BGCRecord:
    bgc_id: str                         # BGC001 … BGCnnn  (locked at parse time)
    contig: str
    region_number: int
    start: int
    end: int
    contig_length: int
    products: list[str] = field(default_factory=list)
    mibig_hits: list[str] = field(default_factory=list)
    edge_status: str = "Full-contig"    # Interior | Edge | Full-contig
    architecture_confidence: str = "D"  # A–E  (parsers.py assigns; prompt refines)
    architecture_rationale: str = ""
    architecture_capacity: str = ""           # v9.7.21: claim-safe class-CAPACITY call from class_architecture.py
    architecture_class_confidence: str = ""    #          (HIGH/MODERATE/LOW) — covers the marker-invisible classes

    # User-facing antiSMASH crosswalk fields.  These prevent naked BGC IDs
    # from appearing without the contig/node/region identifiers a wet-lab or
    # antiSMASH user can actually find in their files.
    antismash_region: str = ""          # e.g. region004
    source_gbk: str = ""                # archive path to source region GBK
    node_id: str = ""                   # original node-like ID when available
    user_label: str = ""                # e.g. BGC004 / ctg10 region004
    # KCB / RiQ from antismash_evidence parser
    kcb_top: str | None = None
    clusterblast_top: str | None = None  # v9.7.22: raw rank-1 KnownClusterBlast line (the genome self-hit for
    #                                      genome-derived clusters). kcb_top now surfaces the MIBiG identity line
    #                                      when one exists; this field preserves the displaced rank-1 line.
    kcb_cumulative: float | None = None
    kcb_protein_hits: int | None = None
    # Typed source state. UNKNOWN_KCB is absence, not observed low similarity.
    kcb_evidence_state: str = "UNKNOWN_KCB"
    # v9.7.166: top-N ranked ClusterBlast hits WITH organism names, in antiSMASH rank order.
    # antiSMASH's clusterblast files carry a "Source:" (organism) line per hit block that the
    # parser already reads but previously discarded after taking rank-1. This preserves the
    # ranked list (e.g. "NZ_CP050692 | Streptomyces antibioticus DSM 41481 | Type: t2pks") so
    # the package answers "what organism does this align to" without re-parsing the raw ZIP.
    # Each entry: {"rank": int, "label": str, "score": float, "protein_hits": int|None}.
    clusterblast_ranked: list = field(default_factory=list)
    # v9.7.166 (#2): full ranked KnownClusterBlast MIBiG hits, not just the rank-1 anchor.
    # antiSMASH's "Significant hits" list is parsed into mibig_reference_hits but previously
    # only rank-1 reached the BGC (as kcb_top / closest_mibig_accession). This keeps the top-N
    # so "no KCB hit" ambiguity is resolvable — a BGC with rank-2+ MIBiG hits is not KCB-dark.
    # Each entry: {"rank": int, "accession": str, "product": str}.
    mibig_ranked: list = field(default_factory=list)
    # v9.7.166 (#3): SubClusterBlast sub-operon hits (sugar-biosynthesis operons, PKS starter
    # units, NRPS monomer pathways). antiSMASH computes these; rggmci parsed them but dropped
    # them (the planned subcluster_markers was never surfaced). Excluded from whole-cluster
    # RG-GMCI geometry (correct — they are sub-operon), but retained here as functional markers,
    # directly relevant to saccharide/deoxysugar-operon interpretation.
    # Each entry: {"ref": str, "rank": int, "nprot": int|None, "mean_identity": float|None}.
    subcluster_hits: list = field(default_factory=list)
    riq_score: float | None = None
    riq_label: str | None = None

    # Deterministic product/source provenance contract (schema v1.1).
    # These fields must remain source-bounded: a MIBiG product claim is allowed
    # only when a concrete knownclusterblast file/rank/accession locator exists.
    closest_mibig_accession: str = "UNRESOLVED"
    closest_candidate_kcb_product: str = "UNRESOLVED"
    closest_product_provenance: str = "UNRESOLVED"
    source_kcb_file: str = "UNRESOLVED"
    source_kcb_locator: str = "UNRESOLVED"
    kcb_hit_rank: str = "UNRESOLVED"
    denominator_type: str = "UNRESOLVED"
    parse_confidence: str = "LOW"
    needs_manual_kcb_check: str = "yes"
    product_claim_ceiling: str = "unresolved; do not use product name"
    release: str = ""                   # R1: PUBLIC/PRIVATE, set at run time from derive_release(strain_id)
    privacy_tier: str = "UNASSIGNED"    # named operator access tier; never biological evidence
    privacy_assignment_state: str = "UNASSIGNED"  # EXACT|DEFAULT|LEGACY_DERIVATION
    cctt_triggers: str = ""             # R-A: per-BGC CCTT T43 triggers, written back from source_scans
    cctt_uncorroborated: str = ""        # N-05: class-defining triggers that fired without corroborating product class

    # Region-merge inflation guard: antiSMASH collapses neighbouring protoclusters into one region; when
    # >=3 /kind="single" cand_clusters share a region, its product string is a merge (not one hybrid cluster)
    # and a single lead score aggregates them. Flag so the inflated multi-class string isn't read as one lead.
    composite_region: bool = False
    single_protocluster_count: int = 0
    # FA3 / R1: antiSMASH tags a genuinely FUSED multi-class pathway with a cand_cluster
    # /kind="chemical_hybrid" (cross-class module wiring), as opposed to merely adjacent
    # protoclusters (/kind="neighbouring"|"interleaved") or a lone /kind="single". mamey's
    # composite_region flag only counts kind="single">=3 to DEMOTE inflated merges; it never
    # read chemical_hybrid, which is the opposite signal — a coherent multi-module architecture.
    # This is a claim-safe CAPACITY descriptor ("multiple biosynthetic classes are fused in one
    # candidate cluster"), NOT a product/novelty/activity claim. Additive; defaults False.
    has_chemical_hybrid: bool = False
    # Exact antiSMASH cand_cluster /kind observations plus a flag-only structural
    # classification. Neither field renames, splits, or reorders the locked BGC.
    cand_cluster_kinds: list[str] = field(default_factory=list)
    overmerge_state: str = "NOT_VERIFIABLE"
    # v9.7.240 (P2): the TRUE number of antiSMASH `protocluster` features in the region.
    # Distinct from single_protocluster_count, which counts cand_clusters with /kind="single".
    # A chemical_hybrid region has >=2 protoclusters but may have exactly 1 single-kind
    # cand_cluster (AS-XXX BGC041: 3 vs 1), so the two are NOT interchangeable. Consumers
    # that mean "how many protoclusters did antiSMASH resolve here" must read this field.
    protocluster_count: int = 0
    # Per-protocluster (product + region-local span) for a composite region — de-inflates the merged product
    # string into its constituent single-class protoclusters. Populated only when composite_region is True.
    protocluster_breakdown: list = field(default_factory=list)
    # Authoritative antiSMASH PKS_KS aSDomain count for the region — a reliable modular-PKS module count
    # (the KS active-site motif is too strict to count modules). Used by the polyene-vs-RiPP mis-anchor gate.
    ks_domain_count: int = 0
    # antiSMASH PKS_KS(Enediyne-KS) subtype count — the enediyne warhead PKS. A genuine enediyne carries >=1;
    # a calicheamicin/neocarzinostatin KCB similarity hit WITHOUT it is a mis-anchor (§4.3 guard).
    ene_ks_count: int = 0

    # v9.7.86: deterministic compound-class annotation (chemotype + evidence trail).
    # Populated from antiSMASH t2pks.product_classes (primary) / resolved MIBiG product
    # line (own-evidence only; never raw kcb_top). Annotation-only for most chemotypes;
    # three families carry a scored consequence applied in scoring.py.
    compound_class_annotation: dict = field(default_factory=dict)

    notes: list[str] = field(default_factory=list)

    def crosswalk_dict(self) -> dict:
        """Stable antiSMASH/user-facing identifier map for reports and workbooks."""
        return {
            "bgc_id": self.bgc_id,
            "user_label": self.user_label or (f"{self.node_id or self.contig} region{int(self.region_number):03d} ({self.bgc_id})" if str(self.region_number).strip().lstrip("-").isdigit() else f"{self.node_id or self.contig} region{self.region_number} ({self.bgc_id})"),
            "contig": self.contig,
            "node_id": self.node_id or self.contig,
            "antismash_region": self.antismash_region or (f"region{int(self.region_number):03d}" if str(self.region_number).strip().lstrip("-").isdigit() else f"region{self.region_number}"),
            "region_number": self.region_number,
            "source_gbk": self.source_gbk,
            "start": self.start,
            "end": self.end,
            "contig_length": self.contig_length,
            "edge_status": self.edge_status,
            "products": self.products,
        }

    @property
    def length_kb(self) -> float:
        return round(max(0, self.end - self.start) / 1000, 2)




@dataclass
class TriageRecord:
    bgc_id: str
    ab_score: float
    af_score: float
    novelty_score: float
    lead_tier: str
    claim_confidence: str
    rationale: str
    primary_metabolism_flag: bool = False  # v9.7.7: region dominated by housekeeping/pigment core genes (P0 guard)
    standing_rule_flag: str = ""            # v9.7.8: permanent-exclusion downgrade (saccharide/NAPAA/hglE-KS)
    corrected_rank: int | None = None       # v9.7.8: rank among non-downgraded, non-primary-metab leads
    misanchor_flag: str = ""                 # v9.7.15: aminoglycoside(no-DOIS) / polyene(<4 PKS_KS) anchor downgrade
    mobile_element_flag: str = ""            # v9.7.33 #28: region dominated by mobile/ICE machinery, not class-typed
    contig: str = ""                         # v9.7.20: the BGC's source contig/node — carried on the record so a
    user_label: str = ""                     # triage-derived report can NEVER name a bare "BGC003" without a
    #                                          contig/node location (e.g. the DAPR C1/C2 lead tables). Mirrors
    #                                          BGCRecord.contig / .user_label.
    architecture_capacity: str = ""          # v9.7.21: class-capacity call (mirrors BGCRecord) — carried into
    architecture_class_confidence: str = ""  #          triage so per-BGC output shows capacity for marker-invisible classes
    concordance_verdict: str = ""            # C1 v9.7.58: CONCORDANT/PARTIAL/DISCORDANT/NO_REFERENCE from concordance_per_bgc
    umed_gap_flag: str = ""                   # v9.7.62: MATURATION_GAP when RiPP/nucleoside BGC has no nearby maturation genes
    ab_recall: float = 0.0                   # v9.7.120: boost-only antimicrobial-recall AB (compound-anchor capacity; parallel to ab_score, never overwrites it)
    af_recall: float = 0.0                   # v9.7.120: boost-only antimicrobial-recall AF
    recall_family: str = ""                  # v9.7.120: resolved compound family that drove the recall boost ("" when none)


# ---------------------------------------------------------------------------
# Source-derived scan bundle — output of run_source_scans()
# ---------------------------------------------------------------------------

@dataclass
class SourceScanBundle:
    """All nine first-pass source-derived scans.

    Every field is a dict produced by the corresponding scan function.
    Shape: {"status": str, "counts": dict, "bgc_coupling": dict, ...}

    The scan functions produce counts and coupling maps.  Prose interpretation
    lives in the Mamey v1.2 prompt.
    """
    chitinase: dict[str, Any]           # CGAD
    tfbs: dict[str, Any]                # TFBS motif scan
    blda_tta: dict[str, Any]            # bldA / TTA gating
    regulators: dict[str, Any]          # regulator keyword scan
    transporters: dict[str, Any]        # transporter keyword scan
    resistance: dict[str, Any]          # resistance gene scan
    cctt: dict[str, Any]                # CCTT T43 triggers
    flbr: dict[str, Any]                # FLBR / LMPKS
    cassettes: dict[str, Any]           # cassette markers
    umed: dict[str, Any]                # UMED maturation
    efls: dict[str, Any]                # EFLS linkage pairs
    domain_architecture: dict[str, Any] # domain counts per BGC
    resistance_tiers: dict[str, Any]    # T1/T2/T3/NULL per BGC
    wetlab_rows: dict[str, Any]         # class-default wet-lab rows
    qs_signals: dict[str, Any]          # QS + NAPAA routing flags
    glycosylation_arms: dict[str, Any]  # §34.5 glycosylation-arm candidates
    per_bgc_dss: dict[str, Any]         # source-derived DSS (0–5) per BGC
    rggmci: dict[str, Any]               # full RG-GMCI pre-triage linkage pass
    primary_metabolism: dict[str, Any] = field(default_factory=dict)  # v9.7.7: per-BGC housekeeping/pigment core-gene flag (P0 guard)
    misanchor_guards: dict[str, Any] = field(default_factory=dict)  # v9.7.15: DOIS/aminoglycoside + polyene-vs-RiPP anchor gates
    concordance_per_bgc: dict[str, Any] = field(default_factory=dict)  # C1 v9.7.58: per-BGC concordance verdict (CONCORDANT/PARTIAL/DISCORDANT/NO_REFERENCE)
    clusterblast_genes: dict[str, Any] = field(default_factory=dict)  # P-CBG v9.7.100: per-gene ClusterBlast correspondence (query gene -> reference gene, %id/%cov/score)
    mibig_per_gene: dict[str, Any] = field(default_factory=dict)  # P-MPG: rank-uncapped KnownClusterBlast/MIBiG per-gene evidence
    antismash_structured: dict[str, Any] = field(default_factory=dict)  # P-AS-TABLES: module/RiPP/motif evidence tables
    functional_profiles: dict[str, Any] = field(default_factory=dict)  # P-CBDB v9.7.100: per-BGC gene-role profile (core/tailoring/transport/regulatory) for rescue complementarity
    pks_ks_scan: dict[str, Any] = field(default_factory=dict)  # .359 (phylogenomics-lane P358): _4B intrinsic PKS-KS cross-contig clade scan (deterministic, offline; feeds _4D two-proof)


# ---------------------------------------------------------------------------
# Run context and master record
# ---------------------------------------------------------------------------

@dataclass
class RunContext:
    strain_id: str                      # e.g. Actinomadura_rubrisoli_H3C3
    display_name: str                   # e.g. Actinomadura rubrisoli H3C3
    version: str                        # Mamey version string
    analysis_mode: str                  # smoke | gold  (standard retired v9.7.92 -> aliased to gold)
    input_zip: str
    outdir: str
    taxonomy: str = "not verified"
    source: str = "not supplied"
    # AMBER-03-2: how strongly the isolation source above is evidenced. `source` is a free
    # string, so a host read off a folder name and a host traced to a GenBank accession were
    # indistinguishable in every downstream artifact. One of:
    #   accession — traced to a deposited record (GenBank /isolation_source, /host, BioSample)
    #   table     — traced to the authoritative strain table (an accession-bearing row)
    #   filename  — inferred from a file/folder label; NOT traced to a record
    #   asserted  — supplied by a person with no on-disk trace (the safe default)
    # Descriptive only: it never changes a score, a tier or a gate verdict.
    source_provenance: str = "asserted"
    # v9.7.392 candidate: a typed metadata object, never a named assay default.
    # Direct and CLI construction share the central admission owner.  The
    # field stays descriptive and is never a scoring input.
    bioactivity: Any = field(default_factory=not_supplied)
    master_path: str | None = None
    # BR6-406-REBASE (originally Codex, engine-facing half; models.py hunk 1 DROPPED --
    # BGCRecord.privacy_tier already exists, see BGCRecord above / BR6_REBASE_MAP.md). These are
    # genuinely new on RunContext: generic project registry axes. Genome and bioassay
    # availability are deliberately independent; neither is inferred from the other.
    # NAMING (engine 1.9.146, owner ruling 2026-09-03): the run-level project-registry tier is named
    # `project_privacy_tier` so it can never be confused with BGCRecord.privacy_tier (sentinel
    # "UNASSIGNED", written by the landed --privacy-profile mechanism, the only field that drives
    # release). The registry tier is RECORDED here and in the manifest; it does not drive release in
    # this engine. Supplying both --project-registry and --privacy-profile is a typed refusal in cli.
    project_privacy_tier: str = "UNDECLARED"
    project_privacy_tier_source: str = "NOT_PROVIDED"
    publication_status: str = "NOT_PROVIDED"
    genome_state: str = "NOT_PROVIDED"
    project_registry_sha256: str = ""
    assay_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.bioactivity = normalize_bioactivity(self.bioactivity)

    @property
    def strain_code(self) -> str:
        """Short code for workbook sheet names (≤20 chars)."""
        parts = self.strain_id.replace(" ", "_").split("_")
        # Last token is usually the strain code (H3C3, AS-XXX, etc.)
        code = parts[-1] if len(parts[-1]) <= 8 else parts[-1][:8]
        return code


@dataclass
class MameyRun:
    context: RunContext
    assembly: AssemblyMetrics
    bgcs: list[BGCRecord]
    scan_status: dict[str, Any]         # nine scan states for the manifest
    source_scans: SourceScanBundle | None = None
    issues: list[str] = field(default_factory=list)

    @property
    def triage(self):
        from .scoring import triage_bgcs
        return triage_bgcs(self.bgcs, self.source_scans.rggmci if self.source_scans else None, self.source_scans if self.source_scans else None)

    def resistance_gene_summary(self) -> dict[str, Any]:
        if not self.source_scans:
            return {}
        return {
            "counts": self.source_scans.resistance.get("counts", {}),
            "bgc_coupling": self.source_scans.resistance.get("bgc_coupling", {}),
            "tier_counts": self.source_scans.resistance_tiers.get("tier_counts", {}),
        }

    def to_dict(self) -> dict[str, Any]:
        """Full JSON snapshot — the manifest handoff object."""
        from . import BUNDLE_VERSION
        from .assembly import (corrected_bgc_count, assembly_tier,
                               assembly_quality as _assembly_quality)
        from .source_provenance import source_provenance_note
        from collections import Counter
        c = Counter(b.edge_status for b in self.bgcs)
        raw = len(self.bgcs)
        interior = c.get("Interior", 0)
        edge = c.get("Edge", 0)
        fc = c.get("Full-contig", 0)
        interior_pct = round(interior / raw * 100, 1) if raw else None
        ss = self.source_scans

        def _uniform_bgc_field(name: str) -> str:
            values = sorted({
                str(getattr(bgc, name, "") or "").strip()
                for bgc in self.bgcs
                if str(getattr(bgc, name, "") or "").strip()
            })
            if len(values) == 1:
                return values[0]
            return "UNRESOLVED_MISSING" if not values else "UNRESOLVED_MIXED"

        # v9.7.86 A1: carry triage scores onto each bgcs[] record so the manifest is a
        # self-sufficient handoff to the figure/consumer layer (previously these lived only
        # in the workbook Triage_First_Board, forcing a workbook join to plot the landscape).
        _triage_by_id = {t.bgc_id: t for t in (self.triage or [])}

        # v9.7.86 A3: per-BGC bldA tier, so a per-BGC bldA figure need not re-derive the
        # tier from raw TTA counts. per_bgc is a dict keyed by bgc_id; tier under bldA_tier.
        _blda_tier_by_id = {}
        if ss and isinstance(getattr(ss, "blda_tta", None), dict):
            _pb = ss.blda_tta.get("per_bgc", {}) or {}
            if isinstance(_pb, dict):
                for _bid, _rec in _pb.items():
                    if isinstance(_rec, dict) and _rec.get("bldA_tier"):
                        _blda_tier_by_id[_bid] = _rec.get("bldA_tier")

        def _bgc_record(b):
            d = {**asdict(b), "length_kb": round((b.end - b.start) / 1000, 2)}
            t = _triage_by_id.get(b.bgc_id)
            if t is not None:
                d["ab_score"] = t.ab_score
                d["af_score"] = t.af_score
                d["novelty"] = t.novelty_score
                d["lead_tier"] = t.lead_tier
                d["claim_confidence"] = t.claim_confidence
                # BCHERRY-374: the four flags scoring.py:686 actually gates corrected_rank on
                # (standing_rule_flag, primary_metabolism_flag, misanchor_flag,
                # mobile_element_flag) were silently absent from this "self-sufficient handoff"
                # (see the A1 comment above) — a fresh judgment session reading manifest.json
                # alone saw a downgraded lead_tier (e.g. Inventory) with no field explaining why,
                # exactly the "resurrected by a fresh, thin-context session" risk
                # rules_registry.json's own docstring warns about. corrected_rank carried too,
                # since it is derived from the same three-flag gate.
                d["standing_rule_flag"] = t.standing_rule_flag
                d["primary_metabolism_flag"] = t.primary_metabolism_flag
                d["misanchor_flag"] = t.misanchor_flag
                d["mobile_element_flag"] = t.mobile_element_flag
                d["corrected_rank"] = t.corrected_rank
            if b.bgc_id in _blda_tier_by_id:
                d["blda_tier"] = _blda_tier_by_id[b.bgc_id]
            return d

        # v9.7.86 A2: populate top-level split_pathway_candidates from the HIGH-confidence
        # RG-GMCI subset, instead of emitting an always-empty []. Keeps the field, the
        # run-issue text ("N RG-GMCI HIGH pairs"), and the workbook in agreement. The HIGH
        # pairs (rggmci_confidence == "HIGH_RG_GMCI_RESCUE") live in ranked_pairs.
        _split_candidates = []
        if ss and isinstance(getattr(ss, "rggmci", None), dict):
            _all_pairs = list(ss.rggmci.get("ranked_pairs", []) or []) + \
                         list(ss.rggmci.get("split_candidates", []) or [])
            _seen = set()
            for _pair in _all_pairs:
                if "HIGH" in str(_pair.get("rggmci_confidence", "")).upper():
                    _key = _pair.get("pair") or id(_pair)
                    if _key not in _seen:
                        _seen.add(_key)
                        _split_candidates.append(_pair)

        return {
            "strain_id": self.context.strain_id,
            "display_name": self.context.display_name,
            "workflow_version": f"Mamey v{self.context.version}",
            "bundle_version": BUNDLE_VERSION,
            # These package-level values are projections of the already-governed
            # per-BGC fields. Mixed/missing inputs remain explicit; the manifest
            # never guesses a public or private state.
            "release": _uniform_bgc_field("release"),
            "privacy_tier": _uniform_bgc_field("privacy_tier"),
            "privacy_assignment_state": _uniform_bgc_field("privacy_assignment_state"),
            "analysis_date": __import__("datetime").date.today().isoformat(),
            "mode": self.context.analysis_mode,
            "taxonomy": self.context.taxonomy,
            "source": self.context.source,
            # AMBER-03-2: provenance strength of `source`, plus the claim-safety sentence a
            # downstream caption/figure must carry when the host is not traced to a record.
            "source_provenance": self.context.source_provenance,
            "source_provenance_note": source_provenance_note(
                self.context.source, self.context.source_provenance),
            # BR6-406-REBASE (originally Codex, engine-facing half): project-registry surfaces,
            # independent of the per-BGC "release"/"privacy_tier" fields emitted per-record below
            # (BGCRecord's own, via asdict(b) -- see BR6_REBASE_MAP.md).
            "project_privacy": {
                "project_privacy_tier": self.context.project_privacy_tier,
                "project_privacy_tier_source": self.context.project_privacy_tier_source,
                "drives_release": False,  # recorded only; BGCRecord.privacy_tier / release own that (1.9.146)
                "publication_status": self.context.publication_status,
                "project_registry_sha256": self.context.project_registry_sha256,
            },
            "genome_state": self.context.genome_state,
            "bioassay_scope": dict(self.context.assay_summary or {
                "assay_data_state": "NOT_PROVIDED",
                "assay_record_count": 0,
            }),
            "bioactivity": self.context.bioactivity,
            # AMBER-03-1: the raw metrics PLUS a machine-readable contiguity verdict and a
            # ready-to-paste caveat sentence. bgc_counts.assembly_tier below is derived from
            # interior_pct (BGC boundary status) and is NOT an assembly-contiguity statement;
            # assembly.quality.fragmentation_tier is. Captions should be generated from this
            # block rather than hand-typed alongside the table.
            "assembly": {**asdict(self.assembly),
                         "quality": _assembly_quality(self.assembly)},
            "bgc_counts": {
                "raw": raw, "interior": interior, "edge": edge,
                "full_contig": fc,
                "corrected": corrected_bgc_count(interior, edge, fc),
                "interior_pct": interior_pct,
                "assembly_tier": assembly_tier(interior_pct),
            },
            "bgcs": [_bgc_record(b) for b in self.bgcs],
            "scan_status": self.scan_status,
            "source_scans": asdict(ss) if ss else None,
            "bgc_crosswalk": [b.crosswalk_dict() for b in self.bgcs],
            # --- Fields filled by Mamey v1.2 prompt during judgment ---
            "top_bgc_targets": [],
            "split_pathway_candidates": _split_candidates,
            "hallucination_traps_triggered": [],
            "resistance_gene_summary": self.resistance_gene_summary(),
            "wet_lab_priorities": [],
            "metabolomics_targets": [],
            "missingness": [],
            "recommended_next_steps": [],
            # --- Cross-strain context (populated by master workbook writer) ---
            "cross_strain_context": {
                "master_workbook": self.context.master_path,
                "related_strains_in_master": [],
                "shared_bgc_families": [],
                "habitat_peers_in_master": 0,
            },
            "issues": self.issues,
        }
