# Mode B gene-first v2 candidate contract

Status: engineering candidate only; judgment deferred.

This candidate turns a compact, content-addressed evidence stage into a fast review surface. It does not run similarity searches, domain searches, cassette detectors, rendering, or workspace discovery. It does not generate a governed long-form card or make a scientific acceptance decision.

## Exact identity

Every per-locus and per-gene row carries the complete identity in this order:

`strain / full node-or-contig / region / BGC alias`

The stage directory and every per-locus output filename carry the same four components in filesystem-safe form. Missing, shortened, conflicting, placeholder, or unsafe components are pre-write refusals.

## Staged-once evidence

The five prepared inputs are an identity record, ordered gene roster, normalized evidence table, locus-context record, and producer-receipt table. The stage sealer validates them before writing one self-excluding receipt.

The query-roster digest binds the complete identity and each ordered `(gene_order, locus_tag, protein_sha256)` tuple. Each producer receipt separately binds its tool and version, parameter fingerprint, query-roster digest, database or model snapshot, normalized output, resource policy, and recorded thread count. Every evidence row must match its producer's channel, output locator and SHA-256, receipt SHA-256, and database fields.

A changed query, database snapshot, parameter fingerprint, or normalized producer output produces a different stage ID. Sealed members and unexpected extra members are rejected on reload.

## Required separated channels

The canonical channels are:

- `nr`
- `clustered_nr`
- `local_swissprot`
- `mibig`
- `domain`
- `cassette`
- `neighborhood`

The legacy input labels `clusterednr` and `swissprot` may be normalized only when the receipt records each normalization. Channels are never merged and no similarity database wins by precedence.

Each canonical gene has an explicit row in `nr`, `clustered_nr`, and `local_swissprot`: either a valid rank-1 binding or a typed workflow gap. The remaining channels have an explicit gene- or locus-level state. `REGISTRY_ONLY_NOT_EXECUTED` is descriptive and contributes no detector support.

Missing, unbound, or unexecuted evidence is never treated as biological absence.

## Paired `nr` and `clustered_nr` comparison

Rank-1 observations are paired by complete identity, locus tag, and query-sequence SHA-256. The output retains both full hit names and metric sets and always records `precedence_winner=NONE_BY_CONTRACT`.

Primary states are:

- `PAIRED_BOUND_FAMILY_CONCORDANT`
- `PAIRED_BOUND_FAMILY_DIVERGENT`
- `PAIRED_BOUND_UNRESOLVED_FAMILY`
- `NR_ONLY_BOUND`
- `CLUSTERED_NR_ONLY_BOUND`
- `NEITHER_BOUND_TYPED_GAP`

Coverage differences of at least 25 percentage points and identity differences of at least 15 percentage points are descriptive secondary flags. These engineering thresholds prioritize review; they do not establish functional truth.

## Independent completeness diagnostics

Four axes remain separate:

1. BGC boundary state on its contig.
2. Assembly fragmentation tier.
3. Per-protein partialness.
4. Detector-window relationship to the region.

The interpreter consumes the canonical result owned by `mamey.fragment_ceiling`; it does not reimplement that policy. A fragmented assembly does not make every locus partial, and an interior locus does not make an assembly contiguous.

## Ranked important-gene review

The rank is a review order, not biological importance, novelty, activity, or lead value.

Structural importance and uncertainty-resolution value are shown separately. The candidate review priority is:

`0.65 x structural importance + 0.35 x uncertainty-resolution value`

The output retains every additive component, the two subtotal axes, the final priority, deterministic tie-breaks, and a claim ceiling. Registry-only cassette definitions add no structural support.

## Warm-stage authoring target

The approximate ten-minute target begins after the evidence stage is sealed. The fast pass verifies compact hashes, reads channel coverage and disagreements, reviews the core and ranked genes, drafts one central model and alternatives, applies completeness limits, chooses one highest-information next analysis, and makes an optional summary-overlay decision.

Producer runtime is explicitly excluded. Recorded elapsed times and stage age are operational telemetry, not a universal performance claim.

## Figure Factory noncontamination

Mode B can produce a separate overlay only for `consumer_plane=BGC_SUMMARY`. The authoring receipt and its four retained members are rehashed, and its complete identity, stage ID, and stage-receipt digest must match the decision before output.

Allowed actions are:

- `RETAIN_SOURCE_SUMMARY`
- `FLAG_SUMMARY_ONLY`
- `WITHHOLD_SUMMARY_PENDING_BINDING`
- `PROPOSE_SUMMARY_RECLASSIFICATION`

The source class is always retained separately from a proposed class. Proposals remain owner-review candidates and are never applied automatically.

The overlay refuses `GENE`, `DOMAIN`, `MODULE`, `CASSETTE`, `NEIGHBORHOOD`, and `RAW_EVIDENCE`. Those independent figures continue to use their own immutable source tables.

## Authority ceiling

These modules are an additive portable candidate. They do not wire a CLI, integrate into a release, change a version, modify existing cards or renderers, export data, establish scientific acceptance, or support a publication claim.

Similarity is not identity. Capacity is not production. Judgment remains deferred.
