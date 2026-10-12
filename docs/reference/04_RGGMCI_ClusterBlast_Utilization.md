# RG-GMCI uses ClusterBlast, not just KnownClusterBlast — source-verified

## Current owner and inference boundary

The original v9.7.117 explanation and historical line pointers remain below. Current owning locations are
`mamey/rggmci.py:748–760` for classification, `:811–829` for TXT selection, `:1036–1061` for subcluster
exclusion and (db_kind,reference) pools, and `:1138–1142` for separate database counters. The current source
still accepts both ClusterBlast and KnownClusterBlast while excluding SubClusterBlast from pairing.
The classifier's fallback means unknown names passed to that helper return clusterblast; parser filename
selection and validated records remain separate constraints, not proof any arbitrary file is genuine evidence.

Cross-genome reference sharing/subject tiling supports a candidate fragmented-locus interpretation; it does
not physically link contigs or establish one pathway or compound. Complete reference-genome assumptions,
exact query/subject bindings and the final aggregation/gate receipt must be for the selected claim.
Verify historical calibration, cryptic-cluster prevalence and complete-reference assumptions separately. Read [current source scope](06_CURRENT_SOURCE_SCOPE.md) and preserve every focal/
partner strain / full node-or-contig / region / BGC alias. Bind actual pair results and source provenance before reuse.



**Status:** Correctness clarification · verified against `mamey/rggmci.py` @ bundle v9.7.117 · 2026-06-23
**Why this exists:** An overview write-up described RG-GMCI's evidence as *KnownClusterBlast* only. That is incomplete. RG-GMCI consumes the cross-genome **ClusterBlast** data as a first-class evidence source. This note pins the exact source lines so the distinction is unambiguous and does not get lost again.

---

## The three antiSMASH BLAST databases

antiSMASH emits three TXT families, distinguished in code by `ClusterBlastReference.db_kind` (`rggmci.py:368`):

- **`clusterblast`** — cross-genome GenBank neighbours. Other genomes that carry a homologous locus. This is the evidence that links *split fragments of one cluster across contigs*, because a complete reference genome tiles both arms.
- **`knownclusterblast`** — characterized MIBiG reference clusters. Similarity to a *named* compound's BGC.
- **`subclusterblast`** — sub-operon / sub-cluster hits. **Excluded** from the pairing pool (kept only as a functional marker).

The classifier is `rggmci.py:_classify_db_kind` (lines 542–553). Order matters there: `knownclusterblast` and `subclusterblast` both contain the substring `clusterblast`, so they are tested first; anything else falls through to `clusterblast`.

## RG-GMCI ingests ClusterBlast — the proof

**1. Parse (`rggmci.py:parse_clusterblast_reference_map`, line ~614):** the glob accepts any `.txt` whose name contains `clusterblast` **or** `knownclusterblast`. The cross-genome `clusterblast/` directory is read, not skipped.

```
if "clusterblast" not in low and "knownclusterblast" not in low:
    continue        # only non-ClusterBlast TXT is skipped
```

**2. Pairing pool (`rggmci.py`, line 824):** the only exclusion is `subclusterblast`. Both `clusterblast` and `knownclusterblast` records enter pairing.

```
ref_records = [r for r in all_records if r.db_kind != "subclusterblast"]
```

**3. Pool keying (line 832):** the pool is keyed on `(db_kind, ref)`, so a `clusterblast` hit and a `knownclusterblast` hit to the same accession are tracked as distinct supporting references — neither shadows the other.

**4. Per-pair accounting (lines 901–909):** every rescue pair separately counts `clusterblast_refs` and `knownclusterblast_refs`. A split can be supported, scored, and promoted on **cross-genome ClusterBlast homology with zero MIBiG/KnownClusterBlast hits**.

```
acc["db_kinds"].add(db_kind)
if db_kind == "knownclusterblast":
    acc["knownclusterblast_refs"] += 1
elif db_kind == "clusterblast":
    acc["clusterblast_refs"] += 1
```

## Why this is the correct design

RG-GMCI's job is to recognize when assembly fragmentation has split one biosynthetic locus across contigs. The signal for that is a *complete reference genome* (a ClusterBlast cross-genome neighbour) whose subjects tile across both fragments — the subject-tiling verdict (`COMPLEMENTARY_SPLIT`) is computed on those cross-genome subjects. Restricting to KnownClusterBlast/MIBiG would blind the rescue to every split whose parent compound is not in MIBiG — which is most cryptic clusters, i.e. exactly the discovery targets. The historical fix at `rggmci.py:56` notes a prior version where the linking coordinate "was computable from data already parsed onto `ClusterBlastReference.subjects`, but was dropped before output" — the lesson that drove the current explicit ClusterBlast utilization.

## What an overview should say

> RG-GMCI scores split-cluster rescue from antiSMASH ClusterBlast evidence — both cross-genome **ClusterBlast** neighbours and characterized **KnownClusterBlast** (MIBiG) references — excluding only SubClusterBlast. Cross-genome ClusterBlast is the primary signal for fragmentation splits; KnownClusterBlast adds named-compound corroboration when present.

*Source-verified against `mamey/rggmci.py` (lines 368, 542–553, 614, 824, 832, 901–909) @ Mamey v1.9.98 / bundle v9.7.117. KCB = similarity, not identity; capacity-level language throughout.*


## Shared invocation contract (`rggmci-shared-invocation-v2`)

The embedded pre-triage gate and standalone `run` use the same `run_archive` owner. Common preparation
binds complete region identities, source coordinates/products/order and pre-enrichment records. Internal snapshots require an immutable parser-created
process-local capability bound to archive bytes; caller JSON/hashes are not derivation authority. The
public standalone `run` rejects snapshot overrides. The
high-level default now supplies archive sequence context to the unchanged scoring gates. This is a
behavior-affecting standalone input migration: complexity-sensitive outcomes can differ from older
standalone runs. Explicit low-level `contigs=None` still means unavailable; explicit high-level None
disables automatic extraction. FASTA-first/longest-GBK-per-contig fallback is retained; clipped region
sequence is not a whole genome. Receipts contain lengths/hashes, never nucleotide/protein payloads.

Expected TypeError/ValueError/AttributeError coordinate failures retain legacy partial bounds and shared
diagnostics. Unexpected exceptions and typed resource refusals propagate. Relevant guarded GBK/FASTA
members refuse common intake before a subset is reported. General source-reader malformed/empty-member
warnings remain visible. The embedded wrapper cannot convert a canonical preparation refusal into an
empty successful RGGMCI result.

Both routes default to completion auto, sensitivity sensitive, threads4, residue scope st_paralog and
no registry anchor. MIBiG/Pfam database assets resolve explicit path, then the corresponding RGGMCI environment variable,
then an explicitly supplied registry anchor. Mamey no longer searches its installation ancestry
implicitly. A missing higher-priority database retains its explicit missing state. Existing aligner fallback remains:
DIAMOND tries explicit, then environment, then PATH; completion can fall back to BLAST+. Receipts bind
the actual selected content. Standalone
`--registry-from` matches Mamey `--rggmci-registry-from`; `--label` matches `--rggmci-label` for one input.
Mamey exposes matching `--rggmci-threads`, `--rggmci-diamond`, `--rggmci-diamond-db`,
`--rggmci-residue-scope`, `--rggmci-residue-work-dir` and `--rggmci-completion-work-dir` controls.
Shared threads reach both existing completion and residue interfaces; legacy low-level residue calls
retain their prior default. Completion OFF skips optional aligner probing; an explicit residue database
is a distinct requested layer. No automatic database download is introduced.

Per successful input the canonical set is eight artifacts: JSON and seven TSVs (ranked pairs, related
loci, candidate groups, summary, and three completion tables). Every row key is retained, including
later-row-only fields; nested evidence uses JSON cells with spreadsheet protection. Empty candidate
tables have headers only. Empty completion tables retain their explicit tier row. JSON includes full
region metadata and four-component endpoint identities: logical strain / full physical contig / region /
BGC alias. Ambiguous alias/source bindings refuse instead of being guessed. Scientific results and
effective resource fingerprints are shared; distribution/path/provenance presentation is confined to
`wrapper_context`. Compare complete analytical data, not a selected subset of scores.

Standalone primary writes remain exclusive and use whole-roster preflight; batch failures retain the
attempted-input denominator. Per-input canonical summary/group TSVs coexist with aggregate SUMMARY.tsv
and CANDIDATE_GROUPS.tsv. Mamey writes its canonical set before sealing with prefix
`<strain>_4A_RGGMCI_canonical`; legacy CSV/workbook views derive from the same result and remain distinct
presentation contracts. No legacy sealed package is rewritten. Shared source is an implementation
contract; runtime parity, optional active-resource profiles and published standalone synchronization
require their own bound validation. Candidate labels remain unadjudicated homology hypotheses, not
physical joins, compound identity or biological accuracy.
