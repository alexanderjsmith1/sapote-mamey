# Quarantine recovery support card — `<STRAIN> / <FULL_NODE_OR_CONTIG> / <REGION> / <BGC_ALIAS>`


Manual support template; placeholders are not observations, QA results or approved prose. Bind all four
identity fields from one source record and use them in the owned output filename. Select actual task,
source package/profile, complete roster and scope before filling fields. This template is a companion
review surface, not the native full48/current50 emitted card or its finished acceptance contract.
Keep one owned candidate and source index; reference existing evidence by path/portable locator plus
SHA-256 and line/member, without copying source packages/databases/report assets. Actual source/job,
claim-safety, profile/content and owner review remain separate; no placeholder or tier label runs them.

## Recovery disposition

- **Priority rank:** `<RANK>`
- **Value tier:** `<THESIS_READY|USEFUL_WITH_LIMITATIONS|CONTEXT_ONLY|HOLD>`
- **Worker status:** `<actual task work state; do not predeclare completion>`
- **QA status:** `PENDING_FINAL_VALIDATION`
- **Expected proteins:** `<E>`
- **Direct-hit union:** `<D>` (count; display D/E separately below)
- **No-significant-hit proteins:** `<N>`
- **Unresolved/unavailable direct-query proteins:** `<U>`
- **Claim ceiling:** `<maximum defensible capacity-level statement and explicit exclusions>`

## Executive verdict

`<One short paragraph: locus completeness, strongest architecture, direct-query coverage, principal limitation, and safe use.>`

## 1. Source lock and locus identity

| Item | Exact audited source | Result |
|---|---|---|
| Assignment row | `<assignment workbook and row/rank>` | `<complete four-part identity / owned path / source binding>` |
| Current manifest | `<current package>/manifest.json` | `<workflow version and assembly tier>` |
| Crosswalk | `<current package>/<crosswalk.csv>` | `<BGC → node, region, coordinates, boundary>` |
| Inventory | `<current package>/<inventory.csv>` | `<length, products, architecture, claim ceiling>` |
| Exact antiSMASH region | `<raw archive.zip>::<exact region.gbk>` | `<antiSMASH version, products, boundary>` |
| Locus/gene inventory | `<exact locus CSV or raw GBK>` | `<E proteins>` |
| Secondary strain capture | `<optional exact path>` | `secondary aggregation only; not independent validation` |
| Quarantined artifact | `<exact DOCX path>` | `read-only prior content; no DOCX write` |

## 2. Complete gene-by-gene verdict

| Protein | Coordinates/strand/aa | Raw-query sequence check | Domain/HMM evidence | NCBI nr | EBI | Local Swiss-Prot | Final verdict |
|---|---|---|---|---|---|---|---|
| `<gene 1>` | `<...>` | `<MATCH/MISMATCH/UNAVAILABLE; checksum>` | `<observed evidence>` | `<state and result>` | `<state and result>` | `<state and result>` | `<role plus uncertainty>` |

### Visible accession links

- `<database and accession>: <public URL>`

## 3. Homology channels

### NCBI nr

- **Status:** `<DIRECT_HIT|NO_SIGNIFICANT_HIT|UNAVAILABLE>`.
- **Source:** `<exact result path>`.
- **Coverage:** `<n/E>`.
- **Ceiling:** similarity supports role/family context, not exact product identity.

### EBI

- **Status:** `<DIRECT_HIT|NO_SIGNIFICANT_HIT|EBI_UNAVAILABLE>`.
- **Source:** `<exact result path or explicit absent-artifact statement>`.
- **Coverage:** `<n/E>`.
- **Ceiling:** do not substitute another database's row.

### Local Swiss-Prot

- **Status:** `<DIRECT_HIT|NO_SIGNIFICANT_HIT|UNAVAILABLE>`.
- **Source:** `<exact result path>`.
- **Coverage:** `<n/E>`.
- **Ceiling:** curated subject annotations do not transfer product or substrate.

### Union and unresolved coverage

`<State D/E, N, U, overlap between channels, and why the denominator closes.>`

## 4. Captured architecture and alternatives

`<Observed gene/domain order, complete modules, missing release/tailoring/transport/regulation, boundary impact, and at least two competing explanations.>`

## 5. Cluster-comparison evidence

### General ClusterBlast

- **Source:** `<exact raw/package source>`.
- **Result:** `<checked result or no-result>`.
- **Ceiling:** local homology/neighborhood context only.

### KnownClusterBlast/MIBiG

- **Source:** `<exact raw/package source>`.
- **Result:** `<rank, accession, query and subject denominators>`.
- **Ceiling:** similarity anchor only; named compounds remain comparator labels.

### SubClusterBlast

- **Source:** `<exact raw source>`.
- **Result:** `<checked result or no-result>`.

### Strain-level capture synthesis

- **Source:** `<optional exact capture files>`.
- **Result:** `<assembly burden, KCB profile, routing membership>`.
- **Ceiling:** secondary aggregation, not independent validation.
- **Excluded fields:** `<unverified taxonomy/source, zero availability counts, or other unsafe imports>`.

## 6. Cohort and cross-contig context

### Current BiG-SCAPE

- **Source:** `<exact run/cutoff TSV>`.
- **Result:** `<family ID and member count>`.
- **Ceiling:** cohort recurrence/placement only; no identity or novelty claim.

### Legacy BiG-SCAPE

- **Source:** `<optional exact legacy source>`.
- **Result:** `<historical namespace only>`.
- **Ceiling:** do not merge namespaces or treat legacy placement as current.

### RG-GMCI

- **Source:** `<exact ranked/evidence source>`.
- **Candidates:** `<partners and confidence or no-result>`.
- **Linkage status:** `NOT_LINKED_ACROSS_CONTIGS` unless sequence plus compatible synteny proves continuity.

## 7. Taxonomy, ecology, and activity boundaries

- **Taxonomy/phylogeny source:** `<exact source or unavailable>`.
- **Taxonomic result and limit:** `<auditable placement; no product transfer>`.
- **Ecology source and limit:** `<collection context only; no locus function>`.
- **Activity source and limit:** `<strain/extract only or unavailable; no BGC phenotype assignment>`.

## 8. Value tier and safe use

`<Why this exact tier fits.>`

Defensible uses:

- `<use 1>`
- `<use 2>`

Not defensible:

- exact product identity;
- production, expression, or bioactivity;
- novelty from similarity/family placement;
- physical cross-contig linkage without sequence and synteny.

## 9. Missing evidence and next decision

`<Prioritized missing evidence, highest-value next experiment, and what decision it would unlock.>`

## 10. QA receipt

- Assignment tuple and ownership boundary: `<PASS/FAIL>`.
- Current crosswalk and exact region: `<PASS/FAIL>`.
- Protein denominator: expected `<E>`; audited `<E>`.
- Direct-hit union/no-hit/unresolved: `<D>/<N>/<U>`.
- Raw-query sequence checks: `<n/E>`.
- NCBI nr, EBI, and local Swiss-Prot separated: `<PASS/FAIL>`.
- Exact source paths verified: `<PASS/FAIL>`.
- Visible public accession URLs: `<count>`.
- Comparator and cohort ceilings: `<PASS/FAIL>`.
- Physical-linkage ceiling: `<PASS/FAIL>`.
- Claim-safety linter: `<PASS/FAIL>`.
- Card/ledger reconciliation: `<PASS/FAIL>`.
- DOCX writes: `NONE`.


Use docs/MODE_B_SUPPORT_CARD_CONTRACT.md for exact checker headings/metadata and scope. tools/audit_modeb_support_card.py is a pattern/count/limited-source-existence screen; it does not verify raw query SHA-256, job receipts, every URL or canonical membership. Its ctg-tag regex must not cause renaming of real genes. PENDING_FINAL_VALIDATION intentionally blocks that screen; update QA only from actual retained findings and independent source review. DOCX writes NONE is a task-specific receipt to confirm, not a pre-filled historical fact or a universal companion ban.
