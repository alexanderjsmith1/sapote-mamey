# RG-GMCI uses ClusterBlast, not just KnownClusterBlast — source-verified

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
